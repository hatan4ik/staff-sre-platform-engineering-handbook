# Question 6 — Capacity Planning and Autoscaling with ASGs, Karpenter, Cluster Autoscaler, and Spot

## Interview prompt

Explain your strategy for capacity planning and autoscaling on AWS using Auto Scaling Groups, Karpenter, Cluster Autoscaler, and Spot Instances.

## What the interviewer is testing

A weak answer lists four scaling technologies. A strong answer explains the control loops, their ownership boundaries, the demand signals, capacity-realization delay, zonal resilience, Spot interruption behavior, and the evidence proving that scaling protects the user SLO.

---

## 90-second Staff/Principal answer

> I separate pod demand, node supply, and business forecasting. HPA or KEDA scales workload replicas from the signal closest to demand, such as RPS, concurrency, or queue age. Karpenter or Cluster Autoscaler provides node capacity for pods that cannot schedule. EC2 Auto Scaling Groups remain the underlying capacity primitive for managed node groups and are appropriate for stable, predefined fleets.
>
> For heterogeneous and bursty EKS workloads, I generally prefer Karpenter because it evaluates pending pod constraints directly and can select from many instance types and zones without pre-creating dozens of node groups. I use Cluster Autoscaler where the fleet is intentionally built from known ASGs or managed node groups and operational simplicity is more important than flexible instance selection. I do not give Karpenter and Cluster Autoscaler overlapping ownership of the same capacity.
>
> I maintain On-Demand baseline capacity for system components and SLO-critical replicas, then use diversified Spot capacity for interruption-tolerant workloads. Spot design includes multiple families and sizes, topology spread, PDBs, graceful termination, interruption handling, idempotent workers, checkpointing where required, and enough On-Demand fallback to preserve service.
>
> Capacity planning includes requests and limits, daemon overhead, pod density and IP capacity, AZ-failure headroom, launch and image-pull time, quotas, and downstream bottlenecks. I measure the complete loop from demand increase to ready load-balancer target, load test it, and use scheduled or predictive pre-scaling when reactive scaling cannot meet the latency SLO.

---

## 1. Understand the control loops

```text
Business demand
      |
      v
Application metric
      |
      +--> HPA / KEDA changes desired pod replicas
      |
      v
Kubernetes scheduler
      |
      +--> pods fit existing nodes --> run
      |
      +--> pods remain Pending
                 |
                 +--> Karpenter provisions matching nodes
                 |          or
                 +--> Cluster Autoscaler expands a node group / ASG
                            |
                            v
                     EC2 instance launch
                            |
                     bootstrap and join
                            |
                     image pull and startup
                            |
                     readiness and target health
                            |
                            v
                       user capacity
```

Each loop has different latency and failure modes.

- HPA can change desired replicas quickly.
- the scheduler can place pods only if capacity exists.
- node provisioning takes time.
- a Ready node is not the same as a Ready pod.
- a Ready pod is not the same as a healthy load-balancer target.
- extra frontend capacity does not help if the database or cache is saturated.

---

## 2. Capacity planning inputs

### Demand

- peak RPS or messages per second
- concurrent requests or sessions
- payload size
- read/write ratio
- burst shape and duration
- daily and seasonal patterns
- event-driven spikes
- tenant skew

### Workload profile

- CPU per request
- memory per pod
- startup time
- image size and pull time
- network throughput
- disk or ephemeral-storage needs
- connection-pool size
- daemon and sidecar overhead
- architecture and instance constraints

### Reliability

- number of AZs
- capacity required after one AZ loss
- minimum replicas per service
- rollout surge
- node replacement overlap
- Spot interruption tolerance
- time allowed to realize new capacity

### Platform limits

- EC2 vCPU quotas
- instance availability by AZ
- subnet free IPs
- ENI and pod-density limits
- EBS and ECR API behavior
- Kubernetes API and controller throughput
- target group and load-balancer limits

### Dependencies

- database connections and writer capacity
- cache memory and hot keys
- queue throughput
- third-party API rate limits
- NAT and egress capacity
- DNS performance

The frontend is only as scalable as the tightest downstream dependency.

---

## 3. Basic capacity math

Assume a pod safely sustains 500 RPS at the target p99 latency.

Peak demand is 100,000 RPS.

```text
base replicas = 100,000 / 500 = 200 pods
```

Add failure and rollout headroom. If the service must tolerate one of three AZs failing, the remaining two AZs must carry the peak.

A simplified target might require at least 100 pods of safe capacity in each surviving AZ, plus rollout and uncertainty margin.

Do not apply one universal percentage. Validate with load tests because per-pod capacity changes with:

- request mix
- garbage collection
- dependency latency
- CPU throttling
- cache hit ratio
- connection contention
- sidecars
- noisy neighbors

### Queue-based worker math

If a queue receives 50,000 messages per second and one worker processes 250 messages per second:

```text
steady workers = 50,000 / 250 = 200
```

If backlog must clear within 5 minutes, include backlog drainage:

```text
required processing rate = arrival rate + backlog / target drain time
```

Queue depth alone is less actionable than age of oldest message and processing rate.

---

## 4. Resource requests and limits

The scheduler and autoscalers rely on declared requests.

### Requests

Requests determine scheduling reservation and CPU-utilization semantics for HPA.

Understated requests cause:

- excessive pod packing
- CPU contention
- memory pressure
- misleading HPA utilization
- node instability

Overstated requests cause:

- low bin-packing efficiency
- unnecessary nodes
- higher cost
- unschedulable pods despite real spare capacity

### CPU limits

CPU limits can create throttling and tail latency. Use them deliberately, not automatically.

### Memory limits

Memory is not compressible. A container exceeding its cgroup limit can be OOM-killed.

Set requests from measured working set and limits from safe burst behavior. Monitor:

- CPU throttling
- working set
- OOM kills
- memory pressure
- request-to-usage ratio

### VPA

Vertical Pod Autoscaler can recommend or adjust requests. In-place or restart behavior depends on mode and platform support.

Use VPA carefully with HPA:

- HPA on CPU utilization and VPA changing CPU requests can interact
- HPA on external or custom business metrics is easier to combine
- production request changes should be staged and observed

---

## 5. Horizontal Pod Autoscaler

### Choose the right signal

Good signals are close to user demand or work backlog:

- RPS per pod
- concurrent requests per pod
- queue age or depth per worker
- active sessions
- in-flight jobs
- custom saturation metric

CPU is useful for CPU-bound workloads, but it is not always the cause of latency.

### Example HPA v2

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 12
  maxReplicas: 300
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
        - type: Pods
          value: 20
          periodSeconds: 60
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 600
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60
```

Tune scale-down more conservatively than scale-up to avoid oscillation.

### HPA failure modes

- missing Metrics Server or adapter data
- zero or missing CPU requests
- wrong target object
- max replicas reached
- new pods cannot schedule
- readiness delay excludes or distorts metrics
- application startup slower than the traffic spike
- downstream service already saturated

Always compare:

```text
current metric
-> desired replicas
-> actual replicas
-> available replicas
-> ready targets
-> recovered SLI
```

---

## 6. KEDA for event-driven scaling

KEDA can scale from external sources such as:

- SQS queue depth
- Kafka lag
- Prometheus queries
- cloud event sources

Scale-to-zero is useful for asynchronous workloads, but analyze:

- cold-start delay
- credential and network initialization
- backlog growth during startup
- message visibility timeout
- downstream rate limits
- duplicate delivery

For latency-sensitive request paths, keep a nonzero warm baseline.

---

## 7. Auto Scaling Groups and managed node groups

EC2 Auto Scaling Groups provide:

- minimum, desired, and maximum instance counts
- multi-AZ placement
- health replacement
- launch templates
- lifecycle hooks
- mixed instance policies
- capacity rebalance features

EKS managed node groups use ASGs underneath while AWS manages parts of the node lifecycle and updates.

### Strong fits

- stable baseline system nodes
- regulated or tightly controlled instance fleets
- known specialized hardware
- teams standardized on managed node-group upgrades
- workloads where predefined capacity classes are desirable

### Design

Use separate groups for:

- system On-Demand nodes
- general application nodes
- specialized GPU or storage nodes
- security or compliance boundaries

Avoid creating a node group for every application. That fragments capacity and increases operations.

---

## 8. Cluster Autoscaler

Cluster Autoscaler watches unschedulable pods and adjusts the size of configured node groups.

### Strong fits

- stable ASG or managed-node-group fleets
- known instance shapes
- mature existing node-group operating model
- limited need for dynamic instance selection

### How it reasons

Cluster Autoscaler simulates whether a pending pod would fit a node group based on the group's template and scaling limits.

### Important practices

- use similar instance shapes within a mixed group where scheduling simulation requires consistent capacity assumptions
- tag or configure node groups correctly for discovery
- ensure labels, taints, and resources are represented accurately
- give the controller least-privilege AWS permissions
- monitor scale-up failures and unneeded-node decisions
- avoid excessive node-group count

### Limitations

- capacity choices are constrained to predefined groups
- many groups increase simulation and operational complexity
- one group may fail capacity acquisition even though another instance family is available
- the controller must coordinate with ASG behavior and node readiness

Cluster Autoscaler is not obsolete. It is appropriate where predefined groups are an intentional design.

---

## 9. Karpenter

Karpenter monitors pods that cannot schedule, evaluates their constraints, selects matching EC2 capacity, launches nodes, and can consolidate underutilized capacity.

### Strong fits

- heterogeneous workloads
- many acceptable instance families and sizes
- rapid and flexible node provisioning
- Spot diversification
- reducing the number of predefined node groups
- application-first scheduling requirements

### NodePool example

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general
spec:
  template:
    metadata:
      labels:
        workload-class: general
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64", "arm64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["us-east-1a", "us-east-1b", "us-east-1c"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: general
  limits:
    cpu: "2000"
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
```

Validate exact API versions against the deployed Karpenter release.

### Production practices

- run the controller on stable On-Demand capacity that it does not depend on itself to create
- pin tested AMIs rather than tracking an untested latest alias
- allow multiple instance categories, families, generations, and sizes
- set NodePool resource limits
- use topology constraints
- account for daemonset overhead
- monitor provisioning, registration, and consolidation
- stage controller and CRD upgrades
- protect workloads with PDBs and graceful shutdown

### Consolidation risk

Consolidation reduces cost but intentionally disrupts nodes.

Protect against:

- excessive churn
- simultaneous deployment and consolidation
- eviction of long-running non-checkpointed work
- strict PDB deadlock
- rescheduling into scarce capacity
- repeated image pulls

Cost optimization must remain subordinate to the service SLO.

---

## 10. Karpenter versus Cluster Autoscaler

| Dimension | Karpenter | Cluster Autoscaler |
|---|---|---|
| Capacity model | dynamic node selection from pod requirements | scales predefined node groups |
| Instance flexibility | high | bounded by groups |
| Fleet complexity | fewer broad NodePools possible | many groups may be needed |
| AWS integration | EC2-aware direct provisioning | ASG/managed-node-group scaling |
| Best fit | heterogeneous and bursty EKS workloads | stable predefined fleets |
| Consolidation | native disruption/consolidation model | scale-down through node-group logic |
| Operational migration | requires CRDs, controller, NodePool/NodeClass design | familiar in existing ASG estates |

Do not run both against the same capacity pool.

A common design is:

- managed node group without Cluster Autoscaler for fixed system baseline
- Karpenter for elastic application nodes

Another valid design is:

- Cluster Autoscaler for all approved managed node groups
- no Karpenter

Choose one owner for elastic capacity.

---

## 11. Spot Instances

Spot capacity is spare EC2 capacity that can be interrupted. It is a capacity market, not a guaranteed cheap instance pool.

### Good Spot workloads

- stateless replicas with sufficient redundancy
- queue consumers with idempotency
- batch jobs with checkpointing
- distributed compute
- caches that tolerate node loss
- noncritical asynchronous processing

### High-risk Spot workloads

- single-replica critical services
- quorum members without careful failure-domain design
- databases not designed for interruption
- long non-checkpointed jobs
- system components required to create replacement capacity
- workloads with no graceful termination behavior

### Diversification

Permit many:

- instance families
- sizes
- generations
- AZs

Avoid pinning one instance type because it had a good historical discount.

### Capacity allocation

Prefer allocation strategies designed to improve capacity availability, such as price-capacity-optimized behavior in the relevant AWS mechanism.

The lowest current price is not useful if the pool is repeatedly interrupted or unavailable.

### Interruption handling

On interruption signal:

1. cordon the node
2. drain evictable pods
3. stop new work
4. checkpoint or return work to the queue
5. remove the node cleanly
6. replace capacity elsewhere

Application termination must fit within the available notice and actual shutdown timeline.

### Capacity rebalance

Capacity rebalance can launch replacement instances when interruption risk is detected. It does not guarantee interruption will be avoided or that replacement capacity will be ready in time.

---

## 12. On-Demand baseline and Spot mix

Use On-Demand for:

- CoreDNS and critical system controllers
- GitOps, admission, and autoscaling controllers
- minimum replicas required by the SLO
- non-interruptible control-plane dependencies
- workloads that cannot recover within interruption time

Use Spot above the durable baseline for tolerant replicas and asynchronous capacity.

Do not use a fixed universal percentage. Determine mix from:

- interruption tolerance
- recovery time
- minimum safe replica count
- demand variability
- cost objective
- available instance diversity
- dependency headroom

Test the loss of all Spot capacity in one AZ and a broad Spot interruption wave.

---

## 13. Zonal capacity and topology

### Placement

Use topology-spread constraints to avoid concentrating replicas:

```yaml
spec:
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: api
```

### Surviving an AZ loss

If normal load consumes nearly all capacity in all three AZs, the service cannot instantly survive one AZ loss.

Plan:

- baseline headroom in surviving AZs
- EC2 capacity diversity
- subnet IP space
- stateful dependency failover
- load-balancer redistribution
- Karpenter or ASG limits
- quotas
- warm capacity for latency-sensitive services

Do not assume the same instance type will be available in the remaining AZs during a regional event.

---

## 14. Overprovisioning and warm capacity

Reactive node scaling may be too slow for sudden bursts.

Options:

### Placeholder pods

Run low-priority pods reserving capacity. Critical pods preempt them when demand rises, and the autoscaler replaces the lost headroom.

### Minimum node capacity

Maintain a small buffer of ready On-Demand nodes.

### Scheduled scaling

Pre-scale before known events, business openings, or batch windows.

### Predictive scaling

Use historical demand forecasting where patterns are stable and errors are understood.

### Image and startup optimization

- smaller images
- ECR locality and permissions
- lazy loading where validated
- pre-pull for very large images when justified
- fast startup probes
- avoid synchronous migrations on every pod start

The cost of warm capacity is often lower than the error-budget cost of repeatedly missing burst traffic.

---

## 15. PodDisruptionBudgets and graceful termination

PDBs protect against voluntary eviction.

They do not protect against:

- instance crash
- AZ loss
- OOM kill
- forced termination
- every Spot interruption scenario

Set PDBs so they preserve availability without blocking all node maintenance.

Graceful termination sequence:

```text
termination starts
  -> readiness becomes false
  -> endpoint and load-balancer propagation
  -> stop accepting new work
  -> complete or hand off in-flight work
  -> flush telemetry
  -> exit before grace period ends
```

Validate actual propagation and shutdown timing.

---

## 16. Scale-down safety

Scale-down can cause:

- cache cold starts
- connection churn
- increased image pulls
- latency oscillation
- PDB blocking
- rescheduling pressure
- loss of local ephemeral data

Use:

- stabilization windows
- conservative scale-down rates
- minimum replicas
- disruption budgets
- Karpenter disruption controls
- workload-specific `safe-to-evict` decisions only when understood
- observability for repeated node churn

Do not optimize for maximum utilization. Optimize for the lowest sustainable cost that still meets the reliability objective.

---

## 17. Autoscaling failure taxonomy

### HPA wants more pods, but replicas do not increase

- max replicas reached
- wrong scale target
- missing metrics
- admission rejection
- deployment controller issue

### Replicas increase, but pods remain Pending

- insufficient CPU or memory
- node selector or affinity impossible
- taint not tolerated
- PVC or topology constraint
- IP exhaustion
- quota reached
- autoscaler not observing the pod

### Nodes launch, but never become Ready

- bootstrap failure
- IAM or access-entry failure
- network path or DNS failure
- wrong AMI or user data
- CNI failure
- security-group rules
- incompatible add-on

### Pods become Ready, but traffic remains unhealthy

- load-balancer target registration delay
- readiness probe too shallow
- application dependency failure
- connection pool exhaustion
- cache warmup
- bad version

### Capacity scales, but latency remains high

- database or cache saturation
- lock contention
- downstream throttling
- retry storm
- CPU throttling
- network or DNS latency
- hot partition

The incident must follow the full capacity path.

---

## 18. Observability

### Demand

- RPS and concurrent requests
- queue depth and oldest-message age
- active jobs or sessions
- forecast versus actual

### Pods

- HPA current and desired replicas
- available and ready replicas
- pending pods by scheduling reason
- startup and readiness time
- CPU throttling and memory pressure

### Nodes

- requested and available CPU/memory
- node provisioning duration
- node registration and Ready duration
- instance type, AZ, and capacity type
- Spot interruptions
- consolidation and termination rate
- allocatable versus requested resources

### AWS

- EC2 quota usage
- insufficient-capacity errors
- ASG desired/in-service/pending instances
- subnet free IPs
- ECR pull failures
- API throttling

### Capacity-realization SLI

Measure:

```text
T0 demand threshold crossed
T1 HPA or KEDA desired replicas changed
T2 pods Pending
T3 node provisioning requested
T4 instance launched
T5 node Ready
T6 pod Ready
T7 load-balancer target healthy
T8 latency/error SLI recovered
```

This timeline identifies the real slow stage.

---

## 19. Validation plan

1. establish per-pod safe throughput under production-like dependency latency
2. load test HPA scale-up and scale-down
3. test node provisioning from zero spare capacity
4. test with large images and cold caches
5. exhaust one permitted instance family and verify diversification
6. remove one AZ
7. simulate Spot interruption waves
8. confirm PDB and graceful termination behavior
9. test quota exhaustion and alerting
10. verify the database and queues can absorb the scaled frontend
11. run deployment and scaling simultaneously
12. measure user SLI recovery, not only node count

---

## 20. Cost model

Use:

- Savings Plans for durable On-Demand baseline
- Spot for interruption-tolerant variable capacity
- Graviton after application and performance validation
- Karpenter consolidation within disruption budgets
- right-sized requests
- scheduled scale-down for known idle windows
- storage and network-cost analysis

Watch hidden scaling costs:

- NAT processing
- cross-AZ data transfer
- log ingestion
- unused large requests
- excess load balancers
- repeated image pulls
- churn from overaggressive consolidation

A cheaper node fleet that causes retries, cross-AZ traffic, or outages may increase total cost.

---

## Adversarial follow-ups

### “Karpenter or Cluster Autoscaler?”

Karpenter for flexible, heterogeneous, application-driven EC2 selection; Cluster Autoscaler for stable predefined ASG or managed-node-group fleets. I select one owner per capacity pool and base the choice on workload diversity and operational model.

### “Why not 100% Spot?”

Because interruption and capacity availability are not under my control. I keep critical controllers and minimum SLO capacity on On-Demand, then use diversified Spot for tolerant excess capacity.

### “Why didn't HPA solve the latency spike?”

HPA may have requested pods that could not schedule, or new pods may have arrived after the spike. The bottleneck may also be a dependency. I trace the loop from metric to desired replicas to Ready targets and user SLI.

### “How much spare capacity do you keep?”

Enough to meet the documented burst and failure objectives. I derive it from traffic shape, node startup time, AZ-failure capacity, forecast error, and the error budget, then validate it under load. I do not use a universal percentage.

### “Can Karpenter always find capacity?”

No. It is constrained by instance availability, quotas, NodePool requirements, AZs, subnet IPs, AMIs, and pod constraints. Diversification and tested fallback are essential.

### “What is the most dangerous autoscaling mistake?”

Treating a node launch as success. The user receives capacity only after the node joins, the pod starts, readiness passes, the target is healthy, and dependencies remain unsaturated.

---

## Weak answers to avoid

- “Use HPA at 70% CPU and Cluster Autoscaler.”
- running Karpenter and Cluster Autoscaler against the same nodes
- 100% Spot for critical system and application minimums
- one exact Spot instance type
- no resource requests
- assuming PDB protects against every interruption
- no AZ-failure headroom
- no subnet IP or quota planning
- optimizing node utilization while ignoring dependency capacity
- measuring desired replicas instead of Ready serving capacity

---

## Closing statement

> Autoscaling is a chain of control loops, not a checkbox. I size from measured workload behavior, reserve failure and burst headroom, assign one controller to each capacity boundary, diversify interruption-tolerant supply, and prove the complete demand-to-ready-capacity timeline against user-facing SLOs.