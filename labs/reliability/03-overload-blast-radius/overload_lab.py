#!/usr/bin/env python3
"""Deterministic overload, retry-budget, and blast-radius lab.

The lab uses only the Python standard library. It demonstrates:
- layered retry amplification;
- priority and per-tenant admission control;
- cell isolation;
- failover headroom checks;
- paced backlog recovery.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Request:
    request_id: str
    tenant: str
    priority: str  # "critical" or "optional"
    work_units: int = 1

    def __post_init__(self) -> None:
        if self.priority not in {"critical", "optional"}:
            raise ValueError(f"unsupported priority: {self.priority}")
        if self.work_units <= 0:
            raise ValueError("work_units must be positive")


@dataclass(frozen=True)
class AdmissionDecision:
    request_id: str
    admitted: bool
    reason: str


@dataclass(frozen=True)
class AdmissionReport:
    decisions: tuple[AdmissionDecision, ...]
    admitted_critical: int
    admitted_optional: int
    rejected_critical: int
    rejected_optional: int
    consumed_units: int


class AdmissionController:
    """Priority-aware, bounded admission with tenant fairness.

    Critical requests are evaluated first. Optional requests may only consume
    capacity that remains after preserving the configured critical reserve.
    """

    def __init__(
        self,
        *,
        capacity_units: int,
        critical_reserve_units: int,
        per_tenant_units: int,
    ) -> None:
        if capacity_units <= 0:
            raise ValueError("capacity_units must be positive")
        if not 0 <= critical_reserve_units <= capacity_units:
            raise ValueError("critical_reserve_units must be between 0 and capacity")
        if per_tenant_units <= 0:
            raise ValueError("per_tenant_units must be positive")
        self.capacity_units = capacity_units
        self.critical_reserve_units = critical_reserve_units
        self.per_tenant_units = per_tenant_units

    def admit(self, requests: Sequence[Request]) -> AdmissionReport:
        ordered = sorted(
            enumerate(requests),
            key=lambda pair: (0 if pair[1].priority == "critical" else 1, pair[0]),
        )
        consumed = 0
        tenant_consumed: dict[str, int] = {}
        decisions: list[AdmissionDecision] = []

        for _, request in ordered:
            tenant_used = tenant_consumed.get(request.tenant, 0)
            if tenant_used + request.work_units > self.per_tenant_units:
                decisions.append(
                    AdmissionDecision(request.request_id, False, "tenant_limit")
                )
                continue

            remaining = self.capacity_units - consumed
            if request.work_units > remaining:
                decisions.append(
                    AdmissionDecision(request.request_id, False, "capacity_exhausted")
                )
                continue

            if request.priority == "optional":
                optional_ceiling = self.capacity_units - self.critical_reserve_units
                if consumed + request.work_units > optional_ceiling:
                    decisions.append(
                        AdmissionDecision(request.request_id, False, "critical_reserve")
                    )
                    continue

            consumed += request.work_units
            tenant_consumed[request.tenant] = tenant_used + request.work_units
            decisions.append(AdmissionDecision(request.request_id, True, "admitted"))

        by_id = {decision.request_id: decision for decision in decisions}
        stable = tuple(by_id[request.request_id] for request in requests)

        def count(priority: str, admitted: bool) -> int:
            return sum(
                1
                for request in requests
                if request.priority == priority
                and by_id[request.request_id].admitted is admitted
            )

        return AdmissionReport(
            decisions=stable,
            admitted_critical=count("critical", True),
            admitted_optional=count("optional", True),
            rejected_critical=count("critical", False),
            rejected_optional=count("optional", False),
            consumed_units=consumed,
        )


@dataclass(frozen=True)
class Cell:
    name: str
    capacity: int
    baseline_load: int
    healthy: bool = True

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if not 0 <= self.baseline_load <= self.capacity:
            raise ValueError("baseline_load must be between 0 and capacity")

    @property
    def headroom(self) -> int:
        return self.capacity - self.baseline_load if self.healthy else 0


@dataclass(frozen=True)
class FailoverDecision:
    allowed: bool
    reason: str
    required_capacity: int
    destination_headroom: int


def plan_failover(
    *,
    source_traffic: int,
    destination: Cell,
    safety_margin: float = 0.20,
) -> FailoverDecision:
    if source_traffic < 0:
        raise ValueError("source_traffic must be non-negative")
    if safety_margin < 0:
        raise ValueError("safety_margin must be non-negative")

    required = int(source_traffic * (1 + safety_margin) + 0.999999)
    if not destination.healthy:
        return FailoverDecision(False, "destination_unhealthy", required, 0)
    if destination.headroom < required:
        return FailoverDecision(
            False,
            "insufficient_headroom",
            required,
            destination.headroom,
        )
    return FailoverDecision(True, "safe_to_shift", required, destination.headroom)


def layered_retry_attempts(retries_per_layer: Iterable[int]) -> int:
    """Return worst-case attempts for independently retrying layers.

    A value of 2 means two retries plus the original attempt, or three total
    attempts for that layer.
    """

    attempts = 1
    for retries in retries_per_layer:
        if retries < 0:
            raise ValueError("retry count must be non-negative")
        attempts *= retries + 1
    return attempts


def retry_budget_attempts(original_requests: int, budget_fraction: float) -> int:
    if original_requests < 0:
        raise ValueError("original_requests must be non-negative")
    if not 0 <= budget_fraction <= 1:
        raise ValueError("budget_fraction must be between 0 and 1")
    return original_requests + int(original_requests * budget_fraction)


@dataclass(frozen=True)
class ReplayPlan:
    original_backlog: int
    expired: int
    replayed: int
    batches: tuple[int, ...]


def plan_replay(
    backlog_ages_seconds: Sequence[int],
    *,
    max_age_seconds: int,
    batch_size: int,
) -> ReplayPlan:
    if max_age_seconds < 0:
        raise ValueError("max_age_seconds must be non-negative")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    live = [age for age in backlog_ages_seconds if age <= max_age_seconds]
    expired = len(backlog_ages_seconds) - len(live)
    batches = tuple(
        min(batch_size, len(live) - offset)
        for offset in range(0, len(live), batch_size)
    )
    return ReplayPlan(
        original_backlog=len(backlog_ages_seconds),
        expired=expired,
        replayed=len(live),
        batches=batches,
    )


def run_scenario() -> dict[str, object]:
    requests = [
        Request("c1", "tenant-a", "critical", 2),
        Request("c2", "tenant-b", "critical", 2),
        Request("o1", "tenant-a", "optional", 2),
        Request("o2", "tenant-c", "optional", 2),
        Request("o3", "tenant-d", "optional", 2),
    ]
    controller = AdmissionController(
        capacity_units=8,
        critical_reserve_units=4,
        per_tenant_units=3,
    )
    admission = controller.admit(requests)

    destination = Cell("cell-b", capacity=100, baseline_load=70)
    unsafe_failover = plan_failover(
        source_traffic=30,
        destination=destination,
        safety_margin=0.20,
    )
    safe_failover = plan_failover(
        source_traffic=20,
        destination=destination,
        safety_margin=0.20,
    )

    retry_storm = layered_retry_attempts([2, 2, 2])
    budgeted_attempts = retry_budget_attempts(100, 0.20)
    replay = plan_replay(
        [10, 20, 30, 60, 120, 600],
        max_age_seconds=120,
        batch_size=2,
    )

    invariants = {
        "critical_requests_preserved": admission.rejected_critical == 0,
        "optional_work_shed": admission.rejected_optional >= 1,
        "tenant_fairness_enforced": any(
            decision.reason == "tenant_limit" for decision in admission.decisions
        ),
        "unsafe_failover_blocked": not unsafe_failover.allowed,
        "safe_failover_allowed": safe_failover.allowed,
        "layered_retries_amplify": retry_storm == 27,
        "retry_budget_is_bounded": budgeted_attempts == 120,
        "expired_backlog_removed": replay.expired == 1,
        "replay_is_paced": replay.batches == (2, 2, 1),
    }

    return {
        "admission": {
            **asdict(admission),
            "decisions": [asdict(item) for item in admission.decisions],
        },
        "unsafe_failover": asdict(unsafe_failover),
        "safe_failover": asdict(safe_failover),
        "layered_retry_attempts": retry_storm,
        "budgeted_total_attempts": budgeted_attempts,
        "replay": asdict(replay),
        "invariants": invariants,
        "passed": all(invariants.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of a human summary",
    )
    args = parser.parse_args()
    result = run_scenario()

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Overload and blast-radius reliability lab")
        print(f"passed: {result['passed']}")
        print(f"layered retry attempts: {result['layered_retry_attempts']}")
        print(f"budgeted total attempts: {result['budgeted_total_attempts']}")
        for name, passed in result["invariants"].items():
            print(f"- {name}: {'PASS' if passed else 'FAIL'}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
