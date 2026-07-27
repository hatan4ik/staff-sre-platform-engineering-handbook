# AWS Staff/Principal Interview-Day Cheatsheet

Use this as the final review sheet before an interview. It is intentionally compact.

---

# Opening frame

> I have more than 20 years in infrastructure, cloud, DevOps, SRE, and platform engineering. At SES/O3b Networks I operated across AWS, Azure, private cloud, and 11 data centers, with roughly 2,500 managed systems. My strongest value is connecting architecture, automation, incident evidence, and organizational ownership rather than treating each cloud service as an isolated tool.

Do not add a metric that cannot be defended.

---

# Architecture answer structure — SCOPE

```text
S — Scope
    users, RPS, bytes, connections, latency, availability, RTO/RPO,
    consistency, ordering, geography, compliance, cost

C — Components
    edge, identity, network, compute, state, cache, queue/stream,
    delivery, observability

O — Operations
    provisioning, deployment, scaling, upgrades, ownership, runbooks

P — Protection
    failure domains, retries, backpressure, blast radius, rollback,
    fencing, backup/restore

E — Evidence
    load test, SLO, game day, restore test, failover test, decision record
```

## First sentence

> I will state a few assumptions first, because the service choice depends on throughput, consistency, and recovery requirements.

## Second sentence

> The invariant I am protecting is...

Examples:

- one resource has one authoritative reconciler;
- one Terraform state has one writer;
- losing one AZ cannot remove more capacity than the survivors can absorb;
- a remote command is not successful until the device confirms execution;
- old and new Regions cannot both act as the writer;
- duplicate event delivery must not create duplicate business effect.

---

# Incident answer structure — STABILIZE

```text
S — State user impact and establish incident command
T — Time-box triage and preserve ephemeral evidence
A — Analyze the exact request, event, or control path
B — Bound by version, AZ, Region, tenant, node, shard, or dependency
I — Implement the smallest reversible mitigation
L — Look for recovery in user-facing SLIs
I — Investigate root cause after stabilization
Z — Zero recurrence through owned corrective actions
E — Exercise the repaired design
```

## First incident sentence

> I first define the customer impact, start one UTC timeline, freeze unrelated changes, and capture one failing transaction before changing the system.

## Four questions at every boundary

```text
Did the request/event arrive?
Did policy allow it?
Did the component process it?
Did the response or acknowledgement return?
```

---

# The 18 invariants

| # | Question | Invariant |
|---:|---|---|
| 1 | EKS at scale | capacity must survive the largest planned failure domain |
| 2 | GitOps | one resource, one authoritative reconciler |
| 3 | Terraform state | state is a privileged database with one writer |
| 4 | EKS security | every human, workload, node, and artifact has a bounded trust identity |
| 5 | IaC tools | resource ownership matters more than tool ideology |
| 6 | Autoscaling | pod demand and node supply are separate control loops |
| 7 | Outage path | trace one real request outside-in |
| 8 | Latency | metrics locate; traces allocate; runtime evidence explains |
| 9 | Partial users | compare matched failing and healthy cohorts; control confounding |
| 10 | No root cause on dashboard | move from aggregate metric to raw evidence and changes |
| 11 | Partial apply | reconcile configuration, state, and actual resources |
| 12 | Restarts | identify process, pod, node, or controller as terminating actor |
| 13 | Postmortem | the incident is complete only when the system changes |
| 14 | Mobile backend | broker acceptance is not remote execution |
| 15 | Secure updates | signed does not mean safe; device preserves trusted rollback |
| 16 | Multi-Region DR | failover is controlled authority transfer |
| 17 | Observability | page only when a human action can protect users |
| 18 | Event platform | partitioning, idempotency, backpressure, and replay are the architecture |

---

# Personal evidence anchors

Use the exact evidence class honestly.

## Production scale

- SES/O3b Networks: AWS, Azure, private cloud, 11 data centers.
- Approximately 2,500 managed systems.
- Monitoring across more than 1,000 devices/platforms.
- Level 3/4 escalation and permanent-fix leadership.
- Runbooks and tooling adopted by Level 1 NOC.
- Team of five SRE/DevOps engineers in a documented role version.

## Large data work

- Approximately 45 TB uncompressed / 6 TB compressed MySQL migration workflow.
- MySQL 5.7, XFS, LVM, MyISAM-to-InnoDB conversion.
- Streaming transforms and per-database restartability.

## Earlier infrastructure

- Alexander Street Press: high-traffic Linux/database estate, approximately 100 TB iSCSI storage, approximately $100K annual infrastructure cost reduction.
- Pipl: more than 120 Linux/Windows servers, HAProxy, caching, MySQL HA, AWS/EC2, monitoring, backup, automation.

## Current hands-on evidence

- Terraform AKS/ACR/Key Vault/VNet/Jenkins/ingress assignment.
- Azure load-balancer identity/permission troubleshooting.
- Azure DevOps-to-GitHub repository migration.
- AWS interview labs for Terraform recovery, Kubernetes restart forensics, and stream backpressure.

State assignments and labs as assignments and labs, not production.

---

# Strong phrases

- “The invariant I am protecting is...”
- “The source of truth is...”
- “The writer authority is...”
- “The largest failure domain is...”
- “The dangerous edge case is...”
- “The first evidence that would disprove this hypothesis is...”
- “The mitigation is reversible because...”
- “Recovery is proven by the original user-facing SLI...”
- “I would verify the current account and Region quota rather than guess.”
- “That service solves routing, but it does not solve data authority.”
- “This is at-least-once transport with exactly-once business effect at the storage boundary.”
- “I would not automate failover until source fencing and destination readiness are repeatedly proven.”

---

# Weak phrases to remove

- “AWS handles that.”
- “It scales automatically.”
- “Use three AZs and we are highly available.”
- “Just restart the pods.”
- “Run Terraform again.”
- “Use CloudWatch to find the issue.”
- “Exactly once.”
- “Zero downtime.”
- “The root cause was human error.”
- “Use all of these services.”
- “I do not remember the limit, but it is very high.”

Replace unsupported certainty with a measurement or verification plan.

---

# Five whiteboards to rehearse

## 1. EKS cell

```text
Route 53 / CloudFront / WAF
           |
       ALB/NLB
           |
    EKS cell across 3 AZs
     |       |       |
  system  on-demand  spot
   nodes   baseline  elastic
           |
 cache / DB / queue / stream
```

Call out:

- pod IPs;
- quotas;
- topology spread;
- N+1 capacity;
- retries/load shedding;
- full-path load test.

## 2. GitOps ownership

```text
Terraform -> AWS + EKS bootstrap
CI -> test, scan, sign, publish digest
Git -> desired state
Argo/Flux -> reconcile cluster
Rollout controller -> traffic and SLI gates
```

## 3. Incident request path

```text
client -> DNS -> edge/WAF -> LB -> VPC -> ingress/service -> pod -> dependency -> response
```

## 4. Regional failover

```text
impact confirmed
 -> destination ready
 -> old writer fenced
 -> data promoted
 -> canary traffic
 -> full traffic
 -> reconcile
 -> restore redundancy
```

## 5. Event platform

```text
producer -> Kinesis -> Lambda/EKS consumers -> SQS work isolation
                     -> S3 archive
                     -> derived EventBridge business events
```

---

# Adversarial one-line answers

**Why not one giant cluster?**

> It creates one controller, upgrade, policy, and operational blast radius; I choose cells from SLO, tenancy, and independent release needs.

**Why not 100% Spot?**

> Critical baseline capacity stays on On-Demand; Spot is diversified excess capacity for interruption-tolerant work.

**Why not Terraform and Argo on the same resource?**

> Two reconcilers make source of truth and rollback authority ambiguous.

**Why not `-lock=false`?**

> A blocked pipeline does not prove the original writer is dead; a second writer can silently corrupt state.

**Why can nodes be healthy while API latency doubles?**

> Node averages hide pod throttling, queueing, connection-pool waits, retries, DNS, and saturated dependencies.

**Why is one-AZ correlation not proof of AWS failure?**

> Version, node group, sidecar, or data path may be confounded with the AZ.

**Why not restart everything?**

> It destroys evidence and can amplify connection, cache, and retry storms.

**Why is MQTT publish not success?**

> It proves broker acceptance, not device execution; the device must return an authenticated result.

**Why is a signed update not automatically safe?**

> Signature proves authorized integrity, not hardware compatibility or functional correctness.

**Why not fail over from one alarm?**

> A false signal can turn a local incident into split brain or destination overload.

**CloudWatch or Prometheus?**

> CloudWatch owns AWS-native evidence; Prometheus owns Kubernetes/application metric semantics; one SLO has one pager owner.

**Exactly once?**

> I assume duplicate transport and enforce one business effect with stable IDs and conditional durable state.

---

# Five personal stories to have ready

1. Global platform and automation across approximately 2,500 systems and 11 data centers.
2. One exact Level 3/4 production incident with impact, evidence, mitigation, and permanent fix.
3. Monitoring/remediation and runbooks adopted by Level 1 NOC.
4. Approximately 45 TB MySQL migration with streaming transformation and restartability.
5. Leading a five-person SRE/DevOps team through a technical decision or operational change.

The missing metrics are documented in [`PERSONAL_STORY_BANK.md`](PERSONAL_STORY_BANK.md). Fill them before claiming Staff/Principal readiness.

---

# Final five-minute self-check

- Did I separate fact from assumption?
- Did I state the invariant?
- Did I name the source of truth and writer?
- Did I identify the largest blast radius?
- Did I explain overload and retry behavior?
- Did I include rollback and recovery?
- Did I state the evidence that proves the design?
- Did I answer the interviewer directly rather than recite?
- Did I use one truthful personal example?
- Did I avoid guessing a quota or metric?