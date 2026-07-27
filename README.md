# Staff SRE & Platform Engineering Handbook

A canonical, company-neutral engineering handbook for Staff/Principal SRE, Platform Engineering, DevOps, Cloud Architecture, and technical-leadership interview preparation.

> This repository contains independent educational material. It does not claim knowledge of any company's private architecture or interview process.

## Why this repository exists

The Netflix-scale, Tesla SRE, and AWS DevOps interview tracks share most engineering foundations: Linux, Kubernetes, networking, observability, incident response, Terraform, security, autoscaling, service mesh, multi-region design, distributed systems, SLOs, and leadership.

Those foundations are written **once here**. Company or platform tracks contain domain-specific scenarios, answer adapters, mock interviews, and operating context.

```text
Canonical shared handbook
        |
        +-- Netflix interview adapters
        |
        +-- Tesla interview adapters
        |
        +-- AWS / Amazon EKS interview adapters
        |
        +-- future company or role tracks
```

## Repository model

```text
core/                       Canonical technical chapters
tracks/netflix/             Netflix/media-delivery question adapters
tracks/tesla/               Tesla/connected-vehicle question adapters
tracks/aws/                 AWS and Amazon EKS question adapters
labs/                       Executable failure experiments
playbooks/                  Incident and architecture answer frameworks
diagrams/                   Shared diagrams and whiteboard models
curriculum-map.md            Question-to-core-chapter mapping
MIGRATION_PLAN.md            Consolidation status and source ownership
```

## Canonical modules

### Linux internals and production debugging

Start with [`core/linux/README.md`](core/linux/README.md).

1. [`01-architecture-boot-syscalls.md`](core/linux/01-architecture-boot-syscalls.md) — kernel architecture, boot, PID 1, systemd, syscalls, faults, interrupts, and crash evidence.
2. [`02-processes-scheduler.md`](core/linux/02-processes-scheduler.md) — tasks, scheduling, cgroup CPU, interrupts, load, affinity, and latency.
3. [`03-memory.md`](core/linux/03-memory.md) — virtual memory, page cache, NUMA, reclaim, PSI, cgroup memory, and OOM.
4. [`04-storage-io.md`](core/linux/04-storage-io.md) — VFS, durability, filesystems, block queues, NVMe, capacity, and tail latency.
5. [`05-networking-containers-security.md`](core/linux/05-networking-containers-security.md) — networking, namespaces, cgroups, containers, and host security.
6. [`06-observability-debugging.md`](core/linux/06-observability-debugging.md) — observability, profiling, eBPF, and production debugging.
7. [`07-linux-incident-labs.md`](core/linux/07-linux-incident-labs.md) — integrated production failure scenarios and interview labs.

### Distributed systems

Start with [`core/distributed-systems/README.md`](core/distributed-systems/README.md).

The ten-chapter module covers:

- partial failure, time, ordering, deadlines, retries, idempotency, and backpressure
- consistency models, CAP, PACELC, invariants, and transaction boundaries
- replication, quorum, failover, consensus, leases, and fencing
- partitioning, sharding, rebalancing, hot keys, and skew
- messaging, streams, delivery semantics, outbox/inbox patterns, and sagas
- caching, invalidation, CDNs, and edge consistency
- resilience, overload control, and cascading-failure containment
- distributed observability, incident labs, and Staff/Principal design drills

### eBPF and runtime security

- [`core/ebpf-security/cilium-hubble-falco-tetragon.md`](core/ebpf-security/cilium-hubble-falco-tetragon.md) — Linux hook selection, Cilium dataplane and policy, Hubble evidence, Falco detection, Tetragon enforcement, failure modes, and safe migration.

## Executable labs

Start with [`labs/distributed-systems/README.md`](labs/distributed-systems/README.md).

Current runnable labs use Python's standard library and include automated tests:

1. [`01-retry-amplification`](labs/distributed-systems/01-retry-amplification/README.md) — layered retries, retry ownership, backoff, jitter, and retry-wave evidence.
2. [`02-transactional-outbox`](labs/distributed-systems/02-transactional-outbox/README.md) — atomic business state plus outbox insertion, relay crash, duplicate delivery, and idempotent consumption.
3. [`03-fencing-tokens`](labs/distributed-systems/03-fencing-tokens/README.md) — lease expiry, paused former owners, stale writes, and resource-enforced fencing.
4. [`04-cache-races`](labs/distributed-systems/04-cache-races/README.md) — stale-fill resurrection, version fences, cache stampedes, and single-flight control.

GitHub Actions compiles the lab programs, runs invariant tests, and executes smoke scenarios on every relevant push or pull request.

## Canonical ownership rule

A topic belongs in `core/` when it can answer questions for more than one company or role.

A track chapter should contain only:

1. Original company- or platform-style question.
2. Domain context and assumptions.
3. A concise interview answer.
4. Links to required core chapters.
5. Domain-specific failure modes and trade-offs.
6. Adversarial follow-ups.
7. Personal-story mapping.

A track must not become a second conflicting Linux, Kubernetes, Terraform, service-mesh, observability, reliability, or distributed-systems source of truth. Transitional deep chapters are migrated into `core/` as canonical coverage is completed.

## Existing interview tracks

- [Netflix-scale DevOps interview track](https://github.com/hatan4ik/netflix-devops-interview)
- [Tesla SRE interview track](https://github.com/hatan4ik/tesla-sre-interview)
- [`tracks/aws/README.md`](tracks/aws/README.md) — AWS DevOps, Amazon EKS, GitOps, Terraform, incident-response, and system-design interview track.

## AWS track

Round 1 contains six Staff/Principal-level chapters:

1. Multi-AZ EKS at hyperscale
2. Terraform plus Argo CD or Flux GitOps
3. Multi-account and multi-Region Terraform state
4. EKS security and workload identity
5. Terraform versus CloudFormation and AWS-native automation
6. Capacity planning with ASGs, Karpenter, Cluster Autoscaler, and Spot

## Coordination

- [`curriculum-map.md`](curriculum-map.md) assigns canonical ownership and maps track scenarios to shared prerequisites.
- [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) records completed migrations, transitional duplicates, and upcoming work.

## Active delivery pipeline

- Expand executable distributed-systems labs with network partitions, queue redelivery, sharding, and overload experiments.
- Build Kubernetes node-failure, fencing, repair, and image-qualification labs.
- Consolidate Kubernetes, Envoy, Istio, xDS, workload identity, and secrets chapters.
- Deepen Terraform state integrity, GitOps, EKS security, and autoscaling control-loop labs.
- Connect Tesla, Netflix, and AWS interview adapters back to canonical chapters and runnable exercises.

## Core principle

> Write engineering fundamentals once, specialize only the business context, and ensure no interview track drifts into a second conflicting source of truth.
