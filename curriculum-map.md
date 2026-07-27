# Consolidated Curriculum Map

This map prevents duplicate chapter development across company- and platform-specific interview tracks.

## Shared-core ownership matrix

| Topic | Canonical core path | Netflix use | Tesla use | AWS use |
|---|---|---:|---:|---:|
| Linux boot, systemd, processes, cgroups | `core/linux/` | Yes | Yes | Yes |
| TCP, DNS, TLS, HTTP, packet debugging | `core/networking/` and `core/linux/05-networking-containers-security.md` | Yes | Yes | Yes |
| Kubernetes API server, etcd, admission, LIST/WATCH, APF | `core/kubernetes/control-plane/` | Yes | Yes | Yes |
| Kubernetes scheduling and placement | future `core/kubernetes/scheduling/` | Yes | Yes | Yes |
| Node health, fencing, drain, repair | `core/kubernetes/node-lifecycle/` | Yes | Yes | Yes |
| Container restart, OOM, eviction, PID 1, kubelet/runtime | `core/kubernetes/runtime-debugging.md` and `core/linux/` | Yes | Yes | Yes |
| Node-image qualification, promotion, rollback | `core/kubernetes/node-images/` | Yes | Yes | Yes |
| Service discovery, Envoy, Istio, xDS | `core/service-mesh/fine-grained-service-discovery.md` | Yes | Yes | Yes |
| Envoy request paths, timeouts, resets, 504s | `core/service-mesh/envoy-request-path-debugging.md` | Yes | Yes | Yes |
| Mesh mTLS, SDS, DNS capture, gateways, multi-cluster | `core/service-mesh/mtls-sds-dns-multicluster.md` | Yes | Yes | Yes |
| eBPF, Cilium, Hubble, Falco, Tetragon | `core/ebpf-security/` | Yes | Yes | Yes |
| OpenTelemetry and Collector architecture | `core/observability/opentelemetry-pipelines-and-governance.md` | Yes | Yes | Yes |
| Metrics, logs, tracing, profiling, alert quality | `core/observability/high-volume-telemetry-alerting-profiling.md` | Yes | Yes | Yes |
| Evidence beyond dashboards | `core/observability/evidence-beyond-dashboards.md` | Yes | Yes | Yes |
| SLOs and error budgets | `core/reliability/slo/` | Yes | Yes | Yes |
| Overload, admission, degradation, blast radius | `core/reliability/graceful-degradation-overload-blast-radius.md` | Yes | Yes | Yes |
| Multi-region failover and failback | `core/reliability/disaster-recovery/` | Yes | Yes | Yes |
| Chaos engineering and game days | `core/reliability/chaos-engineering-game-days.md` | Yes | Yes | Yes |
| HPA, VPA, KEDA, scheduler, Cluster Autoscaler, Karpenter | `core/kubernetes/autoscaling/` | Yes | Yes | Yes |
| Terraform state, locking, drift | `core/infrastructure-as-code/` | Yes | Yes | Yes |
| GitOps and progressive delivery | `core/delivery-gitops/` | Yes | Yes | Yes |
| Workload identity, federation, SPIFFE, cloud IAM | `core/security/identity/` | Yes | Yes | Yes |
| Secret delivery and rotation | `core/security/secrets/` | Yes | Yes | Yes |
| Artifact trust, SLSA, Sigstore, SBOMs | `core/security/software-supply-chain/` | Yes | Yes | Yes |
| Request paths, cohorts, incident command, postmortems | `core/incident-response/` | Yes | Yes | Yes |
| Messaging, streams, idempotency, and backpressure | `core/distributed-systems/` | Yes | Yes | Yes |
| Platform product, IDP, policy, tenancy, fleets | `core/platform-engineering/` | Yes | Yes | Yes |
| Staff/Principal leadership and ROI | future `core/leadership/` expansion | Yes | Yes | Yes |

## Source-to-canonical mapping

| Existing source | Canonical destination | State |
|---|---|---|
| Netflix fine-grained discovery | `core/service-mesh/fine-grained-service-discovery.md` | Canonical |
| Netflix eBPF/Cilium runtime security | `core/ebpf-security/cilium-hubble-falco-tetragon.md` | Canonical |
| Netflix routing, identity, and secrets | service mesh, identity, and secrets modules | Canonical foundations present |
| Netflix EKS/systemd node failure | `core/kubernetes/node-lifecycle/failure-fencing-repair.md` | Canonical |
| Netflix/Tesla node-image concerns | `core/kubernetes/node-images/qualification-promotion-rollback.md` | Canonical |
| Netflix probe and overload scenarios | `core/reliability/graceful-degradation-overload-blast-radius.md` | Canonical foundations present |
| Netflix/Tesla DNS and mesh scenarios | `core/service-mesh/mtls-sds-dns-multicluster.md` | Canonical foundations present |
| Netflix/Tesla/AWS 504 and partial failures | service-mesh request path, incident response, and observability modules | Canonical |
| AWS Round 1 GitOps | `core/delivery-gitops/gitops-progressive-delivery.md` | Canonical |
| AWS Round 1 Terraform state | `core/infrastructure-as-code/terraform-state-integrity.md` | Canonical |
| AWS Round 1 EKS security | identity, secrets, platform policy, and supply-chain modules | Canonical foundations present |
| AWS Round 1 provisioning-tool selection | `core/infrastructure-as-code/tool-selection-and-governance.md` | Canonical |
| AWS Round 1 autoscaling | `core/kubernetes/autoscaling/control-loops-capacity-realization.md` | Canonical |
| AWS Round 2 API-server latency | `core/kubernetes/control-plane/api-server-etcd-list-watch-admission.md` | Canonical |
| AWS Round 2 application latency and evidence | observability and request-path modules | Canonical |
| AWS Round 2 cohort failure | cohort analysis and progressive delivery modules | Canonical |
| AWS Round 2 Terraform partial apply | Terraform state integrity module | Canonical |
| AWS Round 2 pod restarts | Kubernetes runtime and Linux modules | Canonical |
| AWS Round 2 postmortem | incident postmortem and SLO modules | Canonical |
| AWS Round 3 mobile backend | distributed systems, identity, and reliability modules | Canonical foundations present |
| AWS Round 3 secure updates | supply-chain, GitOps, reliability, and observability modules | Canonical foundations present |
| AWS Round 3 disaster recovery | `core/reliability/disaster-recovery/` | Canonical |
| AWS Round 3 observability platform | OpenTelemetry and high-volume observability modules | Canonical |
| AWS Round 3 event platform | distributed systems and overload modules | Canonical foundations present |

## AWS Round 1 question map

| Question | AWS adapter | Canonical prerequisites |
|---|---|---|
| Multi-AZ EKS for millions of users | `tracks/aws/round-1/01-multi-az-eks-millions-users.md` | Kubernetes, node lifecycle, autoscaling, networking, overload, DR, SLOs |
| GitOps with Terraform and Argo CD/Flux | `tracks/aws/round-1/02-gitops-terraform-argocd-flux.md` | GitOps, Terraform ownership, secrets, artifact trust |
| State across accounts and Regions | `tracks/aws/round-1/03-terraform-state-multi-account-region.md` | Terraform state integrity, IAM federation, DR |
| Secure Amazon EKS | `tracks/aws/round-1/04-securing-amazon-eks.md` | workload identity, secrets, policy, tenancy, supply chain |
| Terraform vs CloudFormation | `tracks/aws/round-1/05-terraform-cloudformation-native.md` | IaC tool selection, ownership, drift, policy |
| ASGs, Karpenter, CA, and Spot | `tracks/aws/round-1/06-capacity-autoscaling-karpenter-spot.md` | autoscaling, node images, disruption, overload, SLOs |

## AWS Round 2 question map

| Question | AWS adapter | Canonical prerequisites |
|---|---|---|
| Route 53 to application outage | `tracks/aws/round-2/07-route53-to-application-outage.md` | request-path debugging, DNS/TLS, Envoy path, cohort analysis |
| Kubernetes API latency | `tracks/aws/round-2/08-eks-api-latency-nodes-healthy.md` | control-plane API, etcd, admission, LIST/WATCH, APF, control-plane SLOs |
| Application API latency | `tracks/aws/round-2/08b-application-api-latency-nodes-healthy.md` | evidence hierarchy, RED/USE, histograms, tracing, profiling, dependency saturation |
| Subset of users fail | `tracks/aws/round-2/09-subset-users-fail-after-deployment.md` | cohort analysis, progressive delivery, routing, cells, partitions |
| Dashboards do not show cause | `tracks/aws/round-2/10-beyond-cloudwatch-dashboards.md` | evidence beyond dashboards, OTel, tracing, profiling |
| Terraform partial apply | `tracks/aws/round-2/11-terraform-partial-apply-recovery.md` | Terraform state integrity |
| Pods restart with healthy probes | `tracks/aws/round-2/12-pods-restart-probes-healthy.md` | runtime debugging, cgroups/OOM, kubelet, controller evidence |
| Large outage postmortem | `tracks/aws/round-2/13-large-aws-outage-postmortem.md` | postmortems, SLO/error budgets, chaos re-test |

## AWS Round 3 question map

| Question | AWS adapter | Canonical prerequisites |
|---|---|---|
| Mobile backend | `tracks/aws/round-3/14-highly-available-mobile-backend.md` | identity, idempotency, command state, notifications, cells, overload, DR |
| Secure software updates | `tracks/aws/round-3/15-global-secure-software-updates.md` | artifact trust, identity, staged rollout, blast radius, telemetry, rollback |
| Multi-Region DR | `tracks/aws/round-3/16-multi-region-disaster-recovery.md` | RTO/RPO, replication, fencing, failover/failback, chaos validation |
| Actionable observability | `tracks/aws/round-3/17-actionable-observability-platform.md` | OTel pipelines, high-volume telemetry, alert quality, SLOs |
| Millions of events/second | `tracks/aws/round-3/18-millions-events-per-second.md` | partitioning, queues, idempotency, backpressure, replay, blast radius |

## Cross-track adapter examples

### Netflix playback 504

Required core reading:

- `core/service-mesh/envoy-request-path-debugging.md`
- `core/incident-response/request-path-debugging.md`
- `core/incident-response/cohort-analysis.md`
- `core/observability/evidence-beyond-dashboards.md`
- `core/reliability/graceful-degradation-overload-blast-radius.md`

Netflix adapter adds manifest generation, DRM and entitlement, CDN/origin behavior, segment transfer, playback-start, and rebuffer SLIs.

### Tesla OTA fleet rollout

Required core reading:

- `core/security/software-supply-chain/artifact-trust-slsa-sigstore.md`
- `core/delivery-gitops/gitops-progressive-delivery.md`
- `core/reliability/graceful-degradation-overload-blast-radius.md`
- `core/reliability/chaos-engineering-game-days.md`
- `core/observability/high-volume-telemetry-alerting-profiling.md`

Tesla adapter adds intermittent connectivity, hardware-generation compatibility, battery/bandwidth constraints, vehicle-local safety authority, and delayed rollback populations.

### AWS multi-AZ EKS at hyperscale

Required core reading:

- `core/kubernetes/README.md`
- `core/security/README.md`
- `core/reliability/README.md`
- `core/observability/README.md`
- `core/distributed-systems/README.md`

AWS adapter adds EKS boundaries, VPC CNI, AWS Load Balancer Controller, Karpenter, managed node groups, AWS identity, service quotas, and AWS regional failure domains.

## Executable lab map

| Lab | Canonical topics |
|---|---|
| `labs/reliability/01-error-budget/` | SLOs, burn rates, protected cohorts |
| `labs/reliability/02-disaster-recovery-state-machine/` | fencing, failover, failback, reconciliation |
| `labs/reliability/03-overload-blast-radius/` | retries, admission, tenant fairness, failover capacity, replay |
| `labs/observability/01-telemetry-pipeline/` | quotas, cardinality, priority, loss, freshness, sampling |
| `labs/kubernetes/` | node repair and Kubernetes failure state machines |
| `labs/platform-engineering/` | golden paths, policy, tenancy, artifact trust, fleets, secrets |
| `labs/distributed-systems/` | retries, outbox, fencing, caching, rebalancing, delivery semantics |
| `labs/aws/` | AWS/EKS-shaped incident and control-loop practice |

## Development rule

Before writing a new chapter:

1. Search `core/` for an existing canonical explanation.
2. Extend the shared chapter when the knowledge is company-neutral.
3. Create a track adapter only for company-, platform-, or domain-specific reasoning.
4. Link rather than copy after canonical coverage reaches parity.
5. Treat current deep track chapters as migration sources, not competing permanent textbooks.
6. Deprecate duplicated text after parity review and preserve only scenario-specific adapters.
