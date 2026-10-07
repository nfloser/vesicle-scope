import math
import os
import unittest
from pathlib import Path

from vesiclescope.domain import (
    BoundaryCondition,
    EVPopulationExperiment,
    EVPopulationTransport,
    EvidenceCategory,
    PointReleaseSource,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines import BioFVMNumerics
from vesiclescope.workflows.population_transport import (
    run_population_transport,
    sum_population_fields,
)


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")


def synthetic(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier.replace(".", " "),
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic multi-population verification input.",),
    )


def population_transport(identifier: str, rate: float) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=f"synthetic.population.{identifier}",
        domain=RectangularDomain2D(200.0, 100.0, 25.0),
        duration_min=10.0,
        sample_every_min=5.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=synthetic(f"{identifier}.diffusion", 100.0, "micron^2/min"),
        decay=synthetic(f"{identifier}.decay", 0.0, "1/min"),
        initial_concentration=synthetic(
            f"{identifier}.initial",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            PointReleaseSource(
                identifier="donor",
                x_micron=100.0,
                y_micron=50.0,
                release_rate=synthetic(
                    f"{identifier}.release",
                    rate,
                    "particle_equivalent/min",
                ),
            ),
        ),
    )


def two_population_experiment() -> EVPopulationExperiment:
    return EVPopulationExperiment(
        experiment_id="synthetic.two-phenotype-populations",
        populations=(
            EVPopulationTransport(
                population_id="population.cd9",
                phenotype_id="phenotype.cd9",
                transport=population_transport("cd9", 120.0),
            ),
            EVPopulationTransport(
                population_id="population.cd63",
                phenotype_id="phenotype.cd63",
                transport=population_transport("cd63", 40.0),
            ),
        ),
    )


@unittest.skipUnless(RUNNER, "native BioFVM runner is not built for this test job")
class PopulationTransportIntegrationTests(unittest.TestCase):
    @property
    def runner(self) -> Path:
        assert RUNNER is not None
        return Path(RUNNER)

    def test_two_independent_populations_preserve_mass_across_refinement(self) -> None:
        experiment = two_population_experiment()
        expected_rate = 160.0
        final_totals = []

        for grid, dt in ((20.0, 0.2), (20.0, 0.1), (10.0, 0.1)):
            run = run_population_transport(
                experiment,
                BioFVMNumerics(grid_spacing_micron=grid, time_step_min=dt),
                self.runner,
            )

            self.assertEqual(
                tuple(item.phenotype_id for item in run.populations),
                ("phenotype.cd9", "phenotype.cd63"),
            )
            for population, expected_population_rate in zip(
                run.populations,
                (120.0, 40.0),
            ):
                for sample in population.result.samples:
                    self.assertAlmostEqual(
                        sample.integrated_field_quantity,
                        expected_population_rate * sample.time_min,
                        delta=max(1e-8, expected_population_rate * sample.time_min * 1e-9),
                    )

            combined = sum_population_fields(run)
            final = combined[-1]
            voxel_volume = grid * grid * experiment.populations[0].transport.domain.slice_thickness_micron
            integrated = sum(final.values) * voxel_volume
            expected = expected_rate * final.time_min
            self.assertAlmostEqual(integrated, expected, delta=max(1e-8, expected * 1e-9))
            final_totals.append(integrated)

        self.assertTrue(
            all(
                math.isclose(value, final_totals[0], rel_tol=0.0, abs_tol=1e-8)
                for value in final_totals[1:]
            )
        )


if __name__ == "__main__":
    unittest.main()
