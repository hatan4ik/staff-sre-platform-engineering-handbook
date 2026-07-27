# Question 17 — Actionable Observability with CloudWatch, OpenTelemetry, X-Ray, Prometheus, and Grafana

## Interview prompt

Design an observability platform using CloudWatch, OpenTelemetry, AWS X-Ray, Prometheus, and Grafana that provides actionable alerts without alert fatigue.

## What the interviewer is testing

The interviewer is not asking for a tool list. A Staff/Principal answer must explain:

- telemetry ownership and standards
- metrics, logs, traces, profiles, events, and changes
- collection topology and failure isolation
- cardinality, sampling, retention, and cost
- service-level objectives and alert design
- deduplication, grouping, inhibition, and routing
- platform tenancy and access control
- how telemetry behaves during the outage it must diagnose

Observability is successful when the on-call can determine impact, scope, likely boundary, and safe next action—not when the organization stores the most data.

---

## 90-second Staff/Principal answer

> I standardize instrumentation on OpenTelemetry and a service catalog. Every production service emits consistent resource attributes, request metrics, structured logs, and trace context. I use agent or DaemonSet collectors for local node and pod telemetry, regional gateway collectors for filtering, sampling, redaction, and fan-out, and independent pipelines so a trace spike cannot block critical metrics.
>
> CloudWatch holds AWS-native metrics, logs, alarms, deployment events, Application Signals, Synthetics, and account-level evidence. Traces use OpenTelemetry and can be exported to X-Ray and CloudWatch transaction search; I would not start new instrumentation on the legacy X-Ray SDK or daemon because those entered maintenance mode in February 2026. Prometheus metrics go to Amazon Managed Service for Prometheus, and Amazon Managed Grafana provides cross-source visualization and drill-down.
>
> Alerts start with SLOs and user symptoms: multi-window burn-rate alerts for availability and latency, queue age, saturation close to exhaustion, and failed synthetic business transactions. Component signals create tickets or enrich incidents unless they require immediate human action. Alertmanager or Grafana notification policies group, deduplicate, inhibit, and route alerts by service, environment, severity, and owner.
>
> I govern cardinality, sampling, retention, and cost through quotas and budgets. Every page has an owner, runbook, dashboard, impact statement, and tested escalation. We review page precision, actionability, repeat rate, acknowledgement, and time-to-mitigation, and delete or redesign alerts that do not change an operational decision.

---

## 1. Platform objectives

The observability platform should answer:

1. Are users affected?
2. Which capability, Region, cell, tenant cohort, or version is affected?
3. Where in the request or event path is time or failure introduced?
4. What changed?
5. Is the system overloaded, unavailable, or incorrect?
6. What is the safest mitigation?
7. Has recovery occurred for every affected cohort?

Non-goals:

- alerting on every anomaly
- retaining every debug event forever
- one global dashboard for every team
- replacing service ownership with a central observability team

---

## 2. Reference architecture

```text
Applications / EKS / Lambda / AWS services
       |
       +--> OpenTelemetry SDKs and auto-instrumentation
       +--> Prometheus endpoints
       +--> structured stdout/log APIs
       +--> AWS-native service metrics and events
       |
Local collection layer
       |
       +--> OTel Collector agent / EKS DaemonSet
       +--> CloudWatch agent where AWS integration requires it
       |
Regional gateway layer
       |
       +--> batching / retry / queue
       +--> redaction
       +--> tail sampling
       +--> routing / fan-out
       +--> cardinality controls
       |
       +--> CloudWatch Metrics / Logs / Application Signals
       +--> X-Ray and CloudWatch transaction search
       +--> Amazon Managed Service for Prometheus
       +--> optional OpenSearch / S3 analytics archive
       |
Amazon Managed Grafana / CloudWatch console
       |
Alert evaluation and routing
       +--> CloudWatch alarms and composite alarms
       +--> AMP rule groups and Alertmanager
       +--> Grafana alerting where selected
       +--> SNS / incident-management system / chat
```

Keep data collection, storage, query, and paging as separate failure domains.

---

## 3. Telemetry signal model

### Metrics

Best for:

- rates and ratios
- latency histograms
- saturation
- SLOs
- alert evaluation
- bounded dimensions

### Logs

Best for:

- event detail
- error context
- state transitions
- high-cardinality identity
- audit and forensic evidence

### Traces

Best for:

- request and transaction path
- latency allocation
- fan-out and retries
- dependency boundaries
- cross-service correlation

### Profiles

Best for:

- CPU hot paths
- allocation pressure
- lock contention
- off-CPU wait
- runtime behavior not visible in traces

### Events and changes

Include:

- deployments
- feature flags
- Terraform and CloudFormation changes
- Kubernetes events
- CloudTrail
- AWS Health
- autoscaling and failover events

A useful investigation combines signals on one UTC timeline.

---

## 4. OpenTelemetry standard

### Why OpenTelemetry

Use one vendor-neutral semantic and collection standard for:

- traces
- metrics where supported by the selected implementation
- logs and correlation
- resource detection
- propagation
- export to AWS and other approved backends

AWS X-Ray is transitioning its primary instrumentation direction to OpenTelemetry. The legacy X-Ray SDKs and daemon entered maintenance mode on February 25, 2026 and receive security fixes rather than new feature enhancements.

### Instrumentation policy

Every service defines:

- service name
- service namespace
- service version
- deployment environment
- Region, cell, AZ
- Kubernetes cluster, namespace, workload, pod where relevant
- route templates, not raw URLs
- dependency system and operation

Avoid attribute drift such as `service`, `service_name`, and `app` representing the same concept.

### Trace propagation

Use W3C Trace Context where ecosystem compatibility requires it, and configure AWS exporters or propagators according to the backend design.

Propagate through:

- HTTP and gRPC
- messaging attributes
- scheduled jobs
- async worker handoff
- database or external calls where instrumentation supports it

Do not put trace context in business payload fields without a documented contract.

---

## 5. Collector topology

### Agent or DaemonSet collectors

Use close-to-workload collectors for:

- node and pod metadata enrichment
- local receive endpoints
- host metrics
- log collection
- reducing direct application backend credentials

Run with:

- resource requests and limits
- topology spread
- security context restrictions
- local buffering
- health endpoints
- versioned configuration

### Gateway collectors

Use regional gateways for:

- tail sampling
- redaction
- transformation
- tenant routing
- batching and compression
- backend fan-out
- centralized policy

Run multiple replicas across AZs with load balancing and bounded queues.

### Separate pipelines

Example:

```text
critical metrics -> short queue -> CloudWatch/AMP
traces -> sampling -> X-Ray
application logs -> CloudWatch Logs
verbose debug -> sampled/archive pipeline
security audit -> independent durable pipeline
```

A trace or debug-log storm must not starve SLO metrics or security audit events.

### Backpressure

Configure:

- memory limiter
- batch processor
- persistent or bounded queue where supported
- retry with exponential backoff
- drop policy by signal priority
- self-observability

Unbounded buffering turns an observability outage into a node or application outage.

---

## 6. CloudWatch role

Use CloudWatch for:

- AWS service metrics
- custom application metrics where appropriate
- logs and Logs Insights
- alarms and composite alarms
- Synthetics canaries
- Real User Monitoring where applicable
- Application Signals and SLOs
- deployment and investigation correlation
- Container Insights

### Application Signals

Application Signals can expose service operations, latency, faults, errors, dependencies, and SLOs.

Use it to accelerate service-level triage, but validate:

- instrumentation coverage
- unsupported protocols
- asynchronous boundaries
- sampling
- correct service naming

### Container Insights

For new EKS deployments, use the current OpenTelemetry-based Container Insights path and plan migration for classic deployments.

Collect:

- cluster/node/pod resource signals
- pod restarts
- pending pods
- network and filesystem signals
- node and workload dimensions

Do not mistake infrastructure health for business health.

### Synthetics

Create canaries for critical transactions:

- login
- search
- checkout
- remote command
- read/write preference

Canaries should validate the external path, not only `/health`.

---

## 7. Prometheus and Amazon Managed Service for Prometheus

### Metric ownership

Prometheus is suited to:

- Kubernetes and application metrics
- histograms
- PromQL
- recording rules
- SLO evaluation
- Alertmanager-compatible workflows

Amazon Managed Service for Prometheus provides managed, multi-AZ, Prometheus-compatible ingestion, storage, querying, and alerting.

### Collection options

- AWS-managed EKS scraper
- self-managed Prometheus or Prometheus Agent remote write
- OpenTelemetry collector Prometheus receiver and remote write exporter

Choose based on:

- custom service discovery
- rule ownership
- local buffering
- HA requirements
- cost and operational model

### HA remote write

For paired Prometheus collectors, configure consistent `cluster` and unique `__replica__` external labels so AMP can deduplicate HA samples.

Test failover between collectors and verify no duplicate alerting.

### Histograms

Standardize latency buckets appropriate to SLOs. Poor buckets make p99 estimation meaningless.

Example:

```promql
histogram_quantile(
  0.99,
  sum by (le, service, route) (
    rate(http_server_request_duration_seconds_bucket[5m])
  )
)
```

### Recording rules

Use recording rules for:

- expensive repeated queries
- SLO rates
- normalized service metrics
- dashboard performance

Version them as code and test query behavior.

---

## 8. Amazon Managed Grafana

Use Managed Grafana as a cross-source visualization and investigation interface for:

- AMP/Prometheus
- CloudWatch
- X-Ray
- OpenSearch or approved log source
- external systems where governance permits

### Workspace strategy

Choose from:

- one workspace per trust boundary
- per-environment workspace
- central workspace with account data-source roles

Control:

- SSO through IAM Identity Center or SAML
- team and folder permissions
- data-source IAM roles
- audit
- provisioning as code

### Dashboard design

Service dashboard rows:

1. SLO and user impact
2. rate/errors/duration
3. saturation
4. dependencies
5. deployment and change annotations
6. logs and trace links
7. capacity and quota

A dashboard should guide investigation from symptom to evidence, not contain every metric.

### Dashboard ownership

Every production dashboard has:

- owner
- service tier
- linked SLO
- source repository
- last review date
- runbook links

Delete unused dashboards rather than preserving misleading operational archaeology.

---

## 9. Tracing with X-Ray and CloudWatch transaction search

### Instrument with OpenTelemetry

Use OTel SDKs or auto-instrumentation and collectors, then export to X-Ray-compatible services.

Do not begin a new platform on the maintenance-mode X-Ray SDK/daemon unless a documented legacy constraint requires it.

### Trace sampling

Use:

- head sampling for predictable baseline cost
- tail sampling for errors, high latency, rare operations, and selected tenants
- always-sample policy for critical low-volume transactions
- adaptive incident sampling with safety limits

Sampling policy should preserve:

- errors
- p99 latency examples
- new versions/canaries
- important business operations

Do not sample solely by random rate when rare failures matter.

### Trace-to-log and metric exemplars

Include trace and span IDs in structured logs.

Where supported, attach exemplars to histogram observations so a slow metric bucket links to representative traces.

### Missing spans

Monitor instrumentation health:

- trace completion rate
- orphan spans
- propagation failure
- collector export failure
- sampling changes

A clean service map can be wrong when instrumentation silently disappears.

---

## 10. Logging standard

### Structured schema

Minimum fields:

```json
{
  "timestamp": "...",
  "level": "ERROR",
  "service": "payments",
  "version": "2.14.0",
  "environment": "prod",
  "region": "us-east-1",
  "cell": "a",
  "route": "/payments/{id}",
  "request_id": "...",
  "trace_id": "...",
  "error_class": "DependencyTimeout",
  "message": "payment authorization timed out"
}
```

### Redaction

Never log:

- passwords
- access or refresh tokens
- full payment data
- private keys
- raw session cookies
- secret values

Define allow-listed fields and centralized redaction where possible.

### Log levels

- `ERROR`: failed operation requiring investigation
- `WARN`: degraded or unexpected condition
- `INFO`: bounded lifecycle and business state
- `DEBUG`: temporary or sampled detail

A repeated expected client validation error is not necessarily an application `ERROR`.

### Retention tiers

- hot operational logs
- security/audit retention
- low-cost S3 archive
- legal/compliance retention

Retention is based on use and obligation, not one default for all log groups.

---

## 11. Cardinality governance

### Dangerous metric labels

- user ID
- request ID
- session ID
- raw URL
- unbounded error message
- SQL statement
- device ID for millions of devices

### Bounded alternatives

- route template
- status class
- error class
- service/version
- Region/AZ/cell
- tenant tier, not tenant ID unless controlled

### Cardinality budget

Each team has:

- allowed metric families
- dimension limits
- expected active series
- cost budget
- review for new high-cardinality labels

Monitor top series contributors and sudden cardinality growth.

High-cardinality identity belongs in logs or traces with indexed/query controls.

---

## 12. SLO architecture

### Service-level indicators

Examples:

```text
availability = successful valid requests / valid requests
latency = requests below threshold / valid requests
freshness = events processed before deadline / events produced
correctness = valid business results / completed transactions
```

### Error budgets

Error budget translates reliability into a release and investment control.

Use:

- rolling 28- or 30-day window
- service tier
- business-approved objective
- exclusions defined narrowly
- budget policy for release slowdown or resilience work

### Multi-window burn-rate alerts

Use a fast window and slow window:

```text
fast burn: severe impact, page quickly
slow burn: sustained degradation, page or ticket according to urgency
```

This is more actionable than a fixed `error_rate > 1% for 5m` threshold across all traffic volumes.

### Low-traffic services

Use:

- longer windows
- synthetic transactions
- absolute failure guardrail
- business-event monitoring

Percentages over tiny sample counts can page noisily.

---

## 13. Alert taxonomy

### Page

A human must act now to prevent or reduce material user impact.

Required:

- user or SLO impact
- service and owner
- severity
- first investigation link
- runbook
- recent changes

### Ticket

Action is needed during working hours:

- growing capacity risk
- certificate expiry weeks away
- persistent but nonurgent error
- DR readiness drift
- cardinality or cost anomaly

### Dashboard only

Useful context but no direct action:

- pod restart under automatic recovery
- one transient retry
- autoscaler routine event
- individual node replacement

Do not page on a symptom that automation safely resolves within the SLO.

---

## 14. Alert routing and deduplication

### Alertmanager in AMP

AMP Alertmanager can:

- group
- deduplicate
- route
- silence
- inhibit

AMP Alertmanager routes to SNS topics in the same account, which then integrate with incident tooling.

### Grafana alerting

Use Grafana alerting where cross-source rules and the chosen workspace model justify it.

Avoid evaluating the same rule independently in CloudWatch, AMP, and Grafana without one authoritative pager path.

### Notification labels

Standardize:

```text
service
team
environment
severity
region
cell
slo
runbook_url
dashboard_url
```

### Grouping

Group by service and failure domain so one dependency outage creates one incident, not hundreds of pod pages.

### Inhibition

Examples:

- inhibit pod-level alerts when the service SLO page is active
- inhibit downstream symptom alerts when a known regional dependency incident is declared
- do not inhibit independent security or data-integrity alerts

### Silence and maintenance

Silences have:

- owner
- reason
- expiration
- change reference

Never create indefinite production silences.

---

## 15. Alert quality program

Measure:

- pages per on-call shift
- actionable page percentage
- false-positive and no-action rate
- duplicate pages per incident
- acknowledgement time
- mitigation time
- repeated alert frequency
- pages without runbooks
- pages caused by planned changes
- after-hours versus business-hours relevance

Review every severe incident:

- Did the right alert fire?
- What fired first?
- What was noise?
- Which evidence was missing?
- Did the alert lead to a safe decision?

Delete alerts that repeatedly produce no action.

---

## 16. Change intelligence

Overlay:

- deployments
- GitOps synchronization
- feature flags
- Terraform and CloudFormation changes
- AWS Config timeline
- CloudTrail
- autoscaling
- certificates and secrets rotation
- AWS Health

Use deployment annotations in CloudWatch and Grafana.

A metric transition without change context wastes incident time.

CloudWatch investigations can accelerate correlation and suggest hypotheses, but every hypothesis requires evidence and a falsifiable test.

---

## 17. Multi-account and multi-Region design

### Account structure

```text
workload accounts
   -> regional telemetry endpoints
   -> central or federated observability accounts
```

Use cross-account observability and data-source roles according to the organization's trust model.

### Regional independence

Each Region can:

- collect critical telemetry
- page local incidents
- retain evidence
- operate if the central dashboard or primary Region is unavailable

Do not make the only pager depend on the Region being monitored.

### Central aggregation

Centralize enough for fleet and executive views while preserving regional data-plane operation.

### Disaster recovery

Test:

- collector failure
- AMP or CloudWatch access degradation
- Grafana workspace unavailable
- SNS or incident-system delivery failure
- regional isolation

Maintain a secondary way to query raw evidence and contact responders.

---

## 18. Security and tenancy

### Access

- SSO and least privilege
- team-scoped dashboards and queries
- separate audit access
- cross-account roles
- query and data-source logging

### Telemetry injection

Treat telemetry as untrusted input.

Protect against:

- log injection
- malicious high-cardinality labels
- oversized spans
- tenant spoofing
- secret exfiltration through attributes

### Tenant isolation

For internal platform tenants:

- namespace and service ownership labels
- quotas
- per-team budgets
- workspace/folder permissions
- data access boundaries

For customer telemetry, enforce stronger data partitioning and privacy controls.

---

## 19. Cost controls

Major drivers:

- active metric series
- high-resolution custom metrics
- log ingestion and retention
- trace volume
- Grafana active users
- cross-Region transfer
- duplicate collection
- expensive queries

Controls:

- cardinality budget
- tiered retention
- trace sampling
- log filtering and debug expiration
- recording rules
- metric allow lists
- cost attribution by team/service
- anomaly alerts for telemetry spend

Do not solve an incident by permanently enabling maximum debug volume everywhere.

---

## 20. Platform-as-product operating model

Provide golden paths:

- language instrumentation libraries
- OTel collector charts
- standard dashboards
- SLO templates
- alert labels and routing
- runbook templates
- cost/cardinality tests
- local development tooling

Measure adoption:

- services with valid owner metadata
- services with SLOs
- trace propagation coverage
- actionable alert percentage
- time to onboard
- telemetry cost per request or service

The platform team owns the paved road; service teams own their operational outcomes.

---

## 21. Validation plan

1. drop one collector replica
2. disconnect backend export
3. generate trace and log surge
4. introduce high-cardinality label in staging and verify policy catches it
5. create a 5% error in one cell and test burn-rate paging
6. fail a dependency and verify alert grouping/inhibition
7. break trace propagation
8. rotate collector credentials
9. make Grafana unavailable and use fallback investigation path
10. isolate one Region
11. test silence expiration
12. verify secrets are redacted
13. run an on-call exercise from page to mitigation

---

## Adversarial follow-ups

### “CloudWatch or Prometheus?”

Both. CloudWatch is the native source for AWS services, logs, alarms, Synthetics, and Application Signals. Prometheus is strong for Kubernetes/application metrics, histograms, PromQL, and rule portability. I define ownership so the same pager is not evaluated twice.

### “Why use X-Ray if you standardize on OpenTelemetry?”

X-Ray remains an AWS trace backend and analysis capability. I instrument with OpenTelemetry and export to X-Ray rather than coupling new code to the maintenance-mode X-Ray SDK/daemon.

### “How do you prevent alert fatigue?”

Page only for urgent human action tied to user impact or imminent exhaustion; use SLO burn rates, grouping, deduplication, inhibition, ownership, and continuous page-quality review. Nonurgent conditions become tickets.

### “Would you page on every pod restart?”

No. I page if restart behavior causes or predicts service impact, such as insufficient replicas, persistent crash loop, or SLO burn. Individual automatically recovered restarts are investigation context.

### “What happens if observability goes down during the outage?”

Critical metrics and audit pipelines are independent, collectors buffer within bounds, regional operation remains possible, and responders have raw-query and alternate notification paths. Observability is itself a tiered production service.

### “Why not retain every trace?”

Cost, privacy, and query performance. I retain representative baseline traces plus all errors, high latency, canaries, and critical operations through controlled sampling.

---

## Weak answers to avoid

- “Install Prometheus and Grafana and send logs to CloudWatch.”
- one alert per component symptom
- average latency instead of histograms and SLOs
- raw user/request IDs as metric labels
- new instrumentation based on the legacy X-Ray SDK/daemon
- one collector pipeline for every signal with unbounded queues
- duplicate paging from CloudWatch, Prometheus, and Grafana
- indefinite silences
- dashboards without owner or runbook
- central observability that fails with the primary Region
- treating anomaly detection or AI hypotheses as root-cause proof

---

## Closing statement

> I design observability as a decision system. OpenTelemetry standardizes evidence, CloudWatch and X-Ray provide AWS-native operational context, Prometheus and Grafana provide powerful metric analysis, and SLO-driven alerting ensures the on-call is paged only when a human decision can materially protect users.