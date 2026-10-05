from pathlib import Path
from threading import Thread
import http.client
import json
import tempfile
import unittest
from urllib.request import urlopen

from vesiclescope.ui.app import WorkspaceApplication
from vesiclescope.ui.server import create_server
from vesiclescope.ui.workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def test_initialize_and_baseline_are_confined_to_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace").initialize()
            self.assertTrue(workspace.experiments_dir.is_dir())
            self.assertTrue(workspace.runs_dir.is_dir())

            path = workspace.create_baseline_experiment("baseline.json")
            self.assertEqual(path.parent, workspace.experiments_dir)
            self.assertEqual(workspace.list_experiment_names(), ("baseline.json",))

            with self.assertRaises(ValueError):
                workspace.experiment_path("../escape.json")
            with self.assertRaises(ValueError):
                workspace.run_path("nested/run.json")

    def test_invalid_experiment_file_is_reported_without_breaking_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            workspace = Workspace(root).initialize()
            runner = Path(directory) / "runner"
            runner.write_text("", encoding="utf-8")
            workspace.create_baseline_experiment("baseline.json")
            (workspace.experiments_dir / "broken.json").write_text("{", encoding="utf-8")

            app = WorkspaceApplication(workspace, runner, "a" * 40)
            state = app.state()
            by_name = {item["name"]: item for item in state["experiments"]}
            self.assertTrue(by_name["baseline.json"]["valid"])
            self.assertFalse(by_name["broken.json"]["valid"])

    def test_loopback_server_serves_health_state_and_packaged_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace").initialize()
            runner = Path(directory) / "runner"
            runner.write_text("", encoding="utf-8")
            app = WorkspaceApplication(workspace, runner, "b" * 40)
            server = create_server(app, port=0)
            host, port = server.server_address
            self.assertEqual(host, "127.0.0.1")

            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urlopen(f"http://127.0.0.1:{port}/api/health") as response:
                    health = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(health, {"ok": True})
                    self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

                with urlopen(f"http://127.0.0.1:{port}/api/state") as response:
                    state = json.loads(response.read().decode("utf-8"))
                    self.assertEqual(state["revision"], "b" * 40)
                    self.assertEqual(state["experiments"], [])
                    self.assertEqual(state["runs"], [])

                with urlopen(f"http://127.0.0.1:{port}/") as response:
                    html = response.read().decode("utf-8")
                    self.assertIn("VesicleScope", html)
                    self.assertIn("not experimental evidence", html)
                connection = http.client.HTTPConnection("127.0.0.1", port)
                connection.putrequest("GET", "/api/health", skip_host=True)
                connection.putheader("Host", "attacker.example")
                connection.endheaders()
                hostile = connection.getresponse()
                self.assertEqual(hostile.status, 400)
                payload = json.loads(hostile.read().decode("utf-8"))
                self.assertIn("Host", payload["error"])
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
