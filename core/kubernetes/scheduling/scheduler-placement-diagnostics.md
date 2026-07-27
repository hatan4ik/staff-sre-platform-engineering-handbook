# Kubernetes Scheduler Internals and Placement Diagnostics

This chapter is the canonical foundation for Kubernetes scheduling, placement constraints, unschedulable workloads, preemption, topology, and scheduler-scale incidents.

## Interview answer in 90 seconds

> I treat scheduling as a constraint-solving and capacity-realization pipeline. The scheduler watches unscheduled pods, filters nodes that violate hard requirements, scores feasible nodes, reserves and binds the selected placement, while external controllers may still need to create nodes or attach storage before the pod becomes usable. For an incident I separate “no feasible node” from “feasible capacity exists but the scheduler or node-supply loop is slow.” I inspect pod events and scheduler reasons, then classify constraints: requests versus allocatable capacity, taints and tolerations, node affinity, topology spread, anti-affinity, volume topology, device resources, PodDisruptionBudgets, quotas, and nominated preemption. I compare affected and healthy workload cohorts and confirm whether pending pods are blocked by one impossible constraint or by real shortage. Mitigation is narrow: correct an invalid constraint, restore a missing label or toleration, add compatible capacity, reduce requests only with evidence, or pause a rollout. Recovery is proven when pending age drains, placement satisfies failure-domain policy, and application SLIs recover.

## Scheduling pipeline

```text
pod created without nodeName
          |
          v
scheduler queue
  active / backoff / unschedulable
          |
          v
pre-filter and filter plugins
          |
          v
feasible node set
          |
          v
score and normalize
          |
          v
reserve / permit / pre-bind
          |
          v
bind pod to node
          |
          v
kubelet, runtime, CNI, CSI, image pull
          |
          v
pod ready and serving
```

A successful bind does not prove the pod will start. Scheduling latency and pod-start latency must be measured separately.

## The scheduler is not an autoscaler

The scheduler places pods on existing nodes. A node autoscaler observes unschedulable pods and may provision compatible nodes.

The end-to-end path is:

```text
pod pending
  -> scheduler explains no fit
  -> autoscaler evaluates a compatible node class
  -> infrastructure capacity becomes available
  -> node boots and registers
  -> scheduler binds
  -> pod starts
```

A pod can remain pending even when “more nodes” exist if those nodes do not satisfy architecture, zone, taint, volume, device, or policy requirements.

## Hard and soft constraints

### Hard constraints

These remove nodes from the feasible set:

- CPU, memory, ephemeral storage, PID, and extended-resource requests;
- node selector and required node affinity;
- taints without matching tolerations;
- required pod affinity or anti-affinity;
- topology-spread `DoNotSchedule` constraints;
- volume node affinity and zone topology;
- host ports;
- device-plugin resources;
- maximum pods or networking address capacity;
- scheduling gates;
- namespace quota preventing pod creation before scheduling.

### Soft preferences

These influence scoring but should not make every node infeasible:

- preferred node affinity;
- preferred pod anti-affinity;
- topology-spread `ScheduleAnyway` behavior;
- image locality;
- resource balancing;
- custom scheduler plugins.

A common failure is expressing a preference as a hard rule across a fleet that cannot always satisfy it.

## Requests and allocatable capacity

The scheduler uses declared requests and node allocatable resources, not current observed utilization.

This is intentional: placement must reserve capacity before runtime consumption is known.

Investigate:

- container and init-container requests;
- pod overhead;
- node allocatable after kube/system reservations;
- DaemonSet consumption;
- extended resources;
- ephemeral-storage requests;
- huge pages;
- max pods and CNI address availability;
- recently changed defaults or LimitRanges.

Low CPU utilization does not prove the scheduler can fit another pod if requests reserve the capacity.

## Init containers and sidecars

For init containers, effective scheduling requests follow maximum-at-a-time semantics rather than simply summing every init container with every application container.

Persistent sidecars and evolving Kubernetes lifecycle semantics require version-aware testing. Validate the rendered pod resource requirements rather than relying on an old mental model.

## Taints and tolerations

Taints express node-side exclusion. Tolerations permit scheduling but do not attract the pod to that node.

Common incidents:

- a new taint applied fleet-wide without workload tolerations;
- a toleration matches key but not effect;
- system workloads tolerate a dedicated pool unintentionally;
- autoscaler-created nodes have a startup taint that is never removed;
- node-condition taints persist because the underlying condition is unresolved.

## Node affinity

Use stable labels owned by the platform.

Risky patterns:

- workloads depend on manually applied labels;
- a label key changes across node-image versions;
- architecture or instance-family affinity is narrower than needed;
- required affinity references a value unavailable in a recovery region;
- tenant-provided labels influence privileged placement.

Protect security-sensitive label keys from kubelet self-modification where appropriate.

## Pod affinity and anti-affinity

Anti-affinity can improve resilience but is expensive and can make rolling updates impossible.

Review:

- required versus preferred behavior;
- topology key;
- label selector scope;
- namespaces included;
- replicas versus available topology domains;
- deployment surge settings;
- interaction with PodDisruptionBudgets;
- scheduler performance at scale.

If three replicas require distinct zones but only two eligible zones or node pools exist, the third pod is correctly unschedulable.

## Topology-spread constraints

Topology spread provides more explicit skew control than broad anti-affinity.

Key fields:

- topology key;
- maximum skew;
- when unsatisfiable;
- label selector;
- minimum domains;
- node affinity and taint policy;
- match-label behavior where supported.

Validate behavior during one-zone loss, rolling updates, and partial capacity shortages. A strict spread policy may intentionally reject placement rather than overload surviving domains.

## Volumes and topology

A pod may be schedulable only where its volume can attach.

Potential blockers:

- persistent volume node affinity;
- storage class topology;
- delayed binding behavior;
- zone mismatch;
- attach limits;
- stale attachment;
- multi-attach protection;
- local persistent volume ownership;
- recovery-region data availability.

The scheduler, external provisioner, attach/detach controller, and CSI drivers participate in the path. Inspect all of them.

## Extended resources and devices

GPUs, accelerators, SR-IOV interfaces, and other device-plugin resources require:

- advertised allocatable resource;
- compatible node class;
- correct driver and device-plugin state;
- topology awareness;
- workload request;
- rollout and upgrade coordination.

A node can be Ready while the requested device resource is absent.

## Preemption

Preemption may nominate a node and evict lower-priority pods so a higher-priority pod can fit.

Preemption does not solve:

- impossible affinity;
- missing tolerations;
- volume topology mismatch;
- absent extended resources;
- every node being too small;
- non-preemptible system reservations;
- PodDisruptionBudget constraints in some cases.

Design priority classes carefully. Overuse can starve ordinary services or create eviction loops.

## Scheduler queues and backoff

Pods can reside in:

- active queue;
- backoff queue;
- unschedulable pool.

Events that change cluster state can requeue pods. Controller or webhook churn can produce repeated attempts.

Monitor:

- scheduling attempts;
- scheduling latency;
- pending age;
- unschedulable reasons;
- queue depth;
- plugin execution time;
- binding latency;
- scheduler leader-election stability;
- API-server and watch freshness.

## Incident workflow

### 1. State impact

Examples:

- deployment cannot progress;
- autoscaling creates nodes but pods stay pending;
- one zone or node class is unavailable;
- critical services cannot recover after node failure;
- batch workloads consume topology needed by interactive services;
- rollout surge conflicts with anti-affinity or disruption budgets.

### 2. Inspect the pod contract

```bash
kubectl get pod <pod> -n <namespace> -o yaml
kubectl describe pod <pod> -n <namespace>
kubectl get events -n <namespace> --sort-by=.lastTimestamp
kubectl get resourcequota,limitrange -n <namespace>
```

Capture:

- requests and limits;
- scheduler name;
- priority class;
- selectors and affinity;
- tolerations;
- topology spread;
- volumes and storage class;
- scheduling gates;
- event reasons.

### 3. Inspect candidate nodes

```bash
kubectl get nodes -o wide --show-labels
kubectl describe node <node>
kubectl get nodes -L topology.kubernetes.io/zone,kubernetes.io/arch,node.kubernetes.io/instance-type
kubectl get daemonsets -A
```

Compare allocatable resources, taints, labels, node conditions, pod count, and attached-resource limits.

### 4. Classify the blocker

Ask:

- Is there any feasible node now?
- Could a supported node class satisfy the pod?
- Is the constraint intentional?
- Is capacity real or only theoretically scalable?
- Did the failure begin after a workload, policy, node-image, or autoscaler change?
- Is one workload or the whole cluster affected?

### 5. Stabilize safely

Preferred order:

1. pause the rollout creating additional pending pods;
2. correct an accidental selector, affinity, toleration, request, or topology rule;
3. restore missing compatible capacity;
4. protect critical workloads with intentional priority and reserved capacity;
5. move optional workloads away from constrained pools;
6. resolve volume or device topology;
7. use bounded preemption only when policy supports it;
8. verify placement and user-facing recovery.

Do not delete random running pods to “make room” without understanding priority, disruption, and replacement behavior.

## Scheduler SLOs

Track:

- scheduling attempt success;
- p50, p95, and p99 scheduling latency;
- oldest pending pod age;
- unschedulable pod count by reason;
- percentage of pending pods with a compatible provisionable node class;
- preemption attempts and victim count;
- topology-skew violations;
- bind-to-ready latency;
- autoscaler request-to-node-ready latency;
- critical workload recovery time after node or zone loss.

## Scale and performance

Scheduler cost grows with pods, nodes, and constraint complexity.

Risk factors:

- broad inter-pod affinity/anti-affinity;
- expensive custom plugins;
- very high event churn;
- large numbers of unschedulable pods;
- frequent node and label changes;
- multiple schedulers with overlapping ownership;
- API-server latency and watch reconnects.

Benchmark realistic constraints, not just an empty cluster with simple pods.

## Weak answers to avoid

- “Add more nodes.”
- “CPU is low, so the scheduler is broken.”
- “Remove requests.”
- “Delete pods until it fits.”
- “Preemption will fix it.”
- “Use required anti-affinity for every replica.”
- “The autoscaler should know what to do” without compatible node classes and constraints.

## Adversarial follow-ups

### Why does a pod stay pending after a new node joins?

The node may not satisfy labels, taints, architecture, zone, volume, device, max-pod, or resource requirements. The node may also still have startup taints or missing CNI/device capacity.

### Why can reducing requests be dangerous?

Requests drive placement and CPU/memory protection. Artificially low requests increase overcommit, throttling, eviction, and overload risk. Right-size from measured usage and tail behavior.

### When is strict topology spread correct even if pods remain pending?

When concentrating replicas would violate the service's failure-domain objective or create unsafe capacity imbalance. The system should surface the capacity shortfall rather than silently weaken the invariant.

### What proves recovery?

Pending age and unschedulable reasons drain, pods land on intended failure domains, bind-to-ready latency normalizes, and application or control-plane SLIs recover.

## Principal-level review checklist

- constraints express real availability and security requirements;
- platform-owned labels are stable and protected;
- requests reflect measured capacity needs;
- topology rules survive rollout and zone-loss scenarios;
- storage and device topology are included in capacity planning;
- priority and preemption cannot starve the fleet;
- autoscaler node classes match workload constraints;
- scheduler and capacity-realization SLOs are measured end to end;
- game days cover impossible constraints, zone loss, and rollout deadlock.
