from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Any


class AutoscalingError(ValueError):
    """Raised when autoscaling inputs do not form a valid control problem."""


@dataclass(frozen=True)
class HPAInput:
    current_replicas: int
    average_usage_millicores: float
    average_request_millicores: float
    target_utilization_percent: float
    min_replicas: int = 1
    max_replicas: int = 100
    tolerance_percent: float = 10.0
    max_scale_up_replicas: int | None = None


@dataclass(frozen=True)
class HPAResult:
    current_utilization_percent: float
    raw_desired_replicas: int
    desired_replicas: int
    scaling_limited: bool
    reason: str


@dataclass(frozen=True)
class CapacityInput:
    demand_rps: float
    current_ready_replicas: int
    desired_replicas: int
    safe_rps_per_pod: float
    warm_pod_slots: int
    pods_per_new_node: int
    metric_delay_seconds: float = 15.0
    hpa_reconcile_seconds: float = 15.0
    workload_controller_seconds: float = 2.0
    node_decision_seconds: float = 5.0
    node_launch_seconds: float = 90.0
    pod_startup_seconds: float = 20.0
    target_health_seconds: float = 15.0
    dependency_capacity_rps: float | None = None


@dataclass(frozen=True)
class CapacityResult:
    additional_replicas_requested: int
    immediate_replicas: int
    node_backed_replicas: int
    nodes_requested: int
    current_service_capacity_rps: float
    warm_wave_capacity_rps: float
    final_application_capacity_rps: float
    final_effective_capacity_rps: float
    dependency_limited: bool
    recovered: bool
    recovery_seconds: float | None
    bottleneck: str
    timeline: dict[str, float | None]


def calculate_hpa(inputs: HPAInput) -> HPAResult:
    """Calculate a simplified CPU-utilization HPA decision.

    The model intentionally exposes the request denominator, tolerance, min/max
    bounds, and an optional scale-up rate limit. Kubernetes has additional
    damping behavior for missing metrics and not-yet-ready pods; those are
    discussed in the lab documentation rather than hidden in this function.
    """
    if inputs.current_replicas <= 0:
        raise AutoscalingError("current_replicas must be positive")
    if inputs.average_request_millicores <= 0:
        raise AutoscalingError("CPU request must be positive for utilization scaling")
    if inputs.target_utilization_percent <= 0:
        raise AutoscalingError("target utilization must be positive")
    if inputs.min_replicas <= 0:
        raise AutoscalingError("min_replicas must be positive")
    if inputs.max_replicas < inputs.min_replicas:
        raise AutoscalingError("max_replicas must be greater than or equal to min_replicas")
    if inputs.tolerance_percent < 0:
        raise AutoscalingError("tolerance_percent cannot be negative")
    if inputs.max_scale_up_replicas is not None and inputs.max_scale_up_replicas < 0:
        raise AutoscalingError("max_scale_up_replicas cannot be negative")

    utilization = (
        inputs.average_usage_millicores
        / inputs.average_request_millicores
        * 100.0
    )
    ratio = utilization / inputs.target_utilization_percent
    tolerance_ratio = inputs.tolerance_percent / 100.0

    if abs(ratio - 1.0) <= tolerance_ratio:
        raw_desired = inputs.current_replicas
        reason = "within-tolerance"
    else:
        raw_desired = math.ceil(inputs.current_replicas * ratio)
        reason = "metric-ratio"

    bounded = max(inputs.min_replicas, min(raw_desired, inputs.max_replicas))
    scaling_limited = bounded != raw_desired

    if bounded > inputs.current_replicas and inputs.max_scale_up_replicas is not None:
        rate_limited = min(
            bounded,
            inputs.current_replicas + inputs.max_scale_up_replicas,
        )
        if rate_limited != bounded:
            scaling_limited = True
            reason = "scale-up-rate-limited"
        bounded = rate_limited

    if raw_desired > inputs.max_replicas:
        reason = "max-replicas-limited"
    elif raw_desired < inputs.min_replicas:
        reason = "min-replicas-limited"

    return HPAResult(
        current_utilization_percent=round(utilization, 3),
        raw_desired_replicas=raw_desired,
        desired_replicas=bounded,
        scaling_limited=scaling_limited,
        reason=reason,
    )


def simulate_capacity_realization(inputs: CapacityInput) -> CapacityResult:
    """Simulate two capacity waves: warm slots and newly provisioned nodes."""
    numeric_nonnegative = {
        "demand_rps": inputs.demand_rps,
        "safe_rps_per_pod": inputs.safe_rps_per_pod,
        "metric_delay_seconds": inputs.metric_delay_seconds,
        "hpa_reconcile_seconds": inputs.hpa_reconcile_seconds,
        "workload_controller_seconds": inputs.workload_controller_seconds,
        "node_decision_seconds": inputs.node_decision_seconds,
        "node_launch_seconds": inputs.node_launch_seconds,
        "pod_startup_seconds": inputs.pod_startup_seconds,
        "target_health_seconds": inputs.target_health_seconds,
    }
    for name, value in numeric_nonnegative.items():
        if value < 0:
            raise AutoscalingError(f"{name} cannot be negative")

    if inputs.safe_rps_per_pod <= 0:
        raise AutoscalingError("safe_rps_per_pod must be positive")
    if inputs.current_ready_replicas < 0:
        raise AutoscalingError("current_ready_replicas cannot be negative")
    if inputs.desired_replicas < 0:
        raise AutoscalingError("desired_replicas cannot be negative")
    if inputs.warm_pod_slots < 0:
        raise AutoscalingError("warm_pod_slots cannot be negative")
    if inputs.pods_per_new_node <= 0:
        raise AutoscalingError("pods_per_new_node must be positive")
    if inputs.dependency_capacity_rps is not None and inputs.dependency_capacity_rps < 0:
        raise AutoscalingError("dependency_capacity_rps cannot be negative")

    additional = max(inputs.desired_replicas - inputs.current_ready_replicas, 0)
    immediate = min(additional, inputs.warm_pod_slots)
    node_backed = max(additional - immediate, 0)
    nodes_requested = math.ceil(node_backed / inputs.pods_per_new_node) if node_backed else 0

    t0 = 0.0
    t1_metric_available = t0 + inputs.metric_delay_seconds
    t2_desired_changed = t1_metric_available + inputs.hpa_reconcile_seconds
    t3_pods_created = t2_desired_changed + inputs.workload_controller_seconds

    warm_ready = (
        t3_pods_created
        + inputs.pod_startup_seconds
        + inputs.target_health_seconds
        if immediate > 0
        else None
    )

    if node_backed > 0:
        t4_unschedulable = t3_pods_created
        t5_node_requested = t4_unschedulable + inputs.node_decision_seconds
        t6_node_ready = t5_node_requested + inputs.node_launch_seconds
        node_wave_ready = (
            t6_node_ready
            + inputs.pod_startup_seconds
            + inputs.target_health_seconds
        )
    else:
        t4_unschedulable = None
        t5_node_requested = None
        t6_node_ready = None
        node_wave_ready = None

    current_app_capacity = inputs.current_ready_replicas * inputs.safe_rps_per_pod
    warm_app_capacity = (
        inputs.current_ready_replicas + immediate
    ) * inputs.safe_rps_per_pod
    final_app_capacity = (
        inputs.current_ready_replicas + immediate + node_backed
    ) * inputs.safe_rps_per_pod

    dependency_limit = (
        math.inf
        if inputs.dependency_capacity_rps is None
        else inputs.dependency_capacity_rps
    )
    current_effective = min(current_app_capacity, dependency_limit)
    warm_effective = min(warm_app_capacity, dependency_limit)
    final_effective = min(final_app_capacity, dependency_limit)
    dependency_limited = dependency_limit < final_app_capacity

    if current_effective >= inputs.demand_rps:
        recovered = True
        recovery_seconds: float | None = 0.0
        bottleneck = "none-current-capacity-sufficient"
    elif immediate > 0 and warm_effective >= inputs.demand_rps:
        recovered = True
        recovery_seconds = warm_ready
        bottleneck = "warm-pod-startup-and-target-health"
    elif node_backed > 0 and final_effective >= inputs.demand_rps:
        recovered = True
        recovery_seconds = node_wave_ready
        bottleneck = "node-provisioning-and-pod-startup"
    else:
        recovered = False
        recovery_seconds = None
        if dependency_limit < inputs.demand_rps:
            bottleneck = "downstream-dependency-capacity"
        elif final_app_capacity < inputs.demand_rps:
            bottleneck = "desired-replica-capacity-insufficient"
        else:
            bottleneck = "capacity-not-realized"

    timeline: dict[str, float | None] = {
        "T0_demand_threshold": t0,
        "T1_metric_available": t1_metric_available,
        "T2_desired_replicas_changed": t2_desired_changed,
        "T3_pods_created": t3_pods_created,
        "T4_pods_unschedulable": t4_unschedulable,
        "T5_node_provisioning_requested": t5_node_requested,
        "T6_node_ready": t6_node_ready,
        "T7_warm_wave_target_healthy": warm_ready,
        "T8_node_wave_target_healthy": node_wave_ready,
        "T9_user_sli_recovered": recovery_seconds,
    }

    return CapacityResult(
        additional_replicas_requested=additional,
        immediate_replicas=immediate,
        node_backed_replicas=node_backed,
        nodes_requested=nodes_requested,
        current_service_capacity_rps=round(current_effective, 3),
        warm_wave_capacity_rps=round(warm_effective, 3),
        final_application_capacity_rps=round(final_app_capacity, 3),
        final_effective_capacity_rps=round(final_effective, 3),
        dependency_limited=dependency_limited,
        recovered=recovered,
        recovery_seconds=recovery_seconds,
        bottleneck=bottleneck,
        timeline=timeline,
    )


def run_scenario(name: str, hpa_input: HPAInput, capacity_input: dict[str, Any]) -> dict[str, Any]:
    hpa = calculate_hpa(hpa_input)
    realized = simulate_capacity_realization(
        CapacityInput(desired_replicas=hpa.desired_replicas, **capacity_input)
    )
    return {
        "scenario": name,
        "hpa_input": asdict(hpa_input),
        "hpa_result": asdict(hpa),
        "capacity_result": asdict(realized),
    }


def run_demo() -> int:
    common_capacity: dict[str, Any] = {
        "demand_rps": 8_000.0,
        "current_ready_replicas": 10,
        "safe_rps_per_pod": 500.0,
        "pods_per_new_node": 10,
    }

    scenarios = [
        run_scenario(
            "oversized-request-suppresses-scale-up",
            HPAInput(
                current_replicas=10,
                average_usage_millicores=900,
                average_request_millicores=4_000,
                target_utilization_percent=60,
                max_replicas=100,
            ),
            {**common_capacity, "warm_pod_slots": 0},
        ),
        run_scenario(
            "cold-node-capacity",
            HPAInput(
                current_replicas=10,
                average_usage_millicores=900,
                average_request_millicores=1_000,
                target_utilization_percent=60,
                max_replicas=100,
            ),
            {**common_capacity, "warm_pod_slots": 0},
        ),
        run_scenario(
            "warm-capacity",
            HPAInput(
                current_replicas=10,
                average_usage_millicores=900,
                average_request_millicores=1_000,
                target_utilization_percent=60,
                max_replicas=100,
            ),
            {**common_capacity, "warm_pod_slots": 6},
        ),
        run_scenario(
            "downstream-remains-saturated",
            HPAInput(
                current_replicas=10,
                average_usage_millicores=1_200,
                average_request_millicores=1_000,
                target_utilization_percent=60,
                max_replicas=100,
            ),
            {
                **common_capacity,
                "warm_pod_slots": 20,
                "dependency_capacity_rps": 6_000.0,
            },
        ),
    ]

    print(json.dumps({"scenarios": scenarios}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safe Kubernetes autoscaling and capacity-realization simulator"
    )
    parser.add_argument("--demo", action="store_true", help="run built-in scenarios")
    args = parser.parse_args()
    if args.demo:
        return run_demo()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
