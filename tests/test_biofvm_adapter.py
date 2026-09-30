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

    def test_rejects_multiple_uptake_sinks_or_combined_source_sink(self) -> None:
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

        with self.assertRaises(ValueError):
            build_command(
                experiment(
                    release_sources=(point_source(),),
                    uptake_sinks=(point_sink(),),
                ),
                BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
                Path("runner"),
            )


class BioFVMResultTests(unittest.TestCase):
    def test_parses_normalized_samples_and_engine_metadata(self) -> None:
        output = """VESICLESCOPE_BIOFVM_RESULT\t2
engine\tBioFVM
physicell_release\t1.14.2
physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763
biofvm_version\t1.1.7
sample\t0\t2\t2\t2\t0
sample\t2\t1.63746150616\t1.63746150616\t1.63746150616\t0
sample\t4\t1.34064009207\t1.34064009207\t1.34064009207\t0
sample\t6\t1.09762327219\t1.09762327219\t1.09762327219\t0
sample\t8\t0.898657928234\t0.898657928234\t0.898657928234\t0
sample\t10\t0.735758882343\t0.735758882343\t0.735758882343\t0
"""
        result = parse_result(experiment(), output)

        self.assertEqual(result.experiment_id, "synthetic.uniform-decay")
        self.assertEqual(result.concentration_unit, "particle_equivalent/micron^3")
        self.assertEqual(result.engine, pinned_engine_metadata())
        self.assertEqual(len(result.samples), 6)
        self.assertEqual(result.samples[0].time_min, 0.0)
        self.assertAlmostEqual(result.samples[0].integrated_field_quantity, 1_000_000.0)
        self.assertEqual(result.integrated_quantity_unit, "particle_equivalent")
        self.assertEqual(result.internalized_quantity_unit, "particle_equivalent")
        self.assertEqual(result.samples[0].internalized_field_quantity, 0.0)
        self.assertAlmostEqual(result.samples[-1].mean_concentration, 0.735758882343)

    def test_parses_nonzero_internalized_quantity(self) -> None:
        output = """VESICLESCOPE_BIOFVM_RESULT\t2
engine\tBioFVM
physicell_release\t1.14.2
physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763
biofvm_version\t1.1.7
sample\t0\t2\t2\t2\t0
sample\t2\t1.999\t1.95\t2\t500
sample\t4\t1.998\t1.90\t2\t1000
sample\t6\t1.997\t1.85\t2\t1500
sample\t8\t1.996\t1.80\t2\t2000
sample\t10\t1.995\t1.75\t2\t2500
"""

        result = parse_result(
            experiment(uptake_sinks=(point_sink(),)),
            output,
        )

        self.assertEqual(result.samples[0].internalized_field_quantity, 0.0)
        self.assertEqual(result.samples[-1].internalized_field_quantity, 2500.0)
        self.assertEqual(result.internalized_quantity_unit, "particle_equivalent")

    def test_accepts_roundoff_sized_mean_outside_uniform_min_max(self) -> None:
        output = """VESICLESCOPE_BIOFVM_RESULT\t2
engine\tBioFVM
physicell_release\t1.14.2
physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763
biofvm_version\t1.1.7
sample\t0\t2.0000000000000004\t2\t2\t0
sample\t2\t1.6374615061600002\t1.63746150616\t1.63746150616\t0
sample\t4\t1.3406400920700002\t1.34064009207\t1.34064009207\t0
sample\t6\t1.0976232721900001\t1.09762327219\t1.09762327219\t0
sample\t8\t0.8986579282340001\t0.898657928234\t0.898657928234\t0
sample\t10\t0.7357588823430001\t0.735758882343\t0.735758882343\t0
"""

        result = parse_result(experiment(), output)

        self.assertEqual(len(result.samples), 6)
        self.assertAlmostEqual(result.samples[0].mean_concentration, 2.0)

    def test_rejects_engine_metadata_that_does_not_match_pin(self) -> None:
        output = """VESICLESCOPE_BIOFVM_RESULT\t2
engine\tBioFVM
physicell_release\t1.14.3
physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763
biofvm_version\t1.1.7
sample\t0\t2\t2\t2\t0
"""

        with self.assertRaises(ValueError):
            parse_result(experiment(), output)

    def test_rejects_missing_or_non_monotonic_samples(self) -> None:
        no_samples = """VESICLESCOPE_BIOFVM_RESULT\t2
engine\tBioFVM
physicell_release\t1.14.2
physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763
biofvm_version\t1.1.7
"""
        with self.assertRaises(ValueError):
            parse_result(experiment(), no_samples)

        backwards = """VESICLESCOPE_BIOFVM_RESULT\t2
engine\tBioFVM
physicell_release\t1.14.2
physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763
biofvm_version\t1.1.7
sample\t2\t1\t1\t1\t0
sample\t1\t1\t1\t1\t0
"""
        with self.assertRaises(ValueError):
            parse_result(experiment(), backwards)


class BioFVMRunnerTests(unittest.TestCase):
    @patch("vesiclescope.engines.biofvm.subprocess.run")
    def test_runs_without_shell_and_parses_stdout(self, run_mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess(
            args=["runner"],
            returncode=0,
            stdout="""VESICLESCOPE_BIOFVM_RESULT\t2
engine\tBioFVM
physicell_release\t1.14.2
physicell_commit\tdbd3499250141b27600e91e501c54c46f68f2763
biofvm_version\t1.1.7
sample\t0\t2\t2\t2\t0
sample\t2\t1.63746150616\t1.63746150616\t1.63746150616\t0
sample\t4\t1.34064009207\t1.34064009207\t1.34064009207\t0
sample\t6\t1.09762327219\t1.09762327219\t1.09762327219\t0
sample\t8\t0.898657928234\t0.898657928234\t0.898657928234\t0
sample\t10\t0.735758882343\t0.735758882343\t0.735758882343\t0
""",
            stderr="",
        )

        result = run_transport(
            experiment(),
            BioFVMNumerics(grid_spacing_micron=20.0, time_step_min=0.1),
            Path("runner"),
        )

        self.assertEqual(result.samples[-1].time_min, 10.0)
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
