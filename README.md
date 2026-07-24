# Staff SRE & Platform Engineering Handbook

A canonical, company-neutral engineering handbook for Staff/Principal SRE, Platform Engineering, DevOps, Cloud Architecture, and technical-leadership interview preparation.

> This repository contains independent educational material. It does not claim knowledge of any company's private architecture or interview process.

## Why this repository exists

The Netflix-scale and Tesla SRE interview tracks share most engineering foundations: Linux, Kubernetes, networking, observability, incident response, Terraform, security, autoscaling, service mesh, multi-region design, SLOs, and leadership.

Those foundations are written **once here**. Company repositories contain only domain-specific scenarios, answer adapters, mock interviews, and business context.

```text
Canonical shared handbook
        |
        +-- Netflix interview adapters
        |
        +-- Tesla interview adapters
        |
        +-- future company or role tracks
```

## Repository model

```text
core/                       Canonical technical chapters
tracks/netflix/             Netflix/media-delivery question adapters
tracks/tesla/               Tesla/connected-vehicle question adapters
labs/                       Reusable hands-on exercises
playbooks/                  Incident and architecture answer frameworks
diagrams/                   Shared diagrams and whiteboard models
curriculum-map.md            Question-to-core-chapter mapping
MIGRATION_PLAN.md            Consolidation status and source ownership
```

## Canonical chapters now available

### Linux internals

- [`core/linux/README.md`](core/linux/README.md) — module map, debugging model, and interview method.
- [`core/linux/01-architecture-boot-syscalls.md`](core/linux/01-architecture-boot-syscalls.md) — kernel architecture, boot, PID 1, systemd, syscalls, faults, interrupts, and crash evidence.
- [`core/linux/02-processes-scheduler.md`](core/linux/02-processes-scheduler.md) — tasks, scheduling, cgroup CPU, interrupts, load, affinity, and latency.
- [`core/linux/03-memory.md`](core/linux/03-memory.md) — virtual memory, page cache, NUMA, reclaim, PSI, cgroup memory, and OOM.
- [`core/linux/04-storage-io.md`](core/linux/04-storage-io.md) — VFS, durability, filesystems, block queues, NVMe, capacity, and tail latency.

### eBPF and runtime security

- [`core/ebpf-security/cilium-hubble-falco-tetragon.md`](core/ebpf-security/cilium-hubble-falco-tetragon.md) — Linux hook selection, Cilium dataplane and policy, Hubble evidence, Falco detection, Tetragon enforcement, failure modes, and safe migration.

## Canonical ownership rule

A topic belongs in `core/` when it can answer questions for more than one company or role.

A track chapter should contain only:

1. Original company-style question.
2. Domain context and assumptions.
3. A concise interview answer.
4. Links to required core chapters.
5. Domain-specific failure modes and trade-offs.
6. Adversarial follow-ups.
7. Personal-story mapping.

A track must not reproduce an entire Linux, Kubernetes, Terraform, service-mesh, observability, or reliability textbook.

## Existing interview tracks

- [Netflix-scale DevOps interview track](https://github.com/hatan4ik/netflix-devops-interview)
- [Tesla SRE interview track](https://github.com/hatan4ik/tesla-sre-interview)

## Coordination

- [`curriculum-map.md`](curriculum-map.md) assigns canonical ownership and maps company scenarios to shared prerequisites.
- [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) records completed migrations, transitional duplicates, and the next chapters.

## Next canonical migrations

- Linux networking, namespaces, containers, cgroups, and host security.
- Linux observability, profiling, eBPF, and incident labs.
- Fine-grained service discovery with Kubernetes, Envoy, Istio, and xDS.
- Multi-cloud routing, workload identity, and secrets.
- Kubernetes node failure detection, fencing, repair, and node-image qualification.
- Business-aware probes, DNS failure analysis, Terraform state integrity, and autoscaling control loops.
- SLOs, incident response, multi-region resilience, chaos, and modernization ROI.

## Core principle

> Write engineering fundamentals once, specialize only the business context, and ensure no company-specific preparation drifts into a second conflicting source of truth.