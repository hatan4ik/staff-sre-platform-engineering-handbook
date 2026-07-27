from __future__ import annotations

import pathlib
import sys
import unittest

LAB_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR))

from autoscaling_sim import (  # noqa: E402
    AutoscalingError,
    CapacityInput,
    HPAInput,
    calculate_hpa,
    simulate_capacity_realization,
)


class HPATests(unittest.TestCase):
    def test_expected_cpu_formula(self) -> None:
        result = calculate_hpa(
            HPAInput(
                current_replicas=10,
                average_usage_millicores=900,
                average_request_millicores=1_000,
                target_utilization_percent=60,
            )
        )
        self.assertEqual(result.current_utilization_percent, 90.0)
        self.assertEqual(result.desired_replicas, 15)

    def test_oversized_request_suppresses_scale_up(self) -> None:
        result = calculate_hpa(
            HPAInput(
                current_replicas=10,
                average_usage_millicores=900,
                average_request_millicores=4_000,
                target_utilization_percent=60,
            )
        )
        self.assertEqual(result.current_utilization_percent, 22.5)
        self.assertLess(result.desired_replicas, 10)

    def test_max_replicas_caps_output(self) -> None:
        result = calculate_hpa(
            HPAInput(
                current_replicas=10,
                average_usage_millicores=2_400,
                average_request_millicores=1_000,
                target_utilization_percent=60,
                max_replicas=25,
            )
        )
        self.assertEqual(result.raw_desired_replicas, 40)
        self.assertEqual(result.desired_replicas, 25)
        self.assertTrue(result.scaling_limited)
        self.assertEqual(result.reason, "max-replicas-limited")

    def test_scale_up_policy_can_limit_growth(self) -> None:
        result = calculate_hpa(
            HPAInput(
                current_replicas=10,
                average_usage_millicores=1_200,
                average_request_millicores=1_000,
                target_utilization_percent=60,
                max_replicas=100,
                max_scale_up_replicas=4,
            )
        )
        self.assertEqual(result.raw_desired_replicas, 20)
        self.assertEqual(result.desired_replicas, 14)
        self.assertTrue(result.scaling_limited)
        self.assertEqual(result.reason, "scale-up-rate-limited")

    def test_missing_request_is_invalid(self) -> None:
        with self.assertRaisesRegex(AutoscalingError, "CPU request must be positive"):
            calculate_hpa(
                HPAInput(
                    current_replicas=10,
                    average_usage_millicores=900,
                    average_request_millicores=0,
                    target_utilization_percent=60,
                )
            )


class CapacityRealizationTests(unittest.TestCase):
    def base(self, **overrides: object) -> CapacityInput:
        values: dict[str, object] = {
            "demand_rps": 7_000.0,
            "current_ready_replicas": 10,
            "desired_replicas": 15,
            "safe_rps_per_pod": 500.0,
            "warm_pod_slots": 0,
            "pods_per_new_node": 10,
            "metric_delay_seconds": 15.0,
            "hpa_reconcile_seconds": 15.0,
            "workload_controller_seconds": 2.0,
            "node_decision_seconds": 0.0,
            "node_launch_seconds": 90.0,
            "pod_startup_seconds": 20.0,
            "target_health_seconds": 15.0,
        }
        values.update(overrides)
        return CapacityInput(**values)  # type: ignore[arg-type]

    def test_cold_capacity_requires_node_wave(self) -> None:
        result = simulate_capacity_realization(self.base())
        self.assertTrue(result.recovered)
        self.assertEqual(result.nodes_requested, 1)
        self.assertEqual(result.bottleneck, "node-provisioning-and-pod-startup")
        self.assertEqual(result.recovery_seconds, 157.0)

    def test_warm_capacity_recovers_faster(self) -> None:
        cold = simulate_capacity_realization(self.base())
        warm = simulate_capacity_realization(self.base(warm_pod_slots=5))
        self.assertTrue(warm.recovered)
        self.assertEqual(warm.nodes_requested, 0)
        self.assertEqual(warm.bottleneck, "warm-pod-startup-and-target-health")
        self.assertEqual(warm.recovery_seconds, 67.0)
        self.assertLess(warm.recovery_seconds or 0, cold.recovery_seconds or 0)

    def test_dependency_cap_prevents_sli_recovery(self) -> None:
        result = simulate_capacity_realization(
            self.base(
                desired_replicas=20,
                warm_pod_slots=10,
                dependency_capacity_rps=6_000.0,
            )
        )
        self.assertFalse(result.recovered)
        self.assertTrue(result.dependency_limited)
        self.assertEqual(result.bottleneck, "downstream-dependency-capacity")
        self.assertEqual(result.final_application_capacity_rps, 10_000.0)
        self.assertEqual(result.final_effective_capacity_rps, 6_000.0)

    def test_desired_replica_count_can_be_insufficient(self) -> None:
        result = simulate_capacity_realization(
            self.base(demand_rps=8_000.0, desired_replicas=15, warm_pod_slots=5)
        )
        self.assertFalse(result.recovered)
        self.assertEqual(result.bottleneck, "desired-replica-capacity-insufficient")

    def test_existing_capacity_can_already_be_sufficient(self) -> None:
        result = simulate_capacity_realization(
            self.base(demand_rps=4_000.0, desired_replicas=10)
        )
        self.assertTrue(result.recovered)
        self.assertEqual(result.recovery_seconds, 0.0)
        self.assertEqual(result.bottleneck, "none-current-capacity-sufficient")


if __name__ == "__main__":
    unittest.main()
