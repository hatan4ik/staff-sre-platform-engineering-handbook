# Staff SRE & Platform Engineering Handbook

A canonical, company-neutral engineering handbook for Staff/Principal SRE, Platform Engineering, DevOps, Cloud Architecture, and technical-leadership interview preparation.

> This repository contains independent educational material. It does not claim knowledge of any company's private architecture or interview process.

## Why this repository exists

The Netflix-scale, Tesla SRE, and AWS DevOps interview tracks share most engineering foundations: Linux, Kubernetes, networking, observability, incident response, Terraform, security, autoscaling, service mesh, multi-region design, distributed systems, SLOs, platform engineering, and leadership.

Those foundations are written **once here**. Company or platform tracks contain domain-specific scenarios, answer adapters, mock interviews, and operating context.

```text
Canonical shared handbook
        |
        +-- Netflix interview adapters
        +-- Tesla interview adapters
        +-- AWS / Amazon EKS interview adapters
        +-- future company or role tracks
```

## Repository model

```text
core/                       Canonical technical chapters
tracks/netflix/             Netflix/media-delivery question adapters
tracks/tesla/               Tesla/connected-vehicle question adapters
tracks/aws/                 AWS and Amazon EKS question adapters
labs/                       Executable failure and decision experiments
playbooks/                  Incident and architecture answer frameworks
diagrams/                   Shared diagrams and whiteboard models
curriculum-map.md            Question-to-core-chapter mapping
MIGRATION_PLAN.md            Consolidation status and source ownership
```

## Canonical modules

### Platform engineering

Start with [`core/platform-engineering/README.md`](core/platform-engineering/README.md).

The module covers:

1. platform as a product, golden paths, paved roads, and escape hatches;
2. Internal Developer Platform interfaces, orchestration, provisioning, delivery, runtime, and evidence planes;
3. software catalogs, developer portals, Backstage, templates, TechDocs, plugins, and metadata governance;
4. self-service infrastructure with outcome APIs, Terraform, Crossplane, and GitOps;
5. platform SLOs, adoption, developer experience, economics, support tiers, and operating model;
6. policy as code, native Kubernetes admission, Gatekeeper, Kyverno, exceptions, and staged enforcement;
7. Kubernetes multi-tenancy, namespace versus cluster boundaries, identity, network, storage, quota, and conformance;
8. multi-cluster fleet lifecycle, Cluster API, GitOps topology, rollout rings, compatibility, replacement, and decommissioning.

### Security: identity, secrets, and artifact trust

Start with [`core/security/README.md`](core/security/README.md).

- [`identity/workload-identity-federation.md`](core/security/identity/workload-identity-federation.md) — projected ServiceAccount tokens, audience restriction, EKS Pod Identity and IRSA, Microsoft Entra Workload ID, GKE Workload Identity Federation, cross-cloud exchange, SPIFFE/SPIRE, node-role protection, rotation, and negative testing.
- [`secrets/secret-delivery-rotation-kubernetes.md`](core/security/secrets/secret-delivery-rotation-kubernetes.md) — secret authority, dynamic credentials, direct retrieval, agents, CSI mounts, External Secrets Operator, Vault, Kubernetes Secret risk, rotation, reload, revocation, regional recovery, CI/CD, and Terraform state.
- [`software-supply-chain/artifact-trust-slsa-sigstore.md`](core/security/software-supply-chain/artifact-trust-slsa-sigstore.md) — digests, signatures, provenance, attestations, SBOMs, SLSA, Sigstore/Cosign, trusted builders, deployment verification, runtime inventory, and compromise response.

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

- partial failure, time, ordering, deadlines, retries, idempotency, and backpressure;
- consistency models, CAP, PACELC, invariants, and transaction boundaries;
- replication, quorum, failover, consensus, leases, and fencing;
- partitioning, sharding, rebalancing, hot keys, and skew;
- messaging, streams, delivery semantics, outbox/inbox patterns, and sagas;
- caching, invalidation, CDNs, and edge consistency;
- resilience, overload control, and cascading-failure containment;
- distributed observability, incident labs, and Staff/Principal design drills.

### Infrastructure as code and Terraform governance

Start with [`core/infrastructure-as-code/README.md`](core/infrastructure-as-code/README.md).

- [`terraform-state-integrity.md`](core/infrastructure-as-code/terraform-state-integrity.md) — state bindings, locking, partial-apply recovery, state boundaries, CI concurrency, drift, and break-glass governance.
- [`tool-selection-and-governance.md`](core/infrastructure-as-code/tool-selection-and-governance.md) — declarative, cloud-native, programming-language, GitOps, configuration-management, and control-plane choices; ownership; policy; promotion; rollback; and migration.

### GitOps and progressive delivery

Start with [`core/delivery-gitops/README.md`](core/delivery-gitops/README.md).

- [`gitops-progressive-delivery.md`](core/delivery-gitops/gitops-progressive-delivery.md) — build, promotion, and reconciliation boundaries; ownership; CRDs; pruning; secrets; multi-cluster rollout; canary analysis; rollback; and Argo CD/Flux mappings.

### Kubernetes autoscaling and capacity realization

Start with [`core/kubernetes/autoscaling/README.md`](core/kubernetes/autoscaling/README.md).

- [`control-loops-capacity-realization.md`](core/kubernetes/autoscaling/control-loops-capacity-realization.md) — HPA, VPA, KEDA, scheduler and node-supply loops; requests; Cluster Autoscaler and Karpenter; Spot; topology; disruption; recovery timelines; and validation.

### Incident response and causal analysis

Start with [`core/incident-response/README.md`](core/incident-response/README.md).

- [`request-path-debugging.md`](core/incident-response/request-path-debugging.md) — client-to-dependency isolation, status-code ownership, paired evidence, hypothesis discipline, reversible mitigation, and external recovery proof.
- [`cohort-analysis.md`](core/incident-response/cohort-analysis.md) — partial failures, rates and denominators, confounding, release and infrastructure cohorts, selective mitigation, privacy, and cardinality.
- [`postmortems.md`](core/incident-response/postmortems.md) — impact, fact-versus-inference timelines, causal graphs, response analysis, recovery debt, corrective-action governance, verification, and closure.

### Observability and diagnostic evidence

Start with [`core/observability/README.md`](core/observability/README.md).

- [`evidence-beyond-dashboards.md`](core/observability/evidence-beyond-dashboards.md) — alert validation, evidence hierarchy, paired traces, structured logs, metrics, profiles, changes, network and synthetic evidence, hypothesis ledgers, telemetry-pipeline health, and cardinality governance.

### Reliability engineering, SLOs, and error budgets

Start with [`core/reliability/README.md`](core/reliability/README.md).

- [`slo/error-budgets.md`](core/reliability/slo/error-budgets.md) — user-centered SLIs, SLOs, SLAs, error-budget and burn-rate mathematics, denominator engineering, unknown handling, protected cohorts, multi-window alerting, ownership, release policy, capacity integration, and SLO-as-code.

### Service mesh, Envoy, Istio, and xDS

Start with [`core/service-mesh/README.md`](core/service-mesh/README.md).

- [`fine-grained-service-discovery.md`](core/service-mesh/fine-grained-service-discovery.md) — registry, control-plane and data-plane separation, xDS, configuration fan-out, dependency scoping, sidecar and Ambient trade-offs, multi-cluster failure domains, convergence, and last-known-good behavior.

### eBPF and runtime security

- [`core/ebpf-security/cilium-hubble-falco-tetragon.md`](core/ebpf-security/cilium-hubble-falco-tetragon.md) — Linux hook selection, Cilium dataplane and policy, Hubble evidence, Falco detection, Tetragon enforcement, failure modes, and safe migration.

## Executable labs

### Platform engineering labs

Start with [`labs/platform-engineering/README.md`](labs/platform-engineering/README.md).

1. golden-path contract;
2. staged policy rollout;
3. tenant-isolation contract;
4. artifact-trust verification;
5. multi-cluster fleet rollout planning;
6. secret-delivery and rotation contract.

Run all current platform scenarios with:

```bash
python3 labs/platform-engineering/run_all.py
```

### Distributed-systems labs

Start with [`labs/distributed-systems/README.md`](labs/distributed-systems/README.md).

1. retry amplification;
2. transactional outbox;
3. fencing tokens;
4. cache races;
5. shard rebalancing;
6. queue redelivery.

### AWS and EKS interview labs

Start with [`labs/aws/README.md`](labs/aws/README.md).

1. cohort deployment failure;
2. Terraform partial apply;
3. Kubernetes restart evidence;
4. workload-identity claims;
5. autoscaling control loops.

### Reliability engineering labs

Start with [`labs/reliability/README.md`](labs/reliability/README.md).

1. error-budget mathematics, burn policy, unknown telemetry, protected cohorts, and release decisions.

GitHub Actions compiles and runs the relevant deterministic lab suites on changes to their paths.

## Canonical ownership rule

A topic belongs in `core/` when it can answer questions for more than one company or role.

A track chapter should contain only:

1. the original company- or platform-style question;
2. domain context and assumptions;
3. a concise interview answer;
4. links to required core chapters;
5. domain-specific failure modes and trade-offs;
6. adversarial follow-ups;
7. personal-story mapping.

A track must not become a second conflicting Linux, Kubernetes, Terraform, platform-engineering, service-mesh, observability, incident-response, reliability, security, autoscaling, or distributed-systems source of truth.

## Existing interview tracks

- [Netflix-scale DevOps interview track](https://github.com/hatan4ik/netflix-devops-interview)
- [Tesla SRE interview track](https://github.com/hatan4ik/tesla-sre-interview)
- [`tracks/aws/README.md`](tracks/aws/README.md) — AWS DevOps, Amazon EKS, GitOps, Terraform, incident-response, and system-design track.

All 18 AWS source questions have Staff/Principal-level chapters across infrastructure, incidents, and system design. The track also includes board review, spoken-answer drills, a mock-interview scorecard, a personal-story matrix, an official-source index, and executable labs.

## Coordination

- [`curriculum-map.md`](curriculum-map.md) assigns canonical ownership and maps track scenarios to shared prerequisites.
- [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) records completed migrations, transitional duplicates, and upcoming work.

## Active delivery pipeline

- Build canonical Kubernetes runtime, node-failure, fencing, repair, and image-qualification chapters and labs.
- Build disaster-recovery, blast-radius, overload, graceful-degradation, and chaos modules.
- Expand OpenTelemetry, tracing, profiling, alert-quality, and high-volume observability-platform chapters.
- Expand Envoy request-path, mTLS, DNS-capture, and multi-cluster service-mesh chapters and labs.
- Extend platform labs from declarative simulations into disposable-cluster conformance and recovery exercises.
- Replace duplicated Netflix, Tesla, and AWS theory with concise interview adapters after parity review.

## Core principle

> Write engineering fundamentals once, specialize only the business context, and ensure no interview track drifts into a second conflicting source of truth.
