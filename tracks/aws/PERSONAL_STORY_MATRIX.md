# Personal Story Matrix — AWS Staff/Principal Interview Track

Technical chapters demonstrate what a strong answer should contain. Hiring decisions also require evidence that the candidate has exercised similar judgment in real systems.

This workbook turns production experience into reusable, truthful interview stories without exposing confidential company information.

## The rule

> Never invent scale, impact, ownership, or outcomes. Sanitize names and sensitive architecture, but preserve the actual decision, failure mode, trade-off, and measurable result.

A story should make clear:

- what you personally owned;
- what other teams owned;
- what was uncertain at the start;
- which invariant or business objective mattered;
- what evidence changed the decision;
- what trade-off you accepted;
- what measurable outcome followed;
- what durable mechanism remained after you moved on.

## Story structure: `SCALE`

Use `SCALE` for a two-minute behavioral answer.

1. **S — Situation and stakes**
   - What system, customer journey, or organizational problem was involved?
   - What was the scale and business risk?

2. **C — Constraints and conflict**
   - Time, cost, compliance, legacy, ownership, availability, skill, or political constraints.
   - What reasonable people disagreed about.

3. **A — Actions and architecture**
   - Your investigation, design, decision, implementation, and communication.
   - Separate your work from the team's work.

4. **L — Leadership leverage**
   - How you aligned teams, created standards, delegated, taught, or changed the operating model.

5. **E — Evidence and evolution**
   - Metrics, SLO, incident duration, deployment frequency, cost, toil, recovery time, risk reduction, adoption, or audit result.
   - What you learned and what you would change now.

## Evidence hierarchy

Prefer evidence in this order:

1. user or business outcome;
2. reliability, security, or delivery metric;
3. operational toil or recovery improvement;
4. adoption across teams;
5. technical completion.

Weak:

> I migrated the cluster to Terraform.

Stronger:

> I led the migration of the shared platform to reviewed Terraform modules and short-lived deployment roles. We reduced manual environment drift, cut recovery from undocumented rebuilds to a tested pipeline, and moved six teams onto the same release and rollback contract.

Only use numbers that are true and defensible.

---

# Minimum story bank

Prepare at least ten stories. One story can support several questions, but the emphasis must change.

| ID | Story archetype | Primary signal |
|---|---|---|
| S1 | Severe production incident | incident command, diagnosis, mitigation, recovery |
| S2 | Platform or cloud architecture build | system design, trade-offs, operability |
| S3 | Infrastructure-as-Code failure or recovery | state, ownership, reconciliation, safety |
| S4 | Security or identity hardening | trust boundaries, compromise assumptions, governance |
| S5 | Large migration or modernization | sequencing, compatibility, stakeholder alignment |
| S6 | Capacity or performance breakthrough | measurement, bottlenecks, cost/performance trade-offs |
| S7 | Observability transformation | SLOs, telemetry quality, on-call outcomes |
| S8 | Disaster recovery or continuity program | RTO/RPO, restore proof, organizational readiness |
| S9 | Difficult technical disagreement | influence, decision quality, conflict resolution |
| S10 | Failure, mistake, or changed mind | accountability, learning, system improvement |

Optional Principal-level additions:

| ID | Story archetype | Primary signal |
|---|---|---|
| S11 | Multi-team standard or paved road | organizational leverage and adoption |
| S12 | Cost or vendor strategy | business judgment and lifecycle ownership |
| S13 | Talent development or delegation | multiplier effect |
| S14 | Risk accepted deliberately | executive communication and trade-off ownership |

---

# Map stories to the 18 AWS questions

Use this table to ensure every technical answer can be connected to real evidence.

| # | AWS scenario | Best story slots | Evidence to emphasize |
|---:|---|---|---|
| 1 | Multi-AZ EKS for millions | S2, S6, S11 | scale math, capacity limit, failure domain, adoption |
| 2 | Terraform plus GitOps | S2, S5, S11 | ownership boundaries, promotion, rollback, team enablement |
| 3 | Terraform state across accounts and Regions | S3, S8 | one writer, state recovery, access control, restore test |
| 4 | Securing EKS | S4, S11 | identity, least privilege, runtime isolation, governance |
| 5 | Terraform versus CloudFormation/native | S2, S9, S12 | operating model, tool boundary, disagreement, lifecycle cost |
| 6 | Capacity and autoscaling | S6, S1 | bottleneck evidence, headroom, overload, cost |
| 7 | Route 53-to-application outage | S1, S7 | request-path isolation, evidence, reversible mitigation |
| 8 | API latency while nodes are healthy | S1, S6, S7 | latency allocation, traces, saturation, false hypotheses |
| 9 | Subset of users fail | S1, S7 | cohort analysis, matched requests, rollout containment |
| 10 | Dashboards do not reveal cause | S7, S1 | raw evidence, telemetry gaps, observability redesign |
| 11 | Terraform partial apply | S3, S10 | safe reconciliation, ownership, mistake prevention |
| 12 | Pods restart while probes pass | S1, S7 | previous state, resource evidence, container versus Pod |
| 13 | Large outage postmortem | S1, S10, S11 | causal analysis, accountability, verified corrective actions |
| 14 | Highly available mobile backend | S2, S4 | separate state machines, identity, availability semantics |
| 15 | Global secure software updates | S4, S5, S8 | signing, staged rollout, rollback, device authority |
| 16 | Multi-Region DR | S8, S2 | RTO/RPO, fencing, failover and failback proof |
| 17 | Actionable observability | S7, S11 | SLOs, paging quality, cost/cardinality, platform adoption |
| 18 | Millions of events per second | S2, S6 | partitioning, backpressure, replay, cost and capacity |

The mapping is not a script. It is a coverage check.

---

# Story worksheet

Copy this section once for each story.

## Story ID and title

```text
ID:
Title:
Primary competency:
Secondary competencies:
Questions supported:
```

## Situation and stakes

```text
System or program:
Customer/business impact:
Scale:
Availability or delivery objective:
What made the problem ambiguous:
```

## Constraints and disagreement

```text
Time constraint:
Cost constraint:
Technical constraint:
Organizational constraint:
Security/compliance constraint:
Who disagreed and why:
```

## Your ownership

```text
I was directly accountable for:
I personally designed or implemented:
I delegated:
Other teams owned:
Executive or customer decisions remained with:
```

Avoid saying “I” for work performed by the team. Avoid saying “we” when the interviewer is evaluating your judgment.

## Decision and alternatives

| Option | Benefit | Risk/cost | Why accepted or rejected |
|---|---|---|---|
| A |  |  |  |
| B |  |  |  |
| C |  |  |  |

```text
Invariant protected:
Source of truth:
Failure domain:
Most dangerous edge case:
Rollback or escape path:
```

## Actions

```text
1.
2.
3.
4.
5.
```

Include investigation and communication, not only implementation.

## Evidence

```text
Before metric:
After metric:
Customer/business result:
Reliability/security result:
Delivery/toil result:
Cost result:
Adoption result:
How the result was measured:
```

## Leadership leverage

```text
Standard, policy, module, runbook, or platform created:
Teams influenced:
Conflict resolved:
Knowledge transferred:
Ownership after handoff:
```

## Reflection

```text
What I got wrong initially:
What changed my mind:
What I would do differently now:
What failure test or guardrail I added:
```

---

# Two-minute answer template

```text
The situation was [system and stakes]. The important constraint was [constraint],
and the invariant I needed to protect was [invariant].

I was accountable for [your scope]. We considered [options], and I chose [decision]
because [evidence and trade-off]. The key actions I took were [two or three actions],
including [cross-team leadership action].

The result was [measurable outcome]. More importantly, we left behind [durable
mechanism]. The lesson I carried forward was [specific learning].
```

# Five-minute deep-dive expansion

Be ready to expand any story into:

1. architecture or request path;
2. timeline and decision points;
3. competing hypotheses;
4. alternatives and rejected options;
5. security and failure modes;
6. rollout and rollback;
7. measurement method;
8. organizational conflict;
9. durable corrective action;
10. what you would do differently today.

# Principal-level follow-ups

Expect these questions:

- What did you personally decide?
- Which part failed because of your decision?
- Who disagreed with you, and were they reasonable?
- What evidence would have caused you to choose the other option?
- How did the system behave under a failure you did not predict?
- What did the organization learn, not only you?
- Which mechanism continued working after you left the project?
- How did you know the improvement was causal rather than coincidental?
- What business risk did you accept?
- What was the cost of your solution?

# Redaction and confidentiality

For interview use:

- replace company, customer, account, cluster, and project names;
- use defensible ranges when an exact number is confidential;
- describe the architecture at the level needed to explain the decision;
- do not reveal credentials, private endpoints, customer data, unpublished incidents, or proprietary algorithms;
- never alter the factual outcome to make the story stronger.

Safe:

> A regulated enterprise workload serving tens of thousands of daily transactions.

Unsafe:

> The exact customer, account identifier, internal hostname, incident ticket, and confidential revenue impact.

# Common weak-story patterns

- **Tool diary:** a list of commands without a decision or outcome.
- **Hero story:** everyone else failed until the candidate saved the system.
- **Perfect story:** no uncertainty, disagreement, mistake, or trade-off.
- **Team fog:** “we” hides personal ownership.
- **Number theater:** precise metrics that cannot be explained or defended.
- **Architecture-only:** no rollout, operations, or organizational adoption.
- **Blame postmortem:** failure attributed to one engineer rather than system conditions.
- **No legacy:** the work ended with deployment and left no standard, owner, or verification.

# Readiness checklist

A story is interview-ready only when you can answer yes to all of these:

- [ ] I can deliver it in two minutes without rambling.
- [ ] My personal ownership is explicit.
- [ ] The business or user stakes are clear.
- [ ] I name the invariant and failure domain.
- [ ] I explain at least one rejected alternative.
- [ ] I discuss a real constraint or disagreement.
- [ ] The result includes defensible evidence.
- [ ] I describe a durable organizational mechanism.
- [ ] I acknowledge a mistake, limitation, or trade-off.
- [ ] I can map the story to at least two technical chapters without forcing it.

## Practice method

1. Select one technical question.
2. Deliver its 90-second technical answer.
3. Add one sentence connecting it to a real story.
4. Tell the two-minute `SCALE` story.
5. Accept three adversarial follow-ups.
6. Score the answer using [`MOCK_INTERVIEW_SCORECARD.md`](MOCK_INTERVIEW_SCORECARD.md).
7. Remove unsupported claims and tighten the evidence.

The goal is not to memorize eighteen separate autobiographies. The goal is to build a truthful story bank that demonstrates repeated Staff/Principal judgment across architecture, incidents, security, delivery, and leadership.
