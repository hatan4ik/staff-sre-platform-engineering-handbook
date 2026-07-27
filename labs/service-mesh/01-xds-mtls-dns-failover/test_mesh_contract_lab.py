#!/usr/bin/env python3

import unittest

from mesh_contract_lab import (
    Certificate,
    ConfigSnapshot,
    DnsEntry,
    RemoteCell,
    apply_xds,
    evaluate_dns,
    evaluate_failover,
    evaluate_handshake,
    retry_attempts,
    run_scenario,
)


class XdsTests(unittest.TestCase):
    def test_nack_preserves_last_known_good(self) -> None:
        active = ConfigSnapshot("v1", True, ("10.0.0.1",))
        invalid = ConfigSnapshot("v2", False, ())
        result = apply_xds(active, invalid)
        self.assertEqual(result.response, "NACK")
        self.assertEqual(result.active_version, "v1")
        self.assertEqual(result.serving_endpoints, ("10.0.0.1",))

    def test_valid_update_is_acked(self) -> None:
        active = ConfigSnapshot("v1", True, ("10.0.0.1",))
        candidate = ConfigSnapshot("v2", True, ("10.0.0.2",))
        result = apply_xds(active, candidate)
        self.assertEqual(result.response, "ACK")
        self.assertEqual(result.active_version, "v2")


class CertificateTests(unittest.TestCase):
    def test_rotation_overlap_accepts_both_roots(self) -> None:
        old = Certificate("old", 0, 100, "a")
        new = Certificate("new", 50, 200, "b")
        roots = {"a", "b"}
        self.assertTrue(
            evaluate_handshake(leaf=old, timestamp=75, trusted_roots=roots).handshake_allowed
        )
        self.assertTrue(
            evaluate_handshake(leaf=new, timestamp=75, trusted_roots=roots).handshake_allowed
        )

    def test_expired_or_untrusted_leaf_is_rejected(self) -> None:
        leaf = Certificate("old", 0, 100, "a")
        self.assertFalse(
            evaluate_handshake(leaf=leaf, timestamp=101, trusted_roots={"a"}).handshake_allowed
        )
        self.assertFalse(
            evaluate_handshake(leaf=leaf, timestamp=50, trusted_roots={"b"}).handshake_allowed
        )


class DnsTests(unittest.TestCase):
    def test_stale_fallback_has_a_hard_limit(self) -> None:
        entry = DnsEntry("10.0.0.1", 0, 30, 20)
        self.assertTrue(evaluate_dns(entry, timestamp=20, resolver_healthy=True).usable)
        stale = evaluate_dns(entry, timestamp=40, resolver_healthy=False)
        self.assertTrue(stale.usable)
        self.assertTrue(stale.stale)
        self.assertFalse(evaluate_dns(entry, timestamp=51, resolver_healthy=False).usable)


class FailoverTests(unittest.TestCase):
    def test_write_authority_is_required(self) -> None:
        cell = RemoteCell("b", 100, 20, True, True, True, False)
        decision = evaluate_failover(
            cell,
            traffic_to_shift=20,
            safety_margin_fraction=0.20,
            requires_write_authority=True,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "write_authority_not_fenced")

    def test_headroom_and_health_are_required(self) -> None:
        cell = RemoteCell("b", 100, 85, True, True, True, True)
        decision = evaluate_failover(
            cell,
            traffic_to_shift=20,
            safety_margin_fraction=0.20,
            requires_write_authority=True,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "insufficient_headroom")


class RetryTests(unittest.TestCase):
    def test_retry_budget_is_bounded(self) -> None:
        self.assertEqual(retry_attempts(100, 0.20), 120)


class ScenarioTests(unittest.TestCase):
    def test_full_scenario(self) -> None:
        result = run_scenario()
        self.assertTrue(result["passed"])
        self.assertTrue(all(result["invariants"].values()))


if __name__ == "__main__":
    unittest.main()
