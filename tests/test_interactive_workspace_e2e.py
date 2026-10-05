from pathlib import Path
from threading import Thread
import json
import os
import tempfile
import unittest
from urllib.request import Request, urlopen

from vesiclescope.run_bundles import deserialize_run_bundle
from vesiclescope.ui.app import WorkspaceApplication
from vesiclescope.ui.server import create_server
from vesiclescope.ui.workspace import Workspace


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")
REVISION = os.environ.get("VESICLESCOPE_REVISION")


def request_json(url: str, *, method: str = "GET", payload: dict | None = None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, method=method, data=data, headers=headers)
    with urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


@unittest.skipUnless(
    RUNNER and REVISION,
    "native runner and exact VesicleScope revision are required",
)
class InteractiveWorkspaceEndToEndTests(unittest.TestCase):
    def test_create_execute_inspect_and_download_run_through_http_surface(self) -> None:
        assert RUNNER is not None
        assert REVISION is not None

        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace").initialize()
            app = WorkspaceApplication(
                workspace,
                Path(RUNNER),
                REVISION,
            )
            server = create_server(app, port=0)
            host, port = server.server_address
            self.assertEqual(host, "127.0.0.1")
            base = f"http://127.0.0.1:{port}"
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, created = request_json(
                    f"{base}/api/example",
                    method="POST",
                    payload={"name": "baseline.json"},
                )
                self.assertEqual(status, 201)
                self.assertEqual(created, {"name": "baseline.json"})

                status, run = request_json(
                    f"{base}/api/run",
                    method="POST",
                    payload={
                        "experiment": "baseline.json",
                        "run_name": "baseline.run.json",
                        "grid_spacing_micron": 10.0,
                        "time_step_min": 0.1,
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(run, {"name": "baseline.run.json"})

                status, state = request_json(f"{base}/api/state")
                self.assertEqual(status, 200)
                self.assertEqual(state["revision"], REVISION.lower())
                self.assertEqual(
                    [item["name"] for item in state["experiments"] if item["valid"]],
                    ["baseline.json"],
                )
                self.assertEqual(
                    [item["name"] for item in state["runs"] if item["valid"]],
                    ["baseline.run.json"],
                )

                status, inspected = request_json(
                    f"{base}/api/run?name=baseline.run.json"
                )
                self.assertEqual(status, 200)
                self.assertEqual(inspected["vesiclescope_revision"], REVISION.lower())
                self.assertEqual(inspected["engine"]["name"], "BioFVM")
                self.assertEqual(inspected["engine"]["physicell_release"], "1.14.2")
                self.assertEqual(
                    inspected["experiment"]["scientific_status"],
                    "synthetic_benchmark",
                )
                self.assertEqual(inspected["numerics"]["grid_spacing_micron"], 10.0)
                self.assertEqual(inspected["numerics"]["time_step_min"], 0.1)
                self.assertGreater(len(inspected["samples"]), 1)
                self.assertEqual(
                    inspected["final"]["time_min"],
                    inspected["experiment"]["duration_min"],
                )
                self.assertIn("final_field", inspected)
                self.assertEqual(
                    len(inspected["final_field"]["values"]),
                    inspected["grid"]["nx"] * inspected["grid"]["ny"],
                )

                with urlopen(
                    f"{base}/download/run?name=baseline.run.json"
                ) as response:
                    self.assertEqual(response.status, 200)
                    downloaded = response.read()
                    self.assertIn(
                        "attachment;",
                        response.headers["Content-Disposition"],
                    )

                bundle = deserialize_run_bundle(downloaded)
                self.assertEqual(bundle.vesiclescope_revision, REVISION.lower())
                self.assertEqual(
                    bundle.experiment.experiment_id,
                    inspected["experiment"]["experiment_id"],
                )
                self.assertEqual(bundle.result.engine.engine, "BioFVM")
                self.assertEqual(
                    bundle.result.samples[-1].integrated_field_quantity,
                    inspected["final"]["extracellular_quantity"],
                )
                self.assertEqual(
                    bundle.result.samples[-1].internalized_field_quantity,
                    inspected["final"]["internalized_quantity"],
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


    def test_derive_synthetic_variant_then_execute_and_persist_bundle(self) -> None:
        assert RUNNER is not None
        assert REVISION is not None

        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory) / "workspace").initialize()
            app = WorkspaceApplication(workspace, Path(RUNNER), REVISION)
            server = create_server(app, port=0)
            _, port = server.server_address
            base = f"http://127.0.0.1:{port}"
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                status, created = request_json(
                    f"{base}/api/example",
                    method="POST",
                    payload={"name": "baseline.json"},
                )
                self.assertEqual(status, 201)
                self.assertEqual(created, {"name": "baseline.json"})

                status, baseline = request_json(
                    f"{base}/api/experiment?name=baseline.json"
                )
                self.assertEqual(status, 200)
                release_rates = {
                    item["identifier"]: item["rate"]
                    for item in baseline["release_sources"]
                }
                uptake_rates = {
                    item["identifier"]: item["uptake_rate"] * 1.25
                    for item in baseline["uptake_sinks"]
                }

                status, derived = request_json(
                    f"{base}/api/derive",
                    method="POST",
                    payload={
                        "source": "baseline.json",
                        "name": "variant.json",
                        "experiment_id": "synthetic.workspace.variant",
                        "duration_min": baseline["duration_min"],
                        "sample_every_min": baseline["sample_every_min"],
                        "diffusion_value": baseline["diffusion"]["value"] * 0.75,
                        "decay_value": baseline["decay"]["value"],
                        "initial_concentration_value": baseline["initial_concentration"]["value"],
                        "release_rates": release_rates,
                        "uptake_rates": uptake_rates,
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(derived["name"], "variant.json")
                self.assertEqual(
                    derived["experiment"]["experiment_id"],
                    "synthetic.workspace.variant",
                )
                self.assertEqual(
                    derived["experiment"]["scientific_status"],
                    "synthetic_benchmark",
                )
                self.assertEqual(
                    derived["experiment"]["diffusion"]["value"],
                    baseline["diffusion"]["value"] * 0.75,
                )

                status, baseline_run = request_json(
                    f"{base}/api/run",
                    method="POST",
                    payload={
                        "experiment": "baseline.json",
                        "run_name": "baseline.run.json",
                        "grid_spacing_micron": 10.0,
                        "time_step_min": 0.1,
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(baseline_run, {"name": "baseline.run.json"})

                status, run = request_json(
                    f"{base}/api/run",
                    method="POST",
                    payload={
                        "experiment": "variant.json",
                        "run_name": "variant.run.json",
                        "grid_spacing_micron": 10.0,
                        "time_step_min": 0.1,
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(run, {"name": "variant.run.json"})

                with urlopen(
                    f"{base}/download/run?name=variant.run.json"
                ) as response:
                    downloaded = response.read()

                bundle = deserialize_run_bundle(downloaded)
                self.assertEqual(
                    bundle.experiment.experiment_id,
                    "synthetic.workspace.variant",
                )
                self.assertEqual(bundle.vesiclescope_revision, REVISION.lower())
                self.assertEqual(
                    bundle.experiment.diffusion.value,
                    baseline["diffusion"]["value"] * 0.75,
                )
                self.assertTrue(
                    all(
                        sink.uptake_rate.value
                        == uptake_rates[sink.identifier]
                        for sink in bundle.experiment.uptake_sinks
                    )
                )

                status, comparison = request_json(
                    f"{base}/api/compare?left=baseline.run.json&right=variant.run.json"
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    comparison["left_experiment_id"],
                    baseline["experiment_id"],
                )
                self.assertEqual(
                    comparison["right_experiment_id"],
                    "synthetic.workspace.variant",
                )
                self.assertGreater(len(comparison["left_series"]), 1)
                self.assertGreater(len(comparison["right_series"]), 1)
                self.assertTrue(comparison["spatial"]["compatible"])
                self.assertEqual(
                    len(comparison["spatial"]["values"]),
                    comparison["spatial"]["nx"] * comparison["spatial"]["ny"],
                )
                self.assertEqual(comparison["left_revision"], REVISION.lower())
                self.assertEqual(comparison["right_revision"], REVISION.lower())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
