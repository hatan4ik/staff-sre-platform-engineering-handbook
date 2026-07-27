# AWS DevOps / EKS Mock Interview Scorecard

A repeatable scoring system for Staff/Principal DevOps, SRE, Platform Engineering, and Cloud Architecture mock interviews.

> This scorecard evaluates engineering reasoning, not memorization of AWS product names or exact quota numbers.

## Interview format

### Full loop

| Round | Duration | Questions | Primary signal |
|---|---:|---:|---|
| Round 1 — Infrastructure and IaC | 60 minutes | 2 deep + 2 follow-ups | Architecture, AWS/EKS depth, security, delivery |
| Round 2 — Incident response | 60 minutes | 2 incidents + 1 postmortem | Triage, evidence, mitigation, recovery |
| Round 3 — System design | 60 minutes | 1 full design + adversarial changes | Scale, distributed systems, DR, leadership |
| Behavioral/leadership | 45 minutes | 3 production stories | Influence, judgment, ownership, outcomes |

### Focused practice session

```text
5 minutes  — prompt clarification and assumptions
10 minutes — architecture or incident response
10 minutes — adversarial follow-ups
5 minutes  — self-review and interviewer feedback
```

## Global scoring scale

| Score | Interpretation |
|---:|---|
| 1 | No useful answer; unsafe or fundamentally incorrect |
| 2 | Recognizes topic but cannot build or troubleshoot the system |
| 3 | Basic textbook answer; major production gaps |
| 4 | Competent mid-level implementation knowledge |
| 5 | Solid Senior engineer; handles common production cases |
| 6 | Strong Senior; some Staff-level reasoning |
| 7 | Meets Staff bar with manageable gaps |
| 8 | Strong Staff; reliable across ambiguity and failure |
| 9 | Principal-capable technical and organizational judgment |
| 10 | Exceptional cross-company platform or distributed-systems leadership |

A score of 10 should be rare. It requires both technical accuracy and durable organizational impact.

---

# Core evaluation dimensions

## 1. Requirement clarification — 10 points

| Points | Evidence |
|---:|---|
| 0–2 | Accepts ambiguous prompt literally; no scale, SLO, consistency, or recovery questions |
| 3–4 | Asks generic “how much traffic?” but does not use answer in design |
| 5–6 | States usable assumptions for scale, latency, availability, and geography |
| 7–8 | Clarifies business invariant, RTO/RPO, consistency, ordering, security, and cost |
| 9–10 | Reframes unsafe premise, identifies conflicting requirements, and prioritizes capabilities by business risk |

### Interviewer notes

```text
Did the candidate distinguish concurrency from throughput?
Did they ask what remote access controls?
Did they define RTO/RPO before multi-Region architecture?
Did they clarify whether “API latency” means application or Kubernetes API?
```

---

## 2. Architecture and service semantics — 15 points

| Points | Evidence |
|---:|---|
| 0–3 | Random AWS service list or incorrect semantics |
| 4–6 | Reasonable boxes but unclear request/data/control paths |
| 7–9 | Correct service roles, regional/AZ topology, state and dependencies |
| 10–12 | Alternatives, limits, ownership, cell boundaries, and evolution path |
| 13–15 | Minimal necessary design, explicit invariants, and enterprise operating model |

### Red flags

- EventBridge used as the default raw multi-million-event telemetry stream.
- Device Shadow used as the only short-lived command queue.
- CloudFormation, Terraform, and GitOps own the same resource.
- Route 53 presented as the complete DR architecture.
- EKS selected without explaining why Kubernetes is needed.

---

## 3. Distributed-systems reasoning — 15 points

| Points | Evidence |
|---:|---|
| 0–3 | Assumes no duplicates, no partitions, and instant consistency |
| 4–6 | Mentions eventual consistency but cannot explain consequences |
| 7–9 | Handles idempotency, retry, ordering, backpressure, and replay |
| 10–12 | Defines authority, fencing, conflict, state machine, and uncertain outcomes |
| 13–15 | Connects business invariants to partitioning and recovery across many services |

### Required concepts by scenario

```text
Terraform state     -> one writer, lineage, lock, reconciliation
Remote commands     -> expiry, idempotency, sequence/fencing, acknowledgement
OTA updates         -> immutable identity, staged state machine, local rollback
Multi-Region DR     -> source fencing, recovery point, conflict/reconciliation
Event processing    -> partition ordering, checkpoint after durable effect, replay
```

---

## 4. Reliability and failure containment — 15 points

| Points | Evidence |
|---:|---|
| 0–3 | “Deploy in three AZs” is the whole answer |
| 4–6 | Mentions retries, autoscaling, and backups without failure analysis |
| 7–9 | Defines overload, timeouts, rollback, capacity headroom, and recovery |
| 10–12 | Uses cells, progressive delivery, failure budgets, and tested DR |
| 13–15 | Designs organizational mechanisms that continuously verify resilience |

### Questions to score

- Can the remaining AZs absorb peak load?
- What happens if new nodes cannot obtain IPs?
- Does the rollback preserve schema compatibility?
- How is the old Region prevented from writing after promotion?
- What happens if the update breaks its own communications path?
- Can observability fail without removing the only incident signal?

---

## 5. Security and trust boundaries — 10 points

| Points | Evidence |
|---:|---|
| 0–2 | “Use IAM and encryption” |
| 3–4 | Basic least privilege and private networking |
| 5–6 | Human/workload identity, secret delivery, audit, and network isolation |
| 7–8 | Supply-chain, device identity, compromise, rotation, and break-glass |
| 9–10 | Enterprise guardrails, exceptions, recovery, and adversarial validation |

### Red flags

- static CI AWS keys;
- broad node role inherited by all pods;
- wildcard IRSA trust;
- shared device certificate;
- secret values in Git, image, logs, or Terraform outputs;
- signature treated as proof of functional safety;
- private API endpoint treated as full cluster security.

---

## 6. Operability and observability — 10 points

| Points | Evidence |
|---:|---|
| 0–2 | Generic dashboard and log answer |
| 3–4 | RED metrics and basic CloudWatch/Prometheus usage |
| 5–6 | SLOs, traces, structured logs, deployment/change correlation |
| 7–8 | Evidence hierarchy, cardinality/cost controls, alert routing and runbooks |
| 9–10 | Observability platform treated as a resilient product with quality governance |

### Strong signals

- p50/p95/p99, not average only;
- business transaction and cohort dimensions;
- trace-to-log correlation;
- deployment annotations;
- previous container logs preserved;
- alarms mapped to decisions;
- raw evidence path when dashboards fail;
- on-call quality metrics.

---

## 7. Incident response — 10 points

| Points | Evidence |
|---:|---|
| 0–2 | Restarts resources or makes broad changes immediately |
| 3–4 | Checks likely components but lacks incident structure |
| 5–6 | Measures impact, isolates request path, preserves logs, and mitigates |
| 7–8 | Uses cohort analysis, hypotheses, reversible changes, and recovery proof |
| 9–10 | Establishes incident command and creates cross-team recurrence prevention |

### Required sequence

```text
impact
 -> incident command
 -> freeze unrelated changes
 -> preserve evidence
 -> identify failure domain/cohort
 -> test hypotheses
 -> smallest reversible mitigation
 -> prove user recovery
 -> investigate and prevent recurrence
```

---

## 8. Communication and leadership — 10 points

| Points | Evidence |
|---:|---|
| 0–2 | Rambling, tool-focused, or defensive |
| 3–4 | Technically correct but hard to follow |
| 5–6 | Structured answer, clear trade-offs, responds to follow-ups |
| 7–8 | Aligns stakeholders, explains disagreement and business consequences |
| 9–10 | Creates durable standards, multiplies teams, and demonstrates measurable influence |

### Strong phrasing

```text
“The invariant I am protecting is...”
“The failure domain is...”
“The source of truth is...”
“The dangerous edge case is...”
“The evidence that proves recovery is...”
“The trade-off I accepted was...”
“The organizational mechanism I changed was...”
```

---

## 9. Validation and evidence — 5 points

| Points | Evidence |
|---:|---|
| 0 | No validation |
| 1 | Unit or smoke test only |
| 2 | Load or integration test |
| 3 | Failure and recovery test |
| 4 | Production-like game day with SLO/RTO/RPO evidence |
| 5 | Repeated automated verification and organizational ownership |

---

# Total result

```text
Requirement clarification        /10
Architecture/service semantics    /15
Distributed-systems reasoning     /15
Reliability/failure containment   /15
Security/trust boundaries         /10
Operability/observability         /10
Incident response                 /10
Communication/leadership          /10
Validation/evidence                /5
--------------------------------------
Total                            /100
```

## Hiring recommendation

| Total | Recommendation |
|---:|---|
| 90–100 | Strong Principal / exceptional Staff |
| 82–89 | Strong Staff hire; Principal possible with leadership evidence |
| 74–81 | Staff hire or strong Senior depending on consistency |
| 65–73 | Senior hire; Staff gaps |
| 50–64 | Mixed Senior signal; significant production gaps |
| Below 50 | No hire for senior infrastructure role |

### Override conditions

A high numeric score does not override:

- unsafe state or data handling;
- fabricated experience or numbers;
- inability to accept correction;
- severe security misconception;
- blaming individuals during incidents;
- claiming certainty without evidence.

---

# Round 1 mock interview cards

## Card 1A — EKS at hyperscale

### Prompt

Design a multi-AZ EKS platform for two million concurrent users with a p99 below 250 ms.

### Progressive follow-ups

1. Only 10% of users are active per second. Calculate a starting RPS assumption.
2. Traffic doubles in 90 seconds. Node launch takes two minutes.
3. One AZ fails at peak.
4. Surviving subnets have only 5,000 free pod IPs.
5. Aurora writer connections are already 80% consumed.
6. One global ingress controller becomes CPU-bound.
7. Explain why multiple clusters or cells may be required.

### Expected Staff signals

- Little's Law or equivalent concurrency/throughput reasoning;
- edge caching and request reduction;
- data-plane and dependency capacity;
- HPA plus node-supply timeline;
- warm capacity;
- subnet IP and quota planning;
- topology spread and PDB trade-offs;
- cell boundary and staged release;
- full-path load and AZ-loss test.

### Automatic failure

- “EKS supports millions because AWS manages the control plane.”

---

## Card 1B — GitOps ownership conflict

### Prompt

Terraform created EKS, several Helm releases, and applications. The platform team now wants Argo CD.

### Follow-ups

1. Who owns existing Helm releases during migration?
2. Argo self-heal reverts an emergency patch.
3. A CRD upgrade breaks all dependent resources.
4. The Git repository is unavailable.
5. The Argo ApplicationSet generates deletion across 30 clusters.

### Expected Staff signals

- explicit ownership transfer;
- no dual reconciler;
- break-glass and Git reconciliation;
- controller/CRD ordering;
- repository/controller recovery;
- fleet blast-radius controls.

---

## Card 1C — Terraform backend incident

### Prompt

Production Terraform state is locked in S3. The CI job says canceled, but a network change is urgent.

### Follow-ups

1. How do you prove the writer is dead?
2. The resource changed in AWS but not state.
3. State S3 replication contains an older object in another Region.
4. Another repository uses the same state key.
5. An engineer proposes `-lock=false`.

### Expected Staff signals

- freeze writers;
- capture lock and state versions;
- verify backend/account/identity;
- inspect provider-side operations;
- backup and refresh-only comparison;
- import/reconcile;
- never active-active state from S3 replication;
- prevent shared-key recurrence.

---

## Card 1D — EKS security compromise

### Prompt

A compromised pod obtained broad AWS permissions from the node role.

### Follow-ups

1. Immediate containment?
2. How do Pod Identity and IRSA change the design?
3. Can the pod still reach IMDS?
4. How do you prove no lateral movement?
5. How do you rotate affected secrets without outage?

### Expected Staff signals

- isolate workload/role and preserve evidence;
- node trust assessment and replacement;
- short-lived workload identity;
- IMDS controls verified from a pod;
- CloudTrail, runtime, network, secret access review;
- overlapping credential rotation;
- preventive admission and node-role minimization.

---

# Round 2 mock interview cards

## Card 2A — Partial outage after deployment

### Prompt

A deployment completed successfully, but 3% of users see 500 errors.

### Follow-ups

1. All failures are in `us-east-1c`.
2. All new-version pods also happen to be in `us-east-1c`.
3. Only IPv6 users fail.
4. Only tenants on shard 12 fail.
5. Aggregate success is still above the old 95% alert threshold.

### Expected Staff signals

- paired failing/healthy evidence;
- cohort matrix;
- confounding analysis;
- version/AZ/IPv6/shard isolation;
- targeted rollback or traffic removal;
- cohort-aware SLO.

---

## Card 2B — Latency doubles

### Prompt

API p99 doubles while EKS nodes remain Ready and average node CPU is 40%.

### Follow-ups

1. Clarify which API.
2. ALB TargetResponseTime also doubles.
3. X-Ray shows a slow Aurora span.
4. Database query execution is only 15 ms.
5. Application DB pool acquisition takes 600 ms.
6. HPA adds pods and makes the problem worse.

### Expected Staff signals

- percentile and cohort clarification;
- node average versus pod throttling/saturation;
- trace allocation;
- connection-pool metric;
- frontend scale amplifies database connections;
- concurrency limit, pool correction, and dependency protection.

---

## Card 2C — Restart loop with healthy probes

### Prompt

Pods restart every four minutes, but readiness and liveness never show failure.

### Follow-ups

1. Restart count increases under same pod UID.
2. Last exit code is 0.
3. Entrypoint starts the application in the background.
4. Another version shows exit 137.
5. Karpenter is also consolidating nodes.

### Expected Staff signals

- process versus pod replacement distinction;
- `lastState` and previous logs;
- PID 1 and `exec`;
- OOM versus forced SIGKILL evidence;
- Karpenter disruption correlation;
- recovery observed beyond historical interval.

---

## Card 2D — Postmortem leadership

### Prompt

A global rollout caused a 50-minute outage. The initiating code change came from a junior engineer.

### Follow-ups

1. What is the root cause?
2. Who owns the postmortem?
3. Leadership wants the engineer named.
4. There are 35 action items.
5. How do you know the problem is fixed?

### Expected Staff signals

- trigger versus system/safeguard causes;
- neutral facilitator and service ownership;
- blameless, not ownerless;
- prioritize P0/P1 with tests and due dates;
- verify through canary, dependency failure, and rollout game day.

---

# Round 3 mock interview cards

## Card 3A — Mobile remote command

### Prompt

Design a mobile backend that lets users remotely unlock a connected device.

### Follow-ups

1. The device is offline.
2. MQTT delivers the command twice.
3. The user presses unlock repeatedly.
4. The cloud receives an acknowledgement but the physical action fails.
5. The primary Region returns after failover.
6. A mobile session was stolen.

### Expected Staff signals

- command state machine;
- short expiry;
- idempotency key;
- device execution journal;
- authenticated result, not publish success;
- step-up authentication;
- writer fencing during Region failover;
- device-local safety authority.

---

## Card 3B — Secure fleet update

### Prompt

Deliver a 2 GB software image to five million intermittently connected devices.

### Follow-ups

1. One hardware revision has half the storage.
2. Power fails during installation.
3. The signing key may be compromised.
4. The new image breaks network connectivity.
5. Devices stop reporting after the canary.
6. A critical vulnerability requires rapid rollout.

### Expected Staff signals

- signed compatibility manifest;
- resumable immutable delivery;
- representative cohorts;
- A/B or transactional install;
- device-local rollback and independent update agent;
- key revocation/rotation plan;
- missing heartbeat as failure signal;
- urgency with canary and abort, not global blind rollout.

---

## Card 3C — Multi-Region failover

### Prompt

The primary Region is unreachable. RTO is five minutes; RPO is under ten seconds.

### Follow-ups

1. Route 53 health check failed once.
2. Aurora replication lag is six seconds.
3. The old Region may still accept writes internally.
4. Secondary EKS has 25% capacity.
5. The primary returns after 20 minutes.
6. Failback requested immediately.

### Expected Staff signals

- multi-signal declaration;
- destination capacity realization;
- source fencing;
- recovery-point acknowledgement;
- data promotion and uncertain transaction handling;
- staged traffic shift;
- failback as planned migration.

---

## Card 3D — Observability alert fatigue

### Prompt

The on-call receives 200 pages a week from EKS and AWS services.

### Follow-ups

1. Most pod alerts auto-recover.
2. Teams want every anomaly paged.
3. Prometheus cardinality doubles monthly.
4. Traces cost too much.
5. Grafana is unavailable during an incident.
6. CloudWatch and Prometheus page the same SLO.

### Expected Staff signals

- page/ticket/dashboard taxonomy;
- SLO burn alerts;
- grouping, inhibition, deduplication;
- cardinality budgets;
- targeted trace sampling;
- fallback evidence path;
- one authoritative rule owner;
- alert-quality metrics and deletion.

---

## Card 3E — Event platform overload

### Prompt

A platform ingests five million 1 KB events per second.

### Follow-ups

1. One customer sends 40% of events.
2. Per-customer ordering is required.
3. A consumer is six hours behind.
4. One event permanently crashes processing.
5. Lambda overwhelms DynamoDB.
6. A Region fails during replay.

### Expected Staff signals

- 5 GB/s payload math plus overhead;
- partition-key serial ceiling;
- tenant quota and redesign of ordering invariant;
- retention and safe catch-up rate;
- poison-event isolation with ordering awareness;
- downstream concurrency limit;
- stable event ID and regional replay/idempotency.

---

# Leadership and behavioral scorecard

## Story 1 — Reliability transformation

Prompt:

> Tell me about a production platform whose reliability you materially improved.

Score:

- baseline SLO or incident pain;
- technical and organizational causes;
- alternative solutions;
- cross-team influence;
- rollout and verification;
- measured outcome;
- lasting mechanism.

## Story 2 — Disagreement

Prompt:

> Tell me about a major architecture decision where senior engineers disagreed.

Strong evidence:

- represents opposing position fairly;
- uses data, prototype, or game day;
- identifies reversible versus irreversible choice;
- creates decision record;
- adapts when evidence changes;
- preserves working relationship.

## Story 3 — Incident leadership

Prompt:

> Tell me about the most severe incident you led.

Strong evidence:

- user/business impact;
- incident command roles;
- evidence and hypotheses;
- safe mitigation;
- communication;
- recovery proof;
- postmortem and prevention;
- personal mistake or changed belief.

## Story 4 — Platform adoption

Prompt:

> Tell me about a platform or standard you created that other teams adopted.

Strong evidence:

- internal customer discovery;
- paved road and escape hatch;
- adoption friction;
- product metrics;
- support/ownership model;
- measurable developer or operational outcome.

---

# Interviewer feedback template

```markdown
## Overall recommendation
Strong hire / Hire / Mixed / No hire
Level: Senior / Staff / Principal
Confidence: High / Medium / Low

## Strongest evidence
- 
- 
- 

## Highest-risk gaps
- 
- 
- 

## Technical scores
Requirement clarification:      /10
Architecture/service semantics: /15
Distributed systems:            /15
Reliability:                     /15
Security:                        /10
Operability/observability:       /10
Incident response:               /10
Communication/leadership:        /10
Validation/evidence:              /5
Total:                           /100

## Follow-up evidence needed
- 

## Level rationale
- 

## Direct quotes or behaviors
- 
```

---

# Candidate self-review after every mock

Answer without defending yourself:

1. Did I clarify scale and the invariant before naming services?
2. Did I state the source of truth and write authority?
3. Did I identify the largest blast radius?
4. Did I explain overload and retry behavior?
5. Did I define rollback and recovery proof?
6. Did I claim an AWS guarantee that I have not verified?
7. Did I answer the follow-up directly or return to a memorized speech?
8. Did I connect the design to a real production decision?
9. Did I quantify outcome honestly?
10. What should I remove from the answer to make the judgment clearer?

## Readiness rule

Do not mark a question ready because you can recite the chapter.

Mark it ready when you can:

- answer it in 90 seconds;
- draw it in five minutes;
- survive five adversarial follow-ups;
- identify one unsafe alternative;
- connect it to one truthful production story;
- state how you would validate the design.