# Question 8 — EKS API Latency Doubles While Worker Nodes Remain Healthy

## Interview prompt

API latency on Amazon EKS suddenly doubles while worker nodes remain healthy. How would you investigate using CloudWatch, AWS X-Ray, Prometheus, and Grafana?

## What the interviewer is testing

The interviewer is testing whether you understand that “nodes are healthy” eliminates very little. Latency can double because of application saturation, dependency latency, queueing, retries, DNS, service-mesh behavior, load-balancer routing, one bad cohort, or control-plane and networking pressure.

The strongest answer uses metrics to locate the boundary, traces to allocate latency across the request, logs to explain the slow spans, and profiles or runtime evidence to explain CPU and lock behavior.

---

## 90-second Staff/Principal answer

> I first define the latency symptom precisely: which endpoint, percentile, Region, AZ, tenant, version, and time window changed, and whether throughput or error rate changed with it. “Average latency doubled” is insufficient; I compare p50, p95, and p99 and identify whether the problem is universal or cohort-specific.
>
> In CloudWatch and Grafana I correlate ALB target response time, request rate, 4xx and 5xx, pod CPU throttling, memory, restarts, HPA desired versus available replicas, pending pods, CoreDNS latency, network errors, and database or cache saturation. I use Prometheus histograms to calculate latency by route, status, pod, AZ, version, and dependency, while controlling label cardinality.
>
> Then I sample slow requests in X-Ray or OpenTelemetry traces and compare them with healthy traces. I determine where the extra time appears: load balancer, ingress, application compute, service-to-service call, DNS, database, cache, queue, or retry. I search logs by trace ID and correlate deployment events, configuration changes, autoscaling actions, and AWS Health or CloudTrail events.
>
> I mitigate according to evidence—stop a bad rollout, shift traffic from an unhealthy cohort, scale the saturated tier, disable an expensive feature, reduce retry amplification, or protect the dependency with load shedding. I prove recovery at the user SLI and verify that the latency distribution and saturation signals normalize.

---

## 1. Define the latency signal

Before opening dashboards, establish:

| Dimension | Questions |
|---|---|
| Endpoint | One route, one service, or every API? |
| Percentile | p50, p95, p99, or maximum? |
| Cohort | Version, pod, node, AZ, Region, tenant, client, or protocol? |
| Throughput | Did RPS increase, decrease, or remain flat? |
| Errors | Are timeouts, 429s, 5xx, or retries increasing? |
| Start time | Did it align with a deployment, scaling event, certificate rotation, or dependency failover? |
| Duration | Persistent, periodic, or burst-only? |
| Business effect | Slow response only, failed transaction, queue backlog, or abandoned user operation? |

### Why percentiles matter

A doubled average can be caused by:

- every request becoming moderately slower
- a small fraction becoming extremely slow
- changed traffic mix toward an expensive endpoint
- retries being counted differently

Compare the full histogram and request mix.

---

## 2. Incident hypothesis tree

```text
API latency doubled
|
+-- edge/load balancer
|   +-- one AZ or target cohort slow
|   +-- connection/TLS behavior changed
|   +-- WAF or edge processing overhead
|
+-- Kubernetes routing
|   +-- ingress/controller saturation
|   +-- Service or EndpointSlice imbalance
|   +-- mesh proxy retries or queueing
|   +-- DNS latency
|
+-- application
|   +-- CPU throttling
|   +-- garbage collection
|   +-- lock/thread-pool contention
|   +-- connection-pool exhaustion
|   +-- expensive code path or feature flag
|
+-- dependency
|   +-- database query/lock/failover
|   +-- cache miss/hot key/eviction
|   +-- downstream service latency
|   +-- third-party throttling
|
+-- capacity control loop
    +-- HPA signal delayed or incorrect
    +-- pods pending
    +-- node ready but pod startup slow
    +-- load balancer target registration delay
```

“Worker nodes healthy” does not rule out any of these except obvious node-unready failure.

---

## 3. Start with the user-facing RED signals

For each service and route, inspect:

- **Rate:** requests per second or transactions per second
- **Errors:** failures, timeouts, cancellations, and rejected requests
- **Duration:** p50, p95, p99, and histogram distribution

Also inspect saturation:

- active requests
- queue length
- thread or worker utilization
- connection-pool usage
- CPU throttling
- memory pressure
- database connections and locks

### Compare before and after

Use the same traffic segment and query window.

```text
baseline: 30–60 minutes before the event
incident: first 15–30 minutes of degradation
current: most recent stable window
```

Long dashboard windows can smooth away the exact transition.

---

## 4. CloudWatch investigation

### Load balancer metrics

For ALB, compare:

- `RequestCount`
- `TargetResponseTime`
- target and load-balancer 4xx/5xx
- healthy and unhealthy host count
- rejected connections
- new and active connections
- target reset count

Break down by load balancer, target group, and Availability Zone where possible.

Interpretation examples:

```text
ALB TargetResponseTime increased, app span increased
    -> backend or dependency likely

Client-visible latency increased, TargetResponseTime stable
    -> edge, client network, TLS, WAF, or response transfer path

One AZ target cohort slower
    -> pod, node, subnet, dependency path, or zonal network cohort
```

### Container Insights

Use OTel Container Insights for new EKS deployments where appropriate. Compare:

- pod CPU and memory
- node and pod network throughput and errors
- restarts
- pod count and pending state
- filesystem and ephemeral storage
- cluster and namespace saturation

A node can be Ready while pods are CPU-throttled or one namespace is saturated.

### Application Signals

Where enabled, CloudWatch Application Signals can expose service operations, latency, faults, errors, and service-level objectives. Use it to identify the service or dependency edge whose latency changed.

Do not treat automatic topology as infallible. Missing instrumentation, unsupported libraries, sampling, or asynchronous work can leave gaps.

### Logs Insights

Search around the transition time:

```sql
fields @timestamp, @message, trace_id, route, status, duration_ms
| filter duration_ms > 500
| sort @timestamp desc
| limit 200
```

Group slow requests:

```sql
fields route, duration_ms, version, az
| filter duration_ms > 500
| stats count(*) as slow_requests,
        pct(duration_ms, 50) as p50,
        pct(duration_ms, 95) as p95,
        pct(duration_ms, 99) as p99
  by route, version, az
| sort slow_requests desc
```

Use log anomaly detection or the Logs Insights anomaly command to surface new patterns, changed frequency, or unusual tokens. Treat anomalies as leads, not root-cause proof.

### CloudWatch investigations

CloudWatch investigations can correlate metrics, logs, deployment events, AWS Health events, CloudTrail changes, X-Ray traces, and Logs Insights findings to propose hypotheses.

Use it as an evidence accelerator. Validate every suggested causal relationship against timestamps and authoritative telemetry before remediation.

---

## 5. Prometheus investigation

### Request latency histogram

A conventional metric:

```text
http_server_request_duration_seconds_bucket
```

p99 by route:

```promql
histogram_quantile(
  0.99,
  sum by (le, service, route) (
    rate(http_server_request_duration_seconds_bucket[5m])
  )
)
```

By version and AZ:

```promql
histogram_quantile(
  0.99,
  sum by (le, service, route, version, availability_zone) (
    rate(http_server_request_duration_seconds_bucket[5m])
  )
)
```

### Request rate

```promql
sum by (service, route) (
  rate(http_server_requests_total[5m])
)
```

### Error rate

```promql
sum by (service, route) (
  rate(http_server_requests_total{status=~"5.."}[5m])
)
/
sum by (service, route) (
  rate(http_server_requests_total[5m])
)
```

### In-flight requests

```promql
sum by (service) (http_server_active_requests)
```

### CPU throttling

```promql
sum by (namespace, pod) (
  rate(container_cpu_cfs_throttled_seconds_total{container!=""}[5m])
)
```

Compare with CPU usage and declared limits. A pod can show moderate average CPU but suffer burst throttling that harms p99.

### HPA and serving capacity

```promql
kube_horizontalpodautoscaler_status_desired_replicas
-
kube_horizontalpodautoscaler_status_current_replicas
```

Also compare:

- desired replicas
- current replicas
- available replicas
- ready endpoints
- pending pods

### Pod scheduling

```promql
sum by (namespace) (
  kube_pod_status_phase{phase="Pending"}
)
```

Correlate with scheduler events and reasons; not every Pending pod is a capacity issue.

### CoreDNS

Inspect:

- query duration
- response codes
- request volume
- cache behavior
- forward-plugin errors
- pod CPU throttling

DNS latency can appear as application latency, especially when connection reuse decreases or a rollout increases cold connections.

### Cardinality discipline

Do not add raw user IDs, request IDs, URLs with unbounded parameters, or session tokens as metric labels.

Use logs and traces for high-cardinality request identity. Use bounded labels such as service, route template, status class, version, AZ, and tenant tier only where cardinality is controlled.

---

## 6. Grafana workflow

Create a focused investigation view rather than opening every dashboard.

### Row 1 — user impact

- request rate
- p50/p95/p99 latency
- error rate
- SLO burn rate

### Row 2 — release and cohort

- latency by version
- latency by AZ
- latency by pod
- deployment event annotations

### Row 3 — application saturation

- CPU usage and throttling
- memory and GC pause
- active requests
- thread or worker pool
- connection pool

### Row 4 — Kubernetes capacity

- HPA desired/current/available
- pending pods
- node provisioning time
- pod startup and readiness time

### Row 5 — dependencies

- database query latency and locks
- cache latency and hit ratio
- downstream service p99
- queue age and depth

Use shared dashboard variables for cluster, namespace, service, route, version, and AZ.

A dashboard is useful when it supports a hypothesis. It is not a substitute for one.

---

## 7. X-Ray and OpenTelemetry tracing

### Select slow traces

Compare:

- slow and normal traces for the same route
- traces from failing and healthy versions
- traces from different AZs
- traces before and after the change

Ask:

```text
Where did the additional duration appear?
```

Possible span patterns:

```text
root server span slow, child spans normal
    -> application queueing, compute, lock, GC, or missing child instrumentation

one database span slow
    -> query, lock, connection acquisition, failover, or network path

many downstream spans repeated
    -> retry amplification

DNS/connect span slow
    -> resolver, connection reuse, NAT, TLS, or network issue

large gap between spans
    -> uninstrumented queueing, thread starvation, runtime pause, or async boundary
```

### Trace attributes

Useful bounded attributes:

- service name and version
- route template
- HTTP status
- AWS Region and AZ
- Kubernetes namespace, pod, and node
- database system and operation
- retry count
- tenant tier or cell

Do not put secrets, tokens, or unbounded personal data in trace attributes.

### Sampling

Low fixed-rate sampling can miss rare p99 failures. Consider:

- head sampling for broad coverage
- tail sampling for errors and high latency
- temporary incident sampling increase with cost and privacy controls

Sampling changes must not overload the telemetry pipeline during an incident.

### Trace-to-log correlation

Include trace and span IDs in structured logs.

```json
{
  "trace_id": "...",
  "span_id": "...",
  "route": "/payments/{id}",
  "duration_ms": 842,
  "dependency": "aurora-writer",
  "retry_count": 2
}
```

Trace identifies the slow boundary; logs explain local application behavior.

---

## 8. Application runtime investigation

### CPU throttling versus CPU saturation

Check both:

- host/container CPU usage
- cgroup throttled time
- runnable queue
- application thread pool

A low average over five minutes can hide millisecond-level throttling bursts.

### Garbage collection

Inspect:

- pause duration
- allocation rate
- heap occupancy
- full collection frequency
- container memory limit

A deployment that increases allocation can double latency without changing node health.

### Thread or event-loop saturation

Check:

- active versus maximum threads
- task queue length
- blocked or waiting threads
- event-loop delay
- lock contention

Capture thread dumps or profiles before restarting when safe.

### Connection pools

Measure acquisition wait separately from query or network time.

Common pools:

- database
- Redis/cache
- HTTP client
- TLS connection

An apparently slow database span may include 500 ms waiting for a client connection and only 10 ms executing the query.

### Profiles

Use continuous profiling or an incident profile to locate:

- hot functions
- lock contention
- allocation pressure
- system calls
- off-CPU wait

Profiles answer questions that metrics and traces cannot.

---

## 9. Kubernetes and networking investigation

### Endpoint imbalance

Inspect EndpointSlices and target registration. Determine whether traffic is concentrated on:

- one version
- one AZ
- one small set of pods
- pods with stale readiness

### Readiness and warmup

A pod can become Ready before:

- caches warm
- JIT compilation stabilizes
- database pools fill
- route tables or model data load

Compare latency by pod age.

### Service mesh or proxy

Inspect:

- upstream request time
- pending request queue
- circuit breaker overflow
- retry count
- connection pool
- mTLS handshake errors
- sidecar CPU throttling

A proxy retry can hide errors while doubling latency.

### Network path

Check:

- retransmits and resets
- cross-AZ traffic shift
- NAT path
- DNS
- security appliances
- VPC CNI or pod ENI issues

Use flow evidence and packet capture only when simpler telemetry cannot resolve the boundary and the capture is operationally safe.

---

## 10. Dependency investigation

### Aurora/RDS

Inspect:

- database load
- query latency
- wait events
- locks
- connection count
- failover or maintenance events
- reader/writer endpoint behavior
- replication lag

Use Performance Insights or the current database performance tooling available in the environment.

### DynamoDB

Inspect:

- throttled requests
- consumed capacity
- successful request latency
- hot partition indicators
- retry count

### ElastiCache

Inspect:

- cache hit ratio
- command latency
- connections
- evictions
- CPU
- hot keys
- failover events

### SQS or stream consumers

For asynchronous API flows, inspect:

- age of oldest message
- queue depth
- consumer throughput
- poison-message retries
- downstream completion latency

---

## 11. Change correlation

Overlay:

- application deployments
- configuration and feature-flag changes
- HPA or Karpenter configuration changes
- mesh or ingress upgrades
- CoreDNS or CNI updates
- certificate and secret rotation
- database failover or parameter changes
- security-group and route changes
- AWS Health events

Use:

- Git and GitOps history
- CI/CD events
- Kubernetes audit logs
- CloudTrail
- CloudWatch deployment events

Correlation is not causation, but a precise timestamp sharply narrows the search.

---

## 12. Mitigation patterns

### Bad application version

- stop rollout
- restore known-good digest
- preserve slow trace and runtime evidence
- verify rollback by version-specific latency

### CPU or worker saturation

- add safe replicas
- remove an incorrect CPU limit
- reduce expensive work
- enforce concurrency limit and load shedding
- fix sizing after stabilization

### Dependency latency

- reduce retry count
- enforce deadlines
- use cached or degraded response
- shift reads or traffic if the data design supports it
- protect dependency with circuit breakers and bulkheads

### One bad AZ or cell

- drain or reduce traffic to the cohort
- verify stateful dependency paths
- avoid moving all traffic into an already saturated destination

### Autoscaling lag

- increase minimum replicas or warm capacity
- pre-scale predictable events
- reduce image and startup time
- correct HPA signal and resource requests

---

## 13. Prove recovery

Require:

- p50/p95/p99 return to baseline or SLO
- user success rate recovers
- SLO burn rate normalizes
- slow-trace frequency decreases
- retries and active requests normalize
- queues drain
- dependency saturation recovers
- all cohorts recover
- no hidden error increase from aggressive timeout or shedding changes

---

## Adversarial follow-ups

### “Nodes are under 40% CPU, so why inspect CPU?”

Node average CPU hides pod-level limits and throttling. A container can be throttled while the node has spare CPU because its cgroup limit is lower than available host capacity.

### “Prometheus shows the route is slow. Why do you need traces?”

Metrics show that the route is slow and how broadly. Traces allocate the request duration across service and dependency boundaries and expose retry or fan-out behavior.

### “X-Ray shows the database span is slow. Is the database the root cause?”

Not necessarily. The span may include client-pool wait, DNS, connect, TLS, or retries. I correlate database-side telemetry and application pool metrics.

### “Would you scale pods immediately?”

Only if evidence shows application saturation and dependencies can accept more load. Scaling a retrying frontend against a saturated database can worsen the incident.

### “What if only p99 changed?”

I segment by pod, AZ, version, endpoint, and dependency, then inspect rare slow traces. Tail-only regressions often indicate one cohort, lock contention, GC pauses, cold paths, or retries.

---

## Weak answers to avoid

- “Check CPU and memory in Grafana.”
- using only average latency
- assuming healthy nodes mean infrastructure is not involved
- increasing replicas without checking downstream saturation
- reading traces without comparing healthy samples
- ignoring CPU throttling because node CPU is low
- restarting pods before preserving previous logs, profiles, or thread evidence
- adding unbounded labels to Prometheus during the incident
- declaring recovery from one green dashboard panel

---

## Closing statement

> I treat latency as time that must be allocated. Metrics tell me where and for whom latency changed, traces show which boundary consumed the extra time, logs and profiles explain why, and controlled mitigation proves whether the hypothesis was correct.