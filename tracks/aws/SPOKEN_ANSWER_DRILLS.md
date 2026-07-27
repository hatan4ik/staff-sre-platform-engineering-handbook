# AWS Interview Spoken-Answer Drills

This document converts the deep curriculum into concise interview delivery.

Each answer is designed for roughly 60–90 seconds, followed by five anchor phrases for deeper follow-ups. Do not memorize the text word-for-word. Memorize the **structure, invariant, and evidence**.

## Delivery rule

```text
Assumptions
  -> invariant
  -> request/data/control path
  -> failure and security
  -> proof
```

When the interviewer interrupts, answer the interruption directly and return to the invariant.

---

# Round 1 — Infrastructure, EKS, and Infrastructure as Code

## 1. Multi-AZ EKS for millions of concurrent users

### Spoken answer

> I would first translate “millions of concurrent users” into peak RPS, active connections, payload size, read/write ratio, p99 latency, and regional distribution, because concurrency alone is not a capacity number. Assuming one Region and three AZs, I would use Route 53, CloudFront where responses are cacheable, WAF and Shield, then ALB or NLB into independent EKS cells.
>
> EKS manages the control plane, but I own the data plane: private worker subnets, stable On-Demand system nodes, Karpenter-managed application capacity, topology spread, PDBs, readiness-based traffic admission, and warm headroom for bursts and AZ loss. HPA scales from RPS, concurrency, or queue age; Karpenter supplies nodes for pending pods.
>
> I keep request services stateless, use ElastiCache for hot data, DynamoDB or Aurora according to consistency and access patterns, and queues or streams to remove slow work from the synchronous path. Every dependency has deadlines, bounded retries, concurrency limits, and load shedding.
>
> I would not claim the design handles millions until quotas, subnet IPs, dependency capacity, full-path load tests, and a one-AZ evacuation prove the capacity envelope.

### Follow-up anchors

- `concurrency != RPS`
- `cell boundary, not one giant cluster`
- `pod IPs and quotas`
- `demand-to-ready-target timeline`
- `AZ-loss load test`

---

## 2. GitOps with Terraform and Argo CD or Flux

### Spoken answer

> I define one authoritative reconciler per resource. Terraform owns AWS infrastructure and the minimum bootstrap layer: accounts, VPCs, EKS, IAM, KMS, ECR, and installation of the GitOps controller. Argo CD or Flux owns Kubernetes platform add-ons and applications after bootstrap. CI builds and validates; it does not directly patch production resources that Git owns.
>
> For application delivery, CI tests, scans, signs, and pushes one immutable image digest to ECR, then proposes a pull request that updates desired state. The same digest is promoted through environments. Argo Rollouts or Flagger shifts traffic progressively and evaluates service-level indicators before promotion or automatic abort.
>
> Secrets remain in Secrets Manager and reach workloads through External Secrets or the CSI driver using Pod Identity or IRSA. Infrastructure changes use isolated Terraform state, one writer, a reviewed plan, policy checks, and production approval.
>
> The key safety rule is no dual ownership: Terraform, CI, and GitOps never compete over the same resource. Emergency changes use break-glass access and are immediately reconciled back to Git.

### Follow-up anchors

- `one resource, one reconciler`
- `bootstrap ownership transfer`
- `build once, promote digest`
- `CRD/controller ordering`
- `break-glass reconciled to Git`

---

## 3. Terraform state across AWS accounts and Regions

### Spoken answer

> I treat Terraform state as a production control-plane database. I place it in a dedicated tooling or infrastructure account in S3 with versioning, encryption, public-access blocking, TLS-only policy, audit logging, and exact-prefix permissions. Each state has one protected CI writer using short-lived OIDC credentials.
>
> I partition state by account, Region, environment, system, and lifecycle so a network change does not lock or endanger every application. Target provider roles live in workload accounts, while backend access remains separately governed. For current Terraform versions I evaluate S3 native lockfiles; existing estates may still use DynamoDB locking during a controlled migration.
>
> S3 cross-Region replication is recovery material, not active-active state. During an incident I freeze writers, prove the exact backend and identity, preserve the lock and object version, back up state, compare state with actual AWS resources, and remove a stale lock only after proving the original writer is dead.
>
> Recovery ends with one controlled apply, verified state write and lock release, and a fresh plan showing no unintended drift.

### Follow-up anchors

- `state = control-plane database`
- `one writer per state`
- `partition by blast radius`
- `replica is not active-active`
- `restore only after lineage/reality check`

---

## 4. Securing Amazon EKS

### Spoken answer

> I secure EKS in layers. Humans use federated short-lived IAM sessions, EKS access entries, and least-privilege Kubernetes RBAC. The API endpoint is private where the operating model supports it, or the public endpoint is tightly restricted—but network privacy does not replace authorization.
>
> Pods never rely on a broad node role. Each workload gets a least-privilege role through EKS Pod Identity or IRSA, IMDSv2 is required, and pod access to node credentials is restricted and tested. Nodes run in private subnets, security groups allow only required paths, NetworkPolicy controls pod traffic, and Security Groups for Pods are used when an AWS VPC-level boundary is needed.
>
> Secrets remain in Secrets Manager encrypted by KMS and are delivered through External Secrets or the Secrets Store CSI driver with an explicit rotation and reload plan. I enforce Pod Security, non-root containers, read-only filesystems, dropped capabilities, approved registries, immutable digests, scanning, signatures, and admission policy.
>
> CloudTrail, EKS audit logs, GuardDuty, Config, runtime detection, and tested compromise runbooks provide evidence and recovery.

### Follow-up anchors

- `federated human identity`
- `Pod Identity vs IRSA by trust model`
- `no node-role fallback`
- `NetworkPolicy plus SG where needed`
- `secret rotation is a workflow`

---

## 5. Terraform versus CloudFormation and AWS-native services

### Spoken answer

> I choose one authoritative provisioning engine per resource lifecycle. Terraform is my default when the platform spans AWS, Kubernetes, SaaS, or multiple clouds and benefits from one plan/state/module workflow. CloudFormation is strong for AWS-only stacks, StackSets across accounts and Regions, Service Catalog products, and teams that prefer AWS-managed stack state. CDK is an authoring abstraction that synthesizes CloudFormation, so CloudFormation deployment and rollback semantics still apply.
>
> AWS-native services complement either engine: Organizations and Control Tower establish account guardrails, StackSets distribute baselines, Service Catalog provides approved self-service, Systems Manager Automation runs operational procedures, and Config detects compliance.
>
> Regardless of tool, every change uses short-lived identity, validation, policy, a plan or change set, approval, one writer per state or stack, post-deployment checks, and drift detection.
>
> A deliberate hybrid is valid, but Terraform, CloudFormation, Config remediation, and scripts must never silently own the same resource.

### Follow-up anchors

- `ownership, not ideology`
- `CDK still CloudFormation runtime`
- `Config can create controller conflict`
- `StackSets for fleet baseline`
- `migration is authority transfer`

---

## 6. Capacity planning with ASGs, Karpenter, Cluster Autoscaler, and Spot

### Spoken answer

> I separate pod demand from node supply. HPA or KEDA scales replicas from the signal closest to demand—RPS, active requests, queue age, or consumer lag. The scheduler places those pods, and Karpenter or Cluster Autoscaler supplies nodes for pods that cannot schedule.
>
> I generally use Karpenter for heterogeneous, bursty EKS workloads because it evaluates pending pod constraints and selects from broad instance options. Cluster Autoscaler remains a good fit for stable predefined managed node-group or ASG fleets. I do not give both controllers overlapping ownership of the same capacity.
>
> Critical system components and minimum SLO capacity remain on On-Demand. Diversified Spot capacity is used for interruption-tolerant replicas and workers with graceful termination, idempotency, checkpointing, topology spread, and enough fallback.
>
> Capacity planning includes requests, limits, daemon overhead, pod density, subnet IPs, AZ-failure headroom, node launch and image-pull time, quotas, and downstream capacity. I measure from demand increase to healthy load-balancer target and recovered user SLI—not merely node launch.

### Follow-up anchors

- `pod loop vs node loop`
- `one owner per elastic pool`
- `On-Demand minimum, Spot excess`
- `requests define scheduling/HPA semantics`
- `capacity realization SLI`

---

# Round 2 — Incident Response, Troubleshooting, and Reliability

## 7. Customers cannot access an AWS-hosted application

### Spoken answer

> I first establish impact, start an incident timeline, freeze unrelated changes, and capture one failing request from the user's network with UTC timestamp, resolver, DNS answers, TLS result, HTTP status, and request or trace ID.
>
> Then I follow the exact path: recursive resolver and Route 53 records, health checks and routing policy, CloudFront or WAF if present, certificate and TLS negotiation, ALB or NLB listener and target group, VPC routes, security groups and NACLs, EKS ingress or Service and EndpointSlices, pod readiness, application logs, and dependencies such as database or cache.
>
> At each boundary I ask four questions: did the request arrive, did policy allow it, did the component process it, and did the response return? I use Route 53 query logs, load-balancer access logs, WAF logs, VPC Flow Logs, Reachability Analyzer, Kubernetes events, and traces to prove the boundary.
>
> I choose the smallest reversible mitigation—remove a bad target, pause a rollout, relax a false-positive WAF rule, or shift a bounded cohort—and verify recovery from an external synthetic and user-facing SLI.

### Follow-up anchors

- `one real failing request`
- `outside-in path`
- `Reachability Analyzer models config`
- `health check != business transaction`
- `external recovery proof`

---

## 8A. Kubernetes API-server latency doubles

### Spoken answer

> First I clarify that this is the Kubernetes API, not the application API. Because EKS manages the control plane, I focus on client behavior and cluster extensions that can overload or delay it.
>
> I inspect API and audit logs, request latency and throttling, client-side 429s and timeouts, admission-webhook duration, scheduler and controller behavior, CRD object size, and LIST/WATCH volume. I identify the user agent, resource, verb, namespace, and client generating the pressure.
>
> Common causes are a controller relisting large object sets, an operator with aggressive QPS and burst, a slow or unavailable admission webhook, large secrets or CRDs, or a network path problem from management clients. I stop or rate-limit the abusive client, make a failing webhook safe, or roll back the extension rather than attempting to tune a managed API server blindly.
>
> Recovery is proven through client operation latency, reduced throttling, healthy controller reconciliation, and stable application operation.

### Follow-up anchors

- `clarify control-plane API`
- `user agent + verb + resource`
- `LIST/WATCH and admission`
- `client QPS/burst`
- `managed control plane, customer extensions`

---

## 8B. Application API latency doubles while nodes remain healthy

### Spoken answer

> I define the affected endpoint, percentile, version, AZ, tenant, traffic rate, and start time. Healthy nodes eliminate very little: a pod can be CPU-throttled, a thread pool can queue, retries can multiply, or a dependency can be saturated.
>
> In CloudWatch and Grafana I correlate ALB target response time, request rate, errors, pod CPU throttling and memory, HPA desired versus available replicas, pending pods, CoreDNS, and database or cache saturation. In Prometheus I use request histograms by route, version, pod, and AZ.
>
> Then I compare slow and healthy X-Ray or OpenTelemetry traces for the same transaction and identify where the extra time appears: ingress, local compute, connection-pool wait, DNS, database, cache, or downstream retry. I correlate trace IDs with structured logs and overlay deployments, feature flags, autoscaling, CloudTrail, and AWS Health events.
>
> I mitigate from evidence and prove p50, p95, p99, success rate, retry volume, and dependency saturation recover for every affected cohort.

### Follow-up anchors

- `nodes healthy proves little`
- `metrics locate; traces allocate`
- `pool wait vs query time`
- `frontend scaling can amplify dependency`
- `tail and cohort recovery`

---

## 9. Deployment succeeds, but a subset of users fails

### Spoken answer

> I turn “some users” into measurable cohorts. I compare failing and successful requests across geography, resolver, IPv4 versus IPv6, client version, tenant, authentication provider, feature flag, session age, AZ, pod version, node group, and data shard.
>
> I capture one matched failing and healthy transaction with timestamps, DNS answers, target, status, trace ID, application digest, configuration revision, and dependency path. Then I build a cohort matrix from load-balancer and WAF logs, application logs, traces, Kubernetes placement, and data metrics.
>
> If failure correlates with geography or resolver, I inspect DNS and edge routing. If it correlates with AZ or subnet, I inspect target health, routes, security policy, Flow Logs, and dependency paths. If it correlates with version, feature, tenant, or shard, I focus on code, configuration, authorization, schema compatibility, and data.
>
> I separate confounded variables—for example, all new pods may happen to be in one AZ—then use a targeted rollback, feature disable, or traffic removal. Recovery is verified for the original minority cohort, not only the aggregate.

### Follow-up anchors

- `cohort matrix`
- `paired failing/healthy request`
- `correlation can be confounded`
- `green Deployment != business success`
- `verify minority recovery`

---

## 10. CloudWatch alarms fire, dashboards do not reveal root cause

### Spoken answer

> I first verify the alarm: exact metric, dimensions, statistic, period, missing-data behavior, and transition time. Then I move from aggregate symptoms to high-cardinality evidence on one UTC timeline.
>
> I use Logs Insights to group errors by route, version, AZ, pod, tenant tier, and error class; Contributor Insights to find top contributors; Application Signals and X-Ray or OpenTelemetry traces to locate the failing service edge; and trace IDs to retrieve local logs.
>
> I correlate that window with CloudTrail changes, GitOps and deployment history, Config timelines, AWS Health, WAF and load-balancer logs, Resolver logs, VPC Flow Logs, and Synthetics artifacts such as HAR files and screenshots. If metrics and traces locate the service but not the local mechanism, I preserve thread dumps, profiles, connection pools, and node evidence.
>
> Every hypothesis states expected evidence, disproving evidence, and the smallest reversible test. Afterward I add the missing query, correlation field, synthetic transaction, or runbook—not automatically another dashboard.

### Follow-up anchors

- `validate alarm first`
- `one UTC timeline`
- `change evidence + runtime evidence`
- `hypothesis must be falsifiable`
- `dashboard is not the only artifact`

---

## 11. Terraform apply fails midway

### Spoken answer

> I treat a partial apply as a control-plane integrity incident. I freeze every writer for the exact state, preserve the failed job, lock metadata, plan, state object version, and CloudTrail events, and prove the account, Region, backend key, workspace, Terraform version, and deployment identity.
>
> I back up current state, determine which provider operations completed or remain asynchronous, and build an inventory comparing configuration, Terraform state, and actual AWS resources. A refresh-only plan helps expose divergence, but I review it before changing state.
>
> For each resource I choose an explicit action: keep it, import a successfully created object, complete the operation, recreate a genuinely missing object, or deliberately remove an orphan after dependency and data review. I do not blindly rerun apply, use `-lock=false`, delete resources manually, or restore an older state object.
>
> One reviewed apply resumes convergence, followed by an empty or understood plan, verified state write, lock release, and prevention such as pipeline serialization, quota checks, provider pinning, and state partitioning.

### Follow-up anchors

- `configuration/state/reality`
- `freeze writers and preserve evidence`
- `provider operation may outlive timeout`
- `explicit disposition per resource`
- `one controlled convergence`

---

## 12. Pods restart continuously while probes remain healthy

### Spoken answer

> I first determine whether this is a container restart in the same pod UID, a pod replacement, a node eviction, or a sidecar-only restart. Those have different causes and evidence.
>
> For the affected container I inspect `lastState`, reason, exit code, signal, start and finish times, events, and immediately capture `kubectl logs --previous` before another restart overwrites it. Probes are periodic samples; a process can exit between probes, complete with code zero, be OOM-killed, receive SIGTERM from a rollout or node drain, or lose a sidecar.
>
> I correlate the timestamp with cgroup memory and CPU throttling, node pressure, kubelet and runtime logs, kernel OOM, deployment history, ConfigMap and Secret changes, Karpenter consolidation, managed node-group updates, and Spot interruption. I also inspect PID 1 and wrapper scripts for background-process or signal-propagation errors.
>
> Mitigation follows the cause, and I prove new pods survive beyond the historical failure interval with stable business transactions.

### Follow-up anchors

- `container vs pod vs node`
- `lastState + --previous first`
- `exit 0 can still restart`
- `OOM vs forced kill evidence`
- `survive historical interval`

---

## 13. Postmortem after a large AWS outage

### Spoken answer

> I begin after service is stable and evidence is preserved. A neutral facilitator builds one UTC timeline from customer reports, SLOs, alarms, deployments, CloudTrail, AWS Health, logs, traces, Kubernetes events, decisions, and communications, clearly separating facts from hypotheses.
>
> I quantify customer and business impact: failed transactions, affected cohorts and Regions, duration, latency, error-budget consumption, data loss or uncertainty, backlog, contractual impact, and recovery debt. I distinguish the trigger from contributing technical conditions, safeguard failures, response gaps, and organizational conditions.
>
> Corrective actions cover prevention, blast-radius reduction, detection, diagnosis, mitigation, and recovery. Each important action has an owner, due date, risk, and measurable acceptance test such as a canary, dependency-failure load test, backup restore, or regional game day.
>
> Blameless means we improve the system rather than attributing failure to intent; it does not mean no ownership. The postmortem closes only when critical risks are verified and temporary mitigations are owned or removed.

### Follow-up anchors

- `customer impact first`
- `trigger != entire cause`
- `blameless, not ownerless`
- `actions need acceptance tests`
- `game day proves correction`

---

# Round 3 — System Design, Scale, and Leadership

## 14. Highly available mobile backend

### Spoken answer

> I separate four workloads with different trust and consistency needs: authentication, ordinary mobile APIs, asynchronous notifications, and remote commands. Route 53, CloudFront and WAF front regional API Gateway or ALB endpoints. Cognito provides authentication, federation, MFA, and token issuance, with a tested multi-Region continuity design where required.
>
> Stateless services run on EKS, Lambda, or ECS according to runtime needs. DynamoDB stores preferences, device registration, idempotency records, and command state; Global Tables are used only where conflict semantics fit. EventBridge, SNS, SQS, and workers decouple notifications and provider delivery.
>
> Remote commands use a separate state machine. The cloud authenticates the user, verifies ownership and policy, creates a unique short-lived command with an idempotency key and sequence or fencing token, and transports it through IoT Core. The device independently validates expiry, replay, identity, and local safety, then returns an authenticated acknowledgement and result.
>
> The API reports accepted, delivered, executed, failed, or expired. It never reports physical success merely because the message broker accepted the publish.

### Follow-up anchors

- `separate command trust model`
- `step-up auth for sensitive action`
- `device-local authority`
- `exactly-once business effect`
- `honest offline state`

---

## 15. Global secure software updates to millions of devices

### Spoken answer

> I separate release authorization from artifact delivery. CI produces one immutable artifact, SBOM, and provenance, tests it across the hardware matrix, and signs a manifest that binds the digest, version, hardware compatibility, dependencies, expiry, and anti-rollback information. Artifacts live in versioned encrypted S3 and may be globally cached through CloudFront, but the device trusts the signature and digest—not the transport path.
>
> AWS IoT Device Management Jobs and the Software Package Catalog manage target inventory, rollout state, rate, timeout, and abort behavior. Rollout proceeds through representative internal and production cohorts with explicit success, rollback, crash, heartbeat, and business-SLI gates.
>
> Devices download resumably, verify the signed manifest and artifact, check power, storage, bootloader, and model, then install into an inactive A/B partition or comparable transactional mechanism. After reboot, local health validation either commits the version or rolls back without waiting for the cloud.
>
> The update agent and recovery path remain independent of the application being replaced, and game days include corrupt artifacts, power loss, lost connectivity, disappeared devices, bad canaries, and signing-key compromise.

### Follow-up anchors

- `sign manifest and artifact`
- `representative canary`
- `A/B local rollback`
- `missing heartbeat is failure evidence`
- `update path independent of app`

---

## 16. Multi-Region DR with minimal downtime

### Spoken answer

> I first define RTO and RPO by capability because active-active, hot standby, and warm standby have different cost and consistency implications. I build complete regional cells with local compute, configuration, secrets, images, queues, observability, quotas, and no synchronous dependency on the other Region.
>
> Route 53, Global Accelerator, or CloudFront manages traffic according to protocol. For controlled failover I use ARC routing controls or Region switch with safety rules. Readiness checks identify configuration and capacity drift before the incident, but they are not the only failover health signal.
>
> Data recovery is service-specific: Global Tables where conflict semantics fit; Aurora Global Database with explicit promotion and possible nonzero unplanned-failover RPO; S3/ECR/Secrets replication; and replay or dual-ingestion patterns for regional queues and streams.
>
> Automation confirms user impact, destination readiness, and replication state, fences the old writer, promotes data authority, shifts a small traffic cohort, and then expands. Recovery includes uncertain transaction reconciliation and restored redundancy. Failback is a planned migration, not an immediate reverse switch.

### Follow-up anchors

- `RTO/RPO by capability`
- `regional independence`
- `fence before promote`
- `routing does not solve data`
- `failback is separate migration`

---

## 17. Actionable observability platform

### Spoken answer

> I standardize instrumentation on OpenTelemetry with consistent service, version, environment, Region, cell, and route attributes. Agent or DaemonSet collectors enrich local telemetry; regional gateway collectors batch, redact, sample, and fan out through independent pipelines so a trace storm cannot block critical metrics.
>
> CloudWatch provides AWS-native metrics, logs, alarms, Synthetics, Application Signals, changes, and investigations. New tracing instrumentation uses OpenTelemetry and exports to X-Ray or CloudWatch transaction search. Kubernetes and application metrics go to Amazon Managed Service for Prometheus, and Managed Grafana provides cross-source investigation.
>
> Paging is SLO- and action-driven: multi-window burn-rate alerts, failed synthetic business transactions, queue age, and imminent saturation. Component symptoms enrich incidents or create tickets unless immediate human action is required. Alertmanager or Grafana policies group, deduplicate, inhibit, and route alerts by service and owner.
>
> Cardinality, sampling, retention, and spend have budgets. Every page has an owner, runbook, impact statement, and quality review, and alerts that repeatedly cause no action are removed or redesigned.

### Follow-up anchors

- `OTel as evidence standard`
- `separate critical signal pipelines`
- `SLO page; symptoms enrich`
- `cardinality and cost budgets`
- `observability needs failure mode`

---

## 18. Millions of real-time events per second

### Spoken answer

> I start with both events and bytes per second, event size distribution, ordering key, retention, replay, latency, consumers, and duplicate semantics. Kinesis is the partitioned ordered ingestion log. Producers batch and aggregate, use a well-distributed business partition key, and handle partial batch failures. Enhanced fan-out gives critical consumers independent low-latency read throughput where justified.
>
> Lambda handles stateless transforms and event handlers. EKS handles sustained, long-running, specialized, or stateful consumers and scales from iterator age and processing rate. SQS isolates independent work, retries, and DLQs. SNS provides push fan-out, while EventBridge receives meaningful business events and integrations rather than the raw telemetry firehose by default.
>
> Every event has a stable ID and schema version. Consumers checkpoint only after durable side effects and create exactly-once business effect through idempotency, conditional writes, inbox/outbox patterns, and replay-safe external calls.
>
> I monitor partition skew, write throttles, iterator and queue age, consumer rate, retries, concurrency, and end-to-end freshness, and test hot keys, poison events, downstream throttling, rebalancing, replay, and Region failure.

### Follow-up anchors

- `events/s plus bytes/s`
- `partition key follows ordering invariant`
- `Kinesis log, SQS work isolation`
- `exactly-once business effect`
- `backpressure before scaling`

---

# Rapid adversarial drill

Answer each in one or two sentences.

## Infrastructure

**Why not one giant EKS cluster?**

> Because control-plane clients, shared controllers, upgrades, policies, and add-ons create one operational blast radius. I choose cluster and cell boundaries from SLO, tenancy, ownership, and independent release requirements.

**Why not 100% Spot?**

> Spot availability and interruption are not under my control. Critical controllers and minimum service capacity remain on On-Demand; Spot serves diversified interruption-tolerant excess load.

**Why not let Terraform and Argo both manage Helm?**

> Two reconcilers can continuously undo each other and make rollback authority ambiguous. Ownership must be transferred explicitly.

**Why not force-unlock an urgent Terraform state?**

> Urgency does not prove the original writer is dead. A second writer can corrupt state silently; I first freeze writers, preserve state, and verify provider activity.

## Security

**Private EKS endpoint means secure?**

> It reduces network exposure; it does not replace identity, authorization, workload security, secret controls, or audit.

**Pod Identity or IRSA?**

> I prefer Pod Identity for many new same-account workloads and simpler associations, while IRSA remains useful for existing OIDC-based platforms and direct cross-account trust patterns. Both require least privilege and node-credential isolation.

## Incidents

**All targets are healthy; why are users failing?**

> The health check may not exercise authentication, the failing route, dependency state, payload, or user cohort. I trace the exact business transaction.

**Why not restart everything?**

> It destroys evidence and can amplify connection, cache, and retry storms. I first isolate the failure boundary and choose the smallest reversible mitigation.

**One AZ correlates with failures; AWS fault?**

> Not necessarily. Version, node group, sidecar, or data path may be confounded with the AZ. I separate variables before concluding.

## Distributed systems

**Does MQTT publish success mean command success?**

> No. It means broker acceptance. Device execution requires an authenticated acknowledgement and result after local policy and safety validation.

**Can Global Tables solve active-active writes?**

> They replicate writes, but the application still owns concurrent-write and business-conflict semantics. Some data remains home-region or fenced.

**Exactly once?**

> I assume at-least-once transport and implement exactly-once business effect with stable IDs, idempotent operations, conditional writes, and durable result lookup.

## Reliability

**Why not fail over from one alarm?**

> A noisy alarm can turn a local fault into a regional outage. I require independent impact signals, destination readiness, and source fencing before shifting writes.

**Why not deploy a critical patch globally immediately?**

> Urgency can shorten observation windows but does not remove canary and abort requirements. A broken patch can create a larger, less recoverable risk.

## Observability

**Why not page on every anomaly?**

> A page is for urgent human action. Anomalies without a decision become context or tickets; otherwise responders learn to ignore the pager.

**CloudWatch or Prometheus?**

> CloudWatch is authoritative for many AWS-native signals and operational evidence; Prometheus provides Kubernetes/application metric semantics and PromQL. I use both with one pager owner per SLO.

---

# Final rehearsal checklist

Before declaring the AWS track interview-ready, demonstrate for each question:

- a 90-second spoken response without reading;
- a five-minute whiteboard;
- five adversarial follow-ups;
- one explicit unsafe alternative;
- one truthful production story or clearly labeled hypothetical example;
- one validation or game-day plan;
- one statement of uncertainty where a quota or service behavior must be verified.

The goal is not perfect recitation. The goal is repeatable judgment under interruption.