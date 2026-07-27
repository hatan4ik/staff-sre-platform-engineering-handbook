#!/usr/bin/env python3

import unittest

from telemetry_lab import (
    TelemetryItem,
    TelemetryPipeline,
    deterministic_trace_sample,
    loss_rate,
    run_scenario,
)


class PipelineTests(unittest.TestCase):
    def test_critical_items_are_admitted_before_debug(self) -> None:
        pipeline = TelemetryPipeline(capacity_units=3, per_tenant_units=3)
        report = pipeline.ingest(
            [
                TelemetryItem("debug", "a", "log", "debug", 2, {"service": "a"}),
                TelemetryItem(
                    "critical", "b", "metric", "critical", 2, {"service": "b"}
                ),
            ]
        )
        by_id = {item.item_id: item for item in report.decisions}
        self.assertTrue(by_id["critical"].accepted)
        self.assertFalse(by_id["debug"].accepted)
        self.assertEqual(by_id["debug"].reason, "queue_full")

    def test_forbidden_metric_label_is_rejected(self) -> None:
        pipeline = TelemetryPipeline(capacity_units=10, per_tenant_units=10)
        report = pipeline.ingest(
            [
                TelemetryItem(
                    "bad",
                    "a",
                    "metric",
                    "normal",
                    1,
                    {"service": "api", "request_id": "abc"},
                )
            ]
        )
        self.assertFalse(report.decisions[0].accepted)
        self.assertEqual(report.decisions[0].reason, "forbidden_metric_label")

    def test_tenant_quota_limits_noisy_neighbor(self) -> None:
        pipeline = TelemetryPipeline(capacity_units=10, per_tenant_units=3)
        report = pipeline.ingest(
            [
                TelemetryItem("a1", "a", "log", "normal", 2, {"service": "a"}),
                TelemetryItem("a2", "a", "log", "normal", 2, {"service": "a"}),
                TelemetryItem("b1", "b", "log", "normal", 2, {"service": "b"}),
            ]
        )
        by_id = {item.item_id: item for item in report.decisions}
        self.assertTrue(by_id["a1"].accepted)
        self.assertEqual(by_id["a2"].reason, "tenant_quota")
        self.assertTrue(by_id["b1"].accepted)

    def test_loss_rate_is_explicit(self) -> None:
        pipeline = TelemetryPipeline(capacity_units=1, per_tenant_units=1)
        report = pipeline.ingest(
            [
                TelemetryItem("one", "a", "log", "normal", 1, {}),
                TelemetryItem("two", "b", "log", "normal", 1, {}),
            ]
        )
        self.assertEqual(loss_rate(report), 0.5)


class SamplingTests(unittest.TestCase):
    def test_error_and_slow_traces_are_retained(self) -> None:
        self.assertTrue(
            deterministic_trace_sample(
                "error", error=True, latency_ms=20, baseline_rate=0.0
            )
        )
        self.assertTrue(
            deterministic_trace_sample(
                "slow", error=False, latency_ms=700, baseline_rate=0.0
            )
        )

    def test_baseline_sampling_is_deterministic(self) -> None:
        first = deterministic_trace_sample(
            "stable-trace-id", error=False, latency_ms=20, baseline_rate=0.25
        )
        second = deterministic_trace_sample(
            "stable-trace-id", error=False, latency_ms=20, baseline_rate=0.25
        )
        self.assertEqual(first, second)


class ScenarioTests(unittest.TestCase):
    def test_full_scenario(self) -> None:
        result = run_scenario()
        self.assertTrue(result["passed"])
        self.assertTrue(all(result["invariants"].values()))


if __name__ == "__main__":
    unittest.main()
