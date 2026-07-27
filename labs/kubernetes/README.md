# Executable Kubernetes Reliability Labs

These labs turn Kubernetes lifecycle, runtime, scheduling, networking, probes, and repair concepts into deterministic and disposable-cluster failure exercises.

## Current labs

1. [Node repair state machine and fleet circuit breakers](01-node-repair-state-machine/README.md) — dependency-free simulation of fencing, repair transitions, per-zone limits, and systemic-failure circuit breakers.
2. [Disposable Kind scheduling, DNS, probe, and drain conformance](02-kind-conformance/README.md) — real Kubernetes validation of `FailedScheduling`, Service DNS, EndpointSlice readiness propagation, liveness restart, graceful drain, replacement, and PDB behavior.

## Planned lab expansion

- Node-image qualification and canary promotion.
- API-server LIST/WATCH and admission overload.
- NetworkPolicy, MTU, dual-stack, and Gateway routing.
- CSI provisioning, stale attachment, writer fencing, and snapshot restore.
- Multi-cluster and service-mesh discovery failure.

## Method

1. Define the workload and fleet safety invariants.
2. Inject one bounded failure signature.
3. Preserve evidence before repair.
4. Apply one state-machine or Kubernetes control-loop transition.
5. Enforce per-zone and fleet repair limits.
6. Trip a circuit breaker for systemic patterns.
7. Verify replacement capacity, traffic admission, and writer fencing.
8. Convert the experiment into a Staff/Principal interview answer.

## Ownership rule

Labs must test Kubernetes invariants and controller behavior rather than only demonstrate commands. Every exercise should include safe positive cases, dangerous failure cases, explicit stop conditions, and user- or workload-level recovery evidence.
