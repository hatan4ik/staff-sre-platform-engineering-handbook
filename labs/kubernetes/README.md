# Executable Kubernetes Reliability Labs

These labs turn Kubernetes lifecycle, runtime, scheduling, and repair concepts into deterministic failure exercises.

## Current lab

1. [Node repair state machine and fleet circuit breakers](01-node-repair-state-machine/README.md)

The current lab uses Python's standard library and creates no cluster or cloud resources.

## Planned labs

- Container restarts, OOM, eviction, and previous-log evidence.
- Node-image qualification and canary promotion.
- Scheduler constraints and unschedulable pods.
- EndpointSlice and traffic-admission propagation.
- Probe-safe startup and graceful termination.
- API server LIST/WATCH and controller overload.
- Stateful writer fencing and volume reattachment.

## Method

1. Define the workload and fleet safety invariants.
2. Inject one bounded failure signature.
3. Preserve evidence before repair.
4. Apply one state-machine transition.
5. Enforce per-zone and fleet repair limits.
6. Trip a circuit breaker for systemic patterns.
7. Verify replacement capacity and writer fencing.
8. Convert the experiment into a Staff/Principal interview answer.

## Ownership rule

Labs must test Kubernetes invariants and controller behavior rather than only demonstrate commands. Every exercise should include safe positive cases, dangerous failure cases, and explicit stop conditions.
