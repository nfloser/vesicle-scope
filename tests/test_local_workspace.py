from pathlib import Path
from threading import Thread
import http.client
import json
import tempfile
import unittest
from urllib.request import Request, urlopen

from vesiclescope.ui.app import WorkspaceApplication
from vesiclescope.ui.server import create_server
from vesiclescope.ui.workspace import Workspace



def post_json(url: str, payload: dict):
    request = Request(
        url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


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


    def test_workspace_derives_new_synthetic_experiment_without_overwriting_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace").initialize()
            workspace.create_baseline_experiment("baseline.json")
            source = workspace.read_experiment("baseline.json")

            output = workspace.derive_synthetic_variant(
                source_name="baseline.json",
                output_name="variant.json",
                experiment_id="synthetic.ui.variant",
                duration_min=30.0,
                sample_every_min=5.0,
                diffusion_value=125.0,
                decay_value=0.0,
                initial_concentration_value=0.0,
                release_rates={
                    item.identifier: 150.0
                    for item in source.release_sources
                },
                uptake_rates={
                    item.identifier: 0.75
                    for item in source.uptake_sinks
                },
            )

            self.assertEqual(output.name, "variant.json")
            self.assertEqual(workspace.read_experiment("baseline.json").diffusion.value, 100.0)
            derived = workspace.read_experiment("variant.json")
            self.assertEqual(derived.experiment_id, "synthetic.ui.variant")
            self.assertEqual(derived.diffusion.value, 125.0)
            self.assertEqual(derived.release_sources[0].release_rate.value, 150.0)
            self.assertTrue(
                all(item.uptake_rate.value == 0.75 for item in derived.uptake_sinks)
            )

            with self.assertRaisesRegex(ValueError, "already exists"):
                workspace.derive_synthetic_variant(
                    source_name="baseline.json",
                    output_name="variant.json",
                    experiment_id="synthetic.ui.other",
                    duration_min=20.0,
                    sample_every_min=5.0,
                    diffusion_value=100.0,
                    decay_value=0.0,
                    initial_concentration_value=0.0,
                    release_rates={
                        item.identifier: item.release_rate.value
                        for item in source.release_sources
                    },
                    uptake_rates={
                        item.identifier: item.uptake_rate.value
                        for item in source.uptake_sinks
                    },
                )

    def test_loopback_api_derives_synthetic_variant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace").initialize()
            runner = Path(directory) / "runner"
            runner.write_text("", encoding="utf-8")
            app = WorkspaceApplication(workspace, runner, "c" * 40)
            server = create_server(app, port=0)
            _, port = server.server_address
            base = f"http://127.0.0.1:{port}"

            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, _ = post_json(
                    f"{base}/api/example",
                    {"name": "baseline.json"},
                )
                self.assertEqual(status, 201)

                with urlopen(
                    f"{base}/api/experiment?name=baseline.json",
                    timeout=30,
                ) as response:
                    source = json.loads(response.read().decode("utf-8"))

                status, derived = post_json(
                    f"{base}/api/derive",
                    {
                        "source": "baseline.json",
                        "name": "variant.json",
                        "experiment_id": "synthetic.http.variant",
                        "duration_min": 25.0,
                        "sample_every_min": 5.0,
                        "diffusion_value": 140.0,
                        "decay_value": 0.0,
                        "initial_concentration_value": 0.0,
                        "release_rates": {
                            item["identifier"]: item["rate"]
                            for item in source["release_sources"]
                        },
                        "uptake_rates": {
                            item["identifier"]: 0.65
                            for item in source["uptake_sinks"]
                        },
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(derived["name"], "variant.json")
                self.assertEqual(
                    derived["experiment"]["experiment_id"],
                    "synthetic.http.variant",
                )
                self.assertEqual(derived["experiment"]["diffusion"]["value"], 140.0)
                self.assertTrue(
                    all(
                        item["uptake_rate"] == 0.65
                        for item in derived["experiment"]["uptake_sinks"]
                    )
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

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
                    self.assertIn("Numerical comparison only", html)
                    self.assertIn("no interpolation is performed", html)
                    self.assertIn("Final field difference (right − left)", html)
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
