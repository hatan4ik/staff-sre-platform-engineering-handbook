from __future__ import annotations

import pathlib
import sys
import unittest

LAB_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR))

from node_repair import (  # noqa: E402
    FleetPolicy,
    Node,
    NodeState,
    RepairError,
    apply_decisions,
    evaluate_repair,
    healthy_capacity_percent,
)


class NodeRepairTests(unittest.TestCase):
    def base_policy(self, **overrides: object) -> FleetPolicy:
        values: dict[str, object] = {
            "max_concurrent_repairs_cluster": 2,
            "max_concurrent_repairs_per_zone": 1,
            "min_healthy_capacity_percent": 50.0,
            "systemic_image_failure_percent": 75.0,
            "systemic_signature_zone_count": 3,
            "restart_failure_limit": 1,
            "require_replacement_ready_before_next": True,
        }
        values.update(overrides)
        return FleetPolicy(**values)  # type: ignore[arg-type]

    def test_single_transient_gets_one_restart(self) -> None:
        nodes = [
            Node("a1", "a", "good"),
            Node(
                "a2",
                "a",
                "good",
                state=NodeState.SUSPECT,
                failure_signature="kubelet-timeout",
                failure_count=1,
            ),
            Node("b1", "b", "good"),
            Node("c1", "c", "good"),
        ]
        result = evaluate_repair(nodes, self.base_policy())
        decision = {item.node: item for item in result.decisions}["a2"]
        self.assertFalse(result.circuit_breaker_open)
        self.assertEqual(decision.action, "restart-once-and-verify")
        self.assertEqual(decision.next_state, NodeState.VERIFYING)

    def test_repeated_failure_is_replaced(self) -> None:
        nodes = [
            Node("a1", "a", "good"),
            Node(
                "b1",
                "b",
                "good",
                state=NodeState.DEGRADED,
                failure_signature="disk-errors",
                failure_count=3,
            ),
            Node("c1", "c", "good"),
            Node("c2", "c", "good"),
        ]
        result = evaluate_repair(nodes, self.base_policy())
        decision = {item.node: item for item in result.decisions}["b1"]
        self.assertEqual(decision.action, "replace-with-known-good")
        self.assertEqual(decision.next_state, NodeState.REPLACING)

    def test_storage_writer_must_be_fenced_before_replacement(self) -> None:
        nodes = [
            Node("a1", "a", "good"),
            Node(
                "b1",
                "b",
                "good",
                state=NodeState.DEGRADED,
                failure_signature="network-partition",
                failure_count=4,
                storage_writer=True,
            ),
            Node("c1", "c", "good"),
            Node("c2", "c", "good"),
        ]
        result = evaluate_repair(nodes, self.base_policy())
        decision = {item.node: item for item in result.decisions}["b1"]
        self.assertEqual(decision.action, "cordon-and-fence")
        self.assertEqual(decision.next_state, NodeState.FENCED)

    def test_fenced_writer_can_be_replaced(self) -> None:
        nodes = [
            Node("a1", "a", "good"),
            Node(
                "b1",
                "b",
                "good",
                state=NodeState.DEGRADED,
                failure_signature="network-partition",
                failure_count=4,
                storage_writer=True,
                traffic_fenced=True,
                storage_fenced=True,
                identity_fenced=True,
            ),
            Node("c1", "c", "good"),
            Node("c2", "c", "good"),
        ]
        result = evaluate_repair(nodes, self.base_policy())
        decision = {item.node: item for item in result.decisions}["b1"]
        self.assertEqual(decision.action, "replace-with-known-good")

    def test_zone_concurrency_limit_holds_second_node(self) -> None:
        nodes = [
            Node(
                "a0",
                "a",
                "good",
                state=NodeState.REPLACING,
                replacement_ready=True,
            ),
            Node(
                "a1",
                "a",
                "good",
                state=NodeState.DEGRADED,
                failure_signature="runtime",
                failure_count=3,
            ),
            Node("b1", "b", "good"),
            Node("c1", "c", "good"),
        ]
        result = evaluate_repair(nodes, self.base_policy())
        decision = {item.node: item for item in result.decisions}["a1"]
        self.assertEqual(decision.action, "hold")
        self.assertEqual(decision.reason, "zone repair concurrency limit reached")

    def test_prior_replacement_gate_holds_next_repair(self) -> None:
        nodes = [
            Node(
                "a0",
                "a",
                "good",
                state=NodeState.REPLACING,
                replacement_ready=False,
            ),
            Node(
                "b1",
                "b",
                "good",
                state=NodeState.DEGRADED,
                failure_signature="runtime",
                failure_count=3,
            ),
            Node("c1", "c", "good"),
            Node("c2", "c", "good"),
        ]
        result = evaluate_repair(nodes, self.base_policy())
        decision = {item.node: item for item in result.decisions}["b1"]
        self.assertEqual(decision.action, "hold")
        self.assertEqual(decision.reason, "prior replacement is not Ready")

    def test_capacity_guard_holds_repair(self) -> None:
        nodes = [
            Node(
                "a1",
                "a",
                "good",
                state=NodeState.DEGRADED,
                failure_signature="disk",
                failure_count=4,
                serving_capacity_units=40,
            ),
            Node("b1", "b", "good", serving_capacity_units=30),
            Node("c1", "c", "good", serving_capacity_units=30),
        ]
        result = evaluate_repair(
            nodes,
            self.base_policy(min_healthy_capacity_percent=70.0),
        )
        decision = {item.node: item for item in result.decisions}["a1"]
        self.assertEqual(decision.action, "hold")
        self.assertIn("projected healthy capacity", decision.reason)

    def test_systemic_image_failure_opens_circuit_breaker(self) -> None:
        nodes = [
            Node(
                "a1",
                "a",
                "bad-image",
                state=NodeState.DEGRADED,
                failure_signature="runtime-crash",
                failure_count=3,
            ),
            Node(
                "b1",
                "b",
                "bad-image",
                state=NodeState.DEGRADED,
                failure_signature="runtime-crash",
                failure_count=3,
            ),
            Node("c1", "c", "good-image"),
            Node("c2", "c", "good-image"),
        ]
        result = evaluate_repair(
            nodes,
            self.base_policy(systemic_image_failure_percent=50.0),
        )
        self.assertTrue(result.circuit_breaker_open)
        self.assertIn("image bad-image", result.circuit_breaker_reason or "")
        self.assertEqual(result.decisions, ())

    def test_same_signature_across_zones_opens_circuit_breaker(self) -> None:
        nodes = [
            Node(
                "a1",
                "a",
                "image-a",
                state=NodeState.DEGRADED,
                failure_signature="cni-corruption",
                failure_count=3,
            ),
            Node(
                "b1",
                "b",
                "image-b",
                state=NodeState.DEGRADED,
                failure_signature="cni-corruption",
                failure_count=3,
            ),
            Node("c1", "c", "image-c"),
            Node("c2", "c", "image-c"),
        ]
        result = evaluate_repair(
            nodes,
            self.base_policy(
                systemic_image_failure_percent=100.0,
                systemic_signature_zone_count=2,
            ),
        )
        self.assertTrue(result.circuit_breaker_open)
        self.assertIn("appears in 2 zones", result.circuit_breaker_reason or "")

    def test_global_disable_stops_repairs(self) -> None:
        nodes = [
            Node("a1", "a", "good"),
            Node(
                "b1",
                "b",
                "good",
                state=NodeState.DEGRADED,
                failure_signature="runtime",
                failure_count=3,
            ),
        ]
        result = evaluate_repair(nodes, self.base_policy(), global_disable=True)
        self.assertTrue(result.circuit_breaker_open)
        self.assertEqual(result.decisions, ())

    def test_apply_decisions_changes_state_only(self) -> None:
        nodes = [
            Node("a1", "a", "good"),
            Node(
                "b1",
                "b",
                "good",
                state=NodeState.DEGRADED,
                failure_signature="disk",
                failure_count=3,
            ),
            Node("c1", "c", "good"),
        ]
        result = evaluate_repair(nodes, self.base_policy())
        updated = {item.name: item for item in apply_decisions(nodes, result)}
        self.assertEqual(updated["b1"].state, NodeState.REPLACING)
        self.assertEqual(updated["a1"].state, NodeState.HEALTHY)

    def test_healthy_capacity(self) -> None:
        nodes = [
            Node("a1", "a", "good", serving_capacity_units=20),
            Node(
                "b1",
                "b",
                "good",
                state=NodeState.DEGRADED,
                serving_capacity_units=10,
            ),
            Node("c1", "c", "good", serving_capacity_units=10),
        ]
        self.assertEqual(healthy_capacity_percent(nodes), 75.0)

    def test_duplicate_names_are_rejected(self) -> None:
        with self.assertRaisesRegex(RepairError, "node names must be unique"):
            evaluate_repair(
                [Node("a1", "a", "good"), Node("a1", "b", "good")],
                self.base_policy(),
            )


if __name__ == "__main__":
    unittest.main()
