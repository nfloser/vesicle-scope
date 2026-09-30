import math
import os
import unittest
from pathlib import Path

from vesiclescope.domain import (
    BoundaryCondition,
    EvidenceCategory,
    PointReleaseSource,
    PointUptakeSink,
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


def localized_uptake_experiment(
    *,
    uptake_rate_per_min: float = 0.5,
    effective_volume_micron3: float = 1000.0,
) -> TransportExperiment:
    return TransportExperiment(
        experiment_id="synthetic.localized-uptake",
        domain=RectangularDomain2D(
            width_micron=200.0,
            height_micron=100.0,
            slice_thickness_micron=25.0,
        ),
        duration_min=1.0,
        sample_every_min=0.2,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=synthetic_parameter("transport.diffusion", 0.0, "micron^2/min"),
        decay=synthetic_parameter("transport.decay", 0.0, "1/min"),
        initial_concentration=synthetic_parameter(
            "initial.concentration",
            2.0,
            "particle_equivalent/micron^3",
        ),
        uptake_sinks=(
            PointUptakeSink(
                identifier="sink.center",
                x_micron=100.0,
                y_micron=50.0,
                effective_volume_micron3=effective_volume_micron3,
                uptake_rate=synthetic_parameter(
                    "sink.uptake",
                    uptake_rate_per_min,
                    "1/min",
                ),
            ),
        ),
    )


def donor_recipient_experiment(
    recipient_x_micron: float,
) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=f"synthetic.donor-recipient.{recipient_x_micron:g}",
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
            100.0,
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
                identifier="source.donor",
                x_micron=55.0,
                y_micron=55.0,
                release_rate=synthetic_parameter(
                    "source.release",
                    120.0,
                    "particle_equivalent/min",
                ),
            ),
        ),
        uptake_sinks=(
            PointUptakeSink(
                identifier="sink.recipient",
                x_micron=recipient_x_micron,
                y_micron=55.0,
                effective_volume_micron3=1000.0,
                uptake_rate=synthetic_parameter(
                    "sink.uptake",
                    0.5,
                    "1/min",
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
        self.assertEqual(len(result.field_snapshots), len(result.samples))
        for sample, field in zip(result.samples, result.field_snapshots):
            self.assertAlmostEqual(sample.mean_concentration, 2.0, places=12)
            self.assertEqual(field.time_min, sample.time_min)
            self.assertTrue(
                all(
                    math.isclose(value, 2.0, rel_tol=0.0, abs_tol=1e-12)
                    for value in field.values
                )
            )

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

    def test_localized_release_exposes_nonuniform_spatial_field(self) -> None:
        result = run_transport(
            localized_release_experiment(),
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            self.runner,
        )

        final_field = result.field_snapshots[-1]
        self.assertEqual(final_field.time_min, result.samples[-1].time_min)
        self.assertGreater(max(final_field.values), min(final_field.values))

        derived_mean = sum(final_field.values) / len(final_field.values)
        self.assertAlmostEqual(
            derived_mean,
            result.samples[-1].mean_concentration,
            places=12,
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

    def test_combined_release_and_uptake_close_global_amount_balance(self) -> None:
        experiment = donor_recipient_experiment(75.0)
        result = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            self.runner,
        )
        release_rate = experiment.release_sources[0].release_rate.value

        previous_internalized = -1.0
        for sample in result.samples:
            released = release_rate * sample.time_min
            self.assertAlmostEqual(
                sample.integrated_field_quantity
                + sample.internalized_field_quantity,
                released,
                delta=max(1e-8, released * 1e-9),
            )
            self.assertGreaterEqual(sample.internalized_field_quantity, 0.0)
            self.assertGreaterEqual(
                sample.internalized_field_quantity + 1e-12,
                previous_internalized,
            )
            previous_internalized = sample.internalized_field_quantity

    def test_nearer_recipient_internalizes_more_than_farther_recipient(self) -> None:
        numerics = BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1)

        near = run_transport(
            donor_recipient_experiment(75.0),
            numerics,
            self.runner,
        )
        far = run_transport(
            donor_recipient_experiment(135.0),
            numerics,
            self.runner,
        )

        self.assertGreater(
            near.samples[-1].internalized_field_quantity,
            far.samples[-1].internalized_field_quantity,
        )

    def test_combined_run_has_one_spatial_field_per_requested_sample(self) -> None:
        result = run_transport(
            donor_recipient_experiment(75.0),
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            self.runner,
        )

        self.assertEqual(len(result.field_snapshots), len(result.samples))
        self.assertEqual(
            tuple(field.time_min for field in result.field_snapshots),
            tuple(sample.time_min for sample in result.samples),
        )

    def test_combined_donor_recipient_run_is_deterministic(self) -> None:
        experiment = donor_recipient_experiment(75.0)
        numerics = BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1)

        first = run_transport(experiment, numerics, self.runner)
        second = run_transport(experiment, numerics, self.runner)

        self.assertEqual(len(first.samples), len(second.samples))
        for left, right in zip(first.samples, second.samples):
            self.assertAlmostEqual(
                left.integrated_field_quantity,
                right.integrated_field_quantity,
                places=12,
            )
            self.assertAlmostEqual(
                left.internalized_field_quantity,
                right.internalized_field_quantity,
                places=12,
            )

    def test_localized_uptake_conserves_extracellular_plus_internalized_quantity(self) -> None:
        experiment = localized_uptake_experiment()
        result = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            self.runner,
        )
        initial_total = 2.0 * experiment.domain.volume_micron3

        previous_internalized = -1.0
        for sample in result.samples:
            self.assertAlmostEqual(
                sample.integrated_field_quantity
                + sample.internalized_field_quantity,
                initial_total,
                delta=1e-8,
            )
            self.assertGreaterEqual(sample.internalized_field_quantity, 0.0)
            self.assertGreaterEqual(
                sample.internalized_field_quantity + 1e-12,
                previous_internalized,
            )
            previous_internalized = sample.internalized_field_quantity

    def test_zero_diffusion_uptake_matches_biofvm_discrete_update(self) -> None:
        experiment = localized_uptake_experiment()
        dt = 0.1
        grid = 20.0
        result = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=grid, time_step_min=dt),
            self.runner,
        )

        voxel_volume = grid * grid * experiment.domain.slice_thickness_micron
        sink = experiment.uptake_sinks[0]
        alpha = (
            dt
            * sink.effective_volume_micron3
            / voxel_volume
            * sink.uptake_rate.value
        )
        unaffected_volume = experiment.domain.volume_micron3 - voxel_volume
        initial_total = 2.0 * experiment.domain.volume_micron3

        for sample in result.samples:
            steps = round(sample.time_min / dt)
            local_concentration = 2.0 / ((1.0 + alpha) ** steps)
            expected_extracellular = (
                2.0 * unaffected_volume
                + local_concentration * voxel_volume
            )
            expected_internalized = initial_total - expected_extracellular

            self.assertAlmostEqual(
                sample.integrated_field_quantity,
                expected_extracellular,
                delta=1e-8,
            )
            self.assertAlmostEqual(
                sample.internalized_field_quantity,
                expected_internalized,
                delta=1e-8,
            )

    def test_uptake_timestep_refinement_converges_toward_continuous_limit(self) -> None:
        experiment = localized_uptake_experiment()
        grid = 20.0
        voxel_volume = grid * grid * experiment.domain.slice_thickness_micron
        sink = experiment.uptake_sinks[0]
        effective_rate = (
            sink.effective_volume_micron3
            / voxel_volume
            * sink.uptake_rate.value
        )
        unaffected_volume = experiment.domain.volume_micron3 - voxel_volume
        continuous_local = 2.0 * math.exp(-effective_rate * experiment.duration_min)
        continuous_total = 2.0 * unaffected_volume + continuous_local * voxel_volume

        coarse = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=grid, time_step_min=0.2),
            self.runner,
        )
        fine = run_transport(
            experiment,
            BioFVMNumerics(grid_spacing_micron=grid, time_step_min=0.1),
            self.runner,
        )

        coarse_error = abs(
            coarse.samples[-1].integrated_field_quantity - continuous_total
        )
        fine_error = abs(
            fine.samples[-1].integrated_field_quantity - continuous_total
        )
        self.assertLess(fine_error, coarse_error)

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
