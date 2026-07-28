#!/usr/bin/env python3
"""Deterministic overload-control simulator.

The model compares an unbounded retry design with bounded admission,
priority, and retry budgets. It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    offered_critical: int
    offered_optional: int
    service_capacity: int
    retry_probability_percent: int
    max_retries: int
    critical_reservation_percent: int


@dataclass
class Result:
    admitted_critical: int = 0
    admitted_optional: int = 0
    rejected_critical: int = 0
    rejected_optional: int = 0
    attempts: int = 0
    useful_completions: int = 0
    retries: int = 0

    @property
    def amplification(self) -> float:
        original = self.admitted_critical + self.admitted_optional
        return self.attempts / original if original else 0.0


def deterministic_fail(attempt_number: int, probability_percent: int) -> bool:
    """Return a reproducible pseudo-failure without randomness."""
    return ((attempt_number * 37 + 11) % 100) < probability_percent


def run(s: Scenario, controlled: bool) -> Result:
    result = Result()

    if controlled:
        critical_capacity = max(
            0, min(s.service_capacity, s.service_capacity * s.critical_reservation_percent // 100)
        )
        result.admitted_critical = min(s.offered_critical, critical_capacity)
        remaining = s.service_capacity - result.admitted_critical
        result.admitted_optional = min(s.offered_optional, max(0, remaining))
    else:
        # First-come workload mixing: optional work may consume capacity needed by critical traffic.
        total = s.offered_critical + s.offered_optional
        result.admitted_critical = (
            s.service_capacity * s.offered_critical // total if total else 0
        )
        result.admitted_optional = min(
            s.offered_optional, s.service_capacity - result.admitted_critical
        )

    result.rejected_critical = s.offered_critical - result.admitted_critical
    result.rejected_optional = s.offered_optional - result.admitted_optional

    original = result.admitted_critical + result.admitted_optional
    attempt_id = 0

    for _ in range(original):
        retries_allowed = s.max_retries if not controlled else min(s.max_retries, 1)
        completed = False
        for retry in range(retries_allowed + 1):
            attempt_id += 1
            result.attempts += 1
            if retry:
                result.retries += 1
            if not deterministic_fail(attempt_id, s.retry_probability_percent):
                completed = True
                break
        if completed:
            result.useful_completions += 1

    return result


def print_result(name: str, r: Result) -> None:
    print(f"\n{name}")
    print("-" * len(name))
    print(f"admitted critical : {r.admitted_critical}")
    print(f"admitted optional : {r.admitted_optional}")
    print(f"rejected critical : {r.rejected_critical}")
    print(f"rejected optional : {r.rejected_optional}")
    print(f"total attempts    : {r.attempts}")
    print(f"retries           : {r.retries}")
    print(f"useful completions: {r.useful_completions}")
    print(f"amplification     : {r.amplification:.2f}x")


def parse_args() -> Scenario:
    parser = argparse.ArgumentParser()
    parser.add_argument("--critical", type=int, default=700)
    parser.add_argument("--optional", type=int, default=900)
    parser.add_argument("--capacity", type=int, default=1000)
    parser.add_argument("--failure-percent", type=int, default=35)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--critical-reservation-percent", type=int, default=80)
    args = parser.parse_args()

    values = vars(args)
    if any(value < 0 for value in values.values()):
        parser.error("all values must be non-negative")
    if args.failure_percent > 100 or args.critical_reservation_percent > 100:
        parser.error("percent values must be between 0 and 100")

    return Scenario(
        offered_critical=args.critical,
        offered_optional=args.optional,
        service_capacity=args.capacity,
        retry_probability_percent=args.failure_percent,
        max_retries=args.max_retries,
        critical_reservation_percent=args.critical_reservation_percent,
    )


def main() -> int:
    scenario = parse_args()
    uncontrolled = run(scenario, controlled=False)
    controlled = run(scenario, controlled=True)

    print("Scenario")
    print("========")
    print(scenario)
    print_result("Uncontrolled retries and mixed traffic", uncontrolled)
    print_result("Bounded admission, priority, and retry budget", controlled)

    print("\nInterpretation")
    print("==============")
    print("The controlled design intentionally rejects optional work earlier,")
    print("protects critical capacity, and bounds retry amplification.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
