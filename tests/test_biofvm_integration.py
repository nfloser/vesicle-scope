import os
import unittest
from pathlib import Path

from vesiclescope.domain import (
    BoundaryCondition,
    EvidenceCategory,
    PointReleaseSource,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines.biofvm import BioFVMNumerics, run_transport
from vesiclescope.validation import first_order_decay


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")


def synthetic_parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def uniform_experiment(decay_per_min: float) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=f"synthetic.uniform-decay.{decay_per_min:g}",
        domain=RectangularDomain2D(
            width_micron=200.0,
            height_micron=100.0,
            slice_thickness_micron=25.0,
        ),
        duration_min=20.0,
        sample_every_min=5.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=synthetic_parameter(
            "transport.diffusion",
            1000.0,
            "micron^2/min",
        ),
        decay=synthetic_parameter(
            "transport.decay",
            decay_per_min,
            "1/min",
        ),
        initial_concentration=synthetic_parameter(
            "initial.concentration",
            2.0,
            "synthetic_concentration",
        ),
    )


def localized_release_experiment(rate_per_min: float = 120.0) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=f"synthetic.localized-release.{rate_per_min:g}",
        domain=RectangularDomain2D(
            width_micron=200.0,
            height_micron=100.0,
            slice_thickness_micron=25.0,
        ),
        duration_min=20.0,
        sample_every_min=5.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=synthetic_parameter(
            "transport.diffusion",
            1000.0,
            "micron^2/min",
        ),
        decay=synthetic_parameter("transport.decay", 0.0, "1/min"),
        initial_concentration=synthetic_parameter(
            "initial.concentration",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            PointReleaseSource(
                identifier="source.center",
                x_micron=100.0,
                y_micron=50.0,
                release_rate=synthetic_parameter(
                    "source.release",
                    rate_per_min,
                    "particle_equivalent/min",
                ),
            ),
        ),
    )


@unittest.skipUnless(RUNNER, "native BioFVM runner is not built for this test job")
class BioFVMTransportIntegrationTests(unittest.TestCase):
    @property
    def runner(self) -> Path:
        assert RUNNER is not None
        return Path(RUNNER)

    def assert_uniform(self, result, tolerance: float = 1e-12) -> None:
        for sample in result.samples:
            spread = sample.max_concentration - sample.min_concentration
            scale = max(1.0, abs(sample.mean_concentration))
            self.assertLessEqual(spread, tolerance * scale)

    def relative_final_error(self, result, rate: float) -> float:
        sample = result.samples[-1]
        expected = first_order_decay(2.0, rate, sample.time_min)
        return abs(sample.mean_concentration - expected) / expected

    def test_zero_decay_preserves_uniform_field_and_total_level(self) -> None:
        result = run_transport(
            uniform_experiment(0.0),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            self.runner,
        )

        self.assert_uniform(result)
        for sample in result.samples:
            self.assertAlmostEqual(sample.mean_concentration, 2.0, places=12)

    def test_decay_matches_closed_form_at_every_requested_sample(self) -> None:
        rate = 0.05
        result = run_transport(
            uniform_experiment(rate),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            self.runner,
        )

        self.assert_uniform(result)
        for sample in result.samples:
            expected = first_order_decay(2.0, rate, sample.time_min)
            relative_error = abs(sample.mean_concentration - expected) / expected
            self.assertLessEqual(relative_error, 5e-3)

    def test_timestep_refinement_reduces_decay_error(self) -> None:
        rate = 0.05
        experiment = uniform_experiment(rate)

        coarse = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.2),
            self.runner,
        )
        fine = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            self.runner,
        )

        coarse_error = self.relative_final_error(coarse, rate)
        fine_error = self.relative_final_error(fine, rate)

        self.assertLessEqual(coarse_error, 5e-3)
        self.assertLess(fine_error, coarse_error)

    def test_localized_release_matches_amount_per_time_mass_balance(self) -> None:
        rate = 120.0
        result = run_transport(
            localized_release_experiment(rate),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            self.runner,
        )

        for sample in result.samples:
            expected_amount = rate * sample.time_min
            self.assertAlmostEqual(
                sample.integrated_field_quantity,
                expected_amount,
                delta=max(1e-9, expected_amount * 1e-10),
            )

    def test_localized_release_amount_is_resolution_invariant(self) -> None:
        experiment = localized_release_experiment()

        coarse = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            self.runner,
        )
        fine = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            self.runner,
        )

        self.assertAlmostEqual(
            coarse.samples[-1].integrated_field_quantity,
            fine.samples[-1].integrated_field_quantity,
            delta=1e-8,
        )
        self.assertAlmostEqual(
            coarse.samples[-1].integrated_field_quantity,
            120.0 * experiment.duration_min,
            delta=1e-8,
        )

    def test_uniform_solution_is_stable_across_spatial_resolution(self) -> None:
        rate = 0.05
        experiment = uniform_experiment(rate)

        coarse = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            self.runner,
        )
        fine = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            self.runner,
        )

        self.assert_uniform(coarse)
        self.assert_uniform(fine)
        self.assertAlmostEqual(
            coarse.samples[-1].mean_concentration,
            fine.samples[-1].mean_concentration,
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
