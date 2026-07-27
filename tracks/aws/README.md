# AWS DevOps / EKS Interview Track

A Staff/Principal-level interview curriculum for AWS infrastructure, Amazon EKS, Infrastructure as Code, GitOps, incident response, reliability, observability, distributed systems, and technical leadership.

> These are hypothetical interview scenarios and independent engineering exercises. They do not claim knowledge of Amazon's internal architecture or interview process.

## How this track fits the handbook

Reusable engineering foundations remain canonical in this repository's `core/` modules. This AWS track adds:

- AWS service selection and AWS-specific failure modes
- Amazon EKS implementation details
- multi-account and multi-region operating models
- AWS-native identity, networking, security, observability, and recovery procedures
- concise interview answers, whiteboard flows, adversarial follow-ups, and practical commands

The track does **not** duplicate generic Kubernetes, Linux, Terraform, distributed-systems, security, autoscaling, incident-response, observability, or SRE textbooks.

## Canonical prerequisites

Use these shared chapters before the AWS-specific adapters:

- [`core/security/identity/workload-identity-federation.md`](../../core/security/identity/workload-identity-federation.md) — Kubernetes projected tokens, EKS Pod Identity versus IRSA, cross-cloud federation, SPIFFE/SPIRE, node-role protection, rotation, and incident evidence.
- [`core/kubernetes/autoscaling/control-loops-capacity-realization.md`](../../core/kubernetes/autoscaling/control-loops-capacity-realization.md) — HPA, VPA, KEDA, scheduler and node-supply loops, Cluster Autoscaler versus Karpenter, disruption, topology, and capacity-realization SLIs.
- [`core/incident-response/request-path-debugging.md`](../../core/incident-response/request-path-debugging.md) — client-to-dependency path isolation, status-code ownership, paired evidence, hypothesis discipline, reversible mitigation, and external recovery proof.
- [`core/incident-response/cohort-analysis.md`](../../core/incident-response/cohort-analysis.md) — partial failures, denominators, confounding, release and infrastructure cohorts, narrow mitigation, and cohort-specific recovery.
- [`core/observability/evidence-beyond-dashboards.md`](../../core/observability/evidence-beyond-dashboards.md) — alert validation, structured logs, traces, profiles, changes, network and synthetic evidence, high-cardinality governance, and AI-hypothesis verification.
- [`core/infrastructure-as-code/terraform-state-integrity.md`](../../core/infrastructure-as-code/terraform-state-integrity.md) — state integrity, current S3 lock files, legacy DynamoDB locking, partial-apply reconciliation, and one-writer recovery.
- [`core/infrastructure-as-code/tool-selection-and-governance.md`](../../core/infrastructure-as-code/tool-selection-and-governance.md) — Terraform, CloudFormation, CDK, policy, ownership, and migration principles.
- [`core/delivery-gitops/gitops-progressive-delivery.md`](../../core/delivery-gitops/gitops-progressive-delivery.md) — reconciliation, promotion, progressive delivery, rollback, pruning, and resource ownership.
- [`core/service-mesh/fine-grained-service-discovery.md`](../../core/service-mesh/fine-grained-service-discovery.md) — service discovery, xDS, dependency scoping, control-plane failure, and convergence.
- [`core/linux/README.md`](../../core/linux/README.md) and [`core/distributed-systems/README.md`](../../core/distributed-systems/README.md).

AWS chapters retain AWS-specific implementation details, service limits, failure behavior, commands, and interview framing after canonical parity is confirmed.

## Staff-level answer method

Use two repeatable structures throughout the interview.

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
   - [Customer-facing application API latency with CloudWatch, X-Ray, Prometheus, and Grafana](round-2/08b-application-api-latency-nodes-healthy.md)
9. [Deployment succeeds but only a subset of users fail](round-2/09-subset-users-fail-after-deployment.md)
10. [CloudWatch detects errors but dashboards do not reveal root cause](round-2/10-beyond-cloudwatch-dashboards.md)
11. [Terraform apply fails midway and leaves partial infrastructure](round-2/11-terraform-partial-apply-recovery.md)
12. [EKS pods restart continuously while probes remain healthy](round-2/12-pods-restart-probes-healthy.md)
13. [Postmortem after a large AWS production outage](round-2/13-large-aws-outage-postmortem.md)

### Round 3 — AWS system design, scalability, and leadership

14. [Highly available mobile backend for authentication, notifications, remote access, and preferences](round-3/14-highly-available-mobile-backend.md)
15. [Global secure software-update delivery to millions of devices](round-3/15-global-secure-software-updates.md)
16. [Multi-Region disaster recovery with minimal downtime and automated failover](round-3/16-multi-region-disaster-recovery.md)
17. [Actionable observability with CloudWatch, OpenTelemetry, X-Ray, Prometheus, and Grafana](round-3/17-actionable-observability-platform.md)
18. [Millions of real-time events per second with Kinesis, SQS, SNS, EventBridge, Lambda, and EKS](round-3/18-millions-events-per-second.md)

## Chapter completion standard

Each completed chapter contains:

- a 90-second interview answer
- explicit assumptions and scope
- architecture, request-path, or control-flow diagrams
- production investigation or implementation details
- security and failure-mode analysis
- mitigation, rollback, and recovery validation
- observability and SLOs
- adversarial follow-up questions
- common weak answers to avoid

## Current implementation status

| Round | Scope | Status |
|---|---|---|
| Round 1 | EKS, GitOps, Terraform, security, provisioning, autoscaling | Complete on `main` |
| Round 2 | Incidents, troubleshooting, recovery, postmortems | Complete on `main` |
| Round 3 | System design, global delivery, DR, observability, event platforms | Complete on `main` |
| Practice | Board review, spoken drills, scorecard, story mapping | Complete initial set |
| Labs | Cohort rollout, Terraform recovery, restart evidence, workload identity, autoscaling | Complete initial set |

All 18 source questions now have Staff/Principal-level answer chapters. Reusable request-path, cohort-analysis, evidence, identity, autoscaling, GitOps, and Terraform foundations now link to canonical chapters. The next expansion is postmortems, reliability, control-plane/runtime chapters, additional labs, and candidate-specific story completion.

## Practice and calibration assets

- [FAANG engineering board review](FAANG_BOARD_REVIEW.md)
- [Mock interview scorecard](MOCK_INTERVIEW_SCORECARD.md)
- [Spoken answer drills](SPOKEN_ANSWER_DRILLS.md)
- [Personal story matrix](PERSONAL_STORY_MATRIX.md)
- [Official source index](OFFICIAL_SOURCES.md)
- [Executable AWS and EKS interview labs](../../labs/aws/README.md)

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

## Current-version notes

- Amazon EKS manages a highly available control plane across three Availability Zones in a Region; the customer remains responsible for data-plane and workload reliability.
- EKS Pod Identity is the preferred default for many new same-account workloads; IRSA remains fully supported and is still useful, especially where its trust model or direct cross-account behavior fits better.
- For new Terraform S3 backends, evaluate native S3 lockfiles with `use_lockfile = true`. DynamoDB-based locking remains relevant in existing estates and in the interview prompt, but HashiCorp marks it deprecated.
- Karpenter is generally the preferred dynamic node-provisioning mechanism for heterogeneous EKS workloads; Cluster Autoscaler remains appropriate for stable, pre-defined managed node-group fleets.
- For new EKS Container Insights deployments, use the current OpenTelemetry-based path; existing classic deployments may require a separate migration plan.
- CloudWatch investigations can accelerate correlation across telemetry and changes, but generated hypotheses require evidence-based validation.
- CloudTrail Lake is closed to new customers as of May 31, 2026; existing customers can continue, while new incident-analysis designs should use currently supported CloudWatch and durable CloudTrail architectures.
- Cognito supports multi-Region replication for eligible user pools, but applications still own endpoint routing, write-authority limitations, federation configuration, and failover testing.
- The legacy X-Ray SDKs and daemon entered maintenance mode on February 25, 2026; new instrumentation should use OpenTelemetry and export to AWS trace backends.
- Kinesis Data Streams currently supports on-demand and provisioned operating models, including newer on-demand capabilities; capacity claims still require realistic byte rate, partition-key, consumer, and burst tests.

## Source discipline

Technical behavior should be verified against primary sources:

- AWS EKS Best Practices Guides
- AWS service documentation and quotas
- AWS Well-Architected and Builders' Library guidance
- Kubernetes documentation
- HashiCorp Terraform documentation
- Argo CD and Flux documentation
- Karpenter documentation
- OpenTelemetry, Prometheus, and Grafana documentation

The interview answer must distinguish a documented guarantee from a design assumption.
