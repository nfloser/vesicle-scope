from dataclasses import replace
import math
import unittest

from vesiclescope.analysis import summarize_run_ensemble
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMNumerics,
    BioFVMRunResult,
    RecipientUptakeSample,
    RecipientUptakeSeries,
    SpatialFieldSnapshot2D,
    TransportSample,
)
from vesiclescope.run_bundles import SimulationRunBundle
from vesiclescope.scenarios import diffusion_uptake_factor_conditions


def bundle(index: int, *, extracellular: float, internalized: float) -> SimulationRunBundle:
    base = diffusion_uptake_factor_conditions()[4].experiment
    experiment = replace(base, experiment_id=f"ensemble.member.{index}")
    grid = BioFVMGrid2D(
        nx=21,
        ny=21,
        grid_spacing_micron=10.0,
        slice_thickness_micron=25.0,
    )
    voxel_volume = 10.0 * 10.0 * 25.0
    concentration = extracellular / (grid.voxel_count * voxel_volume)
    per_recipient = internalized / len(experiment.uptake_sinks)
    result = BioFVMRunResult(
        experiment_id=experiment.experiment_id,
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
        samples=(
            TransportSample(
                time_min=20.0,
                mean_concentration=concentration,
                min_concentration=concentration,
                max_concentration=concentration,
                integrated_field_quantity=extracellular,
                internalized_field_quantity=internalized,
            ),
        ),
        field_snapshots=(
            SpatialFieldSnapshot2D(
                time_min=20.0,
                values=(concentration,) * grid.voxel_count,
            ),
        ),
        recipient_uptake_series=tuple(
            RecipientUptakeSeries(
                identifier=sink.identifier,
                x_micron=sink.x_micron,
                y_micron=sink.y_micron,
                effective_volume_micron3=sink.effective_volume_micron3,
                uptake_rate_per_min=sink.uptake_rate.value,
                samples=(
                    RecipientUptakeSample(
                        time_min=20.0,
                        internalized_field_quantity=per_recipient,
                    ),
                ),
            )
            for sink in experiment.uptake_sinks
        ),
    )
    return SimulationRunBundle(
        vesiclescope_revision="a" * 40,
        experiment=experiment,
        numerics=BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
        result=result,
    )


class RunEnsembleTests(unittest.TestCase):
    def test_summarizes_explicit_member_order_and_endpoints(self) -> None:
        bundles = tuple(
            bundle(i, extracellular=float(i), internalized=float(10 - i))
            for i in range(1, 6)
        )

        summary = summarize_run_ensemble(bundles)

        self.assertEqual(
            summary.member_experiment_ids,
            tuple(f"ensemble.member.{i}" for i in range(1, 6)),
        )
        self.assertEqual(summary.quantity_unit, "particle_equivalent")
        self.assertEqual(summary.final_extracellular.member_count, 5)
        self.assertEqual(summary.final_extracellular.minimum, 1.0)
        self.assertEqual(summary.final_extracellular.maximum, 5.0)
        self.assertEqual(summary.final_extracellular.mean, 3.0)
        self.assertEqual(summary.final_extracellular.median, 3.0)
        self.assertIsNone(summary.final_extracellular.empirical_percentile_interval_95)
        self.assertEqual(summary.final_internalized.mean, 7.0)

    def test_reports_documented_empirical_interval_only_for_large_enough_ensemble(self) -> None:
        bundles = tuple(
            bundle(i, extracellular=float(i), internalized=float(i))
            for i in range(40)
        )
        summary = summarize_run_ensemble(bundles)

        self.assertEqual(
            summary.final_extracellular.empirical_percentile_interval_95,
            (0.9750000000000001, 38.025),
        )

    def test_single_member_is_valid_but_has_no_interval(self) -> None:
        summary = summarize_run_ensemble(
            (bundle(1, extracellular=4.0, internalized=2.0),)
        )
        self.assertEqual(summary.final_extracellular.mean, 4.0)
        self.assertIsNone(summary.final_extracellular.empirical_percentile_interval_95)

    def test_rejects_empty_ensemble(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            summarize_run_ensemble(())

    def test_rejects_duplicate_experiment_ids(self) -> None:
        item = bundle(1, extracellular=4.0, internalized=2.0)
        with self.assertRaisesRegex(ValueError, "unique"):
            summarize_run_ensemble((item, item))

    def test_rejects_incompatible_quantity_units(self) -> None:
        left = bundle(1, extracellular=4.0, internalized=2.0)
        right = bundle(2, extracellular=4.0, internalized=2.0)
        right = replace(
            right,
            result=replace(
                right.result,
                integrated_quantity_unit="other",
                internalized_quantity_unit="other",
            ),
        )
        with self.assertRaisesRegex(ValueError, "incompatible"):
            summarize_run_ensemble((left, right))

    def test_rejects_non_finite_endpoint_defensively(self) -> None:
        item = bundle(1, extracellular=4.0, internalized=2.0)
        # Valid persisted bundles cannot contain this value. Bypass the frozen
        # sample only here to exercise the analysis layer's defensive boundary.
        object.__setattr__(
            item.result.samples[-1],
            "integrated_field_quantity",
            math.inf,
        )
        with self.assertRaisesRegex(ValueError, "finite"):
            summarize_run_ensemble((item,))


if __name__ == "__main__":
    unittest.main()
