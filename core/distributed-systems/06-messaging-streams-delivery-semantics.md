# Chapter 6 — Messaging, Streams, Delivery Semantics, and Event-Driven Systems

Messaging systems decouple producers from consumers in time, capacity, and deployment lifecycle. They can absorb bursts, preserve ordering within a scope, replay history, and isolate failures.

They can also hide overload, duplicate side effects, reorder business events, accumulate unbounded recovery work, and turn one local transaction into a distributed consistency problem.

The Staff-level goal is not to choose between a queue and a stream by product name. It is to define the business invariant, delivery contract, ordering scope, replay behavior, and failure policy end to end.

---

## 6.1 Why Introduce Messaging

Synchronous request chains couple availability and latency.

```text
client -> service A -> service B -> service C
```

If service C slows, service A and the client may also fail.

Messaging introduces a durable handoff:

```text
producer -> broker -> consumer
```

The producer may complete after the broker accepts the message, without waiting for the consumer to finish.

### Benefits

- temporal decoupling
- burst absorption
- independent scaling
- retry isolation
- replay
- fan-out
- auditability
- integration across ownership boundaries

### Costs

- eventual completion
- duplicates
- reordering
- lag
- poison messages
- schema evolution
- reconciliation
- operational state hidden in queues

Messaging does not remove complexity. It moves complexity from the synchronous request path into delivery, state management, and recovery.

---

## 6.2 Queue, Log, and Pub/Sub Models

### Work queue

A message is processed by one worker from a competing-consumer group.

```text
producer -> queue -> worker A
                  -> worker B
                  -> worker C
```

Useful for:

- background jobs
- image processing
- email delivery
- task execution
- asynchronous commands

### Append-only log or stream

Messages are ordered within partitions and retained independently of consumer acknowledgement.

```text
producer -> partition log
                   |
                   +--> consumer group A
                   +--> consumer group B
                   +--> replay consumer C
```

Useful for:

- event history
- state propagation
- change data capture
- analytics pipelines
- materialized views

### Pub/Sub

One publication is delivered to multiple subscriptions or consumers.

Useful for:

- notifications
- domain-event fan-out
- cache invalidation
- integration events

These models can overlap in modern systems, but the retention and acknowledgement semantics still matter.

---

## 6.3 Commands, Events, and Facts

### Command

A request for a specific owner to perform work.

```text
CapturePayment
GenerateInvoice
ResizeImage
```

A command usually has one intended handler.

### Event

A statement that something already happened.

```text
PaymentCaptured
InvoiceGenerated
ImageResized
```

Events may have many consumers.

### Fact quality

A valid event should represent durable state, not merely an intention that might later roll back.

Publishing `OrderCreated` before the order transaction commits can create consumers acting on a fact that never became true.

### Naming rule

- command: imperative verb
- event: past-tense fact

This improves ownership reasoning and reduces accidental command broadcasting.

---

## 6.4 Delivery Semantics

Delivery semantics are often described as at-most-once, at-least-once, and exactly-once.

These labels are incomplete unless the system defines the boundary.

### At-most-once delivery

A message is attempted zero or one time.

Benefits:

- no broker-driven duplicate delivery
- simple consumers

Risk:

- messages may be lost on failure

Useful when:

- loss is acceptable
- work can be regenerated
- duplicates are more damaging than omission

### At-least-once delivery

A message is retried until acknowledgement or terminal policy.

Benefits:

- durable work is less likely to be lost

Risks:

- duplicate delivery
- duplicate side effects
- retry amplification

Consumers must be idempotent or deduplicate.

### Exactly-once claims

Ask exactly once at which boundary:

- broker delivery
- handler execution
- database state transition
- external API call
- business outcome

A consumer can update a database and crash before acknowledging. The broker then redelivers.

Therefore, a broker setting alone cannot guarantee one business effect across arbitrary external systems.

### Effectively-once processing

A practical pattern uses:

- at-least-once transport
- stable message ID
- atomic state transition
- deduplication record
- idempotent external API
- reconciliation

The handler may execute multiple times while the business effect remains one logical outcome.

---

## 6.5 Acknowledgement Boundaries

Acknowledgement defines when the broker may consider work complete.

Possible acknowledgement points:

1. message received in memory
2. message written to local disk
3. message replicated to quorum
4. consumer fetched message
5. consumer completed local transaction
6. consumer completed all external effects

Each point provides different guarantees.

### Unsafe early acknowledgement

```text
consume message
acknowledge
write database
```

A crash after acknowledgement loses the work.

### Safer acknowledgement

```text
consume message
commit durable local state and dedupe record
acknowledge
```

External effects may still require idempotency and reconciliation.

### Staff-level requirement

Document the exact durability boundary for producer acknowledgement and the exact completion boundary for consumer acknowledgement.

---

## 6.6 Producer Reliability

A producer may not know whether publication succeeded.

```text
producer sends
  -> broker stores message
  -> acknowledgement is lost
```

The producer times out and retries. The broker may receive a duplicate.

### Producer requirements

- stable event ID across retry
- bounded retry policy
- backoff and jitter
- delivery timeout
- broker acknowledgement level
- local persistence when publication is business-critical

### Idempotent producer

Some brokers can deduplicate repeated sends from one producer session using producer IDs and sequence numbers.

This reduces duplicates inside the broker but does not automatically deduplicate:

- application restarts without preserved identity
- events generated twice by business logic
- downstream external effects

---

## 6.7 The Dual-Write Problem

A service often needs to update its database and publish an event.

```text
1. update order
2. publish OrderConfirmed
```

Failure between steps creates inconsistency.

Reversing the order does not solve it.

```text
1. publish OrderConfirmed
2. update order
```

Now consumers may observe an event for a transaction that later fails.

### Transactional outbox

Write the business change and an outbox row in one local transaction.

```text
BEGIN
  UPDATE orders SET status='CONFIRMED' WHERE id=?;
  INSERT INTO outbox(event_id, event_type, payload) VALUES (...);
COMMIT
```

A relay publishes the outbox asynchronously.

Publication may happen more than once, so consumers still deduplicate.

### Change data capture

Instead of polling an outbox, a log-based capture system can stream committed changes.

Requirements still include:

- event schema
- ordering
- duplicate handling
- replay
- retention
- poison-record policy

### Inbox pattern

A consumer records processed message IDs or applies the message and dedupe marker atomically.

```text
BEGIN
  INSERT INTO inbox(message_id) VALUES (?) ON CONFLICT FAIL;
  UPDATE business_state ...;
COMMIT
```

Duplicate delivery causes the unique constraint to reject repeat application.

---

## 6.8 Ordering Guarantees

Global total order is expensive and often unnecessary.

Most scalable messaging systems provide ordering only within a partition, queue, session, or key.

### Questions to answer

- Which events must be ordered relative to each other?
- What key defines that ordering scope?
- Can independent entities process concurrently?
- What happens when one event is delayed?
- Can a newer version safely overtake an older one?

### Per-entity ordering

Key messages by aggregate or entity ID.

```text
customer-42 -> partition 7
```

All events for that customer use the same partition.

Trade-off:

- preserves order
- one high-volume entity limits parallelism

### Global ordering

A single partition can provide global order but creates:

- throughput ceiling
- larger blast radius
- slow recovery
- one poisoned-message bottleneck

Use global ordering only when the business invariant truly requires it.

---

## 6.9 Out-of-Order Events

Even with partition ordering, out-of-order arrival can occur because of:

- multiple producers
- retries
- different topics
- replay
- network delays
- partition migration
- consumer concurrency

### Version-based handling

Include an entity version:

```text
OrderUpdated { order_id: 91, version: 17 }
```

The consumer stores the highest applied version.

Behavior:

- version 17 after 16: apply
- version 17 after 17: duplicate
- version 15 after 17: stale, ignore or audit
- version 19 after 17: gap, buffer or repair

### Sequence gaps

A gap does not always mean data loss. The missing event may be delayed.

Policies include:

- wait for bounded time
- query source of truth
- request replay
- apply newer state snapshot
- mark entity for reconciliation

---

## 6.10 Event Time, Processing Time, and Watermarks

### Event time

When the event occurred in the source domain.

### Ingestion time

When the messaging system accepted it.

### Processing time

When a consumer processed it.

These can differ significantly.

### Late data

A mobile device may upload events hours later. A stream processor using only processing time can place them in the wrong window.

### Watermark

A watermark estimates that events earlier than a given event time are unlikely to arrive later.

Watermarks allow systems to close windows while still accepting some late data.

### Trade-off

Longer lateness allowance:

- more complete results
- higher state retention
- slower finality

Shorter lateness allowance:

- faster output
- more corrections or dropped late events

The business should define when results are provisional versus final.

---

## 6.11 Consumer Groups and Parallelism

A consumer group distributes partitions across members.

A partition normally has one active consumer within a group.

```text
partition 0 -> consumer A
partition 1 -> consumer B
partition 2 -> consumer C
partition 3 -> consumer A
```

Maximum useful parallelism is bounded by partition count.

### Too few partitions

- insufficient concurrency
- poor scale-out
- large recovery units

### Too many partitions

- metadata overhead
- more open files and connections
- longer coordination operations
- smaller batches
- more complex rebalancing

Partition count is a long-lived capacity decision.

---

## 6.12 Consumer Rebalancing

When consumers join, leave, or fail, partitions are reassigned.

### Failure risks

- stop-the-world pauses
- duplicate processing
- lost in-memory state
- abandoned external work
- commit of incorrect offsets

### Cooperative rebalancing

A cooperative strategy can transfer only affected partitions instead of revoking all assignments at once.

### Revocation handling

Before losing a partition, a consumer should:

- stop accepting new records for it
- complete or cancel in-flight work
- flush state
- commit safe progress
- release resources

### Static membership

Stable member identity can reduce unnecessary rebalances during short restarts.

It does not remove the need to handle real ownership changes safely.

---

## 6.13 Offsets and Checkpoints

An offset identifies progress in a partitioned log.

### Commit before processing

```text
commit offset
process record
```

Risk: message loss on crash.

### Commit after processing

```text
process record
commit offset
```

Risk: duplicate processing on crash before commit.

### Atomic state and offset

Some systems allow output state and consumed offsets to commit together within one transactional boundary.

This can provide exactly-once semantics inside a constrained ecosystem.

It does not automatically include arbitrary external APIs.

### Checkpoint design

A checkpoint should be:

- durable
- monotonic
- partition-specific
- recoverable
- tied to the applied state version

---

## 6.14 Lag and Backlog

Consumer lag measures the difference between produced and consumed positions.

Lag can be expressed as:

- message count
- bytes
- event-time delay
- wall-clock age of oldest unprocessed message

Message count alone can mislead when message sizes or arrival rates vary.

### Backlog age

For user-impact reasoning, the age of the oldest required message is often more meaningful.

A queue with one million tiny messages may clear quickly.

A queue with 10,000 expensive jobs may require hours.

### Drain-time estimate

```text
backlog drain time = backlog work / (consumer capacity - arrival rate)
```

If arrival rate is equal to or greater than processing capacity, the backlog never drains.

---

## 6.15 Little's Law for Messaging

Little's Law applies:

```text
items in system = arrival rate * average time in system
```

If a queue receives 1,000 jobs per second and average completion time is 30 seconds, approximately 30,000 jobs are in the system.

Rising latency increases in-flight work and storage requirements even when arrival rate is unchanged.

### Operational lesson

A queue can keep producers healthy while consumer latency silently violates the business SLO.

Availability of enqueue is not completion availability.

---

## 6.16 Backpressure and Admission Control

A durable queue is not infinite capacity.

Without admission control, backlog can exceed:

- retention period
- storage capacity
- recovery window
- business usefulness
- downstream rate limits

### Producer-side controls

- quotas
- rate limits
- concurrency limits
- priority classes
- reject nonessential work
- aggregate or sample telemetry

### Consumer-side controls

- bounded in-flight messages
- prefetch limits
- batch sizing
- downstream concurrency caps
- pause partitions when dependency is unhealthy

### Business expiry

Some work loses value with age.

Examples:

- promotional notification
- real-time recommendation update
- stale sensor alert

Messages should include a deadline or expiration policy so obsolete work can be discarded intentionally.

---

## 6.17 Retry Topologies

Retries can occur:

- in the consumer process
- by negative acknowledgement
- through delayed retry queues
- by republishing with future delivery
- through workflow orchestration

### Immediate retry

Appropriate only for very short transient failures.

Risk: hot loop and dependency overload.

### Delayed retry

Use exponential backoff and jitter.

Example stages:

```text
retry-1m
retry-5m
retry-30m
retry-4h
```

### Retry metadata

Include or preserve:

- original message ID
- attempt count
- first-seen time
- last error class
- next eligible time
- correlation ID

### Retry ownership

Only one layer should normally own retry timing. Consumer library, broker, workflow engine, and application retries should not multiply invisibly.

---

## 6.18 Poison Messages

A poison message repeatedly fails because of:

- invalid schema
- impossible business state
- corrupted payload
- code bug
- unsupported version
- dependency-specific permanent error

Blind retries block progress and waste capacity.

### Required policy

- classify transient versus permanent
- bound attempts
- isolate the message
- retain full diagnostic context
- alert based on business importance
- provide replay after correction

### Dead-letter queue

A dead-letter queue stores messages that exceeded retry policy.

A DLQ is not a solution by itself.

A mature DLQ process defines:

- ownership
- triage SLO
- retention
- privacy controls
- replay tooling
- deduplication on replay
- bulk remediation

An unowned DLQ is a silent data-loss archive.

---

## 6.19 Ordered Partition and Poisoned Head

Strict ordering can cause one failed message to block every later message in the partition.

Options:

- stop and repair to preserve strict order
- move the failed message to a parking queue and continue
- split entities into narrower ordering keys
- apply later versions and reconcile the gap

The choice depends on the invariant.

For a financial ledger, skipping may be unsafe.

For email notifications, skipping one malformed message may be acceptable.

Ordering is a business policy, not merely a broker setting.

---

## 6.20 Message Schema Design

A durable event becomes an API consumed across time and teams.

### Good event properties

- stable event type
- unique event ID
- producer identity
- entity or aggregate ID
- entity version
- event time
- schema version
- trace or correlation context
- payload with clear semantics

### Envelope example

```json
{
  "event_id": "evt-7f8b",
  "event_type": "OrderConfirmed",
  "schema_version": 3,
  "occurred_at": "2026-07-26T20:42:11Z",
  "aggregate_id": "order-9182",
  "aggregate_version": 14,
  "producer": "orders-service",
  "trace_id": "...",
  "data": {}
}
```

### Avoid ambiguous fields

Bad:

```text
status: 4
```

Better:

```text
status: "CONFIRMED"
```

Schema meaning should not depend on hidden database enums or internal implementation details.

---

## 6.21 Schema Evolution

Messages may outlive the code that produced them.

Consumers may deploy before or after producers.

### Compatibility models

- backward compatibility: new consumer reads old data
- forward compatibility: old consumer reads new data
- full compatibility: both directions

### Safe additive evolution

- add optional fields with defaults
- preserve existing field meaning
- avoid reusing removed field identifiers
- tolerate unknown fields

### Unsafe evolution

- change field meaning
- change units silently
- make optional field required
- reinterpret timestamp timezone
- split one event without migration plan

### Consumer-driven validation

A schema registry can enforce structural compatibility, but semantic compatibility still requires review and tests.

---

## 6.22 Event Versioning Strategies

### One evolving event type

```text
OrderConfirmed v1 -> v2 -> v3
```

Good when semantics remain stable and changes are additive.

### New event type

```text
OrderConfirmed
OrderSettlementCompleted
```

Use when business meaning changes materially.

### Upcasting

A consumer or framework transforms old versions into the current in-memory representation.

This simplifies application logic but requires deterministic migration code.

### Dual publication

Publishing old and new formats temporarily can support migration, but it risks:

- duplicate business handling
- unclear authority
- extended migration forever

Use explicit cutover criteria and telemetry.

---

## 6.23 Event Sourcing

Event sourcing stores state changes as an append-only event sequence.

```text
AccountOpened
MoneyDeposited
MoneyWithdrawn
AddressChanged
```

Current state is derived by replaying events or loading a snapshot plus later events.

### Benefits

- audit history
- temporal reconstruction
- new projections
- replay
- explicit state transitions

### Costs

- schema evolution forever
- replay correctness
- large histories
- deletion and privacy challenges
- event-order dependence
- difficult ad hoc queries

### Important distinction

Using a message broker does not automatically mean event sourcing.

Event sourcing makes the event log the authoritative source of state.

A normal event-driven system may still use a relational database as source of truth and publish derived events.

---

## 6.24 Snapshots and Replay

Replaying millions of events per entity may be too slow.

A snapshot stores derived state at a known version.

```text
snapshot at version 10,000
replay events 10,001 onward
```

### Snapshot requirements

- versioned schema
- verified event position
- rebuild capability
- invalidation policy

A snapshot is an optimization, not the source of truth, unless explicitly designed otherwise.

### Replay safety

Before replaying into production consumers, define:

- idempotency behavior
- side-effect suppression
- rate limits
- ordering
- checkpoint namespace
- destination isolation

Replaying historical events into an email or payment consumer without safeguards can repeat real-world side effects.

---

## 6.25 Materialized Views and Projections

A projection consumes events and builds query-optimized state.

Examples:

- customer order history
- product inventory view
- search index
- fraud feature store
- analytics aggregate

### Properties

A projection is usually:

- derived
- eventually consistent
- rebuildable
- independently scalable

### Drift detection

Derived state can diverge because of:

- missed events
- consumer bug
- schema mismatch
- manual data change
- replay error

Use:

- source version checks
- row counts and checksums
- periodic reconciliation
- full rebuild tests
- lag and gap monitoring

A derived view should not silently become an unrecoverable source of truth.

---

## 6.26 Choreography Versus Orchestration

### Choreography

Services react to events without a central workflow owner.

```text
OrderPlaced
  -> inventory reserves
  -> payment captures
  -> shipping prepares
```

Benefits:

- loose coupling
- independent consumers
- easy fan-out

Risks:

- hidden workflow
- difficult failure reasoning
- cycles
- unclear ownership
- hard compensation

### Orchestration

A workflow owner sends commands and tracks state.

```text
orchestrator
  -> ReserveInventory
  -> CapturePayment
  -> CreateShipment
```

Benefits:

- explicit state machine
- centralized timeout and compensation
- easier operator visibility

Risks:

- coordinator complexity
- central dependency
- service coupling through workflow protocol

### Staff-level rule

Use events for facts and fan-out. Use explicit orchestration when a business process has ordered steps, deadlines, compensation, and a clear owner.

---

## 6.27 Sagas

A saga is a sequence of local transactions coordinated through messages or orchestration.

Each step commits independently.

Failure may trigger compensating actions.

### Example

```text
1. reserve inventory
2. authorize payment
3. create shipment
```

If shipment creation fails:

```text
- release inventory
- void payment authorization
```

### Compensation is not rollback

A compensation is another business action.

It may:

- fail
- be delayed
- be irreversible
- require human review

### Saga design requirements

- durable workflow state
- idempotent steps
- idempotent compensations
- timeouts
- terminal states
- manual intervention path
- audit history

---

## 6.28 Transactional Messaging Within a Broker

Some systems allow a producer to atomically:

- consume records
- publish derived records
- commit input offsets

This is useful for stream-to-stream processing.

It can prevent duplicate outputs inside the same broker ecosystem when configured correctly.

It does not automatically include:

- relational databases outside the transaction
- email providers
- payment processors
- object storage
- arbitrary HTTP services

The guarantee boundary must be stated precisely.

---

## 6.29 Fan-Out and Amplification

One event may trigger many downstream messages.

```text
OrderPlaced
  +--> inventory
  +--> payment
  +--> analytics
  +--> email
  +--> recommendations
  +--> fraud
```

Each consumer may publish more events.

### Amplification risks

- traffic explosion
- cyclic publication
- duplicated downstream work
- unbounded retry multiplication
- hard-to-predict recovery load

### Controls

- event lineage
- per-topic quotas
- loop detection
- retry budgets
- fan-out accounting
- backpressure
- consumer ownership registry

Measure physical messages per logical business event.

---

## 6.30 Priority and Fairness

A shared queue can let bulk work delay critical work.

### Strategies

- separate queues by priority
- weighted scheduling
- reserved consumer capacity
- tenant quotas
- age-based promotion
- deadline-aware scheduling

### Starvation risk

Strict priority may starve lower-priority work indefinitely.

A mature scheduler balances:

- urgency
- business value
- fairness
- age
- resource cost

Priority should be part of the message contract, not inferred from topic names alone.

---

## 6.31 Multi-Tenant Messaging

Shared brokers need isolation across tenants.

Controls include:

- publish quotas
- consume quotas
- per-tenant lag limits
- message-size limits
- namespace isolation
- encryption and authorization
- retention policies
- noisy-neighbor protection

### Large tenant risk

One tenant may generate enough backlog to consume all storage or consumer capacity.

Tenant-aware partitions or dedicated topics may be required for the largest tenants.

---

## 6.32 Security and Data Governance

Messages may contain sensitive data and remain retained for long periods.

Review:

- least-privilege publish and consume permissions
- encryption in transit and at rest
- payload minimization
- secrets exclusion
- tenant isolation
- retention and deletion
- audit logs
- replay authorization

### Deletion challenge

Append-only logs conflict with deletion requirements.

Options include:

- short retention
- tokenized identifiers
- encrypted payloads with destroyable keys
- compaction by key
- externalized sensitive data referenced by ID

Governance must be part of event design from the beginning.

---

## 6.33 Observability

A messaging platform should expose four layers.

### Producer

- publish rate
- publish latency
- failed sends
- retries
- acknowledgement level
- message size

### Broker

- partition leadership
- replication health
- disk usage
- under-replicated partitions
- queue depth
- throughput
- throttling

### Consumer

- processing rate
- error rate
- retry rate
- in-flight messages
- offset commits
- rebalance count
- dependency latency

### Business

- oldest unprocessed business event
- orders awaiting payment
- invoices awaiting generation
- notifications expired before delivery
- messages in manual-review state

Infrastructure lag is not enough. Operators need business-state visibility.

---

## 6.34 Trace Context Across Asynchronous Boundaries

A message should propagate correlation context, but one trace may span minutes or days.

Useful fields include:

- trace ID
- causation ID
- correlation ID
- parent event ID
- workflow ID

### Causation versus correlation

- causation ID: which specific message caused this message
- correlation ID: which broader business workflow these messages belong to

This enables event lineage without pretending the workflow is one synchronous span.

---

## 6.35 Incident: Consumer Applies Side Effect Twice

### Scenario

A consumer charges a payment provider and then crashes before acknowledging the message.

The broker redelivers.

The consumer charges again.

### Root cause

At-least-once delivery was combined with a non-idempotent external side effect.

### Safe design

- stable payment operation ID
- provider idempotency key
- durable local state machine
- query provider after ambiguous timeout
- acknowledge only after durable local result

### Lesson

Exactly-once business effect requires end-to-end idempotency and reconciliation.

---

## 6.36 Incident: Queue Hides a Capacity Failure

### Scenario

Producer rate is 5,000 jobs per second. Consumers process 4,000 jobs per second.

The enqueue API remains healthy.

Backlog grows by 1,000 jobs per second.

After one hour:

```text
3,600,000 additional jobs
```

### Failure

The service reports availability because enqueue succeeds, while completion delay exceeds the user SLO.

### Correct signals

- oldest-message age
- estimated drain time
- completion success rate
- expiry count
- consumer capacity margin

### Lesson

A queue converts immediate failure into delayed failure unless capacity and backlog SLOs are enforced.

---

## 6.37 Incident: Poison Message Blocks Ordered Partition

### Scenario

One malformed event repeatedly fails. Strict ordering prevents the consumer from processing later records in the same partition.

### Choices

- stop and repair
- park and continue
- reconstruct entity state from source
- deploy compatibility fix

### Decision basis

- invariant requiring order
- business impact of delay
- ability to reconcile
- risk of skipping

### Prevention

- schema validation at publish time
- compatibility tests
- bounded retries
- parking workflow
- per-entity partitioning instead of coarse global ordering

---

## 6.38 Incident: Replay Sends Historical Emails

### Scenario

An analytics team replays a topic from the beginning. An email consumer accidentally uses the same consumer group namespace and receives historical events.

Thousands of old emails are sent.

### Prevention

- environment and purpose-specific consumer identities
- side-effect-disabled replay mode
- topic access controls
- replay approval process
- output isolation
- dry-run counts

### Lesson

Replay is a privileged production operation with real-world side effects.

---

## 6.39 Incident: Schema Change Breaks Old Consumer

### Scenario

A producer changes `amount_cents` from integer cents to decimal dollars without changing the field name.

Old consumers interpret `$19.99` incorrectly or fail parsing.

### Root cause

Semantic incompatibility hidden behind a structurally similar schema.

### Prevention

- immutable field meaning
- explicit new field
- schema review
- consumer compatibility tests
- staged migration

---

## 6.40 Design Review Checklist

Before approving an event-driven design, ask:

- Is this message a command or an event?
- What durable fact does it represent?
- What is the source of truth?
- When is the producer allowed to acknowledge success?
- What happens if publication outcome is ambiguous?
- Is a transactional outbox required?
- What delivery guarantee does the broker provide?
- What business effect must be effectively once?
- What is the idempotency key?
- What ordering scope is required?
- What key chooses the partition?
- How are gaps and stale versions handled?
- When is the consumer allowed to acknowledge?
- Where are offsets stored?
- What is the retry owner?
- What is the poison-message policy?
- Who owns the DLQ?
- What is the replay policy?
- Can replay repeat external side effects?
- What is the schema compatibility policy?
- How is backlog age monitored?
- What is the drain-time SLO?
- How are tenants isolated?
- Which data may not be placed in messages?
- How is event lineage observed?

---

## 6.41 Staff and Principal Interview Drills

### Question 1

A broker advertises exactly-once processing. A consumer writes to a database and calls a payment API. Is the business workflow exactly once?

A strong answer should discuss:

- guarantee boundary
- database transaction
- external side effect
- idempotency key
- ambiguous outcomes
- reconciliation

### Question 2

How do you publish an event reliably after updating a relational database?

Expected direction:

- transactional outbox
- change data capture
- at-least-once relay
- consumer deduplication

### Question 3

What key would you choose for an order-event stream?

Expected direction:

- required ordering scope
- `order_id` versus `customer_id`
- hot-key risk
- consumer parallelism
- cross-order invariants

### Question 4

A queue has 20 million messages. Is that an incident?

Expected direction:

- message count alone is insufficient
- oldest age
- arrival and processing rates
- drain time
- business deadline
- storage and retention

### Question 5

How do you safely replay a production topic?

Expected direction:

- isolated consumer identity
- side-effect control
- idempotency
- rate limit
- checkpoint namespace
- dry run
- approval and observability

### Question 6

What is the difference between event sourcing and event-driven integration?

Expected direction:

- authoritative event log versus published derived facts
- state reconstruction
- replay and schema implications

### Question 7

When would you use orchestration instead of choreography?

Expected direction:

- multi-step business workflow
- deadlines
- compensation
- explicit ownership
- operator visibility

### Question 8

How do you prevent one poison message from blocking a partition forever?

Expected direction:

- bounded retries
- classification
- parking or DLQ
- invariant-aware skip policy
- replay after repair

---

## 6.42 Hands-On Labs

### Lab 1 — Duplicate Delivery

1. Consume a message.
2. Apply a database update.
3. Crash before acknowledgement.
4. Observe redelivery.
5. Add a unique message ID and atomic inbox record.
6. Verify one logical state transition.

### Lab 2 — Transactional Outbox

Build a service that:

1. updates an order
2. inserts an outbox event in one transaction
3. publishes asynchronously
4. retries publication
5. demonstrates consumer deduplication

### Lab 3 — Ordering and Partition Keys

Publish events for multiple customers and orders.

Compare keys:

- random
- `order_id`
- `customer_id`

Measure ordering scope, hot partitions, and consumer parallelism.

### Lab 4 — Poison Message Workflow

1. inject an invalid event
2. use bounded retries
3. move it to a parking queue
4. continue the partition where policy permits
5. repair and replay safely

### Lab 5 — Backlog Drain Time

Create producers faster than consumers.

Measure:

- lag count
- oldest age
- processing rate
- arrival rate
- estimated drain time

Scale consumers and confirm the estimate.

### Lab 6 — Schema Evolution

Create version 1 and version 2 producers and consumers.

Test:

- additive optional field
- removed field
- changed semantic meaning
- unknown field tolerance

### Lab 7 — Replay Safety

Replay historical events into a shadow projection.

Add controls so email, payment, and other real-world side effects cannot execute.

### Lab 8 — Saga Failure Injection

Implement a workflow with inventory, payment, and shipment steps.

Crash after each step and compensation. Verify eventual terminal state and no duplicate business effects.

---

## 6.43 Staff-Level Summary

Messaging moves work across time and failure boundaries.

A production-grade design must define:

```text
business invariant
  -> message meaning
  -> publication durability
  -> delivery and ordering scope
  -> idempotent state transition
  -> retry and poison policy
  -> replay and reconciliation
```

The strongest Staff-level answer does not claim that a broker makes the workflow reliable. It explains how producer state, broker state, consumer state, and external side effects converge under duplicate delivery, crashes, reordering, lag, and replay.
