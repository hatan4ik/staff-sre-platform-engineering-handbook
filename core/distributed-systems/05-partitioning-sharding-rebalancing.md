# Chapter 5 — Partitioning, Sharding, Rebalancing, Hot Keys, and Skew

Partitioning is the act of dividing a logical dataset or workload into smaller ownership units that can be placed, replicated, moved, and operated independently.

At small scale, a database appears to be one thing. At large scale, it becomes a fleet of partitions with separate owners, queues, failure modes, replication lag, capacity limits, and operational histories.

The hard problem is not computing `hash(key) % N`. The hard problem is preserving correctness, availability, and operability while ownership changes under load.

---

## 5.1 Why Systems Partition

A system partitions when one node, process, disk, queue, or leader can no longer satisfy the required:

- storage capacity
- request throughput
- write throughput
- memory working set
- replication bandwidth
- recovery time
- fault isolation
- tenant isolation
- operational blast-radius limits

Partitioning can improve scale and isolation, but it introduces coordination costs.

Before partitioning, a transaction may be local.

After partitioning, the same transaction may become distributed.

Before partitioning, a query may use one index.

After partitioning, the same query may become scatter-gather across hundreds of shards.

Before partitioning, failover may replace one primary.

After partitioning, the system must reason about ownership for every shard.

### Staff-level rule

Do not ask only:

> How will we split the data?

Also ask:

> Which operations become cross-partition, who owns routing truth, how is ownership moved, and what happens while metadata is stale?

---

## 5.2 Partitioning Vocabulary

The following terms are often used inconsistently. A design review should define them explicitly.

### Partition

A logical subset of data or work.

Examples:

- user IDs in a hash range
- timestamps in one day
- customers in one geography
- messages assigned to one stream partition

### Shard

A partition together with the storage and execution resources responsible for it.

A shard may have:

- one leader
- multiple replicas
- a replication log
- its own indexes
- its own backup and restore unit
- a placement record in a control plane

### Replica

A copy of one shard used for durability, availability, read scaling, or recovery.

Partitioning and replication solve different problems:

- partitioning divides ownership
- replication copies ownership state

### Routing layer

The mechanism that maps a request to the shard that owns the key.

This may live in:

- a client library
- a stateless router
- a proxy tier
- a service registry
- a database coordinator
- a control-plane-distributed shard map

### Rebalancing

Moving ownership or replica placement to improve capacity, fault tolerance, or load distribution.

### Resharding

Changing partition boundaries or partition count.

Rebalancing may move an existing shard unchanged. Resharding changes the logical ownership map.

---

## 5.3 Partition-Key Selection

The partition key determines where data lives and which operations remain local.

A good key should normally provide:

- high cardinality
- even distribution
- stable ownership
- locality for common operations
- bounded per-key load
- compatibility with retention and compliance requirements

No partition key optimizes every query.

The design question is therefore:

> Which operations must be cheap, and which operations are allowed to pay cross-shard cost?

### Example: Orders

Possible keys:

- `order_id`
- `customer_id`
- `merchant_id`
- `region_id`
- creation date

Partitioning by `order_id` distributes individual orders well but makes customer-history queries scatter.

Partitioning by `customer_id` keeps one customer's orders local but allows a very large customer to become a hot shard.

Partitioning by time simplifies retention but sends all current writes to the newest partition.

The right answer comes from access patterns and invariants, not only distribution statistics.

### Partition-key review questions

- What is the largest possible value behind one key?
- Can one celebrity, enterprise tenant, or device dominate traffic?
- Does the key preserve transaction locality?
- Does the key create write concentration over time?
- Can the key change later?
- Is the key derivable at routing time?
- Does it reveal sensitive or regulated information?
- How will historical data be queried?

---

## 5.4 Range Partitioning

Range partitioning assigns contiguous key ranges to partitions.

```text
Shard A: 00000000 - 24999999
Shard B: 25000000 - 49999999
Shard C: 50000000 - 74999999
Shard D: 75000000 - 99999999
```

### Advantages

- efficient range scans
- natural ordering
- locality for adjacent keys
- easy time-based retention
- simple partition pruning

### Risks

- sequential keys create a hot latest range
- uneven key density creates skew
- one large tenant can dominate a range
- splitting busy ranges requires careful ownership transfer

### Time partitioning

A common form is time-bucketed partitioning:

```text
2026-07-24
2026-07-25
2026-07-26
```

This is excellent for retention and historical scans but can create a single hot partition for all current writes.

Mitigations include:

- time bucket plus hash suffix
- multiple active write buckets
- regional subdivision
- tenant plus time composite key

Example:

```text
partition = day(event_time) + hash(device_id) % 64
```

This preserves manageable time buckets while spreading current writes.

---

## 5.5 Hash Partitioning

Hash partitioning transforms the key and assigns hash ranges to partitions.

```text
partition = hash(customer_id) % partition_count
```

### Advantages

- usually better load distribution
- avoids concentration from sequential keys
- simple direct routing

### Disadvantages

- poor natural range locality
- changing partition count remaps many keys under naive modulo
- multi-key queries may scatter
- data for related entities may be separated

### The modulo resharding problem

With four partitions:

```text
hash(key) % 4
```

After adding a fifth:

```text
hash(key) % 5
```

Most keys move.

This causes:

- massive data movement
- cache invalidation
- network saturation
- replication pressure
- long rebalancing windows

Naive modulo is acceptable only when partition count is fixed, data is small, or another indirection layer absorbs the change.

---

## 5.6 Consistent Hashing

Consistent hashing maps both nodes and keys onto a logical ring.

```text
        node A
      /        \
 key x          node B
 |                 |
 node D          key y
      \        /
        node C
```

A key is assigned to the next owner clockwise, or according to an equivalent token rule.

When a node joins or leaves, only neighboring token ranges move instead of most keys.

### What consistent hashing does well

- limits remapping during membership changes
- supports incremental scale-out
- decentralizes some routing decisions
- works naturally with replicated token ranges

### What it does not solve

- hot keys
- uneven node capacity
- uneven key popularity
- multi-key transaction locality
- placement across zones and racks
- safe ownership transfer
- stale membership views

Consistent hashing is an assignment mechanism, not a complete sharding architecture.

---

## 5.7 Virtual Nodes and Tokens

Instead of assigning one contiguous range to each physical node, systems often assign many virtual tokens.

```text
Node A owns tokens 3, 17, 51, 88
Node B owns tokens 9, 31, 66, 94
Node C owns tokens 1, 22, 57, 73
```

### Benefits

- smoother load distribution
- easier incremental movement
- support for heterogeneous node capacity
- less impact from one node joining or leaving

### Costs

- larger placement metadata
- more replica relationships
- more streams during recovery
- more complex debugging
- potential for excessive concurrent movement

A node with twice the capacity may receive approximately twice the token ownership, but capacity weighting must consider more than disk size.

Useful dimensions include:

- CPU
- memory
- IOPS
- network bandwidth
- compaction cost
- workload type
- failure-domain placement

---

## 5.8 Directory-Based Sharding

Directory-based sharding uses an explicit map:

```text
customer-1001 -> shard-17
customer-1002 -> shard-04
customer-1003 -> shard-17
```

### Advantages

- arbitrary placement
- easy exception handling
- supports tenant-aware moves
- can isolate high-value or noisy tenants
- enables shard splitting without changing the key

### Risks

- shard-map availability becomes critical
- stale routers may write to old owners
- metadata distribution must be versioned
- control-plane corruption can misroute traffic

### Staff-level requirement

A shard map needs the same rigor as other coordination state:

- linearizable updates where required
- version or epoch numbers
- durable audit history
- safe rollback
- cache invalidation
- fencing of old owners
- explicit behavior when the map is unavailable

The routing system should never rely only on eventual metadata propagation when stale ownership can corrupt data.

---

## 5.9 Composite Partition Keys

Composite keys combine dimensions to balance locality and distribution.

Examples:

```text
tenant_id + hash(user_id)
region_id + customer_id
hour_bucket + hash(device_id) % 128
merchant_id + order_id
```

### Benefits

- preserves partial locality
- isolates tenants or regions
- reduces current-time hotspots
- enables targeted retention

### Risks

- the leading component may still dominate
- queries missing the routing prefix may scatter
- repartitioning one dimension can be difficult
- key format may become an accidental long-term API

Composite keys should be designed with routing, indexing, retention, and transaction locality together.

---

## 5.10 Hot Partitions and Hot Keys

A partition is hot when its resource demand is materially higher than peers.

A hot key is one logical key whose demand dominates the partition that owns it.

These are different problems.

### Hot partition causes

- uneven key distribution
- sequential write concentration
- one oversized tenant
- one popular product
- time-windowed traffic
- poor token assignment
- imbalanced replica reads
- compaction or repair on one shard

### Hot key causes

- celebrity account
- viral content
- globally shared counter
- leader-election metadata
- popular cache object
- one high-volume IoT device fleet identifier

Adding more shards does not fix a single indivisible hot key.

### Detection

Monitor per-shard and per-key dimensions:

- requests per second
- bytes per second
- CPU
- queue depth
- p50, p95, and p99 latency
- read and write amplification
- compaction debt
- cache hit rate
- replica lag
- throttled operations
- active connections

Fleet averages hide skew.

A cluster at 40% average CPU may still have one shard at 100% and failing.

---

## 5.11 Hot-Key Mitigation

Possible strategies depend on semantics.

### Read hot keys

- replicate cache entries
- use CDN or edge caching
- request coalescing
- stale-while-revalidate
- local read replicas
- hierarchical caches
- negative caching where appropriate

### Write hot keys

- split the logical value into subkeys
- use sharded counters
- append events and aggregate asynchronously
- allocate regional or tenant-local buckets
- serialize through a dedicated owner with explicit capacity
- batch updates
- enforce rate limits

### Sharded counter example

Instead of one key:

```text
likes:video-42 = 9,813,442
```

Use multiple buckets:

```text
likes:video-42:0
likes:video-42:1
...
likes:video-42:127
```

Writers select a bucket. Readers sum buckets or consume a materialized aggregate.

Trade-offs:

- writes scale better
- exact reads become more expensive
- aggregation may lag
- reset and deletion semantics become harder

The business must decide whether exact real-time totals are required.

---

## 5.12 Tenant-Aware Sharding

Multi-tenant systems often need stronger isolation than uniform hashing provides.

A tenant-aware model can place tenants according to:

- size
- compliance region
- support tier
- workload profile
- noisy-neighbor risk
- encryption boundary
- backup requirements

### Common pattern

Small tenants share pooled shards.

Large tenants receive dedicated shards.

```text
small tenants -> shared pool
large tenant A -> dedicated shard group
large tenant B -> dedicated shard group
```

This is sometimes called cell-based, pod-based, or stamp-based isolation depending on architecture.

### Benefits

- bounded blast radius
- easier tenant migration
- targeted scaling
- clearer cost attribution
- dedicated maintenance windows

### Risks

- capacity fragmentation
- control-plane complexity
- migration tooling becomes mandatory
- dedicated tenants may still outgrow one shard

A mature design treats tenant placement as a lifecycle, not a one-time hash decision.

---

## 5.13 Scatter-Gather Queries

A scatter-gather query sends work to multiple shards and combines the results.

```text
coordinator
  +--> shard A
  +--> shard B
  +--> shard C
  +--> shard D
       |
       v
merge and return
```

Examples:

- global search
- top-N across customers
- analytics aggregation
- lookup without the partition key

### Tail-latency problem

The coordinator is often limited by the slowest required shard.

If a query touches 100 shards, even a low per-shard failure probability can become a high query-level failure probability.

### Required policies

- per-shard deadline
- global deadline
- maximum fan-out
- concurrency cap
- partial-result behavior
- retry policy
- duplicate suppression
- merge memory limit
- cancellation propagation

### Staff-level question

Can the query be redesigned to avoid fan-out?

Alternatives include:

- secondary index service
- denormalized lookup table
- search engine
- precomputed materialized view
- routing directory
- changed API that requires a partition key

Scatter-gather is sometimes necessary, but it should not be the accidental default.

---

## 5.14 Cross-Shard Transactions

Partitioning creates a transaction-locality tax.

A transaction touching one shard can use local ACID semantics.

A transaction touching multiple shards may require:

- two-phase commit
- consensus-backed transaction coordinator
- deterministic transaction ordering
- saga workflow
- escrow allocation
- compensation
- asynchronous reconciliation

### Example: Account transfer

If both accounts live on one shard:

```text
BEGIN
  debit account A
  credit account B
COMMIT
```

If they live on different shards, the system must preserve the invariant that money is neither lost nor created across partial failure.

Possible approaches:

- co-locate accounts likely to transact
- use a durable transfer state machine
- reserve on one side before committing the other
- use a transactional database that supports cross-shard commit
- maintain an immutable ledger and reconcile balances

### Design principle

Partition boundaries should align with the most important atomicity boundaries whenever possible.

Changing the partition key can be cheaper than implementing correct distributed transactions for every request.

---

## 5.15 Secondary Indexes in a Sharded System

A local secondary index exists only inside one shard.

A global secondary index spans shard ownership.

### Local index

```text
partition key: customer_id
index: order_status
```

Querying orders by status for one customer is local.

Querying all pending orders globally requires fan-out.

### Global index

A separate index maps:

```text
status=pending -> order references across shards
```

This introduces a dual-write problem.

The index may be:

- synchronously updated in the transaction
- asynchronously maintained by change data capture
- rebuilt from source data

### Required decisions

- Is the index authoritative or derived?
- How stale may it be?
- How are deletes represented?
- How is drift detected?
- Can queries verify results against the source shard?
- How is the index rebuilt?

Treating a derived index as authoritative without reconciliation creates silent correctness failures.

---

## 5.16 Rebalancing Goals

Rebalancing should optimize multiple dimensions:

- storage utilization
- CPU utilization
- request rate
- write rate
- network load
- replica placement
- failure-domain diversity
- recovery headroom

Equal bytes do not imply equal load.

A 500 GB cold shard may be cheaper than a 20 GB hot shard.

### Rebalancing triggers

- node addition
- node removal
- skew threshold exceeded
- rack or zone evacuation
- tenant growth
- disk nearing capacity
- shard split or merge
- hardware class change

### Control-loop model

```text
observe placement and load
        |
        v
compute desired placement
        |
        v
plan bounded movement
        |
        v
copy, catch up, switch ownership
        |
        v
verify and clean up
```

The movement planner must be conservative. An aggressive balancer can create a self-inflicted outage.

---

## 5.17 Safe Ownership Transfer

A safe shard move usually has phases.

### Phase 1 — Plan

- choose source and destination
- verify destination capacity
- assign a new movement or ownership epoch
- record the desired state durably

### Phase 2 — Copy

- transfer a snapshot
- stream ongoing changes
- verify checksums or positions
- limit bandwidth and concurrency

### Phase 3 — Catch up

- reduce replication lag
- confirm destination has required log position
- ensure indexes and metadata are ready

### Phase 4 — Cut over

- fence the old owner for new writes
- atomically update routing ownership
- activate the destination
- propagate the new map

### Phase 5 — Drain and clean up

- complete in-flight reads where safe
- retain old copy for rollback window
- verify no stale writers remain
- remove source data only after proof

### Critical invariant

At most one owner may accept authoritative writes for a shard epoch.

A stale router may still contact the old node. The old node must reject the write based on ownership epoch, not merely trust routing correctness.

---

## 5.18 Dual Reads and Dual Writes During Migration

Migration strategies sometimes use temporary dual behavior.

### Dual reads

Read destination first, then source on miss.

Risks:

- inconsistent versions
- hidden migration gaps
- doubled load
- ambiguous source of truth

### Dual writes

Write to source and destination.

Risks:

- one write succeeds and the other fails
- ordering differs
- retries duplicate one side
- schemas diverge

Blind dual writes create a distributed transaction problem.

Safer alternatives include:

- one authoritative writer plus change capture
- transactional outbox to a migration stream
- ordered log replay
- destination shadow validation

### Shadow reads

Serve from the source, read the destination in the background, and compare results.

This can validate correctness without exposing users to destination errors.

---

## 5.19 Online Shard Splitting

Suppose shard `S` owns key range `A-Z` and must split.

```text
Before:
S = A-Z

After:
S1 = A-M
S2 = N-Z
```

A safe split requires:

- versioned boundaries
- deterministic routing during transition
- snapshot plus change replay
- fencing old ownership
- atomic activation of new ranges
- rollback plan

### Transition model

```text
epoch 41: S owns A-Z
epoch 42: S1 owns A-M, S2 owns N-Z
```

Requests carrying epoch 41 should not be allowed to create authoritative writes after epoch 42 is active.

### Split triggers

- storage threshold
- throughput threshold
- latency threshold
- key-count threshold
- tenant isolation requirement

Automatic splitting needs hysteresis. Otherwise, noisy measurements can cause split and merge oscillation.

---

## 5.20 Shard Merging

Too many small shards create overhead:

- metadata size
- open files
- connection pools
- replication streams
- compactions
- background tasks
- operational noise

Merging cold adjacent shards can reduce overhead.

The merge must preserve:

- key coverage without overlap or gaps
- replica durability
- routing atomicity
- tombstones and version history
- backup and restore semantics

Merging is not merely concatenating files. It is an ownership transition.

---

## 5.21 Capacity Headroom

A cluster at 80% utilization may be unable to survive one node or zone failure.

Capacity planning must reserve room for:

- failover
- re-replication
- repair
- compaction
- rebalancing
- traffic bursts
- deployment overlap

### Example

A 10-node cluster runs at 70% steady disk usage.

Losing one node redistributes its data across nine nodes.

If repair temporarily duplicates data and increases compaction, the remaining nodes may exceed safe capacity.

The correct metric is not only steady-state utilization. It is utilization during the largest credible recovery event.

### Staff-level review

Ask:

- Can one zone fail without emergency scaling?
- Can recovery complete before another failure?
- What bandwidth is reserved for repair?
- Does rebalancing compete with foreground traffic?
- Is autoscaling fast enough for stateful movement?

---

## 5.22 Rebalancing Throttles

Movement consumes the same resources needed for production traffic.

Throttle dimensions may include:

- bytes per second
- concurrent shard moves
- moves per source node
- moves per destination node
- compactions per node
- cross-zone transfer rate
- CPU budget
- disk queue depth

### Adaptive movement

A balancer can slow or pause when:

- p99 latency rises
- replica lag grows
- disk queue depth exceeds threshold
- error rate increases
- foreground throughput approaches capacity

The goal is not maximum movement speed. The goal is minimum risk while meeting a recovery deadline.

---

## 5.23 Skew Metrics

Skew should be measured explicitly.

Useful statistics include:

```text
max / median
p99 / median
coefficient of variation
Gini coefficient
largest-tenant share
largest-key share
```

Examples:

- maximum QPS is 9x median
- largest tenant owns 18% of one shard
- p99 shard latency is 4x fleet median
- top 0.1% of keys produce 60% of writes

Averages hide the problem.

### Heat maps

Shard-by-time heat maps reveal:

- periodic tenant jobs
- time-zone-driven peaks
- repair storms
- one overloaded replica
- progressive imbalance

Observability must retain shard identity, ownership epoch, node, zone, and tenant dimensions where cardinality permits.

---

## 5.24 Metadata and Routing Failure Modes

The data plane may be healthy while the routing control plane is wrong.

Failure modes include:

- stale shard map
- partially applied map update
- router cache not invalidated
- split ownership
- missing range
- overlapping range
- corrupted metadata
- destination activated before data catch-up

### Defensive mechanisms

- map version on every request
- ownership epoch validation at the shard
- checksum or invariant validation for full keyspace coverage
- atomic metadata updates
- immutable change history
- safe-mode behavior on ambiguity
- periodic reconciliation between desired and actual placement

### Coverage invariant

For a range-partitioned keyspace:

- every key belongs to exactly one active owner
- no active ownership gaps exist
- no active ownership overlaps exist

This invariant should be machine-checked continuously.

---

## 5.25 Shard-Aware APIs

Applications should expose enough routing context to avoid accidental scatter.

Examples:

- require tenant ID
- require region ID
- include account ID in resource paths
- propagate partition key in events
- preserve routing key across retries

Bad API:

```text
GET /orders?email=user@example.com
```

If email is not a routing key, the service may query every shard.

Better options:

```text
GET /customers/{customer_id}/orders
```

or use a dedicated lookup index to resolve email to customer ID first.

The API contract influences the physical scalability of the system.

---

## 5.26 Queue and Stream Partitioning

Partitioning applies to work, not only storage.

A stream partition usually provides ordering only within that partition.

Choosing a message key determines:

- ordering scope
- consumer parallelism
- hot-partition risk
- replay locality

### Example

Keying all order events by `customer_id` preserves per-customer order but limits one large customer's parallelism.

Keying by `order_id` scales better but loses ordering across a customer's orders.

### Poisoned partition

One slow or repeatedly failing message can block a partition when strict ordering is required.

Policies may include:

- bounded retries
- dead-letter handling
- parking-lot queue
- skip with audit and later reconciliation
- split workload into independent subkeys

Ordering guarantees create backpressure boundaries.

---

## 5.27 Cell-Based Architecture

A cell is a bounded deployment unit containing the services and data needed to serve a subset of traffic.

```text
Global control plane
   |
   +--> Cell A: app + cache + database shards
   +--> Cell B: app + cache + database shards
   +--> Cell C: app + cache + database shards
```

### Benefits

- smaller blast radius
- predictable scale unit
- tenant placement control
- simpler failure isolation
- safer incremental deployment

### Costs

- duplicated infrastructure
- placement control plane
- cross-cell operations
- uneven cell growth
- migration tooling

Cells are often preferable when operational isolation matters more than perfect resource pooling.

### Global services risk

A supposedly cell-isolated architecture may still depend on one global:

- identity system
- DNS service
- configuration store
- deployment pipeline
- billing service
- certificate authority

Staff engineers identify and bound these shared dependencies.

---

## 5.28 Incident: Sequential-Key Hotspot

### Scenario

A distributed database partitions by ordered event ID. New IDs always increase. All current writes land on the highest range.

### Symptoms

- one shard at 100% CPU
- rising write latency
- healthy average cluster utilization
- frequent split of the latest shard
- network and compaction pressure on one node group

### Immediate mitigation

- rate-limit producers
- increase active write buckets
- move hot replicas to stronger nodes
- pause noncritical compaction or batch work where safe

### Long-term correction

Use a key such as:

```text
hour_bucket + hash(device_id) % 128
```

or another design that preserves retention while spreading writes.

### Interview lesson

Even key distribution can be uneven over time. Evaluate traffic distribution, not only key-count distribution.

---

## 5.29 Incident: Rebalancer Causes Outage

### Scenario

A node is added to a busy cluster. The balancer starts hundreds of shard transfers simultaneously.

### Failure chain

```text
new node joins
  -> aggressive movement
  -> source disks saturate
  -> replica lag grows
  -> foreground latency rises
  -> clients retry
  -> load increases
  -> cluster-wide timeout storm
```

### Immediate response

- pause or reduce movement
- disable duplicate retry layers
- protect foreground concurrency
- verify replica durability before canceling transfers

### Prevention

- per-node movement limits
- adaptive throttling
- retry budgets
- recovery SLO
- canary movement before fleet-wide action
- load-aware placement rather than byte-only balancing

### Interview lesson

Control-plane automation is production traffic. It requires budgets, observability, and rollback.

---

## 5.30 Incident: Stale Router Writes to Old Owner

### Scenario

Shard 42 moves from Node A to Node B. One application instance retains an old shard map and continues writing to Node A.

### Unsafe system

Node A accepts the writes because it still has the data files.

Now two divergent histories exist.

### Safe system

The move increments ownership epoch from 91 to 92.

Node A rejects writes for epoch 92 because it is no longer owner.

Node B accepts epoch 92.

The stale router refreshes its map and retries.

### Lesson

Routing correctness is not enough. Resource-side fencing is required whenever stale clients can reach old owners.

---

## 5.31 Incident: Oversized Tenant Breaks Uniform Hashing

### Scenario

One tenant produces 35% of all traffic. Hashing by tenant ID places all of its workload on one shard.

### Options

- sub-shard the tenant by user or object ID
- dedicate a shard group
- place tenant in a separate cell
- split reads and writes differently
- enforce tenant-level rate or concurrency limits

### Migration concern

Changing the tenant's partition scheme requires a versioned routing rule.

Example:

```text
tenant A routing version 1 -> shard 17
tenant A routing version 2 -> hash(subkey) across shards 44-51
```

Old and new event producers must not disagree silently about the routing version.

---

## 5.32 Incident: Cross-Shard Query Meltdown

### Scenario

A new dashboard endpoint executes a top-N query across every shard once per page refresh.

### Failure chain

```text
1000 users refresh
  x 200 shards
  = 200,000 shard requests
```

The coordinator exhausts connections and the shards experience queue growth.

### Better design

- precompute top-N continuously
- materialize per-region aggregates
- cache the result
- apply refresh coalescing
- bound query fan-out

### Lesson

One logical request can produce enormous physical work. Measure fan-out amplification explicitly.

---

## 5.33 Design Review Checklist

Before approving a partitioned architecture, ask:

- What is the partition key?
- Which business transactions remain local?
- Which queries scatter?
- What is the largest tenant or key?
- How is skew measured?
- How are hot keys mitigated?
- Where does the shard map live?
- How is routing metadata versioned?
- Can stale routers reach old owners?
- What fencing mechanism rejects stale writes?
- How does a shard move from one owner to another?
- What is the rollback point during movement?
- How is data completeness verified?
- How much recovery headroom exists?
- What throttles protect foreground traffic?
- How are secondary indexes maintained?
- What is the cross-shard transaction model?
- Can one zone fail without emergency resharding?
- How are oversized tenants isolated?
- What is the maximum permitted fan-out?
- How are shard backups and restores performed?
- Can operators identify every key's current owner and epoch?

---

## 5.34 Staff and Principal Interview Drills

### Question 1

A system uses `hash(user_id) % 64`. You need to expand to 96 partitions. What goes wrong, and what migration strategies are available?

A strong answer should discuss:

- widespread remapping under modulo
- indirection through fixed logical buckets
- consistent hashing or directory mapping
- staged ownership transfer
- dual-read or log-replay risks
- fencing and rollback

### Question 2

The cluster is 45% utilized on average, but p99 latency is high. How do you investigate partition skew?

Expected direction:

- per-shard CPU, queue, latency, and traffic
- max-to-median ratios
- top keys and tenants
- replica placement
- background repair and compaction
- time-based heat maps

### Question 3

How do you move a writable shard without downtime?

Expected direction:

- snapshot and incremental change stream
- ownership epoch
- catch-up proof
- atomic cutover
- old-owner fencing
- rollback window
- verification and cleanup

### Question 4

Why does consistent hashing not solve hot keys?

Expected direction:

- it distributes keys, not request popularity
- one indivisible key still has one ownership path
- replication, caching, sub-sharding, or aggregation may be required

### Question 5

A transfer workflow frequently touches accounts on different shards. What architecture changes would you consider?

Expected direction:

- co-location by transaction domain
- durable ledger
- transaction coordinator
- saga or reservation model
- invariant and compensation analysis

### Question 6

When would you choose range partitioning over hash partitioning?

Expected direction:

- ordered scans and retention
- locality requirements
- willingness to manage write hotspots and splits

### Question 7

How would you isolate one enterprise tenant that is 100 times larger than average?

Expected direction:

- dedicated shard group or cell
- tenant-aware routing
- migration versioning
- independent capacity and SLO
- cost and operational trade-offs

### Question 8

What can go wrong with an automatic rebalancer?

Expected direction:

- resource contention
- movement storms
- oscillation
- wrong load model
- reduced fault tolerance during transition
- need for throttles, hysteresis, canaries, and rollback

---

## 5.35 Hands-On Labs

### Lab 1 — Measure Modulo Remapping

1. Generate one million keys.
2. Map them using `hash(key) % 16`.
3. Change the divisor to 17.
4. Measure the percentage of keys that move.
5. Compare with consistent hashing and fixed logical buckets.

### Lab 2 — Create a Hot Key

1. Start a partitioned cache or database.
2. Generate uniform traffic.
3. Send 40% of requests to one key.
4. Compare fleet averages with per-shard metrics.
5. Apply request coalescing or sub-sharding.

### Lab 3 — Build a Versioned Shard Map

Implement a small router with:

- key-range ownership
- map version
- ownership epoch
- refresh on stale-epoch rejection

Demonstrate that an old router cannot write to the former owner.

### Lab 4 — Simulate Online Shard Movement

1. Copy a snapshot from source to destination.
2. Stream incremental writes.
3. wait for destination catch-up.
4. increment the ownership epoch.
5. switch routing.
6. verify that the source rejects new writes.

### Lab 5 — Scatter-Gather Amplification

1. Build an endpoint that fans out to 100 mock shards.
2. Add random tail latency and failures.
3. Measure end-to-end p99.
4. add concurrency limits and deadlines.
5. compare with a precomputed aggregate.

### Lab 6 — Rebalancer Safety

Create a simulator where nodes have different:

- bytes
- QPS
- CPU
- zone

Compare byte-only balancing with multi-dimensional placement. Add movement throttles and failure-domain constraints.

### Lab 7 — Cross-Shard Transfer State Machine

Implement states such as:

```text
CREATED
DEBIT_RESERVED
CREDIT_APPLIED
COMPLETED
COMPENSATING
FAILED
```

Inject crashes after every transition and verify that retries preserve the accounting invariant.

---

## 5.36 Staff-Level Summary

Partitioning is not merely a distribution formula. It is a system of ownership.

A production-grade design must make ownership:

- explicit
- versioned
- observable
- movable
- fenced
- recoverable

The strongest partitioning answers connect five concerns:

```text
partition key
  -> transaction locality
  -> load distribution
  -> ownership metadata
  -> safe movement
  -> operational recovery
```

A Staff or Principal engineer should be able to explain not only where a key lives today, but how the system proves who may write it during failure, migration, and stale-routing conditions.
