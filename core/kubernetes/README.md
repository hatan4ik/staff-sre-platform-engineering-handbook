# Kubernetes Internals, Reliability, and Platform Operations

This module owns reusable Kubernetes foundations shared by AWS, Netflix, Tesla, and future platform tracks.

## Canonical modules and chapters

- [`control-plane/api-server-etcd-list-watch-admission.md`](control-plane/api-server-etcd-list-watch-admission.md) — API-server request paths, authentication, authorization, admission, API Priority and Fairness, etcd, LIST/WATCH behavior, controller queues, scaling, SLOs, and incident response.
- [`scheduling/scheduler-placement-diagnostics.md`](scheduling/scheduler-placement-diagnostics.md) — scheduler queues and plugins, requests, taints, affinity, topology spread, volume and device constraints, preemption, autoscaler handoff, evidence, and placement SLOs.
- [`networking/service-dns-ingress-gateway-request-path.md`](networking/service-dns-ingress-gateway-request-path.md) — Services, EndpointSlices, kube-proxy/eBPF dataplanes, CNI, DNS, NetworkPolicy, Ingress, Gateway API, TLS, dual stack, MTU, conntrack, and request-path debugging.
- [`storage/csi-stateful-recovery.md`](storage/csi-stateful-recovery.md) — PVC/PV/StorageClass, CSI provisioning, attach/detach, mount, topology, snapshots, backups, writer fencing, restore, and stateful recovery.
- [`autoscaling/`](autoscaling/) — HPA, VPA, KEDA, scheduling, node supply, disruption, and end-to-end capacity realization.
- [`node-lifecycle/`](node-lifecycle/) — node health, systemd and runtime failures, fencing, cordon, drain, replacement, and repair automation.
- [`node-images/qualification-promotion-rollback.md`](node-images/qualification-promotion-rollback.md) — immutable image contracts, provenance, boot and conformance testing, workload compatibility, canary pools, rollout rings, rollback, and fleet governance.
- [`runtime-debugging.md`](runtime-debugging.md) — container restart, pod replacement, OOM, eviction, probes, PID 1, kubelet, runtime, configuration, and controller evidence.

## Remaining expansion areas

- Business-aware probe design, startup safety, graceful shutdown, and traffic drain as a dedicated chapter.
- Multi-cluster workload and control-plane fleet operations beyond node and platform lifecycle modules.
- Disposable-cluster conformance suites covering control-plane, scheduling, networking, storage, node-image, and probe failure modes.

## Related foundations

- [`../linux/`](../linux/) — cgroups, namespaces, networking, memory, storage, and kernel evidence.
- [`../incident-response/`](../incident-response/) — request-path, cohort, and postmortem methods.
- [`../observability/`](../observability/) — evidence systems and diagnostic telemetry.
- [`../reliability/`](../reliability/) — SLOs, capacity, DR, overload, and chaos.
- [`../service-mesh/`](../service-mesh/) — proxy request paths, service identity, DNS capture, gateways, and multi-cluster behavior.

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
