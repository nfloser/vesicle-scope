"""Run independent EV phenotype populations through the verified BioFVM path."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

from vesiclescope.domain import EVPopulationExperiment
from vesiclescope.engines import (
    BioFVMNumerics,
    BioFVMRunResult,
    SpatialFieldSnapshot2D,
    run_transport,
)


@dataclass(frozen=True, slots=True)
class PopulationTransportResult:
    """One phenotype-specific normalized transport result."""

    population_id: str
    phenotype_id: str
    result: BioFVMRunResult


@dataclass(frozen=True, slots=True)
class EVPopulationRunResult:
    """Ordered results for one independent-population composition experiment."""

    experiment_id: str
    populations: tuple[PopulationTransportResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.experiment_id, str) or not self.experiment_id.strip():
            raise ValueError("experiment_id must be non-blank")
        if not isinstance(self.populations, tuple) or not self.populations:
            raise ValueError("populations must be a non-empty tuple")
        if not all(isinstance(item, PopulationTransportResult) for item in self.populations):
            raise TypeError("populations must contain PopulationTransportResult objects")

        first = self.populations[0].result
        first_times = tuple(sample.time_min for sample in first.samples)
        first_fields = tuple(item.time_min for item in first.field_snapshots)
        for item in self.populations[1:]:
            result = item.result
            if result.grid != first.grid:
                raise ValueError("population results must share one normalized grid")
            if result.concentration_unit != first.concentration_unit:
                raise ValueError("population results must share one concentration unit")
            if result.integrated_quantity_unit != first.integrated_quantity_unit:
                raise ValueError("population results must share one integrated quantity unit")
            if tuple(sample.time_min for sample in result.samples) != first_times:
                raise ValueError("population results must share sample times")
            if tuple(field.time_min for field in result.field_snapshots) != first_fields:
                raise ValueError("population results must share field snapshot times")


def run_population_transport(
    experiment: EVPopulationExperiment,
    numerics: BioFVMNumerics,
    executable: Path,
) -> EVPopulationRunResult:
    """Run each non-interacting phenotype through the same verified solver path."""

    if not isinstance(experiment, EVPopulationExperiment):
        raise TypeError("experiment must be an EVPopulationExperiment")
    if not isinstance(numerics, BioFVMNumerics):
        raise TypeError("numerics must be BioFVMNumerics")

    results = tuple(
        PopulationTransportResult(
            population_id=population.population_id,
            phenotype_id=population.phenotype_id,
            result=run_transport(population.transport, numerics, executable),
        )
        for population in experiment.populations
    )
    return EVPopulationRunResult(
        experiment_id=experiment.experiment_id,
        populations=results,
    )


def sum_population_fields(
    run: EVPopulationRunResult,
) -> tuple[SpatialFieldSnapshot2D, ...]:
    """Sum compatible phenotype fields for a total-EV visualization.

    Separate population fields remain the primary scientific output. This sum
    is only meaningful because the population contract requires a common
    concentration unit and the composition model contains no cross-reactions.
    """

    if not isinstance(run, EVPopulationRunResult):
        raise TypeError("run must be an EVPopulationRunResult")

    fields_by_population = [
        item.result.field_snapshots for item in run.populations
    ]
    snapshot_count = len(fields_by_population[0])
    if any(len(fields) != snapshot_count for fields in fields_by_population):
        raise ValueError("population field series must have equal length")

    combined: list[SpatialFieldSnapshot2D] = []
    for snapshot_index in range(snapshot_count):
        snapshots = [
            fields[snapshot_index] for fields in fields_by_population
        ]
        time = snapshots[0].time_min
        if any(
            not math.isclose(item.time_min, time, rel_tol=0.0, abs_tol=1e-9)
            for item in snapshots[1:]
        ):
            raise ValueError("population field snapshots must share times")
        voxel_count = len(snapshots[0].values)
        if any(len(item.values) != voxel_count for item in snapshots[1:]):
            raise ValueError("population field snapshots must share voxel count")
        combined.append(
            SpatialFieldSnapshot2D(
                time_min=time,
                values=tuple(
                    sum(item.values[voxel] for item in snapshots)
                    for voxel in range(voxel_count)
                ),
            )
        )
    return tuple(combined)
