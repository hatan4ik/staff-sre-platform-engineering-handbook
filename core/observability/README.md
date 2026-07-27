# Observability, Evidence, and Diagnostic Systems

This module owns reusable observability principles for Staff/Principal SRE and Platform Engineering.

## Canonical chapters

1. [Evidence beyond dashboards](evidence-beyond-dashboards.md)

Planned additions:

- OpenTelemetry architecture and Collector pipelines.
- Metrics, cardinality, histograms, and exemplars.
- Distributed tracing and context propagation.
- Structured logging and retention.
- Continuous profiling and eBPF evidence.
- Alert quality and symptom-based paging.
- High-volume telemetry platform design.
- Observability cost, governance, and tenant isolation.

## Core principle

```text
dashboards detect and orient
raw evidence explains
experiments verify
user SLIs prove recovery
```

## Ownership rule

Reusable telemetry models, evidence hierarchy, correlation, instrumentation, sampling, cardinality, retention, diagnostic workflow, alerting, and observability-platform design belong here. Cloud tracks should add only provider-specific products, queries, quotas, and service integrations.
