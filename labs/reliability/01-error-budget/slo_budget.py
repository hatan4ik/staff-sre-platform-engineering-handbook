from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable


class SLOError(ValueError):
    """Raised when an SLO or event window is invalid."""


@dataclass(frozen=True)
class SLOPolicy:
    objective: float
    compliance_window_seconds: float


@dataclass(frozen=True)
class EventWindow:
    valid_events: int
    bad_events: int
    unknown_events: int = 0
    excluded_events: int = 0
    window_seconds: float = 300.0


@dataclass(frozen=True)
class BudgetResult:
    objective: float
    allowed_bad_fraction: float
    allowed_bad_events: float
    observed_bad_fraction: float
    burn_rate: float
    budget_remaining_events: float
    budget_remaining_percent: float
    budget_consumed_percent: float
    unknown_fraction_of_observed: float
    approximate_time_to_exhaustion_seconds: float | None
    status: str


@dataclass(frozen=True)
class BurnAlertPolicy:
    fast_burn_threshold: float = 14.4
    fast_short_window_seconds: float = 300.0
    fast_long_window_seconds: float = 3_600.0
    slow_burn_threshold: float = 6.0
    slow_short_window_seconds: float = 1_800.0
    slow_long_window_seconds: float = 21_600.0


@dataclass(frozen=True)
class AlertDecision:
    severity: str
    reason: str
    fast_short_burn: float
    fast_long_burn: float
    slow_short_burn: float
    slow_long_burn: float


@dataclass(frozen=True)
class CohortObservation:
    name: str
    window: EventWindow


@dataclass(frozen=True)
class CohortResult:
    name: str
    failure_rate: float
    burn_rate: float
    status: str


def _validate_policy(policy: SLOPolicy) -> None:
    if not 0 < policy.objective < 1:
        raise SLOError("objective must be between 0 and 1")
    if policy.compliance_window_seconds <= 0:
        raise SLOError("compliance window must be positive")


def _validate_window(window: EventWindow) -> None:
    integer_values = {
        "valid_events": window.valid_events,
        "bad_events": window.bad_events,
        "unknown_events": window.unknown_events,
        "excluded_events": window.excluded_events,
    }
    for name, value in integer_values.items():
        if value < 0:
            raise SLOError(f"{name} cannot be negative")
    if window.bad_events > window.valid_events:
        raise SLOError("bad_events cannot exceed valid_events")
    if window.valid_events == 0:
        raise SLOError("valid_events must be positive")
    if window.window_seconds <= 0:
        raise SLOError("window_seconds must be positive")


def calculate_budget(policy: SLOPolicy, window: EventWindow) -> BudgetResult:
    _validate_policy(policy)
    _validate_window(window)

    allowed_bad_fraction = 1.0 - policy.objective
    allowed_bad_events = window.valid_events * allowed_bad_fraction
    observed_bad_fraction = window.bad_events / window.valid_events
    burn_rate = observed_bad_fraction / allowed_bad_fraction
    budget_remaining = allowed_bad_events - window.bad_events

    if allowed_bad_events == 0:
        raise SLOError("allowed bad event count must be positive")

    remaining_percent = budget_remaining / allowed_bad_events * 100.0
    consumed_percent = window.bad_events / allowed_bad_events * 100.0
    observed_total = (
        window.valid_events + window.unknown_events + window.excluded_events
    )
    unknown_fraction = (
        window.unknown_events / observed_total if observed_total else 0.0
    )

    if burn_rate == 0:
        time_to_exhaustion = None
    else:
        time_to_exhaustion = policy.compliance_window_seconds / burn_rate

    if budget_remaining < 0:
        status = "EXHAUSTED"
    elif remaining_percent <= 10:
        status = "CRITICAL"
    elif remaining_percent <= 25:
        status = "AT_RISK"
    else:
        status = "HEALTHY"

    return BudgetResult(
        objective=policy.objective,
        allowed_bad_fraction=round(allowed_bad_fraction, 12),
        allowed_bad_events=round(allowed_bad_events, 3),
        observed_bad_fraction=round(observed_bad_fraction, 12),
        burn_rate=round(burn_rate, 6),
        budget_remaining_events=round(budget_remaining, 3),
        budget_remaining_percent=round(remaining_percent, 3),
        budget_consumed_percent=round(consumed_percent, 3),
        unknown_fraction_of_observed=round(unknown_fraction, 6),
        approximate_time_to_exhaustion_seconds=(
            None if time_to_exhaustion is None else round(time_to_exhaustion, 3)
        ),
        status=status,
    )


def evaluate_multiwindow_alert(
    policy: BurnAlertPolicy,
    *,
    fast_short_burn: float,
    fast_long_burn: float,
    slow_short_burn: float,
    slow_long_burn: float,
) -> AlertDecision:
    burns = {
        "fast_short_burn": fast_short_burn,
        "fast_long_burn": fast_long_burn,
        "slow_short_burn": slow_short_burn,
        "slow_long_burn": slow_long_burn,
    }
    for name, value in burns.items():
        if value < 0 or not math.isfinite(value):
            raise SLOError(f"{name} must be a finite nonnegative number")

    if (
        fast_short_burn >= policy.fast_burn_threshold
        and fast_long_burn >= policy.fast_burn_threshold
    ):
        severity = "PAGE"
        reason = "fast-burn-pair"
    elif (
        slow_short_burn >= policy.slow_burn_threshold
        and slow_long_burn >= policy.slow_burn_threshold
    ):
        severity = "TICKET"
        reason = "slow-burn-pair"
    else:
        severity = "NONE"
        reason = "paired-window-threshold-not-met"

    return AlertDecision(
        severity=severity,
        reason=reason,
        fast_short_burn=fast_short_burn,
        fast_long_burn=fast_long_burn,
        slow_short_burn=slow_short_burn,
        slow_long_burn=slow_long_burn,
    )


def analyze_cohorts(
    policy: SLOPolicy,
    cohorts: Iterable[CohortObservation],
    *,
    protected_burn_threshold: float = 1.0,
) -> list[CohortResult]:
    if protected_burn_threshold < 0:
        raise SLOError("protected_burn_threshold cannot be negative")

    results: list[CohortResult] = []
    for cohort in cohorts:
        budget = calculate_budget(policy, cohort.window)
        status = (
            "VIOLATING"
            if budget.burn_rate > protected_burn_threshold
            else "WITHIN_POLICY"
        )
        results.append(
            CohortResult(
                name=cohort.name,
                failure_rate=budget.observed_bad_fraction,
                burn_rate=budget.burn_rate,
                status=status,
            )
        )
    return results


def aggregate_windows(windows: Iterable[EventWindow]) -> EventWindow:
    items = list(windows)
    if not items:
        raise SLOError("at least one window is required")
    for item in items:
        _validate_window(item)

    return EventWindow(
        valid_events=sum(item.valid_events for item in items),
        bad_events=sum(item.bad_events for item in items),
        unknown_events=sum(item.unknown_events for item in items),
        excluded_events=sum(item.excluded_events for item in items),
        window_seconds=max(item.window_seconds for item in items),
    )


def release_decision(
    budget: BudgetResult,
    alert: AlertDecision,
    cohorts: Iterable[CohortResult],
    *,
    unknown_limit: float = 0.001,
) -> str:
    cohort_list = list(cohorts)
    if budget.unknown_fraction_of_observed > unknown_limit:
        return "PAUSE_TELEMETRY_UNTRUSTED"
    if alert.severity == "PAGE":
        return "STOP_AND_MITIGATE_FAST_BURN"
    if any(item.status == "VIOLATING" for item in cohort_list):
        return "PAUSE_PROTECTED_COHORT_REGRESSION"
    if budget.status in {"EXHAUSTED", "CRITICAL"}:
        return "FREEZE_RISKY_CHANGES"
    if alert.severity == "TICKET" or budget.status == "AT_RISK":
        return "REDUCE_EXPOSURE_AND_PRIORITIZE_RELIABILITY"
    return "PROCEED_WITH_NORMAL_GUARDRAILS"


def run_demo() -> int:
    policy = SLOPolicy(
        objective=0.9995,
        compliance_window_seconds=28 * 24 * 60 * 60,
    )

    healthy_majority = CohortObservation(
        name="cached-read-majority",
        window=EventWindow(valid_events=1_000_000_000, bad_events=10_000),
    )
    critical_minority = CohortObservation(
        name="critical-write-path",
        window=EventWindow(valid_events=1_000_000, bad_events=20_000),
    )

    aggregate = aggregate_windows(
        [healthy_majority.window, critical_minority.window]
    )
    aggregate_result = calculate_budget(policy, aggregate)
    cohort_results = analyze_cohorts(
        policy,
        [healthy_majority, critical_minority],
    )

    alert = evaluate_multiwindow_alert(
        BurnAlertPolicy(),
        fast_short_burn=18.0,
        fast_long_burn=16.0,
        slow_short_burn=8.0,
        slow_long_burn=7.0,
    )

    output = {
        "policy": asdict(policy),
        "aggregate": asdict(aggregate_result),
        "cohorts": [asdict(item) for item in cohort_results],
        "alert": asdict(alert),
        "release_decision": release_decision(
            aggregate_result,
            alert,
            cohort_results,
        ),
    }
    print(json.dumps(output, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safe SLO, error-budget, burn-rate, and cohort simulator"
    )
    parser.add_argument("--demo", action="store_true", help="run built-in scenario")
    args = parser.parse_args()
    if args.demo:
        return run_demo()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
