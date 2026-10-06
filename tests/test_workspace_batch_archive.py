from pathlib import Path
import tempfile
import unittest
from threading import Thread
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
import json
from unittest.mock import patch
from test_batch_combine_archive import inputs
from vesiclescope.combine_archive import serialize_batch_combine_archive, deserialize_batch_combine_archive
from vesiclescope.run_bundles import write_run_bundle
from vesiclescope.ui.workspace import Workspace


class WorkspaceBatchArchiveTests(unittest.TestCase):
    def test_selected_runs_roundtrip_preserves_order_and_is_collision_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory)).initialize()
            manifest, experiments, runs = inputs()
            for i, run in enumerate(runs):
                write_run_bundle(workspace.run_path(f'r{i}.json'), run)
            data = workspace.export_batch_archive(('r1.json', 'r0.json'))
            self.assertEqual(deserialize_batch_combine_archive(data).runs, runs[::-1])
            first = workspace.import_batch_archive(data)
            second = workspace.import_batch_archive(data)
            self.assertEqual(tuple(workspace.read_run(n) for n in first['runs']), runs[::-1])
            self.assertTrue(set(first['experiments']).isdisjoint(second['experiments']))
            self.assertTrue(set(first['runs']).isdisjoint(second['runs']))
            self.assertEqual(workspace.export_batch_archive(tuple(first['runs'])), data)

    def test_failed_import_rolls_back_and_does_not_overwrite_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory)).initialize()
            workspace.create_baseline_experiment('existing.json')
            before = workspace.experiment_path('existing.json').read_bytes()
            data = serialize_batch_combine_archive(*inputs())
            original = Path.open
            calls = 0
            def fail(path, *args, **kwargs):
                nonlocal calls
                if args and args[0] == 'xb':
                    calls += 1
                    if calls == 3:
                        raise OSError('disk failure')
                return original(path, *args, **kwargs)
            with patch.object(Path, 'open', fail), self.assertRaises(OSError):
                workspace.import_batch_archive(data)
            self.assertEqual(workspace.list_experiment_names(), ('existing.json',))
            self.assertEqual(workspace.list_run_names(), ())
            self.assertEqual(workspace.experiment_path('existing.json').read_bytes(), before)

    def test_loopback_batch_export_import_and_rejection(self):
        from vesiclescope.ui.app import WorkspaceApplication
        from vesiclescope.ui.server import create_server
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = root / 'runner'
            runner.write_text('unused')
            workspace = Workspace(root / 'workspace').initialize()
            manifest, experiments, runs = inputs()
            for i, run in enumerate(runs):
                write_run_bundle(workspace.run_path(f'r{i}.json'), run)
            app = WorkspaceApplication(workspace, runner, 'a'*40)
            server = create_server(app, port=0)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_address[1]}'
            try:
                with patch('subprocess.run', side_effect=AssertionError('solver invoked')):
                    query = urlencode([('run', 'r1.json'), ('run', 'r0.json')])
                    with urlopen(base+'/download/batch-archive?'+query) as response:
                        self.assertEqual(response.headers['Content-Type'], 'application/zip')
                        data = response.read()
                    self.assertEqual(deserialize_batch_combine_archive(data).runs, runs[::-1])
                    request = Request(base+'/api/batch-archive/import', data=data, headers={'Content-Type': 'application/zip'})
                    with urlopen(request) as response:
                        self.assertEqual(response.status, 201)
                        imported = json.loads(response.read())
                    self.assertEqual(tuple(workspace.read_run(name) for name in imported['runs']), runs[::-1])
                    before = (workspace.list_experiment_names(), workspace.list_run_names())
                    request = Request(base+'/api/batch-archive/import', data=b'bad zip', headers={'Content-Type': 'application/zip'})
                    with self.assertRaises(HTTPError) as error:
                        urlopen(request)
                    self.assertEqual(error.exception.code, 400)
                    self.assertEqual((workspace.list_experiment_names(), workspace.list_run_names()), before)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_export_rejects_empty_duplicate_and_unsafe_selections(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory)).initialize()
            for selection in [(), ('x.json', 'x.json'), ('../x.json',)]:
                with self.subTest(selection=selection), self.assertRaises(ValueError):
                    workspace.export_batch_archive(selection)
