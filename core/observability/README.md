# Observability, Evidence, and Diagnostic Systems

This module owns reusable observability principles for Staff/Principal SRE and Platform Engineering.

## Canonical chapters

1. [Evidence beyond dashboards](evidence-beyond-dashboards.md) — hypothesis-driven evidence, paired healthy/affected samples, change correlation, telemetry gaps, and recovery proof.
2. [OpenTelemetry pipelines, Collector architecture, and governance](opentelemetry-pipelines-and-governance.md) — instrumentation contracts, agents and gateways, receivers/processors/exporters, bounded failure, sampling, tenancy, redaction, pipeline SLOs, and synthetic telemetry.
3. [High-volume telemetry, alert quality, tracing, and profiling](high-volume-telemetry-alerting-profiling.md) — RED/USE, histograms, cardinality, distributed tracing, continuous profiling, structured logs, paging policy, ingestion, storage tiers, query governance, and platform SLOs.

## Executable labs

- [`../../labs/observability/01-telemetry-pipeline/`](../../labs/observability/01-telemetry-pipeline/) — critical-signal preservation, tenant quotas, metric-label governance, bounded queues, visible loss, freshness, and deterministic trace sampling.
- [`../../labs/observability/02-otel-collector-integration/`](../../labs/observability/02-otel-collector-integration/) — a real OpenTelemetry Collector data path using OTLP/HTTP, memory limiting, batching, resource attributes, and debug-exporter evidence.

## Remaining expansion areas

- Collector exporter-outage, bounded-queue, backpressure, and replay tests.
- Tail-sampling trace-affinity and incomplete-trace tests.
- Backend-specific performance, retention, and migration adapters.
- eBPF profiling and packet-evidence labs.
- Alert-rule test suites tied to synthetic SLO scenarios.
- Cross-region telemetry continuity and archive replay exercises.

## Core principle

```text
dashboards detect and orient
raw evidence explains
experiments verify
user SLIs prove recovery
```

## Ownership rule

Reusable telemetry models, evidence hierarchy, correlation, instrumentation, sampling, cardinality, retention, diagnostic workflow, alerting, profiling, and observability-platform design belong here. Cloud tracks should add only provider-specific products, queries, quotas, and service integrations.
