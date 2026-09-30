from dataclasses import replace
import unittest

from vesiclescope.analysis import analyze_recipient_population
from vesiclescope.engines import (
    BioFVMEngineMetadata,
    BioFVMGrid2D,
    BioFVMRunResult,
    RecipientUptakeSample,
    RecipientUptakeSeries,
    SpatialFieldSnapshot2D,
    TransportSample,
)
from vesiclescope.figures import prepare_recipient_count_figure_data
from vesiclescope.scenarios import recipient_count_sweep_experiment


def synthetic_result(recipient_count: int, total_uptake: float) -> BioFVMRunResult:
    experiment = recipient_count_sweep_experiment(recipient_count)
    per_recipient = total_uptake / recipient_count

    recipient_series = tuple(
        RecipientUptakeSeries(
            identifier=sink.identifier,
            x_micron=sink.x_micron,
            y_micron=sink.y_micron,
            effective_volume_micron3=sink.effective_volume_micron3,
            uptake_rate_per_min=sink.uptake_rate.value,
            samples=(
                RecipientUptakeSample(0.0, 0.0),
                RecipientUptakeSample(experiment.duration_min, per_recipient),
            ),
        )
        for sink in experiment.uptake_sinks
    )

    nx = 21
    ny = 21
    final_field = tuple(
        0.001 + (index / 1_000_000.0)
        for index in range(nx * ny)
    )
    initial_field = tuple(0.0 for _ in range(nx * ny))

    return BioFVMRunResult(
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
        grid=BioFVMGrid2D(
            nx=nx,
            ny=ny,
            grid_spacing_micron=10.0,
            slice_thickness_micron=25.0,
        ),
        samples=(
            TransportSample(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
            TransportSample(
                experiment.duration_min,
                sum(final_field) / len(final_field),
                min(final_field),
                max(final_field),
                1.0,
                total_uptake,
            ),
        ),
        field_snapshots=(
            SpatialFieldSnapshot2D(0.0, initial_field),
            SpatialFieldSnapshot2D(experiment.duration_min, final_field),
        ),
        recipient_uptake_series=recipient_series,
    )


class RecipientCountFigureDataTests(unittest.TestCase):
    def test_uses_normalized_fields_and_analysis_summaries(self) -> None:
        totals = (11.0, 23.0, 47.0)
        experiments = tuple(
            recipient_count_sweep_experiment(count)
            for count in (2, 4, 8)
        )
        results = tuple(
            synthetic_result(count, total)
            for count, total in zip((2, 4, 8), totals)
        )
        summaries = tuple(
            analyze_recipient_population(
                experiment,
                result,
                time_min=experiment.duration_min,
            )
            for experiment, result in zip(experiments, results)
        )

        data = prepare_recipient_count_figure_data(
            experiments,
            results,
            summaries,
        )

        self.assertEqual(data.recipient_counts, (2, 4, 8))
        self.assertEqual(data.total_internalized_quantities, totals)
        self.assertEqual(
            data.planar_densities,
            tuple(summary.planar_density for summary in summaries),
        )
        self.assertEqual(data.planar_density_unit, "recipient/mm^2")
        self.assertEqual(data.quantity_unit, "particle_equivalent")
        self.assertEqual(data.concentration_unit, "particle_equivalent/micron^3")
        self.assertEqual(len(data.heatmap_rows), 21)
        self.assertTrue(all(len(row) == 21 for row in data.heatmap_rows))
        self.assertEqual(
            data.heatmap_rows[0],
            results[-1].field_snapshots[-1].values[:21],
        )

    def test_rejects_mismatched_scenario_result_identity(self) -> None:
        experiments = tuple(
            recipient_count_sweep_experiment(count)
            for count in (2, 4, 8)
        )
        results = tuple(
            synthetic_result(count, float(count))
            for count in (2, 4, 8)
        )
        summaries = tuple(
            analyze_recipient_population(
                experiment,
                result,
                time_min=experiment.duration_min,
            )
            for experiment, result in zip(experiments, results)
        )
        bad_results = (
            replace(results[0], experiment_id="wrong"),
            results[1],
            results[2],
        )

        with self.assertRaises(ValueError):
            prepare_recipient_count_figure_data(
                experiments,
                bad_results,
                summaries,
            )

    def test_rejects_heatmap_grid_that_does_not_match_scenario_geometry(self) -> None:
        experiments = tuple(
            recipient_count_sweep_experiment(count)
            for count in (2, 4, 8)
        )
        results = list(
            synthetic_result(count, float(count))
            for count in (2, 4, 8)
        )
        bad_grid = replace(results[-1].grid, grid_spacing_micron=9.0)
        results[-1] = replace(results[-1], grid=bad_grid)
        summaries = tuple(
            analyze_recipient_population(
                experiment,
                result,
                time_min=experiment.duration_min,
            )
            for experiment, result in zip(experiments, results)
        )

        with self.assertRaises(ValueError):
            prepare_recipient_count_figure_data(
                experiments,
                tuple(results),
                summaries,
            )

    def test_rejects_heatmap_shape_that_does_not_match_grid(self) -> None:
        experiments = tuple(
            recipient_count_sweep_experiment(count)
            for count in (2, 4, 8)
        )
        results = list(
            synthetic_result(count, float(count))
            for count in (2, 4, 8)
        )
        final = results[-1]
        bad_snapshot = replace(
            final.field_snapshots[-1],
            values=final.field_snapshots[-1].values[:-1],
        )
        results[-1] = replace(
            final,
            field_snapshots=(final.field_snapshots[0], bad_snapshot),
        )
        summaries = tuple(
            analyze_recipient_population(
                experiment,
                result,
                time_min=experiment.duration_min,
            )
            for experiment, result in zip(experiments, results)
        )

        with self.assertRaises(ValueError):
            prepare_recipient_count_figure_data(
                experiments,
                tuple(results),
                summaries,
            )


if __name__ == "__main__":
    unittest.main()
