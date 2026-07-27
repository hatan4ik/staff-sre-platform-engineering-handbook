# Real OpenTelemetry Collector Integration Lab

This Docker-based exercise starts an actual OpenTelemetry Collector, sends a synthetic OTLP/HTTP trace, and verifies that the configured pipeline receives, batches, and exports the expected evidence.

## Pipeline under test

```text
OTLP/HTTP receiver
  -> memory limiter
  -> batch processor
  -> debug exporter
```

## Invariants

- the Collector configuration starts successfully;
- OTLP/HTTP accepts a standards-shaped trace payload;
- resource attributes survive the pipeline;
- the span name and test attribute reach the exporter;
- the application-facing send path completes without waiting indefinitely;
- the test fails when the Collector exits, rejects the payload, or loses expected evidence.

## Run

Requirements: Docker and curl.

```bash
cd labs/observability/02-otel-collector-integration
chmod +x run.sh
./run.sh
```

The default image is pinned through `COLLECTOR_VERSION`. Override it to qualify a newer release:

```bash
COLLECTOR_VERSION=0.157.0 ./run.sh
```

Keep the container for inspection:

```bash
KEEP_CONTAINER=true ./run.sh
docker logs sre-otel-collector-integration
```

## Evidence

The runner writes:

- `collector-output.txt` — Collector startup and debug-exporter output;
- `otlp-response.json` — OTLP/HTTP response body.

These generated files are intended for local or CI evidence and should not be committed.

## Production extension

Replace the debug exporter with a test backend and add:

- authenticated OTLP ingestion;
- redaction and transform policy;
- per-tenant routing and quotas;
- exporter outage and bounded-queue tests;
- synthetic freshness measurement;
- tail-sampling trace-affinity tests;
- configuration canary and rollback;
- backend query and alert-evaluation confirmation.

The lab proves a real Collector data path, not production throughput or durability.
