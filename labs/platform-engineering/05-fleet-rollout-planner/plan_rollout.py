#!/usr/bin/env python3
"""Create bounded rollout batches from simplified cluster inventory.

This planning lab validates eligibility and batch shape. A real rollout controller
must also stop promotion on live cluster, add-on, and application SLO evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
KUBERNETES_VERSION = re.compile(r"^(?P<minor>[0-9]+\.[0-9]+)\.[0-9]+$")


class InputError(Exception):
    """Raised when a lab input cannot be parsed or validated."""


@dataclass(frozen=True)
class ClusterDecision:
    cluster_id: str
    ring: str
    failure_domain: str
    status: str
    reasons: tuple[str, ...]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(
            f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{path} must be an object")
    return value


def require_string(parent: dict[str, Any], key: str, path: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{path}.{key} must be a non-empty string")
    return value.strip()


def require_bool(parent: dict[str, Any], key: str, path: str) -> bool:
    value = parent.get(key)
    if not isinstance(value, bool):
        raise InputError(f"{path}.{key} must be true or false")
    return value


def require_positive_int(parent: dict[str, Any], key: str, path: str) -> int:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InputError(f"{path}.{key} must be a positive integer")
    return value


def require_string_list(parent: dict[str, Any], key: str, path: str) -> list[str]:
    value = parent.get(key)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item for item in value)
    ):
        raise InputError(f"{path}.{key} must be a non-empty array of strings")
    if len(set(value)) != len(value):
        raise InputError(f"{path}.{key} must not contain duplicates")
    return value


def parse_time(value: str, path: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InputError(f"{path} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise InputError(f"{path} must include a timezone")
    return parsed.astimezone(timezone.utc)


def within_maintenance_window(now: datetime, start_hour: int, duration: int) -> bool:
    if not 0 <= start_hour <= 23:
        raise InputError("maintenance.startHourUtc must be between 0 and 23")
    if not 1 <= duration <= 24:
        raise InputError("maintenance.durationHours must be between 1 and 24")
    if duration == 24:
        return True
    current = now.hour
    end = (start_hour + duration) % 24
    if start_hour < end:
        return start_hour <= current < end
    return current >= start_hour or current < end


def parse_policy(raw: Any) -> dict[str, Any]:
    policy = require_object(raw, "policy")
    release_id = require_string(policy, "releaseId", "policy")
    candidate = require_string(policy, "candidateBaselineVersion", "policy")
    if not SEMVER.fullmatch(candidate):
        raise InputError("policy.candidateBaselineVersion must be x.y.z")

    ring_order = require_string_list(policy, "ringOrder", "policy")
    supported_minors = require_string_list(
        policy, "supportedKubernetesMinors", "policy"
    )
    supported_classes = require_string_list(
        policy, "supportedClusterClasses", "policy"
    )
    lifecycle_states = require_string_list(
        policy, "eligibleLifecycleStates", "policy"
    )
    maximum_batch_size = require_positive_int(
        policy, "maximumBatchSize", "policy"
    )
    maximum_per_fd = require_positive_int(
        policy, "maximumClustersPerFailureDomainPerBatch", "policy"
    )
    maximum_age = require_positive_int(
        policy, "maximumConformanceAgeHours", "policy"
    )
    require_window = require_bool(policy, "requireMaintenanceWindow", "policy")

    raw_predecessors = require_object(
        policy.get("requiredPredecessorRings", {}),
        "policy.requiredPredecessorRings",
    )
    predecessors: dict[str, list[str]] = {}
    for ring, value in raw_predecessors.items():
        if ring not in ring_order:
            raise InputError(
                f"policy.requiredPredecessorRings references unknown ring {ring!r}"
            )
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item in ring_order for item in value
        ):
            raise InputError(
                f"policy.requiredPredecessorRings.{ring} must contain known rings"
            )
        ring_index = ring_order.index(ring)
        if any(ring_order.index(item) >= ring_index for item in value):
            raise InputError(
                f"policy.requiredPredecessorRings.{ring} may reference only earlier rings"
            )
        predecessors[ring] = value

    return {
        "releaseId": release_id,
        "candidateBaselineVersion": candidate,
        "ringOrder": ring_order,
        "supportedKubernetesMinors": set(supported_minors),
        "supportedClusterClasses": set(supported_classes),
        "eligibleLifecycleStates": set(lifecycle_states),
        "maximumBatchSize": maximum_batch_size,
        "maximumClustersPerFailureDomainPerBatch": maximum_per_fd,
        "maximumConformanceAgeHours": maximum_age,
        "requireMaintenanceWindow": require_window,
        "requiredPredecessorRings": predecessors,
    }


def decide_cluster(
    raw_cluster: Any,
    index: int,
    policy: dict[str, Any],
    now: datetime,
) -> ClusterDecision:
    path = f"clusters[{index}]"
    cluster = require_object(raw_cluster, path)

    cluster_id = require_string(cluster, "clusterId", path)
    cluster_class = require_string(cluster, "clusterClass", path)
    lifecycle = require_string(cluster, "lifecycleState", path)
    require_string(cluster, "region", path)
    failure_domain = require_string(cluster, "failureDomain", path)
    ring = require_string(cluster, "rolloutRing", path)
    kubernetes_version = require_string(cluster, "kubernetesVersion", path)
    baseline = require_string(cluster, "baselineVersion", path)
    conformance_raw = require_string(cluster, "lastConformancePass", path)
    maintenance = require_object(cluster.get("maintenance"), f"{path}.maintenance")

    if ring not in policy["ringOrder"]:
        raise InputError(f"{path}.rolloutRing references unknown ring {ring!r}")
    if not SEMVER.fullmatch(baseline):
        raise InputError(f"{path}.baselineVersion must be x.y.z")

    version_match = KUBERNETES_VERSION.fullmatch(kubernetes_version)
    if version_match is None:
        raise InputError(f"{path}.kubernetesVersion must be major.minor.patch")
    kubernetes_minor = version_match.group("minor")

    conformance = parse_time(conformance_raw, f"{path}.lastConformancePass")
    if conformance > now:
        raise InputError(f"{path}.lastConformancePass cannot be in the future")
    age_hours = (now - conformance).total_seconds() / 3600

    start_hour = maintenance.get("startHourUtc")
    duration = maintenance.get("durationHours")
    if isinstance(start_hour, bool) or not isinstance(start_hour, int):
        raise InputError(f"{path}.maintenance.startHourUtc must be an integer")
    if isinstance(duration, bool) or not isinstance(duration, int):
        raise InputError(f"{path}.maintenance.durationHours must be an integer")
    in_window = within_maintenance_window(now, start_hour, duration)

    blockers: list[str] = []
    deferrals: list[str] = []

    if cluster_class not in policy["supportedClusterClasses"]:
        blockers.append(f"unsupported cluster class {cluster_class}")
    if lifecycle not in policy["eligibleLifecycleStates"]:
        blockers.append(f"lifecycle state {lifecycle} is not eligible")
    if kubernetes_minor not in policy["supportedKubernetesMinors"]:
        blockers.append(f"Kubernetes minor {kubernetes_minor} is not supported")
    if age_hours > policy["maximumConformanceAgeHours"]:
        blockers.append(
            f"conformance evidence is {age_hours:.1f}h old; maximum is "
            f"{policy['maximumConformanceAgeHours']}h"
        )
    if baseline == policy["candidateBaselineVersion"]:
        blockers.append("candidate baseline is already installed")
    if policy["requireMaintenanceWindow"] and not in_window:
        deferrals.append("outside declared maintenance window")

    if blockers:
        return ClusterDecision(
            cluster_id,
            ring,
            failure_domain,
            "BLOCKED",
            tuple(blockers + deferrals),
        )
    if deferrals:
        return ClusterDecision(
            cluster_id,
            ring,
            failure_domain,
            "DEFERRED",
            tuple(deferrals),
        )
    return ClusterDecision(cluster_id, ring, failure_domain, "ELIGIBLE", ())


def create_batches(
    eligible: list[ClusterDecision],
    ring_order: list[str],
    max_batch_size: int,
    max_per_failure_domain: int,
) -> list[tuple[str, int, list[ClusterDecision]]]:
    by_ring: dict[str, list[ClusterDecision]] = defaultdict(list)
    for item in eligible:
        by_ring[item.ring].append(item)

    planned: list[tuple[str, int, list[ClusterDecision]]] = []
    for ring in ring_order:
        remaining = sorted(
            by_ring.get(ring, []),
            key=lambda item: (item.failure_domain, item.cluster_id),
        )
        batch_number = 1
        while remaining:
            selected: list[ClusterDecision] = []
            counts: dict[str, int] = defaultdict(int)
            deferred_for_batch: list[ClusterDecision] = []

            for item in remaining:
                if len(selected) >= max_batch_size:
                    deferred_for_batch.append(item)
                    continue
                if counts[item.failure_domain] >= max_per_failure_domain:
                    deferred_for_batch.append(item)
                    continue
                selected.append(item)
                counts[item.failure_domain] += 1

            if not selected:
                raise InputError(
                    f"cannot create a batch for ring {ring}; failure-domain limits "
                    "prevent progress"
                )

            planned.append((ring, batch_number, selected))
            batch_number += 1
            remaining = deferred_for_batch

    return planned


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("clusters", type=Path)
    parser.add_argument("policy", type=Path)
    parser.add_argument(
        "--now",
        required=True,
        help="RFC3339 planning time used for maintenance and evidence-age checks",
    )
    args = parser.parse_args(argv[1:])

    try:
        raw_clusters = load_json(args.clusters)
        if not isinstance(raw_clusters, list) or not raw_clusters:
            raise InputError("clusters file must contain a non-empty JSON array")
        policy = parse_policy(load_json(args.policy))
        now = parse_time(args.now, "--now")

        decisions = [
            decide_cluster(raw, index, policy, now)
            for index, raw in enumerate(raw_clusters)
        ]
        cluster_ids = [item.cluster_id for item in decisions]
        if len(cluster_ids) != len(set(cluster_ids)):
            raise InputError("clusterId values must be unique")

        eligible = [item for item in decisions if item.status == "ELIGIBLE"]
        batches = create_batches(
            eligible,
            policy["ringOrder"],
            policy["maximumBatchSize"],
            policy["maximumClustersPerFailureDomainPerBatch"],
        )

        print(
            f"RELEASE: {policy['releaseId']} -> "
            f"baseline {policy['candidateBaselineVersion']}"
        )
        print("GATE: each ring requires explicit success before its successor begins")

        for ring, batch_number, members in batches:
            predecessors = policy["requiredPredecessorRings"].get(ring, [])
            predecessor_text = ",".join(predecessors) if predecessors else "none"
            print(
                f"BATCH ring={ring} number={batch_number} "
                f"predecessors={predecessor_text}"
            )
            for member in members:
                print(
                    f"  - {member.cluster_id} failureDomain={member.failure_domain}"
                )

        for item in sorted(
            (decision for decision in decisions if decision.status != "ELIGIBLE"),
            key=lambda decision: (decision.status, decision.ring, decision.cluster_id),
        ):
            print(f"{item.status}: {item.cluster_id}")
            for reason in item.reasons:
                print(f"  - {reason}")

        if not batches:
            print("NO_PLAN: no clusters are currently eligible")
            return 1

        print(
            f"PLANNED: rollout contains bounded batches "
            f"eligible={len(eligible)} deferred="
            f"{sum(item.status == 'DEFERRED' for item in decisions)} blocked="
            f"{sum(item.status == 'BLOCKED' for item in decisions)}"
        )
        return 0
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
