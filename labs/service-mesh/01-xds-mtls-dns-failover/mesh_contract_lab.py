#!/usr/bin/env python3
"""Deterministic service-mesh reliability contract lab.

Models reusable invariants for:
- xDS ACK/NACK and last-known-good configuration;
- certificate rotation overlap and expiry safety;
- DNS cache freshness and stale fallback;
- east-west failover capacity and write-authority fencing;
- bounded retry amplification.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ConfigSnapshot:
    version: str
    valid: bool
    endpoints: tuple[str, ...]


@dataclass(frozen=True)
class XdsResult:
    active_version: str
    response: str
    serving_endpoints: tuple[str, ...]


def apply_xds(active: ConfigSnapshot, candidate: ConfigSnapshot) -> XdsResult:
    if not candidate.valid or not candidate.endpoints:
        return XdsResult(active.version, "NACK", active.endpoints)
    return XdsResult(candidate.version, "ACK", candidate.endpoints)


@dataclass(frozen=True)
class Certificate:
    serial: str
    not_before: int
    not_after: int
    root: str

    def valid_at(self, timestamp: int) -> bool:
        return self.not_before <= timestamp < self.not_after


@dataclass(frozen=True)
class RotationResult:
    handshake_allowed: bool
    reason: str


def evaluate_handshake(
    *,
    leaf: Certificate,
    timestamp: int,
    trusted_roots: set[str],
) -> RotationResult:
    if not leaf.valid_at(timestamp):
        return RotationResult(False, "leaf_not_valid")
    if leaf.root not in trusted_roots:
        return RotationResult(False, "untrusted_root")
    return RotationResult(True, "trusted_and_current")


@dataclass(frozen=True)
class DnsEntry:
    address: str
    observed_at: int
    ttl_seconds: int
    stale_if_error_seconds: int


@dataclass(frozen=True)
class DnsDecision:
    usable: bool
    stale: bool
    reason: str


def evaluate_dns(entry: DnsEntry, *, timestamp: int, resolver_healthy: bool) -> DnsDecision:
    age = timestamp - entry.observed_at
    if age < 0:
        raise ValueError("timestamp precedes observation")
    if age <= entry.ttl_seconds:
        return DnsDecision(True, False, "fresh")
    if not resolver_healthy and age <= entry.ttl_seconds + entry.stale_if_error_seconds:
        return DnsDecision(True, True, "bounded_stale_fallback")
    return DnsDecision(False, False, "expired")


@dataclass(frozen=True)
class RemoteCell:
    name: str
    capacity: int
    current_load: int
    gateway_healthy: bool
    identity_healthy: bool
    data_fresh: bool
    write_authority: bool

    @property
    def headroom(self) -> int:
        return max(0, self.capacity - self.current_load)


@dataclass(frozen=True)
class FailoverResult:
    allowed: bool
    reason: str
    required_headroom: int
    available_headroom: int


def evaluate_failover(
    cell: RemoteCell,
    *,
    traffic_to_shift: int,
    safety_margin_fraction: float,
    requires_write_authority: bool,
) -> FailoverResult:
    if traffic_to_shift < 0:
        raise ValueError("traffic_to_shift must be non-negative")
    if safety_margin_fraction < 0:
        raise ValueError("safety margin must be non-negative")
    required = int(traffic_to_shift * (1 + safety_margin_fraction) + 0.999999)
    if not cell.gateway_healthy:
        return FailoverResult(False, "gateway_unhealthy", required, cell.headroom)
    if not cell.identity_healthy:
        return FailoverResult(False, "identity_path_unhealthy", required, cell.headroom)
    if not cell.data_fresh:
        return FailoverResult(False, "data_not_fresh", required, cell.headroom)
    if requires_write_authority and not cell.write_authority:
        return FailoverResult(False, "write_authority_not_fenced", required, cell.headroom)
    if cell.headroom < required:
        return FailoverResult(False, "insufficient_headroom", required, cell.headroom)
    return FailoverResult(True, "safe_to_shift", required, cell.headroom)


def retry_attempts(original_requests: int, retry_budget_fraction: float) -> int:
    if original_requests < 0:
        raise ValueError("original_requests must be non-negative")
    if not 0 <= retry_budget_fraction <= 1:
        raise ValueError("retry budget must be between zero and one")
    return original_requests + int(original_requests * retry_budget_fraction)


def run_scenario() -> dict[str, object]:
    active = ConfigSnapshot("v41", True, ("10.0.1.10", "10.0.1.11"))
    invalid = ConfigSnapshot("v42", False, ())
    valid = ConfigSnapshot("v43", True, ("10.0.2.10", "10.0.2.11"))
    nack = apply_xds(active, invalid)
    ack = apply_xds(active, valid)

    old_leaf = Certificate("leaf-old", 0, 100, "root-a")
    new_leaf = Certificate("leaf-new", 50, 200, "root-b")
    overlap_roots = {"root-a", "root-b"}
    new_only_roots = {"root-b"}

    old_during_overlap = evaluate_handshake(
        leaf=old_leaf, timestamp=75, trusted_roots=overlap_roots
    )
    new_during_overlap = evaluate_handshake(
        leaf=new_leaf, timestamp=75, trusted_roots=overlap_roots
    )
    old_after_retirement = evaluate_handshake(
        leaf=old_leaf, timestamp=110, trusted_roots=new_only_roots
    )

    dns = DnsEntry("10.0.9.10", observed_at=0, ttl_seconds=30, stale_if_error_seconds=20)
    fresh_dns = evaluate_dns(dns, timestamp=20, resolver_healthy=True)
    bounded_stale_dns = evaluate_dns(dns, timestamp=40, resolver_healthy=False)
    expired_dns = evaluate_dns(dns, timestamp=55, resolver_healthy=False)

    remote_without_authority = RemoteCell(
        "remote-b",
        capacity=100,
        current_load=50,
        gateway_healthy=True,
        identity_healthy=True,
        data_fresh=True,
        write_authority=False,
    )
    blocked_write_failover = evaluate_failover(
        remote_without_authority,
        traffic_to_shift=25,
        safety_margin_fraction=0.20,
        requires_write_authority=True,
    )
    remote_with_authority = RemoteCell(
        "remote-b",
        capacity=100,
        current_load=50,
        gateway_healthy=True,
        identity_healthy=True,
        data_fresh=True,
        write_authority=True,
    )
    safe_failover = evaluate_failover(
        remote_with_authority,
        traffic_to_shift=25,
        safety_margin_fraction=0.20,
        requires_write_authority=True,
    )

    attempts = retry_attempts(100, 0.20)

    invariants = {
        "invalid_xds_is_nacked": nack.response == "NACK",
        "last_known_good_is_preserved": (
            nack.active_version == active.version
            and nack.serving_endpoints == active.endpoints
        ),
        "valid_xds_is_acked": ack.response == "ACK" and ack.active_version == "v43",
        "root_overlap_accepts_old_leaf": old_during_overlap.handshake_allowed,
        "root_overlap_accepts_new_leaf": new_during_overlap.handshake_allowed,
        "retired_old_leaf_is_rejected": not old_after_retirement.handshake_allowed,
        "fresh_dns_is_used": fresh_dns.usable and not fresh_dns.stale,
        "dns_stale_fallback_is_bounded": bounded_stale_dns.usable and bounded_stale_dns.stale,
        "expired_dns_is_rejected": not expired_dns.usable,
        "write_failover_requires_fencing": not blocked_write_failover.allowed,
        "safe_remote_failover_is_allowed": safe_failover.allowed,
        "retry_budget_is_bounded": attempts == 120,
    }

    return {
        "xds_nack": asdict(nack),
        "xds_ack": asdict(ack),
        "old_during_overlap": asdict(old_during_overlap),
        "new_during_overlap": asdict(new_during_overlap),
        "old_after_retirement": asdict(old_after_retirement),
        "fresh_dns": asdict(fresh_dns),
        "bounded_stale_dns": asdict(bounded_stale_dns),
        "expired_dns": asdict(expired_dns),
        "blocked_write_failover": asdict(blocked_write_failover),
        "safe_failover": asdict(safe_failover),
        "budgeted_attempts": attempts,
        "invariants": invariants,
        "passed": all(invariants.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_scenario()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Service-mesh reliability contract lab")
        print(f"passed: {result['passed']}")
        for name, passed in result["invariants"].items():
            print(f"- {name}: {'PASS' if passed else 'FAIL'}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
