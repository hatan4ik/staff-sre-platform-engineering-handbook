# Observability Pipeline Governance Lab

This standard-library Python lab demonstrates bounded telemetry handling and governance decisions.

## What it proves

- critical synthetic and SLO signals are admitted before debug data;
- metric labels with unbounded identifiers are rejected;
- per-tenant quotas prevent one source from monopolizing the pipeline;
- bounded queues make telemetry loss explicit;
- accepted-data freshness is measured;
- error and slow traces are retained by policy;
- ordinary trace sampling is deterministic.

## Run

```bash
cd labs/observability/01-telemetry-pipeline
python3 telemetry_lab.py
python3 telemetry_lab.py --json
python3 -m unittest -v test_telemetry_lab.py
```

## Interview exercise

Explain:

1. why telemetry must not block the application;
2. which signals should be protected first during a backend outage;
3. why raw user and request identifiers are unsafe metric labels;
4. why loss and freshness are separate pipeline SLIs;
5. the difference between head and tail sampling;
6. how a synthetic signal detects silent end-to-end pipeline failure.

## Production translation

Map the same invariants to OpenTelemetry Collector receiver, processor, queue, and exporter self-metrics. Add authenticated tenancy, redaction, retention classes, backend confirmation, and progressive configuration rollout.

This lab validates policy logic; it does not claim to benchmark a real Collector or storage backend.
