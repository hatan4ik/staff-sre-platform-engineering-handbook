# Kubernetes Internals, Reliability, and Platform Operations

This module owns reusable Kubernetes foundations shared by AWS, Netflix, Tesla, and future platform tracks.

## Canonical modules and chapters

- [`control-plane/api-server-etcd-list-watch-admission.md`](control-plane/api-server-etcd-list-watch-admission.md) — API-server request paths, authentication, authorization, admission, API Priority and Fairness, etcd, LIST/WATCH behavior, controller queues, scaling, SLOs, and incident response.
- [`autoscaling/`](autoscaling/) — HPA, VPA, KEDA, scheduling, node supply, disruption, and end-to-end capacity realization.
- [`node-lifecycle/`](node-lifecycle/) — node health, systemd and runtime failures, fencing, cordon, drain, replacement, and repair automation.
- [`node-images/qualification-promotion-rollback.md`](node-images/qualification-promotion-rollback.md) — immutable image contracts, provenance, boot and conformance testing, workload compatibility, canary pools, rollout rings, rollback, and fleet governance.
- [`runtime-debugging.md`](runtime-debugging.md) — container restart, pod replacement, OOM, eviction, probes, PID 1, kubelet, runtime, configuration, and controller evidence.

## Remaining expansion areas

- Scheduler internals and placement diagnostics.
- Service, EndpointSlice, kube-proxy, CNI, DNS, ingress, and Gateway request paths.
- Persistent volumes, CSI, attach/detach, topology, and stateful recovery.
- Probe design and graceful shutdown integrated with overload admission.
- Disposable-cluster conformance suites for control-plane and node-image failure modes.

Related foundations:

- [`../linux/`](../linux/) — cgroups, namespaces, networking, memory, storage, and kernel evidence.
- [`../incident-response/`](../incident-response/) — request-path, cohort, and postmortem methods.
- [`../observability/`](../observability/) — evidence systems and diagnostic telemetry.
- [`../reliability/`](../reliability/) — SLOs, capacity, DR, overload, and chaos.

## Core principle

```text
Kubernetes desired state
      |
      v
API server, storage, controllers, and scheduler
      |
      v
node, runtime, network, and storage mechanisms
      |
      v
pod readiness and traffic admission
      |
      v
user-visible reliability
```

A healthy control-plane object does not prove the underlying process, node, network, storage, or business transaction is healthy. Conversely, healthy application traffic does not prove the control plane can deploy, scale, repair, or fail over safely.

## Ownership rule

Reusable Kubernetes API, controller, scheduling, node, image, runtime, network, storage, probe, and workload-lifecycle material belongs here. Cloud tracks should add only managed-service boundaries, provider-specific controllers, commands, quotas, and failure behavior.
