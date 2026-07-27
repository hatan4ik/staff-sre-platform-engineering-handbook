# Question 1 — Highly Available Multi-AZ EKS Platform for Millions of Concurrent Users

## Interview prompt

Design a highly available, multi-AZ Amazon EKS platform capable of serving millions of concurrent users. Which AWS services would you use, and why?

## What the interviewer is testing

A strong answer does not claim that “EKS scales to millions” by itself. It converts an ambiguous concurrency target into workload demand, identifies every bottleneck in the request path, limits failure domains, and explains how the design is proven under load.

The real test is whether you can reason across:

- edge and ingress capacity
- Kubernetes control-plane and data-plane limits
- pod and node scaling
- IP-address consumption
- stateful dependency capacity
- retries and overload
- zonal failure
- deployment blast radius
- quotas and operational ownership

---

## 90-second Staff/Principal answer

> I would first translate “millions of concurrent users” into peak requests per second, connection duration, payload size, read/write ratio, latency SLO, and regional distribution. Concurrency alone is not a capacity number.
>
> For a single-region, multi-AZ design, I would use Route 53 and optionally Global Accelerator for entry, CloudFront for cacheable content, AWS WAF and Shield at the edge, and ALB or NLB through the AWS Load Balancer Controller. I would run EKS across at least three Availability Zones with private worker subnets, separate small On-Demand system node groups, and Karpenter-managed application capacity diversified across instance families and zones.
>
> Workloads would use topology-spread constraints, pod anti-affinity, PodDisruptionBudgets, readiness-based traffic admission, graceful termination, and HPA based on business demand or queue depth rather than CPU alone. Karpenter scales nodes for unschedulable pods; overprovisioning or warm capacity protects latency during bursts.
>
> I would keep request handling stateless. ElastiCache absorbs hot reads and session state, DynamoDB or Aurora is selected from access and consistency requirements, and SQS, Kinesis, or MSK decouples slow work. Every dependency has explicit timeouts, bounded retries with jitter, concurrency limits, and load shedding.
>
> I would avoid one giant blast radius. At very large scale I would use multiple EKS clusters or cells, with independent ingress, capacity, and deployment waves. I would prove the design with quota reviews, full-path load tests, zonal evacuation tests, node and cluster upgrade tests, and SLOs for availability, latency, saturation, and successful capacity realization.

---

## 1. Clarify the requirement before drawing boxes

Ask for or state assumptions:

| Dimension | Example assumption |
|---|---|
| Concurrent users | 2,000,000 connected users |
| Active request rate | 10% issue a request each second = 200,000 RPS |
| Peak factor | 2.0 during events = 400,000 RPS |
| Read/write ratio | 90/10 |
| Payload | 4 KB request, 20 KB response average |
| Latency SLO | p99 under 300 ms |
| Availability | 99.95% regional service SLO |
| Recovery | tolerate loss of one AZ without violating the error budget |
| Geography | one AWS Region for this question |

Do not present these as facts. Say they are sizing assumptions to be validated.

### Little's Law sanity check

For a request/response API:

```text
concurrency ≈ throughput × average response time
```

At 400,000 RPS and 200 ms average latency:

```text
in-flight requests ≈ 400,000 × 0.2 = 80,000
```

Two million logged-in or socket-connected users therefore does not necessarily mean two million simultaneous application requests.

For WebSockets or long polling, connection count becomes a separate dimension affecting load balancers, file descriptors, NAT, pod memory, connection draining, and client reconnection storms.

---

## 2. Reference architecture

```text
Users
  |
  +--> Route 53 latency/weighted records
          |
          +--> CloudFront -- WAF -- Shield
          |       |
          |       +--> S3 static content / cached API responses
          |
          +--> Global Accelerator (optional for static anycast entry)
                    |
              ALB / NLB per cell
                    |
        +-----------+------------+
        |           |            |
      AZ-a        AZ-b         AZ-c
        |           |            |
   EKS nodes    EKS nodes     EKS nodes
        \           |           /
         \---- stateless services ----/
                   |
       +-----------+----------------------+
       |           |          |           |
  ElastiCache   DynamoDB    Aurora      SQS/Kinesis
       |                                  |
       +---------- async workers ----------+

Shared controls:
ECR, KMS, Secrets Manager, CloudWatch, AMP, AMG, X-Ray,
OpenTelemetry, CloudTrail, Config, GuardDuty, Security Hub
```

At the highest scale, repeat the stack as independent cells:

```text
Regional traffic director
      |
      +--> cell-a: ALB + EKS + cache partition + quotas
      +--> cell-b: ALB + EKS + cache partition + quotas
      +--> cell-c: ALB + EKS + cache partition + quotas
```

A cell is a deliberately bounded failure domain, not merely another namespace.

---

## 3. Edge and traffic entry

### Route 53

Use Route 53 for DNS ownership, health-aware routing, weighted migrations, and controlled failover. Do not rely on DNS as the only fast failover mechanism because resolver and client caches can delay movement.

### CloudFront

Use CloudFront when content or API responses can be cached at the edge. Every request served at the edge is a request that does not consume ALB, pod, cache, and database capacity.

Define cache keys carefully to avoid:

- caching user-specific responses across identities
- cache fragmentation from irrelevant headers or query strings
- origin stampedes on synchronized expiry

Use stale-while-revalidate or controlled origin shielding where applicable.

### AWS WAF and Shield

WAF provides managed rules, rate-based rules, bot controls where required, and application-layer filtering. Shield Standard is inherent for supported resources; Shield Advanced is a risk and business decision for higher protection and response support.

### Global Accelerator

Consider Global Accelerator when static anycast IPs, rapid endpoint health-based traffic shifting, or TCP/UDP path optimization are useful. It does not replace application-level multi-region data design.

### ALB versus NLB

Use **ALB** for HTTP/HTTPS features such as host/path routing, TLS termination, WAF integration, and target-group health.

Use **NLB** for very high-throughput TCP/UDP/TLS workloads, static IP requirements, source-IP preservation needs, or protocols not suited to ALB.

Do not create one load balancer per small service at scale without considering quotas, cost, target registrations, and configuration churn.

---

## 4. EKS cluster and VPC topology

### EKS control plane

EKS provides a managed Kubernetes control plane designed across three Availability Zones in a Region. That removes control-plane node management, but it does not make workloads automatically highly available.

The customer still owns:

- node and pod placement
- application replication
- dependency availability
- disruption budgets
- upgrade safety
- networking and IP capacity
- autoscaling behavior
- observability and incident response

### VPC layout

Use at least three AZs.

```text
VPC
├── public subnets
│   ├── internet-facing load balancers
│   └── NAT gateways when required
├── private application subnets
│   ├── EKS nodes
│   └── pod IPs
└── isolated data subnets
    ├── Aurora/RDS
    └── ElastiCache
```

Prefer VPC endpoints for AWS services such as ECR API, ECR DKR, S3, STS, CloudWatch Logs, and Secrets Manager where they reduce NAT dependency and improve private connectivity.

### IP-address planning

At scale, pod IP exhaustion can arrive before CPU exhaustion.

Plan for:

- subnet CIDR size per AZ
- VPC CNI prefix delegation where appropriate
- ENI and IP limits by instance type
- surge capacity during rollouts
- failed-node replacement overlap
- HPA and Karpenter expansion
- load-balancer target mode

Monitor available IPs continuously. A cluster with free EC2 quota but no pod IPs cannot scale.

### One cluster or many?

One cluster is operationally simpler, but a single giant cluster increases:

- API-server and admission-webhook load
- controller and CRD blast radius
- upgrade risk
- network-policy complexity
- noisy-neighbor exposure
- configuration propagation time
- dependency on shared cluster add-ons

Use multiple clusters or cells when scale, tenant isolation, compliance, release independence, or blast-radius requirements justify the operational cost.

A strong answer says that the cluster count is an SLO and blast-radius decision, not a fashion choice.

---

## 5. Node architecture

Separate critical platform capacity from elastic application capacity.

### System node group

Use a small, fixed or conservatively autoscaled On-Demand managed node group for:

- CoreDNS
- VPC CNI components
- metrics and telemetry agents
- ingress controllers when applicable
- Karpenter controller
- policy and security controllers
- GitOps controllers

Protect these nodes with labels, taints, priority classes, and resource reservations.

### Application capacity

Use Karpenter NodePools for diverse application capacity. Constrain:

- allowed AZs
- architectures
- capacity type: On-Demand or Spot
- instance categories and generations
- minimum resource sizes
- total CPU or memory limits
- taints and workload isolation
- pinned, tested AMIs in production

Avoid requiring one exact instance type. Flexibility improves Spot availability and reduces capacity risk.

### Stateful and specialized pools

Use dedicated NodePools or managed node groups for workloads with:

- local NVMe requirements
- GPUs
- strict latency isolation
- compliance boundaries
- daemon overhead that changes usable capacity
- non-interruptible operations

---

## 6. Workload high availability

### Replica placement

Use topology-spread constraints across zones and hosts:

```yaml
spec:
  replicas: 12
  template:
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: api
        - maxSkew: 1
          topologyKey: kubernetes.io/hostname
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: api
```

`DoNotSchedule` provides stronger placement but can block a rollout when capacity is unavailable. The choice must match the service's availability and rollout strategy.

### PodDisruptionBudgets

PDBs protect against voluntary disruptions, not every failure.

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api
spec:
  minAvailable: 80%
  selector:
    matchLabels:
      app: api
```

A PDB that is too strict can block node upgrades or consolidation. Budget for both application availability and platform maintainability.

### Probes and traffic admission

- `startupProbe` protects slow initialization.
- `readinessProbe` controls traffic admission.
- `livenessProbe` detects unrecoverable local deadlock, not downstream failure.
- graceful shutdown removes the pod from traffic before termination.

Do not make liveness depend on a remote database. A database incident should not cause every pod to restart and amplify the outage.

### Priority and preemption

Use priority classes for critical system and tier-0 workloads, but avoid uncontrolled preemption cascades. Capacity planning is safer than relying on preemption as routine scaling.

---

## 7. Pod and node autoscaling

### HPA

Scale pods using the signal closest to demand:

- requests per second
- concurrent requests
- queue depth per consumer
- active sessions
- latency or saturation with safeguards
- CPU for CPU-bound workloads

CPU utilization is calculated relative to resource requests. Incorrect requests corrupt both scheduling and HPA behavior.

### KEDA

KEDA is useful for event-driven scaling from SQS, Kinesis, Kafka, or Prometheus signals. Scale-to-zero is appropriate only where cold-start latency and recovery behavior meet the SLO.

### Karpenter

Karpenter reacts to unschedulable pods and provisions matching nodes. It does not eliminate the time to launch an EC2 instance, bootstrap it, join the cluster, pull images, and pass readiness.

For sudden traffic:

- maintain minimum replicas
- use predictive or scheduled scaling for known events
- keep small overprovisioning pods or warm node capacity
- preload large images where justified
- reduce image size and startup time
- protect registry and DNS capacity

### Capacity realization SLI

Measure the complete loop:

```text
demand increase
  -> HPA desired replicas
  -> pending pods
  -> node requested
  -> EC2 launched
  -> node Ready
  -> image available
  -> pod Ready
  -> target healthy
  -> user latency recovers
```

Node creation alone is not successful autoscaling.

---

## 8. Data and asynchronous architecture

### Stateless request tier

Keep application pods stateless wherever possible. Do not bind user sessions to one pod unless there is a deliberate and recoverable affinity design.

### ElastiCache

Use Redis or Memcached for hot data, rate-limit counters, short-lived state, and cacheable query results. Design for:

- node or shard failure
- hot keys
- cache stampedes
- TTL jitter
- bounded client connection pools
- behavior when cache is unavailable

A cache is not automatically a source of truth.

### DynamoDB

DynamoDB fits key-value and document access with known partition keys, high scale, managed replication options, conditional writes, and predictable access patterns.

Protect against:

- hot partitions
- unbounded scans
- poorly distributed keys
- retry amplification
- global-table conflict assumptions

### Aurora

Aurora fits relational transactions and SQL access. Scale reads with readers, but understand writer capacity, connection limits, failover behavior, lock contention, and query plans.

Use RDS Proxy where it meaningfully protects database connections from bursty compute fleets. It does not fix slow queries or transaction contention.

### SQS, Kinesis, or MSK

Move slow or non-interactive work off the synchronous request path.

- **SQS:** independent work items, buffering, retries, visibility timeouts, DLQs.
- **Kinesis:** ordered partitioned streams and replay within retention.
- **MSK:** Kafka ecosystem, partitioned logs, consumer groups, operational trade-offs.

Every consumer must be idempotent or have a deduplication strategy.

---

## 9. Failure containment

### Zonal failure

Before failure, do not run each AZ at 100% of its theoretical capacity. To survive one of three AZs, the remaining two AZs must absorb the evacuated load plus headroom.

A simple N+1 target might reserve enough regional capacity such that:

```text
normal per-AZ utilization <= roughly 60–65%
```

The exact number depends on scaling speed, traffic distribution, data capacity, and SLO.

Test:

- node loss in one AZ
- load balancer target redistribution
- NAT gateway or endpoint loss
- database failover
- cache shard failure
- Karpenter capacity in surviving AZs
- subnet IP availability after evacuation

### Retry storms

Use:

- deadlines and timeouts
- exponential backoff with jitter
- bounded retry attempts
- retry budgets
- circuit breakers
- concurrency limits
- load shedding
- idempotency keys for retried writes

A three-layer stack with three retries per layer can multiply one request into many downstream attempts.

### Deployment blast radius

Use canary or progressive delivery by:

- cluster or cell
- AZ where safe
- small traffic percentage
- tenant or cohort
- application version

Rollback criteria should be tied to SLIs, not intuition.

---

## 10. Security baseline

- private EKS API endpoint where operating model permits, or tightly restricted public endpoint
- IAM roles through short-lived federation, not static user keys
- EKS access entries and least-privilege Kubernetes RBAC
- EKS Pod Identity or IRSA per workload
- IMDSv2 and restricted pod access to node instance credentials
- Security Groups for Pods where fine-grained AWS-network enforcement is required
- Kubernetes NetworkPolicy with a supported implementation
- Pod Security Standards, non-root containers, read-only filesystems, and dropped capabilities
- image scanning, signing, admission policy, and immutable digests
- Secrets Manager or Parameter Store with KMS and controlled delivery
- CloudTrail, EKS audit logs, GuardDuty, Config, and Security Hub

Security controls must be load tested. Admission webhooks, policy engines, secret mounts, and telemetry pipelines can become shared bottlenecks.

---

## 11. Observability and SLOs

Collect the four golden signals by service and cell:

- latency
- traffic
- errors
- saturation

Also monitor:

### Edge

- CloudFront hit ratio and origin latency
- WAF blocks and rate limiting
- ALB/NLB target response time, resets, unhealthy targets, and rejected connections

### Kubernetes

- API-server request latency and throttling
- pending pods by reason
- HPA desired versus available replicas
- scheduler latency
- node readiness and pressure
- pod startup and image-pull latency
- CoreDNS latency and errors
- VPC CNI IP allocation and subnet free IPs

### Application

- request rate and concurrency
- p50/p95/p99 latency
- error rate by version, AZ, cell, endpoint, and tenant
- dependency latency
- queue depth and age of oldest message
- cache hit ratio
- database throttling, connections, locks, and failovers

### Example SLOs

- 99.95% successful requests per 30 days
- p99 latency under 300 ms for 99% of five-minute windows
- 99% of scale events add ready capacity within an agreed duration
- zero single-AZ failures exceeding the zonal-failure error-budget allocation

Alert on user impact or imminent SLO violation, not every component symptom.

---

## 12. Quotas and cost

Review and test quotas before launch:

- regional and zonal EC2 capacity
- On-Demand and Spot vCPU quotas
- ENIs and IP addresses
- load balancers, listeners, target groups, and targets
- EBS volume and API quotas
- NAT gateway ports and bandwidth where applicable
- DynamoDB and Kinesis limits
- CloudWatch ingestion and cardinality costs
- ECR pull behavior
- AWS API rate limits during mass scaling

Cost controls include:

- CloudFront caching
- Graviton where validated
- Spot for interruption-tolerant workloads
- Karpenter consolidation with disruption budgets
- Savings Plans for durable baseline load
- VPC endpoints where NAT processing cost is material
- log retention, sampling, and metric-cardinality governance

Do not optimize away the headroom required by the availability SLO.

---

## 13. Validation plan

A design is incomplete until it is tested.

1. Load test the full path, not only the pod service.
2. Increase traffic until each major bottleneck is observed.
3. validate HPA-to-ready-capacity timing.
4. Remove one AZ and sustain peak expected load.
5. terminate nodes during a deployment.
6. throttle or fail cache, database, DNS, and queue dependencies.
7. test Spot interruption and Karpenter consolidation.
8. run cluster and add-on upgrades under production-like load.
9. verify rollback from a bad release.
10. verify alerts correspond to user-visible impact.

Record the tested capacity envelope and the conditions under which it is valid.

---

## Adversarial follow-ups

### “Why not one enormous EKS cluster?”

Because operational simplicity eventually loses to blast radius, API and controller scaling, upgrade risk, tenant isolation, and independent release needs. I would select cluster boundaries from failure-domain and ownership requirements, then verify the cost of operating multiple clusters.

### “Why Karpenter instead of Cluster Autoscaler?”

Karpenter directly evaluates pending pod constraints and can choose from a broad set of instance types without predefining many node groups. Cluster Autoscaler remains a good fit for stable, predefined ASG or managed-node-group fleets. I would not run two controllers with overlapping ownership of the same capacity.

### “Can it really serve millions?”

The architecture alone cannot prove that. I would provide scale assumptions, quota evidence, full-path load-test results, zonal-failure results, and documented saturation points.

### “What happens when an AZ fails during peak traffic?”

Traffic must drain to healthy targets, the remaining AZs must have immediate or rapidly realizable capacity, stateful services must remain available, and subnet/IP and EC2 capacity must exist in surviving zones. I would validate that exact scenario in a game day.

### “What is the first bottleneck?”

I would not guess. Common candidates are database partitions or writer capacity, pod IPs, dependency connection pools, load-balancer targets, DNS, cache hot keys, application locks, or slow capacity realization. The answer comes from load testing and saturation telemetry.

---

## Weak answers to avoid

- “EKS is managed, so it is automatically highly available.”
- “Put the nodes in three AZs and turn on autoscaling.”
- “Use CPU at 70% for everything.”
- “Spot saves 90%, so run the whole platform on Spot.”
- “One cluster is simpler, therefore one cluster is always best.”
- “DynamoDB is infinitely scalable.”
- “We can test after launch.”
- listing AWS services without describing request flow, bottlenecks, failure domains, or validation

---

## Closing statement

> My design goal is not the largest possible cluster. It is a measured, cell-aware platform where traffic, compute, data, and operational control planes scale independently; one AZ, release, controller, or retry policy cannot take down the entire service; and the claimed capacity is backed by load and failure evidence.