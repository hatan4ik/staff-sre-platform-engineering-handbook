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

### Infrastructure as code and Terraform governance

Start with [`core/infrastructure-as-code/README.md`](core/infrastructure-as-code/README.md).

- [`terraform-state-integrity.md`](core/infrastructure-as-code/terraform-state-integrity.md) — state bindings, locking, force-unlock safety, partial-apply recovery, current S3 lock files, legacy DynamoDB migration, state boundaries, CI concurrency, drift, and break-glass governance.
- [`tool-selection-and-governance.md`](core/infrastructure-as-code/tool-selection-and-governance.md) — declarative, cloud-native, programming-language, GitOps, configuration-management, and control-plane tool choices; one-owner rules; policy; promotion; rollback; and migration.

### GitOps and progressive delivery

Start with [`core/delivery-gitops/README.md`](core/delivery-gitops/README.md).

- [`gitops-progressive-delivery.md`](core/delivery-gitops/gitops-progressive-delivery.md) — build, promotion, and reconciliation boundaries; resource ownership; CRDs; pruning; secrets; multi-cluster rollout; canary analysis; rollback; and Argo CD/Flux mappings.

### Workload identity, federation, and authorization

Start with [`core/security/identity/README.md`](core/security/identity/README.md).

- [`workload-identity-federation.md`](core/security/identity/workload-identity-federation.md) — projected ServiceAccount tokens, audience restriction, EKS Pod Identity and IRSA, Microsoft Entra Workload ID, GKE Workload Identity Federation, cross-cloud token exchange, SPIFFE/SPIRE, node-role protection, credential-provider chains, rotation, failure behavior, and negative testing.

### Kubernetes autoscaling and capacity realization

Start with [`core/kubernetes/autoscaling/README.md`](core/kubernetes/autoscaling/README.md).

- [`control-loops-capacity-realization.md`](core/kubernetes/autoscaling/control-loops-capacity-realization.md) — HPA, VPA, KEDA, scheduler and node-supply loops; resource-request semantics; Cluster Autoscaler and Karpenter; Spot and durable baseline capacity; topology, disruption, end-to-end capacity-realization timelines, incident workflows, and validation.

### Service mesh, Envoy, Istio, and xDS

Start with [`core/service-mesh/README.md`](core/service-mesh/README.md).

- [`fine-grained-service-discovery.md`](core/service-mesh/fine-grained-service-discovery.md) — registry, control-plane and data-plane separation, xDS, configuration fan-out, dependency scoping, sidecar and Ambient trade-offs, multi-cluster failure domains, convergence, and last-known-good behavior.

### eBPF and runtime security

- [`core/ebpf-security/cilium-hubble-falco-tetragon.md`](core/ebpf-security/cilium-hubble-falco-tetragon.md) — Linux hook selection, Cilium dataplane and policy, Hubble evidence, Falco detection, Tetragon enforcement, failure modes, and safe migration.

## Executable labs

### Distributed-systems labs

Start with [`labs/distributed-systems/README.md`](labs/distributed-systems/README.md).

These runnable labs use Python's standard library and include automated tests:

1. [`01-retry-amplification`](labs/distributed-systems/01-retry-amplification/README.md) — layered retries, retry ownership, backoff, jitter, and retry-wave evidence.
2. [`02-transactional-outbox`](labs/distributed-systems/02-transactional-outbox/README.md) — atomic business state plus outbox insertion, relay crash, duplicate delivery, and idempotent consumption.
3. [`03-fencing-tokens`](labs/distributed-systems/03-fencing-tokens/README.md) — lease expiry, paused former owners, stale writes, and resource-enforced fencing.
4. [`04-cache-races`](labs/distributed-systems/04-cache-races/README.md) — stale-fill resurrection, version fences, cache stampedes, and single-flight control.
5. [`05-shard-rebalancing`](labs/distributed-systems/05-shard-rebalancing/README.md) — virtual shards, copy/catch-up/cutover/cleanup, ownership epochs, stale-router rejection, hot-shard detection, and tenant skew.
6. [`06-queue-redelivery`](labs/distributed-systems/06-queue-redelivery/README.md) — crash-before-ack duplicates, consumer inbox idempotency, visibility timeouts, DLQs, and ordered-group blocking.

GitHub Actions compiles these lab programs, runs invariant tests, and executes smoke scenarios on every relevant push or pull request.

### AWS and EKS incident labs

Start with [`labs/aws/README.md`](labs/aws/README.md).

1. [`01-cohort-deployment-failure`](labs/aws/01-cohort-deployment-failure/README.md) — a successful rollout where only the new version and one request cohort fail.
2. [`02-terraform-partial-apply`](labs/aws/02-terraform-partial-apply/README.md) — a safe local partial apply followed by configuration/state/reality reconciliation.
3. [`03-kubernetes-restart-evidence`](labs/aws/03-kubernetes-restart-evidence/README.md) — OOM and sidecar restarts while application health checks appear successful.

The first AWS lab set is designed for a disposable Kubernetes environment and a local Terraform workspace. It does not require an AWS account. Automated validation for these manifests and exercises is an active follow-up.

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

A track must not become a second conflicting Linux, Kubernetes, Terraform, service-mesh, observability, reliability, security, autoscaling, or distributed-systems source of truth. Transitional deep chapters are migrated into `core/` as canonical coverage is completed.

## Existing interview tracks

- [Netflix-scale DevOps interview track](https://github.com/hatan4ik/netflix-devops-interview)
- [Tesla SRE interview track](https://github.com/hatan4ik/tesla-sre-interview)
- [`tracks/aws/README.md`](tracks/aws/README.md) — AWS DevOps, Amazon EKS, GitOps, Terraform, incident-response, and system-design interview track.

## AWS track

All 18 AWS source questions now have Staff/Principal-level chapters across infrastructure, incidents, and system design. Round 1 includes:

1. Multi-AZ EKS at hyperscale
2. Terraform plus Argo CD or Flux GitOps
3. Multi-account and multi-Region Terraform state
4. EKS security and workload identity
5. Terraform versus CloudFormation and AWS-native automation
6. Capacity planning with ASGs, Karpenter, Cluster Autoscaler, and Spot

The track also includes a board review, spoken-answer drills, a mock-interview scorecard, a personal-story matrix, an official-source index, and executable incident labs.

## Coordination

- [`curriculum-map.md`](curriculum-map.md) assigns canonical ownership and maps track scenarios to shared prerequisites.
- [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) records completed migrations, transitional duplicates, and upcoming work.

## Active delivery pipeline

- Extract reusable request-path, cohort-debugging, and evidence-beyond-dashboards chapters from AWS Round 2.
- Build canonical Kubernetes runtime, node-failure, fencing, repair, and image-qualification chapters and labs.
- Build SLO, error-budget, incident-command, postmortem, disaster-recovery, and chaos modules.
- Expand Envoy request-path, mTLS, DNS-capture, and multi-cluster service-mesh chapters and labs.
- Automate validation for Terraform recovery, GitOps, workload identity, autoscaling, and AWS/EKS incident labs.
- Replace duplicated Netflix, Tesla, and AWS theory with concise interview adapters after parity review.

## Core principle

> Write engineering fundamentals once, specialize only the business context, and ensure no interview track drifts into a second conflicting source of truth.
