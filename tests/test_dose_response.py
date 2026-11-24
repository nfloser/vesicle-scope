import math
import unittest

from vesiclescope.domain import (
    BiologicalExposure,
    EvidenceCategory,
    ExposureTarget,
    ScientificParameter,
)
from vesiclescope.dose_response import (
    DoseResponseTarget,
    EffectCompartmentDoseResponse,
    dose_response_rate_schedule,
    effect_concentration,
    rate_multiplier,
    weakest_evidence,
)


def p(identifier, value, unit, evidence=EvidenceCategory.SYNTHETIC_BENCHMARK):
    return ScientificParameter(
        identifier=identifier,
        scientific_name=identifier,
        value=value,
        unit=unit,
        evidence=evidence,
        limitations=("Synthetic verification input; not a biological default.",),
    )


def response(ke0=0.05, emax=1.0, ec50=50.0, hill=1.0, baseline=0.0, target=DoseResponseTarget.RELEASE_RATE):
    return EffectCompartmentDoseResponse(
        target=target,
        ke0=p("dr.ke0", ke0, "1/min"),
        emax=p("dr.emax", emax, "1"),
        ec50=p("dr.ec50", ec50, "nM"),
        hill=p("dr.hill", hill, "1"),
        baseline_concentration=p("dr.baseline", baseline, "nM"),
    )


def exposure(concentration=100.0, start=10.0, end=70.0, unit="nM"):
    return BiologicalExposure(
        identifier="synthetic-pulse",
        compound_name="synthetic glucocorticoid",
        concentration=p("exposure.concentration", concentration, unit),
        target=ExposureTarget.DONOR_CELL_POPULATION,
        start_min=start,
        end_min=end,
        evidence=EvidenceCategory.SYNTHETIC_BENCHMARK,
        limitations=("Synthetic.",),
    )


class EffectCompartmentTests(unittest.TestCase):
    def test_effect_concentration_matches_closed_form(self) -> None:
        r, e = response(), exposure()
        c, k = 100.0, 0.05
        self.assertEqual(effect_concentration(r, e, 5.0, duration_min=120.0), 0.0)
        at_40 = effect_concentration(r, e, 40.0, duration_min=120.0)
        self.assertAlmostEqual(at_40, c * (1 - math.exp(-k * 30.0)), places=10)
        at_70 = c * (1 - math.exp(-k * 60.0))
        at_100 = effect_concentration(r, e, 100.0, duration_min=120.0)
        self.assertAlmostEqual(at_100, at_70 * math.exp(-k * 30.0), places=10)

    def test_no_exposure_gives_unit_multiplier(self) -> None:
        r = response(baseline=20.0)
        for t in (0.0, 30.0, 119.0):
            self.assertAlmostEqual(
                rate_multiplier(r, exposure(concentration=0.0), t, duration_min=120.0), 1.0
            )

    def test_long_exposure_reaches_steady_hill_ratio(self) -> None:
        r = response(ke0=5.0, emax=2.0, ec50=50.0, hill=2.0, baseline=10.0)
        m = rate_multiplier(r, exposure(start=0.0, end=600.0), 300.0, duration_min=600.0)
        h = lambda c: c**2 / (50.0**2 + c**2)  # noqa: E731
        self.assertAlmostEqual(m, (1 + 2 * h(110.0)) / (1 + 2 * h(10.0)), places=9)

    def test_delay_lags_exposure(self) -> None:
        slow, fast = response(ke0=0.01), response(ke0=1.0)
        e = exposure()
        self.assertLess(
            rate_multiplier(slow, e, 20.0, duration_min=120.0),
            rate_multiplier(fast, e, 20.0, duration_min=120.0),
        )
        # after the pulse the slow compartment still carries more effect
        self.assertGreater(
            rate_multiplier(slow, e, 110.0, duration_min=120.0),
            rate_multiplier(fast, e, 110.0, duration_min=120.0),
        )

    def test_inhibition_lowers_rate(self) -> None:
        r = response(emax=-0.5, target=DoseResponseTarget.UPTAKE_RATE)
        self.assertLess(rate_multiplier(r, exposure(), 60.0, duration_min=120.0), 1.0)

    def test_validation(self) -> None:
        with self.assertRaises(ValueError):
            response(emax=-1.0)
        with self.assertRaises(ValueError):
            EffectCompartmentDoseResponse(
                target=DoseResponseTarget.RELEASE_RATE,
                ke0=p("k", 0.1, "1/h"),
                emax=p("e", 1.0, "1"),
                ec50=p("c", 1.0, "nM"),
                hill=p("n", 1.0, "1"),
                baseline_concentration=p("b", 0.0, "nM"),
            )
        with self.assertRaises(ValueError):
            dose_response_rate_schedule(
                response(), exposure(unit="ug/dL"), duration_min=120.0, segment_min=10.0
            )


class ScheduleTests(unittest.TestCase):
    def test_schedule_preserves_multiplier_integral(self) -> None:
        r, e = response(ke0=0.08, emax=1.5, hill=2.0, baseline=5.0), exposure()
        schedule = dose_response_rate_schedule(r, e, duration_min=120.0, segment_min=10.0)
        self.assertEqual(len(schedule.segments), 12)
        steps = 24000
        h = 120.0 / steps
        reference = h * sum(
            (0.5 if i in (0, steps) else 1.0)
            * rate_multiplier(r, e, i * h, duration_min=120.0)
            for i in range(steps + 1)
        )
        self.assertAlmostEqual(schedule.integral(0.0, 120.0), reference, places=4)
        self.assertEqual(schedule.segments[0].multiplier, 1.0)
        self.assertIn("synthetic-pulse", schedule.derivation)

    def test_schedule_inherits_weakest_evidence(self) -> None:
        r = response()
        schedule = dose_response_rate_schedule(r, exposure(), duration_min=120.0, segment_min=10.0)
        self.assertEqual(schedule.evidence, EvidenceCategory.SYNTHETIC_BENCHMARK)
        self.assertEqual(
            weakest_evidence((EvidenceCategory.FITTED, EvidenceCategory.ASSUMED)),
            EvidenceCategory.ASSUMED,
        )

    def test_segment_must_tile_duration(self) -> None:
        with self.assertRaises(ValueError):
            dose_response_rate_schedule(response(), exposure(), duration_min=120.0, segment_min=7.0)


if __name__ == "__main__":
    unittest.main()
