from __future__ import annotations

import pathlib
import sys
import unittest

LAB_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR))

from slo_budget import (  # noqa: E402
    AlertDecision,
    BurnAlertPolicy,
    CohortObservation,
    EventWindow,
    SLOError,
    SLOPolicy,
    aggregate_windows,
    analyze_cohorts,
    calculate_budget,
    evaluate_multiwindow_alert,
    release_decision,
)


class BudgetMathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SLOPolicy(
            objective=0.9995,
            compliance_window_seconds=28 * 24 * 60 * 60,
        )

    def test_budget_math(self) -> None:
        result = calculate_budget(
            self.policy,
            EventWindow(valid_events=2_000_000_000, bad_events=250_000),
        )
        self.assertEqual(result.allowed_bad_events, 1_000_000.0)
        self.assertEqual(result.budget_remaining_events, 750_000.0)
        self.assertEqual(result.budget_remaining_percent, 75.0)
        self.assertEqual(result.budget_consumed_percent, 25.0)
        self.assertEqual(result.status, "HEALTHY")

    def test_ten_x_burn(self) -> None:
        policy = SLOPolicy(
            objective=0.999,
            compliance_window_seconds=30 * 24 * 60 * 60,
        )
        result = calculate_budget(
            policy,
            EventWindow(valid_events=100_000, bad_events=1_000),
        )
        self.assertEqual(result.burn_rate, 10.0)
        self.assertEqual(
            result.approximate_time_to_exhaustion_seconds,
            3 * 24 * 60 * 60,
        )

    def test_unknown_rate_is_explicit(self) -> None:
        result = calculate_budget(
            self.policy,
            EventWindow(
                valid_events=99_000,
                bad_events=10,
                unknown_events=1_000,
            ),
        )
        self.assertEqual(result.unknown_fraction_of_observed, 0.01)

    def test_invalid_objective_is_rejected(self) -> None:
        with self.assertRaisesRegex(SLOError, "objective must be between 0 and 1"):
            calculate_budget(
                SLOPolicy(objective=1.0, compliance_window_seconds=100),
                EventWindow(valid_events=100, bad_events=0),
            )

    def test_bad_events_cannot_exceed_valid(self) -> None:
        with self.assertRaisesRegex(SLOError, "bad_events cannot exceed valid_events"):
            calculate_budget(
                self.policy,
                EventWindow(valid_events=100, bad_events=101),
            )


class BurnAlertTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = BurnAlertPolicy()

    def test_fast_burn_requires_both_windows(self) -> None:
        decision = evaluate_multiwindow_alert(
            self.policy,
            fast_short_burn=20.0,
            fast_long_burn=2.0,
            slow_short_burn=2.0,
            slow_long_burn=2.0,
        )
        self.assertEqual(decision.severity, "NONE")

    def test_fast_burn_pages(self) -> None:
        decision = evaluate_multiwindow_alert(
            self.policy,
            fast_short_burn=20.0,
            fast_long_burn=15.0,
            slow_short_burn=8.0,
            slow_long_burn=7.0,
        )
        self.assertEqual(decision.severity, "PAGE")
        self.assertEqual(decision.reason, "fast-burn-pair")

    def test_slow_burn_creates_ticket(self) -> None:
        decision = evaluate_multiwindow_alert(
            self.policy,
            fast_short_burn=3.0,
            fast_long_burn=3.0,
            slow_short_burn=7.0,
            slow_long_burn=6.5,
        )
        self.assertEqual(decision.severity, "TICKET")


class CohortPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = SLOPolicy(
            objective=0.9995,
            compliance_window_seconds=28 * 24 * 60 * 60,
        )

    def test_aggregate_can_hide_critical_cohort(self) -> None:
        majority = CohortObservation(
            name="majority",
            window=EventWindow(valid_events=1_000_000_000, bad_events=10_000),
        )
        minority = CohortObservation(
            name="critical-minority",
            window=EventWindow(valid_events=1_000_000, bad_events=20_000),
        )

        aggregate = calculate_budget(
            self.policy,
            aggregate_windows([majority.window, minority.window]),
        )
        cohorts = analyze_cohorts(self.policy, [majority, minority])
        statuses = {item.name: item.status for item in cohorts}

        self.assertEqual(aggregate.status, "HEALTHY")
        self.assertEqual(statuses["majority"], "WITHIN_POLICY")
        self.assertEqual(statuses["critical-minority"], "VIOLATING")

    def test_protected_cohort_pauses_release(self) -> None:
        budget = calculate_budget(
            self.policy,
            EventWindow(valid_events=1_000_000, bad_events=100),
        )
        alert = AlertDecision(
            severity="NONE",
            reason="paired-window-threshold-not-met",
            fast_short_burn=0.2,
            fast_long_burn=0.2,
            slow_short_burn=0.2,
            slow_long_burn=0.2,
        )
        cohorts = analyze_cohorts(
            self.policy,
            [
                CohortObservation(
                    name="protected-write",
                    window=EventWindow(valid_events=10_000, bad_events=100),
                )
            ],
        )
        self.assertEqual(
            release_decision(budget, alert, cohorts),
            "PAUSE_PROTECTED_COHORT_REGRESSION",
        )

    def test_unknown_telemetry_takes_precedence(self) -> None:
        budget = calculate_budget(
            self.policy,
            EventWindow(
                valid_events=99_000,
                bad_events=1,
                unknown_events=1_000,
            ),
        )
        alert = AlertDecision(
            severity="NONE",
            reason="paired-window-threshold-not-met",
            fast_short_burn=0.0,
            fast_long_burn=0.0,
            slow_short_burn=0.0,
            slow_long_burn=0.0,
        )
        self.assertEqual(
            release_decision(budget, alert, []),
            "PAUSE_TELEMETRY_UNTRUSTED",
        )


if __name__ == "__main__":
    unittest.main()
