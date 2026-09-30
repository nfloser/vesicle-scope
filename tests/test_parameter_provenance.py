import math
import unittest
from dataclasses import FrozenInstanceError

from vesiclescope.domain.parameters import (
    EvidenceCategory,
    EvidenceSource,
    ParameterContext,
    ScientificParameter,
)


class ScientificParameterTests(unittest.TestCase):
    def test_accepts_literature_parameter_with_source_and_context(self) -> None:
        parameter = ScientificParameter(
            identifier="ev.transport.diffusivity",
            scientific_name="effective EV diffusivity",
            value=1.25,
            unit="um^2/min",
            evidence=EvidenceCategory.LITERATURE_ESTIMATE,
            source=EvidenceSource(
                identifier="doi:10.0000/example",
                location="Table 2",
            ),
            context=ParameterContext(
                species="human",
                cell_line="example-cell-line",
                ev_preparation="synthetic test context",
                measurement_method="example method",
            ),
            assumptions=("Converted to canonical time units.",),
            limitations=("Fixture only; not a VesicleScope biological default.",),
        )

        self.assertEqual(parameter.identifier, "ev.transport.diffusivity")
        self.assertEqual(parameter.evidence, EvidenceCategory.LITERATURE_ESTIMATE)
        self.assertEqual(parameter.source.identifier, "doi:10.0000/example")

    def test_source_is_required_for_evidence_backed_categories(self) -> None:
        requiring_source = (
            EvidenceCategory.MEASURED_TARGET_CONTEXT,
            EvidenceCategory.MEASURED_RELATED_CONTEXT,
            EvidenceCategory.LITERATURE_ESTIMATE,
            EvidenceCategory.FITTED,
            EvidenceCategory.INFERRED,
        )

        for category in requiring_source:
            with self.subTest(category=category):
                with self.assertRaises(ValueError):
                    ScientificParameter(
                        identifier="parameter",
                        scientific_name="parameter",
                        value=1.0,
                        unit="1/min",
                        evidence=category,
                    )

    def test_assumed_and_synthetic_values_can_be_source_free(self) -> None:
        for category in (
            EvidenceCategory.ASSUMED,
            EvidenceCategory.SYNTHETIC_BENCHMARK,
        ):
            with self.subTest(category=category):
                parameter = ScientificParameter(
                    identifier="benchmark.value",
                    scientific_name="benchmark value",
                    value=1.0,
                    unit="dimensionless",
                    evidence=category,
                )
                self.assertIsNone(parameter.source)

    def test_rejects_blank_identity_and_unit_fields(self) -> None:
        for field_name in ("identifier", "scientific_name", "unit"):
            with self.subTest(field_name=field_name):
                kwargs = {
                    "identifier": "parameter",
                    "scientific_name": "parameter",
                    "value": 1.0,
                    "unit": "dimensionless",
                    "evidence": EvidenceCategory.SYNTHETIC_BENCHMARK,
                }
                kwargs[field_name] = "   "

                with self.assertRaises(ValueError):
                    ScientificParameter(**kwargs)

    def test_rejects_non_finite_values(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    ScientificParameter(
                        identifier="benchmark.value",
                        scientific_name="benchmark value",
                        value=value,
                        unit="dimensionless",
                        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
                    )

    def test_evidence_source_identifier_cannot_be_blank(self) -> None:
        with self.assertRaises(ValueError):
            EvidenceSource(identifier=" ")

    def test_parameter_is_immutable_after_validation(self) -> None:
        parameter = ScientificParameter(
            identifier="benchmark.value",
            scientific_name="benchmark value",
            value=1.0,
            unit="dimensionless",
            evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        )

        with self.assertRaises(FrozenInstanceError):
            parameter.value = 2.0


if __name__ == "__main__":
    unittest.main()
