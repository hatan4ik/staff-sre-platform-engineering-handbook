# Overload Control and Graceful Degradation

## Purpose

Reliability under overload is not achieved by autoscaling alone. A system must preserve critical user journeys, reject excess work intentionally, prevent retry amplification, and recover without synchronized backlog replay.

## Staff/Principal answer

> I define overload as demand or work amplification exceeding the sustainable capacity of at least one constrained resource. I identify the limiting resource, protect critical traffic with admission control and priority, bound concurrency and queues, enforce deadlines and retry budgets, shed optional work, and degrade features in a predesigned order. Autoscaling is a supporting control loop, not the first or only defense, because capacity arrives late and downstream systems may not scale with the caller. I validate recovery using user-journey SLIs, queue age, saturation, retry amplification, and time-to-drain, then turn the incident into tested overload contracts and game days.

## Overload anatomy

```text
traffic increase or dependency slowdown
        -> concurrency rises
        -> queues grow
        -> latency exceeds deadlines
        -> clients retry
        -> more work arrives
        -> timeouts and resource exhaustion
        -> cascading failure
```

The initial trigger can be legitimate traffic, a hot key, a slow dependency, cache miss amplification, expensive requests, a bad release, a queue replay, or a regional failover.

## Core invariants

1. Critical traffic receives capacity before optional traffic.
2. Every request has a deadline and cancellation propagates downstream.
3. Concurrency and queues are bounded.
4. Retries are budgeted, jittered, and limited to safe/idempotent operations.
5. Load shedding happens before global resource exhaustion.
6. Degradation is explicit, observable, reversible, and tested.
7. Recovery prevents synchronized replay and thundering herds.

## Diagnose the constrained resource

Use RED for request paths and USE for resources.

- **Rate:** demand, admitted rate, rejected rate, retries, queue ingress.
- **Errors:** timeouts, 429/503, cancellations, dependency failures.
- **Duration:** service time versus queue time, p50/p95/p99.
- **Utilization:** CPU, memory, connections, worker slots, I/O, partitions.
- **Saturation:** queue depth and age, run queue, thread-pool wait, pool exhaustion.

Separate offered load from admitted load and completed useful work. High request rate may be mostly retries or duplicate work.

## Controls by layer

### Edge and gateway

- rate limits by tenant, token, endpoint, geography, or device class;
- request size and complexity limits;
- priority classes;
- concurrency limits;
- early rejection with `429` or `503` plus safe retry guidance;
- circuit breaking for unhealthy origins.

### Service

- bounded worker pools and semaphore limits;
- adaptive concurrency based on observed latency;
- deadlines and cancellation propagation;
- bulkheads between critical and optional operations;
- request coalescing and single-flight for duplicate work;
- precomputed or cached fallback responses.

### Dependency

- connection-pool bounds;
- per-dependency retry budget;
- circuit breakers based on meaningful failure signals;
- cache protection and stale-while-revalidate;
- hot-key isolation;
- partition-aware throttling.

### Queue and stream

- monitor oldest-message age, not depth alone;
- cap consumer concurrency against downstream capacity;
- prioritize critical topics or queues;
- pause replay when recovery traffic threatens live traffic;
- use dead-letter and quarantine paths for poison messages;
- drain gradually after recovery.

## Retry budgets

Retries are additional traffic. Define a bounded retry ratio:

```text
retry budget = allowed retry attempts / original attempts
```

A practical policy may permit a small percentage of retries only while the downstream success rate and latency remain within a safe envelope. The exact threshold must be load-tested.

Retry only when:

- the operation is idempotent or protected by an idempotency key;
- the failure is transient;
- enough deadline remains;
- the retry budget is available;
- backoff includes jitter;
- another layer is not already retrying.

## Graceful-degradation ladder

Define the ladder before an incident. Example:

1. disable background analytics and noncritical enrichment;
2. serve cached or slightly stale data;
3. reduce response detail or expensive personalization;
4. defer asynchronous work;
5. restrict high-cost endpoints or tenants;
6. preserve authentication, safety, purchase, command, or playback-critical paths;
7. reject excess critical traffic explicitly rather than hanging indefinitely.

Each step needs an owner, trigger, expected capacity gain, user impact, rollback condition, and verification query.

## Autoscaling limits

Autoscaling can fail when:

- metrics arrive after queues and latency have already exploded;
- pod startup or node provisioning is slow;
- requests are wrong, causing scheduling or packing errors;
- the dependency is the bottleneck;
- scaling increases connection or partition pressure;
- failover doubles load into a region without spare headroom;
- scale-down removes capacity during backlog drain.

Use autoscaling with admission control, headroom, warm capacity, disruption budgets, and dependency-aware limits.

## Incident sequence

1. State user impact and establish incident command.
2. Stop risky releases and large replays.
3. Identify the constrained resource and amplification loops.
4. Protect critical traffic with priority and admission control.
5. Disable optional work using the degradation ladder.
6. Reduce retries and concurrency before adding more demand.
7. Add capacity where it addresses the actual bottleneck.
8. Validate recovery through external SLIs and backlog age.
9. Drain gradually and remove temporary controls one at a time.

## SLOs and alerts

Track:

- admitted-success rate for critical journeys;
- shed/rejected rate by reason and cohort;
- queue age and time-to-drain;
- retry amplification ratio;
- deadline expiration and cancellation rate;
- dependency saturation;
- percentage of traffic operating in degraded mode;
- regional headroom and failover capacity.

Alert on multi-window burn, not raw CPU alone.

## Game-day scenarios

- 3x demand spike;
- dependency latency doubles;
- cache hit rate collapses;
- one partition becomes hot;
- regional failover with backlog replay;
- retry policy accidentally enabled at three layers;
- node provisioning delayed;
- optional feature consumes shared connection pools.

Success requires critical journeys to remain within their objectives, shedding to occur at the intended layer, and recovery to complete without a second incident.

## Adversarial follow-ups

**Why not just return errors immediately?**  
Because indiscriminate rejection may discard critical traffic while optional work consumes capacity. Prioritized admission and a tested degradation order preserve more business value.

**Why not scale everything?**  
Scaling the caller can increase pressure on a fixed database, partition, vendor API, or network path. Capacity must be added at the constrained resource and coordinated across dependencies.

**Is a circuit breaker always good?**  
No. Poor thresholds can create oscillation or block recovery probes. Breakers require bounded half-open testing, observability, and ownership.

## Weak answers to avoid

- “Enable HPA.”
- “Increase all timeouts.”
- “Retry three times everywhere.”
- “Queue everything indefinitely.”
- “Fail over the entire region immediately.”
- “Turn off random features during the incident.”
