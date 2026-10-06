from io import BytesIO
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
from unittest.mock import patch
import zipfile

from test_combine_archive import bundle_for, rewrite_archive
from vesiclescope.scenarios import diffusion_uptake_factor_conditions
from vesiclescope.run_bundles import run_bundle_payload_sha256, serialize_run_bundle
from vesiclescope.combine_archive import serialize_batch_combine_archive, deserialize_batch_combine_archive


def inputs():
    experiments = tuple(c.experiment for c in diffusion_uptake_factor_conditions()[:2])
    runs = tuple(bundle_for(e) for e in experiments)
    manifest = {
        'schema': 'vesiclescope.experiment-batch', 'version': 1,
        'scientific_status': 'explicit input batch; no sampling or biological distribution implied',
        'vesiclescope_revision': runs[0].vesiclescope_revision,
        'numerics': {'grid_spacing_micron': 10.0, 'time_step_min': 0.1},
        'members': [dict(index=i, input_filename=f'e{i}.json', experiment_id=e.experiment_id,
                         run_filename=f'r{i}.json', run_bundle_payload_sha256=run_bundle_payload_sha256(r))
                    for i, (e, r) in enumerate(zip(experiments, runs), 1)]}
    return manifest, experiments, runs


class BatchArchiveTests(unittest.TestCase):
    def test_deterministic_ordered_roundtrip_and_master(self):
        manifest, experiments, runs = inputs()
        data = serialize_batch_combine_archive(manifest, experiments, runs)
        self.assertEqual(data, serialize_batch_combine_archive(manifest, experiments, runs))
        project = deserialize_batch_combine_archive(data)
        self.assertEqual(project.experiments, experiments)
        self.assertEqual(project.runs, runs)
        self.assertEqual([m['index'] for m in project.manifest['members']], [1, 2])
        with zipfile.ZipFile(BytesIO(data)) as archive:
            self.assertIn(b'./batch-manifest.json" format="http://purl.org/NET/mediatypes/application/json" master="true"', archive.read('manifest.xml'))

    def test_rejects_wrong_digest_identity_order_and_duplicates(self):
        for field, value in [('run_bundle_payload_sha256', '0'*64), ('experiment_id', 'wrong'), ('index', 2)]:
            manifest, experiments, runs = inputs()
            manifest['members'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                serialize_batch_combine_archive(manifest, experiments, runs)
        manifest, experiments, runs = inputs()
        with self.assertRaises(ValueError):
            serialize_batch_combine_archive(manifest, experiments, runs[:1])
        with self.assertRaises(ValueError):
            serialize_batch_combine_archive(manifest, experiments, runs[::-1])

    def test_reader_rejects_extra_and_unsafe_members(self):
        data = serialize_batch_combine_archive(*inputs())
        for name in ['extra.json', '../escape']:
            output = BytesIO()
            with zipfile.ZipFile(BytesIO(data)) as source, zipfile.ZipFile(output, 'w') as target:
                for item in source.infolist():
                    target.writestr(item.filename, source.read(item.filename))
                target.writestr(name, b'{}')
            with self.subTest(name=name), self.assertRaises(ValueError):
                deserialize_batch_combine_archive(output.getvalue())

    def test_cli_roundtrip_uses_stored_runs_without_solver(self):
        from vesiclescope.cli import main
        manifest, experiments, runs = inputs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'batch-manifest.json').write_text(json.dumps(manifest))
            for member, run in zip(manifest['members'], runs):
                (root / member['run_filename']).write_bytes(serialize_run_bundle(run))
            from io import StringIO
            out = StringIO()
            with patch('subprocess.run', side_effect=AssertionError('solver invoked')), redirect_stdout(out):
                self.assertEqual(main(['archive', 'create-batch', str(root / 'batch-manifest.json'), '--output', str(root / 'batch.omex')]), 0)
                self.assertEqual(main(['archive', 'inspect', str(root / 'batch.omex')]), 0)
            self.assertIn('project_type: experiment-batch', out.getvalue())
            self.assertIn('stored_runs: 2', out.getvalue())

    def test_export_rejects_symlink_escape_and_preserves_existing_output(self):
        from vesiclescope.combine_archive import write_batch_combine_archive
        manifest, experiments, runs = inputs()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = root / 'batch'
            batch.mkdir()
            source = batch / 'batch-manifest.json'
            source.write_text(json.dumps(manifest))
            for member, run in zip(manifest['members'], runs):
                (batch / member['run_filename']).write_bytes(serialize_run_bundle(run))
            output = root / 'existing.omex'
            output.write_bytes(b'original')
            manifest['members'][0]['run_bundle_payload_sha256'] = '0'*64
            source.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                write_batch_combine_archive(source, output)
            self.assertEqual(output.read_bytes(), b'original')
            outside = root / 'outside.run.json'
            outside.write_bytes(serialize_run_bundle(runs[0]))
            run_path = batch / manifest['members'][0]['run_filename']
            run_path.unlink()
            run_path.symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'within manifest directory'):
                write_batch_combine_archive(source, output)

    def test_batch_metadata_must_match_runs(self):
        for field, value in [('vesiclescope_revision', 'b'*40), ('numerics', {}), ('scientific_status', '')]:
            manifest, experiments, runs = inputs()
            manifest[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                serialize_batch_combine_archive(manifest, experiments, runs)
        manifest, experiments, runs = inputs()
        manifest['members'][1]['run_filename'] = manifest['members'][0]['run_filename']
        with self.assertRaises(ValueError):
            serialize_batch_combine_archive(manifest, experiments, runs)

    def test_missing_member_is_rejected(self):
        original = serialize_batch_combine_archive(*inputs())
        output = BytesIO()
        with zipfile.ZipFile(BytesIO(original)) as source, zipfile.ZipFile(output, 'w') as target:
            for item in source.infolist():
                if item.filename != 'runs/member-002.run.json':
                    target.writestr(item.filename, source.read(item.filename))
        with self.assertRaises(ValueError):
            deserialize_batch_combine_archive(output.getvalue())

    def test_tampered_batch_digest_is_rejected(self):
        data = serialize_batch_combine_archive(*inputs())
        def tamper(name, payload):
            if name == 'batch-manifest.json':
                manifest = json.loads(payload)
                manifest['members'][0]['run_bundle_payload_sha256'] = '0'*64
                payload = json.dumps(manifest).encode()
            return name, payload
        with self.assertRaises(ValueError):
            deserialize_batch_combine_archive(rewrite_archive(data, tamper))
