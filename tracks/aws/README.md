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

The track does **not** duplicate generic Kubernetes, Linux, Terraform, distributed-systems, or SRE textbooks.

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
8. [EKS API latency doubles while nodes remain healthy](round-2/08-eks-api-latency-nodes-healthy.md)
9. Deployment succeeds but only a subset of users fail
10. CloudWatch detects errors but dashboards do not reveal root cause
11. Terraform apply fails midway and leaves partial infrastructure
12. EKS pods restart continuously while probes remain healthy
13. Postmortem after a large AWS production outage

### Round 3 — AWS system design, scalability, and leadership

14. Highly available mobile backend for identity, notifications, remote access, and preferences
15. Global secure software-update delivery to millions of devices
16. Multi-region disaster recovery with minimal downtime and automated failover
17. Actionable observability with CloudWatch, OpenTelemetry, X-Ray, Prometheus, and Grafana
18. Millions of real-time events per second with Kinesis, SQS, SNS, EventBridge, Lambda, and EKS

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
| Round 2 | Incidents, troubleshooting, recovery, postmortems | In progress — questions 7–8 complete |
| Round 3 | System design, global delivery, DR, observability, event platforms | Planned after Round 2 |

## Current-version notes

- Amazon EKS manages a highly available control plane across three Availability Zones in a Region; the customer remains responsible for data-plane and workload reliability.
- EKS Pod Identity is the preferred default for many new same-account workloads; IRSA remains fully supported and is still useful, especially where its trust model or direct cross-account behavior fits better.
- For new Terraform S3 backends, evaluate native S3 lockfiles with `use_lockfile = true`. DynamoDB-based locking remains relevant in existing estates and in the interview prompt, but HashiCorp marks it deprecated.
- Karpenter is generally the preferred dynamic node-provisioning mechanism for heterogeneous EKS workloads; Cluster Autoscaler remains appropriate for stable, pre-defined managed node-group fleets.

## Source discipline

Technical behavior should be verified against primary sources:

- AWS EKS Best Practices Guides
- AWS service documentation and quotas
- Kubernetes documentation
- HashiCorp Terraform documentation
- Argo CD and Flux documentation
- Karpenter documentation

The interview answer must distinguish a documented guarantee from a design assumption.
