# Disaster Recovery, Failover, and Failback

This module owns reusable disaster-recovery principles shared by every cloud and company track.

## Canonical chapter

1. [Multi-region disaster recovery, write fencing, failover, and failback](multi-region-failover.md)

The chapter covers:

- Business impact analysis, RTO, RPO, MTD, and service tiers.
- Active-active, active-passive, warm standby, and pilot-light trade-offs.
- Control-plane, data-plane, and data-path separation.
- Global traffic steering beyond DNS-only designs.
- Failover eligibility: health, capacity, dependencies, data, security, and observability.
- Write fencing, epochs, leases, quorum, and split-brain prevention.
- Replication lag, transaction loss, replay, duplicate handling, and reconciliation.
- Idempotent, evidence-driven failover state machines.
- Controlled failback, recovery debt, and re-protection.
- DR tests, game days, audit evidence, and adversarial interview questions.

## Ownership rule

Reusable RTO/RPO, data-recovery, routing, fencing, failover, failback, reconciliation, and DR-governance material belongs here. Cloud and company tracks should add only provider-specific services, product semantics, safety constraints, commands, and quotas.
