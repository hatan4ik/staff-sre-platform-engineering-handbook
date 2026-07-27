# High-Volume Telemetry, Alert Quality, Tracing, and Profiling

This chapter covers the system-design and operational decisions required to make observability useful at large scale without creating an uncontrolled cost or reliability problem.

## Interview answer in 90 seconds

> I design observability around decisions, not data volume. Critical user journeys get RED metrics and SLO burn alerts; infrastructure gets USE signals; traces preserve causality for representative and anomalous requests; structured logs carry bounded event detail; and continuous profiles explain resource consumption. The platform has per-tenant cardinality, ingest, retention, and query budgets. Histograms use intentional buckets, exemplars connect metric outliers to traces, and alerts page only for actionable user impact or imminent exhaustion. High-volume ingestion is partitioned by tenant and signal, queues are bounded, backpressure is visible, and cold or low-value data moves to cheaper retention tiers. During an incident I compare affected and healthy cohorts, link telemetry to changes, and use profiles or packet evidence when traces and dashboards are insufficient. The platform itself has loss, freshness, query, and alert-evaluation SLOs.

## Evidence roles

```text
metrics   -> detect trends, rates, saturation, and SLO burn
traces    -> show causal request paths and latency ownership
logs      -> preserve structured event details and state transitions
profiles  -> attribute CPU, memory, lock, allocation, and I/O cost
events    -> connect releases, configuration, infrastructure, and incidents
synthetics-> prove end-to-end behavior from outside the service
```

No single signal explains every failure.

## Metrics design

### RED for request-driven services

- **Rate** — accepted request or transaction rate.
- **Errors** — failures using business-correct semantics.
- **Duration** — latency distribution, not only averages.

### USE for resources

- **Utilization** — percentage of resource busy or consumed.
- **Saturation** — queued work or pressure beyond immediately available capacity.
- **Errors** — failed operations or hardware/software faults.

### Business and correctness metrics

Include:

- accepted, rejected, pending, completed, expired, and duplicate operations;
- data freshness;
- reconciliation lag;
- degraded-mode use;
- safety or policy denials;
- protected-cohort outcomes.

A 200 response is not automatically a successful business event.

## Histograms

Histograms support latency distributions and SLO calculations when bucket boundaries match the decision.

Guidelines:

- choose buckets around user and dependency objectives;
- preserve consistent bucket definitions across instances;
- avoid excessively dense buckets that multiply series;
- distinguish client-observed and server-observed latency;
- track queue, execution, and dependency latency separately;
- use native histogram capabilities only after compatibility and cost tests;
- connect outlier buckets to traces through exemplars where supported.

Averages hide tail latency and mixed cohorts.

## Cardinality governance

Series count roughly grows with the product of label values.

For labels with cardinalities `a`, `b`, and `c`:

```text
potential_series ~= a * b * c
```

One unbounded label can dominate storage, memory, and query cost.

### Safe dimensions

- service;
- operation;
- stable error code;
- region, zone, cell;
- release version;
- bounded tenant tier;
- response class;
- dependency name.

### Dangerous dimensions

- user or device ID;
- request or trace ID;
- raw URL;
- full exception text;
- arbitrary SQL or query;
- timestamps;
- UUID-like object names;
- unbounded tenant names without policy.

Move detailed identifiers to traces or logs with controlled indexing and retention.

## Distributed tracing

Tracing answers:

- where latency accumulated;
- which dependency failed;
- how retries and fan-out behaved;
- which version, cell, or cohort handled the request;
- whether context propagation broke;
- how asynchronous work relates to the initiating request.

### Trace contract

Define:

- stable span names;
- client/server/producer/consumer span roles;
- status semantics;
- required resource attributes;
- bounded request attributes;
- links for asynchronous and batch work;
- baggage restrictions;
- propagation formats;
- sampling policy;
- treatment of retries and hedged requests.

### Context propagation failures

Detect:

- new root traces in the middle of a request;
- missing parent IDs;
- inconsistent propagators;
- dropped message metadata;
- proxies that do not preserve headers;
- invalid or oversized baggage;
- trust-boundary rules that intentionally strip context.

Do not propagate sensitive or user-controlled baggage without validation.

## Continuous profiling

Profiles are useful when latency or saturation is caused by resource consumption rather than an obvious external dependency.

Profile types include:

- CPU;
- wall-clock;
- allocation;
- heap;
- mutex and lock contention;
- goroutine or thread state;
- block and I/O wait;
- off-CPU and scheduler delay;
- kernel and eBPF stack evidence.

### Profiling design

- use low-overhead continuous sampling;
- tag by service, version, environment, and bounded cohort;
- preserve symbol resolution;
- protect source paths and sensitive function arguments;
- compare healthy and affected periods;
- link profiles to releases and SLO regressions;
- validate overhead under peak load.

Profiles complement traces: a span may show that one service is slow, while a profile shows CPU spent in serialization, lock contention, garbage collection, or kernel I/O.

## Structured logging

Logs should be machine-readable events, not narrative dumps.

Recommended fields:

- timestamp and monotonic sequence where needed;
- severity;
- service, version, environment, region, and cell;
- event name;
- operation and stable error code;
- trace and span IDs;
- safe cohort dimensions;
- state transition;
- retry attempt and idempotency outcome;
- bounded message.

Avoid logging secrets, credentials, tokens, personal data, or complete request bodies by default.

## Alert design

A page should require urgent human action.

### Page on

- fast or sustained SLO burn;
- critical journey unavailable or unsafe;
- imminent exhaustion with insufficient automated mitigation;
- loss of redundancy that materially increases near-term risk;
- observability blind spot that prevents safe operation;
- security or data-integrity violation requiring response.

### Ticket or dashboard on

- slow trends;
- capacity forecasts;
- nonurgent single-instance failures;
- low-risk drift;
- informational deployment events;
- recoverable transient conditions.

### Alert contract

Each alert needs:

- user or operational impact;
- signal and threshold rationale;
- owner;
- expected first action;
- runbook or diagnostic entry point;
- suppression and maintenance behavior;
- dependency and cohort context;
- test method;
- retirement criteria.

## Multi-window burn alerts

Use short windows for fast catastrophic burn and longer windows for sustained degradation.

Conceptually:

```text
burn_rate = observed_bad_event_rate / allowed_bad_event_rate
```

Pair windows to avoid paging on brief noise while still detecting rapid budget exhaustion.

## Alert-quality metrics

Track:

- pages per service and team;
- actionable-page percentage;
- false-positive and false-negative reviews;
- duplicate-page rate;
- time to acknowledge;
- time to first useful evidence;
- alerts without owners or runbooks;
- alerts muted during real incidents;
- percentage tied to user SLIs;
- changes that introduce or retire alerts.

Alert volume is not a proxy for coverage.

## High-volume ingestion architecture

```text
producers
   |
   v
regional authenticated ingest
   |
   v
partition by tenant / signal / time
   |
   +--> hot operational store
   +--> trace or log index
   +--> stream processing and alerts
   +--> object storage / cold archive
```

Design for:

- partition-key skew;
- burst and incident amplification;
- duplicate delivery;
- late data;
- out-of-order data;
- tenant quotas;
- replay;
- retention and deletion;
- schema evolution;
- regional isolation;
- backend rebuild or migration.

## Backpressure and overload

Telemetry volume often rises during incidents.

Protect the platform with:

- per-tenant and per-signal quotas;
- bounded queues;
- priority classes;
- sampling and aggregation;
- dropping low-value debug logs first;
- preserving SLO metrics and critical audit events;
- compression and batching;
- partition expansion with tested limits;
- explicit rejection and loss metrics;
- controlled replay from durable storage.

Do not let observability overload worsen the production incident.

## Storage tiers

### Hot

- recent operational metrics, logs, traces, and profiles;
- low-latency queries;
- highest cost;
- shortest retention.

### Warm

- longer investigation window;
- reduced indexing or resolution;
- slower queries.

### Cold/archive

- compliance, historical analysis, and reprocessing;
- object storage or low-cost formats;
- explicit restore or query workflow.

Retention should follow data value, legal requirements, and investigation needs—not one global number.

## Query governance

Large queries can become production incidents.

Use:

- tenant and role authorization;
- query time and scan limits;
- concurrency limits;
- cost estimation;
- aggregation and recording rules;
- cached common queries;
- separate interactive and batch query capacity;
- audit logs;
- protected incident-response capacity.

## Change correlation

Record and correlate:

- application releases;
- feature flags;
- infrastructure changes;
- policy and configuration changes;
- certificate and secret rotations;
- autoscaling and failover events;
- dependency incidents;
- experiments and game days.

A timestamp coincidence is a hypothesis, not proof. Compare affected and unaffected cohorts.

## Observability platform SLOs

Examples:

- telemetry acceptance success;
- data freshness by signal;
- alert-evaluation delay;
- alert-delivery success;
- query availability and latency;
- trace completeness;
- profile symbolization success;
- recording-rule freshness;
- synthetic signal visibility;
- tenant-isolation violations;
- dropped or rejected telemetry.

## Incident workflow

### Symptoms

- missing metrics or logs;
- slow or failed queries;
- alert delay;
- cardinality explosion;
- trace gaps;
- profile backend overload;
- one tenant dominates ingest;
- retention or storage capacity approaches a limit.

### Stabilize

1. preserve SLO, critical security, and incident evidence;
2. identify the tenant, signal, attribute, or release causing growth;
3. enforce quotas and drop low-value data;
4. stop unbounded instrumentation or query patterns;
5. protect alert evaluation from interactive queries;
6. expand only the actual constrained stage;
7. route overflow to approved cold storage where supported;
8. verify synthetic signals and alert delivery after recovery.

## Weak answers to avoid

- “Collect all logs forever.”
- “Add Grafana dashboards.”
- “Use tracing at 100%.”
- “Alert on CPU above 80%.”
- “Profiles are too expensive for production.”
- “Cardinality is a backend problem.”
- “One global observability cluster is simpler.”

## Adversarial follow-ups

### How do you retain rare failures without tracing everything?

Use baseline head sampling, targeted higher rates for critical journeys or canaries, bounded tail sampling for selected error and latency policies, exemplars, and temporary incident sampling.

### What telemetry gets dropped first during overload?

Low-value, high-volume debug data and redundant detail. Preserve SLO metrics, critical event transitions, security/audit data under its own durability contract, and enough traces/logs to diagnose the incident.

### How do you stop a cardinality incident?

Identify the new label and source release, block or transform it at ingest, enforce per-tenant limits, roll back or patch the instrumentation, and verify series growth and query latency recover.

### What makes an alert actionable?

It indicates urgent impact or imminent risk, has a clear owner, points to useful evidence, and has a safe first action. Otherwise it should be a ticket, dashboard, or automated signal.

## Principal-level review checklist

- metrics represent business and resource semantics;
- histogram buckets match decisions;
- cardinality budgets are enforced;
- trace context and sampling are intentional;
- continuous profiles are available for key services;
- logs are structured and privacy-controlled;
- pages are tied to SLOs or imminent exhaustion;
- ingest, query, and alert capacity are isolated;
- tenants have quotas and cost attribution;
- storage tiers match value and retention needs;
- the observability platform has loss, freshness, query, and alert SLOs.
