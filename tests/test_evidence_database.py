import json
import math
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from vesiclescope.domain import EffectOutcome, EvidenceCategory, ScientificParameter
from vesiclescope.evidence import QuantityValue, export_sqlite, load_evidence
from vesiclescope.evidence.synthesis import synthesize


DATA = Path(__file__).resolve().parents[1] / "vesiclescope" / "evidence" / "data"


class EvidenceRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = load_evidence()

    def test_packaged_registry_loads_and_matches_repository_copy(self) -> None:
        self.assertEqual(load_evidence(DATA), self.db)
        self.assertGreaterEqual(len(self.db.records), 20)

    def test_every_record_is_sourced_and_limited(self) -> None:
        for record in self.db.records:
            self.assertIn(record.source.id, self.db.sources)
            self.assertTrue(record.source.identifier)
            self.assertTrue(record.limitations, record.id)
            self.assertNotEqual(record.evidence, EvidenceCategory.SYNTHETIC_BENCHMARK)

    def test_every_source_is_cited(self) -> None:
        cited = {record.source.id for record in self.db.records} | {
            secondary
            for record in self.db.records
            for secondary in record.extra.get("secondary_sources", ())
        }
        self.assertEqual(cited, set(self.db.sources))

    def test_quantity_converts_to_provenance_parameter(self) -> None:
        parameter = self.db.get("plasma-sev-half-life-mouse").to_scientific_parameter(
            "blood.half_life"
        )
        self.assertIsInstance(parameter, ScientificParameter)
        self.assertEqual(parameter.unit, "min")
        self.assertTrue(parameter.source.identifier.startswith("doi:"))
        self.assertEqual(parameter.context.species, "mouse")

    def test_range_record_has_no_central_parameter(self) -> None:
        with self.assertRaises(ValueError):
            self.db.get("interstitial-flow-velocity-range").to_scientific_parameter("x")

    def test_queries(self) -> None:
        hormones = self.db.effects(tag="hormone")
        self.assertTrue(all(r.kind == "effect" for r in hormones))
        self.assertIn(
            "glucocorticoid-sev-release-neuro2a",
            {r.id for r in self.db.effects(stimulus="cortisol")},
        )
        clearance = self.db.effects(outcome=EffectOutcome.EV_CLEARANCE)
        self.assertEqual([r.id for r in clearance], ["macrophage-depletion-clearance"])
        self.assertEqual(len(self.db.quantities("circulation_half_life")), 2)

    def test_quantity_value_validation_and_interval(self) -> None:
        self.assertEqual(QuantityValue(central=10.0, sd=2.0).interval(), (6.0, 14.0))
        self.assertEqual(QuantityValue(low=1.0, high=3.0).interval(), (1.0, 3.0))
        with self.assertRaises(ValueError):
            QuantityValue(low=3.0, high=1.0)
        with self.assertRaises(ValueError):
            QuantityValue(sd=1.0, low=0.0, high=1.0)

    def test_registry_rejects_unknown_source_and_unflagged_preprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            shutil.copy(DATA / "sources.json", target / "sources.json")
            records = json.loads((DATA / "records.json").read_text())
            records["records"][0]["source"] = "missing"
            (target / "records.json").write_text(json.dumps(records))
            with self.assertRaises(ValueError):
                load_evidence(target)
            records = json.loads((DATA / "records.json").read_text())
            for item in records["records"]:
                if item["source"] == "glucocorticoid-nsmase2-2025":
                    item["limitations"] = ["Cell-line context."]
            (target / "records.json").write_text(json.dumps(records))
            with self.assertRaisesRegex(ValueError, "preprint"):
                load_evidence(target)

    def test_sqlite_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = export_sqlite(self.db, Path(directory) / "evidence.db")
            connection = sqlite3.connect(path)
            try:
                count = connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]
                joined = connection.execute(
                    "SELECT r.value_central, s.doi FROM records r JOIN sources s "
                    "ON r.source_id = s.id WHERE r.id = 'plasma-sev-half-life-mouse'"
                ).fetchone()
            finally:
                connection.close()
        self.assertEqual(count, len(self.db.records))
        self.assertEqual(joined, (7.0, "10.1080/20013078.2019.1696517"))


class EvidenceSynthesisTests(unittest.TestCase):
    def test_synthesis_numbers(self) -> None:
        result = synthesize()
        self.assertAlmostEqual(result.free_diffusion_micron2_per_min[1], 394.3, delta=0.5)
        self.assertAlmostEqual(result.length_scale_micron[0], 16.8, delta=0.2)
        self.assertAlmostEqual(
            result.blood_clearance_rate_per_min[1], math.log(2) / 2.0, places=9
        )
        lo, hi = result.required_loss_vs_blood_clearance
        self.assertGreater(lo, 1.0)
        self.assertLess(result.peclet_at_free_diffusion[0], 1.0)
        self.assertGreater(result.peclet_at_free_diffusion[1], 1.0)
        self.assertEqual(len(result.summary_lines()), 5)


if __name__ == "__main__":
    unittest.main()
