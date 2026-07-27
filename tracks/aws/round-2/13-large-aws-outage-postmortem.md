# Question 13 — Postmortem After a Large AWS Production Outage

## Interview prompt

Describe how you would conduct a postmortem after a large-scale AWS production outage. What metrics, logs, and operational improvements would you focus on?

## What the interviewer is testing

The interviewer is looking for more than a timeline document. A Staff/Principal engineer must show that the postmortem:

- separates trigger, contributing conditions, and systemic causes
- quantifies customer and business impact
- analyzes detection, response, mitigation, and recovery
- avoids blame while preserving accountability
- produces prioritized, owned corrective actions
- changes architecture, operations, and verification mechanisms
- is closed only when fixes are tested

AWS uses the concept of Correction of Errors and recommends post-incident analysis through the Operational Excellence and Reliability guidance. The goal is not to find one person or one broken component. It is to remove the class of failure.

---

## 90-second Staff/Principal answer

> I begin the postmortem after service is stable and evidence is preserved. I assign a facilitator who was not the primary decision maker, build a single UTC timeline from customer reports, SLOs, alarms, deployments, CloudTrail, AWS Health, application logs, traces, Kubernetes events, and incident communications, and clearly separate facts from hypotheses.
>
> I quantify impact using failed or degraded customer transactions, affected cohorts and Regions, duration, SLO and error-budget consumption, data loss or inconsistency, queue backlog, contractual impact, and recovery time. I analyze the trigger, contributing technical and organizational conditions, why safeguards did not contain the blast radius, why detection or diagnosis was delayed, and why the chosen mitigation succeeded or failed.
>
> Corrective actions cover prevention, detection, mitigation, and recovery. Each action has an owner, priority, due date, measurable acceptance test, and link to the failure mode. High-value actions might add cell boundaries, overload controls, safer rollout gates, state recovery, quota monitoring, synthetic transactions, dependency failover tests, or runbook automation.
>
> I review the findings with engineering, operations, security, and business stakeholders, share reusable lessons without exposing sensitive details, and do not close the postmortem until critical actions are verified through load tests, failover exercises, restore tests, or game days.

---

## 1. Preconditions before the postmortem

Do not start deep analysis while the service is still unstable.

Confirm:

- customer impact has ended or is controlled
- temporary mitigations are monitored
- incident command has transitioned to recovery
- evidence retention is active
- follow-up risks are documented
- customer and executive communications have an owner

Preserve:

- incident chat and command log
- pager events and acknowledgements
- dashboard snapshots and queries
- application and infrastructure logs
- traces and profiles
- Kubernetes events and previous logs
- CloudTrail and Config history
- AWS Health events
- deployment and feature-flag history
- Terraform plans and state versions where relevant
- load-balancer, WAF, DNS, and network logs

Do not rely on memory several days later.

---

## 2. Roles in the postmortem process

### Facilitator

Runs the review, keeps it evidence-based, and challenges vague causal language.

Prefer a facilitator who was not the primary incident commander or person whose change is under analysis.

### Incident commander

Explains operational decisions, escalation, and mitigation sequence.

### Technical owners

Provide evidence for affected services, infrastructure, data, security, and dependencies.

### Customer or business representative

Explains impact in user and business terms.

### Action owners

Accept responsibility for corrective actions and verification.

The process is blameless about human intent but not ownerless about system improvement.

---

## 3. Postmortem document structure

```text
1. Executive summary
2. Customer and business impact
3. Detection and incident declaration
4. Architecture and failure-domain context
5. Detailed UTC timeline
6. Trigger and contributing conditions
7. Why safeguards did not prevent or contain impact
8. Response and mitigation analysis
9. Recovery and validation
10. What went well
11. What made the incident harder
12. Corrective actions
13. Verification and closure criteria
14. Reusable lessons
15. Appendices and evidence links
```

A concise executive section should allow leadership to understand the event without reading raw logs.

---

## 4. Quantify customer impact

Use customer transactions, not only infrastructure symptoms.

Examples:

- failed login rate
- checkout or payment failure rate
- API success rate
- percentage of sessions unable to connect
- p95 and p99 latency beyond SLO
- notifications delayed
- devices unable to receive updates
- data-processing delay
- tenants or geographies affected

### Impact dimensions

| Dimension | Measure |
|---|---|
| Start and end | first customer impact to verified recovery |
| Scope | users, tenants, requests, devices, Regions, AZs, products |
| Severity | unavailable, degraded, delayed, incorrect, or unsafe |
| Data | loss, duplication, stale reads, inconsistency, or privacy impact |
| SLO | error-budget burn and violated objectives |
| Business | revenue, contractual, operational, support, or reputational impact |
| Recovery debt | queues, retries, manual corrections, or customer remediation remaining |

Do not convert an unknown impact into a precise-looking estimate without stating assumptions.

---

## 5. Build the UTC timeline

Example:

```text
14:02 first customer transaction failures
14:04 p99 latency alert fires
14:06 deployment reaches 50%
14:09 on-call acknowledges
14:14 incident declared SEV-1
14:22 errors correlated with new version in two cells
14:27 rollout paused
14:32 rollback begins
14:41 old version serving, DB connection storm continues
14:48 retries reduced and traffic shed
14:55 customer success rate recovers
15:07 queues begin draining
15:28 all cohorts verified healthy
```

Include:

- user impact
- monitoring signals
- changes and deployments
- page and escalation
- hypotheses
- decisions
- mitigations
- recovery proof
- communication events

### Mark fact versus inference

```text
FACT: ALB target 5xx increased at 14:02.
FACT: version v2.7 received 50% traffic at 14:06.
INFERENCE: connection retries amplified database saturation.
EVIDENCE: trace retry counts, DB connections, and rollback behavior.
```

---

## 6. Analyze detection

Questions:

- Which signal detected the issue first?
- Did customers detect it before monitoring?
- Did the alert measure a business SLI or a component proxy?
- Was the alert routed to the correct owner?
- Was the threshold sensitive enough without being noisy?
- Did missing dimensions hide one cohort?
- Was the page actionable?
- Did the alarm include links to relevant dashboards and runbooks?

Metrics:

- time to detect
- time from alarm to acknowledgement
- percentage of impact before detection
- false or duplicate pages
- SLO burn before incident declaration

Improvement examples:

- business transaction canary
- multi-window burn-rate alert
- per-cell or per-tenant-tier SLI
- deployment annotation
- queue-age alert
- certificate or quota leading indicator

---

## 7. Analyze response

### Incident command

- Was an incident commander established early?
- Were roles explicit?
- Did responders duplicate work?
- Was there one decision log?
- Were communications regular and accurate?
- Were subject-matter experts engaged at the right time?

### Evidence handling

- Were logs and previous container states preserved?
- Did restarts destroy evidence?
- Were timestamps aligned?
- Did responders have access to the correct account and Region?
- Did permissions or tooling delay diagnosis?

### Hypothesis quality

- Were hypotheses stated and tested?
- Were changes made one at a time?
- Did responders chase aggregate dashboards instead of affected cohorts?
- Was the first plausible explanation treated as fact?

### Metrics

- mean time to acknowledge
- time to incident declaration
- time to first plausible hypothesis
- time to effective mitigation
- number of failed mitigation attempts
- number of simultaneous uncontrolled changes

---

## 8. Analyze mitigation and recovery

Questions:

- Was the mitigation reversible?
- Did it target the failing cohort?
- Did it create downstream overload?
- Was rollback compatible with schema and configuration?
- Did traffic shifting preserve capacity in the destination?
- Were queues and retries controlled?
- Did service recover before data consistency?
- How was recovery verified externally?

### Recovery metrics

- time to mitigate
- time to recover user SLI
- time to drain backlog
- time to restore full redundancy
- time to remove temporary changes
- RTO and RPO achieved versus target

### Hidden recovery debt

Document:

- disabled security or policy controls
- elevated quotas or capacity
- manual DNS or routing changes
- paused GitOps or autoscaling
- inconsistent data
- unprocessed messages
- emergency credentials

Every temporary mitigation needs an owner and expiration condition.

---

## 9. Causal analysis

Avoid a single shallow root cause such as:

```text
Root cause: engineer deployed bad code.
```

A production system is expected to encounter bugs and human mistakes. Ask why the error became a large outage.

### Causal layers

#### Trigger

The event that initiated the failure.

Example:

- new release changed database connection behavior

#### Contributing technical conditions

- retries were unbounded
- canary did not cover the write path
- every cell shared one database writer
- connection pools opened simultaneously
- rollback did not reduce retry pressure

#### Detection and response conditions

- alert used aggregate error rate
- traces lacked retry-count attributes
- database connection saturation was not on the service dashboard
- runbook did not include overload mitigation

#### Organizational conditions

- ownership of the shared database was unclear
- no operational readiness review for connection behavior
- load test did not model dependency degradation
- release deadline overrode progressive delivery requirement

#### Latent design conditions

- no cell-level data isolation
- no admission control or load shedding
- one global blast radius

---

## 10. Five Whys: use carefully

The Five Whys can help explore causal depth, but complex outages usually have multiple causal branches.

Example:

```text
Why did requests fail?
  Database connections were exhausted.

Why were connections exhausted?
  New pods opened large pools and retried failed requests.

Why did all cells do this together?
  Deployment and autoscaling were globally coordinated.

Why was there no containment?
  Database and rollout architecture lacked cell budgets.

Why was this not found before production?
  Load tests modeled steady-state success, not dependency slowdown and retry behavior.
```

Also analyze parallel branches such as alerting, rollback, and ownership.

---

## 11. Metrics and logs to preserve

### User and service metrics

- request and transaction success rate
- p50/p95/p99 latency
- traffic and concurrency
- SLO burn rate
- retries, timeouts, and load shedding
- queue depth and oldest-message age

### Edge and network

- Route 53 answers and health checks
- CloudFront and WAF logs
- ALB/NLB metrics and access logs
- VPC Flow Logs
- NAT and endpoint metrics
- Resolver query logs

### EKS

- deployment and ReplicaSet history
- pod status and previous logs
- control-plane and audit logs
- Kubernetes events
- HPA desired/current/available replicas
- pending pods and node-provisioning timeline
- node pressure and disruption events
- CoreDNS and CNI signals

### Application

- structured logs with request and trace IDs
- traces and service maps
- profiles, GC, thread, and connection pools
- feature-flag and configuration history

### Data and messaging

- DB load, locks, queries, connections, failover
- cache hit ratio, evictions, latency, hot keys
- DynamoDB throttling and latency
- queue depth, age, DLQ, and consumer throughput

### Change and account evidence

- CloudTrail
- AWS Config history
- AWS Health
- Terraform plans and state versions
- Git and GitOps sync history
- CI/CD logs
- IAM and secret changes

---

## 12. What went well

Record successful mechanisms, not compliments only.

Examples:

- SLO alert detected impact before customer reports
- per-cell dashboards exposed the failure cohort
- canary rollback was one command and preserved schema compatibility
- incident commander reduced duplicate work
- queue buffering prevented data loss
- synthetic checks verified recovery externally

Protect these mechanisms from being removed in future simplification or cost-cutting.

---

## 13. What made the incident harder

Examples:

- no route-level latency histogram
- mutable image tag
- incomplete trace propagation
- missing WAF or Resolver logs
- no access to production account for the on-call
- ambiguous service ownership
- broad Terraform state lock blocked unrelated recovery
- runbook used outdated commands
- alert fatigue delayed acknowledgement
- all retries synchronized
- rollback restored code but not configuration

Convert each important difficulty into an action or explicit accepted risk.

---

## 14. Corrective action taxonomy

### Prevent recurrence

- fix code defect
- enforce schema compatibility
- bounded retries with jitter
- cell or shard isolation
- quota and dependency budgets
- policy-as-code guardrail

### Reduce blast radius

- staged rollout by cell
- per-tenant or per-region rate limit
- separate state and deployment boundaries
- bulkheads and circuit breakers
- independent caches or data partitions

### Detect faster

- business SLI
- multi-window burn-rate alarm
- synthetic transaction
- cohort-aware dashboard
- change correlation

### Diagnose faster

- trace and log correlation
- saved Logs Insights queries
- deployment annotations
- runtime profiling
- automated evidence collection

### Mitigate faster

- one-click or runbook rollback
- traffic shift
- feature kill switch
- load shedding
- dependency fallback

### Recover safely

- tested restore
- queue replay
- state reconciliation
- data-repair tooling
- region or cell failover exercise

---

## 15. Prioritize actions

Do not produce a list of 40 equal-priority tasks.

Score using:

```text
risk reduction
× recurrence likelihood
× blast-radius reduction
× implementation confidence
÷ cost and complexity
```

A practical priority model:

| Priority | Meaning |
|---|---|
| P0 | Immediate safety issue or likely repeat; blocks normal operations |
| P1 | Major risk-reduction action with committed near-term delivery |
| P2 | Important resilience or diagnostic improvement |
| P3 | Backlog optimization or low-likelihood hardening |

Every action includes:

- owner
- due date
- tracking link
- risk addressed
- acceptance test
- dependencies
- status

---

## 16. Write measurable acceptance criteria

Weak action:

```text
Improve monitoring.
```

Strong action:

```text
Add a two-window burn-rate alert for checkout success SLO by production cell.
Test by injecting 5% checkout failures into one cell and verify paging within
five minutes without paging healthy cells.
```

Weak action:

```text
Make failover better.
```

Strong action:

```text
Demonstrate automated regional read failover and controlled write promotion
within the documented RTO, with zero acknowledged writes lost beyond the RPO.
Record the game-day evidence and rollback procedure.
```

---

## 17. Verification and game days

Critical actions should be tested through:

- unit and integration tests
- production-like load tests
- canary rollout
- dependency latency injection
- AZ evacuation
- Spot interruption
- DNS or certificate failure
- Terraform state recovery
- backup restore
- regional failover
- queue replay

A merged pull request is not evidence that the resilience problem is solved.

---

## 18. Governance and closure

### Review audience

- service owners
- SRE/platform
- security where relevant
- data owners
- support/customer representatives
- engineering leadership

### Closure criteria

Close the postmortem only when:

- facts and impact are agreed
- P0/P1 actions have owners and dates
- temporary mitigations are tracked
- critical fixes are verified
- accepted risks are approved
- lessons are shared with affected teams

Do not keep the incident open forever for every low-priority improvement. Separate incident closure from long-term backlog tracking while preserving ownership.

---

## 19. Blameless does not mean consequence-free

Use neutral language:

```text
The deployment system allowed a global 100% rollout without dependency guardrails.
```

Avoid:

```text
The engineer recklessly deployed bad code.
```

Still address:

- ignored controls
- policy violations
- unsafe incentives
- training gaps
- access misuse

The purpose is learning and system correction, with appropriate management processes handled separately when necessary.

---

## 20. Reusable learning

Extract lessons that apply beyond one service:

- retry policy standard
- cell architecture requirement
- state-backend control
- common synthetic transaction framework
- operational readiness review question
- shared rollout-analysis template
- quota and saturation catalog
- incident evidence-collection automation

Update:

- platform golden paths
- architecture standards
- runbooks
- interview and training material
- operational readiness reviews

---

## Adversarial follow-ups

### “Who owns the postmortem?”

The affected service owns the outcome, a neutral facilitator owns the review process, and each corrective action has an explicit engineering owner. SRE can enable the mechanism but should not absorb every team's accountability.

### “What is the root cause?”

I distinguish trigger, contributing conditions, safeguard failures, and organizational conditions. Large outages rarely have one useful single cause.

### “How do you ensure actions are completed?”

Actions live in the normal engineering tracking system with priority, owner, due date, acceptance test, leadership review, and operational-risk visibility. Critical actions are verified through tests or game days.

### “Would you publish the postmortem?”

I share internal detail broadly enough to create learning, with security, privacy, legal, and customer sensitivity controls. External communication is coordinated through the appropriate business and legal process.

### “What metric matters most?”

Customer transaction impact and SLO/error-budget consumption are primary. Component metrics explain mechanism but do not define the outage alone.

---

## Weak answers to avoid

- “Write a timeline and use Five Whys.”
- naming one engineer or one component as the entire root cause
- measuring impact only by pod or instance downtime
- listing actions without owners or tests
- declaring an action done when code merges
- ignoring failed mitigations and communication problems
- removing all human judgment through automation
- treating blameless as no accountability
- closing before temporary mitigations are removed or owned
- failing to share cross-team lessons

---

## Closing statement

> A postmortem is successful when it changes the system. I quantify customer impact, reconstruct evidence, explain why the fault escaped containment, and convert the learning into owned, testable improvements across prevention, detection, mitigation, and recovery.