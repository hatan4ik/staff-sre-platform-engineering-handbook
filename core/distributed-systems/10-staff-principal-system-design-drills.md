# Chapter 10 — Staff and Principal Distributed-System Design Drills

Staff and Principal interviews are not won by naming components. They are won by exposing the business invariant, choosing the consistency boundary, sizing the system, describing failure behavior, and proving operability.

This chapter provides a repeatable answer method and a set of high-depth design drills.

---

## 10.1 The Staff-Level Answer Framework

Use the following sequence.

### 1. Clarify the business outcome

Ask:

- Who uses the system?
- What operation matters most?
- What must never happen?
- What may be delayed or stale?

### 2. Quantify scale

Estimate:

- requests per second
- peak-to-average ratio
- read/write ratio
- object size
- retention
- fan-out
- regional distribution

### 3. Define the data model and source of truth

Identify:

- entities
- keys
- state machine
- authoritative store
- derived indexes and caches

### 4. Define consistency and durability

State:

- linearizable or eventual operations
- read-your-writes requirement
- acknowledgement boundary
- RPO and RTO

### 5. Draw the normal path

Keep it simple and explain why each component exists.

### 6. Walk the failure paths

Cover:

- timeout
- duplicate
- partition
- stale replica
- overload
- failover
- replay

### 7. Explain scaling

Cover:

- partition key
- hot keys
- rebalancing
- cache policy
- consumer parallelism

### 8. Explain operability

Cover:

- SLO
- telemetry
- reconciliation
- runbook
- migration and rollback

### 9. Discuss trade-offs

Name alternatives and why the chosen design fits the invariant.

---

## 10.2 Whiteboard Pattern

A clear interview whiteboard can use five sections.

```text
Requirements | Scale | Data model | Architecture | Failures & operations
```

Do not fill the board with product logos before establishing the invariant.

A strong answer should be understandable even if all vendor names are removed.

---

## 10.3 Capacity Estimation Pattern

Suppose a service receives:

- 100 million requests per day
- 10x peak-to-average ratio
- 2 KB average request

Average requests per second:

```text
100,000,000 / 86,400 ≈ 1,157 RPS
```

Peak:

```text
≈ 11,570 RPS
```

Daily ingress:

```text
100,000,000 * 2 KB ≈ 200 GB/day
```

The exact number matters less than showing:

- order of magnitude
- peak planning
- storage growth
- replication factor
- recovery bandwidth

---

## 10.4 Drill 1 — Globally Unique ID Service

### Requirements

Generate IDs that are:

- unique
- roughly time sortable
- available across regions
- high throughput

### Design choices

#### Central sequence

Strong ordering, simple uniqueness, but central bottleneck and availability dependency.

#### Region or worker allocation

Allocate unique worker or range IDs through a coordination service.

ID structure:

```text
timestamp | region | worker | sequence
```

### Failure questions

- What if clocks move backward?
- What if worker ID is reused?
- What if sequence overflows within one millisecond?
- Is strict global order required?

### Strong answer

Use monotonic handling, worker-epoch allocation, and reject or wait on clock regression. Explain that uniqueness is the invariant; perfect global chronological order is usually unnecessary.

---

## 10.5 Drill 2 — Distributed Rate Limiter

### Requirements

Limit API traffic by:

- tenant
- user
- endpoint
- global service capacity

### Design

Use hierarchical limits:

```text
local token bucket
  -> regional quota
      -> global quota allocation
```

### Why not one global counter?

- latency
- coordination bottleneck
- global dependency
- partition behavior

### Failure policy

- fail open for low-risk analytics
- fail closed for abuse-sensitive operations
- use bounded local leases for quota

### Observability

- allowed and rejected requests
- quota allocation lag
- top tenants
- local versus global decisions

---

## 10.6 Drill 3 — Payment Idempotency Service

### Invariant

One logical purchase must produce at most one successful capture.

### Data model

```text
idempotency_key
request_hash
payment_state
provider_operation_id
final_response
version
```

### Flow

1. Atomically create idempotency record.
2. Reject same key with different request hash.
3. Call provider with stable idempotency key.
4. Persist result.
5. Return stored result on retry.

### Ambiguous timeout

Query provider status using operation ID before retrying.

### Failure handling

- crash before provider call
- provider success with lost response
- crash before local persistence
- concurrent duplicate requests

### Staff-level extension

Explain reconciliation and manual-review states, not only the happy path.

---

## 10.7 Drill 4 — Inventory Reservation System

### Invariant

Do not oversell when the business forbids it.

### Model

```text
available
reserved
sold
reservation_expiry
```

### Local transaction

For one SKU shard:

```text
if available >= quantity:
    decrement available
    increment reserved
    create reservation with expiry
```

### Scale

Partition by SKU or SKU-region.

### Hot product

Options:

- regional allocation
- escrow counters
- queue serialized reservations
- dynamic sub-shards with central allocation

### Failure questions

- expired reservation not released
- duplicate checkout
- region partition
- stale availability cache

### Trade-off

Show whether the system prefers availability or strict no-oversell behavior during partition.

---

## 10.8 Drill 5 — Multi-Region Shopping Cart

### Requirements

- writes accepted in multiple regions
- low latency
- temporary divergence acceptable

### Model

A cart is a set or map of item operations.

Conflict strategies:

- add-wins set
- remove-wins set
- per-item version
- operation log

### Challenge

A delete in one region and quantity increase in another are concurrent.

The design must define business semantics rather than relying on last-write-wins timestamps.

### Staff-level answer

Use deterministic merge rules and preserve user intent where possible. Validate price and inventory at checkout under stronger consistency.

---

## 10.9 Drill 6 — URL Shortener

### Requirements

- create short alias
- redirect quickly
- high read ratio
- custom alias uniqueness

### Data model

```text
short_code -> long_url, owner, created_at, expiry
```

### Write path

- generated code: uniqueness through ID or random collision check
- custom alias: linearizable uniqueness constraint

### Read path

- edge cache
- regional cache
- authoritative key-value store

### Failure questions

- deleted or expired aliases
- malicious URLs
- cache invalidation
- hot viral link

### Extension

Analytics should be asynchronous and must not block redirect.

---

## 10.10 Drill 7 — Notification Platform

### Requirements

Send email, SMS, push, and webhooks.

### Architecture

```text
API
  -> durable request record
  -> channel queues
  -> provider adapters
  -> delivery status events
```

### Invariants

- no silent loss after acceptance
- bounded duplicate delivery according to channel
- user preferences and opt-outs honored

### Design points

- idempotency key
- per-provider rate limits
- retry classification
- expiration
- priority
- DLQ ownership

### Failure questions

- provider timeout after acceptance
- webhook destination returns 500
- old notification replay
- tenant floods platform

---

## 10.11 Drill 8 — Distributed Job Scheduler

### Requirements

- scheduled and recurring jobs
- at-least-once execution
- retries
- leader failover

### Data model

```text
job_id
next_run_at
schedule
state
lease_owner
lease_epoch
attempt
```

### Ownership

Workers claim jobs using compare-and-swap or transactional lease.

The downstream resource should use job attempt or fencing token where duplicate execution is unsafe.

### Clock issue

Use database or coordinator ordering where possible; do not assume all worker clocks agree.

### Recovery

Expired leases make jobs eligible again. Handlers remain idempotent.

---

## 10.12 Drill 9 — Configuration Distribution System

### Requirements

- publish configuration
- region-wide read availability
- versioning
- rollback
- some keys safety critical

### Architecture

- consensus-backed source of truth
- versioned snapshots
- watch stream
- local cache

### Client behavior

- last-known-good configuration
- minimum supported version
- signature or checksum validation
- explicit handling of stale config

### Failure policy

A recommendation flag may use stale config. A security kill switch may require stronger freshness or fail closed.

---

## 10.13 Drill 10 — Service Discovery

### Requirements

- register endpoints
- health and readiness
- fast lookup
- zone-aware routing

### Design

- strongly consistent membership control plane
- cached client or proxy view
- leases for registration
- graceful draining

### Failure questions

- stale endpoint
- registry unavailable
- client DNS cache
- mass restart

### Staff-level answer

Separate liveness from readiness and avoid making every request depend synchronously on the registry.

---

## 10.14 Drill 11 — Distributed Lock Service

### Requirements

Exclusive ownership of a resource.

### Design

- consensus-backed lease
- monotonic fencing token
- resource validates token

### Critical point

A lease alone is insufficient because a paused process may resume after expiration.

### Failure questions

- GC pause
- network partition
- clock skew
- client retry

### Strong answer

Use fencing at the protected resource and explain when a lock should be replaced by compare-and-swap or transactional ownership.

---

## 10.15 Drill 12 — Feature Flag Platform

### Requirements

- low-latency evaluation
- targeting rules
- rapid kill switch
- audit history

### Architecture

- authoritative control plane
- versioned distribution stream
- local SDK evaluation
- last-known-good cache

### Consistency classes

- experimentation flag: eventual propagation acceptable
- safety kill switch: aggressive propagation and server-side enforcement may be required

### Failure questions

- stale SDK cache
- invalid rule
- global rollout mistake

### Operability

- staged rollout
- blast-radius controls
- rollback
- audit

---

## 10.16 Drill 13 — Metrics Ingestion Platform

### Requirements

- millions of samples per second
- high cardinality
- regional ingestion
- query by time and labels

### Architecture

```text
ingest gateways
  -> partitioned durable log
  -> validation and aggregation
  -> time-series storage
  -> query tier
```

### Partitioning

Hash by tenant and series identity, with controls for hot tenants.

### Backpressure

- tenant quotas
- sample or drop low-priority metrics
- bounded queues

### Storage

- compression
- downsampling
- retention tiers

### Failure policy

Telemetry may tolerate bounded loss, but billing or security metrics may require stronger durability.

---

## 10.17 Drill 14 — Log Search Platform

### Requirements

- ingest logs
- search recent data quickly
- retain historical data cheaply

### Architecture

- regional collectors
- durable stream
- index pipeline
- hot search tier
- object storage archive

### Challenges

- unbounded fields
- tenant isolation
- indexing backlog
- schema-on-read versus schema-on-write

### SLO

Separate ingest acceptance from searchable freshness.

A log accepted now may not become searchable immediately.

---

## 10.18 Drill 15 — Distributed Trace Platform

### Requirements

- ingest spans
- reconstruct traces
- tail sampling
- search by service and error

### Design

Partition by trace ID so spans for one trace converge.

### Challenges

- late spans
- huge traces
- sampling consistency
- cardinality

### Strategy

- bounded trace assembly window
- tail sampling decisions
- object storage for full trace
- indexes for selected attributes

### Failure policy

Observability pipeline should not overload production applications. SDKs need bounded buffers and drop policy.

---

## 10.19 Drill 16 — Chat and Messaging Service

### Requirements

- one-to-one and group messages
- offline delivery
- ordering per conversation
- multi-device synchronization

### Model

```text
conversation_id
message_id
sender_id
sequence
content
```

### Partitioning

Partition by conversation ID for ordering.

### Hot group

Large groups require fan-out strategy:

- fan-out on write
- fan-out on read
- hybrid based on group size

### Delivery

Use per-device cursors and idempotent message IDs.

### Failure questions

- duplicate send
- out-of-order receipt
- deleted message
- offline device replay

---

## 10.20 Drill 17 — News Feed

### Requirements

- personalized feed
- celebrity accounts
- low read latency

### Strategies

#### Fan-out on write

Push post references to follower inboxes.

Good for normal users, expensive for celebrities.

#### Fan-out on read

Merge posts from followed accounts at read time.

Good for celebrities, higher read cost.

#### Hybrid

Fan-out normal accounts; merge celebrity posts at read time.

### Challenges

- ranking
- delete propagation
- cache invalidation
- hot keys

---

## 10.21 Drill 18 — Search Autocomplete

### Requirements

- low latency
- prefix lookup
- popularity ranking
- updates from query stream

### Architecture

- offline or streaming aggregation
- prefix index or trie
- edge or regional cache
- versioned snapshots

### Consistency

Eventual updates are acceptable.

### Failure policy

Serve last-known-good snapshot if updater fails.

### Abuse

Filter sensitive or malicious terms and apply tenant or locale policy.

---

## 10.22 Drill 19 — File Upload and Processing

### Requirements

- large resumable uploads
- virus scan
- transcoding
- metadata extraction

### Architecture

1. create upload session
2. direct multipart upload to object storage
3. finalize with checksum
4. publish processing command
5. track workflow state

### Invariants

- object content verified before publication
- duplicate finalize is idempotent
- processing retries do not create duplicate visible assets

### Failure questions

- upload completes but finalize response is lost
- scan fails
- processing backlog
- orphan multipart uploads

---

## 10.23 Drill 20 — Multi-Region Object Metadata Service

### Requirements

- object lookup worldwide
- create and delete
- strong uniqueness for object name
- high read ratio

### Design choices

- home-region ownership per namespace
- globally replicated metadata
- read cache

### Delete challenge

Tombstones must replicate before old replicas can resurrect the object.

### Failover

Promotion requires proving metadata log position and fencing old owner.

---

## 10.24 Drill 21 — Distributed Counter

### Requirements

Count views or likes globally.

### Options

- strong central counter
- sharded counter
- CRDT counter
- append events and aggregate

### Trade-off

Exact real-time value costs coordination.

For display counts, approximate or eventually consistent totals may be sufficient.

For quota enforcement, stronger consistency may be required.

---

## 10.25 Drill 22 — API Gateway

### Requirements

- authentication
- routing
- rate limiting
- retries
- observability

### Risks

The gateway can become:

- global bottleneck
- retry amplifier
- policy single point of failure
- high-blast-radius deployment target

### Design

- regional data planes
- cached policy
- bounded retries only for safe operations
- per-tenant quotas
- progressive rollout

---

## 10.26 Drill 23 — Webhook Delivery Platform

### Requirements

Deliver signed events to customer endpoints.

### Data model

```text
subscription
endpoint
secret_version
event_id
attempt
next_attempt_at
status
```

### Reliability

- at-least-once delivery
- stable event ID
- signature and timestamp
- exponential backoff
- customer-specific rate limit
- expiration

### Security

- prevent SSRF
- validate destination
- secret rotation
- replay protection

### Operability

Customer-facing attempt history and manual retry.

---

## 10.27 Drill 24 — Change Data Capture Platform

### Requirements

Stream database changes to consumers.

### Challenges

- snapshot plus incremental log
- schema evolution
- transaction ordering
- restart position
- duplicate records

### Design

- durable source log position
- per-table or shard partitioning
- transaction metadata
- idempotent sinks

### Failure question

How do you prevent gaps between initial snapshot and log streaming?

Use a consistent snapshot tied to a known log position.

---

## 10.28 Drill 25 — Audit Log

### Requirements

- tamper evidence
- ordered per entity or actor
- long retention
- search

### Design

- append-only durable log
- cryptographic hash chaining or signed batches
- immutable storage tier
- derived search index

### Invariant

Audit history must not be silently altered or omitted after acknowledgement.

### Privacy

Minimize sensitive payloads and define retention and legal access.

---

## 10.29 Drill 26 — Leaderboard

### Requirements

- update scores
- query top N
- rank one user

### Options

- sorted index
- partitioned score ranges
- periodic merge
- approximate top-K

### Consistency

Live game ranking may tolerate small delay. Prize settlement may require authoritative finalization.

### Hot key

One global top-N object can become hot; cache and incremental aggregation are needed.

---

## 10.30 Drill 27 — Distributed Build System

### Requirements

- submit build graph
- cache artifacts
- execute tasks
- retry failed workers

### Model

- content-addressed inputs
- task DAG
- deterministic cache key
- lease and attempt ID

### Invariant

An artifact is published only if produced from the exact declared inputs and toolchain.

### Failure questions

- worker completes after lease expiry
- duplicate execution
- corrupted cache artifact

Use fencing or attempt identity for publication.

---

## 10.31 Drill 28 — Deployment Control Plane

### Requirements

- progressive rollout
- health evaluation
- rollback
- multi-region

### Architecture

- authoritative desired state
- regional agents
- versioned rollout plan
- staged cohorts

### Safety

- no global all-at-once deployment by default
- immutable artifact identity
- pause on SLO burn
- last-known-good rollback

### Failure questions

- control plane unavailable
- partial rollout
- stale agent
- rollback artifact unavailable

---

## 10.32 Drill 29 — Secret Distribution

### Requirements

- secure storage
- rotation
- regional access
- audit

### Design

- strongly protected source
- short-lived credentials
- local agent cache
- versioned secret
- revocation and rotation workflow

### Failure policy

Cached secret may preserve availability, but stale credentials may fail after rotation.

Use overlapping validity windows and explicit version telemetry.

---

## 10.33 Drill 30 — Global DNS and Traffic Management

### Requirements

- route users to healthy region
- fail over
- support maintenance

### Challenges

- DNS TTL and resolver caching
- health-check false positives
- regional capacity
- data consistency

### Strong answer

Explain that traffic failover is safe only when destination data and capacity are ready. DNS change alone does not create a valid failover.

---

## 10.34 Deep-Dive Challenge — Banking Ledger

### Invariant

Money is never created or destroyed.

### Model

Use immutable double-entry postings.

```text
debit account A
credit account B
same transaction ID
```

### Architecture

- authoritative ledger
- transactional posting
- idempotency key
- derived balances
- reconciliation

### Partitioning

Cross-account transfers may cross shards.

Options:

- transaction coordinator
- deterministic ordering
- centralized ledger partitions
- durable transfer state machine

### Critical discussion

- acknowledged durability
- duplicate request
- partial failover
- audit and repair
- balance read consistency

A Staff-level answer prioritizes correctness over superficial availability.

---

## 10.35 Deep-Dive Challenge — Ride Dispatch

### Requirements

- match riders and drivers
- low latency
- location updates
- prevent double assignment

### Architecture

- geo-partitioned location stream
- regional candidate index
- dispatch owner per trip
- strongly consistent assignment transition

### Data classes

- driver location: high-volume, eventually consistent
- trip assignment: strongly coordinated

### Failure questions

- two dispatchers assign same driver
- region boundary
- stale location
- driver app offline

The answer should separate soft location freshness from hard ownership assignment.

---

## 10.36 Deep-Dive Challenge — Ticketing for a Major Event

### Requirements

- huge burst
- strict seat uniqueness
- waiting room
- payment timeout

### Architecture

- admission queue
- seat inventory partitioned by event or section
- short reservation lease
- idempotent payment
- final confirmation state machine

### Failure questions

- user disconnect after reservation
- payment succeeds after reservation expiry
- hot event
- bot traffic

### Controls

- rate limiting
- signed queue position
- reservation expiry
- reconciliation with provider

---

## 10.37 Deep-Dive Challenge — Multi-Region SaaS Control Plane

### Requirements

- tenant management
- deployments
- policy
- regional data planes

### Architecture

- globally authoritative control plane
- regional cached desired state
- tenant cells
- asynchronous status stream

### Failure policy

Data plane should remain statically stable if control plane is temporarily unavailable.

### Risks

- stale policy
- global dependency
- configuration corruption
- rollout blast radius

### Staff-level answer

Explain which operations stop during control-plane loss and which continue from last-known-good state.

---

## 10.38 Deep-Dive Challenge — Global Collaboration Document

### Requirements

- concurrent editing
- offline clients
- low latency
- eventual convergence

### Options

- operational transformation
- CRDT
- central ordering service

### Questions

- character versus block granularity
- causal metadata
- tombstones
- cursor presence
- snapshot compaction

### Invariant

All accepted operations converge without losing user edits according to the chosen merge semantics.

---

## 10.39 Deep-Dive Challenge — Fraud Detection Pipeline

### Requirements

- synchronous decision under 100 ms
- asynchronous model updates
- auditability

### Architecture

- online feature store
- rules and model service
- event stream
- offline training pipeline

### Consistency

Features may be slightly stale, but decision input and model version must be recorded for audit.

### Failure policy

Choose fail open, fail closed, or step-up verification by transaction risk.

---

## 10.40 Staff-Level Trade-Off Language

Use precise language.

Instead of:

> This database is highly available.

Say:

> During loss of one zone, a three-zone quorum continues writes. During loss of quorum, writes fail closed to preserve ownership safety.

Instead of:

> The queue gives exactly once.

Say:

> Transport is at least once. Consumers use message IDs and atomic inbox writes, and external payment calls use provider idempotency keys.

Instead of:

> We cache for speed.

Say:

> Product descriptions tolerate five minutes of staleness, so we use cache-aside with jittered TTL and stale-while-revalidate. Checkout revalidates price at the source.

---

## 10.41 Common Interview Failure Modes

### Jumping to tools

Starting with product names before requirements.

### Ignoring invariants

Saying “eventual consistency” without defining conflict behavior.

### Ignoring duplicate execution

Drawing queues without idempotency.

### Ignoring operations

No SLO, reconciliation, or migration plan.

### Overpromising exactly once

Failing to define the guarantee boundary.

### Ignoring skew

Assuming uniform hashing means uniform traffic.

### Ignoring recovery capacity

Sizing steady state but not failover or backlog drain.

---

## 10.42 Rapid Interview Checklist

Before finishing, confirm that you covered:

- business invariant
- scale estimate
- partition key
- source of truth
- consistency model
- acknowledgement boundary
- idempotency
- ordering
- overload control
- failover
- observability
- reconciliation
- trade-offs

---

## 10.43 Self-Scoring Rubric

### Level 1 — Component naming

Lists services, databases, caches, and queues.

### Level 2 — Functional design

Explains normal request path and basic scaling.

### Level 3 — Senior design

Covers consistency, partitioning, failure handling, and SLOs.

### Level 4 — Staff design

Connects business invariants to protocol guarantees, overload controls, migrations, reconciliation, and blast radius.

### Level 5 — Principal design

Frames organizational and evolutionary trade-offs, identifies platform-level abstractions, plans multi-year migration, and explains how the architecture remains governable across teams.

---

## 10.44 Practice Method

For each drill:

1. Spend 5 minutes clarifying.
2. Spend 5 minutes estimating scale.
3. Spend 15 minutes on architecture.
4. Spend 10 minutes on failure modes.
5. Spend 5 minutes on operations and trade-offs.

Record the answer and review:

- Did you state the invariant?
- Did you explain ambiguous outcomes?
- Did you discuss hot keys and overload?
- Did you define recovery proof?

---

## 10.45 Final Staff-Level Summary

A strong distributed-system design answer connects:

```text
business invariant
  -> data and ownership model
  -> consistency and durability
  -> partitioning and normal path
  -> failure and overload behavior
  -> recovery, reconciliation, and observability
```

The goal is not a perfect diagram. The goal is a system whose promises remain understandable when packets disappear, clocks drift, replicas lag, queues grow, clients retry, and ownership changes.
