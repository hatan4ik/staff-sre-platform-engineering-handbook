# AWS DevOps / EKS Interview Track

A Staff/Principal-level interview curriculum for AWS infrastructure, Amazon EKS, Infrastructure as Code, GitOps, incident response, reliability, observability, distributed systems, and technical leadership.

> These are hypothetical interview scenarios and independent engineering exercises. They do not claim knowledge of Amazon's internal architecture or interview process.

## How this track fits the handbook

Reusable engineering foundations remain canonical in this repository's `core/` modules. This AWS track adds:

- AWS service selection and AWS-specific failure modes;
- Amazon EKS implementation details;
- multi-account and multi-region operating models;
- AWS-native identity, networking, security, observability, and recovery procedures;
- concise interview answers, whiteboard flows, adversarial follow-ups, and practical commands.

The track does **not** duplicate generic Kubernetes, Linux, Terraform, distributed-systems, security, autoscaling, incident-response, observability, reliability, service-mesh, or SRE textbooks.

## Canonical prerequisites

Use these shared chapters before the AWS-specific adapters:

### Kubernetes and platform runtime

- [`core/kubernetes/control-plane/api-server-etcd-list-watch-admission.md`](../../core/kubernetes/control-plane/api-server-etcd-list-watch-admission.md) — API-server, etcd, admission, APF, LIST/WATCH, controller queues, SLOs, and incident response.
- [`core/kubernetes/scheduling/scheduler-placement-diagnostics.md`](../../core/kubernetes/scheduling/scheduler-placement-diagnostics.md) — scheduler queues, requests, taints, affinity, topology spread, volume/device constraints, preemption, and autoscaler handoff.
- [`core/kubernetes/networking/service-dns-ingress-gateway-request-path.md`](../../core/kubernetes/networking/service-dns-ingress-gateway-request-path.md) — Services, EndpointSlices, CNI, DNS, NetworkPolicy, Ingress, Gateway API, TLS, dual stack, MTU, conntrack, and path debugging.
- [`core/kubernetes/storage/csi-stateful-recovery.md`](../../core/kubernetes/storage/csi-stateful-recovery.md) — PVC/PV/StorageClass, CSI provisioning, attach/detach, topology, snapshots, writer fencing, restore, and stateful recovery.
- [`core/kubernetes/workload-lifecycle/probes-startup-shutdown-drain.md`](../../core/kubernetes/workload-lifecycle/probes-startup-shutdown-drain.md) — startup/liveness/readiness semantics, EndpointSlice propagation, graceful drain, long-lived connections, PDBs, and rollout safety.
- [`core/kubernetes/runtime-debugging.md`](../../core/kubernetes/runtime-debugging.md) — container restart, pod replacement, OOM, eviction, probes, PID 1, kubelet, runtime, and controller evidence.
- [`core/kubernetes/node-lifecycle/failure-fencing-repair.md`](../../core/kubernetes/node-lifecycle/failure-fencing-repair.md) — node health, fencing, drain, repair, and replacement.
- [`core/kubernetes/node-images/qualification-promotion-rollback.md`](../../core/kubernetes/node-images/qualification-promotion-rollback.md) — immutable image qualification, canaries, rollout rings, and rollback.
- [`core/kubernetes/autoscaling/control-loops-capacity-realization.md`](../../core/kubernetes/autoscaling/control-loops-capacity-realization.md) — HPA, VPA, KEDA, scheduler and node-supply loops, Cluster Autoscaler versus Karpenter, disruption, topology, and capacity realization.

### Security and delivery

- [`core/security/identity/workload-identity-federation.md`](../../core/security/identity/workload-identity-federation.md) — Kubernetes projected tokens, EKS Pod Identity versus IRSA, cross-cloud federation, SPIFFE/SPIRE, node-role protection, rotation, and incident evidence.
- [`core/security/secrets/secret-delivery-rotation-kubernetes.md`](../../core/security/secrets/secret-delivery-rotation-kubernetes.md) — secret authority, dynamic credentials, delivery, rotation, revocation, and regional recovery.
- [`core/security/software-supply-chain/artifact-trust-slsa-sigstore.md`](../../core/security/software-supply-chain/artifact-trust-slsa-sigstore.md) — digests, provenance, SBOMs, signatures, attestations, deployment verification, and compromise response.
- [`core/infrastructure-as-code/terraform-state-integrity.md`](../../core/infrastructure-as-code/terraform-state-integrity.md) — state integrity, current S3 lock files, legacy DynamoDB locking, partial-apply reconciliation, and one-writer recovery.
- [`core/infrastructure-as-code/tool-selection-and-governance.md`](../../core/infrastructure-as-code/tool-selection-and-governance.md) — Terraform, CloudFormation, CDK, policy, ownership, and migration principles.
- [`core/delivery-gitops/gitops-progressive-delivery.md`](../../core/delivery-gitops/gitops-progressive-delivery.md) — reconciliation, promotion, progressive delivery, rollback, pruning, and resource ownership.

### Incidents, observability, and reliability

- [`core/incident-response/request-path-debugging.md`](../../core/incident-response/request-path-debugging.md) — client-to-dependency path isolation, status-code ownership, paired evidence, hypothesis discipline, mitigation, and recovery proof.
- [`core/incident-response/cohort-analysis.md`](../../core/incident-response/cohort-analysis.md) — partial failures, denominators, confounding, release and infrastructure cohorts, and narrow mitigation.
- [`core/incident-response/postmortems.md`](../../core/incident-response/postmortems.md) — impact, causal analysis, response quality, recovery debt, corrective-action governance, and verification.
- [`core/observability/evidence-beyond-dashboards.md`](../../core/observability/evidence-beyond-dashboards.md) — alert validation, traces, logs, profiles, changes, network evidence, and hypothesis verification.
- [`core/observability/opentelemetry-pipelines-and-governance.md`](../../core/observability/opentelemetry-pipelines-and-governance.md) — instrumentation contracts, Collector architecture, queues, sampling, tenancy, redaction, loss, freshness, and synthetic telemetry.
- [`core/observability/high-volume-telemetry-alerting-profiling.md`](../../core/observability/high-volume-telemetry-alerting-profiling.md) — metrics, cardinality, histograms, tracing, profiling, alert quality, ingest, retention, and query governance.
- [`core/reliability/slo/error-budgets.md`](../../core/reliability/slo/error-budgets.md) — user journeys, good-event semantics, denominator integrity, budgets, burn rates, protected cohorts, and release policy.
- [`core/reliability/graceful-degradation-overload-blast-radius.md`](../../core/reliability/graceful-degradation-overload-blast-radius.md) — deadlines, retry budgets, concurrency, admission, load shedding, degraded modes, cells, failover safety, and backlog recovery.
- [`core/reliability/disaster-recovery/README.md`](../../core/reliability/disaster-recovery/README.md) — RTO/RPO, authority, fencing, failover, failback, and reconciliation.
- [`core/reliability/chaos-engineering-game-days.md`](../../core/reliability/chaos-engineering-game-days.md) — hypotheses, steady state, abort conditions, game-day governance, and re-testing.

### Service mesh and distributed systems

- [`core/service-mesh/fine-grained-service-discovery.md`](../../core/service-mesh/fine-grained-service-discovery.md) — service discovery, xDS, dependency scope, control-plane failure, and convergence.
- [`core/service-mesh/envoy-request-path-debugging.md`](../../core/service-mesh/envoy-request-path-debugging.md) — Envoy 504s, resets, timeouts, retries, connection pools, circuit breakers, and effective configuration.
- [`core/service-mesh/mtls-sds-dns-multicluster.md`](../../core/service-mesh/mtls-sds-dns-multicluster.md) — mTLS, SDS, trust, DNS capture, gateways, multi-cluster, and failover.
- [`core/linux/README.md`](../../core/linux/README.md) and [`core/distributed-systems/README.md`](../../core/distributed-systems/README.md).

AWS chapters retain AWS-specific implementation details, service limits, failure behavior, commands, and interview framing.

## Staff-level answer method

### Architecture: `SCOPE`

1. **S — Scope:** users, traffic, regions, compliance, RTO/RPO, latency, consistency, and cost constraints.
2. **C — Components:** edge, identity, network, compute, data, messaging, delivery, and observability.
3. **O — Operations:** deployment, scaling, upgrades, backup, restore, security, and ownership.
4. **P — Protection:** failure domains, quotas, overload, retries, blast radius, and rollback.
5. **E — Evidence:** SLIs, load tests, game days, recovery tests, and decision records.

### Incident response: `STABILIZE`

1. **S — State the impact and establish incident command.**
2. **T — Time-box triage and preserve evidence.**
3. **A — Analyze from the user path inward.**
4. **B — Bound the blast radius by cohort, AZ, version, and dependency.**
5. **I — Implement the safest mitigation.**
6. **L — Look for recovery in user-facing SLIs.**
7. **I — Investigate root cause after stabilization.**
8. **Z — Zero recurrence through owned corrective actions.**
9. **E — Exercise the repaired design through tests and game days.**

## Interview question sequence

### Round 1 — AWS infrastructure, Kubernetes, and Infrastructure as Code

1. [Highly available multi-AZ EKS platform for millions of concurrent users](round-1/01-multi-az-eks-millions-users.md)
2. [GitOps on EKS with Terraform and Argo CD or Flux](round-1/02-gitops-terraform-argocd-flux.md)
3. [Terraform state across AWS accounts and Regions](round-1/03-terraform-state-multi-account-region.md)
4. [Securing Amazon EKS with IAM, pod identity, VPC controls, and Secrets Manager](round-1/04-securing-amazon-eks.md)
5. [Terraform versus CloudFormation and AWS-native provisioning](round-1/05-terraform-cloudformation-native.md)
6. [Capacity planning and autoscaling with ASGs, Karpenter, Cluster Autoscaler, and Spot](round-1/06-capacity-autoscaling-karpenter-spot.md)

### Round 2 — Incident response, troubleshooting, and reliability

7. [Route 53-to-application outage troubleshooting](round-2/07-route53-to-application-outage.md)
8. API latency while nodes remain healthy:
   - [Kubernetes API-server and control-plane latency](round-2/08-eks-api-latency-nodes-healthy.md)
   - [Customer-facing application API latency](round-2/08b-application-api-latency-nodes-healthy.md)
9. [Deployment succeeds but only a subset of users fail](round-2/09-subset-users-fail-after-deployment.md)
10. [CloudWatch detects errors but dashboards do not reveal root cause](round-2/10-beyond-cloudwatch-dashboards.md)
11. [Terraform apply fails midway and leaves partial infrastructure](round-2/11-terraform-partial-apply-recovery.md)
12. [EKS pods restart continuously while probes remain healthy](round-2/12-pods-restart-probes-healthy.md)
13. [Postmortem after a large AWS production outage](round-2/13-large-aws-outage-postmortem.md)

### Round 3 — AWS system design, scalability, and leadership

14. [Highly available mobile backend](round-3/14-highly-available-mobile-backend.md)
15. [Global secure software-update delivery](round-3/15-global-secure-software-updates.md)
16. [Multi-Region disaster recovery](round-3/16-multi-region-disaster-recovery.md)
17. [Actionable observability platform](round-3/17-actionable-observability-platform.md)
18. [Millions of real-time events per second](round-3/18-millions-events-per-second.md)

## Chapter completion standard

Each completed chapter contains:

- a 90-second interview answer;
- explicit assumptions and scope;
- architecture, request-path, or control-flow diagrams;
- production investigation or implementation details;
- security and failure-mode analysis;
- mitigation, rollback, and recovery validation;
- observability and SLOs;
- adversarial follow-up questions;
- common weak answers to avoid.

## Current implementation status

| Layer | Scope | Status |
|---|---|---|
| Round 1 | EKS, GitOps, Terraform, security, provisioning, autoscaling | Complete on `main` |
| Round 2 | Incidents, troubleshooting, recovery, postmortems | Complete on `main` |
| Round 3 | System design, global delivery, DR, observability, event platforms | Complete on `main` |
| Calibration | FAANG board review, spoken drills, scorecard | Complete initial set |
| Personal evidence | Truthful production story bank and claim boundaries | Complete initial set; missing metrics are explicitly marked |
| Practice | Interview-day cheatsheet, cold baseline, and 30-day execution plan | Complete initial set |
| Labs | Canonical and track-specific AWS, Terraform, Kubernetes, reliability, and stream exercises | Complete initial set |

All 18 source questions have Staff/Principal-level answer chapters. The practice system covers deep study, concise delivery, adversarial scoring, executable labs, truthful personal evidence, and daily execution.

## Practice and calibration assets

Start with the [practice index](PRACTICE_INDEX.md).

- [FAANG engineering board review](FAANG_BOARD_REVIEW.md)
- [Mock interview scorecard](MOCK_INTERVIEW_SCORECARD.md)
- [Spoken answer drills](SPOKEN_ANSWER_DRILLS.md)
- [Truthful personal production story bank](PERSONAL_STORY_BANK.md)
- [Evidence completion worksheet](EVIDENCE_COMPLETION_WORKSHEET.md)
- [Interview-day cheatsheet](INTERVIEW_DAY_CHEATSHEET.md)
- [30-day execution plan](30_DAY_EXECUTION_PLAN.md)
- [Official source index](OFFICIAL_SOURCES.md)
- [Canonical AWS and EKS incident labs](../../labs/aws/README.md)
- [Canonical Kubernetes labs, including disposable Kind conformance](../../labs/kubernetes/README.md)
- [Canonical reliability labs](../../labs/reliability/README.md)
- [Canonical observability lab](../../labs/observability/README.md)
- [Additional track-specific practice labs](labs/README.md)

Recommended loop:

```text
read one chapter
  -> deliver the 90-second answer
  -> run the related lab where available
  -> attach one truthful production story
  -> accept adversarial follow-ups
  -> score the result
  -> tighten unsupported claims
```

## Truth discipline

- Keep production experience, assignment/lab evidence, and hypothetical architecture visibly separate.
- Do not invent scale, availability, cost, outage, or delivery metrics.
- Verify current AWS quotas and service behavior from primary sources.
- Prefer a precise uncertainty statement over a false exact number.
- Principal readiness requires evidence of organizational influence and measurable outcomes, not technical breadth alone.

## Source discipline

Version-sensitive behavior must be checked against official AWS, Kubernetes, HashiCorp, Argo CD, Flux, Karpenter, OpenTelemetry, Prometheus, Grafana, Envoy, and Istio documentation.

The interview answer must distinguish a documented guarantee from a design assumption.
