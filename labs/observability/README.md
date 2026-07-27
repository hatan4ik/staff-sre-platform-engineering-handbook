# Executable Observability Labs

These labs turn observability architecture, telemetry governance, sampling, cardinality, loss, freshness, and alert-quality principles into executable exercises.

## Current labs

1. [Telemetry pipeline governance](01-telemetry-pipeline/README.md) — bounded queues, critical-signal priority, tenant quotas, metric-label policy, deterministic trace sampling, visible loss, and freshness.
2. [Real OpenTelemetry Collector integration](02-otel-collector-integration/README.md) — starts a pinned Collector image, sends an OTLP/HTTP trace, and verifies receiver, memory limiter, batch processor, resource attributes, and exporter evidence.

## Run

```bash
cd labs/observability/01-telemetry-pipeline
python3 telemetry_lab.py
python3 -m unittest -v test_telemetry_lab.py

cd ../02-otel-collector-integration
chmod +x run.sh
./run.sh
```

## Ownership rule

Labs must prove diagnostic and platform invariants. A successful run should demonstrate not only accepted telemetry, but also controlled rejection, loss visibility, freshness evidence, tenant isolation, safe sampling decisions, and end-to-end operation through a real Collector where practical.
