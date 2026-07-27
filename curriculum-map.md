# Consolidated Curriculum Map

This map prevents duplicate chapter development across company- and platform-specific interview tracks.

## Shared-core ownership matrix

| Topic | Canonical core path | Netflix use | Tesla use | AWS use |
|---|---|---:|---:|---:|
| Linux boot, systemd, processes, cgroups | `core/linux/` | Yes | Yes | Yes |
| TCP, DNS, TLS, HTTP, packet debugging | `core/networking/` | Yes | Yes | Yes |
| Kubernetes control plane and scheduling | `core/kubernetes/` | Yes | Yes | Yes |
| Node health, fencing, drain, repair | `core/kubernetes/node-lifecycle/` | Yes | Yes | Yes |
| Custom AMI/node-image qualification | `core/kubernetes/node-images/` | Yes | Yes | Yes |
| Service discovery, Envoy, Istio, xDS | `core/service-mesh/` | Yes | Yes | Yes |
| eBPF, Cilium, Hubble, Falco, Tetragon | `core/ebpf-security/` | Yes | Yes | Yes |
| OpenTelemetry, metrics, logs, traces | `core/observability/` | Yes | Yes | Yes |
| Probes, graceful degradation, backpressure | `core/reliability/` | Yes | Yes | Yes |
| HPA, VPA, KEDA, scheduler, Cluster Autoscaler, Karpenter | `core/kubernetes/autoscaling/` | Yes | Yes | Yes |
| Terraform state, locking, drift | `core/infrastructure-as-code/` | Yes | Yes | Yes |
| GitOps and progressive delivery | `core/delivery-gitops/` | Yes | Yes | Yes |
| Workload identity, federation, SPIFFE, cloud IAM | `core/security/identity/` | Yes | Yes | Yes |
| Network isolation and secrets | `core/security/` | Yes | Yes | Yes |
| SLOs and error budgets | `core/reliability/slo/` | Yes | Yes | Yes |
| Incident command and RCA | `core/incident-response/` | Yes | Yes | Yes |
| Multi-region and disaster recovery | `core/reliability/disaster-recovery/` | Yes | Yes | Yes |
| Messaging, streams, idempotency, and backpressure | `core/distributed-systems/` | Yes | Yes | Yes |
| Chaos engineering | `core/reliability/chaos/` | Yes | Yes | Yes |
| Staff/Principal leadership and ROI | `core/leadership/` | Yes | Yes | Yes |

## Initial source-to-canonical mapping

| Existing source | New canonical destination |
|---|---|
| `netflix-devops-interview/curriculum/01-fine-grained-service-discovery.md` | `core/service-mesh/fine-grained-service-discovery.md` |
| `netflix-devops-interview/curriculum/02-ebpf-cilium-runtime-security.md` | `core/ebpf-security/cilium-hubble-falco-tetragon.md` |
| Identity sections of `netflix-devops-interview/curriculum/03-multicloud-routing-identity-secrets.md` | `core/security/identity/workload-identity-federation.md` |
| Routing and secret-serving sections of Netflix chapter 3 | future `core/cloud/` and `core/security/secrets/` chapters |
| `netflix-devops-interview/curriculum/04-eks-systemd-node-failure-repair.md` | `core/kubernetes/node-lifecycle/failure-fencing-repair.md` |
| Netflix probe scenario | `core/reliability/business-aware-probes.md` |
| Netflix DNS scenario | `core/networking/kubernetes-dns-failure.md` |
| Netflix Terraform scenario | `core/infrastructure-as-code/terraform-state-integrity.md` |
| Netflix HPA scenario | `core/kubernetes/autoscaling/control-loops-capacity-realization.md` |
| Tesla Kubernetes/fleet chapter foundations | Shared Kubernetes, multi-region, GitOps, identity, and reliability chapters |
| AWS Round 1 multi-AZ EKS chapter | `core/kubernetes/`, `core/networking/`, `core/reliability/`, and `core/cloud/` |
| AWS Round 1 GitOps chapter | `core/delivery-gitops/gitops-progressive-delivery.md` and `core/infrastructure-as-code/` |
| AWS Round 1 Terraform-state chapter | `core/infrastructure-as-code/terraform-state-integrity.md` |
| AWS Round 1 EKS-security chapter | `core/security/identity/workload-identity-federation.md`, `core/security/network/`, and `core/security/secrets/` |
| AWS Round 1 provisioning-tool chapter | `core/infrastructure-as-code/tool-selection-and-governance.md` |
| AWS Round 1 autoscaling chapter | `core/kubernetes/autoscaling/control-loops-capacity-realization.md` and `core/reliability/capacity/` |
| AWS Round 2 request-path outage chapter | `core/networking/` and `core/incident-response/request-path-debugging.md` |
| AWS Round 2 control-plane latency chapter | `core/kubernetes/control-plane/` and `core/observability/` |
| AWS Round 2 application-latency chapter | `core/observability/` and `core/reliability/latency-analysis.md` |
| AWS Round 2 cohort-failure chapter | `core/incident-response/cohort-analysis.md` and `core/delivery-gitops/gitops-progressive-delivery.md` |
| AWS Round 2 evidence chapter | `core/observability/evidence-beyond-dashboards.md` |
| AWS Round 2 partial-apply chapter | `core/infrastructure-as-code/terraform-state-integrity.md` |
| AWS Round 2 restart chapter | `core/kubernetes/runtime-debugging.md` and `core/linux/` |
| AWS Round 2 postmortem chapter | `core/incident-response/postmortems.md` and `core/leadership/` |
| AWS Round 3 mobile-backend chapter | `core/security/identity/workload-identity-federation.md`, `core/distributed-systems/`, `core/reliability/`, and `core/cloud/` |
| AWS Round 3 secure-update chapter | `core/delivery-gitops/`, `core/security/supply-chain/`, `core/reliability/blast-radius.md`, and `core/observability/high-volume-telemetry.md` |
| AWS Round 3 disaster-recovery chapter | `core/reliability/disaster-recovery/`, `core/distributed-systems/replication/`, and `core/networking/` |
| AWS Round 3 observability-platform chapter | `core/observability/`, `core/reliability/slo/`, and `core/incident-response/` |
| AWS Round 3 event-platform chapter | `core/distributed-systems/messaging/`, `core/reliability/backpressure/`, and `core/cloud/streaming/` |

## AWS Round 1 question map

| Question | AWS adapter | Canonical prerequisites |
|---|---|---|
| Multi-AZ EKS for millions of users | `tracks/aws/round-1/01-multi-az-eks-millions-users.md` | Kubernetes reliability, networking, data systems, overload, capacity |
| GitOps with Terraform and Argo CD/Flux | `tracks/aws/round-1/02-gitops-terraform-argocd-flux.md` | `core/delivery-gitops/gitops-progressive-delivery.md`, Terraform ownership, secrets |
| State across accounts and Regions | `tracks/aws/round-1/03-terraform-state-multi-account-region.md` | `core/infrastructure-as-code/terraform-state-integrity.md`, IAM federation |
| Secure Amazon EKS | `tracks/aws/round-1/04-securing-amazon-eks.md` | `core/security/identity/workload-identity-federation.md`, network policy, pod security, secret delivery |
| Terraform vs CloudFormation | `tracks/aws/round-1/05-terraform-cloudformation-native.md` | `core/infrastructure-as-code/tool-selection-and-governance.md`, drift, policy |
| ASGs, Karpenter, CA, and Spot | `tracks/aws/round-1/06-capacity-autoscaling-karpenter-spot.md` | `core/kubernetes/autoscaling/control-loops-capacity-realization.md`, disruption, overload |

## AWS Round 2 question map

| Question | AWS adapter | Canonical prerequisites |
|---|---|---|
| Route 53 to application outage | `tracks/aws/round-2/07-route53-to-application-outage.md` | DNS, TLS, edge, load balancing, VPC, Kubernetes request paths |
| Kubernetes API latency | `tracks/aws/round-2/08-eks-api-latency-nodes-healthy.md` | API-server behavior, LIST/WATCH, admission, controller load, control-plane SLOs |
| Application API latency | `tracks/aws/round-2/08b-application-api-latency-nodes-healthy.md` | RED/USE, histograms, tracing, profiling, dependency saturation |
| Subset of users fail | `tracks/aws/round-2/09-subset-users-fail-after-deployment.md` | cohort analysis, progressive delivery, routing, data partitions |
| Dashboards do not show cause | `tracks/aws/round-2/10-beyond-cloudwatch-dashboards.md` | logs, traces, changes, configuration, network evidence |
| Terraform partial apply | `tracks/aws/round-2/11-terraform-partial-apply-recovery.md` | `core/infrastructure-as-code/terraform-state-integrity.md` |
| Pods restart with healthy probes | `tracks/aws/round-2/12-pods-restart-probes-healthy.md` | pod lifecycle, cgroups, OOM, kubelet, disruption controllers |
| Large outage postmortem | `tracks/aws/round-2/13-large-aws-outage-postmortem.md` | SLOs, incident command, causal analysis, corrective actions |

## AWS Round 3 question map

| Question | AWS adapter | Canonical prerequisites |
|---|---|---|
| Mobile backend | `tracks/aws/round-3/14-highly-available-mobile-backend.md` | authentication, authorization, idempotency, command state, notification delivery, multi-Region cells |
| Secure software updates | `tracks/aws/round-3/15-global-secure-software-updates.md` | artifact provenance, PKI, staged rollout, device-local rollback, high-volume telemetry |
| Multi-Region DR | `tracks/aws/round-3/16-multi-region-disaster-recovery.md` | RTO/RPO, replication, fencing, routing, failover/failback, data reconciliation |
| Actionable observability | `tracks/aws/round-3/17-actionable-observability-platform.md` | OpenTelemetry, RED/USE, Prometheus, tracing, SLO burn alerts, alert routing |
| Millions of events/second | `tracks/aws/round-3/18-millions-events-per-second.md` | partitioning, streams, queues, idempotency, backpressure, replay, multi-Region ingestion |

## Example question adapters

### Netflix playback 504

Required core reading:

- `core/networking/http-timeouts.md`
- `core/service-mesh/envoy-debugging.md`
- `core/observability/distributed-tracing.md`
- `core/reliability/graceful-degradation.md`

Netflix adapter adds:

- Manifest generation.
- DRM and entitlement.
- CDN/origin behavior.
- Segment and byte-range transfer.
- Playback-start and rebuffer SLIs.

### Tesla OTA fleet rollout

Required core reading:

- `core/delivery-gitops/gitops-progressive-delivery.md`
- `core/security/identity/workload-identity-federation.md`
- `core/reliability/blast-radius.md`
- `core/cloud/pki-certificate-rotation.md`
- `core/observability/high-volume-telemetry.md`
- `core/incident-response/rollback-decisions.md`

Tesla adapter adds:

- Intermittent connectivity.
- Hardware-generation compatibility.
- Battery and bandwidth constraints.
- Vehicle-local safety authority.
- Delayed or unreachable rollback populations.

### AWS multi-AZ EKS at hyperscale

Required core reading:

- `core/kubernetes/`
- `core/kubernetes/autoscaling/control-loops-capacity-realization.md`
- `core/security/identity/workload-identity-federation.md`
- `core/networking/`
- `core/reliability/`
- `core/distributed-systems/`

AWS adapter adds:

- EKS managed control-plane and customer data-plane boundaries.
- AWS Load Balancer Controller, VPC CNI, subnet IP, and quota behavior.
- Karpenter, managed node groups, EKS Pod Identity, and IRSA.
- CloudFront, Route 53, Global Accelerator, ElastiCache, DynamoDB, Aurora, SQS, and Kinesis selection.
- AWS account, Region, and Availability Zone failure domains.

### AWS partial-user outage

Required core reading:

- `core/incident-response/cohort-analysis.md`
- `core/networking/`
- `core/delivery-gitops/gitops-progressive-delivery.md`
- `core/distributed-systems/partitioning.md`

AWS adapter adds:

- Route 53 and resolver cohorts.
- WAF labels and CloudFront edge behavior.
- ALB targets, Availability Zones, VPC paths, EKS pod versions, and data shards.
- CloudTrail, Config, AWS Health, and CloudWatch evidence sources.

### AWS secure fleet update

Required core reading:

- `core/security/identity/workload-identity-federation.md`
- `core/security/supply-chain/`
- `core/delivery-gitops/gitops-progressive-delivery.md`
- `core/reliability/blast-radius.md`
- `core/distributed-systems/idempotency.md`
- `core/observability/high-volume-telemetry.md`

AWS adapter adds:

- AWS IoT Device Management Jobs and Software Package Catalog.
- S3 and CloudFront artifact distribution.
- Device certificates, signed manifests, A/B partitions, and anti-rollback.
- Fleet cohort targeting, rollout rate, timeout, and abort behavior.

## Development rule

Before writing a new chapter:

1. Search `core/` for an existing canonical explanation.
2. Extend the shared chapter when the knowledge is company-neutral.
3. Create a track adapter only for company-, platform-, or domain-specific reasoning.
4. Link rather than copy after canonical coverage reaches parity.
5. Treat current deep track chapters as migration sources, not competing permanent textbooks.
6. Deprecate duplicated text after the canonical chapter is verified.
