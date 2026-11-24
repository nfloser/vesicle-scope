"""Cross-source consistency analysis built only from registry records.

Combines independent evidence that the individual sources cannot combine
themselves:

1. EV size -> free-solution Stokes-Einstein diffusion bound.
2. Tumour signal retention (Colombo 2025) -> length scale lambda = sqrt(D/k_eff).
3. Required effective loss k_eff = D / lambda^2 at free diffusion, compared with
   blood clearance from measured circulation half-lives, kept separate for
   mouse small EVs and human platelet microparticles.
4. Interstitial flow (device range and an in-tissue measurement) -> Peclet
   number Pe = v lambda / D.
5. Brain extracellular space width versus EV diameter (geometric exclusion).

Every output is conditional on the steady-state linear transport model. Ranges
are interval bounds from the records, not probability distributions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from vesiclescope.analysis.reach import stokes_einstein_diffusion_micron2_per_min
from vesiclescope.validation import colombo_2025_length_scale_constraints

from . import EvidenceDatabase, EvidenceRecord, load_evidence


# Physical reference values used only for the free-diffusion bound.
BODY_TEMPERATURE_K = 310.15
WATER_37C_VISCOSITY_PA_S = 0.6913e-3
ASSUMED_DONOR_RADII_MICRON = (5.0, 10.0, 15.0, 20.0)

_TIME_TO_MIN = {"min": 1.0, "h": 60.0, "s": 1.0 / 60.0}
_VELOCITY_TO_UM_PER_MIN = {"um/s": 60.0, "um/min": 1.0}


def half_life_minutes(record: EvidenceRecord) -> tuple[float, float, float]:
    """(central, low, high) half-life of a record in minutes."""

    if record.unit not in _TIME_TO_MIN:
        raise ValueError(f"unsupported half-life unit {record.unit!r} in {record.id}")
    factor = _TIME_TO_MIN[record.unit]
    value = record.value
    central = value.central if value.central is not None else math.sqrt(value.low * value.high)
    low, high = value.interval()
    return (central * factor, low * factor, high * factor)


def _rate_range(records: tuple[EvidenceRecord, ...]) -> tuple[float, float]:
    rates = [math.log(2.0) / half_life_minutes(item)[0] for item in records]
    return (min(rates), max(rates))


@dataclass(frozen=True, slots=True)
class EvidenceSynthesis:
    record_ids: tuple[str, ...]
    ev_diameter_nm: tuple[float, float]
    free_diffusion_micron2_per_min: tuple[float, float]
    length_scale_micron: tuple[float, float]
    required_loss_rate_per_min: tuple[float, float]
    mouse_sev_clearance_rate_per_min: tuple[float, float]
    human_pmp_clearance_rate_per_min: tuple[float, float]
    flow_velocity_micron_per_min: tuple[float, float]
    tissue_flow_velocity_micron_per_min: float
    peclet_at_free_diffusion: tuple[float, float]
    diffusion_for_peclet_one_micron2_per_min: tuple[float, float]
    brain_ecs_width_nm: tuple[float, float]

    @staticmethod
    def _ratio(required: tuple[float, float], clearance: tuple[float, float]) -> tuple[float, float]:
        return (required[0] / clearance[1], required[1] / clearance[0])

    @property
    def required_loss_vs_blood_clearance(self) -> tuple[float, float]:
        """Required local loss relative to mouse small-EV blood clearance."""

        return self._ratio(self.required_loss_rate_per_min, self.mouse_sev_clearance_rate_per_min)

    @property
    def required_loss_vs_human_pmp_clearance(self) -> tuple[float, float]:
        return self._ratio(self.required_loss_rate_per_min, self.human_pmp_clearance_rate_per_min)

    @property
    def ev_exceeds_brain_ecs_width(self) -> bool:
        return self.ev_diameter_nm[0] > self.brain_ecs_width_nm[1]

    def summary_lines(self) -> tuple[str, ...]:
        lo, hi = self.required_loss_vs_blood_clearance
        hlo, hhi = self.required_loss_vs_human_pmp_clearance
        tissue_pe = (
            self.tissue_flow_velocity_micron_per_min * self.length_scale_micron[0]
            / self.free_diffusion_micron2_per_min[1],
            self.tissue_flow_velocity_micron_per_min * self.length_scale_micron[1]
            / self.free_diffusion_micron2_per_min[0],
        )
        return (
            f"EV diameter {self.ev_diameter_nm[0]:g}-{self.ev_diameter_nm[1]:g} nm -> free "
            f"diffusion {self.free_diffusion_micron2_per_min[0]:.0f}-"
            f"{self.free_diffusion_micron2_per_min[1]:.0f} um^2/min (upper bound).",
            f"Tumour length scale lambda = {self.length_scale_micron[0]:.1f}-"
            f"{self.length_scale_micron[1]:.1f} um.",
            f"At free diffusion this needs local loss k_eff = "
            f"{self.required_loss_rate_per_min[0]:.2f}-{self.required_loss_rate_per_min[1]:.2f} /min "
            f"(1/k = {1 / self.required_loss_rate_per_min[1]:.1f}-"
            f"{1 / self.required_loss_rate_per_min[0]:.1f} min).",
            f"Mouse small-EV blood clearance: {self.mouse_sev_clearance_rate_per_min[0]:.2f}-"
            f"{self.mouse_sev_clearance_rate_per_min[1]:.2f} /min; required local loss is "
            f"{lo:.1f}-{hi:.1f}x that.",
            f"Human platelet-microparticle clearance: {self.human_pmp_clearance_rate_per_min[0]:.4f}-"
            f"{self.human_pmp_clearance_rate_per_min[1]:.4f} /min; required local loss is "
            f"{hlo:.0f}-{hhi:.0f}x that.",
            f"Interstitial flow {self.flow_velocity_micron_per_min[0]:.0f}-"
            f"{self.flow_velocity_micron_per_min[1]:.0f} um/min gives Pe = "
            f"{self.peclet_at_free_diffusion[0]:.2f}-{self.peclet_at_free_diffusion[1]:.2f} at free "
            f"diffusion; convection dominates (Pe > 1) once D < "
            f"{self.diffusion_for_peclet_one_micron2_per_min[0]:.0f}-"
            f"{self.diffusion_for_peclet_one_micron2_per_min[1]:.0f} um^2/min.",
            f"Measured tissue flow {self.tissue_flow_velocity_micron_per_min:.0f} um/min gives Pe = "
            f"{tissue_pe[0]:.2f}-{tissue_pe[1]:.2f} at free diffusion.",
            f"Brain extracellular space width {self.brain_ecs_width_nm[0]:g}-"
            f"{self.brain_ecs_width_nm[1]:g} nm vs EV diameter {self.ev_diameter_nm[0]:g}-"
            f"{self.ev_diameter_nm[1]:g} nm: EVs "
            + ("exceed" if self.ev_exceeds_brain_ecs_width else "do not exceed")
            + " the typical channel width, so unhindered diffusion is not expected there.",
        )


def synthesize(database: EvidenceDatabase | None = None) -> EvidenceSynthesis:
    database = database or load_evidence()
    size = database.get("exercise-sev-diameter")
    flow = database.get("interstitial-flow-velocity-range")
    tissue_flow = database.get("interstitial-flow-velocity-tissue")
    retention = database.get("colombo-tumour-retention-landmarks")
    ecs = database.get("brain-ecs-width")
    half_lives = database.quantities("circulation_half_life")
    mouse = tuple(item for item in half_lives if (item.context.species or "") == "mouse")
    human = tuple(item for item in half_lives if (item.context.species or "") == "human")
    if not mouse or not human:
        raise ValueError("synthesis needs mouse and human circulation half-lives")
    if size.unit != "nm" or ecs.unit != "nm":
        raise ValueError("unexpected size units in synthesis inputs")

    d_lo, d_hi = size.value.interval()
    diffusion = tuple(
        sorted(
            stokes_einstein_diffusion_micron2_per_min(
                hydrodynamic_diameter_nm=diameter,
                temperature_kelvin=BODY_TEMPERATURE_K,
                viscosity_pa_s=WATER_37C_VISCOSITY_PA_S,
            )
            for diameter in (d_lo, d_hi)
        )
    )
    lam_lo, lam_hi = colombo_2025_length_scale_constraints(
        ASSUMED_DONOR_RADII_MICRON
    ).length_scale_range_micron
    required = (diffusion[0] / lam_hi**2, diffusion[1] / lam_lo**2)
    factor = _VELOCITY_TO_UM_PER_MIN[flow.unit]
    v_lo, v_hi = (x * factor for x in flow.value.interval())
    tissue_v = tissue_flow.value.central * _VELOCITY_TO_UM_PER_MIN[tissue_flow.unit]
    return EvidenceSynthesis(
        record_ids=(
            size.id, retention.id, flow.id, tissue_flow.id, ecs.id,
            *(item.id for item in half_lives),
        ),
        ev_diameter_nm=(d_lo, d_hi),
        free_diffusion_micron2_per_min=diffusion,
        length_scale_micron=(lam_lo, lam_hi),
        required_loss_rate_per_min=required,
        mouse_sev_clearance_rate_per_min=_rate_range(mouse),
        human_pmp_clearance_rate_per_min=_rate_range(human),
        flow_velocity_micron_per_min=(v_lo, v_hi),
        tissue_flow_velocity_micron_per_min=tissue_v,
        peclet_at_free_diffusion=(v_lo * lam_lo / diffusion[1], v_hi * lam_hi / diffusion[0]),
        diffusion_for_peclet_one_micron2_per_min=(v_lo * lam_lo, v_hi * lam_hi),
        brain_ecs_width_nm=ecs.value.interval(),
    )
