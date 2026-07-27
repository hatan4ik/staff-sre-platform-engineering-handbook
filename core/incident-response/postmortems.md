# Postmortems, Causal Analysis, and Corrective-Action Governance

## Interview scenario

A large production incident has ended. Service is stable, temporary mitigations remain, and leadership asks for a postmortem.

The Staff/Principal task is not to produce a polished timeline or identify one person who made a mistake. It is to explain customer impact, distinguish trigger from contributing and systemic conditions, evaluate detection and response, create prioritized corrective actions, and prove that the failure class has been reduced through tests and operational changes.

---

## 1. Ninety-second Staff/Principal answer

> I start only after the service is stable and incident evidence is preserved. A facilitator who was not the primary incident decision maker builds one UTC timeline from user impact, SLOs, alerts, changes, logs, traces, events, incident communication, and recovery verification. Facts, inferences, and unknowns are labeled separately.
>
> I quantify customer and business impact using failed or degraded transactions, affected cohorts and regions, duration, latency, error-budget burn, data loss or inconsistency, backlog, contractual exposure, and recovery debt. Then I separate the trigger from contributing technical, detection, response, organizational, and latent architectural conditions. The useful question is not “who caused it?” but “why could a normal bug, failure, or human action produce this blast radius?”
>
> I review what delayed detection, incident declaration, diagnosis, mitigation, and full recovery. Corrective actions cover prevention, containment, detection, mitigation, and recovery. Every action has an owner, priority, due date, acceptance test, and explicit connection to a failure mode.
>
> The postmortem is not closed when the document is approved. Critical actions are verified through load tests, restore tests, failover exercises, game days, rollout simulations, or automated policy checks. Reusable lessons are shared without exposing sensitive details.

### Fifteen-second version

> Quantify impact, separate trigger from systemic conditions, analyze the entire response, and close only after corrective actions are tested.

---

## 2. Preconditions

Do not begin deep postmortem review while production remains unstable.

Confirm:

- Customer impact has ended or is controlled.
- Temporary mitigations are monitored.
- Incident command has transitioned to recovery.
- Evidence retention is active.
- Follow-up risks and recovery debt are recorded.
- Customer, regulatory, security, and executive communications have owners.

Preserve:

- Incident chat, bridge, and decision log.
- Pager events and acknowledgements.
- SLI and dashboard snapshots with queries.
- Application, infrastructure, edge, and dependency logs.
- Traces and profiles.
- Kubernetes events and previous container logs.
- Deployment, configuration, feature-flag, and policy history.
- Infrastructure plans, state versions, and audit events.
- Routing, DNS, certificate, load-balancer, and network evidence.
- Queue, data, and reconciliation state.

Do not rely on memory days later.

---

## 3. Roles

### Facilitator

- Runs the review.
- Separates fact from narrative.
- Challenges shallow causal language.
- Keeps the discussion psychologically safe and technically accountable.

Prefer someone who was not the primary incident decision maker.

### Incident commander

Explains command decisions, escalation, mitigation sequence, and communications.

### Technical owners

Provide evidence for applications, infrastructure, data, security, identity, networking, and dependencies.

### Customer or business representative

Translates infrastructure symptoms into user, contractual, operational, or financial impact.

### Corrective-action owners

Accept ownership of actions and their verification.

The process is blameless about human intent but not ownerless about system improvement.

---

## 4. Document structure

```text
1. Executive summary
2. Customer and business impact
3. Detection and incident declaration
4. Architecture and failure-domain context
5. Detailed UTC timeline
6. Trigger and contributing conditions
7. Why safeguards did not prevent or contain impact
8. Response and mitigation analysis
9. Recovery and residual risk
10. What went well
11. What made the incident harder
12. Corrective actions
13. Verification and closure criteria
14. Reusable lessons
15. Evidence appendices
```

The executive section should be understandable without raw implementation detail.

The technical sections should be precise enough that another engineer can reproduce the reasoning.

---

## 5. Quantify impact

Use customer transactions rather than only component symptoms.

Examples:

- Login, payment, command, playback, or API failure rate.
- Sessions unable to connect.
- p95 and p99 latency outside objective.
- Delayed notifications or events.
- Devices unable to receive commands or updates.
- Processing backlog and oldest-message age.
- Tenants, geographies, clients, or cohorts affected.

Impact dimensions:

| Dimension | Measure |
|---|---|
| Start and end | First customer impact to verified recovery |
| Scope | Users, requests, tenants, devices, regions, zones, products |
| Severity | Unavailable, degraded, delayed, incorrect, insecure, or unsafe |
| Data | Loss, duplication, inconsistency, stale reads, privacy impact |
| Reliability | SLO violation and error-budget consumption |
| Business | Revenue, contractual, support, regulatory, or reputational impact |
| Recovery debt | Backlog, manual correction, temporary controls, degraded redundancy |

State assumptions and uncertainty. Do not invent precision.

---

## 6. Build the UTC timeline

Example:

```text
14:02 first user transaction failures
14:04 p99 latency alert fires
14:06 rollout reaches 50%
14:09 on-call acknowledges
14:14 incident declared
14:22 errors correlated with one version and two cells
14:27 rollout paused
14:32 rollback begins
14:41 old version serving; retry storm continues
14:48 retries reduced and traffic shed
14:55 user success rate recovers
15:07 backlog begins draining
15:28 every affected cohort verified healthy
```

Include:

- Customer impact.
- Monitoring and paging.
- Changes.
- Hypotheses.
- Decisions and owners.
- Mitigations.
- Recovery evidence.
- Communications.

Mark facts, inferences, and unknowns:

```text
FACT: gateway 5xx increased at 14:02.
FACT: image digest B received 50% traffic at 14:06.
INFERENCE: retries amplified database connection pressure.
EVIDENCE: retry spans, connection count, and recovery after retry reduction.
UNKNOWN: whether one client retry policy contributed before server telemetry began.
```

---

## 7. Causal model

Avoid:

```text
Root cause: engineer deployed bad code.
```

Production systems are expected to experience defects, failures, and human mistakes. Analyze why the system allowed the event to become a large incident.

### Trigger

The initiating event.

Examples:

- Release changed connection behavior.
- Certificate expired.
- Node image introduced runtime failure.
- Dependency region became unavailable.
- Incorrect route or policy was applied.

### Contributing technical conditions

Examples:

- Retries were unbounded.
- Canary did not include the write path.
- One shared dependency created a global failure domain.
- Rollback preserved the overload mechanism.
- Readiness did not represent business capability.
- Quota and IP headroom were insufficient.

### Detection conditions

Examples:

- Alert used aggregate success rate.
- Affected cohort was absent from telemetry.
- Synthetic checked only `/health`.
- Error-budget burn was not paged.
- Alert routed to the wrong owner.

### Response conditions

Examples:

- No incident commander.
- Responders changed multiple layers at once.
- Restarts destroyed evidence.
- Access or tooling delayed diagnosis.
- Runbook did not cover overload or failover.

### Organizational conditions

Examples:

- Shared dependency ownership was unclear.
- Operational readiness review omitted failure testing.
- Release pressure bypassed progressive delivery.
- Corrective actions from an earlier incident were never verified.

### Latent architectural conditions

Examples:

- Global blast radius.
- No cell boundaries.
- No admission control or load shedding.
- No fencing for failover.
- Recovery path depended on the failed system.

A useful causal graph has multiple branches. One linear “Five Whys” chain is rarely sufficient.

---

## 8. Analyze detection

Questions:

- Which signal detected impact first?
- Did customers report the incident before monitoring?
- Did the alert measure a user SLI or component proxy?
- Was the affected cohort visible?
- Was the page actionable and routed correctly?
- Were thresholds sensitive without being noisy?
- Did missing data or sampling hide the failure?
- Did dashboards link to evidence and runbooks?

Metrics:

- Time to detect.
- Time from impact to first page.
- Time to acknowledge.
- Impact accumulated before detection.
- Error-budget burn before declaration.
- Duplicate or false pages.

Potential actions:

- Business-transaction synthetic.
- Multi-window burn-rate alert.
- Per-cell or protected-cohort SLI.
- Deployment annotation.
- Queue-age or saturation leading indicator.
- Certificate, quota, or capacity expiry alert.

---

## 9. Analyze response

### Incident command

- When was the incident declared?
- Were roles explicit?
- Was there one decision log?
- Were communications regular and accurate?
- Were experts engaged at the correct time?
- Did responders duplicate or conflict?

### Evidence handling

- Were logs, previous states, profiles, and events preserved?
- Did restarts or rollback destroy evidence?
- Were timestamps aligned?
- Did access to the correct account, cluster, or region exist?
- Was evidence searchable and correlated?

### Hypothesis quality

- Were hypotheses explicit?
- Did each have confirming and disconfirming evidence?
- Were changes made one at a time?
- Did the team compare affected and healthy cohorts?
- Was the first plausible explanation treated as fact?

Response metrics:

- Time to incident declaration.
- Time to first plausible hypothesis.
- Time to first effective mitigation.
- Number of failed mitigations.
- Number of simultaneous uncontrolled changes.
- Time between communications.

These metrics are for system learning, not individual ranking.

---

## 10. Analyze mitigation

Questions:

- Was mitigation reversible?
- Did it target the failed cohort or widen impact?
- Did it create downstream overload?
- Was rollback compatible with schema and configuration?
- Did traffic shifting validate destination capacity and state?
- Were retries, queues, and concurrency controlled?
- Did temporary security changes create risk?
- Was mitigation delayed by a missing control plane?

Classify mitigations:

| Type | Example |
|---|---|
| Containment | Pause rollout, isolate cell, remove target |
| Load reduction | Shed optional work, limit concurrency, reduce retries |
| Restoration | Roll back code, configuration, route, policy, or certificate |
| Traffic shift | Move to healthy region, cell, or dependency |
| Degraded mode | Serve stale data or disable noncritical capability |
| Manual repair | Reconcile state, replay queue, correct data |

Record why the selected action was safer than alternatives.

---

## 11. Analyze recovery

Service restoration and full recovery may be different times.

Measure:

- Time to effective mitigation.
- Time to user-SLI recovery.
- Time to drain backlog.
- Time to reconcile data.
- Time to restore full redundancy.
- Time to remove temporary changes.
- RTO and RPO achieved versus target.

Hidden recovery debt:

- Disabled policy or security control.
- Elevated quota or emergency capacity.
- Manual DNS or routing override.
- Paused GitOps or autoscaling.
- Inconsistent or unprocessed data.
- Emergency credentials.
- Degraded replication.
- Reduced monitoring.

Every temporary condition needs an owner, expiration condition, and validation.

---

## 12. What went well

Record mechanisms that reduced impact.

Examples:

- User-SLI alert detected impact early.
- Per-cell telemetry exposed the cohort.
- Rollback was fast and schema-compatible.
- Load shedding protected the dependency.
- Incident roles prevented duplicate changes.
- External synthetic verified recovery.
- Backups or replay enabled data correction.

Turn successful mechanisms into maintained platform capabilities rather than one-time heroics.

---

## 13. What made the incident harder

Examples:

- Aggregate dashboards hid a cohort.
- No request or trace ID across boundaries.
- Mutable image tags obscured version.
- Runbook was missing or stale.
- Access required manual approval during outage.
- Recovery depended on the unhealthy control plane.
- Failure injection had never tested this interaction.
- Ownership of a shared dependency was unclear.
- Telemetry pipeline lost data under load.

Avoid vague labels such as “communication issue.” Describe the missing mechanism and its impact.

---

## 14. Corrective-action taxonomy

Actions should cover the complete control system.

### Prevention

- Safer API or configuration contract.
- Static analysis and policy checks.
- Compatibility and migration tests.
- Capacity, quota, and dependency budgets.
- Cell or tenant isolation.

### Containment

- Progressive delivery.
- Blast-radius limits.
- Circuit breakers and bulkheads.
- Admission control and load shedding.
- Per-cell or per-shard failover.

### Detection

- User SLI and burn-rate alert.
- Protected-cohort telemetry.
- Business synthetic.
- Change and deployment correlation.
- Telemetry pipeline monitoring.

### Mitigation

- One-command rollback or target removal.
- Feature disable.
- Retry and concurrency control.
- Tested degraded mode.
- Automated fencing or traffic shift.

### Recovery

- Backup and restore.
- Replay and reconciliation.
- Failback procedure.
- Temporary-change cleanup.
- Evidence collection automation.

### Organizational

- Ownership model.
- Operational readiness review.
- On-call training.
- Incident command practice.
- Cross-team dependency contract.

---

## 15. Action quality

Weak action:

```text
Be more careful during deployments.
```

Stronger action:

```text
Add a rollout gate that compares write-path error-budget burn,
database connection growth, and retry rate for each cell before
exposure can increase above 5%.
```

Every action should contain:

- Failure mode addressed.
- Owner.
- Priority.
- Due date.
- Dependencies.
- Measurable acceptance criteria.
- Verification method.
- Residual risk.

Prioritize by expected risk reduction, not document completeness.

Useful categories:

- P0: immediate unsafe or repeatable exposure.
- P1: high-severity containment, detection, or recovery gap.
- P2: important resilience and operational improvement.
- P3: lower-risk cleanup or convenience.

Organizations may use different labels; the principle is explicit prioritization.

---

## 16. Verification and closure

A postmortem is not complete when the action ticket is marked done.

Verification options:

- Unit, integration, and compatibility tests.
- Production-like load test.
- Dependency slowdown and retry test.
- Backup restore.
- Regional failover and failback.
- Node or zone loss.
- Canary abort simulation.
- Queue replay and idempotency test.
- Security policy negative test.
- Game day.
- Automated policy and drift check.

Closure criteria:

```text
critical actions implemented
acceptance tests passed
temporary mitigations removed or accepted as permanent
residual risk documented and approved
runbooks and ownership updated
lessons shared
```

If an action is intentionally rejected, document the reason and accepted risk.

---

## 17. Corrective-action governance

Track across incidents:

- Open actions by severity and age.
- Repeat incidents with the same failure class.
- Verification status.
- Actions blocked by platform gaps.
- Teams or shared dependencies with recurring exposure.
- Risk reduction delivered.

Avoid measuring only ticket closure rate. A large number of low-value completed tickets can hide one unaddressed systemic risk.

Review actions in reliability planning and leadership forums, not only after the incident.

---

## 18. Blamelessness and accountability

Blamelessness means:

- Assume people acted reasonably given information, incentives, tools, and constraints.
- Avoid punishment for reporting errors.
- Examine system design and decision context.

It does not mean:

- Facts are softened.
- Unsafe choices are ignored.
- Ownership disappears.
- Policy violations cannot be investigated separately.
- Corrective actions are optional.

If misconduct or deliberate policy bypass is suspected, handle it through the appropriate process without converting the technical review into a courtroom.

---

## 19. Reusable lessons

Share lessons that apply beyond one cloud service or team:

- Which hidden coupling expanded blast radius?
- Which metric or field would have shortened diagnosis?
- Which control made mitigation possible?
- Which recovery mechanism was untested?
- Which assumption proved false?
- Which organization boundary lacked ownership?

Sanitize:

- Customer data.
- Credentials and security-sensitive details.
- Employee personal information.
- Exploit-enabling specifics where disclosure is unsafe.

Public or company-wide summaries can be shorter than the internal evidence package.

---

## 20. Common weak answers

### “Find the root cause and fix it”

Large incidents usually have multiple causal conditions. Fixing only the trigger leaves the blast radius, detection, and recovery gaps.

### “It was human error”

Human action is expected. Ask why the system accepted, propagated, and failed to contain it.

### “Blameless means no accountability”

Action ownership and verification remain explicit.

### “Create more alerts”

Alerts without user relevance, ownership, and a response action increase noise.

### “Close when every ticket exists”

Tickets are plans. Closure requires implementation and verification.

### “MTTR improved, therefore reliability improved”

Faster recovery is valuable, but repeatability, customer impact, data correctness, and residual risk also matter.

### “The cloud provider caused it”

The postmortem must still analyze architecture, isolation, detection, failover, dependency assumptions, and recovery under provider failure.

---

## 21. Adversarial interview questions

### Who should write the postmortem?

Technical owners provide evidence, but a neutral facilitator should structure the review and challenge causal claims. The document is a shared product, not one person's defense.

### What if leadership wants one root cause?

Provide a concise initiating trigger while preserving the causal graph of contributing and systemic conditions. One sentence should not erase the controls that failed.

### How do you prioritize dozens of actions?

Rank by risk reduction: severity, likelihood, blast radius, detectability, recoverability, effort, and dependency. Focus on actions that remove a failure class or add strong containment.

### What if the incident cannot be reproduced?

Preserve uncertainty, improve evidence, test the most plausible mechanisms in a controlled environment, and implement low-regret containment. Do not manufacture certainty.

### Should every incident have a postmortem?

Use criteria based on customer impact, error-budget burn, data or security risk, near miss, repeatability, and learning value. The review depth can vary.

### How do you prevent action items from dying?

Make them owned, prioritized, visible in planning, tied to acceptance tests, reviewed by leadership, and included in closure criteria.

### How do you measure postmortem quality?

Look for repeated failure classes, action verification, improved detection and mitigation, reduced blast radius, and evidence that exercises succeed—not document length.

---

## 22. Staff/Principal checklist

A strong answer includes:

- Stable service and preserved evidence.
- Neutral facilitation.
- Customer and business impact.
- One UTC timeline.
- Fact versus inference.
- Trigger plus contributing and systemic conditions.
- Detection, response, mitigation, and recovery analysis.
- Recovery debt.
- Prevention, containment, detection, mitigation, and recovery actions.
- Owner, priority, due date, and acceptance test.
- Verification before closure.
- Blamelessness with accountability.
- Reusable lessons and governance.

---

## Related canonical material

- [`request-path-debugging.md`](request-path-debugging.md)
- [`cohort-analysis.md`](cohort-analysis.md)
- [`../observability/evidence-beyond-dashboards.md`](../observability/evidence-beyond-dashboards.md)
- [`../distributed-systems/10-observability-and-incident-labs.md`](../distributed-systems/10-observability-and-incident-labs.md)
