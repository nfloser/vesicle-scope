import unittest

from vesiclescope.analysis.measurement_comparison import (
    MeasurementPredictionTarget,
    PredictionObservable,
    compare_measurements_to_prediction,
)
from vesiclescope.domain import (
    AssayObservation,
    BloodEVPreanalytics,
    LongitudinalEVDataset,
    MeasurementKind,
    MeasurementTimepoint,
    SpecimenKind,
)
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMRunResult,
    SpatialFieldSnapshot2D,
    TransportSample,
)


def observation(identifier: str, value: float, unit: str) -> AssayObservation:
    return AssayObservation(
        identifier=identifier,
        scientific_name="EV-associated events",
        kind=MeasurementKind.EV_ASSOCIATED_EVENT_CONCENTRATION,
        value=value,
        unit=unit,
        method="synthetic assay",
        detection_semantics="Synthetic test observation with declared assay semantics.",
    )


def dataset(unit: str = "particle_equivalent/micron^3") -> LongitudinalEVDataset:
    sample = BloodEVPreanalytics(
        sample_id="sample-1",
        specimen=SpecimenKind.PLASMA,
        anticoagulant="EDTA",
        collection_to_processing_min=20.0,
        limitations=("Synthetic measurement comparison test.",),
    )
    return LongitudinalEVDataset(
        dataset_id="longitudinal-test",
        samples=(sample,),
        timepoints=(
            MeasurementTimepoint(
                sample_id="sample-1",
                condition_id="stimulated",
                time_min=0.0,
                observations=(observation("ev-events", 0.5, unit),),
            ),
            MeasurementTimepoint(
                sample_id="sample-1",
                condition_id="stimulated",
                time_min=2.0,
                observations=(observation("ev-events", 1.5, unit),),
            ),
            MeasurementTimepoint(
                sample_id="sample-1",
                condition_id="stimulated",
                time_min=3.0,
                observations=(observation("ev-events", 2.0, unit),),
            ),
        ),
        limitations=("Synthetic adapter test; no biological calibration.",),
    )


def result() -> BioFVMRunResult:
    grid = BioFVMGrid2D(1, 1, 10.0, 10.0)
    values = ((1.0,), (2.0,), (3.0,))
    times = (0.0, 2.0, 4.0)
    return BioFVMRunResult(
        experiment_id="population-a.run",
        concentration_unit="particle_equivalent/micron^3",
        integrated_quantity_unit="particle_equivalent",
        internalized_quantity_unit="particle_equivalent",
        engine=BioFVMEngineMetadata(
            engine="BioFVM",
            physicell_release="1.14.2",
            physicell_commit="dbd3499250141b27600e91e501c54c46f68f2763",
            biofvm_version="1.1.7",
        ),
        grid=grid,
        samples=tuple(
            TransportSample(
                time_min=time,
                mean_concentration=field[0],
                min_concentration=field[0],
                max_concentration=field[0],
                integrated_field_quantity=field[0] * 1000.0,
                internalized_field_quantity=0.0,
            )
            for time, field in zip(times, values)
        ),
        field_snapshots=tuple(
            SpatialFieldSnapshot2D(time_min=time, values=field)
            for time, field in zip(times, values)
        ),
        recipient_uptake_series=(),
    )


class MeasurementPredictionComparisonTests(unittest.TestCase):
    def test_matches_only_stored_prediction_times_without_interpolation(self) -> None:
        matches = compare_measurements_to_prediction(
            dataset(),
            "stimulated",
            result(),
            (
                MeasurementPredictionTarget(
                    observation_identifier="ev-events",
                    observable=PredictionObservable.MEAN_CONCENTRATION,
                ),
            ),
        )

        self.assertEqual(tuple(item.time_min for item in matches), (0.0, 2.0, 3.0))
        self.assertEqual(matches[0].predicted_value, 1.0)
        self.assertEqual(matches[1].predicted_value, 2.0)
        self.assertIsNone(matches[2].predicted_value)
        self.assertFalse(matches[2].exact_time_match)
        self.assertIn("no stored prediction", matches[2].reason)

    def test_computes_residual_only_when_units_are_identical(self) -> None:
        compatible = compare_measurements_to_prediction(
            dataset(),
            "stimulated",
            result(),
            (
                MeasurementPredictionTarget(
                    observation_identifier="ev-events",
                    observable=PredictionObservable.MEAN_CONCENTRATION,
                ),
            ),
        )[1]
        incompatible = compare_measurements_to_prediction(
            dataset("particles/mL"),
            "stimulated",
            result(),
            (
                MeasurementPredictionTarget(
                    observation_identifier="ev-events",
                    observable=PredictionObservable.MEAN_CONCENTRATION,
                ),
            ),
        )[1]

        self.assertTrue(compatible.unit_compatible)
        self.assertEqual(compatible.residual_prediction_minus_measurement, 0.5)
        self.assertFalse(incompatible.unit_compatible)
        self.assertIsNone(incompatible.residual_prediction_minus_measurement)
        self.assertEqual(incompatible.predicted_value, 2.0)

    def test_does_not_match_other_conditions(self) -> None:
        self.assertEqual(
            compare_measurements_to_prediction(
                dataset(),
                "control",
                result(),
                (
                    MeasurementPredictionTarget(
                        observation_identifier="ev-events",
                        observable=PredictionObservable.MEAN_CONCENTRATION,
                    ),
                ),
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
