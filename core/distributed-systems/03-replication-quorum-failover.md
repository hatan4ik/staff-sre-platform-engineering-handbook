# Chapter 3 — Replication, Quorums, Leader-Based Systems, and Failover

Replication is the act of maintaining copies of data on multiple nodes. It is used for availability, durability, read scaling, geographic locality, disaster recovery, and operational maintenance.

Replication does not automatically provide correctness.

A system can have three replicas and still lose acknowledged writes. It can have a quorum and still return stale data. It can fail over successfully and still create split brain. It can replicate every byte and still violate the business invariant because the application acknowledged the wrong point in the protocol.

The Staff/Principal-level question is therefore not:

> How many replicas do we have?

It is:

> What exact guarantee is provided at the moment the system returns success, and how does that guarantee change during lag, partition, failover, repair, or operator error?

---

## 3.1 Start With the Promise Made to the Caller

Suppose a client writes an order and receives HTTP 200.

That response may mean very different things:

1. The primary stored the write in memory.
2. The primary appended the write to a local log.
3. The primary flushed the write to local durable storage.
4. One replica received the write in memory.
5. One replica durably persisted the write.
6. A majority durably persisted the write.
7. A remote region durably persisted the write.
8. The write became visible to all linearizable reads.
9. The write was applied to every replica.

All of these are plausible acknowledgement policies.

Only some survive process failure. Fewer survive host failure. Fewer still survive zone or region loss.

### Staff-level rule

Every write path must define:

- the authoritative commit point
- the acknowledgement policy
- the durability scope
- the visibility rule
- the failover recovery point
- the maximum accepted data loss

Do not use the word “replicated” as a substitute for these definitions.

---

## 3.2 Why Replicate?

Replication serves several goals, and those goals can conflict.

### Availability

If one node fails, another can continue serving.

### Durability

If one storage device or failure domain is lost, another copy remains.

### Read scale

Read-only traffic can be distributed across replicas.

### Geographic latency

Users can read from a nearby replica rather than crossing an ocean.

### Disaster recovery

A second region can preserve recoverable state after regional loss.

### Maintenance

Nodes can be upgraded, rebooted, or replaced without a full outage.

### The conflict

The replication design that minimizes write latency is often not the design that maximizes durability or read freshness.

For example:

- asynchronous remote replication lowers latency but permits acknowledged-write loss after regional failure
- synchronous remote replication improves durability but adds network latency and can reduce availability
- local replicas improve failover but do not protect against region-wide loss
- many read replicas increase read capacity but increase lag-management complexity

A design review must state which goal dominates for each data class.

---

## 3.3 The Replication Pipeline

A generic replicated write path contains several stages:

```text
client
  |
  v
coordinator or leader receives write
  |
  +--> validate request
  +--> assign version, term, or log position
  +--> append locally
  +--> send to replicas
  +--> wait for acknowledgement policy
  +--> mark committed
  +--> apply to state machine or table
  +--> return success
```

The order differs by system, but the questions are universal.

For each stage, ask:

- Is the data only in memory or on durable storage?
- Can the node acknowledge before local flush?
- Can replicas acknowledge before flush?
- Can a later leader discard this entry?
- Is “replicated” different from “committed”?
- Can a read observe the entry before commit?
- What happens if the leader crashes between acknowledgement and replication?

The difference between received, persisted, committed, and applied is central.

### Received

The node has obtained the write, possibly only in volatile memory.

### Persisted

The node has stored the write in durable local storage according to its configured durability semantics.

### Committed

The system has accepted the write as part of the authoritative history under its protocol.

### Applied

The committed operation has been executed against the local state machine, table, or materialized view.

These states should not be treated as synonyms.

---

## 3.4 Synchronous and Asynchronous Replication

### Synchronous replication

The coordinator waits for one or more replicas before returning success.

```text
client -> leader -> replica
          |          |
          |<-- ACK --|
          |
          +--> success to client
```

Advantages:

- stronger durability at acknowledgement
- smaller recovery point objective
- lower probability of acknowledged-write loss

Costs:

- write latency includes replica latency
- slow replicas can reduce throughput
- failure of required replicas can reduce availability
- cross-region synchronization can be expensive

### Asynchronous replication

The coordinator returns before replicas confirm the write.

```text
client -> leader -> success
                  
leader ----------> replica later
```

Advantages:

- lower write latency
- higher write availability when replicas are slow or unreachable
- simpler use of distant replicas

Costs:

- replica lag
- stale reads
- potential loss of acknowledged writes after leader failure
- more complex failover and reconciliation

### Semi-synchronous replication

Some systems wait for limited evidence from another node, such as receipt by one replica, but not necessarily durable application.

This may improve resilience without paying the full cost of strict synchronous replication.

The exact guarantee depends on what the replica acknowledgement means.

### Staff-level interview answer

Do not say only:

> Synchronous replication is safer but slower.

Say:

> I need to define whether replicas acknowledge receipt, durable append, or application; how many failure domains must acknowledge; and whether the returned write is guaranteed to survive leader, host, zone, or region loss.

---

## 3.5 Leader-Based Replication

In a single-leader design, one node orders writes for a partition or dataset.

```text
             writes
clients ----------------> leader
                           |
                  replication stream
                    /             \
                   v               v
              follower A      follower B
```

Reads may be served by:

- the leader only
- followers with possible staleness
- followers that have reached a required log position
- a lease-holding replica
- any replica using version validation

### Benefits

- one ordering authority
- easier conflict prevention
- straightforward transaction support on the leader
- simpler write semantics than multi-leader designs

### Risks

- leader bottleneck
- failover pause
- stale followers
- split brain during unsafe promotion
- acknowledged-write loss under asynchronous replication
- hot partitions when one leader owns too much traffic

### Log position

Leader-based systems commonly track a monotonically increasing position:

- log sequence number
- binlog position
- replication offset
- term and index
- write-ahead log location

A replica’s position is stronger evidence than a wall-clock timestamp.

It allows the system to answer:

- Has this replica received my write?
- Is it safe to serve a read requiring position X?
- Which candidate is most up to date during failover?
- How far behind is the replica?

---

## 3.6 Replication Lag

Replication lag is the distance between authoritative committed state and replica state.

Lag can be measured in several ways:

- elapsed wall-clock time
- bytes behind
- log entries behind
- transaction IDs behind
- commit timestamp difference
- unapplied event count

Each measurement has limitations.

### Why time-based lag can mislead

A replica may appear only one second behind but be millions of writes behind during a burst.

A quiet system may be many log positions behind while representing little business impact.

Clock skew can distort timestamp-based lag.

### Why byte-based lag can mislead

A small number of large transactions may produce many bytes.

A large number of small but critical transactions may produce few bytes.

### Operationally useful signals

Track at least:

- receive position
- durable position
- apply position
- leader commit position
- replay rate
- estimated catch-up time
- oldest unapplied transaction age
- replica read error or stale-read rate

### Common causes of lag

- insufficient network throughput
- storage latency on replicas
- long-running transactions
- single-threaded apply bottlenecks
- schema changes
- large batch writes
- lock contention on apply
- replica CPU saturation
- network retransmissions
- throttling
- backup activity

### Backlog growth rule

If incoming replication work exceeds apply capacity, lag grows without bound.

```text
incoming replication rate > apply rate
                |
                v
            backlog grows
```

Failover is unsafe or slow when the best candidate is far behind.

---

## 3.7 Read Scaling and Staleness Policies

Sending reads to followers is not a free optimization.

It changes the consistency model observed by clients.

### Stale-read example

```text
1. client writes profile to leader
2. write succeeds
3. client reads from lagging follower
4. old profile is returned
```

The database may be healthy. The architecture is still wrong if the product promised immediate read-your-writes behavior.

### Possible policies

#### Leader reads

Route consistency-sensitive reads to the leader.

Advantages:

- simple semantics
- latest committed state

Costs:

- leader load
- cross-region latency

#### Session stickiness

After a write, keep the client on the same authoritative path for a period.

Advantages:

- easy read-your-writes improvement

Risks:

- time-based stickiness may expire before lag clears
- failover complicates routing

#### Position token

Return a commit position with the write. A later read requires a replica that has reached at least that position.

```text
write response: commit_position = 98124
read request: require_position >= 98124
```

Advantages:

- explicit correctness
- avoids guessing with sleep windows

Costs:

- routing complexity
- possible wait or leader fallback

#### Bounded staleness

Allow reads only when the replica is within a defined lag threshold.

Thresholds may be:

- time based
- version based
- log-distance based
- domain specific

#### Monotonic session reads

A client carries the highest observed version. It must never be routed to a replica behind that version.

### Staff-level rule

Staleness must be a product and API decision, not an accidental consequence of a load balancer distributing reads.

---

## 3.8 Failover Is a Data-Safety Protocol

Failover is often described as:

> Detect that the leader is down and promote a follower.

That description omits the hardest part.

The real problem is:

> Prove that the old leader can no longer accept authoritative writes, select a sufficiently up-to-date successor, establish a new epoch, and prevent stale actors from continuing to mutate shared state.

A safe failover process must address:

1. failure detection
2. quorum or external authority
3. candidate freshness
4. promotion
5. client rerouting
6. fencing of the old leader
7. reintegration of recovered nodes
8. recovery of divergent or missing writes

### Failure detection is suspicion

A timeout does not prove death.

The old leader may be:

- paused
- partitioned
- overloaded
- isolated only from the monitor
- alive and still reachable by some clients

Promoting a new leader without fencing the old one can create split brain.

---

## 3.9 Recovery Point Objective and Recovery Time Objective

### Recovery Point Objective — RPO

How much committed or acknowledged data may be lost after a disaster?

Examples:

- RPO 0: no acknowledged data loss is acceptable under the defined failure model
- RPO 30 seconds: up to 30 seconds of data may be lost
- RPO 5 minutes: asynchronous disaster-recovery copies may lag by five minutes

### Recovery Time Objective — RTO

How long may service remain unavailable before recovery?

Examples:

- RTO 30 seconds
- RTO 15 minutes
- RTO 4 hours

### Trade-off

Low RPO and low RTO usually require:

- more synchronous coordination
- more independent infrastructure
- tested automation
- better failure detection
- more operational complexity
- higher cost

### The hidden contradiction

A design may claim:

- asynchronous cross-region replication
- automatic immediate failover
- zero data loss

These claims are incompatible unless another mechanism closes the durability gap.

Staff engineers challenge contradictory guarantees before production does.

---

## 3.10 Quorum Basics

Leaderless and some replicated systems describe replication with:

- `N`: number of replicas
- `W`: number of replicas that must acknowledge a write
- `R`: number of replicas consulted for a read

A common rule is:

```text
R + W > N
```

This ensures that the read set and write set overlap in at least one replica.

Example:

```text
N = 3
W = 2
R = 2

R + W = 4 > 3
```

At least one node in the read quorum should have participated in the write quorum.

### Why overlap helps

Suppose replicas are A, B, and C.

A write succeeds on A and B.

A read consults B and C.

The read overlaps the successful write at B.

The coordinator can compare versions and choose or reconcile the newest value.

### Quorum is not magic

`R + W > N` does not by itself guarantee linearizability.

Correctness also depends on:

- version assignment
- concurrent-write handling
- conflict resolution
- coordinator behavior
- whether quorums are drawn from the same replica set
- whether failed nodes are temporarily substituted
- read repair correctness
- clock assumptions
- durable versus in-memory acknowledgements

### Durable quorum versus receipt quorum

If `W=2` but both replicas acknowledge only volatile memory, power loss may erase both copies.

The formula says nothing about local durability semantics.

---

## 3.11 Choosing N, R, and W

### `N=3, W=2, R=2`

Typical balanced quorum.

Properties:

- tolerates one unavailable replica for many operations
- read and write quorums overlap
- moderate read and write cost

### `N=3, W=3, R=1`

Write-all, read-one.

Properties:

- fast reads
- expensive writes
- one unavailable replica can block writes
- a read can be fresh only if write completion truly reached all replicas and no topology substitution occurred

### `N=3, W=1, R=3`

Write-one, read-all.

Properties:

- low write latency
- high read cost
- acknowledged writes may be fragile
- read availability suffers when any replica is unavailable

### `N=5, W=3, R=3`

Larger quorum.

Properties:

- tolerates more failures
- higher network and storage cost
- potentially better geographic distribution
- slower tail latency because more acknowledgements are required

### Tail-latency effect

A quorum operation waits for enough responses, not necessarily all responses.

The required order statistic matters.

For `W=2` across three replicas, latency is approximately determined by the second-fastest qualifying acknowledgement, plus coordinator work.

Increasing quorum size can improve safety while exposing more tail latency.

---

## 3.12 Leaderless Replication

In a leaderless design, clients or coordinators may write to multiple replicas directly.

```text
             coordinator
             /    |    \
            v     v     v
           A      B      C
```

A write succeeds after `W` acknowledgements.

A read consults `R` replicas and reconciles versions.

### Benefits

- no single write leader
- continued operation during some node failures
- potentially lower regional write latency
- natural distribution across replicas

### Challenges

- concurrent writes
- conflict resolution
- stale replicas
- repair traffic
- tombstone handling
- membership changes
- hotspot coordination
- difficult transaction semantics across keys

### Versioned values

Replicas may store:

```text
key: cart-91
value: {...}
version: v42
```

A read coordinator compares versions from replicas.

If one version dominates, it is returned.

If versions are concurrent, the system must:

- preserve siblings
- merge automatically
- apply last-write-wins
- invoke application reconciliation
- reject the update

The merge policy is part of the data model.

---

## 3.13 Concurrent Writes and Conflict Resolution

Two coordinators may accept writes concurrently:

```text
client A -> replica set: cart = {book}
client B -> replica set: cart = {camera}
```

Without a single ordering authority, neither write necessarily happened after the other.

### Last-write-wins

Choose the value with the greatest timestamp or version according to a deterministic rule.

Advantages:

- simple
- convergent
- low metadata overhead

Risks:

- silently discards valid concurrent updates
- physical clocks can skew
- “last” may be an artifact of network timing

Last-write-wins is acceptable only when lost concurrent updates are acceptable or impossible by domain design.

### Vector clocks or version vectors

Track causal history by replica or actor.

Conceptually:

```text
A: {A: 3, B: 1}
B: {A: 2, B: 2}
```

Neither version dominates the other, so they are concurrent.

Advantages:

- detects concurrency
- preserves causality better than wall-clock timestamps

Costs:

- metadata growth
- compaction complexity
- application reconciliation

### Application merge

The domain may define a meaningful merge.

Examples:

- union of shopping-cart items
- maximum observed counter
- set addition with tombstones
- field-level merge where ownership is independent

### CRDT-style convergence

Conflict-free replicated data types encode merge operations that are associative, commutative, and idempotent.

They are powerful when the business operation naturally maps to a convergent algebra.

They do not eliminate the need to understand semantics.

A bank balance is not safely modeled by casually merging two independently updated scalar values.

---

## 3.14 Sloppy Quorums

During failures, a system may accept writes on temporary substitute nodes that are not part of the key’s normal replica set.

This is a sloppy quorum.

Example:

```text
normal replicas: A, B, C
B and C unavailable
temporary write stored on A, D, E
```

This improves availability.

However, the read and write quorums may no longer overlap within the intended replica set.

The simple `R + W > N` reasoning becomes weaker.

### Hinted handoff

Temporary nodes store a hint:

```text
this value belongs to replica B
```

When B returns, the temporary node forwards the value.

### Risks

- temporary nodes fail before handoff
- hints accumulate
- read paths miss temporary copies
- topology changes during recovery
- stale values resurrect
- disk pressure from hint backlog

Availability gained during failure creates repair obligations afterward.

---

## 3.15 Read Repair and Anti-Entropy

Replication systems need mechanisms to repair divergent replicas.

### Read repair

A read detects that replicas disagree and updates stale copies.

```text
read A -> version 9
read B -> version 7
read C -> version 9

return version 9
repair B asynchronously or synchronously
```

Advantages:

- repair piggybacks on real traffic
- frequently read keys converge quickly

Limitations:

- cold keys may remain inconsistent
- repair adds read latency or background load
- incorrect conflict rules can propagate bad state

### Anti-entropy

Background processes compare replica state and repair differences.

Techniques include:

- hash trees
- range digests
- checksums
- log comparison
- snapshot synchronization

Advantages:

- repairs cold data
- provides systematic convergence

Costs:

- network and disk load
- operational tuning
- long repair windows on large datasets
- interaction with compaction and tombstones

### Repair debt

A system can continue serving while accumulating inconsistency debt.

Track:

- unrepaired ranges
- oldest pending repair
- repair throughput
- repair failure rate
- hint backlog
- tombstone age
- checksum mismatch rate

Repair is not optional maintenance. It is part of the consistency protocol.

---

## 3.16 Deletes, Tombstones, and Resurrection

Deleting a replicated value is not as simple as removing it locally.

Suppose A and B receive a delete while C is offline.

If A and B physically remove the value, then C returns later with the old copy.

Without evidence of the delete, repair may resurrect the data.

### Tombstone

A tombstone records that the key was deleted at a particular version.

```text
key: customer-7
state: deleted
version: 104
```

The tombstone must remain long enough for all replicas and repair processes to observe it.

### Garbage collection risk

If tombstones are removed too early:

- stale replicas may reintroduce deleted values
- deleted user data may reappear
- compliance obligations may be violated

### Operational requirements

Define:

- tombstone retention
- maximum replica outage duration
- repair completion expectations
- decommission procedure for long-offline nodes
- backup restoration behavior

A replica offline longer than the tombstone safety window may need full re-seeding rather than normal rejoin.

---

## 3.17 Split Brain

Split brain occurs when multiple nodes or partitions believe they are authoritative leaders for the same state.

```text
        network partition

old leader A          promoted leader B
accepts writes        accepts writes
```

Both sides may be internally healthy.

The failure is conflicting authority.

### Causes

- unsafe timeout-based promotion
- missing quorum requirement
- independent control planes
- stale DNS or client routing
- fencing failure
- operator force-promotion
- storage reachable from both leaders
- network partition that isolates monitors differently from clients

### Consequences

- conflicting writes
- duplicate job execution
- double allocation
- corrupted shared storage
- inconsistent external side effects
- difficult reconciliation

### Prevention

- majority-based election
- epochs or terms
- fencing tokens
- storage-level fencing
- single external authority
- promotion only from sufficiently fresh candidates
- refusal to operate without quorum

Chapter 4 treats consensus, leases, and fencing in detail. For this chapter, the key point is:

> Failover without exclusive authority is not recovery. It is creation of a second failure mode.

---

## 3.18 Promotion Safety

A promotion algorithm should prefer the candidate with the most complete authoritative history.

Possible evidence:

- highest committed log index
- latest durable replication position
- membership in the last successful quorum
- matching term or epoch
- absence of uncommitted divergent entries

### Unsafe promotion example

1. Leader A acknowledges write X locally.
2. Replica B has not received X.
3. A fails.
4. B is promoted immediately.
5. X disappears from the new authoritative history.

The system may have met its configured asynchronous semantics, but the product may still perceive this as data loss.

### Candidate freshness policy

Define:

- maximum allowed lag for automatic promotion
- whether promotion blocks when no safe candidate exists
- whether degraded read-only mode is preferable
- whether an operator may override safety
- what data-loss warning is required

### Staff-level decision

Sometimes the correct response is to remain unavailable rather than promote a stale replica and silently violate a hard invariant.

Availability is not always the highest-order requirement.

---

## 3.19 Rejoining the Old Leader

When the old leader returns, it may contain:

- writes missing from the new leader
- uncommitted entries
- an obsolete epoch
- stale client connections
- pending background work

It must not simply resume as leader.

Safe rejoin usually requires:

1. reject writes under the old epoch
2. identify the current authority
3. compare histories
4. discard or archive divergent uncommitted state
5. catch up from the current leader
6. rejoin as follower
7. become eligible for promotion only after validation

### Divergent write handling

Some systems discard old-leader-only writes because they were never committed.

Other systems preserve them for manual reconciliation.

The correct choice depends on whether clients were told those writes succeeded.

If an acknowledged write is discarded, the system must be able to explain which guarantee was violated or which configured durability model allowed it.

---

## 3.20 Multi-Leader Replication

In multi-leader replication, more than one node accepts writes.

```text
region A leader <---- replication ----> region B leader
```

### Use cases

- multi-region write locality
- disconnected operation
- collaborative applications
- migration between systems
- independent sites that later synchronize

### Benefits

- lower local write latency
- continued writes during inter-region partition
- regional autonomy

### Costs

- conflicting writes
- ordering ambiguity
- complex uniqueness enforcement
- difficult cross-region transactions
- conflict resolution in the application
- surprising failback behavior

### Uniqueness problem

Two leaders may independently allocate the same unique value.

Solutions include:

- region-prefixed identifiers
- globally unique random IDs
- partitioned ownership ranges
- central coordination for constrained keys
- conflict detection and compensation

### Multi-leader warning

Do not choose multi-leader replication only because the diagram looks highly available.

Choose it only when the business can define conflict semantics for every concurrently writable field or operation.

---

## 3.21 Cross-Region Topologies

### Active-passive

One region serves writes. Another receives replicas and is promoted during disaster.

Advantages:

- simple authority model
- fewer conflicts

Risks:

- failover delay
- replica lag
- untested standby
- DNS and routing convergence

### Active-active reads, single-region writes

Users read locally but writes route to one primary region.

Advantages:

- simpler write consistency
- low read latency

Risks:

- remote write latency
- read-after-write issues
- primary-region dependency

### Active-active writes

Multiple regions accept writes.

Advantages:

- local write latency
- regional autonomy

Risks:

- conflict resolution
- partition semantics
- global invariant difficulty

### Partitioned ownership by region

Each region owns specific tenants, accounts, or shards.

Advantages:

- one writer per item
- local latency for owned data
- reduced conflict scope

Risks:

- hot-region imbalance
- ownership transfer complexity
- cross-shard operations
- metadata authority dependency

### Architecture review question

For every cross-region design, draw:

- normal write path
- normal read path
- region-isolation path
- failover path
- failback path
- data reconciliation path

The failback path is often less tested and more dangerous than failover.

---

## 3.22 Failover Control Plane Dependencies

A data plane may be redundant while failover depends on a fragile control plane.

Potential hidden dependencies:

- DNS provider
- global load balancer
- cloud API
- identity provider
- secrets service
- certificate authority
- configuration store
- operator VPN
- CI/CD pipeline
- monitoring system

Example:

A standby database is healthy, but promotion requires credentials stored in the failed region.

The data copy exists, yet recovery cannot proceed.

### Review rule

Disaster recovery must include the dependencies needed to execute recovery, not only the application data.

---

## 3.23 Operational Telemetry for Replicated Systems

A replication dashboard should answer:

### Authority

- Which node is leader for each partition?
- What term or epoch is active?
- Are multiple leaders visible?
- When did the last leadership change occur?

### Durability

- What acknowledgement mode is configured?
- How many durable replicas exist?
- Which failure domains contain current copies?
- Are writes being acknowledged below policy?

### Lag

- What is each replica’s receive position?
- What is each replica’s durable position?
- What is each replica’s apply position?
- What is estimated catch-up time?

### Quorum

- Which replicas participated in recent quorums?
- Are operations using substitute replicas?
- Is quorum latency increasing?
- Are read and write failures caused by quorum loss?

### Repair

- How many ranges are inconsistent?
- What is the hint backlog?
- What is the oldest unrepaired range?
- What is tombstone pressure?

### Failover

- Is the best candidate sufficiently fresh?
- What data-loss estimate applies if promoted now?
- Is the old leader fenced?
- Are clients converging on the new authority?

### Customer-visible impact

- stale-read rate
- read-your-writes violations
- duplicate operation rate
- lost acknowledgement reconciliation count
- conflict rate
- failed or delayed writes

Infrastructure telemetry should connect to product semantics.

---

## 3.24 Incident Scenario — Lost Acknowledged Writes

### Scenario

A database primary uses asynchronous replication.

1. Client writes order `O-8841`.
2. Primary persists locally and returns success.
3. Replication to the standby is delayed.
4. Primary host fails permanently.
5. Standby is promoted.
6. Order `O-8841` is absent.

### What happened?

The system provided local durability, not failover durability.

The write was acknowledged before entering the standby’s recoverable history.

### Investigation

Collect:

- primary acknowledgement policy
- local flush configuration
- replica receive and apply positions
- last acknowledged primary position
- promotion candidate position
- failover timeline
- client retry and reconciliation evidence

### Immediate mitigation

- reconcile missing operations from upstream audit logs or external providers
- prevent duplicate replays with idempotency keys
- communicate the precise affected window
- preserve old-primary storage for forensic recovery

### Long-term options

- synchronous acknowledgement to another failure domain
- explicit API guarantee matching asynchronous behavior
- operation journal outside the primary
- delayed promotion when old-primary recovery is plausible
- business-level reconciliation

### Interview conclusion

A replica count of three would not have prevented this if success still depended only on one local acknowledgement.

---

## 3.25 Incident Scenario — Replica Lag Causes Overselling

### Scenario

Inventory writes go to the primary. Checkout availability reads are load-balanced to followers.

During a campaign:

- write volume spikes
- followers lag by 20 seconds
- customers continue reading old stock values
- multiple checkouts reserve the same remaining units

### Root design error

The architecture treated an invariant-sensitive read as safely stale.

### Immediate mitigation

- route checkout stock validation to the authoritative writer
- pause low-priority follower reads
- reduce batch load causing lag
- enforce reservation atomically at the source of truth

### Correct design options

- authoritative conditional decrement
- short-lived inventory reservation
- regional inventory allocation
- version token from product view to checkout
- bounded oversell policy where business permits it

### Staff-level takeaway

Read replicas are appropriate for catalog display. They are not automatically appropriate for the final invariant-preserving decision.

---

## 3.26 Incident Scenario — Split Brain After Automated Promotion

### Scenario

The monitoring system loses connectivity to the primary database, but some application nodes still reach it.

Automation promotes the standby.

Now:

- half the application writes to old primary A
- half writes to promoted primary B
- both databases appear healthy locally

### Evidence

- overlapping leader intervals
- different epochs or absent epoch enforcement
- divergent transaction histories
- clients connected to both endpoints
- DNS or service-discovery inconsistency

### Immediate response

1. stop writes or isolate one side
2. identify the chosen authority
3. fence the losing leader
4. preserve divergent logs
5. determine conflict scope
6. reconcile business operations
7. restore one topology

### Prevention

- quorum-based promotion
- external fencing
- monotonic epochs
- clients rejecting stale leaders
- storage fencing
- automation that refuses promotion without exclusive authority

### Staff-level takeaway

Health-check failure is not proof that the leader is dead. Promotion requires authority, not just suspicion.

---

## 3.27 Incident Scenario — Repair Storm

### Scenario

A network partition isolates replicas for several hours. When connectivity returns, all nodes begin aggressive anti-entropy repair.

Effects:

- disks saturate
- foreground latency rises
- timeouts trigger retries
- compaction falls behind
- replication lag worsens

### Failure pattern

```text
partition heals
  -> repair traffic spikes
  -> storage latency rises
  -> foreground operations slow
  -> retries multiply
  -> backlog and repair both grow
```

### Mitigation

- throttle repair concurrency
- prioritize foreground traffic
- stagger repair by range
- apply admission control
- pause nonessential compaction or backup work carefully
- extend recovery over a controlled window

### Prevention

- repair budgets
- rate-limited anti-entropy
- capacity reserved for recovery
- chaos testing of partition-heal behavior
- alerts on repair debt before emergency recovery

Recovery traffic is production traffic and must be capacity-planned.

---

## 3.28 Design Review Checklist

Before approving a replicated design, answer:

### Write guarantees

- What exact event causes success to be returned?
- How many replicas acknowledge?
- Are acknowledgements durable?
- Which failure domains contain the acknowledged write?
- Can an acknowledged write be lost during automatic failover?

### Read guarantees

- Which replicas serve reads?
- How stale may data be?
- Is read-your-writes required?
- Are monotonic reads required?
- How does the client express a minimum acceptable version?

### Failover

- Who is authorized to promote?
- How is the old leader fenced?
- How fresh must a candidate be?
- What happens when no safe candidate exists?
- What RPO and RTO are actually achievable?

### Quorum

- What are `N`, `R`, and `W`?
- Are quorums strict or sloppy?
- Are replica sets stable during the operation?
- How are concurrent writes versioned?
- Does the claimed consistency require more than quorum overlap?

### Repair

- How are stale replicas detected?
- How are cold keys repaired?
- What is the tombstone retention policy?
- What happens when a replica returns after a long outage?
- How much capacity is reserved for repair?

### Operations

- Can operators see commit, durable, and apply positions separately?
- Is failover tested under realistic partition conditions?
- Is failback tested?
- Are control-plane dependencies available during disaster?
- Can the organization reconcile divergent business effects?

---

## 3.29 Staff and Principal Interview Drills

### Question 1 — Three replicas, one acknowledgement

A service has three replicas but returns success after the primary writes locally. What failure can still lose acknowledged data?

A strong answer should discuss:

- primary loss before replication
- difference between replica count and acknowledgement policy
- local durability versus failover durability
- RPO implications
- possible synchronous or reconciliation-based mitigations

### Question 2 — Explain `R + W > N`

A strong answer should explain:

- quorum overlap
- why one read replica should overlap a successful write quorum
- why overlap alone does not ensure linearizability
- versioning and concurrent-write requirements
- sloppy-quorum caveats
- durable acknowledgement semantics

### Question 3 — Read replicas after writes

A user updates a password and immediately reads account metadata from a replica that has not applied the change. What consistency model is violated, and how would you fix it?

Expected direction:

- read-your-writes
- leader routing, session stickiness, or commit-position token
- security-sensitive reads may require authoritative routing

### Question 4 — Automatic failover with zero data loss

A team proposes asynchronous cross-region replication with ten-second automatic failover and RPO 0. Challenge the design.

Expected direction:

- asynchronous lag permits acknowledged-write loss
- RPO 0 requires synchronous durability or another authoritative journal
- promotion safety and fencing
- latency and availability trade-offs

### Question 5 — Multi-leader uniqueness

Two regions accept account creation. How will you preserve unique usernames during a partition?

Expected direction:

- central coordination sacrifices partition availability
- ownership partitioning
- reservation service
- region-qualified identifiers
- conflict and compensation if temporary duplicates are allowed

### Question 6 — Tombstones

Why can a deleted value return after a replica has been offline for a long time?

Expected direction:

- stale replica retained old value
- tombstone was garbage-collected
- repair treated old value as live
- full re-seed or longer retention prevents resurrection

### Question 7 — Best failover candidate

What information is more useful than wall-clock “last updated” time when selecting a replica for promotion?

Expected direction:

- durable log position
- committed index
- term or epoch
- membership in the last quorum
- divergence detection

### Question 8 — Repair after partition

Why can healing the network cause a second outage?

Expected direction:

- anti-entropy and hinted handoff create I/O and network spikes
- foreground traffic competes with repair
- retries amplify slowdown
- recovery work needs throttling and reserved capacity

---

## 3.30 Hands-On Labs

### Lab 1 — Measure asynchronous replication loss window

Goal: demonstrate that acknowledged success and failover durability can differ.

1. Start a primary and asynchronous replica.
2. Introduce replication delay.
3. Continuously write uniquely numbered records.
4. Record every client acknowledgement.
5. Terminate the primary abruptly.
6. Promote the replica.
7. Compare acknowledged IDs with surviving IDs.
8. Calculate the observed data-loss window.
9. Repeat with synchronous acknowledgement.

Document:

- latency difference
- surviving write count
- RPO under each mode
- operational cost of stronger acknowledgement

### Lab 2 — Read-your-writes using commit positions

1. Configure a leader and read replica.
2. Introduce apply delay on the replica.
3. Write a record and capture the leader’s commit position.
4. Immediately read from the follower without a position check.
5. Observe stale data.
6. Add a router that waits until follower apply position reaches the required token.
7. Add leader fallback when the wait budget is exhausted.
8. Measure latency and correctness.

### Lab 3 — Quorum experiment

Build a small simulator with `N=3`.

Test:

- `W=1, R=1`
- `W=2, R=2`
- `W=3, R=1`
- `W=1, R=3`

Inject:

- one failed replica
- delayed replicas
- concurrent writes
- volatile acknowledgements

Record:

- operation availability
- stale-read frequency
- tail latency
- acknowledged-write survival

### Lab 4 — Conflict detection

1. Create three replicas.
2. Partition one replica from the others.
3. Write value A on one side and value B on the other.
4. Reconnect the replicas.
5. Compare last-write-wins with version-vector conflict detection.
6. Implement an application merge policy.
7. Document which business semantics each policy preserves or destroys.

### Lab 5 — Tombstone resurrection

1. Replicate a key to three nodes.
2. Take node C offline.
3. Delete the key on A and B.
4. Expire the tombstone before C returns.
5. Rejoin C and run naive repair.
6. Observe possible resurrection.
7. Repeat with retained tombstones or full re-seeding.

### Lab 6 — Unsafe failover

1. Run a primary and two followers.
2. Partition the monitor from the primary while one client still reaches it.
3. Promote a follower without fencing.
4. Send writes to both leaders.
5. Reconnect the cluster.
6. Inspect divergent histories.
7. Repeat using epochs and a fencing mechanism.

### Lab 7 — Repair storm

1. Generate divergent data during a partition.
2. Reconnect nodes and start unrestricted repair.
3. Measure foreground latency, disk utilization, queue depth, and retry rate.
4. Repeat with throttled repair and workload prioritization.
5. Estimate reserved capacity needed for safe recovery.

---

## 3.31 Whiteboard Answer Pattern

When asked to design replication or failover in an interview, use this sequence:

1. State the business invariant and allowed data loss.
2. Define the source of truth and write authority.
3. Draw the normal replication path.
4. Define acknowledgement: received, durable, committed, or applied.
5. Define read routing and staleness policy.
6. State the failure domains covered by replicas.
7. Walk through leader loss before and after replication.
8. Explain promotion authority and fencing.
9. Explain repair, rejoin, and failback.
10. Name the telemetry proving the guarantees.
11. Discuss latency, availability, and cost trade-offs.

A strong answer distinguishes:

- normal availability
- partition availability
- durability at acknowledgement
- consistency observed by reads
- recovery correctness

---

## 3.32 Principal-Level Architecture Heuristics

### Heuristic 1

A replica is useful only if it is in a sufficiently independent failure domain and sufficiently current for the recovery objective.

### Heuristic 2

A write guarantee is defined by the acknowledgement path, not by the configured replica count.

### Heuristic 3

Follower reads are a consistency decision disguised as a scaling decision.

### Heuristic 4

Automatic failover that cannot fence the old leader is unsafe automation.

### Heuristic 5

Quorum overlap is necessary for some guarantees but not sufficient for linearizability.

### Heuristic 6

Every availability gain from sloppy quorum or multi-leader writes creates conflict and repair obligations.

### Heuristic 7

Repair capacity must be reserved before failure; it cannot be invented during recovery.

### Heuristic 8

Failback deserves the same design rigor and testing as failover.

### Heuristic 9

RPO and RTO are properties of the entire recovery workflow, including routing, identity, secrets, operators, and control planes.

### Heuristic 10

The weakest replica is not only a performance concern. It can become a promotion, repair, or data-resurrection risk.

---

## 3.33 Chapter Summary

Replication creates copies. Correctness comes from the protocol governing those copies.

A production-grade design must make explicit:

- what success means
- where durability exists
- how writes are ordered
- how reads choose versions
- how stale replicas are repaired
- how deletes remain deleted
- how leaders are replaced
- how old leaders are fenced
- how data loss and downtime map to RPO and RTO

The key mental model is:

```text
business invariant
      |
      v
acknowledgement rule
      |
      v
replication and quorum protocol
      |
      v
read visibility + failover behavior
      |
      v
repair, reconciliation, and proof
```

The next chapter builds on this foundation by examining consensus, elections, leases, epochs, and fencing tokens—the mechanisms used to establish exclusive authority when failures and partitions make simple leader promotion unsafe.
