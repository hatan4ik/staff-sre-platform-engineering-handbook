from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Iterable


class RepairError(ValueError):
    """Raised when fleet or repair inputs violate the lab contract."""


class NodeState(str, Enum):
    HEALTHY = "healthy"
    SUSPECT = "suspect"
    DEGRADED = "degraded"
    CORDONED = "cordoned"
    FENCED = "fenced"
    DRAINING = "draining"
    REPLACING = "replacing"
    VERIFYING = "verifying"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class Node:
    name: str
    zone: str
    image: str
    state: NodeState = NodeState.HEALTHY
    failure_signature: str | None = None
    failure_count: int = 0
    serving_capacity_units: int = 10
    critical_workloads: bool = False
    storage_writer: bool = False
    traffic_fenced: bool = False
    storage_fenced: bool = False
    identity_fenced: bool = False
    replacement_ready: bool = False


@dataclass(frozen=True)
class FleetPolicy:
    max_concurrent_repairs_cluster: int = 3
    max_concurrent_repairs_per_zone: int = 1
    min_healthy_capacity_percent: float = 70.0
    systemic_image_failure_percent: float = 20.0
    systemic_signature_zone_count: int = 2
    restart_failure_limit: int = 1
    require_replacement_ready_before_next: bool = True


@dataclass(frozen=True)
class RepairDecision:
    node: str
    action: str
    reason: str
    next_state: NodeState


@dataclass(frozen=True)
class ControllerResult:
    circuit_breaker_open: bool
    circuit_breaker_reason: str | None
    decisions: tuple[RepairDecision, ...]
    projected_healthy_capacity_percent: float


REPAIR_STATES = {
    NodeState.CORDONED,
    NodeState.FENCED,
    NodeState.DRAINING,
    NodeState.REPLACING,
    NodeState.VERIFYING,
}


def _validate_policy(policy: FleetPolicy) -> None:
    if policy.max_concurrent_repairs_cluster <= 0:
        raise RepairError("cluster repair limit must be positive")
    if policy.max_concurrent_repairs_per_zone <= 0:
        raise RepairError("zone repair limit must be positive")
    if not 0 < policy.min_healthy_capacity_percent <= 100:
        raise RepairError("minimum healthy capacity percent must be in (0, 100]")
    if not 0 < policy.systemic_image_failure_percent <= 100:
        raise RepairError("systemic image failure percent must be in (0, 100]")
    if policy.systemic_signature_zone_count <= 0:
        raise RepairError("systemic signature zone count must be positive")
    if policy.restart_failure_limit < 0:
        raise RepairError("restart failure limit cannot be negative")


def _validate_nodes(nodes: Iterable[Node]) -> list[Node]:
    fleet = list(nodes)
    if not fleet:
        raise RepairError("fleet must contain at least one node")
    names = [node.name for node in fleet]
    if len(names) != len(set(names)):
        raise RepairError("node names must be unique")
    for node in fleet:
        if node.serving_capacity_units <= 0:
            raise RepairError("node capacity must be positive")
        if node.storage_fenced and not node.traffic_fenced:
            raise RepairError("storage fencing requires traffic fencing in this lab")
    return fleet


def healthy_capacity_percent(nodes: Iterable[Node]) -> float:
    fleet = _validate_nodes(nodes)
    total = sum(node.serving_capacity_units for node in fleet)
    healthy = sum(
        node.serving_capacity_units
        for node in fleet
        if node.state in {NodeState.HEALTHY, NodeState.SUSPECT}
    )
    return healthy / total * 100.0


def _systemic_failure_reason(
    nodes: list[Node], policy: FleetPolicy
) -> str | None:
    unhealthy = [
        node
        for node in nodes
        if node.state not in {NodeState.HEALTHY, NodeState.SUSPECT}
        and node.failure_signature
    ]
    if not unhealthy:
        return None

    by_image: dict[str, list[Node]] = {}
    by_signature: dict[str, list[Node]] = {}
    for node in nodes:
        by_image.setdefault(node.image, []).append(node)
    for node in unhealthy:
        by_signature.setdefault(node.failure_signature or "unknown", []).append(node)

    for image, image_nodes in by_image.items():
        failed = [node for node in unhealthy if node.image == image]
        if not failed:
            continue
        failure_percent = len(failed) / len(image_nodes) * 100.0
        if failure_percent >= policy.systemic_image_failure_percent:
            return (
                f"image {image} failure rate {failure_percent:.1f}% "
                f"exceeds {policy.systemic_image_failure_percent:.1f}%"
            )

    for signature, signature_nodes in by_signature.items():
        zones = {node.zone for node in signature_nodes}
        if len(zones) >= policy.systemic_signature_zone_count:
            return (
                f"signature {signature} appears in {len(zones)} zones; "
                "treat as fleet pattern"
            )

    return None


def _current_repairs(nodes: list[Node]) -> tuple[int, dict[str, int]]:
    cluster = 0
    per_zone: dict[str, int] = {}
    for node in nodes:
        if node.state in REPAIR_STATES:
            cluster += 1
            per_zone[node.zone] = per_zone.get(node.zone, 0) + 1
    return cluster, per_zone


def _replacement_gate_open(nodes: list[Node], policy: FleetPolicy) -> bool:
    if not policy.require_replacement_ready_before_next:
        return True
    replacing = [node for node in nodes if node.state == NodeState.REPLACING]
    if not replacing:
        return True
    return any(node.replacement_ready for node in replacing)


def _projected_capacity_after_removal(nodes: list[Node], node: Node) -> float:
    total = sum(item.serving_capacity_units for item in nodes)
    healthy = sum(
        item.serving_capacity_units
        for item in nodes
        if item.state in {NodeState.HEALTHY, NodeState.SUSPECT}
        and item.name != node.name
    )
    return healthy / total * 100.0


def evaluate_repair(
    nodes: Iterable[Node],
    policy: FleetPolicy,
    *,
    global_disable: bool = False,
) -> ControllerResult:
    """Evaluate one safe repair-controller reconciliation cycle."""
    _validate_policy(policy)
    fleet = _validate_nodes(nodes)

    if global_disable:
        return ControllerResult(
            circuit_breaker_open=True,
            circuit_breaker_reason="global repair disable is active",
            decisions=(),
            projected_healthy_capacity_percent=healthy_capacity_percent(fleet),
        )

    systemic = _systemic_failure_reason(fleet, policy)
    if systemic:
        return ControllerResult(
            circuit_breaker_open=True,
            circuit_breaker_reason=systemic,
            decisions=(),
            projected_healthy_capacity_percent=healthy_capacity_percent(fleet),
        )

    cluster_repairs, zone_repairs = _current_repairs(fleet)
    replacement_gate = _replacement_gate_open(fleet, policy)
    decisions: list[RepairDecision] = []
    projected_percent = healthy_capacity_percent(fleet)

    candidates = sorted(
        [node for node in fleet if node.state in {NodeState.SUSPECT, NodeState.DEGRADED}],
        key=lambda item: (
            not item.critical_workloads,
            -item.failure_count,
            item.zone,
            item.name,
        ),
    )

    for node in candidates:
        if node.state == NodeState.SUSPECT and node.failure_count <= policy.restart_failure_limit:
            decisions.append(
                RepairDecision(
                    node=node.name,
                    action="restart-once-and-verify",
                    reason="known bounded transient candidate",
                    next_state=NodeState.VERIFYING,
                )
            )
            continue

        if cluster_repairs >= policy.max_concurrent_repairs_cluster:
            decisions.append(
                RepairDecision(
                    node=node.name,
                    action="hold",
                    reason="cluster repair concurrency limit reached",
                    next_state=node.state,
                )
            )
            continue

        if zone_repairs.get(node.zone, 0) >= policy.max_concurrent_repairs_per_zone:
            decisions.append(
                RepairDecision(
                    node=node.name,
                    action="hold",
                    reason="zone repair concurrency limit reached",
                    next_state=node.state,
                )
            )
            continue

        if not replacement_gate:
            decisions.append(
                RepairDecision(
                    node=node.name,
                    action="hold",
                    reason="prior replacement is not Ready",
                    next_state=node.state,
                )
            )
            continue

        projected = _projected_capacity_after_removal(fleet, node)
        if projected < policy.min_healthy_capacity_percent:
            decisions.append(
                RepairDecision(
                    node=node.name,
                    action="hold",
                    reason=(
                        f"projected healthy capacity {projected:.1f}% below "
                        f"minimum {policy.min_healthy_capacity_percent:.1f}%"
                    ),
                    next_state=node.state,
                )
            )
            continue

        if node.storage_writer and not (
            node.traffic_fenced and node.storage_fenced and node.identity_fenced
        ):
            decisions.append(
                RepairDecision(
                    node=node.name,
                    action="cordon-and-fence",
                    reason="storage writer requires traffic, storage, and identity fencing",
                    next_state=NodeState.FENCED,
                )
            )
            cluster_repairs += 1
            zone_repairs[node.zone] = zone_repairs.get(node.zone, 0) + 1
            projected_percent = min(projected_percent, projected)
            continue

        decisions.append(
            RepairDecision(
                node=node.name,
                action="replace-with-known-good",
                reason="repeated or severe local failure with guardrails satisfied",
                next_state=NodeState.REPLACING,
            )
        )
        cluster_repairs += 1
        zone_repairs[node.zone] = zone_repairs.get(node.zone, 0) + 1
        projected_percent = min(projected_percent, projected)
        replacement_gate = not policy.require_replacement_ready_before_next

    return ControllerResult(
        circuit_breaker_open=False,
        circuit_breaker_reason=None,
        decisions=tuple(decisions),
        projected_healthy_capacity_percent=round(projected_percent, 3),
    )


def apply_decisions(nodes: Iterable[Node], result: ControllerResult) -> list[Node]:
    """Apply state transitions only; this lab never performs real repair actions."""
    fleet = _validate_nodes(nodes)
    by_name = {decision.node: decision for decision in result.decisions}
    output: list[Node] = []
    for node in fleet:
        decision = by_name.get(node.name)
        if decision is None or decision.action == "hold":
            output.append(node)
            continue
        output.append(replace(node, state=decision.next_state))
    return output


def run_demo() -> int:
    policy = FleetPolicy(
        max_concurrent_repairs_cluster=2,
        max_concurrent_repairs_per_zone=1,
        min_healthy_capacity_percent=60.0,
        systemic_image_failure_percent=50.0,
        systemic_signature_zone_count=3,
    )

    local_fleet = [
        Node("node-a1", "zone-a", "image-good"),
        Node(
            "node-a2",
            "zone-a",
            "image-good",
            state=NodeState.SUSPECT,
            failure_signature="runtime-timeout",
            failure_count=1,
        ),
        Node(
            "node-b1",
            "zone-b",
            "image-good",
            state=NodeState.DEGRADED,
            failure_signature="disk-errors",
            failure_count=3,
        ),
        Node("node-b2", "zone-b", "image-good"),
        Node("node-c1", "zone-c", "image-good"),
        Node("node-c2", "zone-c", "image-good"),
    ]

    systemic_fleet = [
        Node(
            "node-a1",
            "zone-a",
            "image-bad",
            state=NodeState.DEGRADED,
            failure_signature="runtime-crash",
            failure_count=3,
        ),
        Node(
            "node-b1",
            "zone-b",
            "image-bad",
            state=NodeState.DEGRADED,
            failure_signature="runtime-crash",
            failure_count=3,
        ),
        Node("node-c1", "zone-c", "image-good"),
        Node("node-c2", "zone-c", "image-good"),
    ]

    writer_fleet = [
        Node("node-a1", "zone-a", "image-good"),
        Node(
            "node-b1",
            "zone-b",
            "image-good",
            state=NodeState.DEGRADED,
            failure_signature="network-partition",
            failure_count=4,
            storage_writer=True,
        ),
        Node("node-c1", "zone-c", "image-good"),
        Node("node-c2", "zone-c", "image-good"),
    ]

    output = {
        "local_failure": asdict(evaluate_repair(local_fleet, policy)),
        "systemic_failure": asdict(evaluate_repair(systemic_fleet, policy)),
        "writer_fencing": asdict(evaluate_repair(writer_fleet, policy)),
    }
    print(json.dumps(output, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safe Kubernetes node repair state-machine simulator"
    )
    parser.add_argument("--demo", action="store_true", help="run built-in scenarios")
    args = parser.parse_args()
    if args.demo:
        return run_demo()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
