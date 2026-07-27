# Lab 5 — Kubernetes Autoscaling Control Loops and Capacity Realization

## Interview scenario

Traffic rises sharply. CPU dashboards show pressure and the HPA is configured, but the service continues breaching latency and error objectives.

Possible observations include:

- HPA does not request more replicas;
- desired replicas increase but pods remain Pending;
- nodes launch slowly;
- pods become Ready but do not receive traffic;
- application capacity increases but a database or downstream service remains saturated.

The weak response is to lower the HPA target or raise `maxReplicas` without identifying the failed transition.

The Staff/Principal task is to trace demand through every control loop and measure when it becomes useful customer-serving capacity.

## Safety invariant

> Scaling is complete only when the user-facing SLI recovers. More desired replicas, more nodes, and more Ready pods are intermediate states—not the outcome.

This lab is a deterministic standard-library simulation. It creates no cloud resources and does not require Kubernetes.

## What the simulator models

```text
CPU usage and request
      |
      v
simplified HPA replica calculation
      |
      v
desired replicas
      |
      +--> warm pod slots
      |
      +--> unschedulable pods
                |
                v
          node provisioning
                |
                v
          pod startup
                |
                v
          target health
                |
                v
          application capacity
                |
                v
          dependency capacity cap
                |
                v
          user SLI recovery or continued failure
```

The HPA calculation exposes:

- CPU usage divided by CPU request;
- target utilization;
- tolerance;
- minimum and maximum replicas;
- an optional scale-up rate limit.

The capacity model exposes:

- current Ready replicas;
- warm scheduling slots;
- node launch delay;
- pod startup delay;
- target-health delay;
- per-pod safe throughput;
- dependency capacity;
- end-to-end recovery time.

It is intentionally smaller than Kubernetes. Real HPA behavior also accounts for missing metrics, not-yet-ready pods, stabilization, recommendation history, and metric-specific rules.

## Prerequisites

- Python 3.11 or newer.
- No third-party packages.

## Run the demonstration

```bash
python3 autoscaling_sim.py --demo
```

The built-in scenarios demonstrate:

1. **Oversized CPU request suppresses scale-up** — absolute CPU is substantial, but utilization relative to request is low.
2. **Cold node capacity** — the HPA requests pods, but user recovery waits on node launch, pod startup, and target health.
3. **Warm capacity** — existing scheduling headroom avoids the node-provisioning delay.
4. **Downstream saturation** — application replicas increase, but effective capacity remains capped by a dependency.

The demo intentionally includes scenarios where scaling does not recover the service. That is the lesson: a functioning HPA is not proof of sufficient or useful capacity.

## Run the tests

```bash
python3 -m unittest -v test_autoscaling_sim.py
```

The tests prove:

- the utilization-based HPA formula;
- oversized requests can suppress scale-up;
- `maxReplicas` can cap the result;
- scale-up policy can rate-limit growth;
- a missing CPU request makes utilization scaling invalid;
- cold node supply recovers later than warm capacity;
- dependency capacity can prevent SLI recovery;
- desired replicas can still be insufficient for demand;
- existing capacity can already satisfy demand.

## HPA reasoning exercise

Given:

```text
current replicas: 10
average CPU usage: 900m
average CPU request: 1000m
target utilization: 60%
```

The simplified result is:

```text
current utilization = 900 / 1000 = 90%
desired replicas = ceil(10 × 90 / 60) = 15
```

Change only the request:

```text
average request: 4000m
current utilization = 900 / 4000 = 22.5%
```

A graph showing `900m` can be correct while the utilization-based HPA decides not to scale up.

## Capacity-realization timeline

The simulator emits timestamps similar to:

```text
T0 demand threshold crossed
T1 metric available
T2 desired replicas changed
T3 pods created
T4 pods unschedulable
T5 node provisioning requested
T6 node Ready
T7 warm-wave targets healthy
T8 node-wave targets healthy
T9 user SLI recovered
```

Use the differences to identify the dominant delay:

```text
metric delay
replica-control delay
node-decision delay
machine-launch delay
pod-startup delay
traffic-admission delay
end-to-end SLI recovery
```

## Production investigation mapping

### Step 1 — Protect users

Before tuning:

- shed optional work;
- reduce expensive feature paths;
- bound concurrency and queues;
- open circuits to failed dependencies;
- serve safe stale results where allowed;
- manually raise replicas only after proving cluster and dependency headroom.

### Step 2 — Capture the replica chain

```bash
kubectl get hpa -n <namespace> <name> -o yaml
kubectl get deploy -n <namespace> <name> -o yaml
kubectl get pods -n <namespace> -l app=<label> -o wide
```

Record:

1. HPA current replicas;
2. HPA desired replicas;
3. workload `spec.replicas`;
4. created replicas;
5. scheduled pods;
6. Ready pods;
7. EndpointSlice members;
8. healthy load-balancer targets;
9. traffic per pod;
10. user latency and error SLI.

### Step 3 — Inspect the exact metric path

```bash
kubectl describe hpa -n <namespace> <name>
kubectl top pods -n <namespace> --containers
kubectl get --raw '/apis/metrics.k8s.io/v1beta1/namespaces/<namespace>/pods' | jq
kubectl get apiservice v1beta1.metrics.k8s.io -o yaml
```

Compare:

- metric source and timestamp;
- units and aggregation;
- CPU requests;
- sidecar inclusion;
- HPA metric type and target;
- current, desired, and maximum replicas.

### Step 4 — Inspect control ownership

Look for:

- GitOps applying fixed `spec.replicas`;
- another HPA or custom autoscaler;
- KEDA `ScaledObject`;
- VPA mutating requests;
- scheduled scaling;
- rollout controller behavior;
- Cluster Autoscaler and Karpenter overlap.

One resource should have one authoritative controller for each decision dimension.

### Step 5 — Inspect Pending pods

```bash
kubectl describe pod -n <namespace> <pending-pod>
kubectl get events -A --sort-by=.lastTimestamp
kubectl get nodes -o wide
```

Common causes:

- insufficient requested CPU or memory;
- impossible affinity or topology;
- untolerated taint;
- PVC topology;
- host-port conflict;
- GPU or architecture requirement;
- subnet or pod-IP exhaustion;
- compute quota;
- node-autoscaler policy cannot create a matching node.

### Step 6 — Inspect startup and traffic admission

```bash
kubectl get endpointslice -n <namespace> \
  -l kubernetes.io/service-name=<service> -o yaml
kubectl describe pod -n <namespace> <new-pod>
```

Measure:

- image pull;
- init containers;
- identity and secret acquisition;
- startup probe;
- readiness;
- EndpointSlice publication;
- gateway and load-balancer target health;
- per-pod traffic balance.

### Step 7 — Inspect downstream capacity

More callers can worsen a saturated dependency.

Check:

- database CPU and connections;
- cache memory, hit rate, and hot keys;
- queue throughput and oldest-message age;
- downstream API quotas;
- locks and serialization;
- retry amplification;
- DNS, NAT, and network capacity.

## Warm capacity exercise

Using the test defaults:

```text
current replicas: 10
safe throughput: 500 RPS per pod
demand: 7000 RPS
desired replicas: 15
```

Current capacity is `5000 RPS`; final application capacity is `7500 RPS`.

With no warm slots, recovery includes node launch and occurs at the simulated `157 seconds`.

With five warm slots, no new node is needed and recovery occurs at `67 seconds`.

The values are illustrative. Production values must come from measured metric, provisioning, startup, readiness, and load-balancer timings.

## Dependency-cap exercise

If 20 pods can provide `10,000 RPS` but the database safely supports only `6,000 RPS`, effective capacity is still `6,000 RPS`.

The correct mitigation may involve:

- load shedding;
- cache or query changes;
- connection governance;
- read scaling;
- partition repair;
- rollback;
- reducing retries;
- restoring the dependency.

Adding more frontend replicas can increase connection pressure and make recovery slower.

## Failure modes this lab teaches

### Observation failure

The autoscaler cannot obtain a valid metric.

### Calculation or policy failure

The metric exists, but requests, tolerance, limits, or behavior prevent the intended replica count.

### Mutation or controller conflict

The desired count is computed but another controller rejects or overwrites it.

### Scheduling and node-supply failure

Pods exist but no compatible capacity becomes Ready.

### Startup or traffic-admission failure

Pods run but do not become healthy targets.

### Wrong bottleneck

Application capacity rises while the dependency, lock, partition, or network remains saturated.

## Production controls

- Requests derived from representative load tests.
- Scaling metrics close to demand or backlog.
- One controller per replica and capacity decision.
- Warm baseline for latency-sensitive services.
- Diversified node capacity and failure-domain headroom.
- Explicit NodePool or node-group limits.
- Conservative scale-down and disruption budgets.
- Startup and target-health latency instrumentation.
- Dependency-aware maximum replicas and load shedding.
- Game days for zone loss, quota exhaustion, cold images, and interruption waves.

## Interview answer drill

> I would separate metric observation, replica calculation, scale-target mutation, scheduling, node provisioning, startup, readiness, traffic admission, and dependency capacity. I would capture current, desired, specified, available, and traffic-serving replicas; compare the exact HPA metric with resource requests; inspect Pending reasons and node-autoscaler evidence; then trace new pods into EndpointSlices and healthy targets. I would measure demand-to-SLI-recovery time and avoid adding replicas when the true bottleneck is downstream.

## Related material

- [`core/kubernetes/autoscaling/control-loops-capacity-realization.md`](../../../core/kubernetes/autoscaling/control-loops-capacity-realization.md)
- [`tracks/aws/round-1/06-capacity-autoscaling-karpenter-spot.md`](../../../tracks/aws/round-1/06-capacity-autoscaling-karpenter-spot.md)
- [`netflix-devops-interview/curriculum/10-hpa-not-scaling-high-cpu.md`](https://github.com/hatan4ik/netflix-devops-interview/blob/main/curriculum/10-hpa-not-scaling-high-cpu.md)
