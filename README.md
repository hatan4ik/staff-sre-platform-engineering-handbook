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

The module covers platform-as-product thinking, golden paths, Internal Developer Platform architecture, software catalogs and Backstage, self-service infrastructure, platform SLOs and economics, policy as code, Kubernetes multi-tenancy, and multi-cluster fleet lifecycle.

### Security: identity, secrets, and artifact trust

Start with [`core/security/README.md`](core/security/README.md).

- [`identity/workload-identity-federation.md`](core/security/identity/workload-identity-federation.md) — projected ServiceAccount tokens, EKS Pod Identity and IRSA, Entra and GKE federation, SPIFFE/SPIRE, node-role protection, rotation, and negative testing.
- [`secrets/secret-delivery-rotation-kubernetes.md`](core/security/secrets/secret-delivery-rotation-kubernetes.md) — secret authority, dynamic credentials, CSI, External Secrets Operator, Vault, rotation, revocation, regional recovery, CI/CD, and Terraform state.
- [`software-supply-chain/artifact-trust-slsa-sigstore.md`](core/security/software-supply-chain/artifact-trust-slsa-sigstore.md) — digests, signatures, provenance, attestations, SBOMs, SLSA, Sigstore/Cosign, deployment verification, runtime inventory, and compromise response.

### Linux internals and production debugging

Start with [`core/linux/README.md`](core/linux/README.md).

Seven chapters cover kernel architecture and boot, processes and scheduling, memory and OOM, storage and I/O, networking and containers, observability and eBPF, and integrated incident labs.

### Kubernetes internals and platform operations

Start with [`core/kubernetes/README.md`](core/kubernetes/README.md).

Canonical material now includes:

- API-server, etcd, admission, LIST/WATCH, API Priority and Fairness, and control-plane latency;
- autoscaling and capacity realization;
- node health, fencing, drain, repair, and replacement;
- container restart, OOM, eviction, probe, PID 1, kubelet, and runtime debugging;
- immutable node-image qualification, canary promotion, rollout rings, and rollback.

### Distributed systems

Start with [`core/distributed-systems/README.md`](core/distributed-systems/README.md).

The ten-chapter module covers partial failure, time and retries, consistency, replication and consensus, partitioning, messaging, caching, overload and cascading failures, observability, and Staff/Principal design drills.

### Infrastructure as code and Terraform governance

Start with [`core/infrastructure-as-code/README.md`](core/infrastructure-as-code/README.md).

- [`terraform-state-integrity.md`](core/infrastructure-as-code/terraform-state-integrity.md) — state bindings, locking, partial-apply recovery, state boundaries, concurrency, drift, and break-glass governance.
- [`tool-selection-and-governance.md`](core/infrastructure-as-code/tool-selection-and-governance.md) — declarative, cloud-native, programming-language, GitOps, configuration-management, and control-plane choices.

### GitOps and progressive delivery

Start with [`core/delivery-gitops/README.md`](core/delivery-gitops/README.md).

The canonical chapter covers build, promotion, reconciliation, ownership, CRDs, pruning, secrets, multi-cluster rollout, canary analysis, rollback, Argo CD, and Flux.

### Incident response and causal analysis

Start with [`core/incident-response/README.md`](core/incident-response/README.md).

The module covers client-to-dependency request-path isolation, cohort analysis, evidence discipline, postmortems, corrective actions, and recovery proof.

### Observability and diagnostic evidence

Start with [`core/observability/README.md`](core/observability/README.md).

Canonical chapters cover:

- evidence beyond dashboards;
- OpenTelemetry instrumentation and Collector topology;
- bounded queues, backpressure, sampling, tenancy, redaction, and synthetic telemetry;
- metrics, histograms, cardinality, distributed tracing, structured logs, continuous profiling, alert quality, high-volume ingestion, retention, and query governance.

### Reliability engineering, SLOs, overload, DR, and chaos

Start with [`core/reliability/README.md`](core/reliability/README.md).

Canonical modules cover:

- user-centered SLIs, SLOs, error budgets, and burn policy;
- deadlines, retry budgets, concurrency limits, bounded queues, admission, load shedding, degraded modes, dependency contracts, cells, blast radius, failover safety, and backlog recovery;
- multi-region failover, failback, fencing, RTO/RPO, and reconciliation;
- chaos hypotheses, steady state, abort conditions, production safeguards, game-day governance, evidence, and re-testing.

### Service mesh, Envoy, Istio, and xDS

Start with [`core/service-mesh/README.md`](core/service-mesh/README.md).

Canonical chapters cover:

- fine-grained discovery and xDS;
- Envoy request-path, timeout, reset, circuit-breaker, outlier-ejection, and 504 debugging;
- workload identity, mTLS, SDS, trust bundles, authorization, DNS capture, service export/import, east-west gateways, multi-cluster failover, and last-known-good behavior.

### eBPF and runtime security

- [`core/ebpf-security/cilium-hubble-falco-tetragon.md`](core/ebpf-security/cilium-hubble-falco-tetragon.md) — Linux hook selection, Cilium dataplane and policy, Hubble evidence, Falco detection, Tetragon enforcement, failure modes, and safe migration.

## Executable labs

### Platform engineering

Start with [`labs/platform-engineering/README.md`](labs/platform-engineering/README.md).

Current scenarios cover golden-path contracts, staged policy rollout, tenant isolation, artifact trust, fleet rollout planning, and secret-delivery rotation.

```bash
python3 labs/platform-engineering/run_all.py
```

### Distributed systems

Start with [`labs/distributed-systems/README.md`](labs/distributed-systems/README.md).

Current scenarios cover retry amplification, transactional outbox, fencing tokens, cache races, shard rebalancing, and queue redelivery.

### AWS and EKS interview labs

Start with [`labs/aws/README.md`](labs/aws/README.md).

Current scenarios cover cohort-specific deployment failure, Terraform partial apply, Kubernetes restart evidence, workload identity claims, and autoscaling control loops.

### Reliability engineering

Start with [`labs/reliability/README.md`](labs/reliability/README.md).

Current scenarios cover error-budget policy, disaster-recovery state transitions, retry amplification, priority and tenant admission, failover headroom, and paced backlog recovery.

### Observability

Start with [`labs/observability/README.md`](labs/observability/README.md).

The telemetry-pipeline lab covers critical-signal preservation, tenant quotas, cardinality policy, bounded queues, visible loss, freshness, and deterministic sampling.

GitHub Actions compiles and runs the relevant deterministic lab suites and uploads machine-readable evidence reports.

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

A track must not become a second conflicting source of truth for Linux, Kubernetes, Terraform, platform engineering, service mesh, observability, incident response, reliability, security, autoscaling, or distributed systems.

## Existing interview tracks

- [Netflix-scale DevOps interview track](https://github.com/hatan4ik/netflix-devops-interview)
- [Tesla SRE interview track](https://github.com/hatan4ik/tesla-sre-interview)
- [`tracks/aws/README.md`](tracks/aws/README.md) — AWS DevOps, Amazon EKS, GitOps, Terraform, incident-response, and system-design track.

All 18 AWS source questions have Staff/Principal-level chapters. The track also includes board review, spoken-answer drills, a mock-interview scorecard, a personal-story bank, an official-source index, an executable cold baseline, evidence-completion worksheets, and hands-on labs.

## Coordination

- [`curriculum-map.md`](curriculum-map.md) assigns canonical ownership and maps track scenarios to shared prerequisites.
- [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md) records completed migrations, transitional duplicates, and upcoming work.

## Remaining delivery pipeline

The principal remaining engineering work is narrower than the original backlog:

- build disposable-cluster conformance for control-plane, node-image, probe, DNS, mesh, OpenTelemetry, and recovery failures;
- add dedicated scheduler, Kubernetes networking/Gateway, and CSI/stateful-recovery chapters;
- create direct service-mesh xDS, certificate-rotation, DNS-capture, and east-west-gateway labs;
- add real OpenTelemetry Collector and alert-rule integration tests;
- complete parity review and thin duplicated Netflix, Tesla, and AWS theory into concise adapters;
- split `tracks/aws/` into a separate top-level adapter repository when repository-creation capability is available;
- complete candidate-specific production metrics and evidence without inventing results.

## Core principle

> Write engineering fundamentals once, specialize only the business context, and ensure no interview track drifts into a second conflicting source of truth.
