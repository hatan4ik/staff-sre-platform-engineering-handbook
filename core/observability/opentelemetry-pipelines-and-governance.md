# OpenTelemetry Pipelines, Collector Architecture, and Governance

This chapter is the canonical foundation for OpenTelemetry instrumentation, Collector topology, telemetry routing, backpressure, sampling, tenancy, and operational governance.

## Interview answer in 90 seconds

> I treat observability as a production data platform with its own reliability and security requirements. Applications emit vendor-neutral metrics, logs, and traces using OpenTelemetry APIs and semantic conventions. Collectors are deployed in layers: local agents or node collectors for low-latency receipt and enrichment, then regional gateways for sampling, routing, redaction, tenancy, and export. Every queue is bounded, exporters have retry and timeout budgets, and telemetry failure must not block the application. I define explicit loss and freshness SLOs, protect sensitive attributes, control cardinality at instrumentation time, and use tail sampling only where the gateway capacity and trace-completeness model support it. The pipeline is observable through self-metrics, synthetic telemetry, queue age, rejected spans, dropped data, and backend ingest confirmation. A provider backend is replaceable; the instrumentation contract and evidence semantics remain platform-owned.

## Architectural goals

An observability pipeline should provide:

- stable instrumentation contracts;
- low application overhead;
- bounded failure behavior;
- explicit loss and delay semantics;
- secure enrichment and redaction;
- multi-tenant isolation;
- controlled cardinality and cost;
- portable routing to one or more backends;
- evidence that the pipeline itself is healthy;
- safe migration between vendors and storage systems.

## Reference architecture

```text
applications and infrastructure
  | metrics / logs / traces
  v
SDKs, auto-instrumentation, receivers
  |
  v
local or node Collector layer
  - batching
  - local enrichment
  - memory protection
  - short queues
  |
  v
regional gateway Collector layer
  - authentication
  - tenant routing
  - redaction
  - sampling
  - transformation
  - durable or bounded buffering
  |
  +-------> metrics backend
  +-------> log backend
  +-------> trace backend
  +-------> archive or secondary backend
```

Not every environment needs both layers, but high-volume fleets usually benefit from separating local receipt from regional policy and export.

## Instrumentation ownership

Define a platform contract for:

- service name and namespace;
- deployment environment;
- service version and release identifier;
- cluster, region, zone, and cell;
- request and operation names;
- status and error semantics;
- trace and span relationships;
- resource attributes;
- tenant or customer attributes allowed for telemetry;
- sensitive fields that must never be emitted;
- metric units and aggregation temporality;
- log structure and severity.

Application teams own meaningful business spans and events. The platform owns libraries, defaults, policy, validation, and transport.

## Collector deployment patterns

### Sidecar

Advantages:

- strong workload isolation;
- local buffering and policy;
- easy workload-specific configuration.

Costs:

- high resource overhead;
- lifecycle coupling;
- configuration duplication;
- more upgrade surfaces.

Use when isolation or specialized protocol handling justifies the cost.

### DaemonSet or node agent

Advantages:

- efficient host, container, and file-log collection;
- fewer collectors than sidecars;
- local endpoint for workloads.

Risks:

- node-level noisy-neighbor effects;
- loss during node failure;
- tenant separation requires explicit controls;
- host-network and file permissions increase privilege.

### Deployment or regional gateway

Advantages:

- centralized routing and policy;
- tail sampling;
- backend credential isolation;
- controlled egress;
- easier multi-backend export.

Risks:

- shared bottleneck;
- cross-zone or cross-region dependency;
- queue memory and network saturation;
- incomplete traces if routing is inconsistent.

### Agent plus gateway

This is the common scalable pattern: agents absorb protocol and node-local concerns; gateways apply regional policy and export.

## Pipeline stages

### Receivers

Examples include OTLP, Prometheus scrape, host metrics, file logs, syslog, cloud-provider streams, and language-specific protocols.

Receiver design must specify:

- authentication;
- network exposure;
- accepted tenants;
- maximum request size;
- concurrency;
- protocol timeout;
- malformed-data behavior.

### Processors

Typical processors:

- memory limiter;
- batch;
- resource and attribute enrichment;
- filtering;
- transformation;
- redaction;
- metric aggregation;
- span or log sampling;
- Kubernetes metadata enrichment.

Processor order matters. For example, redact before export and apply memory protection before queues can exhaust the process.

### Exporters

Each exporter needs:

- timeout;
- retry policy;
- bounded queue;
- authentication and rotation;
- endpoint and TLS validation;
- failure classification;
- backpressure behavior;
- observability for accepted, failed, retried, and dropped data.

## Failure semantics

### Rule 1 — application availability wins

Telemetry emission must not block critical application work indefinitely. Use asynchronous export and bounded buffering.

### Rule 2 — loss must be visible

A best-effort pipeline is acceptable only when dropped or delayed telemetry is measured and reported.

### Rule 3 — no infinite buffering

Unbounded queues turn a backend outage into memory exhaustion or disk exhaustion.

### Rule 4 — retries are bounded

Collector retries should not amplify a backend outage. Use backoff, jitter, queue limits, and drop or spill policies.

### Rule 5 — preserve emergency evidence intentionally

For critical audit or security events, use a separate durability contract rather than assuming the general telemetry path is lossless.

## Memory protection and backpressure

The Collector is often memory-bound under backend slowdown.

Monitor:

- process RSS and heap;
- receiver accepted and refused items;
- processor dropped items;
- exporter queue size and capacity;
- enqueue failures;
- retry count;
- oldest queued item age;
- export latency;
- backend rejection and throttle rate.

Use:

- memory limiter;
- bounded sending queues;
- batch sizing;
- per-tenant limits;
- separate pipelines for critical and high-volume data;
- horizontal scaling with stable routing;
- disk-backed queues only with clear durability and capacity limits.

## Sampling

### Head sampling

Decision is made near trace creation.

Advantages:

- predictable cost;
- low pipeline load;
- simple routing.

Limitation: the sampler does not know the final outcome and may miss rare errors or slow traces.

### Tail sampling

Decision is made after collecting spans for a trace.

Advantages:

- retain errors, latency outliers, or selected cohorts;
- better diagnostic value.

Costs:

- requires trace affinity;
- memory and wait-time overhead;
- incomplete-trace handling;
- gateway scaling complexity;
- loss during collector restart.

### Practical policy

Combine:

- baseline probabilistic sample;
- always retain important errors and selected critical journeys where feasible;
- higher sampling for canaries and incident cohorts;
- exemplars linking metrics to traces;
- temporary incident sampling with expiry;
- privacy and cost limits.

Never claim all errors are retained unless the pipeline can prove trace completeness and capacity under peak failure volume.

## Metrics and cardinality

High cardinality is often created at instrumentation time.

Avoid labels such as:

- raw user ID;
- request ID;
- full URL with identifiers;
- unbounded error message;
- timestamp;
- pod UID when long-term aggregation does not need it;
- arbitrary tenant value without quotas and governance.

Prefer bounded dimensions and move high-cardinality detail into traces or structured logs with controlled retention.

## Logs

Structured logs should include:

- timestamp;
- severity;
- service and version;
- operation;
- trace and span IDs where available;
- event name;
- stable error code;
- safe cohort dimensions;
- message and bounded context.

Do not depend on free-text parsing for critical alerts or SLOs.

## Security and privacy

Controls include:

- workload identity instead of static exporter keys;
- TLS and endpoint authentication;
- namespace and tenant isolation;
- attribute allowlists;
- token, password, and personal-data redaction;
- regional residency routing;
- retention by data class;
- least-privilege backend credentials;
- audit logs for configuration and query access;
- separate security/audit event guarantees.

Redaction should occur as close to the source as practical. Once sensitive data reaches multiple backends, deletion becomes harder.

## Multi-tenancy

Isolate tenants through:

- authenticated source identity;
- explicit tenant mapping;
- per-tenant quotas;
- separate queues or pipelines for high-risk tenants;
- backend namespace or project separation;
- query authorization;
- cost attribution;
- cardinality limits;
- noisy-neighbor detection.

Do not trust a tenant ID supplied only as an arbitrary application attribute.

## Pipeline SLOs

Define per signal and criticality:

- accepted telemetry rate;
- end-to-end delivery success;
- p95 and p99 freshness delay;
- drop and rejection rate;
- trace completeness or partial-trace rate;
- metric scrape and export gaps;
- log ingestion lag;
- configuration propagation time;
- backend query availability;
- synthetic telemetry detection time.

A useful objective might state that 99.9% of production service metrics arrive within a defined freshness window, excluding explicitly classified client-side invalid data.

## Synthetic telemetry

Continuously emit known telemetry with unique but bounded identifiers through every pipeline.

Verify:

- receipt at the local collector;
- passage through gateways;
- arrival in each backend;
- queryability;
- expected enrichment;
- correct tenant routing;
- redaction;
- alert evaluation.

This detects silent pipeline gaps that self-metrics alone may miss.

## Incident workflow

### Symptoms

- dashboards show gaps;
- traces disappear during an application incident;
- one tenant overwhelms the gateway;
- collector memory rises;
- backend rejects or throttles data;
- logs arrive late;
- attributes or trace context disappear;
- alerts stop evaluating despite healthy applications.

### Bound the failure

Compare:

- signal type;
- source service and language;
- collector layer;
- region, zone, and tenant;
- receiver, processor, exporter, and backend;
- release or configuration version;
- sampled versus unsampled traffic;
- application telemetry versus infrastructure telemetry.

### Stabilize

1. protect applications from synchronous telemetry overhead;
2. stop a bad configuration or unbounded source;
3. preserve critical pipelines and shed low-value data;
4. increase bounded gateway capacity if the exporter/backend can accept it;
5. route to an approved secondary or archive path;
6. reduce temporary incident sampling if it threatens stability;
7. restore backend connectivity or credentials;
8. verify synthetic telemetry and end-to-end freshness.

## Configuration delivery

Treat Collector configuration as code:

- schema validation;
- static checks;
- secret separation;
- canary deployment;
- bounded rollout rings;
- configuration hash and version attributes;
- automatic rollback on queue, drop, or freshness regressions;
- compatibility tests for receivers, processors, and exporters;
- documented ownership of each route.

## Weak answers to avoid

- “Install the OTel Collector.”
- “Send everything to the vendor.”
- “Tail sampling keeps every error.”
- “Telemetry cannot be dropped.”
- “Use pod name as a metric label everywhere.”
- “The observability platform does not need an SLO.”
- “Add more collectors” without identifying exporter or backend limits.

## Adversarial follow-ups

### Why use agents and gateways?

Agents handle local receipt and node-specific collection; gateways centralize regional policy, credentials, sampling, and backend routing. The layers separate failure and ownership concerns.

### What happens when the backend is unavailable?

Queues and retries absorb a bounded window, loss or spill follows explicit policy, applications remain available, and pipeline loss/freshness alerts fire. Critical audit data uses a separate durability contract.

### How do you prevent cardinality incidents?

Instrumentation standards, allowlists, CI validation, per-tenant budgets, backend limits, and rapid identification of the source attribute and release.

### What proves recovery?

Collector self-metrics normalize, queues drain without overload, synthetic telemetry arrives and is queryable with correct attributes, backend freshness recovers, and no critical signal remains silently absent.

## Principal-level review checklist

- instrumentation semantics are platform-owned and versioned;
- application emission is asynchronous and bounded;
- collectors have explicit topology and failure domains;
- every queue, timeout, and retry is bounded;
- cardinality is governed before backend ingestion;
- sampling policy matches diagnostic and cost goals;
- sensitive data is removed early;
- tenants have authenticated identity and quotas;
- pipeline SLOs include loss and freshness;
- synthetic telemetry proves end-to-end operation;
- configuration rolls out progressively with rollback evidence.
