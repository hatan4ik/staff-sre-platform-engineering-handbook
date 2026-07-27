# 30-Day AWS Staff/Principal Interview Execution Plan

This plan converts the completed curriculum into interview performance.

## Outcome at day 30

Nathanel can:

- answer every one of the 18 AWS questions in 60–90 seconds;
- whiteboard the six highest-value architectures in five minutes;
- survive adversarial follow-ups without returning to a memorized speech;
- run and explain the three hands-on labs;
- deliver five truthful production stories with defensible scale and outcomes;
- score at least 82/100 in two consecutive mock interview loops;
- identify uncertainty and verification steps instead of guessing.

## Daily time budget

```text
60 minutes minimum
90 minutes preferred
120 minutes on mock-interview days
```

Daily structure:

```text
15 min — spoken-answer repetition
20 min — deep technical correction
15 min — adversarial follow-ups
20 min — story or lab evidence
10 min — score and written correction
```

---

# Week 1 — Round 1 and factual story foundation

## Day 1 — Baseline assessment

- Record answers to Q1, Q3, Q7, Q13, Q16, and Q18 without reading.
- Score each with `MOCK_INTERVIEW_SCORECARD.md`.
- Do not correct during the recording.
- Write the three weakest dimensions.
- Read `INTERVIEW_DAY_CHEATSHEET.md` once.

Deliverable:

```text
baseline-score.md
six audio/video recordings
three priority gaps
```

## Day 2 — EKS scale and capacity

- Read Q1 and Q6.
- Deliver both spoken answers.
- Whiteboard the demand-to-serving timeline.
- Answer:
  - one AZ fails at peak;
  - pod IPs are exhausted;
  - Karpenter cannot get permitted capacity;
  - database connections are at 80%;
  - why not one giant cluster?
- Map to Story 1 and label what is real versus hypothetical.

Exit criterion:

> Can explain why node launch is not user recovery.

## Day 3 — GitOps and source-of-truth ownership

- Read Q2 and Q5.
- Draw Terraform/CI/Git/Argo ownership.
- Explain bootstrap ownership transfer.
- Explain emergency break-glass reconciliation.
- Use Story 6 for repository source-of-truth migration.
- Add the missing repository count and CI scope if records are available.

Exit criterion:

> Can identify and stop a dual-reconciler design in under 30 seconds.

## Day 4 — Terraform state and recovery

- Read Q3 and Q11.
- Run Lab 01 from a clean checkout.
- Capture evidence before recovery.
- Explain why old state, `-lock=false`, and blind reapply are unsafe.
- Deliver a 90-second partial-apply answer without notes.

Exit criterion:

> Can state the exact difference between import, `state rm`, refresh-only, and normal apply.

## Day 5 — EKS security

- Read Q4.
- Draw human identity, cluster authorization, workload identity, node role, secret, network, and artifact layers.
- Explain Pod Identity versus IRSA without declaring one universally superior.
- Translate the AKS assignment identity issue into the AWS model.
- Answer one compromised-pod scenario.

Exit criterion:

> Can explain why a private endpoint does not make a cluster secure.

## Day 6 — Personal story extraction session 1

Complete Story 1 and Story 3 in `PERSONAL_STORY_BANK.md`.

Find defensible evidence for:

- platform adoption;
- deployment or operational improvement;
- NOC escalation reduction;
- before/after MTTR if available;
- one disagreement;
- one action deliberately not automated.

Use ranges when exact figures are unavailable and record the measurement source.

## Day 7 — Round 1 mock

Run a 60-minute mock:

- one EKS scale question;
- one GitOps/Terraform question;
- one security follow-up;
- one production story.

Target score:

```text
74/100 or higher
no automatic-failure statement
```

Write the corrections the same day.

---

# Week 2 — Incident response and evidence discipline

## Day 8 — Request-path outage

- Read Q7.
- Draw the outside-in path in 60 seconds.
- Practice one failing transaction with DNS, TLS, LB, VPC, Kubernetes, application, dependency, and response evidence.
- Select the exact production incident for Story 2.

Exit criterion:

> Can name what `ACCEPT`, healthy target, and successful DNS response do not prove.

## Day 9 — Latency

- Read Q8A and Q8B.
- Practice clarifying control-plane versus application API.
- Use the phrase: metrics locate, traces allocate, runtime evidence explains.
- Explain CPU throttling at low node average.
- Explain connection-pool wait versus database execution.
- Map the MySQL story to dependency saturation and evidence.

## Day 10 — Partial-user failures

- Read Q9.
- Build a cohort matrix from a hypothetical deployment.
- Separate AZ/version confounding.
- Add IPv6, tenant shard, feature flag, and session age.
- Identify a real incident that had a partial or asymmetric cohort, if one exists.
- Do not invent one when none is documented.

Exit criterion:

> Can verify recovery for the original 2–3% cohort rather than aggregate health.

## Day 11 — Evidence beyond dashboards

- Read Q10.
- Create one UTC incident timeline template.
- Practice alarm validation, Logs Insights dimensions, traces, CloudTrail, Config, AWS Health, LB/WAF/Flow Logs, and runtime evidence.
- Use Story 3 to explain why evidence must enable an operational decision.

Exit criterion:

> Can write a hypothesis with supporting, disproving, and safe-test columns.

## Day 12 — Kubernetes restart forensics

- Read Q12.
- Run Lab 02.
- Diagnose exit 0, OOMKilled, PID 1, and sidecar restart.
- Inject a Deployment rollout and distinguish pod replacement from container restart.
- Record the evidence order from memory.

Exit criterion:

> First commands include `lastState` and `kubectl logs --previous`.

## Day 13 — Postmortem and incident leadership

- Read Q13.
- Complete Story 2 with one exact incident.
- Separate trigger, contributing conditions, safeguard failure, and organizational condition.
- Reduce proposed actions to three P0/P1 actions with acceptance tests.
- Prepare the answer to: “The junior engineer caused it—why not name them?”

## Day 14 — Round 2 mock

Run a 60-minute mock:

- one latency or partial-user incident;
- one Terraform or restart incident;
- one postmortem leadership discussion.

Target score:

```text
78/100 or higher
incident response >= 7/10
no broad restart as first mitigation
```

---

# Week 3 — Global system design and distributed systems

## Day 15 — Mobile backend and remote commands

- Read Q14.
- Draw identity, API, preference, notification, command, and device paths separately.
- Practice offline device, duplicate MQTT delivery, stolen mobile session, and failover.
- State clearly that this is an architecture answer unless a direct production example is documented.

Exit criterion:

> Can describe accepted, delivered, acknowledged, executed, failed, and expired states.

## Day 16 — Secure software update

- Read Q15.
- Draw release control plane and artifact data plane.
- Explain signed manifest, immutable artifact, cohorts, abort threshold, A/B install, anti-rollback, and disappeared-device evidence.
- Practice the signing-key-compromise question.

Exit criterion:

> Can explain why valid signature does not prove safety.

## Day 17 — Multi-Region DR

- Read Q16.
- Define RTO/RPO for authentication, writes, reads, events, and analytics separately.
- Draw source fencing before promotion.
- Practice ARC routing controls versus readiness checks.
- Explain SQS/stream recovery without claiming transparent replication.
- Add one real backup, restore, failover, or recovery story to Story 9 or Story 4.

Exit criterion:

> Can describe failback as a planned authority migration.

## Day 18 — Observability platform

- Read Q17.
- Draw OTel agent/gateway pipelines, CloudWatch, X-Ray, AMP, Grafana, alarms, and incident routing.
- Practice page/ticket/dashboard classification.
- Use Story 3 and Story 1 as evidence.
- Add one alert that should be deleted and one that should page.

Exit criterion:

> Can explain the observability platform's own failure mode.

## Day 19 — Event processing

- Read Q18.
- Run Lab 03 baseline, hot-key, duplicate, transient, poison, and stress scenarios.
- Explain Kinesis, SQS, SNS, EventBridge, Lambda, EKS, and S3 roles without decorative chaining.
- Calculate 5 million × 1 KB = approximately 5 GB/s raw payload before overhead.

Exit criterion:

> Can explain why more workers do not solve one strictly ordered hot key.

## Day 20 — Large migration story

Complete Story 4.

Find:

- final data volume;
- elapsed time;
- sustained throughput;
- database/table count;
- validation method;
- failure recovery point;
- business result.

Create a 90-second answer and a five-minute deep version.

## Day 21 — Round 3 mock

Run a 75-minute mock:

- one full system design;
- five changing requirements;
- one personal migration or platform story;
- one disagreement/leadership question.

Target score:

```text
82/100 or higher
requirement clarification >= 7/10
distributed systems >= 10/15
```

---

# Week 4 — Principal calibration and repeated performance

## Day 22 — Leadership story: team of five

Complete Story 10.

Prepare:

- team mission;
- one conflict;
- one delegation decision;
- one person developed or mentored;
- one measurable team outcome;
- one mechanism that reduced dependency on Nathanel.

Avoid turning the story into a list of technologies.

## Day 23 — Cost and business trade-offs

Complete Story 7.

- Reconstruct the approximately $100K annual reduction.
- Identify what was changed.
- Identify one rejected unsafe cost reduction.
- State how capacity and recovery were protected.
- Practice explaining cost versus reliability to an executive.

## Day 24 — Hybrid architecture story

Complete Story 9 with one specific topology.

Prepare:

- AWS/Azure/private/data-center boundaries;
- routing and DNS ownership;
- identity and certificate flow;
- failure encountered;
- mitigation and permanent change;
- measured result.

## Day 25 — Principal disagreement drill

For three questions, state:

1. the opposing design;
2. why it was reasonable;
3. the invariant;
4. what evidence would choose between the options;
5. whether the choice is reversible;
6. the final decision record.

Use:

- one cluster versus multiple cells;
- active-active versus hot standby;
- Lambda versus EKS stream processing.

## Day 26 — Executive communication drill

Answer each in two minutes without architecture jargon overload:

- Why are we paying for idle DR capacity?
- Why not deploy the security update to everyone immediately?
- Why are we slowing releases after error-budget burn?
- Why not standardize on one IaC tool?
- Why spend on tracing when dashboards exist?

Each answer includes business risk, option, trade-off, evidence, and decision.

## Day 27 — Full mock loop 1

Run:

- 45 minutes infrastructure/IaC;
- 45 minutes incident response;
- 60 minutes system design;
- 30 minutes leadership.

Target:

```text
82/100 overall
no section below Staff threshold
at least three defensible personal metrics
```

## Day 28 — Correction day

Do not reread the whole curriculum.

For every lost point:

- identify the exact behavior;
- rewrite one sentence or diagram;
- run one lab or evidence query when practical;
- repeat the failed follow-up twice.

Remove unnecessary detail from strong areas.

## Day 29 — Full mock loop 2

Use different scenarios and interruptions.

Target:

```text
85/100 overall
no unsupported certainty
no answer longer than 120 seconds before interviewer engagement
```

## Day 30 — Interview-ready package

Finalize:

- `PERSONAL_STORY_BANK.md` missing fields;
- five 90-second personal stories;
- one-page resume alignment notes;
- interview-day cheatsheet;
- six whiteboards;
- lab evidence screenshots or logs;
- top 20 adversarial questions;
- current AWS facts that must be verified before a real interview.

Final self-verdict:

```text
Ready for Staff
Ready for Principal
Not ready because: <specific evidence gap>
```

Do not mark Principal-ready based only on technical score. Principal readiness requires organizational influence and measurable outcomes.

---

# Score tracking table

| Date | Mock | Requirements /10 | Architecture /15 | Distributed /15 | Reliability /15 | Security /10 | Observability /10 | Incident /10 | Leadership /10 | Evidence /5 | Total |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| | Baseline | | | | | | | | | | |
| | Round 1 | | | | | | | | | | |
| | Round 2 | | | | | | | | | | |
| | Round 3 | | | | | | | | | | |
| | Full loop 1 | | | | | | | | | | |
| | Full loop 2 | | | | | | | | | | |

---

# Non-negotiable truth rules

- Production fact and hypothetical architecture remain visibly separate.
- Assignment/lab experience is labeled assignment/lab.
- No invented availability, traffic, cost, or incident metric.
- No guessed current AWS quota.
- No “zero downtime,” “zero data loss,” “infinite scale,” or transport-level “exactly once” without a precise proof boundary.
- A strong uncertainty statement is better than a false precise number.