# Chapter 8 — Resilience Patterns, Overload Control, and Cascading-Failure Containment

Resilience is not the ability to avoid all failures. It is the ability to preserve critical business behavior, limit blast radius, and recover predictably when failures occur.

Distributed systems rarely fail as one isolated component. They fail through feedback loops:

```text
latency rises
  -> timeouts increase
  -> retries multiply load
  -> queues grow
  -> dependencies slow further
  -> more timeouts and retries
```

The Staff-level task is to design explicit limits so local degradation does not become systemic collapse.

---

## 8.1 Resilience Starts with Failure Policy

For each dependency and operation, define:

- what failure is expected
- how long the caller waits
- whether retry is allowed
- whether stale or partial data is acceptable
- which traffic is shed first
- which state must be preserved
- how operators detect and recover

A vague requirement such as “the service should be highly available” is insufficient.

A useful resilience requirement is specific:

> During loss of the recommendation service, checkout remains available, recommendations are omitted, and the dependency receives no more than 5% probe traffic until recovery.

---

## 8.2 Safety, Liveness, and Degradation

A resilient system separates:

### Safety

What must never happen.

Examples:

- duplicate payment capture
- two active shard owners
- unauthorized access
- acknowledged ledger entry silently lost

### Liveness

What must eventually happen.

Examples:

- queued order eventually reaches a terminal state
- failed leader is replaced
- replicas eventually repair

### Degradation policy

What functionality may be reduced temporarily.

Examples:

- omit recommendations
- serve stale catalog data
- pause exports
- reject new batch jobs
- disable expensive search filters

Graceful degradation preserves the core invariant while reducing noncritical work.

---

## 8.3 Failure Domains and Blast Radius

Resilience depends on isolation.

Failure domains include:

- process
- pod
- node
- rack
- availability zone
- region
- tenant
- shard
- deployment cohort
- dependency endpoint
- control plane

### Blast-radius questions

- Can one tenant exhaust all workers?
- Can one bad deployment affect every region simultaneously?
- Can one hot shard consume the database fleet?
- Can one dependency timeout consume every application thread?
- Can one configuration error disable all cells?

Isolation is a capacity and architecture property, not only an organizational intention.

---

## 8.4 Timeout Design

A timeout is a resource-allocation decision.

Without a timeout, a request may hold:

- thread or task slot
- memory
- socket
- connection-pool entry
- lock
- queue position

### End-to-end deadline

A request should carry a deadline through the call chain.

```text
client budget: 1000 ms
edge: 100 ms
service A: 150 ms
service B: 250 ms
retry reserve: 150 ms
response margin: 350 ms
```

Child calls must not outlive the parent request.

### Timeout anti-pattern

Every service uses a 30-second default.

A five-hop chain can retain work long after the client has left, creating hidden load.

### Adaptive concern

Increasing timeouts during overload may reduce false failures but also increase in-flight concurrency and worsen saturation.

Timeout changes must be capacity-aware.

---

## 8.5 Retry Discipline

Retries are controlled load multiplication.

A retry is appropriate only when:

- the failure is plausibly transient
- the operation is idempotent or deduplicated
- enough deadline remains
- the dependency has recovery capacity
- attempts are bounded

### Retry multiplication

If application, SDK, proxy, and service mesh each retry twice, one logical request can create many physical attempts.

### Single retry owner

Choose the layer with the best knowledge of:

- operation semantics
- deadline
- idempotency
- dependency health

Other layers should normally disable retries or coordinate through a shared budget.

---

## 8.6 Retry Budgets

A retry budget caps retries as a fraction of normal requests.

Example:

```text
retry attempts <= 10% of successful original traffic
```

When failures rise, the system stops retrying before retries dominate load.

### Benefits

- protects dependency capacity
- bounds amplification
- makes retry cost observable

### Metrics

- logical requests
- physical attempts
- retries by reason
- retries by layer
- retry success rate
- budget exhaustion

A retry that rarely succeeds but consumes significant capacity should be removed.

---

## 8.7 Backoff and Jitter

Exponential backoff spaces attempts:

```text
100 ms
200 ms
400 ms
800 ms
```

Without jitter, clients synchronize and produce retry waves.

Full jitter example:

```text
sleep = random(0, min(cap, base * 2^attempt))
```

Backoff should also respect the request deadline.

Retrying after the user-visible deadline wastes capacity unless the work remains valuable asynchronously.

---

## 8.8 Circuit Breakers

A circuit breaker stops repeated calls to an unhealthy dependency.

States:

- closed: calls flow
- open: calls fail fast or use fallback
- half-open: limited probes test recovery

### Benefits

- reduces wasted work
- accelerates caller failure
- protects dependency recovery

### Risks

- synchronized half-open probes
- stale fallback data
- one global breaker masking healthy partitions
- oscillation from poor thresholds

### Scope

Breakers should match the failure domain:

- endpoint
- zone
- region
- tenant
- operation type

A global breaker for one unhealthy zone can unnecessarily disable healthy zones.

---

## 8.9 Bulkheads

Bulkheads divide resources so one workload cannot consume everything.

Examples:

- separate thread pools
- separate queues
- separate connection pools
- per-tenant concurrency
- dedicated worker groups
- isolated cells

### Scenario

A reporting endpoint performs slow database scans.

Without a bulkhead, it consumes every database connection and blocks checkout.

With separate pools, reporting degrades while checkout remains healthy.

### Staff-level rule

Critical and noncritical traffic should not share unbounded resource pools.

---

## 8.10 Concurrency Limits

Rate limits control requests over time.

Concurrency limits control simultaneous in-flight work.

Concurrency is often the direct protection for:

- database connections
- CPU-heavy handlers
- model inference
- downstream RPCs
- memory-heavy jobs

### Little's Law

```text
concurrency = throughput * latency
```

If latency rises while throughput remains constant, required concurrency rises.

At a fixed pool size, queueing begins.

At an unbounded pool size, memory and dependency load grow.

### Adaptive concurrency

An adaptive limiter observes latency or queue delay and changes the in-flight limit.

It should react gradually and include hysteresis to avoid oscillation.

---

## 8.11 Queue Bounds

An unbounded queue converts overload into latency and memory growth.

A bounded queue makes capacity limits explicit.

When full, the system must:

- reject
- shed
- redirect
- degrade
- persist to a durable overflow path

### Queue-size policy

Queue capacity should follow:

- acceptable waiting time
- service rate
- memory per item
- recovery target

A queue that can hold six hours of traffic may already violate a 30-second business deadline.

---

## 8.12 Load Shedding

Load shedding rejects work before it consumes scarce resources.

Possible priority order:

1. preserve health checks and control plane
2. preserve authenticated critical transactions
3. preserve existing sessions
4. reject expensive optional reads
5. reject batch and background work

### Early rejection

Failing fast at the edge is cheaper than accepting work that times out after consuming five dependencies.

### Response semantics

Use explicit errors and retry guidance where appropriate:

- `429 Too Many Requests`
- `503 Service Unavailable`
- retry-after information

Clients must still use jitter and bounded retry.

---

## 8.13 Admission Control

Admission control decides whether new work enters the system.

Signals may include:

- current concurrency
- queue depth
- CPU
- memory pressure
- dependency saturation
- tenant quota
- estimated work cost

### Cost-aware admission

Not all requests cost the same.

A full-text export may be 1,000 times more expensive than a cached lookup.

Admission decisions should consider request class, not only request count.

---

## 8.14 Rate Limiting Algorithms

### Fixed window

Simple count per interval.

Risk: burst at window boundaries.

### Sliding window

More accurate rolling limit.

Higher state cost.

### Token bucket

Tokens accumulate at a rate up to a burst capacity.

Allows bounded bursts.

### Leaky bucket

Smooths output at a fixed rate.

Useful when downstream needs stable traffic.

### Distributed limiter concerns

- consistency of counters
- clock skew
- partition behavior
- local versus global limits
- failure fallback

A perfectly consistent global rate limiter may add latency and become a critical dependency.

Hierarchical local plus global quotas are often more resilient.

---

## 8.15 Per-Tenant Fairness

A single tenant should not consume all shared capacity.

Controls include:

- per-tenant rate limits
- per-tenant concurrency
- weighted fair queues
- reserved minimum capacity
- maximum burst
- cost-based quotas

### Fairness versus utilization

Strict reservation can waste idle capacity.

A better model may provide:

- guaranteed baseline
- shared burst pool
- hard maximum

This preserves fairness while allowing efficient use of spare resources.

---

## 8.16 Hedged Requests

A hedge sends a second request after a delay and uses the first successful response.

Useful for reducing tail latency when:

- operations are read-only or idempotent
- replicas have variable latency
- spare capacity exists

### Risks

- extra load
- duplicate side effects
- synchronized hedging
- worsening overload

### Safe policy

- hedge only a small percentile
- delay based on observed latency
- cancel losing attempt
- disable under saturation
- use separate retry budget

Hedging is not a general outage strategy.

---

## 8.17 Request Coalescing

When many callers request the same expensive value, one request performs the work and others share the result.

Useful for:

- cache refresh
- configuration fetch
- metadata lookup
- expensive read query

### Risks

- one slow request delays many waiters
- failure fans out to all waiters
- key cardinality may consume memory

Use waiter deadlines and bounded coalescing state.

---

## 8.18 Graceful Degradation

A service should identify optional features before an incident.

Examples:

- omit recommendations
- reduce image quality
- disable sorting options
- serve cached profile
- defer analytics emission
- return partial search results

### Degradation requirements

- explicit user experience
- observability
- bounded stale data
- feature dependency graph
- tested activation

A fallback that has never been load-tested may fail when needed most.

---

## 8.19 Partial Results

Scatter-gather systems may return partial results when some shards fail.

The response should indicate:

- completeness
- missing regions or shards
- data timestamp
- whether retry is safe

Silent partial results can violate user trust or business correctness.

For analytics, partial may be acceptable.

For compliance exports, partial may be unacceptable.

---

## 8.20 Fallbacks

Fallback types include:

- stale cache
- default value
- alternate provider
- reduced feature
- queued asynchronous completion

### Fallback risks

- stale or unsafe data
- fallback dependency overload
- hidden correctness change
- permanent operation in degraded mode

A fallback should have its own SLO, capacity model, and observability.

---

## 8.21 Fail Open Versus Fail Closed

### Fail open

Continue operation when a dependency is unavailable.

Examples:

- show page without recommendations
- accept telemetry locally

### Fail closed

Reject operation when safety cannot be proven.

Examples:

- deny access when authorization cannot be verified
- reject write when quorum is lost

The decision follows the invariant.

Security and money-sensitive operations often fail closed.

Availability-oriented optional features often fail open.

---

## 8.22 Dependency Criticality Classification

Classify dependencies:

### Tier 0 — safety critical

Failure requires rejecting the operation.

Examples:

- authorization
- payment ledger
- ownership coordinator

### Tier 1 — core availability

Failure prevents primary service function.

### Tier 2 — degradable

Failure reduces experience but core path remains.

### Tier 3 — asynchronous or optional

Failure can be deferred.

This classification drives timeout, retry, capacity, and fallback policy.

---

## 8.23 Cascading Failure Anatomy

A common cascade:

```text
database latency rises
  -> application threads block
  -> request queues grow
  -> client timeouts
  -> retries
  -> connection pools saturate
  -> unrelated endpoints fail
  -> health checks fail
  -> instances restart
  -> cold caches increase database load
```

The original database slowdown may be modest. The system's feedback loops create the outage.

### Containment points

- timeout
- concurrency limit
- queue bound
- retry budget
- circuit breaker
- bulkhead
- load shedding
- restart policy

Resilience comes from multiple independent brakes.

---

## 8.24 Health Checks and Restart Storms

Health checks should distinguish:

- process alive
- ready for traffic
- dependency degraded
- safe to restart

### Anti-pattern

A service marks itself unhealthy when a shared database is slow. The orchestrator restarts every instance.

Restarting:

- drops caches
- creates connection storms
- increases dependency load

### Better behavior

- readiness may reject new traffic
- liveness should remain healthy if restart will not help
- dependency health should be surfaced separately

A restart is a remediation action, not a universal response to slowness.

---

## 8.25 Autoscaling Failure Modes

Autoscaling can help CPU-bound workloads, but it may worsen dependency-bound incidents.

### Scenario

Database is saturated. Application latency rises. Autoscaler adds application instances.

New instances create more database connections and retries.

### Required checks

- what resource is saturated?
- can the dependency scale too?
- does scale-out increase downstream load?
- how fast does new capacity become useful?
- does cold start create extra work?

Autoscaling is a control loop and can create positive feedback if based on the wrong signal.

---

## 8.26 Control-Loop Stability

Systems contain many control loops:

- autoscaler
- retry logic
- circuit breaker
- load balancer
- rebalancer
- garbage collector
- queue consumer scaler

Each reacts with delay.

When loops operate on similar signals without coordination, they may oscillate.

### Stability mechanisms

- hysteresis
- cooldown
- rate-of-change limit
- minimum observation window
- bounded actuation
- one clear owner per control objective

Staff engineers evaluate interactions between loops, not only each loop independently.

---

## 8.27 Regional Failover

Failover is not only DNS change.

A regional failover requires:

- data readiness
- capacity in destination
- routing change
- dependency reachability
- secret and certificate availability
- idempotent replay
- stale-writer fencing

### Cold standby risk

A region that receives no traffic may have:

- cold caches
- expired credentials
- configuration drift
- insufficient quotas
- untested dependencies

### Active-active risk

- conflicting writes
- duplicated work
- split brain
- more complex reconciliation

The failover model must match the data consistency design.

---

## 8.28 Brownout Mode

A brownout intentionally disables optional work under stress.

Examples:

- skip recommendation calls
- reduce logging detail
- stop synchronous analytics
- disable expensive personalization

### Activation

- automatic based on saturation
- operator-controlled flag
- per-region or per-tenant

### Requirements

- tested regularly
- reversible
- visible in telemetry
- no hidden invariant violation

Brownout is planned degradation, not accidental feature failure.

---

## 8.29 Priority Queues

Critical and noncritical work can use separate priority queues.

### Risks

- starvation of low-priority work
- priority inversion
- unbounded high-priority classification

### Better policy

- reserved capacity for critical work
- minimum service for lower classes
- deadline and age awareness
- authenticated priority assignment

Clients should not be able to self-declare unlimited critical priority.

---

## 8.30 Cell-Based Isolation

Cells contain a subset of tenants or traffic with independent service and data capacity.

Benefits:

- bounded blast radius
- incremental deployment
- easier capacity planning
- isolated overload

Costs:

- duplicated infrastructure
- placement control plane
- cross-cell operations

A cell architecture is effective only if global dependencies do not reintroduce a global failure domain.

---

## 8.31 Static Stability

A statically stable system can continue serving critical traffic for some time without immediate control-plane actions.

Examples:

- enough spare capacity after one-zone loss
- cached configuration when control plane is down
- local routing table survives registry outage
- credentials remain valid during identity-provider interruption

Static stability reduces dependence on emergency automation during incidents.

---

## 8.32 Recovery Capacity

Recovery work consumes capacity:

- replica repair
- cache warming
- backlog drain
- shard movement
- replay
- reindexing

A system sized only for steady state may be unable to recover.

### Recovery SLO

Define:

- maximum backlog age
- target drain time
- replica rebuild time
- failback time

Reserve bandwidth and compute accordingly.

---

## 8.33 Overload Testing

Test beyond normal load.

Experiments should include:

- dependency latency injection
- dependency error injection
- sudden traffic spike
- cache loss
- one-zone loss
- message backlog
- slow downstream
- retry storm

Observe whether:

- queues remain bounded
- load shedding activates
- critical traffic survives
- recovery occurs without manual data repair

A load test that only measures maximum happy-path throughput does not validate resilience.

---

## 8.34 Chaos Engineering

Chaos engineering validates hypotheses about system behavior under controlled failure.

A good experiment defines:

- steady-state metric
- failure injected
- expected containment
- abort condition
- blast radius
- recovery proof

Examples:

- one dependency endpoint returns 500
- one zone loses network
- 10% of calls receive 2-second latency
- one consumer group stops

Chaos without hypotheses and safety controls is random disruption.

---

## 8.35 Resilience Telemetry

Measure:

### Demand

- logical requests
- physical attempts
- tenant share
- request cost class

### Saturation

- concurrency
- queue depth
- connection-pool wait
- CPU and memory pressure
- dependency limits

### Protection mechanisms

- retries
- breaker state
- shed count
- rate-limit count
- fallback usage
- brownout activation

### Recovery

- backlog age
- drain time
- replica rebuild progress
- error-budget recovery

### Business

- successful checkouts
- duplicate payments prevented
- orders delayed
- degraded responses

---

## 8.36 Incident: Retry Storm

### Scenario

A dependency slows from 50 ms to 600 ms. Caller timeout is 300 ms. The application retries twice and the proxy retries once.

### Failure chain

```text
slow dependency
  -> timeout
  -> layered retries
  -> request amplification
  -> dependency queue growth
  -> further slowdown
```

### Immediate response

- disable one retry layer
- reduce concurrency
- shed optional traffic
- open breaker selectively

### Prevention

- deadline propagation
- retry budget
- single retry owner
- jitter
- attempts-per-logical-request dashboard

---

## 8.37 Incident: Connection-Pool Exhaustion

### Scenario

One slow query class holds every database connection.

Unrelated fast endpoints wait for connections and fail.

### Correction

- separate pools
- query timeout
- concurrency cap
- workload-specific queue
- cancel abandoned queries

### Lesson

Shared pools create correlated failure.

---

## 8.38 Incident: Autoscaler Amplifies Database Outage

### Scenario

Application p95 rises because the database is saturated. Autoscaler doubles application instances.

Each instance opens 100 connections.

The database receives thousands of new connection attempts.

### Prevention

- dependency-aware scaling
- connection budget
- startup ramp
- concurrency limit
- database capacity signal

### Lesson

More callers do not create more downstream capacity.

---

## 8.39 Incident: Health Check Restart Loop

### Scenario

A shared dependency is slow. Every application instance fails liveness and restarts.

Cold caches and reconnect storms intensify the problem.

### Prevention

- dependency failure affects readiness, not liveness, when restart is useless
- startup jitter
- connection backoff
- cached configuration

---

## 8.40 Incident: Fallback Overload

### Scenario

Primary recommendation service fails. All traffic falls back to a smaller legacy service.

The fallback collapses.

### Prevention

- capacity-test fallback
- rate-limit fallback usage
- partial feature disablement
- stale cache
- brownout

### Lesson

A fallback is another production dependency and must be sized accordingly.

---

## 8.41 Incident: Queue Recovery Floods Downstream

### Scenario

Consumers are down for two hours. After recovery, autoscaling launches many workers that drain backlog at maximum rate.

The downstream payment service is overwhelmed.

### Prevention

- controlled drain rate
- downstream concurrency cap
- priority and expiry
- gradual consumer ramp

### Lesson

Recovery traffic can exceed normal traffic and requires explicit shaping.

---

## 8.42 Design Review Checklist

Before approving a resilient service design, ask:

- What are the safety invariants?
- Which features are degradable?
- What is the end-to-end deadline?
- Which layer owns retries?
- What is the retry budget?
- Are operations idempotent?
- Where are queues bounded?
- What happens when queues are full?
- What is the concurrency limit?
- Are critical workloads bulkheaded?
- Which traffic is shed first?
- Is the circuit breaker scoped correctly?
- Can the fallback handle full traffic?
- Does cache failure overload the origin?
- Can one tenant exhaust capacity?
- Are health checks restart-safe?
- Can autoscaling worsen dependency saturation?
- What control loops may interact?
- Is one-zone failure statically survivable?
- How much recovery headroom exists?
- What is the backlog drain policy?
- How is brownout activated and tested?
- What telemetry proves containment?

---

## 8.43 Staff and Principal Interview Drills

### Question 1

A dependency is slow, not failing. How can retries make the incident worse?

Expected direction:

- timeouts
- duplicate in-flight work
- queue growth
- layered retry amplification
- retry budget and concurrency control

### Question 2

What is the difference between rate limiting and concurrency limiting?

Expected direction:

- requests per interval versus simultaneous resource use
- dependency and latency sensitivity

### Question 3

When should a service fail open versus fail closed?

Expected direction:

- business invariant
- security and money safety
- optional versus authoritative dependency

### Question 4

Why can autoscaling be harmful?

Expected direction:

- wrong bottleneck
- downstream saturation
- connection storms
- cold starts
- feedback-loop instability

### Question 5

How do you design a queue backlog recovery plan?

Expected direction:

- arrival rate
- processing capacity
- drain time
- downstream limits
- expiry and priority
- gradual ramp

### Question 6

What should happen when a circuit breaker opens?

Expected direction:

- fail fast or safe fallback
- limited recovery probes
- scoped breaker
- telemetry

### Question 7

How do bulkheads reduce blast radius?

Expected direction:

- separate resource pools
- preserve critical traffic
- prevent slow workload from consuming everything

### Question 8

What is static stability?

Expected direction:

- continue critical service without immediate control-plane action
- spare capacity and cached state
- reduced emergency automation dependency

---

## 8.44 Hands-On Labs

### Lab 1 — Layered Retry Amplification

Create three services, each retrying twice.

Inject 500 ms dependency latency and measure physical attempts per logical request.

Disable retries at intermediate layers and add a retry budget.

### Lab 2 — Concurrency Collapse

Run a service with an unbounded worker pool against a slow dependency.

Compare with a bounded concurrency limiter and bounded queue.

### Lab 3 — Circuit Breaker

Implement closed, open, and half-open states.

Inject failure and validate limited recovery probes with jitter.

### Lab 4 — Bulkhead

Use separate pools for checkout and reporting.

Overload reporting and verify checkout remains healthy.

### Lab 5 — Brownout

Disable optional recommendation and analytics calls when p99 latency exceeds threshold.

Measure recovered capacity and user-visible behavior.

### Lab 6 — Backlog Drain

Create a two-hour synthetic backlog.

Drain with and without downstream rate limits. Demonstrate why maximum consumer scale can overload dependencies.

### Lab 7 — Health-Check Safety

Make a dependency slow. Compare liveness-triggered restart loops with readiness-only removal.

### Lab 8 — One-Zone Failure

Remove one zone under peak load. Validate spare capacity, routing, dependency reachability, and recovery telemetry.

---

## 8.45 Staff-Level Summary

Resilience is the design of negative feedback.

A production-grade system connects:

```text
failure policy
  -> deadlines and bounded retries
  -> concurrency and queue limits
  -> isolation and load shedding
  -> degradation and fallback
  -> controlled recovery
  -> observability
```

The strongest Staff-level answer explains how the system prevents a local slowdown from multiplying into a fleet-wide outage and how critical business invariants remain protected while optional functionality degrades.
