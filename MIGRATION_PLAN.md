# Consolidation and Migration Plan

This file is the coordination point for all overlapping interview-preparation work.

## Objective

Maintain one canonical technical explanation for every reusable engineering topic while keeping Tesla-, Netflix-, and AWS-shaped scenarios in adapters.

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

The GitHub connector used for this work cannot create a new top-level repository. AWS material is therefore developed in `tracks/aws/` with clean ownership boundaries and can be split later into a thin `aws-devops-interview` adapter repository without rewriting canonical content.

## Ownership rules

### Canonical handbook owns

- Linux internals and production debugging.
- Networking, DNS, TLS, load balancing, NAT, and service discovery.
- Kubernetes API, controllers, scheduling, autoscaling, probes, networking, storage, node lifecycle, runtime, and node images.
- eBPF, Cilium, Hubble, Falco, Tetragon, and runtime security.
- Envoy, Istio, service-mesh control/data planes, xDS, mTLS, DNS capture, gateways, and multi-cluster behavior.
- Terraform state, locking, drift, recovery, modules, and policy.
- GitOps, CI/CD, artifact integrity, and progressive delivery.
- Identity, federation, secrets, supply-chain security, and admission control.
- Observability, OpenTelemetry, metrics, logs, tracing, profiling, alerting, and evidence systems.
- Request-path isolation, cohort analysis, incident command, postmortems, and corrective actions.
- SLOs, error budgets, capacity, overload, graceful degradation, blast radius, DR, failback, and chaos.
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
| Envoy request paths, timeouts, resets, retries, and 504s | Netflix and AWS incidents | `core/service-mesh/envoy-request-path-debugging.md` | Migrated and normalized |
| Mesh mTLS, SDS, DNS capture, gateways, and multi-cluster | Netflix, Tesla, and AWS scenarios | `core/service-mesh/mtls-sds-dns-multicluster.md` | Migrated and normalized |
| Terraform state and recovery | Netflix and AWS tracks | `core/infrastructure-as-code/terraform-state-integrity.md` | Migrated and normalized; AWS recovery adapter retained |
| GitOps and progressive delivery | AWS Round 1 and 2 | `core/delivery-gitops/gitops-progressive-delivery.md` | Migrated and normalized; AWS incident adapters retained |
| Workload identity, federation, and SPIFFE | Netflix, Tesla, and AWS tracks | `core/security/identity/workload-identity-federation.md` | Migrated and normalized; cloud-specific adapters retained |
| Secret delivery and rotation | Platform and cloud tracks | `core/security/secrets/secret-delivery-rotation-kubernetes.md` | Migrated and normalized |
| Software supply-chain and artifact trust | Fleet, platform, and delivery scenarios | `core/security/software-supply-chain/artifact-trust-slsa-sigstore.md` | Migrated and normalized |
| Kubernetes autoscaling and capacity realization | Netflix and AWS tracks | `core/kubernetes/autoscaling/control-loops-capacity-realization.md` | Migrated and normalized; AWS capacity adapter retained |
| Kubernetes control-plane and API latency | AWS Round 2 | `core/kubernetes/control-plane/api-server-etcd-list-watch-admission.md` | Migrated and normalized |
| Kubernetes runtime restart and OOM debugging | Tesla, Netflix, and AWS tracks | `core/kubernetes/runtime-debugging.md` and `core/linux/` | Migrated and normalized; AWS incident adapter retained |
| Kubernetes node failure, fencing, and repair | Netflix and shared operations | `core/kubernetes/node-lifecycle/failure-fencing-repair.md` | Migrated and normalized with executable repair lab |
| Kubernetes node-image qualification | Shared platform operations | `core/kubernetes/node-images/qualification-promotion-rollback.md` | Added as canonical foundation |
| IaC tool selection and governance | AWS Round 1 | `core/infrastructure-as-code/tool-selection-and-governance.md` | Migrated and normalized |
| Client-to-dependency request-path isolation | AWS Round 2 and all tracks | `core/incident-response/request-path-debugging.md` | Migrated and normalized |
| Selective failures and cohort analysis | AWS Round 2 and progressive delivery | `core/incident-response/cohort-analysis.md` | Migrated and normalized |
| Evidence beyond dashboards | AWS Round 2 and all tracks | `core/observability/evidence-beyond-dashboards.md` | Migrated and normalized |
| OpenTelemetry pipelines and Collector governance | AWS observability and all tracks | `core/observability/opentelemetry-pipelines-and-governance.md` | Migrated and normalized |
| Metrics, tracing, profiling, alert quality, and high-volume telemetry | All tracks | `core/observability/high-volume-telemetry-alerting-profiling.md` | Migrated and normalized |
| Postmortems and corrective actions | All tracks | `core/incident-response/postmortems.md` | Migrated and normalized |
| SLOs, error budgets, burn rates, and ownership | Netflix and all tracks | `core/reliability/slo/error-budgets.md` | Migrated and normalized |
| Overload, graceful degradation, blast radius, and backlog recovery | All tracks | `core/reliability/graceful-degradation-overload-blast-radius.md` | Migrated and normalized |
| Multi-region disaster recovery and failback | All tracks | `core/reliability/disaster-recovery/` | Migrated and normalized with executable state-machine lab |
| Chaos engineering and game-day governance | All tracks | `core/reliability/chaos-engineering-game-days.md` | Migrated and normalized |
| Mobile identity, commands, notifications, and preference synchronization | Tesla and AWS tracks | `core/distributed-systems/`, `core/security/identity/`, and `core/reliability/` | Canonical foundations present; thin adapter review remains |
| Secure fleet and OTA delivery | Tesla and AWS tracks | `core/security/software-supply-chain/`, `core/delivery-gitops/`, and `core/reliability/` | Canonical foundations present; thin adapter review remains |
| High-volume streams, queues, replay, and backpressure | All tracks | `core/distributed-systems/` and `core/reliability/` | Canonical foundations present; cloud adapters retained |

## Executable-lab migration status

| Lab | Canonical foundation | Status |
|---|---|---|
| Cohort-specific deployment failure | Incident cohort analysis and GitOps | Added and automated |
| Terraform partial apply | Terraform state integrity | Added with failure and convergence proof |
| Kubernetes restart evidence | Kubernetes runtime and Linux memory/observability | Added and validated |
| Workload identity claims | Workload identity federation | Added with unit tests and smoke scenarios |
| Autoscaling control loop | Kubernetes autoscaling | Added with unit tests and smoke scenarios |
| SLO and error-budget policy | Reliability SLO module | Added with protected-cohort and burn-rate tests |
| Kubernetes node repair | Node lifecycle and fencing | Added with state-machine simulator, tests, and CI |
| Disaster-recovery state machine | Multi-region DR | Added with guarded transitions, tests, and CI |
| Overload and blast radius | Graceful degradation and overload | Added with retry, admission, failover, and replay tests |
| Telemetry pipeline governance | OpenTelemetry and high-volume observability | Added with quota, cardinality, loss, freshness, and sampling tests |
| Platform policy, tenant isolation, artifact trust, fleet rollout, and secrets | Platform and security modules | Added with deterministic scenarios and CI |

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

### Round 3 — complete on `main`

- `tracks/aws/round-3/14-highly-available-mobile-backend.md`
- `tracks/aws/round-3/15-global-secure-software-updates.md`
- `tracks/aws/round-3/16-multi-region-disaster-recovery.md`
- `tracks/aws/round-3/17-actionable-observability-platform.md`
- `tracks/aws/round-3/18-millions-events-per-second.md`

### Practice system — complete initial set

- FAANG board review and spoken drills.
- Mock scorecard and executable cold-baseline runner.
- Interview-day cheatsheet and 30-day plan.
- Personal story bank and evidence-completion worksheet.
- Official-source index.
- AWS, Kubernetes, Terraform, reliability, and distributed-systems labs.

## Remaining work

1. Build disposable-cluster conformance for control-plane, node-image, probes, DNS, mesh, OpenTelemetry, and recovery failures.
2. Add dedicated scheduler, Kubernetes network/Gateway, and CSI/stateful-recovery canonical chapters.
3. Add direct xDS convergence, certificate rotation, DNS capture, and east-west gateway labs.
4. Add real OpenTelemetry Collector, trace-context, profile, and alert-rule integration tests.
5. Perform parity review and replace duplicated Netflix, Tesla, and AWS theory with thin adapters.
6. Split the AWS track into a top-level repository when repository-creation capability is available.
7. Complete candidate-specific metrics and exact production evidence without inventing outcomes.

## No-duplication workflow

Before creating a chapter:

1. Search this repository by topic and failure mode.
2. Search `curriculum-map.md` for an existing canonical owner.
3. Extend the canonical chapter rather than creating a second permanent textbook.
4. Put cloud or company assumptions and trade-offs in the track.
5. Link the track chapter to exact canonical prerequisites.
6. Record the ownership decision in this migration plan.
7. Treat a deep track chapter as migration source material until canonical parity exists.

## Transitional policy

Existing duplicate chapters in company or platform tracks are not deleted immediately. They remain as source material until the canonical replacement is reviewed for coverage.

During transition, track READMEs must point readers to this handbook as the source of truth. Once coverage parity is confirmed, duplicated theory should be replaced with concise adapters and links.

## New-repository split plan

When a top-level `hatan4ik/aws-devops-interview` repository is available:

1. create a thin adapter README and interview sequence there;
2. move or link AWS-only scenario material;
3. retain reusable theory in this handbook;
4. add reciprocal links in both repositories;
5. preserve commit history where practical;
6. verify no contradictory duplicate explanations remain.
