import math
import unittest
from dataclasses import FrozenInstanceError, fields

from vesiclescope.domain import ScientificParameter
from vesiclescope.validation import (
    RawDataAvailability,
    colombo_2025_tumour_distance_target,
)


class Colombo2025TumourDistanceTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target = colombo_2025_tumour_distance_target()

    def test_pins_publication_and_external_analysis_code_exactly(self) -> None:
        self.assertEqual(
            self.target.source.identifier,
            "doi:10.1002/jev2.70169",
        )
        self.assertEqual(self.target.pmid, "41167986")
        self.assertEqual(
            self.target.pipeline.repository,
            "CocucciLab/spatial-limits-of-extracellular-vesicles",
        )
        self.assertEqual(
            self.target.pipeline.commit,
            "ed9e28173929c9f896d16658781d7a4b9cc2297c",
        )
        self.assertEqual(
            self.target.pipeline.path,
            "in vivo/distTraAnalysis.py",
        )
        self.assertEqual(
            self.target.pipeline.file_sha,
            "16744cd7d0eb0271ce5a8c3949b84e7cb86d8933",
        )
        self.assertEqual(self.target.pipeline.license, "MIT")

    def test_records_experimental_context_and_boundary_distance_observable(self) -> None:
        context = self.target.context

        self.assertIn("HeLa", context.cell_line)
        self.assertIn("mouse", context.species)
        self.assertIn("tumour", context.tissue.lower())
        self.assertIn("confocal", context.measurement_method.lower())
        self.assertEqual(
            self.target.distance_reference,
            "nearest donor-cell boundary",
        )
        self.assertIn("CD9-Halo", self.target.observable)

    def test_records_paper_and_public_code_binning_without_hiding_discrepancy(self) -> None:
        for value in (
            self.target.pixel_size_micron,
            self.target.published_zone_width_micron,
            self.target.public_code_bin_width_micron,
        ):
            self.assertTrue(math.isfinite(value))
            self.assertGreater(value, 0.0)

        self.assertEqual(self.target.pixel_size_micron, 0.2)
        self.assertEqual(self.target.published_zone_pixels, 50)
        self.assertEqual(self.target.public_code_bin_pixels, 25)
        self.assertEqual(self.target.published_zone_width_micron, 10.0)
        self.assertEqual(self.target.public_code_bin_width_micron, 5.0)
        self.assertNotEqual(
            self.target.published_zone_width_micron,
            self.target.public_code_bin_width_micron,
        )

    def test_fit_derived_landmarks_are_ordered_and_explicitly_not_raw_measurements(self) -> None:
        landmarks = self.target.fit_derived_retention_landmarks

        self.assertEqual(
            tuple((item.distance_micron, item.cumulative_fraction) for item in landmarks),
            ((17.0, 0.5), (40.0, 0.8)),
        )
        self.assertTrue(
            all(item.is_fit_derived for item in landmarks)
        )
        for previous, current in zip(landmarks, landmarks[1:]):
            self.assertGreater(current.distance_micron, previous.distance_micron)
            self.assertGreater(current.cumulative_fraction, previous.cumulative_fraction)

        self.assertIn(
            "less than 5% beyond 100 micron",
            self.target.additional_fit_summary,
        )

    def test_raw_data_is_on_request_and_target_is_not_quantitatively_ready(self) -> None:
        self.assertEqual(
            self.target.raw_data_availability,
            RawDataAvailability.ON_REQUEST,
        )
        self.assertFalse(self.target.quantitatively_ready)
        self.assertEqual(len(self.target.comparison_blockers), 4)

        blockers = " ".join(self.target.comparison_blockers).lower()
        self.assertIn("raw", blockers)
        self.assertIn("synthetic", blockers)
        self.assertIn("thresholded", blockers)
        self.assertIn("bin", blockers)
        self.assertIn("calibrated", blockers)

    def test_target_is_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.target.pixel_size_micron = 1.0

        with self.assertRaises(FrozenInstanceError):
            self.target.pipeline.commit = "different"

    def test_validation_summary_does_not_create_model_parameters(self) -> None:
        for field in fields(self.target):
            value = getattr(self.target, field.name)
            self.assertNotIsInstance(value, ScientificParameter)

        self.assertFalse(
            any(
                isinstance(value, ScientificParameter)
                for value in self.target.fit_derived_retention_landmarks
            )
        )


if __name__ == "__main__":
    unittest.main()
