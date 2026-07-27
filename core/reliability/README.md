# Reliability Engineering, SLOs, Capacity, DR, and Chaos

This module owns reusable reliability principles shared by every interview track.

## Canonical modules

- [`slo/`](slo/) — user-centered SLIs, SLOs, error budgets, burn rates, ownership, and governance.

Planned modules:

- Business-aware probes and graceful degradation.
- Capacity, overload, and admission control.
- Blast-radius design and fault containment.
- Multi-region disaster recovery and failback.
- Chaos engineering and game-day governance.
- Dependency reliability and resilience contracts.
- Retry budgets, deadlines, and load shedding.

Related foundations:

- [`../incident-response/`](../incident-response/) — incident isolation, cohorts, and postmortems.
- [`../observability/`](../observability/) — telemetry and diagnostic evidence.
- [`../distributed-systems/`](../distributed-systems/) — partial failure, replication, queues, and consistency.
- [`../kubernetes/autoscaling/`](../kubernetes/autoscaling/) — capacity-realization control loops.

## Ownership rule

Reusable SLO, error-budget, overload, capacity, graceful-degradation, blast-radius, disaster-recovery, and chaos principles belong here. Track adapters should add only product semantics, cloud mechanisms, safety constraints, and interview context.
