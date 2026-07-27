#!/usr/bin/env python3
"""Deterministic observability-pipeline governance lab.

Demonstrates:
- bounded queues;
- critical-signal priority;
- per-tenant quotas;
- cardinality policy;
- deterministic trace sampling;
- visible telemetry loss and freshness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence


FORBIDDEN_METRIC_LABELS = {
    "user_id",
    "request_id",
    "trace_id",
    "timestamp",
    "raw_url",
    "error_message",
}


@dataclass(frozen=True)
class TelemetryItem:
    item_id: str
    tenant: str
    signal: str  # metric, log, trace, synthetic
    priority: str  # critical, normal, debug
    size_units: int
    attributes: Mapping[str, str]
    age_seconds: int = 0

    def __post_init__(self) -> None:
        if self.signal not in {"metric", "log", "trace", "synthetic"}:
            raise ValueError(f"unsupported signal: {self.signal}")
        if self.priority not in {"critical", "normal", "debug"}:
            raise ValueError(f"unsupported priority: {self.priority}")
        if self.size_units <= 0:
            raise ValueError("size_units must be positive")
        if self.age_seconds < 0:
            raise ValueError("age_seconds must be non-negative")


@dataclass(frozen=True)
class PipelineDecision:
    item_id: str
    accepted: bool
    reason: str


@dataclass(frozen=True)
class PipelineReport:
    decisions: tuple[PipelineDecision, ...]
    accepted_units: int
    dropped_units: int
    accepted_items: int
    dropped_items: int
    max_accepted_age_seconds: int


class TelemetryPipeline:
    def __init__(
        self,
        *,
        capacity_units: int,
        per_tenant_units: int,
        metric_label_value_limit: int = 64,
    ) -> None:
        if capacity_units <= 0:
            raise ValueError("capacity_units must be positive")
        if per_tenant_units <= 0:
            raise ValueError("per_tenant_units must be positive")
        if metric_label_value_limit <= 0:
            raise ValueError("metric_label_value_limit must be positive")
        self.capacity_units = capacity_units
        self.per_tenant_units = per_tenant_units
        self.metric_label_value_limit = metric_label_value_limit

    def _cardinality_reason(self, item: TelemetryItem) -> str | None:
        if item.signal != "metric":
            return None
        forbidden = FORBIDDEN_METRIC_LABELS.intersection(item.attributes)
        if forbidden:
            return "forbidden_metric_label"
        if any(
            len(str(value)) > self.metric_label_value_limit
            for value in item.attributes.values()
        ):
            return "metric_label_value_too_long"
        return None

    def ingest(self, items: Sequence[TelemetryItem]) -> PipelineReport:
        priority_rank = {"critical": 0, "normal": 1, "debug": 2}
        ordered = sorted(
            enumerate(items),
            key=lambda pair: (priority_rank[pair[1].priority], pair[0]),
        )
        accepted_units = 0
        dropped_units = 0
        tenant_units: dict[str, int] = {}
        decisions: list[PipelineDecision] = []
        accepted_ages: list[int] = []

        for _, item in ordered:
            cardinality_reason = self._cardinality_reason(item)
            if cardinality_reason:
                decisions.append(
                    PipelineDecision(item.item_id, False, cardinality_reason)
                )
                dropped_units += item.size_units
                continue

            used_by_tenant = tenant_units.get(item.tenant, 0)
            if used_by_tenant + item.size_units > self.per_tenant_units:
                decisions.append(
                    PipelineDecision(item.item_id, False, "tenant_quota")
                )
                dropped_units += item.size_units
                continue

            if accepted_units + item.size_units > self.capacity_units:
                decisions.append(PipelineDecision(item.item_id, False, "queue_full"))
                dropped_units += item.size_units
                continue

            accepted_units += item.size_units
            tenant_units[item.tenant] = used_by_tenant + item.size_units
            accepted_ages.append(item.age_seconds)
            decisions.append(PipelineDecision(item.item_id, True, "accepted"))

        by_id = {decision.item_id: decision for decision in decisions}
        stable = tuple(by_id[item.item_id] for item in items)
        accepted_items = sum(1 for decision in stable if decision.accepted)

        return PipelineReport(
            decisions=stable,
            accepted_units=accepted_units,
            dropped_units=dropped_units,
            accepted_items=accepted_items,
            dropped_items=len(items) - accepted_items,
            max_accepted_age_seconds=max(accepted_ages, default=0),
        )


def deterministic_trace_sample(
    trace_id: str,
    *,
    error: bool,
    latency_ms: int,
    baseline_rate: float = 0.10,
    slow_threshold_ms: int = 500,
) -> bool:
    if not 0 <= baseline_rate <= 1:
        raise ValueError("baseline_rate must be between 0 and 1")
    if latency_ms < 0:
        raise ValueError("latency_ms must be non-negative")
    if error or latency_ms >= slow_threshold_ms:
        return True
    digest = hashlib.sha256(trace_id.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big") / 2**64
    return value < baseline_rate


def loss_rate(report: PipelineReport) -> float:
    total = report.accepted_items + report.dropped_items
    return 0.0 if total == 0 else report.dropped_items / total


def run_scenario() -> dict[str, object]:
    items = [
        TelemetryItem(
            "synth",
            "platform",
            "synthetic",
            "critical",
            1,
            {"route": "collector-to-backend"},
            age_seconds=2,
        ),
        TelemetryItem(
            "slo-metric",
            "tenant-a",
            "metric",
            "critical",
            2,
            {"service": "checkout", "operation": "purchase"},
            age_seconds=3,
        ),
        TelemetryItem(
            "bad-metric",
            "tenant-a",
            "metric",
            "normal",
            2,
            {"service": "checkout", "user_id": "customer-123"},
            age_seconds=1,
        ),
        TelemetryItem(
            "normal-trace",
            "tenant-b",
            "trace",
            "normal",
            3,
            {"service": "catalog"},
            age_seconds=4,
        ),
        TelemetryItem(
            "debug-log-1",
            "tenant-c",
            "log",
            "debug",
            3,
            {"service": "search"},
            age_seconds=8,
        ),
        TelemetryItem(
            "debug-log-2",
            "tenant-c",
            "log",
            "debug",
            3,
            {"service": "search"},
            age_seconds=9,
        ),
    ]

    pipeline = TelemetryPipeline(capacity_units=8, per_tenant_units=4)
    report = pipeline.ingest(items)
    decisions = {item.item_id: item for item in report.decisions}

    invariants = {
        "synthetic_signal_preserved": decisions["synth"].accepted,
        "critical_slo_metric_preserved": decisions["slo-metric"].accepted,
        "unbounded_metric_label_rejected": (
            decisions["bad-metric"].reason == "forbidden_metric_label"
        ),
        "normal_trace_preserved": decisions["normal-trace"].accepted,
        "debug_data_shed_first": (
            not decisions["debug-log-1"].accepted
            and not decisions["debug-log-2"].accepted
        ),
        "loss_is_visible": report.dropped_items > 0 and loss_rate(report) > 0,
        "freshness_is_measured": report.max_accepted_age_seconds == 4,
        "errors_are_sampled": deterministic_trace_sample(
            "trace-error", error=True, latency_ms=50, baseline_rate=0.0
        ),
        "slow_traces_are_sampled": deterministic_trace_sample(
            "trace-slow", error=False, latency_ms=900, baseline_rate=0.0
        ),
        "ordinary_trace_can_be_dropped": not deterministic_trace_sample(
            "trace-normal", error=False, latency_ms=50, baseline_rate=0.0
        ),
    }

    return {
        "report": {
            **asdict(report),
            "decisions": [asdict(item) for item in report.decisions],
            "loss_rate": loss_rate(report),
        },
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
        print("Observability pipeline governance lab")
        print(f"passed: {result['passed']}")
        print(f"loss rate: {result['report']['loss_rate']:.2%}")
        for name, passed in result["invariants"].items():
            print(f"- {name}: {'PASS' if passed else 'FAIL'}")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
