# Distributed Systems for Staff and Principal Engineers

This module is the canonical shared curriculum for reasoning about systems that span processes, hosts, zones, regions, networks, storage engines, and organizational boundaries.

The goal is not to memorize CAP, quorum formulas, or consensus vocabulary. The goal is to make correct architectural decisions when clocks drift, packets disappear, replicas lag, dependencies fail partially, and retries amplify load.

## Learning outcomes

By completing this module, you should be able to:

- Explain why partial failure is the defining property of distributed systems.
- Separate safety, liveness, durability, availability, and consistency requirements.
- Choose consistency and replication models based on business invariants rather than fashion.
- Design idempotent APIs, bounded retries, backpressure, and overload protection.
- Reason about leader election, quorum, fencing, split brain, and stale ownership.
- Diagnose retry storms, hot partitions, replication lag, clock issues, and cascading failures.
- Explain trade-offs clearly at Staff/Principal interview depth.

## Chapter map

1. [Foundations: partial failure, time, ordering, retries, and backpressure](01-foundations-failure-time-retries.md)
2. Consistency models, invariants, CAP, PACELC, and transaction boundaries — next
3. Replication, quorum, leader-based systems, and failover — planned
4. Consensus, leases, fencing tokens, and split-brain prevention — planned
5. Partitioning, sharding, rebalancing, hot keys, and skew — planned
6. Messaging, streams, delivery semantics, and event-driven systems — planned
7. Caching, invalidation, CDNs, and consistency at the edge — planned
8. Resilience patterns, overload control, and cascading-failure containment — planned
9. Distributed observability and incident labs — planned
10. Staff/Principal system-design drills — planned

## Core mental model

```text
business invariant
      |
      v
request crosses a process boundary
      |
      +--> network delay, loss, duplication, reordering
      +--> independent failure and restart
      +--> stale state and replica lag
      +--> clock uncertainty
      +--> retries and duplicate effects
      +--> overload and queue growth
      |
      v
safety + liveness + operability decision
```

Every design should answer five questions:

1. **What must never happen?** This is the safety invariant.
2. **What must eventually happen?** This is the liveness requirement.
3. **What happens during partitions or dependency loss?** This is the availability policy.
4. **How are duplicates, reordering, and retries handled?** This is the side-effect model.
5. **How will operators prove what happened?** This is the observability and recovery model.

## Interview answer pattern

For any distributed-systems question:

1. State the invariant.
2. Identify failure domains and trust boundaries.
3. Define consistency and availability requirements.
4. Describe the normal path.
5. Describe partition, timeout, duplicate, and overload behavior.
6. Explain recovery and reconciliation.
7. Name the telemetry that proves correctness.
8. Discuss trade-offs and alternatives.

The Staff-level bar is not naming a pattern. It is showing that the pattern preserves the business invariant under realistic failure.