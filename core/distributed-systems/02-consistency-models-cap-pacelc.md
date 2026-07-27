# Chapter 2 — Consistency Models, CAP, PACELC, and Transaction Boundaries

## 2.1 The Biggest Lie in Distributed Systems

A single computer has one memory space, one kernel, one clock, and one authoritative state.

A distributed system has none of these.

Instead, it consists of independent computers communicating over unreliable networks, each with its own:

- CPU scheduler
- Memory
- Clock
- Network interface
- Failure modes
- Local view of reality

There is no global truth.

There are only nodes attempting to converge on a sufficiently consistent view of reality.

This changes everything.

---

## 2.2 The Three Facts Every Staff Engineer Must Accept

### Fact #1: Networks Fail

Failures include:

- Dropped packets
- Delayed packets
- Duplicated packets
- Reordered packets
- Network partitions
- Half-open TCP connections
- DNS failures
- TLS negotiation failures

Every distributed algorithm begins by assuming the network will eventually betray you.

### Fact #2: Time Is Not Global

Machine A:

```text
12:00:00.001
```

Machine B:

```text
11:59:59.940
```

Machine C:

```text
12:00:01.180
```

Which event happened first?

You do not know.

Wall clocks cannot reliably determine causality.

### Fact #3: Every Node Can Lie

A node that stops responding may be:

- dead
- overloaded
- partitioned
- paused by garbage collection
- CPU-starved
- experiencing storage latency

To the rest of the cluster, these failures are indistinguishable.

---

## 2.3 Consistency

Consistency answers one question:

> If one client writes data, when should every other client observe that write?

Different businesses require different answers.

### Strong Consistency

```text
Write
  ↓
Commit
  ↓
Every future read returns the new value
```

Advantages:

- Simplifies reasoning
- Prevents stale reads after commit
- Makes many transactional workflows easier to model

Disadvantages:

- Higher latency
- Lower availability during some failures
- Often requires coordination across nodes

Examples include strongly consistent access paths in systems such as etcd, ZooKeeper, and a relational database primary.

### Eventual Consistency

```text
Write
  ↓
Replication
  ↓
Eventually all replicas converge
```

Temporary stale reads are allowed.

Eventually, every healthy replica converges on the accepted state.

Common examples include DNS, many leaderless databases, and asynchronous replication pipelines.

### Read-Your-Writes Consistency

If a client performs:

```text
PUT /profile
```

and immediately executes:

```text
GET /profile
```

that client must observe its own update.

Other clients may still observe stale data.

This model significantly improves user experience while remaining cheaper than global strong consistency.

### Monotonic Reads

A client should never observe state moving backward.

Bad sequence:

```text
Version 8
  ↓
Version 6
```

Acceptable sequence:

```text
Version 6
  ↓
Version 7
  ↓
Version 8
```

Monotonic reads are frequently implemented with session affinity, replica stickiness, version checks, or causal metadata.

### Causal Consistency

Suppose Alice creates a document and Bob replies to that document.

It must not be possible for another client to observe Bob's reply before observing the document it depends on.

Cause must precede effect.

Causal consistency is weaker than linearizability but stronger than unconstrained eventual consistency.

---

## 2.4 Linearizability

A common Staff-level interview question is:

> Explain linearizability.

Linearizability means every successful operation appears to execute atomically at one instant between invocation and completion.

The system behaves as though all operations occurred on one global real-time timeline.

```text
Write A completes
  ↓
Write B completes
  ↓
Read begins
  ↓
Read returns B
```

Because the read began after Write B completed, returning A would violate linearizability.

Linearizability is stronger than sequential consistency because it preserves real-time ordering between non-overlapping operations.

Typical use cases include:

- leader election
- distributed locks
- cluster membership
- configuration state
- fencing token generation
- metadata required for safe orchestration

Systems such as etcd and Consul expose linearizable operations for these use cases.

---

## 2.5 Sequential Consistency

Sequential consistency guarantees that all operations appear in one total order that is consistent with the program order of each individual client.

Unlike linearizability, that total order does not have to respect real-time ordering across clients.

This distinction matters:

- Linearizability constrains observable order using wall-clock precedence between completed operations.
- Sequential consistency constrains order using per-client program order, but may reorder concurrent operations globally.

Sequential consistency is often sufficient for systems where users need a coherent history but do not require strict real-time visibility.

---

## 2.6 CAP Theorem

CAP does not mean that a system casually chooses any two properties at design time.

The useful interpretation is:

> When a network partition prevents some nodes from communicating, a distributed system must choose whether to preserve consistency or availability for the affected operation.

The three properties are:

- **Consistency:** every read receives the latest accepted write or an error.
- **Availability:** every request to a non-failed node receives a non-error response, without guaranteeing that it contains the latest write.
- **Partition tolerance:** the system continues operating despite dropped or indefinitely delayed messages between nodes.

Partition tolerance is not an optional feature in a real distributed system. Networks can partition.

Therefore, during a partition, the practical trade-off is:

```text
             Network partition
                  /      \
                 /        \
      Preserve consistency  Preserve availability
```

### CP Behavior

A CP system rejects or blocks operations when it cannot prove that they are safe.

For example, if an etcd cluster loses quorum, it stops accepting writes.

The system sacrifices availability to avoid divergent authoritative histories.

This is appropriate for:

- coordination state
- locks
- leader election
- service discovery metadata
- security policy
- allocation of unique ownership

### AP Behavior

An AP system continues serving requests on both sides of a partition, accepting that conflicting versions may need reconciliation later.

This is appropriate when:

- temporary divergence is acceptable
- writes must remain available
- conflicts have a defined merge policy
- the business can tolerate delayed convergence

Examples include shopping-cart-like workloads, social reactions, telemetry ingestion, and some catalog metadata.

### Why “CA” Is Misleading

A single-node database can provide consistency and availability while no partition exists, but once a system spans failure domains, it cannot guarantee that partitions will never happen.

Calling a distributed system “CA” usually avoids the exact failure mode CAP asks engineers to reason about.

---

## 2.7 PACELC

CAP focuses on partitions, but most production time is spent without a partition.

PACELC expands the model:

```text
If there is a Partition:
    choose Availability or Consistency
Else:
    choose Latency or Consistency
```

This is often written as:

```text
P -> A/C
E -> L/C
```

The first trade-off is exercised during partition.

The second trade-off is exercised during normal operation.

### Cross-Region Example

A service writes in Virginia and synchronously waits for replication in Europe.

Option A:

- return only after the remote acknowledgement
- higher latency
- stronger durability and consistency guarantees

Option B:

- return after the local write
- lower latency
- remote replicas may temporarily lag

That is PACELC in practice.

### Why PACELC Is Operationally Useful

It forces architecture reviews to ask two different questions:

1. What happens when regions cannot communicate?
2. What latency are we willing to pay when everything is healthy?

A design that says “we use quorum, therefore we are consistent” is incomplete unless it also defines:

- quorum scope
- acknowledgement path
- replication mode
- read path
- failover behavior
- stale-read tolerance
- conflict handling

---

## 2.8 Business Invariants Before Technology

Technology does not determine consistency requirements.

Business invariants do.

Examples of hard invariants:

- A payment must not be captured twice.
- Money must not be created or lost.
- One seat must not be sold to two customers.
- A username must remain unique.
- One active leader must own a shard at a time.

Examples of softer requirements:

- Social-media like counts may lag.
- Analytics may be delayed.
- Search indexes may be temporarily stale.
- Recommendations may use slightly old user features.

A Staff engineer begins with the invariant and chooses the weakest consistency model that still preserves it.

That usually produces a better system than defaulting to either global strong consistency or uncontrolled eventual consistency.

### Invariant Decomposition

For each workflow, ask:

1. What must never happen?
2. What may temporarily happen?
3. What can be repaired asynchronously?
4. Who owns the authoritative state?
5. What evidence proves an operation committed?
6. What happens when the result is ambiguous?
7. What is the reconciliation mechanism?

### Example: Payment Processing

Hard invariants:

- one logical purchase maps to at most one successful capture
- an accepted capture is durably recorded
- retries do not create duplicate captures

Possible implementation choices:

- idempotency key per logical purchase
- unique constraint on the idempotency key
- state machine for payment lifecycle
- transactional write of payment state and outbound event
- reconciliation against the payment provider

The consistency mechanism is selected to preserve the invariant, not because a specific database is fashionable.

### Example: Inventory

A globally consistent stock counter may be too expensive for every product and region.

Alternatives include:

- regional inventory allocation
- reservation with expiration
- escrow-style counters
- oversell buffer for low-risk products
- synchronous consistency only at checkout

The right answer depends on the cost of overselling, the value of latency, and the ability to compensate.

---

## 2.9 Transaction Boundaries

A transaction boundary defines the state that must change atomically.

Inside one relational database, this boundary may be one ACID transaction.

Across services, queues, caches, and external providers, there is usually no single atomic transaction.

That means the architecture must explicitly handle partial completion.

### Local Transaction

```text
BEGIN
  update order
  insert payment attempt
  insert outbox event
COMMIT
```

All three changes either commit or roll back together.

### Distributed Workflow

```text
Order service
  ↓
Payment provider
  ↓
Inventory service
  ↓
Notification service
```

These operations cannot generally be committed as one atomic unit.

The workflow therefore needs:

- idempotency
- durable state transitions
- retries
- compensating actions
- timeout handling
- reconciliation
- observability for stuck states

### The Staff-Level Rule

Do not draw a distributed workflow as a clean sequence of arrows and assume every step succeeds exactly once.

For every arrow, define:

- timeout
- retry owner
- idempotency key
- duplicate behavior
- out-of-order behavior
- persistence point
- compensation path
- operator visibility

---

## 2.10 Design Review Checklist

Before approving a distributed stateful design, ask:

- Which business invariants require strong coordination?
- Which reads may be stale, and for how long?
- Does the system require read-your-writes behavior?
- What happens during a network partition?
- Which side continues serving writes?
- How are conflicts detected and resolved?
- Does failover risk split brain?
- What is the source of truth?
- Are cache and search indexes derived or authoritative?
- How are ambiguous outcomes reconciled?
- What is the transaction boundary?
- Which operations are idempotent?
- Which data can be repaired asynchronously?
- What consistency does the user actually observe?
- What latency is paid for stronger guarantees?

---

## 2.11 Staff and Principal Interview Drills

### Question 1

Your database uses asynchronous cross-region replication. The primary region fails immediately after returning success to a client, before the write reaches the replica. What guarantees were actually provided?

A strong answer should discuss:

- local durability versus regional durability
- acknowledged-write loss
- recovery point objective
- failover policy
- whether the API overstated its guarantee
- reconciliation options

### Question 2

A social application requires users to see their own profile update immediately, but global propagation may take seconds. Which consistency model fits?

Expected direction:

- read-your-writes consistency
- session routing or version tokens
- asynchronous global replication

### Question 3

Two regions must accept cart updates during a partition. What must the design define before claiming AP behavior is safe?

Expected direction:

- conflict representation
- merge semantics
- item identity
- quantity reconciliation
- delete versus add conflicts
- convergence guarantees

### Question 4

Why is linearizability useful for leader election but often unnecessary for analytics?

Expected direction:

- leader election is a safety-critical ownership decision
- analytics tolerates lag and recomputation
- the cost of stale data differs by workload

### Question 5

A system claims exactly-once processing because the queue removes each message after acknowledgement. Challenge that claim.

Expected direction:

- consumer may apply side effect and crash before acknowledgement
- broker may redeliver
- external side effects require idempotency
- exactly-once is an end-to-end property, not a broker setting

---

## 2.12 Hands-On Labs

### Lab 1 — Observe Stale Reads

1. Run a primary and asynchronous replica.
2. Introduce artificial replication delay.
3. Write to the primary.
4. Immediately read from the replica.
5. Measure the stale-read window.
6. Add read-your-writes routing and compare behavior.

### Lab 2 — Partition a Three-Node Quorum System

1. Start a three-node etcd or Consul cluster.
2. Isolate one node.
3. Confirm the majority continues processing writes.
4. Isolate two nodes from one another.
5. Observe that no isolated minority can safely commit.
6. Record the operational signals indicating quorum loss.

### Lab 3 — Demonstrate Ambiguous Success

1. Build an HTTP endpoint that commits a database write.
2. Delay the response after commit.
3. Force the client timeout before the response arrives.
4. Retry the request.
5. Observe duplicate state without an idempotency key.
6. Add a unique idempotency key and verify safe replay.

### Lab 4 — Compare Linearizable and Stale Reads

1. Write a key to a consensus-backed store.
2. Read using a linearizable path.
3. Read using a serializable or stale path where supported.
4. Measure latency differences under cross-zone delay.
5. Explain which workloads justify the stronger read.

### Lab 5 — Model a Transaction Boundary

Design an order workflow spanning:

- order database
- payment provider
- inventory service
- notification queue

For each edge, document:

- commit point
- timeout
- retry policy
- idempotency mechanism
- compensation
- reconciliation job
- alerting signal

---

## 2.13 Chapter Summary

The core lessons are:

1. Distributed systems do not have one global clock or one universally visible state.
2. Consistency is a spectrum, not a binary property.
3. Linearizability preserves real-time ordering and is valuable for coordination-sensitive state.
4. CAP describes the choice forced by a partition, not a casual “pick two” menu.
5. PACELC adds the latency-versus-consistency trade-off during normal operation.
6. Business invariants should drive consistency choices.
7. Transaction boundaries must be explicit, especially across services.
8. Ambiguous outcomes, retries, duplicates, and partial completion are normal—not exceptional.

The next chapter expands these foundations into replication, quorum mathematics, split-brain prevention, leader election, leases, and fencing tokens.
