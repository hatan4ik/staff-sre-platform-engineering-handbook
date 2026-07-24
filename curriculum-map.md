# Consolidated Curriculum Map

This map prevents duplicate chapter development across company-specific interview tracks.

## Shared-core ownership matrix

| Topic | Canonical core path | Netflix use | Tesla use |
|---|---|---:|---:|
| Linux boot, systemd, processes, cgroups | `core/linux/` | Yes | Yes |
| TCP, DNS, TLS, HTTP, packet debugging | `core/networking/` | Yes | Yes |
| Kubernetes control plane and scheduling | `core/kubernetes/` | Yes | Yes |
| Node health, fencing, drain, repair | `core/kubernetes/node-lifecycle/` | Yes | Yes |
| Custom AMI/node-image qualification | `core/kubernetes/node-images/` | Yes | Yes |
| Service discovery, Envoy, Istio, xDS | `core/service-mesh/` | Yes | Yes |
| eBPF, Cilium, Hubble, Falco, Tetragon | `core/ebpf-security/` | Yes | Yes |
| OpenTelemetry, metrics, logs, traces | `core/observability/` | Yes | Yes |
| Probes, graceful degradation, backpressure | `core/reliability/` | Yes | Yes |
| HPA, scheduler, Cluster Autoscaler/Karpenter | `core/kubernetes/autoscaling/` | Yes | Yes |
| Terraform state, locking, drift | `core/infrastructure-as-code/` | Yes | Yes |
| GitOps and progressive delivery | `core/delivery-gitops/` | Yes | Yes |
| SLOs and error budgets | `core/reliability/slo/` | Yes | Yes |
| Incident command and RCA | `core/incident-response/` | Yes | Yes |
| Multi-region and disaster recovery | `core/reliability/disaster-recovery/` | Yes | Yes |
| Chaos engineering | `core/reliability/chaos/` | Yes | Yes |
| Staff/Principal leadership and ROI | `core/leadership/` | Yes | Yes |

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

## Development rule

Before writing a new chapter:

1. Search `core/` for an existing canonical explanation.
2. Extend the shared chapter when the knowledge is company-neutral.
3. Create a track adapter only for company/domain-specific reasoning.
4. Link rather than copy.
5. Deprecate duplicated text after the canonical chapter is verified.
