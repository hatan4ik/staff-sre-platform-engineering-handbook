# Kubernetes Autoscaling Control Loops, Scheduling, and Capacity Realization

## Interview scenario

A high-traffic Kubernetes service breaches latency and error objectives during a demand spike. Dashboards show high CPU, the HPA exists, and node autoscaling is enabled, yet useful serving capacity does not increase quickly enough.

The Staff/Principal task is to identify the exact failed transition, stabilize the service, correct the control system, and prove that future demand can become healthy customer-serving capacity within the required time.

---

## 1. Ninety-second Staff/Principal answer

> I separate demand detection, pod-replica control, scheduling, node supply, workload startup, and traffic admission because each is a different control loop with different inputs and delays. HPA or KEDA changes desired replicas from a metric close to work, the scheduler attempts placement, and one node-capacity controller such as Cluster Autoscaler or Karpenter supplies capacity for unschedulable pods. A Ready node, a Ready pod, and a healthy load-balancer target are three different milestones.
>
> I first classify whether the failure is observation, replica calculation, scale-target mutation, scheduling, node provisioning, startup, readiness, traffic distribution, or a saturated downstream dependency. For CPU-based HPA, I verify the exact Metrics API data and requests because utilization is usage divided by request. I also check max replicas, HPA behavior, competing GitOps writers, pending-pod reasons, topology, IP capacity, quotas, image-pull time, and dependency headroom.
>
> For stable predefined node groups, Cluster Autoscaler is valid. For heterogeneous and bursty AWS fleets, Karpenter can select capacity directly from pending-pod constraints. I never give two controllers overlapping ownership of the same elastic pool. I keep a durable baseline for critical system and service replicas, then use interruption-tolerant capacity for safe workloads.
>
> The success metric is end-to-end capacity-realization time: demand threshold, desired replicas, Pending pods, node request, node Ready, pod Ready, target healthy, and user SLI recovery. I load-test that sequence, including an AZ loss, cold images, quota exhaustion, Spot interruption, and simultaneous deployment.

### Fifteen-second version

> Trace demand through every scaling transition, give each resource one controller, measure time to usable traffic capacity, and design enough warm and diversified supply to meet the SLO under failure.

---

## 2. End-to-end control-loop model

```text
business demand
      |
      v
resource, custom, or external metric
      |
      v
HPA / KEDA / another replica controller
      |
      v
scale subresource: desired replicas
      |
      v
Deployment / StatefulSet / Job controller
      |
      v
new Pods
      |
      v
scheduler
      |
      +--> fit existing nodes --------------------+
      |                                           |
      +--> remain Pending                         |
                |                                 |
                v                                 |
      node capacity controller                    |
      Cluster Autoscaler or Karpenter             |
                |                                 |
                v                                 |
      VM launch -> bootstrap -> node Ready -------+
                                                  |
                                                  v
                                      images, init, startup
                                                  |
                                                  v
                                      readiness and endpoints
                                                  |
                                                  v
                                      load-balancer target health
                                                  |
                                                  v
                                      useful serving capacity
                                                  |
                                                  v
                                      user SLI recovery
```

Every arrow can fail or be slow.

A common mistake is to say “the HPA failed” when the HPA correctly increased desired replicas but pods never scheduled or never became useful.

---

## 3. Ownership boundaries

A stable platform assigns one controller to each decision.

| Decision | Typical owner |
|---|---|
| Desired pod replicas | HPA, KEDA, custom autoscaler, or operator |
| Resource requests | Human policy, VPA recommender/updater, or platform automation |
| Pod placement | Kubernetes scheduler |
| Predefined node-group size | Cluster Autoscaler or cloud autoscaling policy |
| Dynamic node selection | Karpenter or equivalent provisioner |
| Deployment rollout | Deployment, Argo Rollouts, Flagger, or another rollout controller |
| Fixed replica baseline | HPA `minReplicas`, workload policy, or explicit non-autoscaled deployment |
| Traffic admission | Readiness, EndpointSlice, ingress, gateway, and load balancer |

Conflicting writers cause unstable behavior:

- GitOps continuously reapplies `spec.replicas` while HPA changes it.
- HPA and a custom controller target the same scale subresource.
- VPA changes CPU requests while HPA scales on CPU utilization without a deliberate interaction design.
- Cluster Autoscaler and Karpenter both attempt to own the same capacity.
- Scheduled scaling and reactive scaling use incompatible minimums.

The Principal rule is:

> One resource, one authoritative controller per decision dimension.

---

## 4. HPA algorithm from first principles

For a metric target, the simplified formula is:

```text
desiredReplicas = ceil(
  currentReplicas × currentMetricValue / desiredMetricValue
)
```

For CPU `averageUtilization`, the metric is CPU usage relative to CPU request.

Example:

```text
current replicas: 10
average usage:    900m per pod
average request: 1000m per pod
current CPU:       90%
target CPU:        60%

desired = ceil(10 × 90 / 60) = 15
```

Change only the request:

```text
average usage:    900m
average request: 4000m
current CPU:     22.5%
target CPU:       60%
```

The dashboard can honestly show substantial CPU consumption while the HPA correctly decides not to scale.

### Requests are control inputs

CPU requests are simultaneously:

- Scheduler reservations.
- HPA utilization denominators.
- Inputs to node-capacity simulation.
- Signals used for bin packing and cost allocation.

Understated requests can produce:

- Excessive packing.
- CPU contention.
- Memory pressure.
- Early or noisy HPA scale-up.
- Node instability.

Overstated requests can produce:

- Suppressed utilization-based scale-up.
- Poor bin packing.
- More nodes and higher cost.
- Pending pods despite real unused capacity.

Missing requests can make a utilization metric undefined for relevant pods or containers.

---

## 5. Metric types

### Resource metrics

Examples:

- CPU.
- Memory.

Useful when resource consumption closely tracks work.

Limitations:

- CPU may lag demand.
- Memory often does not fall quickly.
- Resource usage can be dominated by sidecars or background work.
- A downstream bottleneck may cause low CPU and high latency.

### Container resource metrics

Useful when one application container should drive scaling while a sidecar has independent behavior.

Migration caution:

During a rollout that renames the container, both old and new versions may need metric coverage.

### Pods metrics

Examples:

- Requests in flight per pod.
- Active sessions per pod.
- Work queue per pod.

### Object metrics

A metric associated with a Kubernetes object.

### External metrics

Examples:

- Queue depth.
- Oldest-message age.
- Load-balancer RPS.
- Stream lag.
- Business backlog outside the cluster.

External metrics require an adapter or system that exposes them to the autoscaling API.

### Choose the signal closest to demand

Good scaling signals often include:

- RPS per serving pod.
- Concurrent requests.
- Queue age.
- Stream lag.
- In-flight jobs.
- Active sessions.
- Application saturation.

CPU remains appropriate for CPU-bound work, but should not be used merely because it is available.

---

## 6. HPA behavior and stability

Example:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ledger-api
  namespace: payments
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ledger-api
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

Design principles:

- Scale up quickly enough to protect the SLO.
- Scale down conservatively to avoid oscillation.
- Maintain a nonzero baseline for latency-sensitive paths.
- Set maximum replicas from dependency and budget constraints, not an arbitrary large number.
- Ensure rollout surge plus HPA growth can fit cluster capacity.
- Treat behavior policies as rate limits on the control loop.

A higher maximum does not help if the database, queue, API quota, or subnet is the real limit.

---

## 7. Four primary failure domains

### Domain A — Observation failure

The controller cannot obtain a valid metric.

Examples:

- Metrics Server unavailable.
- `metrics.k8s.io` APIService unhealthy.
- Kubelet scrape failure.
- Custom or external adapter unavailable.
- Metric stale or missing.
- Wrong label selector.
- Pod or container requests absent.

Evidence:

- HPA target is `<unknown>`.
- `ScalingActive=False`.
- Events such as failed resource or external metric retrieval.
- `kubectl top` fails or omits pods.

### Domain B — Calculation or policy failure

The metric is available, but desired replicas do not increase.

Examples:

- CPU request makes utilization appear low.
- Target already near desired ratio.
- `maxReplicas` reached.
- Scale-up policy limits growth.
- Wrong target or metric selector.
- Missing and not-yet-ready metrics dampen the result.
- Spike shorter than collection and reconciliation windows.

### Domain C — Scale mutation or controller conflict

The autoscaler wants more replicas but cannot make the target retain the change.

Examples:

- Scale target is wrong or missing.
- Admission policy rejects update.
- API authorization or control-plane failure.
- GitOps reapplies a fixed replica count.
- Two autoscalers fight.
- Rollout controller constrains or replaces pods unexpectedly.

### Domain D — Capacity realization failure

Desired replicas increase but serving capacity does not.

Examples:

- Pods Pending.
- Node capacity cannot be acquired.
- Impossible affinity, taint, or topology rule.
- PVC topology or storage delay.
- Pod IP or subnet exhaustion.
- Image pull is slow.
- Init container or sidecar fails.
- Readiness remains false.
- EndpointSlice or load-balancer target is delayed.
- Cache warmup consumes resources.
- Database or downstream dependency is saturated.

---

## 8. Incident classification using the replica chain

Capture:

1. HPA current replicas.
2. HPA desired replicas.
3. Workload `spec.replicas`.
4. Workload created replicas.
5. Scheduled pods.
6. Ready pods.
7. Ready endpoints or targets.
8. Per-pod traffic.
9. User SLI.

| Observation | Likely domain |
|---|---|
| Desired equals current despite load | observation or calculation |
| Desired exceeds current but target spec does not change | mutation or controller conflict |
| Spec rises but pods remain Pending | scheduling or node supply |
| Pods run but are not Ready | startup, health, secret, network, or dependency |
| Pods are Ready but receive no traffic | Service, EndpointSlice, ingress, LB, or stickiness |
| Traffic spreads but SLI remains bad | wrong signal or downstream bottleneck |

---

## 9. First-response workflow

### Step 1 — Protect users

Possible containment:

- Shed optional work.
- Reject low-priority traffic early.
- Serve safe stale responses.
- Limit concurrency.
- Open a circuit to a failed dependency.
- Pause expensive background work.
- Manually increase replicas when verified cluster and dependency headroom exists.
- Pre-provision nodes when the node loop is too slow.

Do not lower requests or remove limits blindly during an outage.

### Step 2 — Inspect HPA conditions

```bash
kubectl get hpa -n <namespace> <name> -o yaml
kubectl describe hpa -n <namespace> <name>
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

Focus on:

- `AbleToScale`.
- `ScalingActive`.
- `ScalingLimited`.
- Current and desired metrics.
- Current and desired replicas.
- Last scale time.
- Event reasons.

### Step 3 — Inspect the exact metric pipeline

```bash
kubectl top pods -n <namespace> --containers
kubectl get --raw '/apis/metrics.k8s.io/v1beta1/namespaces/<namespace>/pods' | jq
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml
```

Compare with:

- CPU and memory requests.
- Metric timestamps.
- Prometheus or APM query semantics.
- Sidecar inclusion.
- HPA metric target type.

### Step 4 — Inspect scale ownership

```bash
kubectl get deploy -n <namespace> <name> -o yaml
kubectl get hpa -A
kubectl get scaledobject -A 2>/dev/null
```

Review:

- GitOps desired state.
- Deployment pipeline.
- Scheduled scaler.
- VPA.
- Custom operator.
- Rollout controller.

### Step 5 — Inspect Pending and startup states

```bash
kubectl get pods -n <namespace> -l app=<label> -o wide
kubectl describe pod -n <namespace> <pending-pod>
kubectl get events -A --sort-by=.lastTimestamp
kubectl get nodes -o wide
kubectl describe node <node>
```

Look for:

- `Insufficient cpu` or memory.
- Untolerated taint.
- Node affinity mismatch.
- Topology spread failure.
- PVC binding.
- Pod IP exhaustion.
- Image-pull errors.
- Admission or secret-mount failures.
- Readiness and startup probe failures.

### Step 6 — Inspect traffic admission

```bash
kubectl get endpointslice -n <namespace> \
  -l kubernetes.io/service-name=<service> -o yaml
kubectl get service -n <namespace> <service> -o yaml
```

Also inspect ingress, gateway, service mesh, and cloud load-balancer target health.

### Step 7 — Inspect dependencies

Validate:

- Database connections and CPU.
- Cache hit rate and hot keys.
- Queue throughput.
- Third-party rate limits.
- DNS and network latency.
- Locks and serialization points.

Scaling the caller can amplify pressure on an already failing dependency.

---

## 10. VPA and request management

Vertical Pod Autoscaler can recommend or modify requests based on observed usage and platform capabilities.

Modes and exact behavior depend on deployment and version, but the important design questions are:

- Does changing requests require pod replacement?
- Can the workload tolerate that disruption?
- Does HPA scale on utilization that uses the same request as its denominator?
- Are recommendations based on representative peaks and startup behavior?
- Are sidecars and init containers accounted for?
- Is policy limiting unsafe recommendations?

Common safe pattern:

- Use VPA in recommendation mode first.
- Review recommendations against load tests and SLOs.
- Apply changes through normal deployment promotion.
- Use HPA on a business or absolute metric when automatic VPA changes would destabilize utilization-based scaling.

Do not let a right-sizing controller and a replica controller form an unexamined feedback loop.

---

## 11. KEDA and event-driven scaling

KEDA connects event sources to Kubernetes scaling.

Typical signals:

- Queue depth.
- Oldest-message age.
- Kafka or stream lag.
- Prometheus query.
- Scheduled work.
- Cloud event source.

For queue workers, use capacity math:

```text
required processing rate = arrival rate + backlog / target drain time
required workers = required processing rate / safe worker rate
```

Queue depth alone can be misleading. Oldest-message age and processing rate often better represent user impact.

Scale-to-zero considerations:

- Cold-start delay.
- Identity and secret initialization.
- Connection establishment.
- Queue growth during startup.
- Visibility timeout.
- Duplicate delivery.
- Downstream rate limits.

Keep a warm baseline when the latency objective cannot tolerate cold start.

---

## 12. Scheduler constraints are capacity requirements

The scheduler does not place a generic pod on a generic node. It evaluates constraints.

Examples:

- Resource requests.
- Node selectors.
- Required node affinity.
- Pod affinity and anti-affinity.
- Taints and tolerations.
- Topology spread.
- Persistent-volume topology.
- Host ports.
- Extended resources such as GPUs.
- Architecture and operating system.
- Pod density and platform limits.

A node autoscaler must create a node that satisfies all required constraints.

Impossible example:

```text
Pod requires:
  zone-a
  arm64
  GPU type X
  encrypted local NVMe
  dedicated tenant taint

No permitted capacity type provides that combination.
```

Adding more generic nodes will never schedule the pod.

---

## 13. Cluster Autoscaler

Cluster Autoscaler scales predefined node groups when pods cannot schedule and simulates whether a node-group template would fit them.

Strong fit:

- Stable managed node groups or ASGs.
- Known instance shapes.
- Regulated fleets with predefined capacity classes.
- Existing mature node-group operations.
- Limited need for dynamic instance selection.

Operational requirements:

- Correct node-group discovery.
- Accurate labels, taints, and template resources.
- Consistent capacity assumptions for mixed groups.
- Least-privilege cloud permissions.
- Reasonable number of node groups.
- Monitoring of scale-up failures and unneeded-node decisions.

Limitations:

- Can choose only from predefined groups.
- A group may fail to acquire capacity while another instance family is available.
- Many groups increase simulation and operating complexity.
- Node readiness remains a separate failure domain.

Cluster Autoscaler is not obsolete. It is appropriate when predefined capacity is an intentional platform contract.

---

## 14. Karpenter

Karpenter evaluates unschedulable pod constraints and creates node capacity matching those constraints using NodePools and provider-specific node classes.

Strong fit:

- Heterogeneous workloads.
- Many acceptable instance families and sizes.
- Bursty capacity.
- Broad Spot diversification.
- Reducing the number of static node groups.
- Application-first capacity selection.

Conceptual NodePool:

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
          values: ["zone-a", "zone-b", "zone-c"]
      nodeClassRef:
        group: provider.example
        kind: ProviderNodeClass
        name: general
  limits:
    cpu: "2000"
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    budgets:
      - nodes: "10%"
```

Provider-specific fields and exact API versions must be validated against the deployed release.

Production practices:

- Run the controller on stable capacity that does not depend on itself.
- Use tested node images.
- Allow enough instance and zone diversity.
- Set NodePool limits.
- Include DaemonSet overhead.
- Separate trust or hardware boundaries deliberately.
- Stage CRD and controller upgrades.
- Monitor NodeClaims, provisioning, registration, drift, and disruption.
- Use disruption budgets and maintenance windows where necessary.

### Consolidation and disruption

Consolidation reduces cost by voluntarily replacing or removing nodes.

Risks:

- Excessive churn.
- Cold caches and repeated image pulls.
- Disruption during deployment.
- Strict PDB deadlock.
- Replacement capacity unavailable.
- Long-running jobs evicted.
- Stateful local data lost.

Cost optimization must remain subordinate to the workload SLO.

---

## 15. Cluster Autoscaler versus Karpenter

| Dimension | Cluster Autoscaler | Karpenter |
|---|---|---|
| Supply model | Scales predefined node groups | Selects and creates capacity from pod requirements |
| Instance flexibility | Bounded by groups | Broad, policy constrained |
| Best fit | Stable known fleets | Heterogeneous and bursty fleets |
| Underlying abstraction | Node group / ASG | NodePool / NodeClaim / provider node class |
| Scale-down | Node-group autoscaler behavior | Disruption, consolidation, drift, expiration |
| Migration cost | Lower in established group fleets | Requires controller, CRDs, policy, and image design |

Valid architecture A:

```text
fixed system managed node group
Karpenter owns elastic application capacity
Cluster Autoscaler does not own that pool
```

Valid architecture B:

```text
approved managed node groups
Cluster Autoscaler owns their elasticity
Karpenter is absent
```

Invalid architecture:

```text
Cluster Autoscaler and Karpenter both attempt to create or remove the same logical capacity
```

---

## 16. On-Demand, reserved, and interruptible capacity

Maintain durable capacity for:

- DNS and networking components.
- Autoscaling controllers.
- Admission and GitOps controllers.
- Minimum replicas required by the SLO.
- Workloads that cannot recover within interruption time.
- Critical stateful members.

Use interruptible or Spot capacity for:

- Stateless redundant replicas.
- Idempotent queue consumers.
- Checkpointed batch work.
- Caches that tolerate loss.
- Noncritical asynchronous processing.

Diversify across:

- Instance families.
- Sizes.
- Generations.
- Zones.
- Capacity pools.

Do not set one universal Spot percentage. Derive the mix from:

- Minimum safe capacity.
- Interruption tolerance.
- Recovery time.
- Demand variability.
- Instance diversity.
- Dependency headroom.
- Error-budget policy.

Test the loss of all interruptible capacity in one zone and a broader interruption wave.

---

## 17. Warm capacity and burst handling

Reactive scaling cannot serve demand that arrives faster than capacity can become useful.

Options:

### Minimum warm replicas

Maintain pods sufficient for ordinary variation.

### Ready node buffer

Keep a small amount of schedulable capacity.

### Placeholder pods

Low-priority pods reserve capacity and are preempted by real work. Their eviction triggers replenishment of the buffer.

### Scheduled pre-scaling

Use before known business events, batch windows, or launches.

### Forecast-based scaling

Useful for repeatable patterns when forecast error is measured.

### Startup optimization

- Reduce image size.
- Improve registry locality and authentication.
- Avoid synchronous migrations on pod start.
- Make initialization parallel where safe.
- Use startup probes correctly.
- Pre-warm caches only when the cost is justified.

Warm capacity is an insurance premium against capacity-realization delay.

---

## 18. Topology and failure headroom

A three-zone service that consumes nearly all available capacity in every zone cannot instantly survive one zone loss.

Plan for:

- Replica distribution.
- Node supply in surviving zones.
- Subnet and pod IP capacity.
- Load-balancer redistribution.
- Stateful dependency failover.
- Quotas.
- Image and registry availability.
- Capacity type diversity.

Example topology spread:

```yaml
spec:
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: DoNotSchedule
      labelSelector:
        matchLabels:
          app: ledger-api
```

`DoNotSchedule` preserves distribution but can keep pods Pending when one zone lacks capacity. That may be correct, but the node-supply policy must be able to satisfy it.

---

## 19. PDBs and graceful termination

A PodDisruptionBudget limits voluntary disruption. It does not protect against every involuntary failure.

It does not prevent:

- Node crash.
- Zone failure.
- OOM kill.
- Forced termination.
- All interruptible-capacity events.

A strict PDB can block maintenance or consolidation indefinitely.

Graceful termination sequence:

```text
termination begins
      |
      v
readiness becomes false
      |
      v
endpoints and load balancers stop new traffic
      |
      v
application drains or checkpoints work
      |
      v
telemetry flushes
      |
      v
process exits before grace period expires
```

Measure real propagation time. Do not assume readiness removal is instantaneous at every proxy and load balancer.

---

## 20. Scale-down safety

Scale-down can cause:

- Cache cold starts.
- Connection churn.
- Increased image pulls.
- Tail-latency oscillation.
- Rescheduling pressure.
- Local-data loss.
- PDB blocking.
- Zone imbalance.

Controls:

- Conservative HPA scale-down policy.
- Minimum replicas.
- Disruption budgets.
- Karpenter disruption limits.
- Maintenance windows.
- Workload-safe eviction annotations only when understood.
- Churn and cache-warmup observability.

The objective is not maximum utilization. It is the lowest sustainable cost that continues to meet reliability and recovery objectives.

---

## 21. Capacity-realization timeline

Instrument these timestamps:

```text
T0 demand threshold crossed
T1 metric available to autoscaler
T2 desired replicas increased
T3 new pods created
T4 pods declared unschedulable
T5 node provisioning requested
T6 VM or machine launched
T7 node joined and became Ready
T8 pod scheduled
T9 containers started
T10 pod Ready
T11 endpoint published
T12 load-balancer target healthy
T13 per-pod traffic balanced
T14 user latency and error SLI recovered
```

Derived metrics:

```text
metric delay             = T1 - T0
replica-control delay    = T2 - T1
pod-creation delay       = T3 - T2
node-decision delay      = T5 - T4
machine launch delay     = T7 - T5
pod startup delay        = T10 - T8
traffic admission delay  = T13 - T10
SLI recovery delay       = T14 - T13
end-to-end realization   = T14 - T0
```

This timeline prevents teams from optimizing the wrong controller.

---

## 22. Capacity planning

### Demand inputs

- Peak RPS or events per second.
- Concurrency.
- Payload size.
- Burst shape.
- Daily and seasonal pattern.
- Tenant skew.
- Failure-driven traffic shift.

### Per-pod profile

- Safe throughput at target p99.
- CPU and memory.
- Startup time.
- Image pull time.
- Sidecar and DaemonSet overhead.
- Network and storage needs.
- Connection pools.
- Cache behavior.

### Reliability inputs

- Failure domains.
- Zone-loss headroom.
- Rollout surge.
- Replacement overlap.
- Interruption tolerance.
- Recovery objective.

### Platform inputs

- Compute quotas.
- Instance or machine availability.
- Subnet IPs.
- Pod density.
- Registry and image limits.
- Control-plane throughput.
- Storage attachment limits.
- Load-balancer limits.

### Dependency inputs

- Database connections.
- Cache capacity.
- Queue throughput.
- Downstream API quotas.
- Egress and NAT capacity.
- DNS.

### Basic service math

If one pod safely handles 500 RPS at the target p99 and peak is 100,000 RPS:

```text
base replicas = 100,000 / 500 = 200
```

Then add explicit margin for:

- Zone failure.
- Rollout surge.
- Forecast error.
- Uneven load balancing.
- Cold caches.
- Dependency latency.

Do not use one universal headroom percentage. Derive and validate it.

---

## 23. Failure taxonomy by stage

### HPA wants no additional pods

- Wrong or missing metric.
- CPU request denominator too high.
- Tolerance or behavior policy.
- Max replicas reached.
- Wrong target.

### HPA wants pods but target does not retain replicas

- Scale update failure.
- RBAC or admission denial.
- GitOps conflict.
- Another autoscaler.

### Pods are created but Pending

- Insufficient requested resources.
- Affinity or topology impossible.
- Taints.
- PVC topology.
- Host-port conflict.
- Pod IP exhaustion.
- Quota.
- Node autoscaler not observing or unable to match.

### Nodes launch but do not become Ready

- Bootstrap failure.
- Identity or join failure.
- DNS or network.
- Wrong image.
- CNI failure.
- Security policy.
- Kubelet or runtime failure.

### Pods run but do not become Ready

- Startup probe.
- Secret or identity retrieval.
- Dependency unavailable.
- Sidecar initialization.
- Configuration error.
- Cache or model loading.

### Pods are Ready but not useful

- Endpoint propagation.
- Load-balancer target delay.
- Sticky sessions.
- Uneven hashing.
- Wrong version.
- Downstream saturation.
- Lock contention.
- Retry storm.

---

## 24. Validation plan

1. Establish safe per-pod throughput under production-like dependency latency.
2. Validate HPA formula and metric source.
3. Test a step increase and gradual increase in demand.
4. Measure scaling from zero spare node capacity.
5. Test cold images and empty caches.
6. Run deployment and autoscaling simultaneously.
7. Remove one zone.
8. Exhaust one instance family or capacity pool.
9. Trigger quota and subnet-IP exhaustion.
10. Simulate interruptible-node termination.
11. Verify PDB and graceful shutdown.
12. Saturate a downstream dependency and confirm load shedding.
13. Validate scale-down and consolidation churn.
14. Confirm user SLI recovery, not only replica count.

---

## 25. Observability and SLOs

Demand:

- RPS, concurrency, queue age, lag.
- Forecast versus actual.
- Demand by tenant, region, and version.

Autoscaler:

- Metric availability and age.
- Current and desired replicas.
- Scaling conditions and reasons.
- Reconciliation errors.
- Time at min or max replicas.

Pods:

- Created, Pending, scheduled, running, Ready.
- Pending reason.
- Startup duration.
- Image-pull duration.
- CPU throttling and memory pressure.
- Requests versus usage.

Nodes:

- Requested versus allocatable resources.
- Provisioning duration.
- Registration and Ready duration.
- Capacity type and zone.
- Disruptions and consolidations.
- Node churn.

Traffic:

- Endpoint publication.
- Target-health time.
- Requests per pod.
- Load imbalance.
- User latency and error rate.

Example objectives:

- 99% of demand spikes within tested envelope reach usable capacity before the fast-burn alert threshold.
- p99 pod capacity realization below the documented burst budget.
- No unschedulable pod waits more than the node-provisioning objective when compatible capacity and quota exist.
- Critical baseline remains available after loss of one zone or the interruptible fleet defined by policy.

---

## 26. Common weak answers

### “Lower the HPA CPU target”

This may create more desired replicas without fixing missing metrics, requests, scheduling, node supply, readiness, or dependencies.

### “Restart Metrics Server”

Only valid after evidence places the failure in the metrics pipeline.

### “Set max replicas to 1,000”

A large maximum can amplify a downstream outage and does not create node, IP, database, or quota capacity.

### “Use Karpenter because Cluster Autoscaler is old”

The correct choice depends on whether capacity is dynamic or intentionally predefined.

### “Use Spot for 100% of workloads”

This ignores control-plane dependencies, minimum safe capacity, interruption waves, and recovery time.

### “PDB protects us from node loss”

PDBs govern voluntary eviction and do not prevent all involuntary failures.

### “A Ready pod means scaling is complete”

The pod may not yet be in EndpointSlices, healthy in the external load balancer, receiving balanced traffic, or improving the SLI.

---

## 27. Adversarial interview questions

### CPU is 95%, so why does HPA show 30%?

Clarify the graph denominator. HPA utilization compares usage to requests, while the graph may show percent of one core, a limit, or node capacity.

### HPA desired replicas increased. Is the incident solved?

No. Verify actual replicas, Pending reasons, node provisioning, readiness, endpoints, target health, traffic distribution, and user SLI.

### Can VPA and HPA run together?

Yes with a deliberate metric and ownership design. HPA on CPU utilization can interact with VPA changes to CPU requests because the denominator changes.

### Why keep warm capacity if autoscaling works?

Because observation, node launch, image pull, startup, and traffic admission have nonzero latency. Sudden demand can outrun reactive loops.

### Why not run Karpenter and Cluster Autoscaler together?

They can coexist only with clearly separate capacity ownership. Overlapping ownership produces conflicting supply and disruption decisions.

### How do you scale during a zone failure?

Redistribute traffic, maintain headroom and compatible capacity in surviving zones, ensure topology and IP space allow placement, and include stateful dependency readiness in the failover calculation.

### How do you know whether the problem is HPA or the database?

Trace the replica and capacity chain, then compare per-pod traffic, saturation, and dependency metrics. If capacity grows and requests reach new pods but latency remains high, investigate downstream limits and contention.

---

## 28. Staff/Principal answer checklist

A strong answer includes:

- Full control-loop diagram.
- One-owner rule.
- HPA request denominator.
- Exact metric pipeline.
- Four failure domains.
- Pending-pod and scheduler reasoning.
- Cluster Autoscaler versus Karpenter trade-off.
- Warm baseline and interruption strategy.
- Topology and failure headroom.
- PDB and graceful shutdown limitations.
- Capacity-realization timeline.
- User-facing validation.

---

## Primary references

- [Kubernetes Horizontal Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)
- [Kubernetes HPA v2 API](https://kubernetes.io/docs/reference/kubernetes-api/autoscaling/horizontal-pod-autoscaler-v2/)
- [Kubernetes workload autoscaling overview](https://kubernetes.io/docs/concepts/workloads/autoscaling/)
- [Kubernetes Vertical Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/vertical-pod-autoscale/)
- [Karpenter NodePools](https://karpenter.sh/docs/concepts/nodepools/)
- [Karpenter disruption](https://karpenter.sh/docs/concepts/disruption/)
