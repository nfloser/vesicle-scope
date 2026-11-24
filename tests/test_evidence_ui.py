import json
import os
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from vesiclescope.ui.app import WorkspaceApplication
from vesiclescope.ui.evidence_services import evidence_payload, synthesis_payload
from vesiclescope.ui.server import create_server
from vesiclescope.ui.workspace import Workspace


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")

SCENARIO = {
    "experiment": "baseline.json",
    "compound": "synthetic hormone",
    "target": "release_rate",
    "concentration": 100.0,
    "concentration_unit": "nM",
    "start_min": 10.0,
    "end_min": 40.0,
    "emax": 1.0,
    "ec50": 50.0,
    "hill": 1.0,
    "delay_min": 10.0,
    "baseline_concentration": 0.0,
    "duration_min": 60.0,
    "sample_every_min": 5.0,
    "segment_min": 5.0,
    "grid_spacing_micron": 10.0,
    "time_step_min": 0.1,
}


def post_json(url: str, payload: dict) -> tuple[int, dict]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class EvidencePayloadTests(unittest.TestCase):
    def test_payload_has_records_sources_and_gaps(self) -> None:
        payload = evidence_payload()
        self.assertGreaterEqual(len(payload["records"]), 40)
        self.assertTrue(payload["gaps"])
        for record in payload["records"]:
            self.assertTrue(record["source"]["identifier"])
            self.assertIn(record["kind"], ("quantity", "effect"))
            if record["source"]["url"]:
                self.assertTrue(record["source"]["url"].startswith("https://"))

    def test_synthesis_payload_is_json_serializable(self) -> None:
        payload = synthesis_payload()
        json.dumps(payload)
        self.assertEqual(len(payload["lines"]), 8)


class EvidenceHttpTests(unittest.TestCase):
    def start(self, directory: str, runner: Path) -> tuple[str, object]:
        workspace = Workspace(Path(directory) / "workspace").initialize()
        app = WorkspaceApplication(workspace, runner, "c" * 40)
        server = create_server(app, port=0)
        Thread(target=server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{server.server_address[1]}", server

    def test_evidence_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runner = Path(directory) / "runner"
            runner.write_text("", encoding="utf-8")
            base, server = self.start(directory, runner)
            try:
                with urlopen(f"{base}/api/evidence", timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                self.assertGreaterEqual(data["source_count"], 30)
                with urlopen(f"{base}/api/evidence/synthesis", timeout=30) as response:
                    synthesis = json.loads(response.read().decode("utf-8"))
                self.assertTrue(synthesis["ev_exceeds_brain_ecs_width"])
                status, _ = post_json(f"{base}/api/example", {"name": "baseline.json"})
                self.assertEqual(status, 201)
                status, error = post_json(f"{base}/api/exposure-scenario", {**SCENARIO, "target": "bad"})
                self.assertEqual(status, 400)
                self.assertIn("target", error["error"])
            finally:
                server.shutdown()
                server.server_close()

    @unittest.skipUnless(RUNNER, "native BioFVM runner is required")
    def test_exposure_scenario_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base, server = self.start(directory, Path(RUNNER))
            try:
                status, _ = post_json(f"{base}/api/example", {"name": "baseline.json"})
                self.assertEqual(status, 201)
                status, result = post_json(f"{base}/api/exposure-scenario", SCENARIO)
                self.assertEqual(status, 200, result)
                self.assertEqual(result["evidence"], "assumed")
                self.assertEqual(len(result["schedule"]), 12)
                ratios = [item["ratio"] for item in result["internalization_rate_ratio"]]
                self.assertEqual(ratios[0], 1.0)
                self.assertGreater(max(ratios), 1.0)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
