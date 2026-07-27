# Reliability Engineering, SLOs, Capacity, DR, and Chaos

This module owns reusable reliability principles shared by every interview track.

## Canonical modules

1. [`slo/`](slo/) — user-centered SLIs, SLOs, error budgets, burn rates, protected cohorts, release policy, and governance.
2. [`graceful-degradation-overload-blast-radius.md`](graceful-degradation-overload-blast-radius.md) — deadlines, retry budgets, concurrency limits, bounded queues, admission, load shedding, degraded modes, dependency contracts, cells, failover safety, and backlog recovery.
3. [`disaster-recovery/`](disaster-recovery/) — RTO/RPO, replication, write authority, fencing, routing, failover state machines, failback, reconciliation, and recovery evidence.
4. [`chaos-engineering-game-days.md`](chaos-engineering-game-days.md) — hypotheses, steady state, blast-radius controls, abort criteria, production safeguards, game-day roles, evidence, corrective actions, and maturity.

## Executable labs

- [`../../labs/reliability/01-error-budget/`](../../labs/reliability/01-error-budget/) — SLO and burn-policy decisions.
- [`../../labs/reliability/02-disaster-recovery-state-machine/`](../../labs/reliability/02-disaster-recovery-state-machine/) — guarded failover and failback transitions.
- [`../../labs/reliability/03-overload-blast-radius/`](../../labs/reliability/03-overload-blast-radius/) — retry amplification, priority admission, tenant fairness, failover headroom, and paced backlog recovery.

## Remaining expansion areas

- Business-aware probe and graceful-shutdown conformance on disposable clusters.
- Dependency-specific resilience contracts and automated policy validation.
- Capacity forecasting tied to deployment, failover, and maintenance windows.
- Production-grade chaos tooling integrations and experiment evidence pipelines.

## Related foundations

- [`../incident-response/`](../incident-response/) — incident isolation, cohorts, and postmortems.
- [`../observability/`](../observability/) — telemetry and diagnostic evidence.
- [`../distributed-systems/`](../distributed-systems/) — partial failure, replication, queues, and consistency.
- [`../kubernetes/autoscaling/`](../kubernetes/autoscaling/) — capacity-realization control loops.
- [`../service-mesh/`](../service-mesh/) — proxy deadlines, retries, circuit breakers, identity, discovery, and failover.

## Ownership rule

Reusable SLO, error-budget, overload, capacity, graceful-degradation, blast-radius, disaster-recovery, failback, and chaos principles belong here. Track adapters should add only product semantics, cloud mechanisms, safety constraints, and interview context.
