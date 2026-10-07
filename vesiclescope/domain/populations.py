"""EV phenotype-specific transport composition contracts."""

from __future__ import annotations

from dataclasses import dataclass

from .transport import TransportExperiment


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class EVPopulationTransport:
    """One EV phenotype mapped to one existing verified transport experiment."""

    population_id: str
    phenotype_id: str
    transport: TransportExperiment

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "population_id", _required_text(self.population_id, "population_id")
        )
        object.__setattr__(
            self, "phenotype_id", _required_text(self.phenotype_id, "phenotype_id")
        )
        if not isinstance(self.transport, TransportExperiment):
            raise TypeError("transport must be a TransportExperiment")


@dataclass(frozen=True, slots=True)
class EVPopulationExperiment:
    """Ordered independent EV populations sharing one space/time experiment frame.

    Populations are intentionally independent in this first composition model.
    They may have distinct release, diffusion, decay and uptake parameters, but
    no cross-population reaction term is implied.
    """

    experiment_id: str
    populations: tuple[EVPopulationTransport, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "experiment_id", _required_text(self.experiment_id, "experiment_id")
        )
        if not isinstance(self.populations, tuple) or not self.populations:
            raise ValueError("populations must be a non-empty tuple")
        if not all(isinstance(item, EVPopulationTransport) for item in self.populations):
            raise TypeError("populations must contain EVPopulationTransport objects")

        population_ids = tuple(item.population_id for item in self.populations)
        phenotype_ids = tuple(item.phenotype_id for item in self.populations)
        transport_ids = tuple(item.transport.experiment_id for item in self.populations)
        if len(set(population_ids)) != len(population_ids):
            raise ValueError("population identifiers must be unique")
        if len(set(phenotype_ids)) != len(phenotype_ids):
            raise ValueError("phenotype identifiers must be unique across simulated populations")
        if len(set(transport_ids)) != len(transport_ids):
            raise ValueError("population transport experiment identifiers must be unique")

        first = self.populations[0].transport
        for item in self.populations[1:]:
            transport = item.transport
            if transport.domain != first.domain:
                raise ValueError("all EV populations must share a common domain")
            if transport.duration_min != first.duration_min:
                raise ValueError("all EV populations must share a common duration")
            if transport.sample_every_min != first.sample_every_min:
                raise ValueError("all EV populations must share a common sampling interval")
            if transport.boundary != first.boundary:
                raise ValueError("all EV populations must share a common boundary condition")
            if transport.initial_concentration.unit != first.initial_concentration.unit:
                raise ValueError("all EV populations must share a common concentration unit")
