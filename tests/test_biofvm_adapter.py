import math
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from vesiclescope.domain import (
    BoundaryCondition,
    EvidenceCategory,
    PointReleaseSource,
    PointUptakeSink,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines.biofvm import (
    BioFVMNumerics,
    BioFVMRunError,
    build_command,
    parse_result,
    pinned_engine_metadata,
    run_transport,
)


def synthetic_parameter(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def point_source(identifier: str = "source.center") -> PointReleaseSource:
    return PointReleaseSource(
        identifier=identifier,
        x_micron=100.0,
        y_micron=50.0,
        release_rate=synthetic_parameter(
            f"{identifier}.release",
            120.0,
            "particle_equivalent/min",
        ),
    )


def point_sink(identifier: str = "sink.center") -> PointUptakeSink:
    return PointUptakeSink(
        identifier=identifier,
        x_micron=100.0,
        y_micron=50.0,
        effective_volume_micron3=1000.0,
        uptake_rate=synthetic_parameter(
            f"{identifier}.uptake",
            0.5,
            "1/min",
        ),
    )


def experiment(
    *,
    release_sources: tuple[PointReleaseSource, ...] = (),
    uptake_sinks: tuple[PointUptakeSink, ...] = (),
    concentration_unit: str = "particle_equivalent/micron^3",
) -> TransportExperiment:
    return TransportExperiment(
        experiment_id="synthetic.uniform-decay",
        domain=RectangularDomain2D(
            width_micron=200.0,
            height_micron=100.0,
            slice_thickness_micron=25.0,
        ),
        duration_min=10.0,
        sample_every_min=2.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=synthetic_parameter("transport.diffusion", 10.0, "micron^2/min"),
        decay=synthetic_parameter("transport.decay", 0.1, "1/min"),
        initial_concentration=synthetic_parameter(
            "initial.concentration",
            2.0,
            concentration_unit,
        ),
        release_sources=release_sources,
        uptake_sinks=uptake_sinks,
    )


GRID_NX = 10
GRID_NY = 5
GRID_SPACING = 20.0
GRID_THICKNESS = 25.0


def result_output(
    samples: tuple[tuple[float, float, float, float, float], ...],
    *,
    physicell_release: str = "1.14.2",
    include_grid: bool = True,
    fields: tuple[tuple[float, ...], ...] | None = None,
) -> str:
    lines = [
        "VESICLESCOPE_BIOFVM_RESULT\t3",
        "engine\tBioFVM",
        f"physicell_release\t{physicell_release}",
        "physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763",
        "biofvm_version\t1.1.7",
    ]
    if include_grid:
        lines.append(
            "grid\t10\t5\t20\t25\tx_fastest_then_y"
        )

    for index, (time, mean, minimum, maximum, internalized) in enumerate(samples):
        lines.append(
            f"sample\t{time}\t{mean}\t{minimum}\t{maximum}\t{internalized}"
        )
        values = (
            fields[index]
            if fields is not None
            else tuple(mean for _ in range(GRID_NX * GRID_NY))
        )
        lines.append(
            "field\t"
            + str(time)
            + "\t"
            + "\t".join(str(value) for value in values)
        )

    return "\n".join(lines) + "\n"


class BioFVMMetadataTests(unittest.TestCase):
    def test_pinned_metadata_matches_reviewed_upstream_release(self) -> None:
        metadata = pinned_engine_metadata()

        self.assertEqual(metadata.engine, "BioFVM")
        self.assertEqual(metadata.physicell_release, "1.14.2")
        self.assertEqual(
            metadata.physicell_commit,
            "dbd3499250141b27600e91e501c54c46f68f2763",
        )
        self.assertEqual(metadata.biofvm_version, "1.1.7")


class BioFVMNumericsTests(unittest.TestCase):
    def test_requires_positive_finite_grid_and_timestep(self) -> None:
        for grid, dt in (
            (0.0, 0.1),
            (-1.0, 0.1),
            (math.inf, 0.1),
            (20.0, 0.0),
            (20.0, -0.1),
            (20.0, math.nan),
        ):
            with self.subTest(grid=grid, dt=dt):
                with self.assertRaises(ValueError):
                    BioFVMNumerics(grid_spacing_micron=grid, time_step_min=dt)

    def test_requires_grid_and_time_steps_to_tile_experiment(self) -> None:
        exp = experiment()

        with self.assertRaises(ValueError):
            build_command(
                exp,
                BioFVMNumerics(grid_spacing_micron=30.0, time_step_min=0.1),
                Path("runner"),
            )

        with self.assertRaises(ValueError):
            build_command(
                exp,
                BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.3),
                Path("runner"),
            )


class BioFVMCommandTests(unittest.TestCase):
    def test_maps_transport_contract_without_unit_conversion(self) -> None:
        command = build_command(
            experiment(),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("build/native/biofvm_transport_runner"),
        )

        self.assertEqual(command[0], "build/native/biofvm_transport_runner")
        self.assertIn("--boundary", command)
        self.assertEqual(
            command[command.index("--slice-thickness-micron") + 1],
            "25",
        )
        self.assertEqual(command[command.index("--boundary") + 1], "no_flux")
        self.assertEqual(
            command[command.index("--diffusion-micron2-per-min") + 1],
            "10",
        )
        self.assertEqual(
            command[command.index("--decay-per-min") + 1],
            "0.1",
        )
        self.assertEqual(
            command[command.index("--initial-concentration") + 1],
            "2",
        )
        self.assertEqual(
            command[command.index("--concentration-unit") + 1],
            "particle_equivalent/micron^3",
        )
        self.assertEqual(
            command[command.index("--grid-spacing-micron") + 1],
            "20",
        )
        self.assertEqual(command[command.index("--time-step-min") + 1], "0.1")


    def test_grid_refinement_does_not_change_physical_slice_thickness(self) -> None:
        exp = experiment()

        coarse = build_command(
            exp,
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("runner"),
        )
        fine = build_command(
            exp,
            BioFVMNumerics(grid_spacing_micron=10.0, time_step_min=0.1),
            Path("runner"),
        )

        coarse_thickness = coarse[coarse.index("--slice-thickness-micron") + 1]
        fine_thickness = fine[fine.index("--slice-thickness-micron") + 1]
        self.assertEqual(coarse_thickness, "25")
        self.assertEqual(fine_thickness, "25")


    def test_maps_one_localized_release_source(self) -> None:
        command = build_command(
            experiment(release_sources=(point_source(),)),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("runner"),
        )

        self.assertEqual(
            command[command.index("--source-x-micron") + 1],
            "100",
        )
        self.assertEqual(
            command[command.index("--source-y-micron") + 1],
            "50",
        )
        self.assertEqual(
            command[
                command.index("--source-rate-particle-equivalent-per-min") + 1
            ],
            "120",
        )

    def test_rejects_multiple_sources_until_native_contract_supports_them(self) -> None:
        with self.assertRaises(ValueError):
            build_command(
                experiment(
                    release_sources=(
                        point_source("source.one"),
                        point_source("source.two"),
                    )
                ),
                BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
                Path("runner"),
            )

    def test_source_requires_particle_equivalent_concentration_semantics(self) -> None:
        with self.assertRaises(ValueError):
            build_command(
                experiment(
                    release_sources=(point_source(),),
                    concentration_unit="synthetic_concentration",
                ),
                BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
                Path("runner"),
            )


    def test_maps_one_explicit_volume_uptake_sink(self) -> None:
        command = build_command(
            experiment(uptake_sinks=(point_sink(),)),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("runner"),
        )

        self.assertEqual(
            command[command.index("--uptake-x-micron") + 1],
            "100",
        )
        self.assertEqual(
            command[command.index("--uptake-y-micron") + 1],
            "50",
        )
        self.assertEqual(
            command[command.index("--uptake-volume-micron3") + 1],
            "1000",
        )
        self.assertEqual(
            command[command.index("--uptake-rate-per-min") + 1],
            "0.5",
        )

    def test_rejects_multiple_uptake_sinks(self) -> None:
        with self.assertRaises(ValueError):
            build_command(
                experiment(
                    uptake_sinks=(
                        point_sink("sink.one"),
                        point_sink("sink.two"),
                    )
                ),
                BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
                Path("runner"),
            )

    def test_maps_combined_release_and_uptake(self) -> None:
        command = build_command(
            experiment(
                release_sources=(point_source(),),
                uptake_sinks=(point_sink(),),
            ),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("runner"),
        )

        self.assertEqual(
            command[command.index("--source-rate-particle-equivalent-per-min") + 1],
            "120",
        )
        self.assertEqual(
            command[command.index("--uptake-rate-per-min") + 1],
            "0.5",
        )


class BioFVMResultTests(unittest.TestCase):
    def base_samples(self) -> tuple[tuple[float, float, float, float, float], ...]:
        return (
            (0.0, 2.0, 2.0, 2.0, 0.0),
            (2.0, 1.63746150616, 1.63746150616, 1.63746150616, 0.0),
            (4.0, 1.34064009207, 1.34064009207, 1.34064009207, 0.0),
            (6.0, 1.09762327219, 1.09762327219, 1.09762327219, 0.0),
            (8.0, 0.898657928234, 0.898657928234, 0.898657928234, 0.0),
            (10.0, 0.735758882343, 0.735758882343, 0.735758882343, 0.0),
        )

    def test_parses_samples_grid_fields_and_engine_metadata(self) -> None:
        result = parse_result(experiment(), result_output(self.base_samples()))

        self.assertEqual(result.experiment_id, "synthetic.uniform-decay")
        self.assertEqual(result.concentration_unit, "particle_equivalent/micron^3")
        self.assertEqual(result.engine, pinned_engine_metadata())
        self.assertEqual(result.grid.nx, 10)
        self.assertEqual(result.grid.ny, 5)
        self.assertEqual(result.grid.grid_spacing_micron, 20.0)
        self.assertEqual(result.grid.slice_thickness_micron, 25.0)
        self.assertEqual(result.grid.ordering, "x_fastest_then_y")
        self.assertEqual(len(result.samples), 6)
        self.assertEqual(len(result.field_snapshots), 6)
        self.assertEqual(len(result.field_snapshots[0].values), 50)
        self.assertEqual(result.field_snapshots[0].time_min, 0.0)
        self.assertTrue(all(value == 2.0 for value in result.field_snapshots[0].values))
        self.assertAlmostEqual(result.samples[0].integrated_field_quantity, 1_000_000.0)
        self.assertEqual(result.integrated_quantity_unit, "particle_equivalent")
        self.assertEqual(result.internalized_quantity_unit, "particle_equivalent")
        self.assertEqual(result.samples[0].internalized_field_quantity, 0.0)
        self.assertAlmostEqual(result.samples[-1].mean_concentration, 0.735758882343)

    def test_parses_nonzero_internalized_quantity(self) -> None:
        samples = (
            (0.0, 2.0, 2.0, 2.0, 0.0),
            (2.0, 1.999, 1.999, 1.999, 500.0),
            (4.0, 1.998, 1.998, 1.998, 1000.0),
            (6.0, 1.997, 1.997, 1.997, 1500.0),
            (8.0, 1.996, 1.996, 1.996, 2000.0),
            (10.0, 1.995, 1.995, 1.995, 2500.0),
        )

        result = parse_result(
            experiment(uptake_sinks=(point_sink(),)),
            result_output(samples),
        )

        self.assertEqual(result.samples[0].internalized_field_quantity, 0.0)
        self.assertEqual(result.samples[-1].internalized_field_quantity, 2500.0)

    def test_rejects_missing_or_duplicate_grid(self) -> None:
        with self.assertRaises(ValueError):
            parse_result(
                experiment(),
                result_output(self.base_samples(), include_grid=False),
            )

        output = result_output(self.base_samples())
        duplicate = output.replace(
            "grid\t10\t5\t20\t25\tx_fastest_then_y\n",
            "grid\t10\t5\t20\t25\tx_fastest_then_y\n"
            "grid\t10\t5\t20\t25\tx_fastest_then_y\n",
            1,
        )
        with self.assertRaises(ValueError):
            parse_result(experiment(), duplicate)

    def test_rejects_wrong_field_length(self) -> None:
        samples = self.base_samples()
        fields = tuple(
            tuple(sample[1] for _ in range(49))
            for sample in samples
        )
        with self.assertRaises(ValueError):
            parse_result(experiment(), result_output(samples, fields=fields))

    def test_rejects_field_summary_mismatch(self) -> None:
        samples = self.base_samples()
        fields = list(
            tuple(sample[1] for _ in range(50))
            for sample in samples
        )
        fields[0] = (3.0,) + tuple(2.0 for _ in range(49))

        with self.assertRaises(ValueError):
            parse_result(
                experiment(),
                result_output(samples, fields=tuple(fields)),
            )

    def test_rejects_internalized_quantity_without_uptake_or_at_uptake_start(self) -> None:
        unexpected = list(self.base_samples())
        unexpected[1] = (*unexpected[1][:4], 1.0)
        with self.assertRaises(ValueError):
            parse_result(experiment(), result_output(tuple(unexpected)))

        nonzero_start = list(self.base_samples())
        nonzero_start[0] = (*nonzero_start[0][:4], 1.0)
        with self.assertRaises(ValueError):
            parse_result(
                experiment(uptake_sinks=(point_sink(),)),
                result_output(tuple(nonzero_start)),
            )

    def test_accepts_roundoff_sized_summary_drift(self) -> None:
        samples = list(self.base_samples())
        samples[0] = (0.0, 2.0000000000000004, 2.0, 2.0, 0.0)
        fields = tuple(
            tuple(2.0 if index == 0 else sample[1] for _ in range(50))
            for index, sample in enumerate(samples)
        )

        result = parse_result(
            experiment(),
            result_output(tuple(samples), fields=fields),
        )

        self.assertAlmostEqual(result.samples[0].mean_concentration, 2.0)

    def test_rejects_engine_metadata_that_does_not_match_pin(self) -> None:
        with self.assertRaises(ValueError):
            parse_result(
                experiment(),
                result_output(self.base_samples(), physicell_release="1.14.3"),
            )

    def test_rejects_missing_or_non_monotonic_samples(self) -> None:
        no_samples = (
            "VESICLESCOPE_BIOFVM_RESULT\t3\n"
            "engine\tBioFVM\n"
            "physicell_release\t1.14.2\n"
            "physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763\n"
            "biofvm_version\t1.1.7\n"
            "grid\t10\t5\t20\t25\tx_fastest_then_y\n"
        )
        with self.assertRaises(ValueError):
            parse_result(experiment(), no_samples)

        backwards = (
            (2.0, 1.0, 1.0, 1.0, 0.0),
            (1.0, 1.0, 1.0, 1.0, 0.0),
        )
        with self.assertRaises(ValueError):
            parse_result(experiment(), result_output(backwards))


class BioFVMRunnerTests(unittest.TestCase):
    @patch("vesiclescope.engines.biofvm.subprocess.run")
    def test_runs_without_shell_and_parses_stdout(self, run_mock) -> None:
        samples = BioFVMResultTests().base_samples()
        run_mock.return_value = subprocess.CompletedProcess(
            args=["runner"],
            returncode=0,
            stdout=result_output(samples),
            stderr="",
        )

        result = run_transport(
            experiment(),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("runner"),
        )

        self.assertEqual(result.samples[-1].time_min, 10.0)
        self.assertEqual(result.field_snapshots[-1].time_min, 10.0)
        _, kwargs = run_mock.call_args
        self.assertTrue(kwargs["check"])
        self.assertTrue(kwargs["text"])
        self.assertTrue(kwargs["capture_output"])

    @patch("vesiclescope.engines.biofvm.subprocess.run")
    def test_surfaces_native_runner_failure(self, run_mock) -> None:
        run_mock.side_effect = subprocess.CalledProcessError(
            returncode=2,
            cmd=["runner"],
            stderr="invalid benchmark configuration",
        )

        with self.assertRaises(BioFVMRunError) as context:
            run_transport(
                experiment(),
                BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
                Path("runner"),
            )

        self.assertIn("invalid benchmark configuration", str(context.exception))


if __name__ == "__main__":
    unittest.main()
