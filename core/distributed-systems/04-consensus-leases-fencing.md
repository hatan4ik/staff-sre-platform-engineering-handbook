# Chapter 4 — Consensus, Elections, Leases, Epochs, and Fencing Tokens

Replication creates copies. Consensus establishes one authoritative history among those copies despite failures, retries, delays, duplication, reordering, and partitions.

The central problem is not merely choosing a leader.

It is preserving safety when nodes have incomplete and contradictory views of the system.

A node may believe it is leader after its lease expired. A client may continue sending work to an old primary after failover. A paused process may wake up and resume writing with stale authority. A network partition may leave two groups internally healthy but mutually unreachable.

Consensus protocols, terms, epochs, leases, and fencing tokens exist to answer one question:

> Which actor is currently authorized to make an irreversible decision, and how do all other actors prove that stale authority can no longer cause damage?

---

## 4.1 Coordination Is About Safety Under Uncertainty

Distributed coordination appears in many forms:

- leader election
- shard ownership
- distributed locks
- membership changes
- job scheduling
- configuration updates
- primary selection
- exclusive access to storage
- allocation of unique sequence ranges

The common invariant is exclusivity or ordered agreement.

Examples:

- At most one controller may publish commands for a shard.
- At most one process may hold the migration lock.
- A configuration update must appear in one globally agreed order.
- A stale database primary must not continue writing after failover.

A coordination system must preserve safety even when liveness is temporarily lost.

### Safety before liveness

A safe system may refuse progress when it cannot establish authority.

An unsafe system may remain available by allowing multiple actors to proceed.

For exclusive ownership, refusing work is usually preferable to creating two owners.

---

## 4.2 Consensus in Plain Language

Consensus allows a group of nodes to agree on a sequence of values despite some failures.

A practical replicated-state-machine model is:

```text
clients propose commands
        |
        v
consensus protocol orders commands
        |
        v
replicated log
        |
        v
all healthy state machines apply the same commands in the same order
```

If every node begins with the same state and applies the same deterministic commands in the same order, the nodes converge on the same state.

Consensus is therefore usually about agreeing on the log, not directly synchronizing every memory cell.

### Consensus properties

A protocol should preserve:

- **Agreement:** healthy participants do not decide conflicting values for the same position.
- **Validity:** the decided value was legitimately proposed under the protocol.
- **Integrity:** a participant does not decide multiple values for one position.
- **Termination:** under sufficient synchrony and healthy quorum, a value is eventually decided.

Safety properties should hold even during arbitrary delays.

Liveness generally requires timing assumptions, such as the network eventually behaving well enough for an election to complete.

---

## 4.3 FLP and the Practical Meaning of Timing

In a fully asynchronous system, deterministic consensus cannot guarantee termination if even one process may fail.

The practical lesson is not that consensus is impossible.

It is that a system cannot distinguish indefinitely between:

- a failed node
- a slow node
- a delayed message
- a network partition

Production consensus protocols therefore use timeouts to make progress, while structuring the protocol so incorrect timeout guesses do not violate safety.

### Important distinction

Timeouts influence liveness decisions such as starting an election.

Timeouts must not be treated as proof that old authority is safely gone.

Safety comes from quorum, terms, log rules, and fencing—not from the clock alone.

---

## 4.4 Majority Quorum

For a cluster with `N` voting members, a majority is:

```text
floor(N / 2) + 1
```

Examples:

```text
N=3 -> majority 2
N=5 -> majority 3
N=7 -> majority 4
```

Any two majorities overlap in at least one member.

That overlap is fundamental because it prevents two disjoint groups from both forming a majority at the same time within one fixed membership configuration.

### Why odd cluster sizes are common

A four-node cluster still requires three votes for a majority and tolerates only one failure.

A three-node cluster requires two votes and also tolerates one failure.

The fourth voter adds cost without increasing failure tolerance.

Similarly:

- five voters tolerate two failures
- six voters still tolerate only two failures

Non-voting replicas may still be useful for reads, backup, or geography, but they should not be confused with voting fault tolerance.

---

## 4.5 Terms and Epochs

A term or epoch is a monotonically increasing identifier for an authority period.

```text
term 41: leader A
term 42: leader B
term 43: leader C
```

When a node observes a higher term, it must treat its older authority as stale.

Terms solve several problems:

- distinguish old leaders from current leaders
- reject delayed messages from prior elections
- order leadership changes
- provide a basis for fencing
- prevent stale state from being accepted as current

### Monotonicity requirement

Epochs must never move backward.

A value based only on wall-clock time is risky because clocks can jump, skew, or repeat.

Safer sources include:

- consensus log term
- compare-and-swap counter
- database sequence
- strongly consistent metadata store

### Epoch propagation

The epoch should travel with every operation that depends on authority.

```text
write(resource=X, epoch=43)
```

The receiving system must reject lower epochs.

Without enforcement at the side-effect boundary, the epoch is only advisory metadata.

---

## 4.6 Election Lifecycle

A generic leader election has these stages:

1. Followers receive heartbeats from the current leader.
2. A follower stops receiving heartbeats before its election timeout.
3. The follower increments its term and becomes a candidate.
4. It requests votes from peers.
5. Peers grant at most one vote per term according to freshness rules.
6. A candidate receiving a majority becomes leader.
7. The new leader sends heartbeats to establish authority.

### Randomized election timeouts

If every follower times out simultaneously, multiple candidates may repeatedly split the vote.

Randomized timeouts reduce synchronized elections.

### Election safety

At most one leader should be elected for a given term.

This follows from majority overlap and one vote per term.

### Election liveness

A leader is eventually elected when:

- a majority can communicate
- timing stabilizes sufficiently
- candidates use randomized retry behavior

---

## 4.7 Raft Mental Model

Raft separates consensus into understandable components:

- leader election
- log replication
- safety rules
- membership changes

The protocol maintains a replicated log of commands.

Each log entry typically includes:

- term
- index
- command

```text
index: 101  term: 8  command: set x=4
index: 102  term: 8  command: create user 91
index: 103  term: 9  command: delete lock A
```

### Leader role

The leader:

- accepts client commands
- appends entries locally
- replicates entries to followers
- advances commit index when protocol rules are met
- informs followers which entries are committed

### Follower role

A follower:

- validates the leader term
- checks log continuity
- appends matching entries
- rejects conflicting history
- applies committed entries in order

### Candidate role

A candidate requests votes after an election timeout.

The role is temporary until it wins or observes a valid leader.

---

## 4.8 Log Matching

A consensus log must prevent divergent committed histories.

A common property is:

> If two logs contain an entry with the same index and term, the logs are identical through that index.

Followers reject append requests that do not match the expected previous index and term.

The leader backs up until it finds a common prefix, then overwrites conflicting uncommitted suffixes.

### Example

Leader log:

```text
1/1 2/1 3/2 4/3 5/3
```

Follower log:

```text
1/1 2/1 3/2 4/2 5/2
```

Entries after the common prefix at index 3 conflict.

The follower discards its uncommitted suffix and follows the current leader’s history.

### Operational implication

A node may contain durable log entries that are later discarded because durability on one node does not imply consensus commitment.

---

## 4.9 Committed Versus Uncommitted Entries

An entry may exist on several nodes but still not be committed under the protocol’s rules.

A committed entry is safe to apply as part of the authoritative history.

An uncommitted entry may be overwritten after failover.

### Client acknowledgement

A correct client-facing write path should normally return success only after the entry is committed according to the promised consistency and durability model.

Returning success after local append alone can expose acknowledged-write loss.

### Apply lag

Even after commitment, followers may apply entries later.

Therefore systems track:

- last log index received
- last durable index
- commit index
- last applied index

These are different operational states.

---

## 4.10 Leader Completeness

A newly elected leader must contain all entries that were committed in previous terms.

Election freshness rules usually compare candidate logs using term and index.

A voter rejects a candidate whose log is less up to date.

This prevents a stale follower from becoming leader and losing committed history.

### Staff-level interview point

Choosing the node with the newest wall-clock timestamp is not sufficient.

The protocol must compare authoritative log history.

---

## 4.11 Linearizable Reads

A leader may appear current while actually being partitioned from the majority.

If it serves reads from local state without confirmation, it may return stale data after a new leader has been elected elsewhere.

### Safe read options

#### Log entry barrier

Commit a no-op or read barrier through the consensus log before serving the read.

This proves current authority but adds write-like coordination.

#### Read index

Confirm leadership with a quorum and use a commit index that is safe for the read.

#### Valid leader lease

Serve local reads under a lease only when the timing assumptions and clock model safely support it.

#### Follower read with token

A follower may serve a read if it has applied at least the required committed index.

### Staff-level rule

Being the node named “leader” is not enough. The node must prove that it still has current authority before promising linearizable reads.

---

## 4.12 Leases

A lease grants authority for a bounded period.

Example:

```text
worker A owns shard 7 until lease expiration
```

Leases improve liveness and reduce repeated coordination, but they introduce assumptions about time.

### Lease holder perspective

The holder believes the lease is valid until its local deadline.

### Grantor perspective

The authority believes the lease expires according to its own clock or consensus state.

### Risk

Clock skew, process pause, scheduling delay, or network delay can cause the holder and grantor to disagree about validity.

### Safer lease design

- use monotonic clocks for elapsed duration
- keep lease duration larger than expected timing uncertainty
- renew well before expiration
- stop work before local uncertainty boundary
- pair leases with fencing tokens
- ensure the resource validates the token

### Lease is not ownership proof at the resource

A lease may tell a worker it should stop.

It does not prevent a paused worker from waking up and issuing stale writes.

Fencing is required to protect the resource.

---

## 4.13 The Pause Problem

Consider a worker holding a distributed lock:

1. Worker A acquires the lock.
2. A experiences a long garbage-collection pause or VM suspension.
3. The lock lease expires.
4. Worker B acquires the lock.
5. A wakes up and continues operating.

Now both A and B may act.

The lock service behaved correctly.

The application is still unsafe because A did not know it had lost authority while paused.

### Key conclusion

Distributed locks without fencing tokens do not protect external resources from stale holders.

---

## 4.14 Fencing Tokens

A fencing token is a monotonically increasing number issued with each ownership grant.

```text
A acquires lock -> token 81
lease expires
B acquires lock -> token 82
```

Every write to the protected resource includes the token.

```text
write(data, fencing_token=82)
```

The resource remembers the highest token seen and rejects lower tokens.

```text
if token < highest_token:
    reject stale operation
```

When A wakes and submits token 81, the resource rejects it.

### Critical requirement

The protected resource must enforce fencing.

If only clients compare tokens among themselves, a stale client can still cause damage.

### Suitable enforcement points

- database row with atomic compare-and-set
- storage gateway
- job coordinator
- API service owning the resource
- message consumer state machine
- hypervisor or orchestration controller

### Unsuitable assumption

A plain object store or external service may not support atomic token validation.

In that case, the design needs an intermediary authority or a different ownership model.

---

## 4.15 Distributed Lock Semantics

The phrase “distributed lock” is incomplete.

A lock design must define:

- acquisition semantics
- lease duration
- renewal policy
- fairness
- reentrancy
- fencing token
- failure behavior
- maximum critical-section duration
- resource-side enforcement

### Lock safety invariant

At most one valid fencing epoch may mutate the protected resource.

### Lock liveness requirement

If the current holder fails, another participant eventually acquires ownership.

### Lock anti-pattern

```text
SET lock owner=A TTL=30s
```

This may be useful for best-effort coordination, but it is not automatically safe for irreversible exclusive side effects.

Ask what happens when:

- A pauses for 45 seconds
- the TTL expires
- B acquires the lock
- A resumes

Without fencing, two actors may proceed.

---

## 4.16 Compare-and-Swap and Optimistic Concurrency

Not every coordination problem requires a long-lived lock.

Optimistic concurrency uses a version and atomic compare-and-swap:

```text
read value with version 41
compute update
write only if version is still 41
```

The storage system performs:

```text
UPDATE resource
SET value = new_value, version = 42
WHERE id = X AND version = 41
```

If zero rows are updated, another writer won the race.

### Benefits

- no lease management
- stale writers fail safely
- good for short transactions
- naturally exposes conflicts

### Costs

- retries under contention
- starvation for hot resources
- multi-resource invariants remain difficult

### Staff-level choice

Prefer optimistic concurrency when conflicts are rare and operations are short.

Use serialized ownership when ordering is essential or contention is high.

---

## 4.17 Consensus Versus Coordination Services

Applications often use a coordination service such as a strongly consistent key-value store rather than implementing consensus directly.

This is usually correct.

The application receives abstractions such as:

- conditional writes
- watches
- leases
- sessions
- monotonic revisions
- transactions

### But abstraction does not remove semantics

The application still must understand:

- whether reads are linearizable or serializable
- whether watches can miss events after compaction
- whether leases provide fencing
- what happens during quorum loss
- how revisions map to ownership
- how transactions are scoped

### Coordination service is a dependency

If every service requires the coordination cluster for every request, the cluster becomes part of the critical latency and availability path.

Use coordination for metadata and authority decisions, not as an accidental high-volume data plane unless designed for it.

---

## 4.18 Cluster Membership

Consensus safety assumes a defined voter set.

Changing membership is itself a consensus problem.

### Unsafe membership change

Suppose cluster A, B, C changes directly to D, E, F.

The old and new majorities may be disjoint.

Two groups could each believe they have authority.

### Joint consensus

A safe transition temporarily requires agreement under both old and new configurations.

Conceptually:

```text
old config: A B C
joint config: A B C + D E F
new config: D E F
```

This preserves quorum overlap during transition.

### Operational rules

- change one voter at a time unless protocol explicitly supports joint changes
- avoid replacing multiple failed voters simultaneously without understanding quorum state
- do not count non-voting replicas as voters
- verify the actual membership, not only intended configuration

---

## 4.19 Witnesses and Tie-Breakers

A witness participates in voting but may not hold full application data.

It can help establish majority without maintaining a complete data replica.

### Benefits

- lower storage cost
- useful in some two-site topologies

### Risks

- quorum may exist without enough recoverable data
- witness placement may share failure domains unexpectedly
- network asymmetry can produce surprising availability

### Review question

Does a majority vote also imply that a sufficiently current data copy exists?

Voting availability and data durability are related but not identical.

---

## 4.20 Two-Data-Center Trap

A cluster split evenly across two sites is difficult.

Example:

```text
site A: 2 voters
site B: 2 voters
```

A site partition leaves neither side with the required majority of three.

Adding a fifth voter in an independent failure domain can break the tie:

```text
site A: 2
site B: 2
site C/witness: 1
```

But the fifth location becomes strategically important.

### Asymmetric design

Another approach places three voters in the primary site and two in the secondary.

This preserves service after losing the secondary but not after losing the primary.

The topology expresses a business decision about preferred availability.

### Staff-level rule

Quorum placement is a failure-policy decision, not merely a distribution exercise.

---

## 4.21 Network Partitions and Minority Behavior

During a partition, only the side with quorum may continue consensus writes.

The minority should:

- stop accepting authoritative writes
- step down stale leaders
- expose clear quorum-loss health
- avoid serving linearizable reads
- preserve local state for later catch-up

### Read-only minority

A minority may serve explicitly stale reads if the API and business allow it.

It must not label those reads as strongly consistent.

### Dangerous fallback

Automatically switching from strong writes to local writes during quorum loss creates divergent histories.

That is a consistency-model change and must be an explicit business decision with reconciliation semantics.

---

## 4.22 Session and Watch Semantics

Coordination systems often expose watches or subscriptions to changes.

Applications may assume watches are a permanent event stream.

Risks include:

- disconnected watch
- event compaction
- duplicate notification
- delayed notification
- reconnect from stale revision

### Correct pattern

1. Read current state at a known revision.
2. Start watch from that revision.
3. Process events idempotently.
4. On compaction or gap, re-read current state.
5. Reconcile desired and observed state.

A watch is a notification optimization, not the only source of truth.

---

## 4.23 Exactly-Once Leadership Is Not Enough

Even with safe leader election, side effects can duplicate.

Example:

1. Leader A sends an external payment request.
2. The payment succeeds.
3. A crashes before recording completion.
4. Leader B replays the task.

Consensus ensured only one leader at a time.

It did not make the external side effect exactly once.

### Required mechanisms

- idempotency key
- durable operation state
- transactional outbox or command log
- reconciliation with external provider
- fencing where supported

Consensus orders decisions. End-to-end correctness still requires idempotent side-effect design.

---

## 4.24 Control-Plane Versus Data-Plane Availability

A coordination cluster often belongs to the control plane.

The data plane may continue for a limited time when the control plane is unavailable.

Examples:

- proxies continue using cached routes
- workloads continue under existing leases
- schedulers stop placing new work
- databases continue serving from current leadership

### Graceful degradation

Define which actions require fresh coordination:

- new leader election
- configuration mutation
- new workload scheduling
- certificate issuance
- policy changes

Define which actions may continue from cached state:

- established request routing
- existing workload execution
- read-only service

### Risk

Continuing indefinitely with stale control-plane state can violate safety.

Grace periods and authority boundaries must be explicit.

---

## 4.25 Incident Scenario — Stale Lock Holder Corrupts Output

### Scenario

A batch worker acquires a 30-second lease and begins writing a report to shared storage.

The worker pauses for 45 seconds.

The lease expires, and a second worker acquires ownership.

Both workers write overlapping output after the first resumes.

### Root cause

The design used a lease as if it fenced the storage resource.

### Immediate mitigation

- stop both workers
- identify the newest valid ownership epoch
- restore output from a known-good checkpoint
- prevent stale workers from reaching the resource

### Permanent fix

- issue monotonic fencing tokens
- require token validation on every mutation
- write to epoch-specific temporary paths
- publish final output using conditional atomic promotion
- make retries idempotent

### Takeaway

A lock service cannot protect a resource that does not validate ownership.

---

## 4.26 Incident Scenario — Leader Serves Stale Reads

### Scenario

Leader A becomes partitioned from the cluster but remains reachable by some clients.

The majority elects leader B.

A continues serving local reads and reports outdated configuration.

### Root cause

The read path trusted local leader state without proving current majority authority.

### Mitigation

- stop reads from A
- require quorum-confirmed read index or lease validity
- route consistency-sensitive reads through current authority

### Prevention

- term validation
- leader step-down on quorum loss
- linearizable read protocol
- client awareness of stale epochs

---

## 4.27 Incident Scenario — Election Storm

### Scenario

Storage latency causes heartbeat processing delays.

Followers repeatedly time out and start elections.

Effects:

- leadership churn
- write unavailability
- repeated log synchronization
- rising client retries
- further CPU and disk pressure

### Signals

- term increasing rapidly
- frequent leader changes
- heartbeat RTT spikes
- fsync latency
- scheduler pause time
- queue depth
- failed proposal count

### Mitigation

- reduce load
- fix storage or CPU saturation
- ensure election timeout exceeds normal worst-case heartbeat delay
- add jitter
- suppress retry amplification

### Warning

Blindly increasing election timeout may hide a performance problem and slow real failure recovery.

Tune after measuring the latency distribution and failure objectives.

---

## 4.28 Incident Scenario — Unsafe Membership Replacement

### Scenario

Operators lose two nodes in a five-member cluster.

They remove both and add two replacements simultaneously through manual configuration.

Different nodes observe different membership states.

### Risks

- split quorum assumptions
- inability to elect
- conflicting authority
- permanent loss of committed entries if the wrong history is chosen

### Safe response

- inspect actual committed membership
- follow protocol-supported joint consensus or one-at-a-time replacement
- avoid force operations unless a documented disaster procedure exists
- snapshot and preserve forensic state

### Takeaway

Membership metadata is consensus state, not ordinary configuration.

---

## 4.29 Operational Telemetry

A consensus dashboard should expose:

### Leadership

- current leader
- current term or epoch
- leader changes per hour
- time since last stable leadership
- duplicate-leader detection

### Quorum

- voting members
- reachable voters
- quorum health
- proposal success rate
- commit latency

### Log

- leader last index
- follower match index
- commit index
- applied index
- log divergence or rejected append count
- snapshot install progress

### Timing

- heartbeat latency
- election timeout events
- process pause duration
- fsync latency
- network RTT between voters

### Leases

- active lease count
- renewal latency
- lease expiration rate
- stale-holder rejection rate
- fencing token monotonicity

### Client impact

- linearizable read latency
- unavailable write rate
- retry attempts per logical operation
- stale-epoch rejection count
- leadership-related error rate

---

## 4.30 Design Review Checklist

### Consensus scope

- What state requires global ordering?
- Can the problem be partitioned by shard or tenant?
- Is consensus on the critical request path?
- What happens during quorum loss?

### Election

- What starts an election?
- What constitutes a vote?
- How is candidate freshness checked?
- Can two leaders exist in one term?
- How does an old leader learn it is stale?

### Leases

- What clock assumptions exist?
- What is the maximum process pause?
- When does the holder stop work?
- What happens if renewal succeeds but the response is lost?
- Is a fencing token issued?

### Fencing

- Is the token monotonic?
- Is it attached to every protected mutation?
- Does the resource reject stale tokens atomically?
- What happens when the resource cannot enforce fencing?

### Membership

- How are voters added and removed?
- Is joint consensus used?
- Are failure domains independent?
- Does quorum imply current data availability?

### Reads

- Are reads linearizable, serializable, or stale?
- How does the leader prove current authority?
- Can followers serve reads with a minimum revision?

### Operations

- Are election storms detectable?
- Are term changes audited?
- Is quorum-loss behavior tested?
- Is stale-leader rejection tested?
- Are disaster membership procedures documented?

---

## 4.31 Staff and Principal Interview Drills

### Question 1 — Why not use a timeout as proof of death?

Expected direction:

- timeout proves only lack of timely response
- node may be paused or partitioned
- promotion requires quorum and fencing
- safety cannot depend on perfect failure detection

### Question 2 — Explain fencing tokens

Expected direction:

- monotonically increasing ownership epoch
- included in every protected operation
- resource stores highest accepted token
- stale holders are rejected
- lease alone is insufficient

### Question 3 — Why can an old leader serve stale reads?

Expected direction:

- it may be partitioned from quorum
- a newer leader may exist
- local role state is stale
- linearizable read requires quorum confirmation, read index, or safe lease

### Question 4 — Why are three voters often better than four?

Expected direction:

- both tolerate one failure
- majority of three is two
- majority of four is three
- the fourth voter adds cost without another tolerated failure

### Question 5 — What can consensus not solve?

Expected direction:

- exactly-once external side effects
- business-level idempotency
- arbitrary multi-system transactions
- resource fencing when downstream does not enforce epochs
- capacity and overload

### Question 6 — What is the danger of a long GC pause?

Expected direction:

- lease expiration while holder is paused
- new owner elected
- stale process resumes
- fencing token needed

### Question 7 — How do you safely change cluster membership?

Expected direction:

- membership is consensus state
- preserve overlapping quorums
- joint consensus or protocol-defined staged changes
- avoid simultaneous uncoordinated replacement

### Question 8 — Should a minority partition serve traffic?

Expected direction:

- no authoritative writes
- possibly explicitly stale reads
- depends on business and API semantics
- must not masquerade as strong consistency

---

## 4.32 Hands-On Labs

### Lab 1 — Observe terms and elections

1. Run a three-node consensus cluster.
2. Record the current leader and term.
3. Stop the leader.
4. Measure election duration.
5. Restart the old leader.
6. Confirm it rejoins as follower under the newer term.
7. Repeat with network delay instead of process termination.

### Lab 2 — Minority behavior

1. Partition one node from a three-node cluster.
2. Confirm the majority continues committing.
3. Attempt writes through the minority.
4. Attempt stale and linearizable reads.
5. Document the difference.

### Lab 3 — Stale leader read

1. Isolate the leader from peers but keep it reachable from a test client.
2. Allow the majority to elect a new leader and commit a change.
3. Read from the old leader using an unsafe local-read path.
4. Observe stale data.
5. Repeat with a quorum-confirmed read protocol.

### Lab 4 — Lease pause problem

1. Implement a lease-based worker lock.
2. Pause worker A longer than the lease.
3. Let worker B acquire the lease.
4. Resume A.
5. Observe both workers acting.
6. Add fencing tokens and resource-side validation.
7. Confirm A’s stale operations are rejected.

### Lab 5 — Optimistic concurrency

1. Create a versioned record.
2. Have two clients read version 10.
3. Submit competing updates with compare-and-swap.
4. Confirm only one succeeds.
5. Add bounded retry with conflict-aware merge.
6. Measure behavior under high contention.

### Lab 6 — Election storm

1. Introduce storage delay on cluster nodes.
2. Reduce election timeout until leadership churn begins.
3. Track term changes, commit latency, and client retries.
4. Restore realistic timeouts and remove the storage bottleneck.
5. Compare recovery time and stability.

### Lab 7 — Membership change

1. Run a three-node cluster.
2. Add a fourth node using the supported membership protocol.
3. Remove one old node.
4. Observe quorum requirements at each step.
5. Simulate an unsafe out-of-band configuration change in a disposable lab.
6. Document why the protocol-managed path is required.

---

## 4.33 Whiteboard Answer Pattern

For a coordination or leader-election design:

1. State the exclusivity or ordering invariant.
2. Define voter membership and failure domains.
3. Explain the majority requirement.
4. Describe election and candidate freshness.
5. Define terms or epochs.
6. Explain log commitment.
7. Explain how stale leaders step down.
8. Add leases only with timing assumptions stated.
9. Add fencing at the side-effect boundary.
10. Define behavior during quorum loss.
11. Explain membership change.
12. Name operational telemetry and recovery procedures.

A Principal-level answer should explicitly separate:

- authority election
- log agreement
- lease validity
- resource fencing
- end-to-end idempotency

---

## 4.34 Principal-Level Architecture Heuristics

### Heuristic 1

A timeout may start an election, but it must never be the only proof that old authority is gone.

### Heuristic 2

A lease is a promise to stop; a fencing token is enforcement against stale continuation.

### Heuristic 3

The side-effecting resource, not merely the lock service, must reject stale epochs.

### Heuristic 4

Consensus solves ordered agreement, not exactly-once external effects.

### Heuristic 5

Voting topology encodes the organization’s preferred failure behavior.

### Heuristic 6

Committed, durable, and applied are different states and deserve separate telemetry.

### Heuristic 7

A leader that cannot contact quorum should not assume it remains authoritative.

### Heuristic 8

Membership changes are protocol operations, not configuration edits.

### Heuristic 9

Linearizable reads require current-authority proof, not merely local leader identity.

### Heuristic 10

Coordination belongs only around the smallest state that truly requires serialization.

---

## 4.35 Chapter Summary

Consensus establishes one authoritative ordered history.

Elections decide who may propose that history.

Terms and epochs invalidate stale authority.

Leases improve liveness but depend on timing assumptions.

Fencing tokens protect resources when stale actors resume after pause or partition.

The complete safety chain is:

```text
majority elects authority
        |
        v
monotonic term or epoch
        |
        v
commands committed through consensus
        |
        v
lease bounds current ownership
        |
        v
fencing token enforced by resource
        |
        v
idempotent business side effects
```

Omitting any layer may leave a gap:

- election without fencing permits stale actors
- fencing without monotonic tokens permits rollback
- consensus without idempotency permits duplicated external effects
- leases without process-pause reasoning permit overlapping workers
- membership changes without quorum overlap permit split authority

The next chapter moves from authority to scale: partitioning, sharding, rebalancing, hotspots, skew, ownership transfer, and the operational risks created when one logical dataset is divided across many independently moving partitions.
