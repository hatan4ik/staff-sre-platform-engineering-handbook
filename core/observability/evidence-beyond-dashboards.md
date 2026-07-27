# Evidence Beyond Dashboards

## Interview scenario

An alert fires for elevated errors or latency, but the standard dashboards do not reveal the cause. The service spans multiple versions, zones, dependencies, queues, network paths, and recent changes.

The Staff/Principal task is to move from aggregate symptom to raw, correlated, falsifiable evidence without creating an unbounded data hunt or changing production blindly.

---

## 1. Ninety-second Staff/Principal answer

> I first validate the alert itself: exact signal, dimensions, statistic, window, missing-data behavior, and transition time. Then I establish one UTC timeline and confirm the customer impact independently.
>
> Dashboards contain expected, pre-aggregated questions. I pivot into evidence that preserves hidden dimensions: structured logs, traces, exemplars, profiles, events, configuration and deployment history, network-flow evidence, load-balancer access records, Kubernetes events, dependency telemetry, and external synthetic artifacts. I compare one failing transaction with one healthy transaction and join them by request or trace ID, version, zone, pod, tenant-safe cohort, shard, and dependency.
>
> I use the least invasive tool that can falsify the current hypothesis. A trace can reveal the slow edge, logs can reveal the error class and cohort, a profile can reveal CPU or lock cost, and change records can establish temporal correlation. Generated anomaly or AI hypotheses are leads, not proof.
>
> I preserve queries and raw evidence, change one reversible thing, and confirm recovery through user SLIs and the affected cohort. Afterward I add the missing signal, field, runbook, or test so the same incident becomes faster to diagnose without putting unbounded cardinality or sensitive data into metrics.

### Fifteen-second version

> Validate the alert, pivot from aggregate symptoms to correlated raw evidence, test one hypothesis at a time, and use user SLIs to prove recovery.

---

## 2. Why dashboards are insufficient by design

A dashboard answers questions selected before the incident.

It usually contains:

- Bounded dimensions.
- Aggregated time series.
- Predefined routes and services.
- Expected failure modes.
- Chosen percentiles and windows.

Root cause may exist in:

- One pod or image digest.
- One zone or node image.
- One tenant-safe cohort.
- One shard or hot key.
- One WAF, gateway, or authorization rule.
- One rare exception.
- One long-lived session.
- One deployment or configuration event.
- Queueing or lock delay absent from traces.
- Traffic that never reaches the application.

The correct conclusion is not “dashboards are useless.” It is:

> Dashboards should detect impact, orient responders, and provide pivots into evidence systems that support high-cardinality investigation.

---

## 3. Validate the alert

Before following an alarm, record:

- Signal name and source.
- Exact labels or dimensions.
- Query or expression.
- Window and evaluation interval.
- Statistic, percentile, or histogram query.
- Traffic denominator.
- Missing-data behavior.
- Grouping and aggregation.
- Alert transition time.
- Recent alert-rule changes.

Questions:

```text
Does it measure a user symptom or an infrastructure proxy?
Did traffic volume change?
Is the percentile based on enough observations?
Did missing data become breaching or appear healthy?
Are histogram buckets and units correct?
Is ingestion delayed?
Is the alert duplicated across replicas or regions?
```

A misleading alert is an observability defect, but user impact must still be checked.

---

## 4. Build one incident timeline

Normalize to UTC:

```text
T0 last known healthy
T1 first user-impact evidence
T2 first telemetry change
T3 alert transition
T4 relevant deployment, configuration, dependency, or platform event
T5 mitigation
T6 recovery begins
T7 user SLI recovered
```

Account for:

- Scrape and export interval.
- Metric and log ingestion delay.
- Trace sampling.
- Batch processing.
- Clock skew.
- Configuration propagation.
- Dashboard query alignment.
- Cache and connection lifetime.

Temporal ordering is necessary but not sufficient for causality.

---

## 5. Evidence hierarchy

Use the least invasive source that can answer the question.

```text
user SLI and external synthetic
      |
      v
service RED and resource USE metrics
      |
      v
high-cardinality logs and traces
      |
      v
changes, events, configuration, topology
      |
      v
profiles, scheduler/off-CPU evidence
      |
      v
network flow and bounded packet evidence
      |
      v
crash dump or controlled reproduction
```

Each source has blind spots:

| Evidence | Strong for | Weak for |
|---|---|---|
| Metrics | Trends, rates, saturation, alerts | Individual causality and rare dimensions |
| Logs | Error detail, events, high-cardinality fields | Unlogged work and timing gaps |
| Traces | Request path and latency attribution | Unsampled failures, background work, queue gaps |
| Profiles | CPU, allocation, lock, off-CPU cost | Individual customer transaction |
| Change records | Who changed what and when | Proving the change caused impact |
| Flow logs | Network metadata and accept/reject | Payload, process correctness, precise packet timing |
| Packet capture | Protocol details | Application semantics, long-term trend, low overhead |
| Synthetic | External user-path behavior | Every real client and data shape |

Use multiple independent sources for load-bearing conclusions.

---

## 6. Start with paired evidence

Capture one failing and one successful transaction for the same operation.

Join fields:

- Request ID.
- Trace ID and span ID.
- UTC timestamp.
- Route and operation.
- Status-code issuer.
- Region, zone, cell, cluster, node, and pod.
- Image digest and configuration revision.
- Safe tenant or feature cohort.
- Shard, partition, and dependency.
- Retry attempt and remaining deadline.

Example:

```text
healthy:
  gateway -> api v1 in zone-a -> cache -> shard-2, 42 ms

failing:
  gateway -> api v2 in zone-c -> cache miss -> shard-7 timeout, 3.0 s
```

The next step is to separate version, zone, cache state, and shard rather than immediately blaming the final timeout.

---

## 7. Structured logs

Useful fields:

```text
timestamp
severity
service and operation
request_id and trace_id
status and error_class
latency_ms
region, zone, cell, cluster, pod, node
image_digest and config_version
safe tenant or feature cohort
shard and dependency
retry_attempt and deadline_remaining_ms
```

Investigation patterns:

### Error classes

```sql
SELECT service, route, error_class, COUNT(*) AS errors
FROM logs
WHERE timestamp BETWEEN :start AND :end
  AND severity = 'ERROR'
GROUP BY service, route, error_class
ORDER BY errors DESC;
```

### Version and zone

```sql
SELECT version, zone,
       COUNT(*) AS requests,
       SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END) AS failures
FROM requests
WHERE timestamp BETWEEN :start AND :end
GROUP BY version, zone;
```

### New pattern

Compare incident and baseline windows for:

- Newly appearing exception templates.
- Frequency shifts.
- New dependency or status.
- New configuration version.
- New caller or route.

Cautions:

- Text logs without fields are difficult to aggregate.
- Logging every payload creates security and cost risk.
- Exceptions after the initial fault may be secondary effects.
- Log ingestion can fail during the incident.
- Duplicate retries can inflate counts.

Preserve the query, time window, and result used in the decision.

---

## 8. Distributed traces

Compare failing and healthy traces by:

- Route.
- Version.
- Zone or cell.
- Status.
- Latency.
- Tenant-safe cohort.
- Dependency.

Common patterns:

```text
edge span fails before application
  -> edge, WAF, TLS, routing, or target boundary

application root span fails immediately
  -> validation, auth, configuration, or code

one child span dominates
  -> dependency or connection acquisition

repeated child spans
  -> retry amplification

large gap without a span
  -> queue, lock, scheduler, GC, or missing instrumentation

trace terminates abruptly
  -> timeout, cancellation, process exit, or telemetry loss
```

Trace cautions:

- Head sampling can miss rare errors.
- Tail sampling requires buffering and resilient collectors.
- Context propagation can break at queues, async tasks, and third parties.
- A missing span may mean uninstrumented code, not no work.
- Instrumentation overhead and attribute volume need governance.

Temporarily increase error or latency sampling only through a bounded policy and within telemetry capacity.

---

## 9. Metrics, histograms, and exemplars

Metrics provide efficient detection and comparison.

Use:

- RED for services: rate, errors, duration.
- USE for resources: utilization, saturation, errors.
- Queue length and age.
- Concurrency and admission rejection.
- Dependency latency and failure.
- Error-budget burn.

### Histograms

Histograms allow aggregation of latency distributions across instances when bucket design is appropriate.

Check:

- Units.
- Bucket boundaries.
- Native versus classic representation.
- Query correctness.
- Sufficient sample count.
- Whether client and server latency differ.

Averages hide tails. A percentile without traffic count can overstate a tiny sample.

### Exemplars

Exemplars can connect an unusual metric observation to a representative trace.

They accelerate:

```text
p99 spike -> exemplar -> trace -> logs -> pod/version/dependency
```

They do not replace representative sampling or broad cohort analysis.

---

## 10. Profiles and kernel evidence

When telemetry shows saturation but not mechanism, use profiles.

Types:

- CPU profile.
- Allocation profile.
- Heap profile.
- Lock or mutex profile.
- Thread dump.
- Event-loop lag.
- Off-CPU or scheduler profile.
- I/O latency profile.
- eBPF-based network or syscall evidence.

Questions:

- Which code consumes CPU?
- Which allocation retains memory?
- Where do threads block?
- Is delay on CPU, off CPU, in reclaim, or in I/O?
- Is one core handling excessive softirq or lock work?

Use bounded collection windows and understand overhead.

A profile from a healthy replica does not explain a failing cohort. Capture the affected version, node, or request path.

---

## 11. Change and configuration evidence

Correlate the incident window with:

- Git commits and deployment records.
- Image digest promotion.
- Feature-flag changes.
- Configuration and Secret revisions.
- Infrastructure API audit events.
- Policy and identity changes.
- Certificate and trust-bundle rotation.
- Node image and kernel rollout.
- Database schema and migration.
- Dependency releases.

Record:

- Actor or automation identity.
- Change ID.
- Resource and previous value.
- Start and completion time.
- Rollout cohort.
- Approval and test evidence.

A nearby change is a hypothesis, not proof. Validate mechanism and cohort correlation.

Change systems should provide bidirectional links:

```text
incident -> deployment/configuration
change -> metrics/logs/traces during rollout
```

---

## 12. Kubernetes and runtime evidence

Capture:

```bash
kubectl get pods -A -o wide
kubectl get events -A --sort-by=.lastTimestamp
kubectl get endpointslice -A
kubectl rollout history deployment/<name> -n <namespace>
kubectl describe pod <pod> -n <namespace>
kubectl logs <pod> -n <namespace> -c <container> --previous
```

Look for:

- Pod replacement versus container restart.
- Previous termination reason and exit code.
- OOM, throttling, and node pressure.
- Readiness and startup transitions.
- Endpoint version and zone mix.
- Pending and scheduling reason.
- Controller reconciliation error.
- Admission mutation.
- Config and Secret checksum.
- Node image and runtime.
- Network policy and CNI state.

Pod phase is a coarse state. Inspect individual containers and owner chains.

---

## 13. Network evidence

Evidence sources:

- DNS query and resolver logs.
- Load-balancer and gateway access logs.
- WAF logs.
- Flow logs.
- Modeled reachability.
- Host socket state.
- Retransmission and drop counters.
- Service-mesh flow telemetry.
- Bounded packet capture.

Questions:

- Did the request resolve to the expected destination?
- Did the connection establish?
- Which side reset or timed out?
- Was traffic accepted in both directions?
- Was one IP family, zone, or target different?
- Did MTU, retransmission, or conntrack pressure appear?

A flow accepted by a firewall can still fail at the application. A modeled reachable path can still experience runtime loss or saturation.

Packet capture is a targeted escalation, not a default first step.

---

## 14. External synthetic evidence

External synthetics reveal failures before the request enters internal telemetry.

Capture:

- DNS result.
- TLS handshake.
- Step timing.
- HTTP status and selected headers.
- Redirect chain.
- Screenshot or browser console for UI paths.
- HAR or equivalent timing artifact.
- Trace linkage where supported.
- Test location, IP family, and auth flow.

Test business operations, not only `/health`.

Use multiple paths to distinguish:

- Global versus regional.
- Public versus private network.
- IPv4 versus IPv6.
- Anonymous versus authenticated.
- New versus existing session.
- Page shell versus transaction completion.

Synthetic credentials must be protected and narrowly authorized.

---

## 15. Events and dependency evidence

Check:

- Cloud or platform health events.
- Database failover and maintenance.
- Queue throttling or partition movement.
- Certificate authority or identity-provider event.
- Registry or artifact outage.
- Third-party provider status and request evidence.
- Capacity and quota events.

Public status does not prove account- or tenant-specific health. Conversely, a provider event may be correlated but irrelevant to the actual request path.

The application still owns graceful behavior for dependency failure.

---

## 16. Generated hypotheses and AI-assisted investigation

Automated systems can correlate:

- Metrics.
- Logs.
- Traces.
- Changes.
- Topology.
- Platform events.

Safe operating sequence:

```text
generated hypothesis
      |
      v
supporting raw evidence
      |
      v
falsifiable prediction
      |
      v
bounded test
      |
      v
reversible mitigation
```

Do not execute a remediation because the explanation sounds plausible.

Validate:

- Resource identity.
- Account, environment, and region.
- Timeline ordering.
- Cohort correlation.
- Data freshness.
- Permission and security impact.
- Reversibility.

Human incident command remains accountable.

---

## 17. Hypothesis ledger

Maintain a concise table:

| Hypothesis | Supporting evidence | Disconfirming test | Status | Owner |
|---|---|---|---|---|
| New version causes 5xx | Error rate higher on digest B | Route small safe cohort to digest A | Testing | App lead |
| Zone-c network path fails | Resets only on targets in c | Compare old version in c | Rejected | Network lead |
| Shard 7 saturated | Trace child latency and throttles | Query shard metrics and same tenant through replica | Confirmed | Data lead |

This prevents repeated work and narrative drift.

Mark:

- Proposed.
- Testing.
- Confirmed.
- Rejected.
- Mitigated but not causal.

---

## 18. High-cardinality design

Do not put unbounded values such as raw user ID, request ID, or URL into metric labels.

Use:

- Bounded labels in metrics.
- Structured logs for detailed events.
- Traces for request-level context.
- Exemplars linking metrics to traces.
- Columnar or indexed analytics for incident windows.
- Pseudonymized identifiers.
- Retention and access controls.

Cardinality governance includes:

- Approved attribute dictionary.
- Per-tenant and per-team budgets.
- Drop and redaction rules.
- Collector-side limits.
- Sampling policy.
- Cost and query monitoring.
- Emergency diagnostic override with expiration.

Telemetry must remain available during incidents; uncontrolled cardinality can cause the observability system itself to fail.

---

## 19. Telemetry pipeline failure

Treat observability as a distributed system.

Failure modes:

- Collector overload.
- Export queue full.
- Backend throttling.
- Network partition.
- Schema change.
- Invalid attribute explosion.
- Clock skew.
- Sampling misconfiguration.
- Tenant noisy neighbor.
- Authentication or certificate failure.

Monitor the monitor:

- Accepted, dropped, retried, and queued telemetry.
- Export latency and failure.
- Collector CPU and memory.
- Sampling rate.
- Attribute cardinality.
- Backend ingestion lag.
- Query latency and error.
- Cost by signal and tenant.

Loss of telemetry during a service incident is evidence and should be on the timeline.

---

## 20. Mitigation and recovery

Evidence should change a decision.

Possible mitigations:

- Stop or roll back a release.
- Remove one bad target or cohort.
- Disable a feature.
- Shift traffic.
- Restore configuration or policy.
- Shed optional load.
- Reduce retries.
- Expand a constrained pool.
- Bypass a failed dependency through a tested degraded mode.

After mitigation verify:

- User SLI.
- Affected cohort.
- Tail latency.
- Error-budget burn.
- Backlog and retries.
- Dependency stability.
- No new security or correctness failure.
- Telemetry pipeline health.

Do not declare recovery because a dashboard line moved before the full propagation window.

---

## 21. Prevention

After the incident add only evidence that will drive a future decision.

Examples:

- Status-code issuer field.
- Image digest and config revision.
- Zone, cell, shard, and feature dimensions.
- Deadline and retry attempt.
- Error-class taxonomy.
- Trace-log correlation.
- External business synthetic.
- Change annotations.
- Profile trigger on sustained saturation.
- Runbook query and expected interpretation.
- Alert based on user symptom or fast burn.

Avoid creating a permanent dashboard panel for every one-time detail. Prefer navigable drill-down and reusable diagnostic dimensions.

---

## 22. Common weak answers

### “Add more dashboards”

More aggregates do not automatically expose high-cardinality or raw causal evidence.

### “Search the logs”

State the hypothesis, fields, comparison, time window, and decision the query informs.

### “The AI investigation found the root cause”

Generated hypotheses require source evidence and a falsifiable test.

### “Turn on debug logging everywhere”

This can overload the service and telemetry pipeline, expose secrets, and still miss uninstrumented queues.

### “Trace every request forever”

Full tracing may be too expensive and can violate data policy. Use governed sampling, tail policies, and targeted diagnostics.

### “Metrics say the node is fine”

Host averages can hide one cgroup, core, queue, disk, NIC, or workload cohort.

### “No logs means no error”

The request may never reach the application, logging may fail, or the process may terminate before flushing.

---

## 23. Adversarial interview questions

### Where do you start when there are thousands of signals?

Start from one user symptom and one time window. Validate the alert, draw the request path, and compare one failing and healthy transaction. Pull only evidence that separates the current hypotheses.

### How do you investigate a rare failure missed by tracing?

Use error logs, access logs, client or synthetic evidence, and controlled error-aware or tail sampling. Correlate the rare cohort and increase sampling only within a bounded policy.

### When do you use profiling instead of tracing?

When the question is where CPU, allocation, lock, or off-CPU time is spent inside a process or kernel path rather than which service edge a request followed.

### How do you avoid observability cost explosion?

Bound metric labels, govern attributes, sample traces, tier retention, aggregate where appropriate, allocate budgets by tenant, and measure ingestion and query cost.

### What if telemetry sources disagree?

Check definitions, units, windows, ingestion delay, clock, aggregation, sampling, and scope. Preserve disagreement rather than forcing one narrative.

### Can a dashboard ever prove root cause?

It can contain decisive evidence, but causal confidence still depends on mechanism, timeline, cohort, and a confirming or disconfirming test.

---

## 24. Staff/Principal checklist

A strong answer includes:

- Alert validation.
- User impact and UTC timeline.
- Paired transaction comparison.
- Evidence hierarchy.
- Metrics, logs, traces, profiles, changes, and network evidence.
- High-cardinality and privacy design.
- Hypothesis ledger.
- AI hypothesis verification.
- Telemetry-pipeline health.
- Reversible mitigation.
- User-SLI recovery proof.
- Targeted prevention rather than dashboard sprawl.

---

## Related canonical material

- [`../incident-response/request-path-debugging.md`](../incident-response/request-path-debugging.md)
- [`../incident-response/cohort-analysis.md`](../incident-response/cohort-analysis.md)
- [`../linux/06-observability-debugging.md`](../linux/06-observability-debugging.md)
- [`../distributed-systems/10-observability-and-incident-labs.md`](../distributed-systems/10-observability-and-incident-labs.md)
