"""Evidence-aware perturbation, EV phenotype and cargo contracts.

The contracts in this module describe biological context and evidence. They do
not themselves alter transport parameters. Executable model effects require an
explicit ModelEffectMapping and a separate execution boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .parameters import (
    EvidenceCategory,
    EvidenceSource,
    ParameterContext,
    ScientificParameter,
)


class ExposureTarget(str, Enum):
    """Biological compartment exposed to a declared perturbation."""

    WHOLE_BLOOD = "whole_blood"
    BLOOD_CELL_POPULATION = "blood_cell_population"
    DONOR_CELL_POPULATION = "donor_cell_population"
    RECIPIENT_CELL_POPULATION = "recipient_cell_population"
    CELL_CULTURE = "cell_culture"
    ISOLATED_EV_PREPARATION = "isolated_ev_preparation"
    OTHER = "other"


class MarkerState(str, Enum):
    """Qualitative state of one marker in a phenotype definition."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNRESOLVED = "unresolved"


class CargoClass(str, Enum):
    """Broad cargo class without claiming a particular biogenesis route."""

    PROTEIN = "protein"
    MRNA = "mrna"
    MIRNA = "mirna"
    OTHER_RNA = "other_rna"
    LIPID = "lipid"
    METABOLITE = "metabolite"
    OTHER = "other"


class EffectOutcome(str, Enum):
    """Observed outcome associated with a perturbation."""

    EV_RELEASE = "ev_release"
    EV_UPTAKE = "ev_uptake"
    EV_CLEARANCE = "ev_clearance"
    EV_SIZE = "ev_size"
    MARKER_ABUNDANCE = "marker_abundance"
    CARGO_ABUNDANCE = "cargo_abundance"
    OTHER = "other"


class EffectDirection(str, Enum):
    """Direction reported by evidence without inventing an effect size."""

    INCREASE = "increase"
    DECREASE = "decrease"
    NO_CHANGE = "no_change"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ModelEffectTarget(str, Enum):
    """Model quantity an evidence-backed effect may explicitly map onto."""

    RELEASE_RATE = "release_rate"
    UPTAKE_RATE = "uptake_rate"
    DECAY_RATE = "decay_rate"
    PHENOTYPE_FRACTION = "phenotype_fraction"
    CARGO_ABUNDANCE = "cargo_abundance"


class EffectOperation(str, Enum):
    """How an explicit model mapping changes its target quantity."""

    MULTIPLY = "multiply"
    ADD = "add"
    SET = "set"


_SOURCE_REQUIRED = frozenset(
    {
        EvidenceCategory.MEASURED_TARGET_CONTEXT,
        EvidenceCategory.MEASURED_RELATED_CONTEXT,
        EvidenceCategory.LITERATURE_ESTIMATE,
        EvidenceCategory.FITTED,
        EvidenceCategory.INFERRED,
    }
)


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-blank string")
    return value.strip()


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field_name} must be a tuple of strings")
    return tuple(_required_text(value, field_name) for value in values)


def _finite(value: float, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _require_evidence(
    evidence: EvidenceCategory,
    source: EvidenceSource | None,
) -> None:
    if not isinstance(evidence, EvidenceCategory):
        raise TypeError("evidence must be an EvidenceCategory")
    if source is not None and not isinstance(source, EvidenceSource):
        raise TypeError("source must be an EvidenceSource or None")
    if evidence in _SOURCE_REQUIRED and source is None:
        raise ValueError(f"{evidence.value} evidence requires a source")


def _require_context(context: ParameterContext | None) -> None:
    if context is not None and not isinstance(context, ParameterContext):
        raise TypeError("context must be a ParameterContext or None")


@dataclass(frozen=True, slots=True)
class BiologicalExposure:
    """One explicit time-bounded stimulus applied to one biological target."""

    identifier: str
    compound_name: str
    concentration: ScientificParameter
    target: ExposureTarget
    start_min: float
    end_min: float
    evidence: EvidenceCategory
    source: EvidenceSource | None = None
    context: ParameterContext | None = None
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "compound_name",
            _required_text(self.compound_name, "compound_name"),
        )
        if not isinstance(self.concentration, ScientificParameter):
            raise TypeError("concentration must be a ScientificParameter")
        if self.concentration.value < 0.0:
            raise ValueError("concentration must be non-negative")
        if not isinstance(self.target, ExposureTarget):
            raise TypeError("target must be an ExposureTarget")
        start = _finite(self.start_min, "start_min")
        end = _finite(self.end_min, "end_min")
        if end <= start:
            raise ValueError("end_min must be greater than start_min")
        object.__setattr__(self, "start_min", start)
        object.__setattr__(self, "end_min", end)
        _require_evidence(self.evidence, self.source)
        _require_context(self.context)
        object.__setattr__(
            self,
            "assumptions",
            _text_tuple(self.assumptions, "assumptions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )


@dataclass(frozen=True, slots=True)
class EVMarkerFeature:
    """One marker annotation within an EV phenotype."""

    identifier: str
    marker_name: str
    state: MarkerState
    evidence: EvidenceCategory
    source: EvidenceSource | None = None
    context: ParameterContext | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "marker_name",
            _required_text(self.marker_name, "marker_name"),
        )
        if not isinstance(self.state, MarkerState):
            raise TypeError("state must be a MarkerState")
        _require_evidence(self.evidence, self.source)
        _require_context(self.context)
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )


@dataclass(frozen=True, slots=True)
class EVCargoFeature:
    """One cargo annotation or measured quantity within an EV phenotype."""

    identifier: str
    molecule_name: str
    cargo_class: CargoClass
    evidence: EvidenceCategory
    source: EvidenceSource | None = None
    context: ParameterContext | None = None
    abundance: ScientificParameter | None = None
    qualitative_state: str | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "molecule_name",
            _required_text(self.molecule_name, "molecule_name"),
        )
        if not isinstance(self.cargo_class, CargoClass):
            raise TypeError("cargo_class must be a CargoClass")
        _require_evidence(self.evidence, self.source)
        _require_context(self.context)
        if self.abundance is not None and not isinstance(
            self.abundance,
            ScientificParameter,
        ):
            raise TypeError("abundance must be a ScientificParameter or None")
        object.__setattr__(
            self,
            "qualitative_state",
            _optional_text(self.qualitative_state, "qualitative_state"),
        )
        if self.abundance is None and self.qualitative_state is None:
            raise ValueError(
                "cargo feature requires abundance or a qualitative_state"
            )
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )


@dataclass(frozen=True, slots=True)
class EVPhenotype:
    """One named EV subpopulation/phenotype with explicit marker and cargo evidence."""

    identifier: str
    name: str
    markers: tuple[EVMarkerFeature, ...] = ()
    cargo: tuple[EVCargoFeature, ...] = ()
    context: ParameterContext | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(self, "name", _required_text(self.name, "name"))
        if not isinstance(self.markers, tuple) or not all(
            isinstance(item, EVMarkerFeature) for item in self.markers
        ):
            raise TypeError("markers must be a tuple of EVMarkerFeature objects")
        if not isinstance(self.cargo, tuple) or not all(
            isinstance(item, EVCargoFeature) for item in self.cargo
        ):
            raise TypeError("cargo must be a tuple of EVCargoFeature objects")
        if not self.markers and not self.cargo:
            raise ValueError("EV phenotype requires at least one marker or cargo feature")
        feature_ids = tuple(
            item.identifier for item in (*self.markers, *self.cargo)
        )
        if len(set(feature_ids)) != len(feature_ids):
            raise ValueError("phenotype feature identifiers must be unique")
        _require_context(self.context)
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )


@dataclass(frozen=True, slots=True)
class ModelEffectMapping:
    """Explicit optional mapping from evidence to one model quantity."""

    target: ModelEffectTarget
    operation: EffectOperation
    value: ScientificParameter
    target_identifier: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.target, ModelEffectTarget):
            raise TypeError("target must be a ModelEffectTarget")
        if not isinstance(self.operation, EffectOperation):
            raise TypeError("operation must be an EffectOperation")
        if not isinstance(self.value, ScientificParameter):
            raise TypeError("value must be a ScientificParameter")
        object.__setattr__(
            self,
            "target_identifier",
            _optional_text(self.target_identifier, "target_identifier"),
        )


@dataclass(frozen=True, slots=True)
class PerturbationEffect:
    """One evidence-backed outcome, distinct from the exposure that precedes it."""

    identifier: str
    exposure_id: str
    outcome: EffectOutcome
    direction: EffectDirection
    evidence: EvidenceCategory
    source: EvidenceSource | None = None
    context: ParameterContext | None = None
    phenotype_id: str | None = None
    feature_id: str | None = None
    magnitude: ScientificParameter | None = None
    model_mapping: ModelEffectMapping | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "identifier",
            _required_text(self.identifier, "identifier"),
        )
        object.__setattr__(
            self,
            "exposure_id",
            _required_text(self.exposure_id, "exposure_id"),
        )
        if not isinstance(self.outcome, EffectOutcome):
            raise TypeError("outcome must be an EffectOutcome")
        if not isinstance(self.direction, EffectDirection):
            raise TypeError("direction must be an EffectDirection")
        _require_evidence(self.evidence, self.source)
        _require_context(self.context)
        object.__setattr__(
            self,
            "phenotype_id",
            _optional_text(self.phenotype_id, "phenotype_id"),
        )
        object.__setattr__(
            self,
            "feature_id",
            _optional_text(self.feature_id, "feature_id"),
        )
        if self.feature_id is not None and self.phenotype_id is None:
            raise ValueError("feature_id requires phenotype_id")
        if self.magnitude is not None and not isinstance(
            self.magnitude,
            ScientificParameter,
        ):
            raise TypeError("magnitude must be a ScientificParameter or None")
        if self.model_mapping is not None and not isinstance(
            self.model_mapping,
            ModelEffectMapping,
        ):
            raise TypeError("model_mapping must be a ModelEffectMapping or None")
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )


@dataclass(frozen=True, slots=True)
class PerturbationStudy:
    """Evidence package linking exposures, EV phenotypes and reported effects."""

    study_id: str
    exposures: tuple[BiologicalExposure, ...]
    phenotypes: tuple[EVPhenotype, ...]
    effects: tuple[PerturbationEffect, ...]
    measurement_dataset_ids: tuple[str, ...] = ()
    transport_experiment_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "study_id",
            _required_text(self.study_id, "study_id"),
        )
        if not isinstance(self.exposures, tuple) or not self.exposures:
            raise ValueError("exposures must be a non-empty tuple")
        if not all(isinstance(item, BiologicalExposure) for item in self.exposures):
            raise TypeError("exposures must contain BiologicalExposure objects")
        if not isinstance(self.phenotypes, tuple):
            raise TypeError("phenotypes must be a tuple")
        if not all(isinstance(item, EVPhenotype) for item in self.phenotypes):
            raise TypeError("phenotypes must contain EVPhenotype objects")
        if not isinstance(self.effects, tuple):
            raise TypeError("effects must be a tuple")
        if not all(isinstance(item, PerturbationEffect) for item in self.effects):
            raise TypeError("effects must contain PerturbationEffect objects")

        exposure_ids = tuple(item.identifier for item in self.exposures)
        phenotype_ids = tuple(item.identifier for item in self.phenotypes)
        effect_ids = tuple(item.identifier for item in self.effects)
        for values, label in (
            (exposure_ids, "exposure"),
            (phenotype_ids, "phenotype"),
            (effect_ids, "effect"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} identifiers must be unique")

        phenotype_by_id = {
            phenotype.identifier: phenotype for phenotype in self.phenotypes
        }
        exposure_id_set = set(exposure_ids)
        for effect in self.effects:
            if effect.exposure_id not in exposure_id_set:
                raise ValueError(
                    f"effect {effect.identifier!r} references unknown exposure "
                    f"{effect.exposure_id!r}"
                )
            if (
                effect.phenotype_id is not None
                and effect.phenotype_id not in phenotype_by_id
            ):
                raise ValueError(
                    f"effect {effect.identifier!r} references unknown phenotype "
                    f"{effect.phenotype_id!r}"
                )
            if effect.feature_id is not None:
                phenotype = phenotype_by_id[effect.phenotype_id]
                feature_ids = {
                    item.identifier
                    for item in (*phenotype.markers, *phenotype.cargo)
                }
                if effect.feature_id not in feature_ids:
                    raise ValueError(
                        f"effect {effect.identifier!r} references unknown phenotype "
                        f"feature {effect.feature_id!r}"
                    )

        measurement_ids = _text_tuple(
            self.measurement_dataset_ids,
            "measurement_dataset_ids",
        )
        transport_ids = _text_tuple(
            self.transport_experiment_ids,
            "transport_experiment_ids",
        )
        if len(set(measurement_ids)) != len(measurement_ids):
            raise ValueError("measurement_dataset_ids must be unique")
        if len(set(transport_ids)) != len(transport_ids):
            raise ValueError("transport_experiment_ids must be unique")
        object.__setattr__(self, "measurement_dataset_ids", measurement_ids)
        object.__setattr__(self, "transport_experiment_ids", transport_ids)
        object.__setattr__(
            self,
            "limitations",
            _text_tuple(self.limitations, "limitations"),
        )
