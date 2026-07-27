# Kubernetes Internals, Reliability, and Platform Operations

This module owns reusable Kubernetes foundations shared by AWS, Netflix, Tesla, and future platform tracks.

## Canonical modules and chapters

- [`autoscaling/`](autoscaling/) — HPA, VPA, KEDA, scheduling, node supply, disruption, and end-to-end capacity realization.
- [`node-lifecycle/`](node-lifecycle/) — node health, systemd and runtime failures, fencing, cordon, drain, replacement, and repair automation.
- [`runtime-debugging.md`](runtime-debugging.md) — container restart, pod replacement, OOM, eviction, probes, PID 1, kubelet, runtime, configuration, and controller evidence.

Planned additions:

- Kubernetes API server, etcd, LIST/WATCH, admission, and controller scaling.
- Scheduler internals and placement diagnostics.
- Service, EndpointSlice, kube-proxy, CNI, DNS, ingress, and Gateway request paths.
- Persistent volumes, CSI, attach/detach, topology, and stateful recovery.
- Probe design, graceful shutdown, and overload admission.
- Node-image construction, qualification, promotion, and rollback.
- Multi-cluster and fleet control planes.

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
controllers and scheduler
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

A healthy control-plane object does not prove the underlying process, node, network, storage, or business transaction is healthy.

## Ownership rule

Reusable Kubernetes API, controller, scheduling, node, runtime, network, storage, probe, and workload-lifecycle material belongs here. Cloud tracks should add only managed-service boundaries, provider-specific controllers, commands, quotas, and failure behavior.
