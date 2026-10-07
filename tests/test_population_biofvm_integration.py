import math
import os
import unittest
from pathlib import Path

from vesiclescope.domain import (
    BiologicalExposure,
    BoundaryCondition,
    EVMarkerFeature,
    EVPhenotype,
    EvidenceCategory,
    ExposureTarget,
    MarkerState,
    PerturbationStudy,
    PointReleaseSource,
    RectangularDomain2D,
    ScientificParameter,
    TransportExperiment,
)
from vesiclescope.engines import BioFVMNumerics
from vesiclescope.workflows.perturbation_transport import (
    PopulationTransportSpec,
    aggregate_population_samples,
    resolve_perturbation_transport,
    run_population_transport,
)


RUNNER = os.environ.get("VESICLESCOPE_BIOFVM_RUNNER")


def p(identifier: str, value: float, unit: str) -> ScientificParameter:
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier,
        value=value,
        unit=unit,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic two-population verification input.",),
    )


def phenotype(identifier: str) -> EVPhenotype:
    return EVPhenotype(
        identifier=identifier,
        name=identifier,
        markers=(
            EVMarkerFeature(
                identifier=f"{identifier}.marker",
                marker_name="synthetic marker",
                state=MarkerState.UNRESOLVED,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
                limitations=("Synthetic phenotype identity only.",),
            ),
        ),
    )


def experiment(identifier: str, release_rate: float) -> TransportExperiment:
    return TransportExperiment(
        experiment_id=identifier,
        domain=RectangularDomain2D(
            width_micron=200.0,
            height_micron=100.0,
            slice_thickness_micron=25.0,
        ),
        duration_min=4.0,
        sample_every_min=2.0,
        boundary=BoundaryCondition.NO_FLUX,
        diffusion=p(f"{identifier}.diffusion", 100.0, "micron^2/min"),
        decay=p(f"{identifier}.decay", 0.0, "1/min"),
        initial_concentration=p(
            f"{identifier}.initial",
            0.0,
            "particle_equivalent/micron^3",
        ),
        release_sources=(
            PointReleaseSource(
                identifier="donor",
                x_micron=100.0,
                y_micron=50.0,
                release_rate=p(
                    f"{identifier}.release",
                    release_rate,
                    "particle_equivalent/min",
                ),
            ),
        ),
    )


def resolved_two_population_plan():
    study = PerturbationStudy(
        study_id="synthetic.two-population-mass-balance",
        exposures=(
            BiologicalExposure(
                identifier="declared-control",
                compound_name="no-op synthetic control",
                concentration=p("control.concentration", 0.0, "a.u."),
                target=ExposureTarget.DONOR_CELL_POPULATION,
                start_min=0.0,
                end_min=4.0,
                evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
                limitations=("No biological stimulus is implied.",),
            ),
        ),
        phenotypes=(phenotype("population-a"), phenotype("population-b")),
        effects=(),
        limitations=("Numerical composition benchmark only.",),
    )
    return resolve_perturbation_transport(
        study,
        (
            PopulationTransportSpec(
                phenotype_id="population-a",
                experiment=experiment("population-a", 30.0),
            ),
            PopulationTransportSpec(
                phenotype_id="population-b",
                experiment=experiment("population-b", 70.0),
            ),
        ),
    )


@unittest.skipUnless(RUNNER, "native BioFVM runner is not built for this test job")
class PopulationBioFVMIntegrationTests(unittest.TestCase):
    @property
    def runner(self) -> Path:
        assert RUNNER is not None
        return Path(RUNNER)

    def run_plan(self, grid: float, dt: float):
        return run_population_transport(
            resolved_two_population_plan(),
            BioFVMNumerics(grid_spacing_micron=grid, time_step_min=dt),
            self.runner,
            "e" * 40,
        )

    def test_two_population_total_closes_mass_balance(self) -> None:
        run = self.run_plan(10.0, 0.1)
        aggregate = aggregate_population_samples(run)
        expected_release_rate = 100.0

        for sample in aggregate:
            expected = expected_release_rate * sample.time_min
            self.assertAlmostEqual(
                sample.integrated_field_quantity
                + sample.internalized_field_quantity,
                expected,
                delta=max(1e-8, expected * 1e-9),
            )
            self.assertTrue(
                math.isclose(
                    sample.internalized_field_quantity,
                    0.0,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            )

    def test_two_population_total_is_stable_across_grid_and_timestep_refinement(self) -> None:
        coarse = aggregate_population_samples(self.run_plan(20.0, 0.2))
        fine = aggregate_population_samples(self.run_plan(10.0, 0.1))

        self.assertAlmostEqual(
            coarse[-1].integrated_field_quantity,
            fine[-1].integrated_field_quantity,
            delta=1e-8,
        )
        self.assertAlmostEqual(
            coarse[-1].integrated_field_quantity,
            100.0 * 4.0,
            delta=1e-8,
        )


if __name__ == "__main__":
    unittest.main()
