# Distributed Systems Foundations: Partial Failure, Time, Ordering, Retries, and Backpressure

A distributed system begins the moment one component depends on another component across a communication boundary. The second component may be healthy, slow, overloaded, partitioned, restarting, stale, or unreachable. The caller usually cannot distinguish those states immediately.

That uncertainty—not scale—is the central difficulty.

## 1. The fundamental problem: partial failure

In a single process, a function usually returns, throws, or the process crashes. Across a network, many ambiguous states exist:

```text
client sends request
      |
      +--> request never leaves client
      +--> request leaves but is dropped
      +--> server receives and rejects it
      +--> server executes but reply is lost
      +--> server executes partially and crashes
      +--> reply arrives after client timeout
      +--> duplicate retry executes again
```

A timeout means only that the caller stopped waiting. It does not prove that the operation failed.

This distinction drives idempotency, reconciliation, deduplication, fencing, and audit-log design.

### Staff-level rule

Never model a remote call as a normal function call. Model it as an uncertain protocol with explicit failure, retry, duplicate, and recovery behavior.

## 2. Safety and liveness

Distributed-system requirements should be separated into two categories.

### Safety

Something bad never happens.

Examples:

- A payment is not captured twice for one purchase.
- Two controllers do not both believe they own the same exclusive resource.
- An acknowledged write is not silently lost beyond the promised durability model.
- Inventory does not become negative when the business forbids overselling.

### Liveness

Something good eventually happens.

Examples:

- A submitted order eventually completes or reaches a terminal failure state.
- A failed leader is eventually replaced.
- Replicas eventually converge.
- A queued event is eventually processed or sent to a dead-letter workflow.

A design can preserve safety while losing liveness. For example, refusing all writes during uncertainty may prevent corruption but make the service unavailable.

A design can preserve liveness while violating safety. For example, allowing two isolated leaders to accept writes may keep both sides available but create conflicting ownership.

The correct trade-off comes from the business invariant, not from an abstract desire for maximum availability.

## 3. Failure domains

Architectures should name failure domains explicitly:

- process
- container
- virtual machine
- physical host
- rack
- availability zone
- region
- cloud control plane
- identity provider
- DNS system
- network path
- storage subsystem
- deployment pipeline
- operator action

Three replicas on one host are not three independent replicas. Three zones that share one regional control plane are not fully independent. Multi-region services that share one global identity or DNS dependency may still have a global single point of failure.

### Review question

For every redundant component, ask:

> Which failures are actually independent, and which supposedly separate replicas share a fate?

## 4. Time is not a trustworthy global authority

Physical clocks drift and are corrected. NTP can step or slew clocks. Virtual machines can pause. Network delays vary. A timestamp generated on one machine cannot, by itself, prove global causal ordering.

### Wall clock

Useful for:

- human-readable event times
- retention policies
- certificates
- coarse incident correlation

Dangerous for:

- exclusive ownership
- exact distributed ordering
- deduplication without another identifier
- deciding which concurrent write is universally “latest”

### Monotonic clock

Useful for measuring elapsed time within one running process:

- timeout deadlines
- latency measurement
- lease duration tracking inside a process

A monotonic clock does not move backward when wall time changes, but it is not normally comparable across machines.

### Logical ordering

When causal ordering matters, systems use mechanisms such as:

- sequence numbers
- versions
- epochs
- offsets
- Lamport clocks
- vector clocks
- consensus log indexes
- database commit positions

These encode ordering relationships without pretending that wall clocks are perfectly synchronized.

## 5. Happens-before and concurrency

Suppose operation A causes operation B. Then A happens before B.

If neither operation causally depends on the other, they may be concurrent even when their wall-clock timestamps differ slightly.

```text
client 1: write X=1 ------>
                         replica
client 2: write X=2 ------>
```

Without a shared ordering protocol, the system may not know which write should dominate. “Last write wins” is not neutral: it chooses a conflict-resolution policy, often based on uncertain clocks.

Staff engineers make conflict semantics explicit:

- reject concurrent updates
- merge them
- choose a deterministic winner
- preserve both versions
- serialize through a leader
- use application-level reconciliation

## 6. Timeouts are policy

A timeout should be based on an end-to-end latency budget, not copied from a framework default.

If a user-facing operation has a 1-second budget, a service cannot safely assign 1 second independently to each of five sequential dependencies.

```text
request budget: 1000 ms

edge and queueing          100 ms
service processing         150 ms
dependency A               200 ms
dependency B               250 ms
retry reserve              150 ms
response and safety margin 150 ms
```

The exact allocation varies, but the principle is universal: child deadlines must fit inside the parent deadline.

### Deadline propagation

Prefer an absolute or remaining deadline propagated through the call chain.

Without propagation:

```text
client times out at 1 s
service continues for 10 s
its dependency continues for 30 s
```

The result is wasted work, rising queues, and overload after the customer has already left.

### Timeout failure modes

Too short:

- false failures
- unnecessary retries
- duplicate work
- reduced success rate during harmless latency variation

Too long:

- resource retention
- larger queues
- slower failure detection
- thread, socket, and connection-pool exhaustion

## 7. Retries are controlled load multiplication

Retries can improve success during transient failures. They can also turn a small slowdown into a system-wide outage.

If five layers each retry three times, one original request can generate far more than three attempts. Layered retries multiply.

### Retry only when all are true

1. The failure is plausibly transient.
2. The operation is safe to repeat or protected by idempotency.
3. There is enough deadline remaining.
4. The retry load will not overwhelm the dependency.
5. The caller uses bounded attempts and backoff.

### Exponential backoff with jitter

A basic progression is:

```text
100 ms, 200 ms, 400 ms, 800 ms
```

Without jitter, thousands of clients retry in synchronized waves. Jitter spreads retries over time.

Conceptually:

```text
sleep = random(0, min(cap, base * 2^attempt))
```

Variants such as full jitter, equal jitter, and decorrelated jitter differ in behavior, but all aim to avoid coordinated retry storms.

### Retry ownership

Choose one layer to own retries whenever possible. The layer with the best knowledge of the operation, deadline, and idempotency semantics should control them.

Blind retries in SDKs, proxies, service meshes, application code, queues, and load balancers can otherwise stack invisibly.

## 8. Idempotency

An operation is idempotent when repeating the same logical request has the same intended effect as performing it once.

HTTP method labels alone do not guarantee application-level idempotency.

### Idempotency key pattern

A client sends a stable key for one logical operation:

```text
POST /payments
Idempotency-Key: order-8472-payment-v1
```

The service stores:

- key
- request fingerprint
- operation state
- final response or result reference
- expiration policy

On retry:

- same key and same request: return or continue the original result
- same key and different request: reject as misuse

### Race conditions

A naïve check-then-insert is unsafe:

```text
if key not found:
    perform side effect
    insert key
```

Two concurrent requests may both pass the check. Correct implementations need an atomic uniqueness boundary, transactional write, compare-and-set operation, or serialized owner.

### Idempotency is not exactly-once execution

The handler may execute more than once. The system aims for one externally visible logical effect.

This is why “exactly once” should always be unpacked into:

- exactly-once delivery?
- exactly-once handler execution?
- exactly-once state transition?
- exactly-once observable business effect?

Usually, only the last is the real requirement, and it is achieved through durable deduplication plus transactional state management.

## 9. At-most-once, at-least-once, and effectively-once

### At-most-once

The system does not retry after uncertainty. Duplicate execution is minimized, but work may be lost.

Useful when duplicate effects are worse than omission and the caller can reconcile later.

### At-least-once

The system retries until acknowledgment or a terminal policy. Work is less likely to be lost, but handlers must tolerate duplicates.

Common in queues and event systems.

### Effectively-once business processing

A practical design combines:

- at-least-once transport
- unique event or operation identifiers
- idempotent state transitions
- atomic persistence or an outbox/inbox pattern
- reconciliation

This is more honest and useful than claiming magical exactly-once behavior across arbitrary failure boundaries.

## 10. The transactional outbox

A classic dual-write bug occurs when a service must update its database and publish an event.

```text
1. commit order
2. publish OrderCreated
```

If the process crashes between steps, the database contains the order but no event exists.

Reversing the order creates the opposite problem: an event may be published for a transaction that later fails.

### Outbox pattern

Write both the business change and an outbox record in one local database transaction:

```text
BEGIN
  INSERT order ...
  INSERT outbox(event_id, type, payload, status) ...
COMMIT
```

A relay publishes outbox rows and marks progress. Publication can still be duplicated, so consumers remain idempotent.

The outbox converts an unsafe distributed dual write into:

- one atomic local transaction
- asynchronous at-least-once publication
- consumer-side deduplication

## 11. Backpressure

Backpressure tells producers to slow down when consumers cannot keep up.

Without backpressure, overload appears as growing queues, memory consumption, timeouts, retries, and eventually collapse.

### Possible mechanisms

- bounded queues
- admission control
- rate limits
- concurrency limits
- demand signaling
- credits or windows
- pull-based consumption
- load shedding
- HTTP 429 or 503 with retry guidance

### Bounded queues

An unbounded queue does not remove overload. It hides overload while increasing latency and memory use.

Little’s Law provides the relationship:

```text
concurrency = throughput * time-in-system
```

If arrival rate stays high while latency rises, concurrency and queue size rise too. This is why latency incidents often become resource-exhaustion incidents.

### Load shedding

When capacity is exhausted, rejecting low-priority work early is often safer than accepting everything and timing out everything.

Good shedding policy may prioritize:

- authenticated over anonymous traffic
- reads over expensive writes
- interactive over batch work
- control-plane over reporting traffic
- existing sessions over new sessions

The policy should reflect business value and recovery needs.

## 12. Concurrency limits

Static rate limits control requests per time interval. Concurrency limits control simultaneous in-flight work.

Concurrency is often the more direct protection when each request consumes a scarce resource such as:

- database connections
- CPU-intensive workers
- downstream RPC slots
- memory-heavy model execution

Adaptive concurrency controllers can reduce allowed in-flight work when latency rises, helping the service operate near capacity without entering runaway queue growth.

## 13. Circuit breakers

A circuit breaker stops repeatedly calling a dependency that is failing or timing out.

Typical states:

- closed: calls flow normally
- open: calls fail fast or use fallback
- half-open: limited probes test recovery

A breaker is not a substitute for timeouts, retries, or capacity planning. It is a containment mechanism.

### Risks

- synchronized half-open probes
- stale fallback data
- global breakers that punish healthy partitions
- thresholds that oscillate
- masking an outage instead of surfacing it

Breakers should usually be scoped to the actual failure domain: endpoint, zone, tenant, or operation type.

## 14. Bulkheads

Bulkheads prevent one workload from consuming every shared resource.

Examples:

- separate thread pools for critical and batch traffic
- per-tenant concurrency limits
- separate connection pools for read and write paths
- isolated queues for control-plane operations
- resource quotas by workload class

A single shared pool creates correlated failure. One slow dependency can consume every worker and make unrelated endpoints unavailable.

## 15. Hedged requests

A hedged request sends a second attempt after a delay, often near a high latency percentile, and uses the first successful response.

This can reduce tail latency for read-only operations with variable replica latency.

It also increases load. Hedging is appropriate only when:

- the operation is safe to duplicate
- the service has spare capacity
- hedge delay is based on observed latency
- duplicate work is canceled when possible
- the system limits hedge rate

Hedging during saturation can accelerate collapse.

## 16. Retry storm incident

### Scenario

A database slows from 20 ms to 400 ms. Application timeout is 300 ms. Each service instance retries twice immediately. The service mesh also retries once.

### Failure chain

```text
database slows
  -> application timeouts
  -> application retries
  -> mesh retries
  -> in-flight work multiplies
  -> database queue grows
  -> latency rises further
  -> more timeouts and retries
```

### Evidence

Look for:

- attempts per logical request
- timeout rate by hop
- dependency concurrency
- connection-pool wait time
- queue length
- retry reason and retry layer
- latency before and after retry amplification

### Immediate mitigation

- disable one retry layer
- reduce concurrency
- shed noncritical work
- increase timeout only when capacity and deadline permit
- route to healthy replicas if available
- pause expensive batch traffic

### Prevention

- retry budgets
- jittered backoff
- single retry owner
- propagated deadlines
- adaptive concurrency
- dashboards separating logical requests from physical attempts

## 17. Ambiguous payment incident

### Scenario

A payment provider receives a capture request. The client times out before receiving the response. The provider may have completed the capture.

### Unsafe response

Retry with a new request identifier.

This may charge the customer twice.

### Correct design

- stable idempotency key for the logical payment
- durable local state machine
- provider operation identifier
- status-query API
- reconciliation job
- explicit states such as `PENDING`, `SUCCEEDED`, `FAILED`, `UNKNOWN`

`UNKNOWN` is a legitimate distributed state. Hiding it as `FAILED` creates corruption.

### Recovery

Query by idempotency key or provider operation ID. Reconcile before initiating a distinct capture.

## 18. Queue backlog incident

### Scenario

Consumer throughput falls below producer throughput. Queue age rises for hours while queue depth remains within a large configured maximum.

### Key insight

Depth alone is insufficient. The oldest-message age often reflects customer impact more directly.

### Evidence

- arrival rate
- completion rate
- oldest-message age
- processing-time distribution
- retry count
- poison-message rate
- consumer concurrency
- downstream dependency latency

### Mitigation

- stop or reduce producers
- scale consumers only if the downstream can absorb the load
- isolate poison messages
- prioritize critical partitions
- skip or compact obsolete work when business semantics allow

### Prevention

- bounded queue-age SLO
- admission control
- autoscaling based on drain time, not depth alone
- dead-letter and quarantine workflows
- replay tooling

## 19. Observability requirements

A distributed request should carry identifiers that allow operators to reconstruct the logical operation:

- trace ID
- request ID
- idempotency key
- event ID
- tenant or workload class
- attempt number
- parent deadline
- producer timestamp and processing timestamp
- version, epoch, or offset where relevant

Metrics should distinguish:

- logical requests from physical attempts
- first attempts from retries and hedges
- client cancellations from server failures
- queue time from service time
- dependency latency from local processing
- admitted work from rejected work

Logs should capture state transitions, not merely error strings.

## 20. Design review checklist

Before approving a remote workflow, ask:

### Invariant

- What must never happen?
- Is the invariant enforced in one atomic boundary or through compensation?

### Failure

- What if the request is lost?
- What if the response is lost?
- What if the server commits and crashes?
- What if the client retries concurrently?

### Time

- What is the end-to-end deadline?
- Are deadlines propagated?
- Does any decision depend unsafely on wall-clock ordering?

### Load

- Are queues bounded?
- What applies backpressure?
- Which traffic is shed first?
- How many layers retry?

### Recovery

- Can the operation be reconciled?
- Is there a durable operation ID?
- Can operators replay or repair safely?

### Evidence

- Can logical requests be separated from attempts?
- Can an operator prove whether a side effect occurred?

## 21. Interview drills

### Why is a timeout not proof of failure?

Because the operation may have completed while the response was delayed or lost. The caller only knows that it did not observe completion before its deadline.

### Why can retries reduce availability?

They add load precisely when a dependency is already slow or failing. Without backoff, jitter, budgets, and idempotency, they amplify queues and duplicate effects.

### What is the difference between safety and liveness?

Safety prevents forbidden states; liveness ensures progress. During uncertainty, a system may sacrifice availability to preserve safety or accept conflict to preserve liveness.

### Why are unbounded queues dangerous?

They convert overload into growing latency and memory usage instead of applying backpressure. Eventually the system fails with a much larger backlog and slower recovery.

### Is exactly-once delivery realistic?

Not across arbitrary failure boundaries in the simplistic sense. Practical systems use at-least-once transport, durable identifiers, atomic state transitions, deduplication, and reconciliation to achieve one logical business effect.

## 22. Hands-on labs

### Lab 1: ambiguous completion

Build a small client and server. Make the server persist a result, then randomly drop the response. Observe that client timeouts do not reveal whether persistence occurred. Add an idempotency key and status lookup.

### Lab 2: retry amplification

Place three services in a chain. Enable two retries at each layer. Inject latency in the final service and measure physical attempts per logical request. Then assign retry ownership to one layer and compare load.

### Lab 3: bounded versus unbounded queues

Feed work faster than a consumer can process it. Compare memory, latency, and recovery time for an unbounded queue, a bounded blocking queue, and a bounded queue with explicit rejection.

### Lab 4: deadline propagation

Create a request path with sequential sleeps. Compare independent per-hop timeouts with one propagated deadline. Verify that canceled work stops consuming capacity.

### Lab 5: transactional outbox

Write a database update and event publication using an unsafe dual write. Inject crashes between steps. Then implement an outbox table and idempotent consumer.

## Principal-level summary

Reliable distributed systems are built by treating uncertainty as a first-class state.

A strong design:

- starts from business invariants
- assumes partial failure
- uses explicit deadlines
- bounds retries and queues
- makes side effects idempotent
- applies backpressure before collapse
- isolates failure domains
- preserves durable operation identity
- supports reconciliation
- exposes enough evidence to reconstruct what happened

The Principal-level question is never merely, “Which pattern should we use?”

It is:

> Under loss, delay, duplication, overload, restart, and operator error, does this design preserve the invariant, make bounded progress, and remain diagnosable?