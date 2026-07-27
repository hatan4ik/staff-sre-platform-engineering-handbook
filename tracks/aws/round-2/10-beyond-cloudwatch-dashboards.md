# Question 10 — CloudWatch Alarms Fire, but Dashboards Do Not Reveal Root Cause

## Interview prompt

CloudWatch alarms indicate elevated error rates, but dashboards do not reveal the root cause. What additional AWS tools and techniques would you use?

## What the interviewer is testing

Dashboards summarize expected signals. Root causes often live in high-cardinality dimensions, change history, individual traces, rare log patterns, configuration paths, or account-specific service events that were not placed on the dashboard.

The strongest answer moves from aggregate symptoms to raw evidence while preserving a common incident timeline.

---

## 90-second Staff/Principal answer

> I first verify the alarm expression and identify the exact metric, dimensions, period, statistic, missing-data behavior, and timestamp. Then I pivot from the aggregate into evidence that can reveal hidden dimensions.
>
> I use CloudWatch Logs Insights to query structured logs around the alarm transition, group by route, status, version, AZ, pod, tenant tier, and error class, and use log pattern or anomaly analysis to find newly appearing messages. Contributor Insights helps identify top talkers, failing URLs, source IPs, keys, or resources. I inspect Application Signals and X-Ray or OpenTelemetry traces to identify the service edge or dependency consuming time or generating faults, then correlate trace IDs back to logs.
>
> I correlate the same window with CloudTrail change events, GitOps and deployment history, AWS Config configuration timelines, and AWS Health account-specific events. For network hypotheses I use VPC Flow Logs, Reachability Analyzer, Resolver query logs, load-balancer access logs, and WAF logs. For user-path evidence I use CloudWatch Synthetics artifacts such as screenshots, HAR files, logs, and traces.
>
> I can use CloudWatch investigations to accelerate correlation across telemetry and changes, but I treat AI-generated hypotheses as leads that require verification. I preserve raw evidence, test one hypothesis at a time, mitigate safely, and add the missing diagnostic signal or runbook after the incident.

---

## 1. Validate the alarm before following it

Inspect:

- metric namespace and name
- exact dimensions
- statistic or percentile
- period and evaluation periods
- datapoints to alarm
- missing-data treatment
- metric math expression
- anomaly-detection band configuration
- composite alarm dependencies
- alarm state transition timestamp
- recent alarm configuration changes

Questions:

```text
Is the alarm measuring user failure or a proxy?
Did traffic volume change enough to distort a count-based threshold?
Is a percentile based on enough samples?
Did missing data become breaching?
Is the metric delayed or duplicated?
```

A false or misleading alarm is itself an observability defect, but do not dismiss it until user impact is checked.

---

## 2. Create one incident timeline

Normalize all evidence to UTC and record:

```text
T0 last known healthy
T1 first error-rate increase
T2 alarm entered ALARM
T3 first customer report
T4 deployment/configuration/infrastructure events
T5 mitigation action
T6 recovery begins
T7 SLI recovered
```

Aligning timestamps prevents incorrect causal claims from dashboards with different periods or ingestion delays.

---

## 3. CloudWatch Logs Insights

Dashboards usually show counts. Logs Insights exposes event detail.

### Find error classes

```sql
fields @timestamp, service, route, status, error_class, message
| filter status >= 500 or level = "ERROR"
| stats count(*) as errors by service, route, error_class
| sort errors desc
```

### Compare versions and AZs

```sql
fields version, availability_zone, status, duration_ms
| filter status >= 500
| stats count(*) as errors,
        pct(duration_ms, 95) as p95
  by version, availability_zone
| sort errors desc
```

### Search by request or trace ID

```sql
fields @timestamp, @message, trace_id, span_id, request_id
| filter trace_id = "<trace-id>"
| sort @timestamp asc
```

### New-pattern detection

Use pattern clustering and log anomaly detection to identify:

- new message templates
- sudden frequency changes
- unusual token values
- rare exception families

An anomaly is not automatically causal. Validate whether it starts before or after the user symptom.

### Query discipline

- start with a narrow incident window
- use indexed fields where configured
- avoid scanning months of logs during urgent triage
- preserve the query and result with the incident
- redact secret or personal data

---

## 4. CloudWatch Contributor Insights

Contributor Insights can rank high-cardinality contributors from logs.

Useful examples:

- top URLs generating 5xx
- top source IPs or clients causing errors
- top database keys or partitions, when safely logged
- top target IDs or pods returning failures
- top tenants by rejected requests
- top NAT destinations or network talkers

This answers:

```text
Who or what contributes most to the aggregate failure?
```

Avoid contributor keys containing secrets or uncontrolled personal identifiers.

---

## 5. CloudWatch Application Signals

Where instrumentation and service discovery are enabled, inspect:

- service and operation latency
- faults and errors
- dependency edges
- SLO status and burn
- service map changes

Look for the first edge where:

- fault rate appears
- latency increases
- call volume changes
- downstream requests multiply because of retries

Application Signals is only as complete as the instrumentation and supported topology. Verify missing asynchronous, third-party, or custom-protocol paths separately.

---

## 6. AWS X-Ray and OpenTelemetry traces

### Select traces from the incident window

Filter by:

- service
- route
- status or fault
- response time
- annotation such as version, AZ, cell, or tenant tier

Compare a failing trace with a healthy trace for the same transaction.

### Interpret trace patterns

```text
edge span fails before application
    -> TLS, WAF, routing, or load-balancer boundary

application root span faults immediately
    -> validation, auth, configuration, or code error

one downstream span dominates
    -> dependency or connection acquisition

repeated downstream spans
    -> retry amplification

trace ends without child completion
    -> timeout, process crash, cancellation, or missing telemetry

large unexplained gap
    -> queueing, lock, GC, event-loop delay, or uninstrumented work
```

### Span search and CloudWatch transaction data

When spans are ingested into CloudWatch transaction search, span data can be queried and analyzed with log-oriented features. Use this to correlate trace attributes, errors, and top contributors.

### Sampling limitation

A sampled tracing system may miss rare failures. Temporarily increase error or latency sampling through a controlled policy if the telemetry pipeline and cost envelope can handle it.

---

## 7. CloudWatch investigations

CloudWatch investigations can analyze:

- metrics
- logs
- deployment events
- AWS Health events
- CloudTrail changes
- X-Ray traces
- Logs Insights queries

Use it to generate observations, causal diagrams, and root-cause hypotheses.

### Safe operating rule

```text
AI suggestion -> supporting evidence -> falsifiable test -> mitigation
```

Do not execute a suggested remediation merely because the explanation is plausible.

Validate:

- timeline ordering
- resource identity
- Region and account
- cohort correlation
- whether the suggested change is reversible

Investigation reports can help capture the incident evidence, but human incident command remains accountable.

---

## 8. CloudWatch Synthetics

Synthetic canaries provide an independent user-path view.

Inspect failed-run artifacts:

- step results
- screenshots
- console and canary logs
- HAR file
- response headers and body
- trace data when active tracing is enabled
- DNS, TLS, and timing breakdown

Use canaries from multiple locations or paths to distinguish:

- global versus regional failure
- authentication versus anonymous flow
- page shell versus critical transaction
- IPv4 and IPv6 where supported by the test design

A canary that checks only `/health` may miss the business outage.

---

## 9. CloudTrail change history

Use CloudTrail Event history, organization trails, or centrally stored CloudTrail logs to identify API changes near the incident.

Search for changes to:

- Route 53 records and health checks
- WAF web ACLs and rules
- load balancers, listeners, and target groups
- security groups, NACLs, and routes
- EKS cluster and add-ons
- IAM roles and policies
- Secrets Manager and KMS policies
- RDS, DynamoDB, ElastiCache, or queue configuration
- Auto Scaling Groups and launch templates

Capture:

- principal and assumed role
- source IP and user agent
- request parameters
- affected resource
- event time
- error code

CloudTrail records control-plane API activity. It does not replace application logs or network-flow evidence.

### CloudTrail Lake current-status caution

CloudTrail Lake is no longer open to new customers as of May 31, 2026. Existing customers can continue using it, but new designs should follow AWS's current CloudWatch-oriented migration guidance and durable CloudTrail-to-S3 or supported analytics architecture.

Do not recommend CloudTrail Lake as a universally available new deployment.

---

## 10. AWS Config timeline

AWS Config can show resource configuration history and relationships for supported resources.

Use it to answer:

- What was the security-group rule before and after the incident?
- Did a route-table association change?
- Was encryption, public access, or retention modified?
- Did a resource become noncompliant at the same time?

Config timing and coverage depend on recorder setup and supported resource types. Verify the actual API event with CloudTrail when attribution matters.

---

## 11. AWS Health

Check account-specific AWS Health events for:

- service degradation
- scheduled maintenance
- resource-specific impairment
- networking or capacity events
- upcoming required action

Use EventBridge integration to surface relevant events into incident tooling.

The public service-status page may not show an account-specific event. Conversely, an AWS Health event may be correlated but not causal for the affected application path.

---

## 12. Load-balancer, CloudFront, and WAF logs

### ALB access logs

Inspect:

- load-balancer status
- target status
- request-processing, target-processing, and response-processing time
- target IP and port
- TLS protocol and cipher
- request path and user agent
- trace/request identifiers

A `-1` timing field can signal that a stage did not complete; interpret according to the load-balancer logging format.

### CloudFront logs

Compare:

- edge result type
- detailed result type
- cache status
- origin status and latency
- edge location
- viewer TLS behavior

### WAF logs

Find:

- terminating rule
- action
- labels
- matched field
- rate-based rule behavior
- country or source cohort

A dashboard showing 403 count does not explain which rule blocked valid requests.

---

## 13. Network evidence

### VPC Flow Logs

Use for observed accept/reject decisions and flow dimensions.

Questions:

- Did traffic reach the expected ENI?
- Was it accepted?
- Is return traffic present?
- Did source or destination change?
- Is one AZ or subnet different?

Flow Logs do not contain application payload and do not prove the process responded correctly.

### Reachability Analyzer

Use for configuration-path analysis between supported resources. It can identify blockers in:

- routes
- security groups
- NACLs
- load-balancer path

It models configuration and is not a live packet probe.

### Network Access Analyzer

Use to identify network paths that match unwanted-access findings across the configured scope. It is more suited to exposure analysis and validation than one-request runtime tracing.

### Traffic Mirroring or packet capture

Use only when necessary and authorized. Capture at the narrowest scope, protect sensitive payloads, and avoid adding significant incident load.

### Route 53 Resolver query logs

Use for private DNS queries and response codes. Remember resolver caching means not every client lookup generates a new upstream log event.

---

## 14. EKS evidence

### Control-plane logs

Enable and inspect relevant EKS logs:

- API server
- audit
- authenticator
- controller manager
- scheduler

Questions:

- Did an admission webhook time out?
- Were requests throttled or denied?
- Did a controller fail to reconcile?
- Was a resource mutated unexpectedly?
- Did scheduler behavior change?

### Kubernetes events

```bash
kubectl get events -A --sort-by=.lastTimestamp
```

Events are useful but ephemeral and rate-limited. Export important events centrally.

### Previous container logs

```bash
kubectl logs -n <namespace> <pod> -c <container> --previous
```

Preserve them before another restart overwrites the previous instance evidence.

### Node evidence

Use node logs, EKS log collector, and node monitoring signals when the hypothesis points to kubelet, runtime, CNI, disk, memory, or kernel behavior.

---

## 15. Database and queue tools

### Aurora/RDS

Use current database performance tooling to inspect:

- wait events
- top SQL
- locks
- load
- connections
- failover and maintenance events

### DynamoDB

Inspect:

- throttling
- successful request latency
- consumed capacity
- partition behavior
- retry count

### ElastiCache

Inspect:

- command latency
- evictions
- CPU
- connections
- hit ratio
- failovers

### SQS

Inspect:

- age of oldest message
- visible and in-flight messages
- delayed messages
- DLQ growth
- consumer throughput

The alarmed frontend error may originate from a backed-up or poisoned asynchronous dependency.

---

## 16. Runtime and profiling evidence

If metrics, logs, and traces identify the service but not the local cause, inspect:

- thread dumps
- heap and GC behavior
- CPU profiles
- lock contention
- event-loop delay
- file descriptors and sockets
- connection-pool waits
- kernel pressure and retransmits

Preserve evidence before restarting. A restart can be a valid mitigation but is often destructive to root-cause data.

---

## 17. Hypothesis-driven workflow

Use a small hypothesis table:

| Hypothesis | Evidence expected | Disproving evidence | Safe test |
|---|---|---|---|
| New WAF rule blocks users | WAF terminating rule rises at T1 | Requests reach app and return 5xx | Set rule to count for narrow scope |
| New version fails one route | Errors concentrated on digest | Old and new versions fail equally | Shift canary weight to zero |
| DB pool exhausted | Acquisition wait and active pool max | Pool has headroom, DB spans normal | Reduce concurrency or add safe pool capacity |
| One AZ impaired | Errors and latency by AZ | Same pods fail in every AZ | Drain small target cohort |

Change one variable at a time where incident urgency permits.

---

## 18. After the incident

Add the diagnostic signal that was missing:

- structured field or correlation ID
- route-level histogram
- deployment annotation
- trace attribute
- WAF or load-balancer logging
- Resolver query logging
- Config recorder coverage
- cohort-aware SLI
- synthetic business transaction
- runbook query

Do not solve every observability gap by adding a dashboard. Sometimes the correct artifact is a saved query, trace filter, profile, or automated evidence-collection runbook.

---

## Adversarial follow-ups

### “Why not just add more dashboards?”

Dashboards are for recurring questions and known signals. Root-cause investigation often requires high-cardinality raw evidence and ad hoc comparison. I add dashboards only for signals that deserve continuous operational attention.

### “Would you trust CloudWatch investigations?”

I use it to accelerate correlation and generate hypotheses. I verify timelines and supporting telemetry before remediation because plausible AI output is not authoritative evidence.

### “What does CloudTrail tell you that logs do not?”

CloudTrail attributes AWS API changes to a principal, time, request, and resource. Application logs explain runtime behavior. Both are required to connect a control-plane change to a user symptom.

### “Reachability Analyzer says reachable, but requests fail.”

It proves the modeled configuration permits the path. The application can still reject, time out, resolve the wrong name, use a different source, or fail at TLS or dependencies.

### “Can you use CloudTrail Lake?”

Existing customers can continue, but as of May 31, 2026 it is closed to new customers. I would not design a new incident platform that assumes new enrollment.

---

## Weak answers to avoid

- “Use CloudWatch Logs and X-Ray.”
- trusting a dashboard without checking the alarm definition
- searching logs without a precise time window or cohort
- treating AI-generated hypotheses as proof
- using CloudTrail as if it contains application transactions
- assuming Config has every resource and immediate history
- recommending CloudTrail Lake to new customers after service availability changed
- packet capturing before simpler evidence sources
- restarting before preserving previous logs or runtime evidence
- adding unlimited high-cardinality metrics as the solution

---

## Closing statement

> When dashboards stop at the symptom, I move down the observability pyramid: aggregate metric to contributor, trace, log event, change record, configuration path, and runtime evidence. I maintain one timeline, test falsifiable hypotheses, and turn the missing evidence into a durable operational capability.