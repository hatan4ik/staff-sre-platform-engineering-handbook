# Consolidation and Migration Plan

This file is the coordination point for all overlapping interview-preparation work.

## Objective

Maintain one canonical technical explanation for every reusable engineering topic while keeping Tesla-, Netflix-, and AWS-shaped scenarios in adapters.

The intended flow is:

```text
canonical technical chapter
        |
        +--> Tesla connected-vehicle adapter
        +--> Netflix streaming-platform adapter
        +--> AWS / Amazon EKS adapter
        +--> future company or role adapters
```

## Source repositories and tracks

- `hatan4ik/tesla-sre-interview`
- `hatan4ik/netflix-devops-interview`
- `hatan4ik/staff-sre-platform-engineering-handbook` — canonical shared source
- `tracks/aws/` — AWS DevOps and Amazon EKS interview adapter currently hosted in the canonical handbook

The GitHub connector used for this work cannot create a new top-level repository. The AWS material is therefore developed in `tracks/aws/` with clean ownership boundaries and can be split later into a thin `aws-devops-interview` adapter repository without rewriting the canonical content.

## Ownership rules

### Canonical handbook owns

- Linux internals and production debugging.
- Networking, DNS, TLS, load balancing, NAT, and service discovery.
- Kubernetes internals, scheduling, autoscaling, probes, networking, storage, and security.
- eBPF, Cilium, Hubble, Falco, Tetragon, and runtime security.
- Envoy, Istio, service-mesh control/data planes, and mTLS.
- Terraform state, locking, drift, recovery, modules, and policy.
- GitOps, CI/CD, artifact integrity, and progressive delivery.
- Identity, secrets, supply-chain security, and admission control.
- Observability, OpenTelemetry, Prometheus, tracing, profiling, and alerting.
- SLOs, error budgets, incident command, postmortems, capacity, DR, and chaos.
- Distributed systems, queues, consistency, idempotency, backpressure, and multi-region design.

### Tesla track owns

- Connected-vehicle command lifecycle and local vehicle authority.
- Remote unlock and mobile-feature reliability.
- Vehicle session ownership, command expiry, replay resistance, and fencing.
- Fleet telemetry and OTA architecture.
- Driver-profile synchronization and intermittent-connectivity behavior.
- Tesla-shaped mock interviews and behavioral stories.

### Netflix track owns

- Streaming request paths and playback-oriented availability.
- Discovery across very large microservice estates.
- Cache-sidecar and tail-latency scenarios.
- Streaming-scale DNS, mesh, NAT, and failover scenarios.
- Major-release chaos exercises and graceful degradation.
- Netflix-shaped mock interviews, modernization ROI, and leadership framing.

### AWS track owns

- AWS service selection for interview scenarios.
- Amazon EKS managed-control-plane and customer-data-plane boundaries.
- VPC, Availability Zone, account, Region, IAM, quota, and service-specific failure behavior.
- EKS Pod Identity, IRSA, Security Groups for Pods, VPC CNI, and AWS Load Balancer Controller details.
- S3 backend implementation, current lock-file behavior, and legacy DynamoDB-lock migration on AWS.
- CloudFormation, CDK, StackSets, Service Catalog, Control Tower, Config, and Systems Manager trade-offs.
- Karpenter, managed node groups, EC2 Auto Scaling Groups, and Spot operational details.
- Cognito, IoT Core, IoT Device Management Jobs, Software Package Catalog, ARC, Global Accelerator, Global Tables, Aurora Global Database, AMP, Managed Grafana, Kinesis, SQS, SNS, EventBridge, and Lambda adapters.
- AWS-shaped incident workflows, evidence sources, system designs, commands, whiteboards, and adversarial follow-ups.

## Migration status

| Shared topic | Existing source | Canonical destination | Status |
|---|---|---|---|
| Linux architecture, boot, and syscalls | Tesla Linux chapter | `core/linux/01-architecture-boot-syscalls.md` | Migrated and normalized |
| Processes, scheduling, interrupts, and load | Tesla Linux chapter | `core/linux/02-processes-scheduler.md` | Migrated and normalized |
| Memory, page cache, NUMA, reclaim, and OOM | Tesla Linux chapter | `core/linux/03-memory.md` | Migrated and normalized |
| VFS, filesystem, and block I/O | Tesla Linux chapter | `core/linux/04-storage-io.md` | Migrated and normalized |
| Networking, containers, cgroups, and Linux security | Tesla Linux plan | `core/linux/05-networking-containers-security.md` | Migrated and normalized |
| Linux observability, eBPF, and production debugging | Tesla Linux plan | `core/linux/06-observability-debugging.md` | Migrated and normalized |
| Integrated Linux incident scenarios | Shared interview requirements | `core/linux/07-linux-incident-labs.md` | Added as canonical practice layer |
| eBPF/Cilium/Hubble/Falco/Tetragon | Netflix chapter 2 | `core/ebpf-security/cilium-hubble-falco-tetragon.md` | Migrated and normalized |
| Fine-grained Envoy/Istio discovery | Netflix chapter 1 | `core/service-mesh/fine-grained-service-discovery.md` | Migrated and normalized |
| Terraform state and recovery | Netflix and AWS tracks | `core/infrastructure-as-code/terraform-state-integrity.md` | Migrated and normalized; AWS recovery adapter added |
| GitOps and progressive delivery | AWS Round 1 and 2 | `core/delivery-gitops/gitops-progressive-delivery.md` | Migrated and normalized; AWS incident adapters added |
| IAM and workload identity | Netflix, Tesla, and AWS tracks | `core/security/identity/` | AWS source added; canonical migration planned |
| EKS and Kubernetes autoscaling | Netflix and AWS tracks | `core/kubernetes/autoscaling/` | AWS source added; canonical migration planned |
| IaC tool selection and governance | AWS Round 1 | `core/infrastructure-as-code/tool-selection-and-governance.md` | Migrated and normalized |
| Request-path and cohort debugging | AWS Round 2 | `core/incident-response/` and `core/networking/` | Source added; canonical migration planned |
| Control-plane and application latency analysis | AWS Round 2 | `core/kubernetes/control-plane/`, `core/observability/`, and `core/reliability/` | Source added; canonical migration planned |
| Evidence beyond dashboards | AWS Round 2 | `core/observability/` | Source added; canonical migration planned |
| Runtime restart and OOM debugging | Tesla, Netflix, and AWS tracks | `core/kubernetes/runtime-debugging.md` and `core/linux/` | AWS source added; canonical migration planned |
| Postmortems and corrective actions | All tracks | `core/incident-response/postmortems.md` | AWS source added; canonical migration planned |
| Mobile identity, commands, notifications, and preference synchronization | Tesla and AWS tracks | `core/distributed-systems/`, `core/security/identity/`, and `core/reliability/` | AWS system-design source added; canonical extraction planned |
| Secure fleet and OTA delivery | Tesla and AWS tracks | `core/security/supply-chain/`, `core/delivery-gitops/`, and `core/reliability/blast-radius.md` | AWS system-design source added; canonical extraction planned |
| Multi-Region disaster recovery | All tracks | `core/reliability/disaster-recovery/` | AWS system-design source added; canonical extraction planned |
| Observability platform and alert quality | All tracks | `core/observability/` and `core/reliability/slo/` | AWS system-design source added; canonical extraction planned |
| High-volume streams, queues, replay, and backpressure | All tracks | `core/distributed-systems/` and `core/reliability/` | AWS system-design source added; canonical extraction planned |
| SLOs, incidents, multi-region, and chaos | All tracks | `core/reliability/` | Planned |

## AWS interview implementation status

### Round 1 — complete on `main`

- `tracks/aws/round-1/01-multi-az-eks-millions-users.md`
- `tracks/aws/round-1/02-gitops-terraform-argocd-flux.md`
- `tracks/aws/round-1/03-terraform-state-multi-account-region.md`
- `tracks/aws/round-1/04-securing-amazon-eks.md`
- `tracks/aws/round-1/05-terraform-cloudformation-native.md`
- `tracks/aws/round-1/06-capacity-autoscaling-karpenter-spot.md`

### Round 2 — complete on `main`

- `tracks/aws/round-2/07-route53-to-application-outage.md`
- `tracks/aws/round-2/08-eks-api-latency-nodes-healthy.md`
- `tracks/aws/round-2/08b-application-api-latency-nodes-healthy.md`
- `tracks/aws/round-2/09-subset-users-fail-after-deployment.md`
- `tracks/aws/round-2/10-beyond-cloudwatch-dashboards.md`
- `tracks/aws/round-2/11-terraform-partial-apply-recovery.md`
- `tracks/aws/round-2/12-pods-restart-probes-healthy.md`
- `tracks/aws/round-2/13-large-aws-outage-postmortem.md`

### Round 3 — complete in `aws-round-3-system-design`

- `tracks/aws/round-3/14-highly-available-mobile-backend.md`
- `tracks/aws/round-3/15-global-secure-software-updates.md`
- `tracks/aws/round-3/16-multi-region-disaster-recovery.md`
- `tracks/aws/round-3/17-actionable-observability-platform.md`
- `tracks/aws/round-3/18-millions-events-per-second.md`

### Next phase

- FAANG board review across all 18 answers.
- concise spoken-answer sheets and interviewer follow-up drills.
- hands-on labs and runnable reference implementations.
- mock interview scorecards.
- personal story mapping to the candidate's production experience.
- canonical-core extraction of reusable Round 2 and Round 3 foundations.

## No-duplication workflow

Before creating a chapter:

1. Search this repository by topic and failure mode.
2. Search `curriculum-map.md` for an existing canonical owner.
3. Extend the canonical chapter rather than creating a second permanent textbook.
4. Put AWS service assumptions and trade-offs in the AWS track.
5. Link the track chapter to exact canonical prerequisites.
6. Record the ownership decision in this migration plan.
7. Treat a deep track chapter as migration source material until canonical parity exists.

## Transitional policy

Existing duplicate chapters in company or platform tracks are not deleted immediately. They remain as source material until the canonical replacement is reviewed for coverage.

During transition, track READMEs must point readers to this handbook as the source of truth. Once coverage parity is confirmed, duplicated theory should be replaced with concise adapters and links.

## New-repository split plan

When a top-level `hatan4ik/aws-devops-interview` repository is available:

1. create a thin adapter README and interview sequence there
2. move or link AWS-only scenario material
3. retain reusable theory in this handbook
4. add reciprocal links in both repositories
5. preserve commit history where practical
6. verify no contradictory duplicate explanations remain