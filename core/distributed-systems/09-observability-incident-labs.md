# Chapter 9 — Distributed Observability and Production Incident Labs

Distributed systems fail across boundaries: process, host, zone, region, queue, shard, dependency, and ownership domain. No single metric, log line, or trace proves what happened.

The Staff-level observability goal is not to collect everything. It is to build enough evidence to answer:

1. What user-visible invariant failed?
2. Where did work stop making progress?
3. Which failure domain is affected?
4. What feedback loop is amplifying the incident?
5. Which mitigation reduces risk without destroying evidence or durability?

---

## 9.1 Observability Versus Monitoring

Monitoring answers known questions:

- Is error rate above threshold?
- Is CPU saturated?
- Is replication lag high?

Observability supports investigation of unknown failure modes by exposing system state through:

- metrics
- logs
- traces
- profiles
- events
- topology and ownership metadata

A mature system needs both.

### Staff-level rule

Telemetry must represent the distributed protocol, not only individual processes.

That means recording:

- logical request ID
- physical attempt number
- ownership epoch
- shard or partition
- message ID and offset
- source and destination region
- entity version
- retry reason
- deadline remaining
- reconciliation state

---

## 9.2 Start with the Business Signal

Infrastructure can look healthy while business processing is broken.

Examples:

- enqueue succeeds but orders never complete
- database is healthy but cache serves stale authorization
- consumers process messages but duplicate payments occur
- replicas are available but acknowledged writes are lost during failover

Business signals include:

- checkout completion rate
- payment capture uniqueness
- order terminal-state age
- inventory reservation conflicts
- oldest unprocessed critical event
- successful leader ownership transitions

### Investigation order

```text
business impact
  -> request or workflow path
  -> distributed protocol state
  -> resource saturation
  -> underlying infrastructure
```

Starting with CPU before confirming user impact often wastes time.

---

## 9.3 The Four Golden Signals

The classic four signals remain useful:

- latency
- traffic
- errors
- saturation

Distributed systems require additional dimensions.

### Latency

Measure:

- end-to-end latency
- per-hop latency
- queue delay
- processing time
- replication delay
- reconciliation age

### Traffic

Measure:

- logical requests
- physical attempts
- messages
- bytes
- shard fan-out
- tenant share

### Errors

Separate:

- application rejection
- timeout
- transport failure
- dependency error
- stale-version rejection
- duplicate suppression
- consistency violation

### Saturation

Measure:

- concurrency
- queue depth
- connection-pool wait
- disk queue
- compaction debt
- broker partition load
- repair backlog

---

## 9.4 Logical Requests Versus Physical Attempts

Retries, hedges, fan-out, and replay create amplification.

One user request may produce:

- multiple RPC attempts
- several shard reads
- duplicate broker deliveries
- cache refresh calls

Track both:

```text
logical_requests_total
physical_attempts_total
```

Amplification ratio:

```text
physical attempts / logical requests
```

A rising ratio is an early signal of retry storms, fan-out growth, or duplicate processing.

---

## 9.5 Correlation, Causation, and Identity

Useful identifiers include:

- request ID
- trace ID
- workflow ID
- message ID
- causation ID
- entity ID
- idempotency key
- shard ID
- ownership epoch

### Correlation ID

Groups activity belonging to one business workflow.

### Causation ID

Identifies the exact event or command that produced another event.

### Idempotency key

Identifies one logical side effect across retries.

These identifiers should survive asynchronous boundaries and retries.

---

## 9.6 Distributed Tracing

A trace shows causally related operations across services.

Useful span attributes:

- service and operation
- region and zone
- peer endpoint
- retry attempt
- timeout and deadline
- message topic and partition
- shard ID
- cache hit or miss
- database role
- consistency mode

### Sampling challenge

Rare failures may disappear under low-rate head sampling.

Strategies:

- tail-based sampling
- always sample errors
- always sample high latency
- sample specific tenants or workflows during incident
- retain exemplars linking metrics to traces

### Trace limitation

A trace may show that a call returned success. It does not prove a replicated write is durable or that an asynchronous consumer later completed.

Trace business state transitions separately.

---

## 9.7 Logging

Logs should record decisions and state transitions, not repeat every metric.

High-value log events:

- ownership acquired or rejected
- idempotency duplicate detected
- message moved to DLQ
- retry suppressed by budget
- circuit breaker opened
- shard movement phase changed
- reconciliation repaired drift
- failover promoted replica at log position X

### Structured fields

Prefer structured fields over embedded prose:

```json
{
  "event": "stale_owner_rejected",
  "shard_id": "42",
  "request_epoch": 91,
  "current_epoch": 92,
  "request_id": "..."
}
```

### Log cardinality

High-cardinality fields belong in logs or traces, while metrics usually aggregate them carefully.

Do not place unrestricted user IDs or request IDs into metric labels.

---

## 9.8 Metrics and Cardinality

Metrics are powerful for trends and alerts but can become expensive with high-cardinality dimensions.

### Good bounded labels

- service
- region
- zone
- operation
- status class
- shard group
- retry reason

### Dangerous unbounded labels

- request ID
- email
- raw URL
- user ID
- message payload

### Heavy-hitter telemetry

For hot keys or tenants, use:

- top-K sketches
- sampled logs
- exemplars
- dedicated analytics pipeline

This preserves visibility without exploding metric cardinality.

---

## 9.9 SLOs for Distributed Workflows

A service-level indicator should represent the user outcome.

Examples:

- percentage of checkout requests completed within 2 seconds
- percentage of accepted orders reaching terminal state within 5 minutes
- percentage of acknowledged writes surviving one-zone failover
- percentage of authorization revocations effective within 30 seconds

### Queue-based workflow SLO

Enqueue latency is insufficient.

Measure:

- end-to-end completion
- oldest-message age
- terminal success rate
- expiry rate

### Correctness SLI

Some invariants are better expressed as counts:

- duplicate captures
- negative inventory violations
- stale-owner writes accepted
- inconsistent ledger balances

A single correctness violation may be more severe than thousands of latency misses.

---

## 9.10 Error Budgets

An error budget converts an SLO into permitted unreliability.

Distributed systems may need separate budgets for:

- availability
- latency
- freshness
- durability
- correctness

Do not combine a duplicate-payment incident with ordinary 500 errors as though they have equal severity.

### Burn-rate alerts

Use multiple windows:

- fast burn for acute incident
- slow burn for gradual degradation

This reduces noisy alerts while catching serious budget consumption.

---

## 9.11 Freshness Observability

Eventual consistency requires freshness metrics.

Possible signals:

- source version minus replica version
- source timestamp minus materialized-view timestamp
- invalidation publication-to-application delay
- oldest unapplied event
- read served from version older than client's minimum

### User-visible freshness

System replication lag is not always the same as user-visible staleness.

A router may keep a session on a fresh replica even while another replica lags.

Measure the guarantee the client actually observes.

---

## 9.12 Replication Observability

For each shard or replica, expose:

- leader identity
- term or epoch
- applied log position
- commit position
- replication lag
- last successful heartbeat
- snapshot or repair progress
- under-replicated status

### Dangerous aggregate

Average replication lag can hide one critical shard far behind.

Use:

- maximum
- p99
- oldest lag age
- lag by business criticality

---

## 9.13 Consensus Observability

Useful signals:

- current leader
- term changes
- election duration
- quorum health
- proposal latency
- commit index
- applied index
- rejected stale terms
- membership changes

### Election storm

Frequent leader changes may indicate:

- network loss
- overloaded leader
- GC pauses
- disk latency
- timeout tuning problem

Alert on rate and impact, not only one election.

---

## 9.14 Messaging Observability

Measure:

- publish success and latency
- broker acknowledgement level
- partition skew
- consumer lag
- oldest-message age
- processing time
- retry attempts
- DLQ growth
- rebalance count
- offset commit failures

### Business queue state

Map technical lag to business states:

- orders awaiting capture
- invoices awaiting delivery
- workflows in compensation
- events missing sequence versions

---

## 9.15 Cache Observability

Measure:

- hit rate
- byte hit rate
- miss cost
- refresh latency
- stale-response rate
- invalidation lag
- eviction rate
- hot-key distribution
- origin fallback traffic

### Freshness proof

Where correctness matters, record source and cache version so stale responses can be detected rather than inferred.

---

## 9.16 Shard and Partition Observability

Per-shard metrics should include:

- QPS
- bytes
- CPU
- storage
- queue depth
- p99 latency
- compaction or repair debt
- owner and epoch
- replica locations

### Skew metrics

- max-to-median
- p99-to-median
- top tenant share
- top key share

Fleet averages are insufficient.

---

## 9.17 Topology-Aware Investigation

A dependency graph should connect:

- service
- region
- zone
- shard
- queue
- database
- external provider

During an incident, topology helps answer:

- Is impact limited to one zone?
- Do failing requests share one shard?
- Is one dependency endpoint responsible?
- Did a deployment cohort introduce the issue?

Static architecture diagrams become stale. Prefer topology derived from traffic and ownership metadata where possible.

---

## 9.18 Change Events

Correlate incidents with changes:

- deployment
- configuration update
- feature flag
- schema migration
- shard movement
- certificate rotation
- quota change
- dependency failover

Change markers should appear on dashboards and timelines.

A high percentage of incidents follow change, but not every correlation is causation. Verify through rollback or controlled comparison.

---

## 9.19 Incident Command Evidence Loop

A disciplined response loop:

1. State impact and invariant.
2. Form one hypothesis.
3. Identify evidence that would confirm or reject it.
4. Execute the lowest-risk query or mitigation.
5. Record result and next decision.

Avoid random command execution without a hypothesis.

### Example

Hypothesis:

> Retry amplification is saturating the database.

Evidence:

- physical attempts per logical request increased
- connection-pool wait rose
- database QPS exceeds user request rate

Mitigation:

- disable proxy retry
- reduce application concurrency

Proof:

- attempts ratio falls
- database queue drains
- completion rate recovers

---

## 9.20 Mitigation Principles

Prefer mitigations that:

- reduce load
- preserve durability
- limit blast radius
- are reversible
- do not destroy evidence

Examples:

- shed optional traffic
- pause rebalancing
- reduce retries
- isolate one tenant
- route around one zone

High-risk mitigations include:

- deleting queues
- forcing unsafe failover
- disabling consistency checks
- restarting every node
- truncating logs

---

## 9.21 Incident Lab 1 — Retry Storm

### Initial symptoms

- p99 latency increases
- timeout errors rise
- database CPU reaches 85%
- application CPU remains moderate

### Investigation

Check:

- logical requests versus physical attempts
- retries by application, SDK, and proxy
- connection-pool wait
- database queue depth
- remaining request deadline

### Expected diagnosis

Layered retries amplify a dependency slowdown.

### Mitigation

- disable one retry layer
- reduce concurrency
- shed optional traffic
- apply jittered retry budget

### Prevention

- single retry owner
- attempts-ratio alert
- dependency saturation dashboard

---

## 9.22 Incident Lab 2 — Split Brain

### Initial symptoms

- two regions report active leader
- conflicting writes exist
- clients observe different state

### Investigation

Check:

- term or epoch
- quorum membership
- lease assumptions
- fencing-token enforcement
- routing metadata

### Expected diagnosis

Old owner continued accepting writes because the resource did not enforce fencing.

### Mitigation

- stop stale owner
- preserve both histories
- reconcile according to business invariant
- increment ownership epoch

### Prevention

- quorum-backed ownership
- resource-side fencing
- failover drills

---

## 9.23 Incident Lab 3 — Acknowledged Write Lost

### Initial symptoms

A client received success before regional failover, but the write is absent after promotion.

### Investigation

Check:

- producer acknowledgement boundary
- synchronous versus asynchronous replicas
- promoted replica log position
- RPO promise

### Expected diagnosis

The API acknowledged local durability only, while users assumed regional durability.

### Mitigation

- reconcile from client or audit records
- communicate data-loss boundary

### Prevention

- explicit durability contract
- quorum acknowledgement for critical writes
- failover gate based on log position

---

## 9.24 Incident Lab 4 — Hot Shard

### Initial symptoms

- fleet CPU 40%
- one shard at 100%
- p99 latency high only for one tenant

### Investigation

Check:

- per-shard traffic
- top tenant and key share
- replica read distribution
- compaction debt

### Mitigation

- isolate tenant
- move replica
- rate-limit hot workload
- split key or shard

### Prevention

- skew alerts
- tenant-aware placement
- hot-key mitigation

---

## 9.25 Incident Lab 5 — Consumer Lag

### Initial symptoms

- broker healthy
- enqueue succeeds
- orders complete 40 minutes late

### Investigation

Check:

- oldest-message age
- arrival and processing rate
- downstream latency
- retry count
- poison messages
- partition skew

### Expected diagnosis

One partition is blocked by a poison message and retry loop.

### Mitigation

- park message according to invariant
- resume partition
- repair and replay later

### Prevention

- bounded retry
- DLQ ownership
- partition-level lag alert

---

## 9.26 Incident Lab 6 — Cache Staleness

### Initial symptoms

A revoked administrator still has access.

### Investigation

Check:

- authorization cache TTL
- invalidation event delivery
- policy version
- cache key

### Expected diagnosis

Invalidation consumer lag and no version check.

### Mitigation

- bypass cache for high-risk action
- increment auth version
- purge affected entries

### Prevention

- versioned authorization
- short TTL
- freshness SLI

---

## 9.27 Incident Lab 7 — Rebalancer Outage

### Initial symptoms

- latency rises after node addition
- disk queue depth high across source nodes
- replication lag increasing

### Investigation

Check:

- concurrent shard moves
- bandwidth throttle
- foreground versus background I/O
- retry amplification

### Expected diagnosis

Aggressive rebalancing saturates storage and causes a retry storm.

### Mitigation

- pause or throttle movement
- preserve current replicas
- reduce retry load

### Prevention

- adaptive movement budget
- canary move
- recovery SLO

---

## 9.28 Incident Lab 8 — DNS or Service Discovery Staleness

### Initial symptoms

A subset of clients continue calling removed instances.

### Investigation

Check:

- DNS TTL
- client resolver cache
- connection pooling
- endpoint health propagation

### Mitigation

- restore compatible endpoint temporarily
- drain connections
- force resolver refresh where safe

### Prevention

- graceful endpoint draining
- tested TTL behavior
- version-compatible rollout

---

## 9.29 Incident Lab 9 — Clock Skew

### Initial symptoms

- leases overlap
- events appear out of order
- tokens rejected intermittently

### Investigation

Check:

- NTP state
- monotonic versus wall-clock use
- lease duration and pause time
- timestamp-based conflict resolution

### Expected diagnosis

Wall clock was used as ownership authority or last-write winner.

### Prevention

- epochs and fencing
- monotonic elapsed-time measurement
- logical versions

---

## 9.30 Incident Lab 10 — Cross-Region Partial Failure

### Initial symptoms

- one region can reach database but not message broker
- another region has opposite reachability
- workflows remain half complete

### Investigation

Map dependency reachability by region.

Check:

- transaction boundaries
- outbox backlog
- idempotency state
- compensation workflows

### Mitigation

- stop unsafe new workflows
- preserve durable local state
- replay outbox after recovery
- reconcile ambiguous external effects

### Prevention

- partial-failure drills
- region-specific dependency maps
- explicit workflow state machine

---

## 9.31 Runbook Structure

A useful runbook includes:

- impact definition
- key dashboards
- common hypotheses
- safe queries
- reversible mitigations
- escalation ownership
- data-safety warnings
- recovery verification

Avoid runbooks that say only “restart service.”

### Verification section

Every mitigation should define proof:

- error rate below threshold
- backlog draining
- no new duplicate side effects
- replication healthy
- ownership unique

---

## 9.32 Post-Incident Review

A blameless review should identify:

- triggering event
- contributing conditions
- detection gap
- amplification mechanisms
- mitigation effectiveness
- recovery bottlenecks
- invariant impact

### Corrective action quality

Weak:

- be more careful
- watch dashboard

Strong:

- enforce ownership epoch at storage layer
- cap retry ratio at 10%
- add oldest-message-age SLO
- test cold-cache origin capacity quarterly

Actions should change the system, not only human memory.

---

## 9.33 Design Review Checklist

Before approving observability for a distributed system, ask:

- What user-visible invariant is measured?
- Can logical requests be separated from physical attempts?
- Are retries and hedges visible?
- Are shard, partition, region, and ownership epoch recorded?
- Is message age measured, not only count?
- Can source and replica versions be compared?
- Are leader changes and terms observable?
- Can operators identify stale-owner rejections?
- Are cache freshness and invalidation lag measurable?
- Are change events correlated with telemetry?
- Are high-cardinality fields handled safely?
- Can traces cross asynchronous boundaries?
- Are DLQ and reconciliation states visible?
- Does each mitigation have verification criteria?

---

## 9.34 Staff and Principal Interview Drills

### Question 1

A service's CPU and error rate are normal, but customers report delayed orders. What do you inspect?

Expected direction:

- end-to-end workflow SLI
- queue age
- consumer lag
- terminal-state age
- downstream dependency

### Question 2

How do you detect a retry storm?

Expected direction:

- logical versus physical attempts
- retry reasons and layers
- dependency QPS versus user QPS
- connection-pool wait

### Question 3

Why is average replication lag dangerous?

Expected direction:

- one critical shard may be far behind
- use maximum, p99, oldest age, business weighting

### Question 4

How do you trace asynchronous workflows?

Expected direction:

- correlation and causation IDs
- message identity
- workflow state
- long-lived traces or linked spans

### Question 5

What telemetry proves fencing works?

Expected direction:

- ownership epochs
- stale-owner rejection count
- one active owner
- resource-side enforcement

### Question 6

How should a postmortem action differ from “operator error”?

Expected direction:

- system guardrail
- validation
- safer automation
- reduced blast radius

---

## 9.35 Hands-On Labs

### Lab 1 — Amplification Dashboard

Instrument logical request IDs and physical attempts across retries and fan-out.

Build an amplification-ratio alert.

### Lab 2 — Freshness SLI

Expose source version and served version. Measure the percentage of reads within the freshness objective.

### Lab 3 — Queue Completion SLO

Track enqueue-to-terminal-state latency and oldest-message age.

### Lab 4 — Shard Heat Map

Generate skew and build a shard-by-time heat map for QPS, p99, and queue depth.

### Lab 5 — Failure Injection Trace

Inject latency into one zone and verify traces identify region, retry attempt, and remaining deadline.

### Lab 6 — Incident Timeline

Combine deployments, configuration changes, breaker events, and SLO burn into one timeline.

### Lab 7 — Runbook Drill

Execute a simulated retry storm using only the runbook. Record missing evidence and unsafe steps.

---

## 9.36 Staff-Level Summary

Distributed observability must reveal protocol state and business progress.

A production-grade evidence model connects:

```text
business invariant
  -> logical workflow identity
  -> attempts, versions, offsets, and epochs
  -> topology and saturation
  -> mitigation and recovery proof
```

The strongest Staff-level operator does not merely find a red graph. They identify the failed invariant, the amplification loop, the affected failure domain, and the safest reversible action that restores progress.
