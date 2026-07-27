# FAANG Engineering Board Review — AWS DevOps / EKS Interview Track

> Independent Staff/Principal-level calibration of the AWS interview curriculum.
>
> These are hypothetical interview scenarios and educational exercises. This review does not claim to represent Amazon's private architecture or official interview process.

## Executive verdict

| Material | Board score | Hiring signal |
|---|---:|---|
| Screenshot questions answered as a service list | 5.5/10 | Senior-level familiarity, Staff no-hire risk |
| Completed AWS curriculum, read but delivered mechanically | 8.2/10 | Strong Senior; possible Staff |
| Curriculum delivered with explicit assumptions and evidence | 9.1/10 | Strong Staff hire |
| Board-calibrated delivery with leadership and personal evidence | 9.4+/10 | Competitive Principal signal |

The technical depth is now strong enough for serious Staff-level interviews. The remaining risk is not missing another AWS product. It is **delivery discipline**:

- clarify the ambiguous requirement before drawing architecture;
- distinguish documented service behavior from a sizing assumption;
- name the business invariant before naming the service;
- separate control plane, data plane, and application behavior;
- explain the failure domain and blast radius;
- define state authority and fencing;
- connect every mitigation to evidence and rollback criteria;
- state how the design will be proven under load and failure;
- demonstrate influence across teams, not only individual technical execution.

## Hiring committee summary

### Material delivered as an AWS service catalog

**No hire for Staff or Principal.**

A candidate who says “Route 53, CloudFront, ALB, EKS, DynamoDB, Karpenter, CloudWatch” sounds familiar with AWS but has not demonstrated engineering judgment. The interview signal remains weak because the candidate has not explained:

- how many requests or bytes the design must process;
- what consistency or ordering is required;
- which layer owns state;
- what happens when one AZ or Region fails;
- how retries are bounded;
- how the secondary Region is fenced;
- how a bad deployment is contained;
- how the claim is validated.

### Completed curriculum delivered competently

**Strong Senior; likely Staff hire.**

The candidate demonstrates production experience across EKS, Terraform, networking, workload identity, GitOps, observability, incident response, distributed systems, and recovery.

### Curriculum plus board calibration

**Competitive Principal-level performance.**

The expected voice is:

> I begin with the user-visible objective and the system invariant. I divide the design into explicit failure and authority domains, choose the simplest AWS service whose semantics satisfy the requirement, and state where the service does not solve the problem. I define overload, rollback, recovery, and measurable proof before declaring the design complete.

---

# Board-wide scoring rubric

| Dimension | Senior | Staff | Principal |
|---|---|---|---|
| Requirements | accepts prompt literally | clarifies scale, SLO, RTO/RPO, consistency | reframes ambiguous or unsafe assumptions and establishes business invariants |
| Architecture | names correct services | explains request/data/control paths and alternatives | defines cells, authority, organizational boundaries, and evolution strategy |
| Reliability | deploys across AZs | designs overload, failover, rollback, and recovery | sets reliability policy and drives verification across teams |
| Security | applies IAM and encryption | designs workload identity, trust boundaries, supply chain, and audit | defines enterprise guardrails and handles compromise scenarios |
| Operations | provides commands and dashboards | defines ownership, runbooks, SLOs, and evidence | improves the platform and reduces organizational toil/risk |
| Incident response | checks common components | isolates by request path and cohort, mitigates safely | establishes incident command, preserves evidence, and eliminates the failure class |
| Leadership | describes personal task | explains cross-team decision and trade-off | shows durable standards, influence, conflict resolution, and measurable outcomes |

## Automatic down-level signals

The board will down-level or reject an otherwise experienced candidate for statements such as:

- “EKS is highly available, so the application is highly available.”
- “DynamoDB scales infinitely.”
- “Use HPA on CPU and Karpenter handles the rest.”
- “Use `terraform apply` again because Terraform is idempotent.”
- “Force-unlock the state if the pipeline is blocked.”
- “Private EKS endpoint means the cluster is secure.”
- “IRSA and EKS Pod Identity are the same thing.”
- “A successful MQTT publish means the device executed the command.”
- “Route 53 failover makes DR automatic.”
- “Global Tables give strong global consistency for every workflow.”
- “CloudWatch dashboards will reveal the root cause.”
- “Exactly once is guaranteed by the queue or stream.”
- “A signed update is a safe update.”
- “The postmortem root cause was the engineer who deployed bad code.”

---

# Board scorecard by question

| # | Scenario | Final score | Principal-level emphasis |
|---:|---|---:|---|
| 1 | Multi-AZ EKS for millions | 9.2 | Scale math, cells, IP/quota limits, dependency capacity, proof |
| 2 | Terraform plus Argo CD/Flux | 9.3 | One owner per resource, bootstrap boundary, immutable promotion |
| 3 | Terraform state across accounts/Regions | 9.5 | State as control-plane database, one writer, recovery evidence |
| 4 | Secure Amazon EKS | 9.2 | Human/workload identity, node-credential isolation, network and supply-chain layers |
| 5 | Terraform vs CloudFormation/native | 9.0 | Resource ownership and operating model, not tool ideology |
| 6 | ASGs/Karpenter/CA/Spot | 9.3 | Separate pod and node loops; complete demand-to-serving timeline |
| 7 | Route 53-to-application outage | 9.4 | One failing request, external path proof, narrow reversible mitigation |
| 8 | API latency while nodes healthy | 9.3 | Clarify control-plane vs application API; allocate time with traces |
| 9 | Subset of users fail | 9.5 | Cohort matrix and matched healthy/failing request comparison |
| 10 | Dashboards show symptom, not cause | 9.2 | Raw evidence, changes, high-cardinality analysis, falsifiable hypotheses |
| 11 | Terraform partial apply | 9.6 | Reconcile configuration/state/reality; no destructive shortcut |
| 12 | Pods restart while probes pass | 9.4 | Process vs pod vs node termination; preserve previous evidence |
| 13 | Large outage postmortem | 9.4 | Customer impact, causal branches, owned verified corrective actions |
| 14 | Highly available mobile backend | 9.1 | Separate identity, preferences, notifications, and remote-command semantics |
| 15 | Secure global software updates | 9.5 | Signed manifest, staged fleet rollout, device-local authority and rollback |
| 16 | Multi-Region DR | 9.3 | RTO/RPO, source fencing, destination readiness, failback and reconciliation |
| 17 | Actionable observability | 9.4 | OTel standard, SLO paging, cardinality/cost, alert-quality program |
| 18 | Millions of events per second | 9.4 | Service semantics, partition design, backpressure, idempotency and replay |

---

# Round 1 — Infrastructure, EKS, and Infrastructure as Code

## 1. Highly available multi-AZ EKS for millions of users

### Board ruling

The question is a **capacity-envelope and failure-domain problem**, not an EKS product question.

The answer must convert “millions of concurrent users” into:

- peak requests or messages per second;
- average and maximum payload;
- active connections and connection duration;
- read/write ratio;
- p99 latency and availability objective;
- geography and data-residency constraints;
- expected burst and failure load;
- downstream database/cache/queue capacity.

### Top-1% correction

Do not say:

> EKS can scale to millions with Karpenter and HPA.

Say:

> I can claim the platform serves this load only after translating concurrency into RPS, bytes, and active connections, identifying every quota and dependency ceiling, and reproducing peak load during an AZ evacuation. EKS is one compute layer; it does not prove database, IP, load-balancer, DNS, or application capacity.

### Required failure-domain reasoning

Use:

- at least three AZs for regional workload placement;
- topology spread and anti-affinity;
- separate stable system capacity from elastic application capacity;
- cells or multiple clusters when one cluster's operational blast radius exceeds the SLO;
- enough surviving-AZ capacity, subnet IPs, and quotas for N+1 operation;
- stateless request handling and explicit state-service design;
- bounded retries, concurrency limits, and load shedding;
- progressive delivery by cell or cluster.

### Board challenge questions

1. What is your first bottleneck at 400,000 RPS?
2. How do you survive one AZ when every remaining AZ is already at 80%?
3. What happens if HPA requests 500 pods but the subnets have no pod IPs?
4. Why not one giant EKS cluster?
5. What evidence proves the word “millions”?

### Principal signal

The candidate explains **when organizational and failure-domain boundaries justify multiple clusters**, and how the platform team provides consistent operations without recreating one global blast radius.

---

## 2. GitOps with Terraform and Argo CD or Flux

### Board ruling

The key invariant is:

> One resource has one authoritative reconciler.

Terraform owns AWS infrastructure and the minimum bootstrap boundary. Argo CD or Flux owns long-running Kubernetes desired state after bootstrap. CI builds and validates immutable artifacts; it does not become a hidden second cluster reconciler.

### Top-1% answer

> I separate infrastructure state, GitOps state, and artifact state. Terraform establishes accounts, network, EKS, IAM, KMS, and the bootstrap controller. GitOps continuously reconciles platform add-ons and applications. CI builds once, signs and publishes an immutable digest, then proposes a desired-state change through pull request. Promotion reuses the same digest, and progressive delivery evaluates user SLIs before expanding traffic.

### Board-required safeguards

- no Terraform Helm release and Argo Application owning the same object;
- no `kubectl set image` from CI against Git-owned resources;
- explicit CRD/controller/custom-resource ordering;
- environment and cell promotion, not one global merge-to-everywhere;
- secret values outside Git and ordinary plan output;
- emergency changes reconciled back to Git immediately;
- restore GitOps control before routine deployment resumes.

### Board challenge questions

1. Who upgrades Argo CD itself?
2. What happens if the Git repository is unavailable?
3. What happens if the GitOps controller deletes a resource across 50 clusters?
4. How do you roll back a database schema?
5. When would Terraform still manage a Helm release?

### Principal signal

The candidate discusses the platform governance model: project/namespace boundaries, policy, controller topology, fleet rollout, and ownership transfer—not only YAML mechanics.

---

## 3. Terraform state across accounts and Regions

### Board ruling

Terraform state is a **privileged control-plane database**.

The strongest answer emphasizes:

- independent protected backend;
- versioning and encryption;
- exact-prefix permissions;
- short-lived CI identity;
- one writer per state;
- state partitioning by blast radius and lifecycle;
- tested recovery;
- deliberate migration from legacy DynamoDB locking where applicable.

### Top-1% answer

> Workload deployment roles can be distributed across accounts and Regions, but state authority is explicit. Each state has one protected pipeline writer, one backend lineage, one lock domain, and one recovery procedure. S3 replication is backup material—not an active-active state database.

### Board challenge questions

1. One bucket or one bucket per account?
2. Why not one state for every Region?
3. When can you force-unlock?
4. Can a replica S3 object become the new backend automatically?
5. How do you share outputs without giving consumers full state access?

### Principal signal

The candidate treats state recovery as an organizational capability with ownership, restore exercises, break-glass access, and risk segmentation.

---

## 4. Securing Amazon EKS

### Board ruling

Security must be layered across:

1. human control-plane identity;
2. Kubernetes authorization;
3. workload AWS identity;
4. node and metadata isolation;
5. VPC and pod networking;
6. secret lifecycle;
7. pod/runtime hardening;
8. artifact provenance and admission;
9. detective controls and incident recovery.

### Top-1% answer

> I assume one workload, one engineer session, or one automation path can be compromised. Human sessions are federated and short-lived; access entries and RBAC scope cluster authority. Pods receive workload-specific roles through Pod Identity or IRSA and cannot fall back to broad node credentials. Network access is explicitly allowed at the Kubernetes and VPC layers, secrets remain externally governed, and only verified immutable artifacts pass admission.

### Board challenge questions

1. Pod Identity or IRSA, and why?
2. Can a pod still obtain the node role?
3. Private API endpoint: what threat did you actually reduce?
4. NetworkPolicy or Security Groups for Pods?
5. What happens if your admission webhook is unavailable?
6. How do you rotate a database credential without outage?

### Principal signal

The candidate defines enterprise defaults, exception handling, policy availability, security validation, and account/cluster boundaries for stronger tenancy.

---

## 5. Terraform versus CloudFormation and AWS-native automation

### Board ruling

Tool selection is an **ownership and operating-model decision**, not ideology.

- Terraform fits multi-provider and standardized plan/state workflows.
- CloudFormation fits AWS-native stack state, StackSets, and Service Catalog ecosystems.
- CDK changes authoring abstraction but still deploys through CloudFormation.
- Systems Manager Automation fits operational runbooks.
- Config detects compliance; it should not create a controller war with IaC.

### Top-1% answer

> I standardize identity, review, policy, evidence, and recovery across a small approved set of control planes. Each resource class has one owner, one source repository, one deployment role, and one drift-remediation path. A deliberate hybrid is safer than forcing one tool into a lifecycle it handles poorly.

### Board challenge questions

1. Does CloudFormation rollback make it safer than Terraform?
2. When does CDK create hidden risk?
3. Can Config automatically remediate a Terraform-owned resource?
4. How do you migrate ownership between tools?
5. Why not one tool for everything?

### Principal signal

The candidate can define and govern an enterprise provisioning portfolio without creating duplicate ownership.

---

## 6. Capacity planning with ASGs, Karpenter, Cluster Autoscaler, and Spot

### Board ruling

Separate the loops:

```text
demand signal
  -> HPA/KEDA desired pods
  -> scheduler placement
  -> pending pods
  -> node autoscaler
  -> EC2 launch
  -> node Ready
  -> image/startup
  -> pod Ready
  -> target healthy
  -> user SLI recovers
```

### Top-1% answer

> I scale workloads from the signal closest to demand, then measure whether node supply becomes serving capacity before the SLO is violated. Karpenter and Cluster Autoscaler are alternative owners for elastic pools, not competing controllers. On-Demand protects the critical baseline; diversified Spot supplies interruption-tolerant excess capacity.

### Board challenge questions

1. Why did latency remain high after nodes launched?
2. Why not 100% Spot?
3. What does HPA CPU utilization actually divide by?
4. How much warm capacity do you keep?
5. What if Karpenter cannot obtain any permitted instance type?

### Principal signal

The candidate connects capacity policy to error budget, cost, quota governance, and workload architecture—not just autoscaler settings.

---

# Round 2 — Incident Response and Reliability

## 7. Route 53 to application outage

### Board ruling

Troubleshoot one real request from the outside in.

```text
client
 -> recursive resolver
 -> authoritative DNS
 -> edge/WAF/TLS
 -> load balancer
 -> VPC policy/path
 -> Kubernetes endpoint
 -> application
 -> dependency
 -> response path
```

### Top-1% answer

> I capture a failing request with UTC timestamp, resolver, DNS answers, TLS result, HTTP status, request/trace ID, and client cohort. At each boundary I ask whether the request arrived, whether policy allowed it, whether the component processed it, and whether the response returned. I use the narrowest reversible mitigation and prove recovery externally.

### Board challenge questions

1. Route 53 is healthy. Why are users still failing?
2. All ALB targets are healthy. What does that not prove?
3. Reachability Analyzer says reachable. Why can traffic still fail?
4. Why does lowering TTL now not fix cached answers?
5. Would you restart pods first?

### Principal signal

The candidate establishes incident command, controls concurrent changes, preserves evidence, and guides multiple teams through one request-path model.

---

## 8. API latency doubles while nodes remain healthy

### Board ruling

Clarify whether the interviewer means:

- Kubernetes API-server/control-plane latency; or
- customer-facing application API latency.

The curriculum correctly provides both.

### Application-latency top-1% answer

> Metrics tell me where and for whom latency changed. Traces allocate the extra time across ingress, application, and dependencies. Logs and profiles explain local behavior. Healthy nodes do not rule out pod CPU throttling, queueing, connection-pool waits, DNS, retry amplification, or database saturation.

### Control-plane top-1% answer

> I distinguish EKS control-plane service health from client-induced API pressure. I inspect request latency and throttling, audit and API logs, admission webhooks, LIST/WATCH volume, controller reconciliation, CRD size, client QPS/burst, and network path. I stop the abusive or failing client rather than attempting to tune a managed control plane blindly.

### Board challenge questions

1. Node CPU is 40%; why inspect CPU throttling?
2. A database span is slow; is the database the root cause?
3. Why might a controller generate API-server latency?
4. What happens if you scale the frontend while the database is saturated?
5. What if only p99 changed?

---

## 9. Deployment succeeds but a subset of users fails

### Board ruling

This is a **classification and confounding problem**.

Build a cohort matrix across:

- geography/resolver;
- IPv4/IPv6;
- version/pod/AZ/node;
- tenant/data shard;
- authentication provider;
- feature flag;
- new versus existing sessions;
- payload and operation type.

### Top-1% answer

> I compare a matched failing and successful transaction and find the first dimension that separates them. I do not conclude “AZ problem” if every new-version pod happens to run in that AZ; I separate correlated variables before mitigation. Recovery is verified for the original minority cohort, not only the aggregate.

### Board challenge questions

1. Why does a green Deployment not prove success?
2. All failures occur in one AZ. What else could explain it?
3. Why can only IPv6 clients fail?
4. Why can only old sessions fail?
5. How do you alert on a 2% critical tenant outage hidden by a 98% aggregate success rate?

### Principal signal

The candidate drives cohort-aware SLI and progressive-delivery standards across the organization.

---

## 10. Alarms fire, dashboards do not show root cause

### Board ruling

Move down the evidence pyramid:

```text
alarm definition
 -> metric dimensions
 -> top contributors
 -> trace
 -> log event
 -> change record
 -> configuration timeline
 -> network/runtime evidence
```

### Top-1% answer

> I verify the alarm first, then build one UTC timeline across Logs Insights, traces, Contributor Insights, CloudTrail, Config, AWS Health, deployment history, load-balancer/WAF logs, VPC Flow Logs, Resolver logs, and runtime evidence. Every hypothesis states expected evidence, disproving evidence, and the smallest safe test.

### Board challenge questions

1. Why not add another dashboard?
2. What does CloudTrail prove that application logs do not?
3. What does a VPC Flow Log `ACCEPT` not prove?
4. Would you trust an automatically generated root-cause hypothesis?
5. When is packet capture justified?

### Principal signal

The candidate improves evidence architecture and incident tooling after the event rather than merely adding more panels.

---

## 11. Terraform partial apply

### Board ruling

Reconcile three realities:

```text
configuration
Terraform state
actual AWS resources
```

### Top-1% answer

> I freeze every writer, preserve logs and lock metadata, prove account/Region/backend identity, back up the current state version, and inventory which provider operations completed. I then choose an explicit disposition for every resource—keep, import, recreate, complete, or deliberately remove—before one reviewed apply resumes convergence.

### Board challenge questions

1. Why not rerun apply immediately?
2. When is `terraform state rm` legitimate?
3. When is `-target` acceptable?
4. Why not restore the previous S3 object version?
5. What if the provider timed out but AWS completed the operation?

### Principal signal

The candidate creates recovery standards that prevent an urgent incident from becoming state corruption across many teams.

---

## 12. Pods restart while probes remain healthy

### Board ruling

First determine whether this is:

- a container restart in one pod UID;
- a pod replacement;
- a node-driven eviction or termination;
- a sidecar-only restart.

### Top-1% answer

> I inspect `lastState`, reason, exit code, signal, timestamps, events, and `kubectl logs --previous` before another restart overwrites evidence. Probes are periodic samples; they do not explain OOM, process completion, SIGTERM from a rollout, sidecar failure, node pressure, or an external disruption controller.

### Board challenge questions

1. How can liveness stay green if the process restarts?
2. Exit code 0: why is a Deployment still restarting?
3. Restart count is zero; how can users observe repeated replacement?
4. Would increasing the memory limit solve OOM?
5. What evidence do you collect from the node?

### Principal signal

The candidate establishes runtime evidence retention, safe node remediation, and application lifecycle standards rather than treating every failure as a probe issue.

---

## 13. Large AWS production outage postmortem

### Board ruling

A postmortem is successful only when it changes the system.

Separate:

- customer impact;
- trigger;
- contributing technical conditions;
- safeguard failures;
- detection and response gaps;
- organizational conditions;
- verified corrective actions.

### Top-1% answer

> I quantify failed customer transactions, SLO and error-budget consumption, data uncertainty, and recovery debt. I create one fact-based timeline, analyze why the fault escaped containment, and assign corrective actions across prevention, detection, mitigation, and recovery. Each critical action has an owner, due date, and an acceptance test such as a load test, restore, or game day.

### Board challenge questions

1. Who owns the postmortem?
2. What is the root cause?
3. How is “blameless” different from “ownerless”?
4. When is the postmortem closed?
5. How do you ensure actions do not disappear into backlog?

### Principal signal

The candidate changes incentives, platform standards, and cross-team operating mechanisms—not only the affected service.

---

# Round 3 — System Design, Scale, and Leadership

## 14. Highly available mobile backend

### Board ruling

Do not collapse the following into one generic API:

- identity and token issuance;
- ordinary user preferences;
- asynchronous notifications;
- remote commands to a protected device or resource.

Remote commands require explicit authorization, expiry, replay resistance, device identity, device-local safety, and result semantics.

### Top-1% answer

> The cloud authorizes and records a short-lived unique command; AWS IoT Core transports it; the device independently validates identity, expiry, sequence, prior execution, and local safety conditions. The API distinguishes accepted, delivered, acknowledged, executed, failed, and expired. A successful publish is never reported as physical success.

### Board challenge questions

1. Why not use Device Shadow for remote unlock?
2. How do you create exactly-once business effect over at-least-once delivery?
3. What happens when the device is offline?
4. How do Cognito failover and token issuer behavior work?
5. How do user-preference conflicts resolve across Regions?

### Principal signal

The candidate establishes command/security invariants that apply across a connected-product portfolio.

---

## 15. Global secure software updates

### Board ruling

Code signing proves authorization and integrity; it does not prove functional safety.

The design requires:

- immutable artifact and signed manifest;
- protected release and signing roles;
- exact hardware and dependency compatibility;
- staged representative cohorts;
- rollout rate, timeout, pause, and abort controls;
- resumable delivery;
- device-local verification;
- transactional or A/B install;
- local health validation and rollback;
- anti-replay and anti-downgrade;
- an update path independent of the application being replaced.

### Top-1% answer

> The cloud controls authorization, cohort, and rollout evidence. The artifact carries signed identity and compatibility metadata. The device preserves a trusted bootable version and remains the final authority. A rollout advances only after representative devices survive install, reboot, and a meaningful observation window.

### Board challenge questions

1. Why not publish one MQTT message to the fleet?
2. Does a valid signature make the release safe?
3. What if the update breaks the only network path used for rollback?
4. How do you detect devices that disappear and cannot report failure?
5. How do you patch an urgent vulnerability without bricking the fleet?

### Principal signal

The candidate connects product safety, security, release engineering, telemetry, support, and hardware recovery into one governed system.

---

## 16. Multi-Region disaster recovery

### Board ruling

Failover is an **authority transfer**, not a DNS edit.

The answer must define:

- RTO/RPO per capability;
- source and destination readiness;
- old-writer fencing;
- data promotion and conflict semantics;
- traffic canary and staged movement;
- uncertain transaction reconciliation;
- failback;
- tested runbook and automation safety.

### Top-1% answer

> I verify the destination is independently operable, choose the recovery point from the data model, fence the old writer, promote or enable the new authority, then move a small traffic cohort before broad shift. ARC routing controls and safety rules reduce operator error, but no routing service solves data consistency. Failback is a planned migration after replication and authority are restored.

### Board challenge questions

1. Why not fail over from one Route 53 health check?
2. What does an ARC readiness check prove, and what does it not prove?
3. Can Global Tables provide zero-RPO semantics for every transaction?
4. What happens if the old Aurora primary returns after promotion?
5. How do regional SQS queues recover?

### Principal signal

The candidate drives business-owned recovery objectives and repeated executable game days, not a paper DR plan.

---

## 17. Actionable observability platform

### Board ruling

Observability is a **decision platform**, not a storage platform.

The architecture should standardize:

- OpenTelemetry instrumentation and semantic attributes;
- local and gateway collectors;
- independent critical signal pipelines;
- CloudWatch native evidence;
- Prometheus/AMP metrics and rules;
- Grafana investigation;
- trace/log correlation;
- cardinality and cost budgets;
- SLO-driven paging;
- alert grouping, deduplication, inhibition, and ownership;
- fallback during observability outages.

### Top-1% answer

> I page only when a human must act now to protect users or prevent imminent exhaustion. SLO burn-rate and synthetic-transaction alerts own the pager; component signals enrich the incident or create tickets. Every page has an owner, runbook, impact statement, and reviewed alert-quality history. OpenTelemetry provides the evidence standard, while CloudWatch, X-Ray, AMP, and Grafana serve distinct operational roles.

### Board challenge questions

1. CloudWatch or Prometheus?
2. Why use X-Ray if you standardize on OpenTelemetry?
3. Why not retain every trace?
4. How do you stop a high-cardinality label from exploding cost?
5. What happens if the observability platform fails during the outage?
6. Would you page on every pod restart?

### Principal signal

The candidate defines service ownership, platform golden paths, alert-quality governance, and cost attribution across the engineering organization.

---

## 18. Millions of real-time events per second

### Board ruling

Assign one role to each service:

- Kinesis: partitioned ordered replayable log;
- SQS: independent work queue and retry isolation;
- SNS: high-throughput push fan-out;
- EventBridge: business event routing and integration;
- Lambda: managed stateless event handlers;
- EKS: long-running, custom, stateful, specialized, or continuously saturated consumers;
- S3: durable archive and replay source.

### Top-1% answer

> I size both events per second and bytes per second, design the partition key from the required ordering invariant, and assume at-least-once delivery. Consumers checkpoint only after durable idempotent effects. Kinesis preserves shared ordered history, SQS isolates downstream work and poison-event retries, and EventBridge receives meaningful derived business events rather than the raw telemetry firehose by default.

### Board challenge questions

1. Why not EventBridge for every event?
2. How does one hot customer affect Kinesis?
3. When do you use enhanced fan-out?
4. Can Lambda really process millions per second?
5. How do you create exactly-once business effect?
6. How do you replay six hours without overwhelming the database?

### Principal signal

The candidate defines producer contracts, schema governance, replay controls, tenant quotas, and capacity/error-budget policy across many consuming teams.

---

# Cross-question board findings

## Strongest parts of the curriculum

1. **State integrity:** Terraform locking, partial-apply recovery, import, and one-writer control are handled at a high bar.
2. **Failure-domain reasoning:** AZ, Region, cell, cluster, version, and tenant boundaries appear consistently.
3. **Evidence-driven incidents:** request paths, cohort matrices, traces, previous logs, CloudTrail, and network evidence are used correctly.
4. **Modern AWS corrections:** Pod Identity, native Terraform S3 lockfiles, OpenTelemetry-first tracing, ARC, and current service boundaries are acknowledged.
5. **Connected-device safety:** command state, device authority, update signing, A/B rollback, and anti-replay are substantially stronger than generic cloud answers.
6. **Distributed-systems honesty:** the curriculum avoids casual exactly-once, infinite scale, instant failover, and globally strong consistency claims.

## Remaining Principal-level gaps

The written curriculum is technically strong, but a candidate can still underperform if they do not add:

- a real production story with scale and outcome;
- a decision they influenced across teams;
- a disagreement and how it was resolved;
- a measurable before/after reliability or delivery result;
- an example where they rejected unnecessary complexity;
- an example where they stopped unsafe automation or rollout;
- a case where their first hypothesis was wrong and evidence corrected it;
- business framing: outage cost, error budget, compliance, or delivery speed.

## Required personal-story pattern

For each major topic, prepare one story using:

```text
Context
  scale, business function, ownership, constraints

Risk
  user impact, data/security risk, operational pain

Decision
  alternatives considered, invariant, trade-off, disagreement

Execution
  architecture, rollout, evidence, cross-team leadership

Failure handling
  what went wrong or what was tested

Result
  measured reliability, cost, speed, or risk reduction

Learning
  what standard or platform mechanism changed afterward
```

Do not invent scale or outcomes. Use exact values only when defensible; otherwise state ranges and the measurement method.

---

# Board delivery rules

## First 30 seconds

A strong opening uses this structure:

```text
1. Clarify the requirement or state assumptions.
2. Name the critical invariant.
3. Draw the primary request/data path.
4. State the failure-domain strategy.
```

Example:

> I will assume 200,000 peak RPS, three AZs, a p99 below 300 ms, and tolerance of one AZ without violating the error budget. My first invariant is that losing an AZ or one deployment cohort cannot remove more capacity than the remaining cells can absorb.

## Next 60 seconds

Cover:

- service selection and why;
- state and consistency;
- scale/control loops;
- security boundary;
- failure and rollback;
- evidence.

## When interrupted

Do not race through the prepared answer. Answer the follow-up directly, then reconnect it to the invariant.

Example:

> Yes, Global Tables replicate writes, but the important question is whether concurrent regional writes to the same business entity are acceptable. For command ordering, I would retain a home-region writer or use fencing rather than relying on last-writer-wins.

## When the prompt is impossible or underspecified

Challenge it respectfully.

> “Minimal downtime” is not enough to choose active-active. I need the write RPO and conflict semantics. A routing solution can move requests quickly, but it cannot make a single-writer database active-active without a transaction design.

## When you do not know an exact service limit

Do not guess.

> I would verify the current service quota for the target Region and account. Architecturally, I would model records and bytes per second, number of consumers, and partition skew, then load-test below a defined headroom threshold.

This is a stronger Staff signal than an incorrect memorized number.

---

# Final board verdict

## Technical level

**Strong Staff; Principal-capable with disciplined delivery and demonstrated organizational impact.**

## What would trigger a Staff hire

- correct architecture and incident reasoning across most scenarios;
- explicit assumptions and trade-offs;
- safe state and rollback behavior;
- realistic AWS and Kubernetes operations;
- evidence-driven validation;
- at least two strong production stories.

## What would trigger a Principal hire

- defines platform or organizational standards rather than solving one system;
- challenges unsafe requirements and aligns stakeholders around invariants;
- quantifies business and reliability outcomes;
- designs boundaries that let teams operate independently;
- creates mechanisms that prevent recurrence across many services;
- demonstrates judgment about what **not** to build;
- makes other engineers and teams more effective.

## Final expected voice

> I do not optimize for the most AWS services or the most automation. I optimize for explicit authority, bounded failure, measurable user outcomes, and recovery that does not corrupt state or weaken security. I choose the simplest design that satisfies the invariant, prove it under expected load and failure, and turn the result into a reusable platform capability.