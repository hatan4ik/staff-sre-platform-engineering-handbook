# Lab 1 — Kubernetes Node Repair State Machine and Fleet Circuit Breakers

## Interview scenario

A Kubernetes fleet contains several nodes with repeated runtime, disk, network, or systemd failures. A simple repair controller can restart or replace nodes, but the platform must avoid these failure modes:

- endless restart loops;
- replacing nodes with the same bad image;
- removing too much capacity from one zone;
- beginning another repair before replacement capacity is Ready;
- replacing a storage writer before traffic, storage, and identity fencing;
- allowing repair automation to become the outage.

The Staff/Principal task is to encode repair as a bounded state machine with explicit safety guards and fleet-level stop conditions.

## Safety invariants

> Repair may remove capacity only when the projected healthy fleet remains above policy, per-zone and cluster concurrency limits are satisfied, writer fencing is complete, and the failure does not look systemic.

> A repeated multi-node or bad-image pattern must stop automatic repair and escalate to fleet rollback or containment.

The lab is a deterministic Python simulation. It does not contact Kubernetes or any cloud provider.

## What the simulator models

```text
Healthy
  |
  v
Suspect
  |
  +--> one bounded restart -> Verifying
  |
  v
Degraded
  |
  +--> hold: capacity, zone, cluster, or replacement gate
  |
  +--> cordon and fence: storage writer or ambiguous ownership
  |
  +--> replace with known-good image

fleet evidence
  |
  +--> same image failure rate
  +--> same signature across zones
  +--> global repair disable
  |
  v
circuit breaker: stop automatic repair
```

The program models state and decisions only. It never executes real restart, drain, or termination commands.

## Prerequisites

- Python 3.11 or newer.
- No third-party packages.

## Run the demo

```bash
python3 node_repair.py --demo
```

Built-in scenarios:

1. **Local failure**
   - one suspect node receives one restart-and-verify decision;
   - one repeatedly degraded node is eligible for known-good replacement.

2. **Systemic failure**
   - the same bad image fails across a large fraction of its population;
   - the fleet circuit breaker opens and no repair decisions are emitted.

3. **Writer fencing**
   - a degraded storage writer lacks traffic, storage, and identity fencing;
   - the controller selects `cordon-and-fence` rather than replacement.

## Run the tests

```bash
python3 -m unittest -v test_node_repair.py
```

The test suite proves:

- a single transient failure receives one restart;
- repeated failure transitions toward replacement;
- a storage writer must be fenced before replacement;
- a fully fenced writer can be replaced;
- per-zone concurrency blocks another repair;
- replacement-readiness gating blocks the next repair;
- minimum healthy-capacity policy blocks unsafe removal;
- bad-image and cross-zone signature patterns open a circuit breaker;
- global disable stops repairs;
- state application changes only the modeled lifecycle state;
- invalid fleet definitions are rejected.

## State-machine exercise

For each real repair state, define:

| State | Entry evidence | Allowed action | Exit condition | Timeout |
|---|---|---|---|---|
| `Healthy` | normal node and workload signals | observe | anomaly | continuous |
| `Suspect` | one bounded anomaly | collect evidence, optionally restart once | verified healthy or repeated failure | short |
| `Degraded` | repeated or severe local failure | cordon, fence, plan replacement | guardrails satisfied | bounded |
| `Fenced` | scheduling, traffic, writer, and identity controls | drain or hard replace | stale ownership impossible | bounded |
| `Replacing` | known-good replacement requested | wait, verify capacity | replacement Ready and useful | bounded |
| `Verifying` | restart, reboot, or replacement completed | functional checks | healthy or quarantine | bounded |
| `Quarantined` | forensics or trust concern | no customer workloads | evidence objective complete | explicit |

Every transition should produce an auditable reason and a stop condition.

## Capacity guard exercise

Suppose a degraded node supplies 40% of modeled capacity and the two remaining nodes supply 30% each.

If policy requires at least 70% healthy capacity after removal:

```text
projected healthy capacity = 30% + 30% = 60%
```

The controller must hold the repair until replacement or additional capacity exists.

In production, capacity must include:

- allocatable CPU and memory;
- topology and scheduling constraints;
- pod IP and quota headroom;
- critical workload minimums;
- system DaemonSet overhead;
- load-balancer and dependency capacity;
- time to useful pod readiness.

## Fleet circuit-breaker exercise

Automatic repair should stop when evidence indicates a common defect.

Examples:

```text
bad image:
  failed nodes using image / total nodes using image >= threshold

cross-zone signature:
  same failure signature appears in >= N zones

replacement failure:
  new capacity does not become Ready within objective

capacity danger:
  critical workload or fleet margin falls below minimum
```

The correct response is often:

1. pause image rollout;
2. stop replacement with the suspected image;
3. preserve representative evidence;
4. restore capacity using a last-known-good image;
5. correct and requalify the image or component.

## Writer-fencing exercise

A control plane may decide a node is dead while the node still has network access and can continue writing.

Complete fencing can include:

- cordon and scheduling block;
- removal from traffic targets;
- storage detach or storage-controller fencing;
- leader-lease expiry and resource-enforced fencing token;
- identity revocation;
- network or hypervisor isolation.

The lab requires traffic, storage, and identity fencing before replacing a modeled storage writer.

Production systems should enforce stale-writer rejection at the resource using epochs, terms, fencing tokens, or equivalent authority. Control-plane belief alone is insufficient.

## Production investigation mapping

### Step 1 — Classify the failure

Separate:

- systemd unit failure;
- runtime or CNI/CSI degradation;
- node failure;
- control-plane observation delay;
- fleet or image pattern.

### Step 2 — Capture evidence

```bash
kubectl describe node <node>
kubectl get lease -n kube-node-lease <node> -o yaml
kubectl get pods -A --field-selector spec.nodeName=<node> -o wide
systemctl show <unit> -p ActiveState -p Result -p NRestarts
journalctl -u <unit> --since '-30 min'
journalctl -k --since '-30 min'
```

Also record image, kernel, runtime, node pool, zone, instance type, node age, rollout wave, disk, inode, PSI, CNI, CSI, and provider health evidence.

### Step 3 — Bound the population

Use rates and denominators:

```text
failures by image / deployed nodes or node-hours by image
failures by zone / fleet share by zone
failure signatures by runtime and kernel
```

Control for image, zone, instance family, and launch wave moving together.

### Step 4 — Apply the least destructive state transition

- known transient: one restart and functional verification;
- repeated local failure: cordon, fence, drain if possible, replace;
- terminal or untrusted node: hard fence and replace;
- fleet pattern: stop automation and roll back common change.

### Step 5 — Prove recovery

- replacement capacity is Ready and useful;
- workloads reschedule and pass business checks;
- stale writers cannot act;
- no new node repeats the failure signature;
- repair remains within zone and cluster limits;
- user-SLI burn stops.

## Common weak answers

### “Restart kubelet until it works”

This hides repeated failure and creates an unbounded repair loop.

### “Terminate every unhealthy node”

A bad image or capacity shortage can turn this into a fleet outage.

### “Cordon is fencing”

Cordon only prevents new scheduling.

### “Always drain”

A terminal node may be unable to drain. Workloads must tolerate involuntary loss and stale authority must be fenced.

### “PDB guarantees availability”

A PDB governs voluntary eviction, not dead hardware or every interruption.

### “The replacement is Ready, so recovery is complete”

Verify runtime, networking, storage, DaemonSets, workload readiness, traffic admission, and user SLI.

## Interview answer drill

> I model repair as a state machine rather than a restart script. A known transient gets one controlled restart after evidence capture; repeated failure moves to cordon and full fencing, then drain or replacement. Before removing capacity I check cluster and per-zone repair limits, projected healthy capacity, replacement readiness, and stateful writer fencing. If the same image or signature fails across a meaningful fleet population, a circuit breaker stops auto-repair and the response becomes image rollback and fleet containment.

## Related material

- [`core/kubernetes/node-lifecycle/failure-fencing-repair.md`](../../../core/kubernetes/node-lifecycle/failure-fencing-repair.md)
- [`core/kubernetes/runtime-debugging.md`](../../../core/kubernetes/runtime-debugging.md)
- [`core/kubernetes/autoscaling/control-loops-capacity-realization.md`](../../../core/kubernetes/autoscaling/control-loops-capacity-realization.md)
- [`core/distributed-systems/03-replication-quorum-consensus.md`](../../../core/distributed-systems/03-replication-quorum-consensus.md)
- [`core/distributed-systems/05-time-leases-and-fencing.md`](../../../core/distributed-systems/05-time-leases-and-fencing.md)
