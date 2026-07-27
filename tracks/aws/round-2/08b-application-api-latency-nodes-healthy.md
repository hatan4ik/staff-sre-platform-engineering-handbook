# Question 8B — Application API Latency Doubles While EKS Nodes Remain Healthy

## Why this companion chapter exists

The phrase “API latency on EKS” is ambiguous.

- [`08-eks-api-latency-nodes-healthy.md`](08-eks-api-latency-nodes-healthy.md) treats it as **Kubernetes API-server/control-plane latency**.
- This chapter treats it as **customer-facing application API latency**, matching the prompt's use of CloudWatch, X-Ray, Prometheus, and Grafana.

A strong candidate should clarify which API the interviewer means, then answer the correct path.

---

## Interview prompt

Application API latency on Amazon EKS suddenly doubles while worker nodes remain healthy. How would you investigate using CloudWatch, AWS X-Ray, Prometheus, and Grafana?

## 90-second Staff/Principal answer

> I first define the symptom precisely: endpoint, percentile, Region, AZ, tenant, version, and time window. Healthy nodes eliminate very little; pods can be throttled, ingress can queue, retries can multiply, or a database, cache, DNS, or downstream service can be slow.
>
> In CloudWatch and Grafana I correlate ALB target response time, request rate, 4xx and 5xx, pod CPU throttling, memory, HPA desired versus available replicas, pending pods, CoreDNS latency, network errors, and database or cache saturation. In Prometheus I calculate latency histograms by route, status, version, pod, and AZ while controlling label cardinality.
>
> I then compare slow and healthy X-Ray or OpenTelemetry traces for the same route. I identify where the added time appears: load balancer, ingress, application queueing, service-to-service call, DNS, database, cache, or retry. I correlate trace IDs with structured logs and overlay deployment, configuration, autoscaling, CloudTrail, and AWS Health events.
>
> I mitigate from evidence—stop a bad rollout, shift traffic from a failing cohort, scale the actually saturated tier, reduce retry amplification, disable an expensive feature, or protect a dependency with load shedding. Recovery is proven through user-facing latency and success SLIs, not node health.

---

## 1. Define the latency signal

Establish:

| Dimension | Questions |
|---|---|
| Endpoint | One route, one service, or every API? |
| Percentile | p50, p95, p99, or maximum? |
| Cohort | Version, pod, node, AZ, Region, tenant, client, or protocol? |
| Throughput | Did RPS increase, decrease, or remain flat? |
| Errors | Are timeouts, 429s, 5xx, cancellations, or retries increasing? |
| Start time | Did it align with deployment, scaling, failover, or configuration change? |
| Business effect | Slow only, failed transaction, queue backlog, or abandonment? |

Do not investigate only average latency. A doubled average can mean every request became slower or a small tail became extremely slow.

---

## 2. Hypothesis tree

```text
Application API latency doubled
|
+-- edge/load balancer
|   +-- one AZ or target cohort slow
|   +-- connection/TLS behavior changed
|   +-- WAF or origin processing overhead
|
+-- Kubernetes routing
|   +-- ingress saturation
|   +-- Service/EndpointSlice imbalance
|   +-- mesh proxy queueing or retries
|   +-- DNS latency
|
+-- application runtime
|   +-- CPU throttling
|   +-- GC pause or allocation regression
|   +-- thread/event-loop contention
|   +-- connection-pool exhaustion
|   +-- expensive code path or feature flag
|
+-- dependency
|   +-- database query, lock, or failover
|   +-- cache miss, hot key, or eviction
|   +-- downstream service latency
|   +-- third-party throttling
|
+-- capacity realization
    +-- HPA signal delayed or wrong
    +-- pods pending
    +-- pod startup or target registration slow
```

---

## 3. CloudWatch workflow

### ALB

Compare:

- `RequestCount`
- `TargetResponseTime`
- load-balancer versus target 4xx/5xx
- healthy and unhealthy targets
- rejected connections
- active and new connections
- resets

Interpretation:

```text
TargetResponseTime rises with application trace duration
    -> backend or dependency likely

Client latency rises but TargetResponseTime stays flat
    -> edge, client network, TLS, WAF, or transfer path

One AZ or target group rises
    -> cohort-specific pod, subnet, dependency, or routing issue
```

### OTel Container Insights

For new EKS deployments, AWS recommends OTel Container Insights. Inspect:

- pod CPU and memory
- CPU throttling
- restarts
- network throughput/errors
- pod count and pending state
- cluster and namespace saturation

A Ready node can host a throttled or memory-constrained pod.

### Application Signals

Where enabled, inspect service operations, latency, faults, errors, dependency edges, and SLO burn. Use topology as a lead; missing instrumentation can hide async or third-party paths.

### Logs Insights

```sql
fields @timestamp, route, status, duration_ms, version, az, trace_id
| filter duration_ms > 500
| stats count(*) as slow,
        pct(duration_ms, 50) as p50,
        pct(duration_ms, 95) as p95,
        pct(duration_ms, 99) as p99
  by route, version, az
| sort slow desc
```

Use log anomaly detection to find newly appearing patterns, but validate chronology and causality.

### CloudWatch investigations

Use CloudWatch investigations to correlate metrics, logs, deployment events, AWS Health events, CloudTrail changes, X-Ray traces, and Logs Insights queries. Treat generated hypotheses as evidence leads, not automatic truth.

---

## 4. Prometheus workflow

### p99 latency by route

```promql
histogram_quantile(
  0.99,
  sum by (le, service, route) (
    rate(http_server_request_duration_seconds_bucket[5m])
  )
)
```

### p99 by version and AZ

```promql
histogram_quantile(
  0.99,
  sum by (le, service, route, version, availability_zone) (
    rate(http_server_request_duration_seconds_bucket[5m])
  )
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

### CPU throttling

```promql
sum by (namespace, pod) (
  rate(container_cpu_cfs_throttled_seconds_total{container!=""}[5m])
)
```

### HPA gap

```promql
kube_horizontalpodautoscaler_status_desired_replicas
-
kube_horizontalpodautoscaler_status_current_replicas
```

Also compare desired, current, available, ready endpoints, pending pods, and target registration.

### Cardinality rule

Use bounded labels: service, route template, status class, version, AZ, and cell. Do not use raw request IDs, user IDs, or unbounded URL values as metric labels.

---

## 5. Grafana investigation layout

### User impact

- request rate
- p50/p95/p99
- error rate
- SLO burn

### Cohort and release

- latency by version
- latency by AZ
- latency by pod
- deployment annotations

### Runtime saturation

- CPU usage and throttling
- memory and GC pause
- active requests
- thread/event-loop queue
- connection pools

### Kubernetes capacity

- HPA desired/current/available
- pending pods
- node provisioning time
- pod startup and readiness time

### Dependencies

- database wait/query latency
- cache latency/hit ratio
- downstream service p99
- queue age/depth

A dashboard supports a hypothesis; it does not replace one.

---

## 6. X-Ray and OpenTelemetry tracing

Compare slow and healthy traces for the same route and cohort.

```text
root server span slow; children normal
    -> local queueing, compute, lock, GC, or missing instrumentation

one DB span slow
    -> query, lock, pool acquisition, connect, or failover

many repeated downstream spans
    -> retry amplification

DNS/connect span slow
    -> resolver, connection reuse, NAT, TLS, or network path

large gap between spans
    -> uninstrumented queueing, runtime pause, or async boundary
```

Useful bounded attributes:

- service and version
- route template
- status
- Region/AZ/cell
- namespace/pod/node
- dependency system and operation
- retry count

Correlate trace and span IDs into structured logs.

---

## 7. Runtime investigation

### CPU throttling

Node CPU below 50% does not rule out a pod hitting its cgroup CPU limit.

### Garbage collection

Inspect pause duration, allocation rate, heap occupancy, and full collection frequency. A release can increase allocation without changing node readiness.

### Thread and event-loop saturation

Inspect active/max threads, queue length, blocked threads, event-loop delay, and lock contention. Preserve thread dumps or profiles before restart when safe.

### Connection pools

Measure acquisition wait separately from network or query execution. A “slow database span” may spend most of its time waiting for a client pool slot.

### Profiling

Use profiling to identify hot functions, lock contention, allocation pressure, system calls, and off-CPU wait after metrics/traces locate the slow service.

---

## 8. Kubernetes and network checks

- EndpointSlices and target distribution by version/AZ
- readiness and warmup behavior
- pod age versus latency
- ingress or sidecar queueing
- service-mesh retries and circuit-breaker overflow
- CoreDNS latency and errors
- cross-AZ traffic shifts
- retransmits and resets
- VPC CNI or subnet IP pressure

A pod can become Ready before caches, JIT, database pools, or model data are warm.

---

## 9. Dependency checks

### Aurora/RDS

- DB load and wait events
- locks and top SQL
- connection count
- failover or maintenance
- reader/writer endpoint behavior

### DynamoDB

- throttled requests
- successful request latency
- consumed capacity
- retry count and hot-key behavior

### ElastiCache

- command latency
- hit ratio
- evictions
- connections
- hot keys
- failovers

### Queues/streams

- oldest-message age
- backlog
- consumer throughput
- poison-message retries

---

## 10. Mitigation patterns

### Bad release

Stop rollout and restore the known-good immutable digest. Preserve slow traces and runtime evidence.

### Saturated application

Add safe replicas, correct requests/limits, reduce expensive work, and enforce concurrency/load shedding.

### Saturated dependency

Reduce retries, enforce deadlines, use degraded/cached behavior, and protect the dependency from frontend scaling amplification.

### One bad AZ or cell

Drain or reduce traffic only after ensuring the destination has compute, IP, and dependency capacity.

### Autoscaling lag

Increase warm baseline, pre-scale predictable events, reduce image/startup time, and fix the HPA signal.

---

## 11. Prove recovery

Require:

- p50/p95/p99 return to baseline or SLO
- user success rate and SLO burn normalize
- slow-trace frequency falls
- retries and active requests normalize
- queues drain
- dependencies recover
- every affected cohort recovers
- no hidden error increase caused by shorter timeouts or shedding

---

## Adversarial follow-ups

### “Nodes are healthy, so why inspect CPU?”

Node health and average CPU hide pod-level cgroup throttling and runtime queueing.

### “Prometheus shows the route is slow. Why use traces?”

Metrics identify scope and frequency. Traces allocate duration across boundaries and reveal retries or fan-out.

### “X-Ray shows a slow database span. Is the database the root cause?”

Not necessarily. It can include client-pool wait, DNS, connect, TLS, retry, and query execution. I correlate database-side telemetry.

### “Would you scale immediately?”

Only if the saturated tier is identified and downstream systems can accept more load. Scaling a retrying frontend can worsen the outage.

### “What if only p99 changed?”

Segment by pod, AZ, version, route, and dependency, then inspect rare slow traces for lock, GC, cold path, or retry behavior.

---

## Weak answers to avoid

- checking only node CPU and memory
- using average latency
- scaling pods before checking dependency saturation
- inspecting traces without a healthy comparison
- ignoring CPU throttling because the node has spare CPU
- restarting before preserving previous logs, profiles, or thread evidence
- adding unbounded labels during the incident
- declaring recovery from one green panel

---

## Closing statement

> I treat latency as time that must be allocated. Metrics show where and for whom latency changed, traces show which boundary consumed the extra time, logs and profiles explain why, and controlled mitigation proves the hypothesis.