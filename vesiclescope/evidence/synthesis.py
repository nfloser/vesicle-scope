"""Cross-source consistency analysis built only from registry records.

Combines independent evidence that the individual sources cannot combine
themselves:

1. EV size (Frühbeis 2015) -> free-solution Stokes-Einstein diffusion bound.
2. Tumour signal retention (Colombo 2025) -> length scale lambda = sqrt(D/k_eff).
3. Required effective loss k_eff = D / lambda^2 at free diffusion, compared with
   whole-body blood clearance from measured circulation half-lives.
4. Interstitial flow (Sariano 2023) -> Peclet number Pe = v lambda / D, i.e.
   whether convection or diffusion dominates transport over one length scale.

Every output is conditional on the steady-state linear transport model. Ranges
are interval bounds from the records, not probability distributions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from vesiclescope.analysis.reach import stokes_einstein_diffusion_micron2_per_min
from vesiclescope.validation import colombo_2025_length_scale_constraints

from . import EvidenceDatabase, load_evidence


# Physical reference values used only for the free-diffusion bound.
BODY_TEMPERATURE_K = 310.15
WATER_37C_VISCOSITY_PA_S = 0.6913e-3
ASSUMED_DONOR_RADII_MICRON = (5.0, 10.0, 15.0, 20.0)


@dataclass(frozen=True, slots=True)
class EvidenceSynthesis:
    record_ids: tuple[str, ...]
    ev_diameter_nm: tuple[float, float]
    free_diffusion_micron2_per_min: tuple[float, float]
    length_scale_micron: tuple[float, float]
    required_loss_rate_per_min: tuple[float, float]
    blood_clearance_rate_per_min: tuple[float, float]
    flow_velocity_micron_per_min: tuple[float, float]
    peclet_at_free_diffusion: tuple[float, float]
    diffusion_for_peclet_one_micron2_per_min: tuple[float, float]

    @property
    def required_loss_vs_blood_clearance(self) -> tuple[float, float]:
        """Ratio of required local loss to whole-body blood clearance (min, max)."""

        return (
            self.required_loss_rate_per_min[0] / self.blood_clearance_rate_per_min[1],
            self.required_loss_rate_per_min[1] / self.blood_clearance_rate_per_min[0],
        )

    def summary_lines(self) -> tuple[str, ...]:
        lo, hi = self.required_loss_vs_blood_clearance
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
            f"Whole-body blood clearance from half-lives: "
            f"{self.blood_clearance_rate_per_min[0]:.2f}-{self.blood_clearance_rate_per_min[1]:.2f} /min; "
            f"required local loss is {lo:.1f}-{hi:.1f}x that.",
            f"Interstitial flow {self.flow_velocity_micron_per_min[0]:.0f}-"
            f"{self.flow_velocity_micron_per_min[1]:.0f} um/min gives Pe = "
            f"{self.peclet_at_free_diffusion[0]:.2f}-{self.peclet_at_free_diffusion[1]:.2f} at free "
            f"diffusion; convection dominates (Pe > 1) once D < "
            f"{self.diffusion_for_peclet_one_micron2_per_min[0]:.0f}-"
            f"{self.diffusion_for_peclet_one_micron2_per_min[1]:.0f} um^2/min.",
        )


def synthesize(database: EvidenceDatabase | None = None) -> EvidenceSynthesis:
    database = database or load_evidence()
    size = database.get("exercise-sev-diameter")
    half_lives = database.quantities("circulation_half_life")
    flow = database.get("interstitial-flow-velocity-range")
    retention = database.get("colombo-tumour-retention-landmarks")
    if size.unit != "nm" or flow.unit != "um/s":
        raise ValueError("unexpected units in synthesis inputs")
    if any(item.unit != "min" for item in half_lives) or not half_lives:
        raise ValueError("circulation half-lives must be present in minutes")

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
    clearance_rates = [math.log(2.0) / item.value.central for item in half_lives]
    clearance = (min(clearance_rates), max(clearance_rates))
    v_lo, v_hi = (x * 60.0 for x in flow.value.interval())
    peclet = (v_lo * lam_lo / diffusion[1], v_hi * lam_hi / diffusion[0])
    d_star = (v_lo * lam_lo, v_hi * lam_hi)
    return EvidenceSynthesis(
        record_ids=(size.id, retention.id, flow.id, *(item.id for item in half_lives)),
        ev_diameter_nm=(d_lo, d_hi),
        free_diffusion_micron2_per_min=diffusion,
        length_scale_micron=(lam_lo, lam_hi),
        required_loss_rate_per_min=required,
        blood_clearance_rate_per_min=clearance,
        flow_velocity_micron_per_min=(v_lo, v_hi),
        peclet_at_free_diffusion=peclet,
        diffusion_for_peclet_one_micron2_per_min=d_star,
    )
