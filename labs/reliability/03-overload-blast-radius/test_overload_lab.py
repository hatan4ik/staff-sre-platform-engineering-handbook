#!/usr/bin/env python3

import unittest

from overload_lab import (
    AdmissionController,
    Cell,
    Request,
    layered_retry_attempts,
    plan_failover,
    plan_replay,
    retry_budget_attempts,
    run_scenario,
)


class AdmissionControllerTests(unittest.TestCase):
    def test_critical_requests_are_evaluated_before_optional(self) -> None:
        controller = AdmissionController(
            capacity_units=4,
            critical_reserve_units=2,
            per_tenant_units=4,
        )
        report = controller.admit(
            [
                Request("o1", "a", "optional", 2),
                Request("c1", "b", "critical", 2),
                Request("o2", "c", "optional", 2),
            ]
        )
        by_id = {item.request_id: item for item in report.decisions}
        self.assertTrue(by_id["c1"].admitted)
        self.assertTrue(by_id["o1"].admitted)
        self.assertFalse(by_id["o2"].admitted)

    def test_per_tenant_limit_prevents_monopoly(self) -> None:
        controller = AdmissionController(
            capacity_units=10,
            critical_reserve_units=4,
            per_tenant_units=3,
        )
        report = controller.admit(
            [
                Request("a1", "tenant-a", "critical", 2),
                Request("a2", "tenant-a", "critical", 2),
                Request("b1", "tenant-b", "critical", 2),
            ]
        )
        by_id = {item.request_id: item for item in report.decisions}
        self.assertTrue(by_id["a1"].admitted)
        self.assertEqual(by_id["a2"].reason, "tenant_limit")
        self.assertTrue(by_id["b1"].admitted)


class RetryTests(unittest.TestCase):
    def test_layered_retries_amplify(self) -> None:
        self.assertEqual(layered_retry_attempts([2, 2, 2]), 27)

    def test_retry_budget_is_bounded(self) -> None:
        self.assertEqual(retry_budget_attempts(100, 0.20), 120)


class FailoverTests(unittest.TestCase):
    def test_insufficient_headroom_blocks_failover(self) -> None:
        destination = Cell("b", capacity=100, baseline_load=75)
        decision = plan_failover(
            source_traffic=25,
            destination=destination,
            safety_margin=0.20,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "insufficient_headroom")

    def test_sufficient_headroom_allows_failover(self) -> None:
        destination = Cell("b", capacity=100, baseline_load=50)
        decision = plan_failover(
            source_traffic=25,
            destination=destination,
            safety_margin=0.20,
        )
        self.assertTrue(decision.allowed)


class ReplayTests(unittest.TestCase):
    def test_expiry_and_pacing(self) -> None:
        plan = plan_replay(
            [10, 20, 60, 120, 121, 600],
            max_age_seconds=120,
            batch_size=3,
        )
        self.assertEqual(plan.expired, 2)
        self.assertEqual(plan.replayed, 4)
        self.assertEqual(plan.batches, (3, 1))


class ScenarioTests(unittest.TestCase):
    def test_full_scenario(self) -> None:
        result = run_scenario()
        self.assertTrue(result["passed"])
        self.assertTrue(all(result["invariants"].values()))


if __name__ == "__main__":
    unittest.main()
