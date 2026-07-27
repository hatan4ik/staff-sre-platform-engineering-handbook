# Kubernetes Node Lifecycle, Fencing, and Repair

This module owns reusable node-health and repair principles across self-managed Kubernetes, EKS, AKS, GKE, and private platforms.

## Canonical chapter

1. [Node failure detection, fencing, drain, repair, and replacement](failure-fencing-repair.md)

The chapter covers:

- Unit failure versus node failure.
- Node conditions, leases, taints, and workload impact.
- systemd, kubelet, container runtime, CNI, CSI, kernel, disk, and network evidence.
- Bounded restart, cordon, drain, reboot, quarantine, and hard replacement.
- Traffic, storage, identity, and writer fencing.
- PDB limitations and involuntary failure.
- Immutable repair versus SSH patching.
- Repair state machines, fleet circuit breakers, and concurrency limits.
- Rollout correlation, bad-image containment, and last-known-good replacement.
- Node-repair SLIs, acceptance tests, and adversarial interview questions.

## Ownership rule

Reusable node-health, fencing, drain, replacement, repair-controller, and fleet-safety material belongs here. Cloud tracks should add only provider-specific node managers, agents, instance lifecycle events, quotas, and commands.
