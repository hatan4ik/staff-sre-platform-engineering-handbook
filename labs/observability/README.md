# Executable Observability Labs

These labs turn observability architecture, telemetry governance, sampling, cardinality, loss, freshness, and alert-quality principles into deterministic exercises.

## Current lab

1. [Telemetry pipeline governance](01-telemetry-pipeline/README.md) — bounded queues, critical-signal priority, tenant quotas, metric-label policy, deterministic trace sampling, visible loss, and freshness.

## Run

```bash
cd labs/observability/01-telemetry-pipeline
python3 telemetry_lab.py
python3 -m unittest -v test_telemetry_lab.py
```

## Ownership rule

Labs must prove diagnostic and platform invariants. A successful run should demonstrate not only accepted telemetry, but also controlled rejection, loss visibility, freshness evidence, tenant isolation, and safe sampling decisions.
