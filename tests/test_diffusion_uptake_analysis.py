from dataclasses import replace
import unittest

from vesiclescope.analysis import analyze_diffusion_uptake_condition
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMRunResult,
    TransportSample,
)
from vesiclescope.scenarios import (
    DiffusionUptakeCondition,
    diffusion_uptake_factor_conditions,
)


def normalized_result(
    condition: DiffusionUptakeCondition,
    *,
    extracellular: float = 1800.0,
    internalized: float = 600.0,
    experiment_id: str | None = None,
) -> BioFVMRunResult:
    experiment = condition.experiment
    concentration = extracellular / experiment.domain.volume_micron3
    return BioFVMRunResult(
        experiment_id=experiment_id or experiment.experiment_id,
        concentration_unit="particle_equivalent/micron^3",
        integrated_quantity_unit="particle_equivalent",
        internalized_quantity_unit="particle_equivalent",
        engine=BioFVMEngineMetadata(
            engine="BioFVM",
            physicell_release="1.14.2",
            physicell_commit="dbd3499250141b27600e91e501c54c46f68f2763",
            biofvm_version="1.1.7",
        ),
        grid=BioFVMGrid2D(
            nx=21,
            ny=21,
            grid_spacing_micron=10.0,
            slice_thickness_micron=25.0,
        ),
        samples=(
            TransportSample(
                time_min=experiment.duration_min,
                mean_concentration=concentration,
                min_concentration=0.0,
                max_concentration=max(concentration, concentration * 2.0),
                integrated_field_quantity=extracellular,
                internalized_field_quantity=internalized,
            ),
        ),
        field_snapshots=(),
        recipient_uptake_series=(),
    )


class DiffusionUptakeAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.condition = diffusion_uptake_factor_conditions()[4]

    def test_computes_fraction_of_declared_released_quantity(self) -> None:
        summary = analyze_diffusion_uptake_condition(
            self.condition,
            normalized_result(self.condition),
        )

        self.assertEqual(summary.diffusion_factor, 1.0)
        self.assertEqual(summary.uptake_factor, 1.0)
        self.assertEqual(summary.diffusion_value, 100.0)
        self.assertEqual(summary.diffusion_unit, "micron^2/min")
        self.assertEqual(summary.uptake_value, 0.5)
        self.assertEqual(summary.uptake_unit, "1/min")
        self.assertEqual(summary.total_released_quantity, 2400.0)
        self.assertEqual(summary.final_extracellular_quantity, 1800.0)
        self.assertEqual(summary.final_internalized_quantity, 600.0)
        self.assertAlmostEqual(summary.extracellular_fraction, 0.75)
        self.assertAlmostEqual(summary.internalized_fraction, 0.25)
        self.assertEqual(summary.quantity_unit, "particle_equivalent")

    def test_rejects_mass_accounting_that_does_not_close(self) -> None:
        with self.assertRaisesRegex(ValueError, "conservation"):
            analyze_diffusion_uptake_condition(
                self.condition,
                normalized_result(
                    self.condition,
                    extracellular=1700.0,
                    internalized=600.0,
                ),
            )

    def test_rejects_result_for_another_experiment(self) -> None:
        with self.assertRaisesRegex(ValueError, "experiment_id"):
            analyze_diffusion_uptake_condition(
                self.condition,
                normalized_result(self.condition, experiment_id="different"),
            )

    def test_rejects_nonzero_decay_for_this_conservation_endpoint(self) -> None:
        experiment = replace(
            self.condition.experiment,
            decay=replace(self.condition.experiment.decay, value=0.1),
        )
        altered = DiffusionUptakeCondition(
            diffusion_factor=self.condition.diffusion_factor,
            uptake_factor=self.condition.uptake_factor,
            experiment=experiment,
        )
        with self.assertRaisesRegex(ValueError, "zero decay"):
            analyze_diffusion_uptake_condition(
                altered,
                normalized_result(altered),
            )

    def test_rejects_nonzero_initial_quantity_for_this_conservation_endpoint(self) -> None:
        experiment = replace(
            self.condition.experiment,
            initial_concentration=replace(
                self.condition.experiment.initial_concentration,
                value=0.001,
            ),
        )
        altered = DiffusionUptakeCondition(
            diffusion_factor=self.condition.diffusion_factor,
            uptake_factor=self.condition.uptake_factor,
            experiment=experiment,
        )
        with self.assertRaisesRegex(ValueError, "zero initial"):
            analyze_diffusion_uptake_condition(
                altered,
                normalized_result(altered),
            )


if __name__ == "__main__":
    unittest.main()
