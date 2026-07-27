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
| HPA, scheduler, Cluster Autoscaler/Karpenter | `core/kubernetes/autoscaling/` | Yes | Yes | Yes |
| Terraform state, locking, drift | `core/infrastructure-as-code/` | Yes | Yes | Yes |
| GitOps and progressive delivery | `core/delivery-gitops/` | Yes | Yes | Yes |
| IAM and workload identity | `core/security/identity/` | Yes | Yes | Yes |
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
| `netflix-devops-interview/curriculum/03-multicloud-routing-identity-secrets.md` | `core/cloud/multicloud-routing-identity-secrets.md` |
| `netflix-devops-interview/curriculum/04-eks-systemd-node-failure-repair.md` | `core/kubernetes/node-lifecycle/failure-fencing-repair.md` |
| Netflix probe scenario | `core/reliability/business-aware-probes.md` |
| Netflix DNS scenario | `core/networking/kubernetes-dns-failure.md` |
| Netflix Terraform scenario | `core/infrastructure-as-code/terraform-state-integrity.md` |
| Netflix HPA scenario | `core/kubernetes/autoscaling/hpa-control-loops.md` |
| Tesla Kubernetes/fleet chapter foundations | Shared Kubernetes, multi-region, GitOps, identity, and reliability chapters |
| AWS Round 1 multi-AZ EKS chapter | `core/kubernetes/`, `core/networking/`, `core/reliability/`, and `core/cloud/` |
| AWS Round 1 GitOps chapter | `core/delivery-gitops/` and `core/infrastructure-as-code/` |
| AWS Round 1 Terraform-state chapter | `core/infrastructure-as-code/terraform-state-integrity.md` |
| AWS Round 1 EKS-security chapter | `core/security/identity/`, `core/security/network/`, and `core/security/secrets/` |
| AWS Round 1 provisioning-tool chapter | `core/infrastructure-as-code/tool-selection-and-governance.md` |
| AWS Round 1 autoscaling chapter | `core/kubernetes/autoscaling/` and `core/reliability/capacity/` |

## AWS Round 1 question map

| Question | AWS adapter | Canonical prerequisites |
|---|---|---|
| Multi-AZ EKS for millions of users | `tracks/aws/round-1/01-multi-az-eks-millions-users.md` | Kubernetes reliability, networking, data systems, overload, capacity |
| GitOps with Terraform and Argo CD/Flux | `tracks/aws/round-1/02-gitops-terraform-argocd-flux.md` | GitOps, progressive delivery, Terraform ownership, secrets |
| State across accounts and Regions | `tracks/aws/round-1/03-terraform-state-multi-account-region.md` | Terraform state integrity, locking, recovery, IAM federation |
| Secure Amazon EKS | `tracks/aws/round-1/04-securing-amazon-eks.md` | IAM, workload identity, network policy, pod security, secret delivery |
| Terraform vs CloudFormation | `tracks/aws/round-1/05-terraform-cloudformation-native.md` | IaC ownership, drift, policy, fleet governance |
| ASGs, Karpenter, CA, and Spot | `tracks/aws/round-1/06-capacity-autoscaling-karpenter-spot.md` | scheduling, HPA, capacity, disruption, overload |

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

- `core/delivery-gitops/progressive-delivery.md`
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
- `core/networking/`
- `core/reliability/`
- `core/distributed-systems/`

AWS adapter adds:

- EKS managed control-plane and customer data-plane boundaries.
- AWS Load Balancer Controller, VPC CNI, subnet IP, and quota behavior.
- Karpenter, managed node groups, EKS Pod Identity, and IRSA.
- CloudFront, Route 53, Global Accelerator, ElastiCache, DynamoDB, Aurora, SQS, and Kinesis selection.
- AWS account, Region, and Availability Zone failure domains.

## Development rule

Before writing a new chapter:

1. Search `core/` for an existing canonical explanation.
2. Extend the shared chapter when the knowledge is company-neutral.
3. Create a track adapter only for company-, platform-, or domain-specific reasoning.
4. Link rather than copy after canonical coverage reaches parity.
5. Treat current deep track chapters as migration sources, not competing permanent textbooks.
6. Deprecate duplicated text after the canonical chapter is verified.