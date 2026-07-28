# High-Volume Observability Platform: OpenTelemetry, Sampling, Cost, and Reliability

## Purpose

This chapter describes how to design and operate a multi-tenant telemetry platform for metrics, logs, traces, profiles, events, and change evidence without allowing cardinality, ingestion spikes, or collector failure to become a production incident.

## Staff/Principal answer

> I treat observability as a reliability-critical data platform, not a collection of dashboards. I define the investigations and SLO decisions the platform must support, standardize OpenTelemetry resource identity, separate collection from storage, and use regional buffering, load balancing, backpressure, and tenant quotas. Metrics retain low-cardinality operational truth; traces use head or tail sampling with guaranteed error and high-latency retention; logs are structured and governed; profiles are selectively enabled. I measure telemetry loss, delay, sampling decisions, cardinality, query latency, and cost per tenant. The application must continue serving if the telemetry pipeline is impaired, while the platform preserves enough external and local evidence to diagnose that impairment.

## Architecture

```text
applications / hosts / gateways / cloud services
             |
      local agents or SDK exporters
             |
     regional collector gateways
             |
   routing / sampling / redaction / quotas
             |
  metrics | logs | traces | profiles | archive
             |
     query, alerting, incident and SLO systems
```

Separate these concerns:

- instrumentation and semantic conventions;
- collection and buffering;
- processing and governance;
- durable storage;
- query and alerting;
- evidence retention and compliance.

## Data contracts

Every signal should carry stable resource identity where applicable:

- service name and namespace;
- deployment environment;
- cluster, region, and availability zone;
- version, release, and build digest;
- tenant or cohort only where privacy and cardinality policy permit;
- trace and request identifiers;
- ownership metadata.

Do not place unbounded user IDs, URLs, exception text, pod UIDs, or arbitrary request values into metric labels.

## Signal roles

### Metrics

Best for bounded, aggregatable operational truth and alerts.

Use:

- counters for events;
- histograms for latency and size;
- gauges only for meaningful current state;
- recording rules for expensive repeated queries;
- exemplars to connect metrics to traces.

Protect the platform with label allowlists, cardinality budgets, and pre-ingestion rejection or transformation.

### Traces

Best for request-path causality and distributed latency.

Sampling strategy:

- deterministic head sampling for baseline coverage;
- tail sampling for errors, high latency, rare routes, or protected tenants;
- explicit priority sampling for incident cohorts;
- bounded decision windows and memory;
- consistent propagation across services.

Sampling decisions must be measurable. “No traces found” may mean no traffic, broken propagation, export failure, or sampling loss.

### Logs

Best for discrete events and detailed state transitions.

Require:

- structured fields;
- severity discipline;
- stable event names;
- redaction and tokenization policy;
- rate limits and duplicate suppression;
- retention tiers.

Avoid using raw logs as the only source for high-frequency metrics when a native metric is cheaper and more reliable.

### Profiles

Best for CPU, allocation, lock, and runtime-hotspot analysis. Enable continuously only where overhead and privacy are understood; otherwise use targeted or adaptive profiling.

## Collector topology

### Agent layer

Responsibilities:

- local discovery and enrichment;
- batching and compression;
- limited buffering;
- node or sidecar isolation where required;
- endpoint failover.

### Gateway layer

Responsibilities:

- tenant authentication and quotas;
- load balancing;
- tail-sampling coordination;
- redaction and transformation;
- routing to signal-specific backends;
- durable or bounded queues;
- drop accounting.

Avoid a single global collector fleet. Use regional cells so one region, tenant, or backend cannot consume all telemetry capacity.

## Backpressure and failure behavior

The observability platform must not cause the application outage it is meant to explain.

Rules:

1. exporters use bounded memory and queues;
2. application threads do not block indefinitely on telemetry;
3. retries have budgets and jitter;
4. collectors shed lower-value data before exhausting memory;
5. telemetry drops are counted by signal, tenant, reason, and stage;
6. critical security or audit evidence uses a separately engineered durable path where required;
7. local or edge evidence remains available during backend loss.

Prioritized shedding example:

1. duplicate debug logs;
2. successful high-volume traces already represented by metrics;
3. verbose informational logs;
4. noncritical profiles;
5. preserve errors, high-latency traces, change events, audit records, and critical-journey metrics as long as possible.

## Cardinality governance

Define a budget per service and tenant.

Track:

- active series and growth rate;
- top labels by cardinality contribution;
- bytes per signal and tenant;
- rejected points and logs;
- query fanout and scan volume;
- unused metrics and dashboards;
- cost per retained useful event.

Governance workflow:

- SDK and CI linting;
- schema registry or semantic-convention checks;
- preproduction load tests;
- production quotas;
- owner notification;
- temporary quarantine or label dropping;
- remediation and verification.

## Multi-tenancy

Isolate tenants through:

- authenticated ingestion identity;
- per-tenant limits and queues;
- storage and query boundaries;
- encryption and access control;
- noisy-neighbor protection;
- retention classes;
- cost attribution;
- deletion and legal-hold controls.

A shared dashboard folder is not a tenancy boundary.

## Alert quality

Alerts should be derived from user impact, error-budget burn, and actionable platform failure—not raw telemetry volume alone.

For the telemetry platform itself, alert on:

- ingestion success and end-to-end delay;
- collector refusal, queue saturation, restarts, and memory pressure;
- exporter failures and retry exhaustion;
- sampling-policy errors;
- storage write failures;
- query latency and timeout;
- missing expected telemetry from protected services;
- alert-evaluation delay;
- sudden cardinality growth.

Use an independent synthetic signal to verify the telemetry path end to end.

## Incident investigation workflow

1. Validate the user-impact alert through an independent signal.
2. Check telemetry freshness and completeness before trusting dashboards.
3. Determine which signal or cohort is missing.
4. Inspect instrumentation, agent, gateway, routing, storage, and query stages.
5. Compare one successful and one failed request with paired traces and logs.
6. Correlate deployments, configuration, sampling, and schema changes.
7. Restore critical evidence first; do not flood the platform by disabling all sampling.
8. Verify that delayed queues drain without corrupting event time or alert semantics.

## SLOs

Suggested platform SLIs:

- accepted telemetry percentage by signal and protected tenant;
- end-to-end freshness;
- critical-trace retention probability;
- metrics remote-write success;
- alert-evaluation timeliness;
- query availability and p95/p99 latency;
- dropped-data ratio by reason;
- cardinality-budget compliance;
- cost per service or tenant;
- time to apply an incident sampling override.

## Migration strategy

For a legacy agent or vendor migration:

1. define the semantic and query parity contract;
2. dual-emit a narrow cohort;
3. compare counts, histograms, trace continuity, and alert results;
4. migrate dashboards and runbooks;
5. test backend and collector failure;
6. expand by service ring;
7. remove the old path only after retention and incident evidence requirements are met.

## Adversarial follow-ups

**Why not collect 100% of traces?**  
At scale it may be economically and operationally unsustainable. The goal is enough representative and protected evidence to answer important questions, with explicit sampling guarantees and measurements.

**Should telemetry be lossless?**  
Not every signal. Audit or compliance streams may require durable loss-resistant delivery; debug logs and successful traces usually need bounded best-effort delivery. Treat signals according to business value.

**Would you use one vendor?**  
Vendor selection is secondary to open instrumentation, export control, data contracts, retention, portability, and operational ownership.

## Weak answers to avoid

- “Install OpenTelemetry and Grafana.”
- “Store every log forever.”
- “Add user ID as a metric label.”
- “Disable sampling during every incident.”
- “If dashboards are empty, the service is healthy.”
- “Telemetry can block the request because observability is important.”
