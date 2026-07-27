# Nathanel — Interview Evidence Completion Worksheet

This worksheet closes the five evidence gaps that still separate a strong technical curriculum from a defensible Staff/Principal interview package.

## Rules

1. Use records, repositories, tickets, reports, emails, calendars, monitoring exports, or direct personal recollection.
2. Mark uncertain values as ranges and record how the range was estimated.
3. Do not convert an assignment, lab, or hypothetical architecture into a production claim.
4. Do not claim that one change caused an outcome when multiple changes occurred unless the evidence supports attribution.
5. Use customer or business outcomes before internal activity counts.
6. Preserve confidential names and data by describing the system generically where required.

## Evidence labels

- **Verified:** supported by a source that can be identified.
- **Personally confirmed:** Nathanel directly remembers the fact but does not currently have an artifact.
- **Estimated range:** approximation with an explicit method.
- **Unknown:** do not use as an interview fact.

---

# Evidence Set 1 — Platform adoption and operational scale

Use this to complete the global SES/O3b platform story.

## Stable facts already available

- AWS, Azure, private cloud, and 11 data centers.
- Approximately 2,500 managed systems.
- Monitoring across more than 1,000 devices/platforms.
- Terraform, Ansible, Puppet, Helm, CI/CD, observability, remediation, and runbooks.
- Operational tools and procedures adopted by Level 1 NOC.

## Fill the evidence

```text
Platform/tool/process name:
Business capability supported:
Time period:
My role and decision authority:
Engineering teams involved:
Operations/NOC teams involved:
Approximate users or operators:
Systems/services covered:
Regions/data centers/accounts covered:
```

## Before state

```text
Deployment or change process before:
Typical lead time before:
Manual steps before:
Common failure or escalation pattern:
Who had to be involved:
How often senior engineering was interrupted:
Evidence source:
Confidence label:
```

## Decision and alternatives

```text
Invariant protected:
Option A:
Option B:
Chosen approach:
Why the rejected option was reasonable:
Why it was rejected:
Was the decision reversible?
Who disagreed and what evidence resolved the disagreement?
```

## After state

```text
Deployment/change lead time after:
Manual steps removed:
Teams adopting the mechanism:
Systems/services onboarded:
Escalations reduced:
Incidents prevented or shortened:
Operator satisfaction/adoption evidence:
Evidence source:
Confidence label:
```

## Defensible interview metric

Use only one primary metric initially.

```text
Metric:
Before:
After:
Measurement window:
Measurement method:
Known confounding changes:
Safe wording for interview:
```

Example safe wording when exact values are unavailable:

> Across an estate of roughly 2,500 managed systems, we moved a recurring operational workflow from senior-engineer execution to a standardized NOC-owned process. I do not have the exact percentage in front of me, but the measurable indicator was the reduction in Level 3/4 escalations over the following review period.

---

# Evidence Set 2 — One exact severe production incident

Use this for outage troubleshooting, latency, cohort failure, evidence, postmortem, and leadership questions.

## Incident identity

```text
Generic incident name:
Date or approximate period:
Service/business capability:
Production environment:
My on-call/incident role:
Other teams involved:
```

## Customer impact

```text
What users could not do:
Affected geography/cohort/customer group:
Start time UTC:
Detection time UTC:
Mitigation time UTC:
Full recovery time UTC:
Failed transactions or requests:
Latency/SLO/error-budget impact:
Data loss, duplication, or uncertainty:
Contractual/revenue/operational impact:
Evidence source:
Confidence label:
```

## Timeline

```text
T+00 — first known symptom:
T+__ — incident command established:
T+__ — first hypothesis:
T+__ — first misleading signal:
T+__ — decisive evidence:
T+__ — mitigation selected:
T+__ — customer SLI recovered:
T+__ — full cleanup/reconciliation completed:
```

## Technical path

```text
Client/request/event path:
First failing boundary:
Component that appeared healthy but was not sufficient evidence:
Decisive log/trace/metric/network/runtime evidence:
Hypothesis disproved:
Root technical mechanism:
```

## Mitigation

```text
Immediate mitigation:
Why it was the smallest reversible action:
Rollback or abort condition:
How recovery was verified externally:
Residual risk after mitigation:
```

## Causal analysis

```text
Trigger:
Contributing technical condition:
Blast-radius or containment failure:
Detection gap:
Diagnosis gap:
Recovery gap:
Organizational/process condition:
```

## Permanent actions

For each important action:

```text
Action:
Owner:
Due date:
Risk reduced:
Acceptance test:
Status:
```

## Personal learning

```text
What I initially believed:
What evidence changed my mind:
What I would do earlier next time:
What platform/organizational mechanism changed afterward:
```

---

# Evidence Set 3 — Observability and NOC capability transfer

Use this for actionable observability, toil reduction, platform adoption, and leadership.

## Scope

```text
Monitoring/tooling name:
Time period:
More than 1,000 devices/platforms — exact defensible wording:
Primary users:
Alert/event volume before:
Top recurring failure classes:
```

## Problem

```text
What evidence was missing:
What senior engineers had to do manually:
Why existing dashboards or alerts were insufficient:
Escalation quality before:
Customer or operational consequence:
```

## Product decision

```text
Signals standardized:
Alert taxonomy: page / ticket / context:
Runbooks created:
Remediations automated:
Actions deliberately not automated:
Reason automation was unsafe:
Ownership and escalation model:
Training/knowledge-transfer approach:
```

## Outcome

```text
Alerts handled by Level 1 after adoption:
Level 3/4 escalations before:
Level 3/4 escalations after:
MTTA before/after:
MTTR before/after:
After-hours pages before/after:
Repeat incidents before/after:
Runbook or automation adoption:
Evidence source:
Confidence label:
```

## Strong story sentence

Complete only after the metric is supported:

> I treated observability as an operational decision product rather than a dashboard project. After standardizing evidence, runbooks, and bounded remediation for more than ______ monitored devices/platforms, Level 1 NOC handled ______, reducing ______ from ______ to ______ over ______.

---

# Evidence Set 4 — Approximately 45 TB MySQL migration

Use this for large migrations, state recovery, backpressure, restartability, database performance, and DR thinking.

## Stable facts already available

- Approximately 45 TB uncompressed and approximately 6 TB compressed.
- MySQL 5.7.
- Ubuntu, XFS, LVM, and two approximately 31 TB volumes.
- MyISAM-to-InnoDB conversion.
- Removal of `DATA DIRECTORY` and `INDEX DIRECTORY` clauses.
- Streaming transformations to avoid memory exhaustion.
- Per-database restartability.

## Business context

```text
Why the migration was required:
Source environment:
Target environment:
Deadline or outage constraint:
Applications/teams depending on completion:
My responsibility:
```

## Scale

```text
Final source volume:
Final imported volume:
Number of databases:
Number of tables:
Largest database/table:
Compressed/uncompressed ratio:
Evidence source:
Confidence label:
```

## Capacity and performance

```text
CPU/RAM:
Storage layout:
Measured read throughput:
Measured write throughput:
Observed IOPS/latency:
Sustained import throughput:
Peak import throughput:
Primary bottleneck:
Secondary bottleneck:
```

## Recovery architecture

```text
Unit of restartability:
Checkpoint/progress record:
Maximum work lost after failure:
How partially completed databases were detected:
How duplicate/replayed work was made safe:
How concurrent writers were prevented:
```

## Failures encountered

```text
No database selected — cause and correction:
Memory exhaustion — cause and streaming correction:
Unsupported variable/configuration — cause and correction:
InnoDB configuration issue — cause and correction:
Storage bottleneck — evidence and correction:
Other significant failure:
```

## Validation

```text
Schema validation:
Row-count validation:
Checksum or sampling validation:
Application query validation:
Performance validation:
Data-loss/duplication result:
Who accepted completion:
```

## Outcome

```text
Total elapsed time:
Hands-on engineering time:
Longest interruption:
Recovery time after representative failure:
Business result:
Evidence source:
Confidence label:
```

## Safe 90-second result sentence

> I designed the roughly 45 TB migration as a streaming, per-database, resumable workflow. The final sustained rate was ______, the maximum recovery loss was ______, and validation used ______. The key result was ______.

Do not use the sentence until every blank has a defensible value.

---

# Evidence Set 5 — Leadership of a five-person SRE/DevOps team

Use this for Principal-level influence, conflict, delegation, mentoring, and platform operating-model questions.

## Team context

```text
Time period:
Team size:
Roles/seniority mix:
Team mission:
Systems/business capabilities owned:
My formal authority:
My technical authority outside the team:
Partner teams:
```

## Initial problem

```text
Delivery/reliability/ownership problem:
How it affected customers or engineering teams:
Why individual heroics were not sufficient:
Metric or evidence showing the problem:
```

## Leadership decision

```text
Standard or platform mechanism introduced:
What I personally owned:
What I delegated:
Decision rights given to engineers:
Guardrails and review model:
Escape hatch:
```

## Conflict example

```text
Decision under disagreement:
My initial position:
Opposing position:
Why the opposing position was reasonable:
Evidence/prototype/game day used:
Final decision:
How the relationship was preserved:
What I changed in my own view:
```

## Developing others

```text
Engineer or role developed:
Starting gap:
Coaching/delegation approach:
New responsibility they assumed:
Evidence they succeeded independently:
How this reduced dependency on me:
```

## Outcome

```text
Team delivery metric before/after:
Reliability or incident metric before/after:
Adoption or customer outcome:
Toil/escalation reduction:
Mechanism that continued without my direct involvement:
Evidence source:
Confidence label:
```

## Principal-level closing sentence

> The result was not only that my team delivered ______. We created ______, which allowed ______ teams/operators to act independently while preserving ______. The mechanism continued through ______ rather than depending on me as the escalation point.

---

# Final five-story readiness table

| Story | Primary metric verified? | Decision/trade-off clear? | Failure/uncertainty included? | Organizational influence shown? | Ready? |
|---|---|---|---|---|---|
| Global platform transformation | | | | | |
| Severe production incident | | | | | |
| Observability/NOC transfer | | | | | |
| 45 TB MySQL migration | | | | | |
| Five-person team leadership | | | | | |

A story is ready only when every column can be answered without inventing a fact.

## Minimum completion target

Before the first full external mock interview, complete:

- one exact severe incident;
- the 45 TB migration result and validation;
- one adoption or NOC metric;
- one leadership disagreement;
- one mechanism that continued without Nathanel's direct involvement.
