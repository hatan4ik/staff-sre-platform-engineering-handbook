# Kubernetes Node Failure Detection, Fencing, Drain, Repair, and Replacement

## Interview scenario

A subset of Kubernetes nodes intermittently reports kubelet, container-runtime, network, storage, or systemd failures. Some nodes remain `Ready`, some become `NotReady`, and automated restarts appear to help temporarily. The platform must protect workloads, preserve evidence, avoid fleet-wide repair storms, and restore capacity safely.

The Staff/Principal task is not to propose “restart kubelet” or “replace the node.” It is to classify the failure, identify which authority is still functioning, fence ambiguous ownership, choose the least destructive repair state, and design automation that stops when the pattern indicates a systemic fleet defect.

---

## 1. Ninety-second Staff/Principal answer

> I separate a process or systemd-unit failure from a node failure, a node failure from a control-plane observation delay, and a single-node event from a fleet pattern. I correlate Kubernetes conditions and leases with systemd state, journal and kernel evidence, container-runtime and CNI/CSI health, disk and inode pressure, networking, hardware or VM signals, node image, zone, instance type, and rollout history.
>
> I model repair as a bounded state machine: healthy, suspect, degraded, cordoned or fenced, drained when possible, then rebooted or replaced, followed by verification. A known transient service failure may receive one controlled restart after evidence capture. Repeated or critical failure transitions to cordon and fencing rather than an infinite restart loop.
>
> Fencing is broader than cordon. I remove traffic eligibility, prevent new scheduling, ensure a failed node cannot remain a storage writer or leader, and revoke or isolate node identity when required. I prefer graceful drain when the node can cooperate and spare capacity exists, but a terminal node may require hard replacement; a PDB governs voluntary eviction and cannot resurrect failed hardware.
>
> The repair controller has per-zone and cluster-wide concurrency limits, replacement-capacity checks, bad-image and multi-zone circuit breakers, a global disable switch, audit events, and last-known-good rollback. Success means capacity is restored faster than automation removes it, stateful writer fencing is proven, and a systemic image or platform defect stops the repair loop automatically.

### Fifteen-second version

> Classify the failure, preserve evidence, fence ambiguous ownership, repair through a bounded state machine, and stop automation when the fleet—not one node—is unhealthy.

---

## 2. Failure taxonomy

### Unit or process failure

Examples:

- `kubelet` stopped.
- Container runtime unhealthy.
- CNI agent failed.
- CSI node plugin failed.
- Log or security agent failed.
- Time synchronization service failed.

The node may still be reachable and repairable.

### Node-service degradation

Examples:

- Runtime operations time out.
- Image filesystem is full.
- CNI cannot program new workloads.
- DNS or route failure affects only the node.
- Kubelet posts stale status.
- One storage mount hangs.

The node may still report `Ready` while one workload cohort fails.

### Node failure

Examples:

- VM or physical host stopped.
- Kernel panic.
- Network partition.
- Root filesystem unavailable.
- Kubelet and runtime are both lost.
- Node is compromised or cannot be trusted.

### Control-plane observation failure

Examples:

- API server cannot receive lease updates.
- Controller backlog delays taints or evictions.
- Network path between node and control plane fails.
- Admission or API latency slows repair actions.

The physical node may still be running workloads while the control plane considers it unavailable.

### Fleet or image failure

Examples:

- New kernel or AMI causes runtime crash.
- Certificate or bootstrap configuration expires across a node pool.
- One instance family has a firmware issue.
- One CNI version corrupts state.
- A common disk-size change causes image filesystem exhaustion.

Treating every affected node independently can amplify the incident.

---

## 3. Unit failure is not automatically node failure

A node is a collection of independently failing subsystems:

```text
systemd and host services
      |
      +--> kubelet
      +--> container runtime
      +--> CNI and network datapath
      +--> CSI and mount helpers
      +--> DNS and time
      +--> logging, security, and monitoring agents
      |
      v
kernel, filesystems, devices, firmware, hypervisor, network
```

A service can be `active` while functionally broken. A node can be `Ready` while:

- Image pulls fail.
- New pods cannot obtain IP addresses.
- Existing pods cannot reach one dependency.
- Volume operations hang.
- One runtime snapshotter is corrupted.
- A local disk or inode pool is exhausted.

Verification must test the function represented by the service, not only its unit state.

---

## 4. Evidence model

### Kubernetes evidence

```bash
kubectl get node <node> -o yaml
kubectl describe node <node>
kubectl get lease -n kube-node-lease <node> -o yaml
kubectl get events --field-selector involvedObject.kind=Node,involvedObject.name=<node> --sort-by=.lastTimestamp
kubectl get pods -A --field-selector spec.nodeName=<node> -o wide
```

Record:

- `Ready`, `MemoryPressure`, `DiskPressure`, and `PIDPressure`.
- Lease renewal time.
- Taints and unschedulable state.
- Allocatable versus requested resources.
- Pods and workload importance.
- Repeated events.
- Owner node pool or lifecycle controller.

Events are ephemeral and may be rate-limited. Centralize important node and repair events.

### systemd evidence

```bash
systemctl status <unit> --no-pager
systemctl show <unit> \
  -p ActiveState -p SubState -p Result \
  -p ExecMainCode -p ExecMainStatus \
  -p NRestarts -p ActiveEnterTimestamp
journalctl -u <unit> --since '-30 min' --no-pager
systemctl list-units --state=failed
```

Inspect:

- Exit status and signal.
- Restart count and interval.
- Start-limit state.
- Dependencies and ordering.
- Environment and drop-ins.
- Timeout and watchdog behavior.
- Resource-control settings.

### Kernel and host evidence

```bash
journalctl -k --since '-30 min' --no-pager
dmesg -T | tail -n 300
cat /proc/pressure/cpu
cat /proc/pressure/memory
cat /proc/pressure/io
df -hT
df -i
findmnt
free -m
vmstat 1
iostat -xz 1
ss -s
ip -s link
```

Look for:

- OOM and allocation failure.
- I/O errors or resets.
- Filesystem read-only transition.
- Hung tasks and blocked mounts.
- Kernel panic or machine check.
- NIC drops, retransmission, and softirq pressure.
- Clock instability.
- Device or hypervisor error.

### Runtime and workload evidence

Inspect:

- Container-runtime journal.
- Image filesystem and snapshotter state.
- Pod sandbox creation latency.
- Image pull and unpack errors.
- CNI ADD/DEL errors.
- CSI node-stage, mount, and unmount errors.
- DaemonSet health.
- Node-local DNS behavior.
- Canary pod connectivity.

### Platform evidence

Record:

- Node image and kernel version.
- Bootstrap and launch-template version.
- Instance or machine family.
- Zone and subnet.
- Capacity type.
- Recent upgrade, image, configuration, or security change.
- VM console or serial output.
- Health and lifecycle events from the infrastructure provider.

---

## 5. Correlate the population

Build a matrix:

| Dimension | Compare |
|---|---|
| Image | image ID, kernel, runtime, bootstrap |
| Hardware | instance family, CPU architecture, disk type |
| Topology | region, zone, rack, subnet |
| Lifecycle | age, launch wave, node pool, autoscaler |
| Workload | DaemonSets, tenant, storage, traffic class |
| Failure | unit, exit code, kernel signature, condition |
| Time | before/after rollout, repeated interval |

Use failure rates and denominators.

Example:

```text
image A:  2 failures / 10,000 node-hours
image B: 80 failures / 2,000 node-hours
```

This is stronger than saying most failing nodes use image B without knowing deployment share.

Control for confounding. If image B exists only in one zone and instance family, image, zone, and hardware are not independently established.

---

## 6. Repair state machine

```text
Healthy
  |
  | anomaly or repeated signal
  v
Suspect
  |
  | evidence threshold reached
  v
Degraded
  |\
  | \ known transient + one bounded restart
  |  +-----------------------------------> Verify
  |                                          |
  |                                          +--> Healthy
  |
  +--> Cordon / Fence
          |
          +--> cooperative node + spare capacity --> Drain
          |                                            |
          |                                            +--> Reboot or Replace
          |
          +--> terminal or untrusted node ------------> Hard Replace
                                                        |
                                                        v
                                                      Verify
```

Every transition should define:

- Triggering evidence.
- Maximum time in state.
- Allowed actions.
- Evidence to preserve.
- Rollback or stop condition.
- Audit event.
- Verification requirement.

A single log line is rarely enough for destructive repair.

---

## 7. Suspect state

Use one or more:

- Repetition threshold.
- Duration threshold.
- Multiple independent signals.
- Workload impact.
- Known failure signature.
- Correlation with a rollout or population.

Examples:

```text
kubelet inactive once for 5 seconds
  -> suspect, inspect

runtime restarts three times in 10 minutes
  -> degraded, cordon and preserve evidence

node stops renewing lease and VM health is failed
  -> terminal candidate, fence and replace
```

Do not flap between states. Use hysteresis and a bounded waiting period.

---

## 8. One controlled restart

Appropriate only when:

- Failure signature is understood and known to be transient.
- Restart is idempotent.
- Evidence has been captured or restart will not destroy it.
- Customer capacity remains safe.
- This is not a repeated failure.
- Unit dependencies and ordering are correct.

```bash
systemctl reset-failed <unit>
systemctl restart <unit>
systemctl is-active <unit>
```

Then verify function:

- Kubelet posts status and node reaches expected condition.
- Runtime can create, start, stop, and remove a disposable container.
- CNI can create a pod with expected connectivity.
- CSI can mount and unmount a test volume in a disposable environment.
- Node-local DNS resolves representative names.

Repeated restart is not healing. It is an unstable control loop and should escalate.

---

## 9. Cordon

```bash
kubectl cordon <node>
```

Cordon prevents new scheduling. It does not:

- Remove existing pods.
- Stop application traffic.
- Revoke leases or writer authority.
- Detach volumes.
- Isolate a compromised node.

Use cordon early when a node is suspected of harming new workloads, but do not call it complete fencing.

---

## 10. Fencing

Fencing prevents an ambiguous or failed participant from continuing to act as an owner.

### Scheduling fencing

- Cordon.
- Add a taint where appropriate.
- Stop lifecycle controllers from placing new work.

### Traffic fencing

- Remove or fail targets from load balancers.
- Ensure endpoints are no longer eligible.
- Stop node-local proxies or isolate the path when necessary.
- Confirm long-lived connections drain or fail safely.

### Storage and writer fencing

- Confirm volume detach or storage-controller fencing.
- Prevent simultaneous read-write attachment.
- Revoke or expire leader lease.
- Use fencing tokens or epochs at the resource.
- Verify the old node cannot continue writes after replacement starts.

### Identity fencing

- Revoke node-specific credentials where applicable.
- Prevent an untrusted node from obtaining new workload credentials.
- Remove it from attestation or trust inventory.

### Network fencing

For compromised or split-brain nodes:

- Isolate at security group, firewall, switch, or hypervisor boundary.
- Preserve a separate forensics path when authorized.

Hard termination without writer fencing can create duplicate ownership, stale writes, or split brain.

---

## 11. Drain

```bash
kubectl drain <node> \
  --ignore-daemonsets \
  --delete-emptydir-data \
  --timeout=15m
```

Before drain verify:

- Spare capacity exists or replacement is already Ready.
- PDBs and topology constraints are understood.
- Stateful replica health is safe.
- Local data and `emptyDir` consequences are accepted.
- Jobs are idempotent or checkpointed.
- Graceful termination and connection drain are tested.
- Volume detach and reattach can complete.

A drain timeout is evidence. Identify whether it is caused by:

- PDB.
- Finalizer.
- Stuck termination.
- Long grace period.
- CSI or volume detach.
- Unmanaged pod.
- Admission or API failure.
- Insufficient replacement capacity.

Do not routinely override PDBs merely to make automation complete.

---

## 12. Reboot versus replace

### Reboot

Use for a known repairable host state when:

- Node identity and image remain trusted.
- Reboot is faster than replacement.
- Volatile evidence is preserved.
- Failure is not expected to repeat immediately.
- Storage and workload semantics allow it.

Risks:

- Repeated defect returns.
- Boot fails.
- Local state changes.
- The node rejoins before health is verified.

Keep the node cordoned until functional verification passes.

### Replace

Prefer replacement when:

- Image or runtime state is suspect.
- Immutable infrastructure is the operating model.
- Failure repeats.
- Node is compromised.
- Repair would require interactive mutation.
- Replacement is safer and faster.

Replacement should use a known-good image and configuration, not recreate the same suspected defect blindly.

---

## 13. Hard replacement

Use when:

- Kubelet or API path is lost.
- Runtime is irrecoverable.
- Node is isolated, terminal, or untrusted.
- Graceful drain cannot complete.
- Workloads are designed for involuntary node loss.
- Traffic, storage, writer, and identity fencing are complete or the failure mode guarantees the node cannot act.

Risks:

- Abrupt connection loss.
- Duplicate job execution.
- Volume attach delay.
- Quorum reduction.
- Data loss from local state.
- Termination grace not honored.

These are workload-architecture responsibilities. A platform cannot guarantee every failed node will participate in graceful drain.

---

## 14. PDBs and involuntary failure

PodDisruptionBudgets constrain voluntary evictions.

They do not prevent:

- Node crash.
- Network partition.
- Kernel panic.
- Hypervisor or VM termination.
- OOM kill.
- Storage failure.
- Every interruption event.

A resilient workload combines:

- Replicas.
- Topology spread.
- Anti-affinity where justified.
- PDBs.
- Capacity headroom.
- Graceful shutdown.
- State-machine and idempotency design.
- Involuntary-node-loss testing.

Correct framing:

> If a node is truly dead, its capacity is already lost. Restore replicas elsewhere and fence stale ownership; the PDB guides voluntary maintenance but cannot revive the node.

---

## 15. Repair automation guardrails

Every repair controller needs:

- Maximum concurrent repairs.
- Maximum repairs per interval.
- Per-zone and per-node-pool limits.
- Minimum healthy-fleet and spare-capacity threshold.
- Condition-specific observation period.
- Maximum time in each state.
- Replacement-success prerequisite before more removals.
- Exclusion or quarantine label.
- Stateful and storage rules.
- Bad-image, multi-zone, and multi-condition circuit breakers.
- Global disable switch.
- Audit event and notification.
- Rollout correlation.
- Last-known-good replacement policy.

Example:

```text
normal repair budget:
  max 1 node per zone
  max 3 cluster-wide
  require one replacement Ready before next removal

stop automatically when:
  >10% of one node pool is unhealthy
  more than one zone shows the same new signature
  replacement provisioning fails
  the same image repeats the failure
  critical workload capacity margin is below threshold
  storage fencing cannot be proven
```

The repair mechanism must never become the largest source of disruption.

---

## 16. One lifecycle owner

Possible lifecycle owners:

- Managed node group or cloud node manager.
- Karpenter-like dynamic provisioner.
- Cluster Autoscaler plus node-group manager.
- Custom repair controller.
- Bare-metal fleet manager.

Clearly assign ownership of:

- Provisioning.
- Health assessment.
- Cordon and drain.
- Replacement.
- Image rollout.
- Consolidation.
- Interruption handling.

Two controllers independently terminating or replacing the same nodes can oscillate or exceed disruption budgets.

---

## 17. Bad image or rollout containment

Scenario:

```text
new node image rollout
  -> runtime metadata growth
  -> disk or inode exhaustion
  -> runtime restart
  -> temporary recovery
  -> repeated failure
```

Response:

1. Pause image rollout.
2. Stop auto-repair if replacement would use the same image.
3. Freeze unrelated node changes.
4. Bound affected image, instance type, zone, and launch wave.
5. Quarantine representative evidence nodes.
6. Replace customer-serving nodes with last-known-good image under repair limits.
7. Verify capacity and workload SLOs.
8. Correct image construction and qualification.

Permanent controls:

- Disk and inode soak tests.
- Image-pull and snapshotter churn.
- Runtime and CNI/CSI startup tests.
- Reboot and cold-start tests.
- Node-problem signatures as promotion blockers.
- Canary duration that covers the failure mechanism.
- Automated rollback to last known good.

---

## 18. Verification after repair

A repaired node must prove more than `Ready`.

Verify:

- Lease and status updates.
- Runtime operations.
- Pod sandbox creation.
- CNI connectivity and DNS.
- Representative egress.
- CSI mount behavior where applicable.
- DaemonSets healthy.
- Image filesystem and inode headroom.
- No repeated unit restart.
- No kernel or hardware warning.
- Time synchronization.
- Workload SLI and target health.

Only then uncordon:

```bash
kubectl uncordon <node>
```

For immutable fleets, a repaired old node may remain quarantined and be replaced instead of returned to service.

---

## 19. Observability and SLOs

### Host and unit signals

- Active and failed state.
- Restart count and exit status.
- Journal error rate.
- CPU, memory, and I/O pressure.
- Disk, inode, and image filesystem usage.
- Kernel, device, and network errors.
- Runtime operation latency.

### Kubernetes signals

- Node conditions and lease age.
- Time `NotReady` or `Unknown`.
- Pending pods and reason.
- Evictions.
- Drain duration and blocked reason.
- Pod rescheduling and readiness time.
- Endpoint and target-health delay.
- Stateful quorum and volume attach state.

### Repair signals

- Attempts by reason and state transition.
- Restart, reboot, and replacement success.
- Time to cordon and fence.
- Time to replacement Ready.
- Concurrent repairs by zone and node pool.
- Circuit-breaker and global-stop events.
- Replacement image and configuration.

### Product signals

- Capacity margin.
- Error and latency by node pool, image, and zone.
- Critical workload replicas and quorum.
- User-SLI burn during repair.

Example objectives:

- Known transient unit failure recovers within the documented target after one restart.
- Repeated failure transitions to replacement rather than infinite restart.
- Terminal node traffic and writer authority are fenced within target.
- Replacement capacity becomes useful within the node-provisioning objective.
- Repair never exceeds per-zone or cluster limits.
- One-node and one-zone failure remain within workload SLO.

---

## 20. Incident workflow

### Step 1 — Protect capacity

- Pause node and image rollouts.
- Freeze disruptive consolidation or repair if systemic pattern is suspected.
- Maintain system and critical workload capacity.
- Avoid replacing nodes with the suspected image.

### Step 2 — Bound the population

Compare:

- Image and kernel.
- Runtime and CNI/CSI version.
- Zone and subnet.
- Instance family and disk.
- Launch wave and node age.
- Failure signature.

### Step 3 — Preserve evidence

- Journal and kernel logs.
- Runtime and plugin logs.
- PSI, disk, inode, and filesystem state.
- VM console or serial output.
- Node and Kubernetes events.
- Image and launch metadata.
- Representative pod and network evidence.

### Step 4 — Select state transition

- Known one-time transient: one restart, verify.
- Repeated local issue: cordon, fence, drain if possible, replace.
- Terminal or untrusted: hard fence and replace.
- Fleet pattern: stop automation and roll back image or configuration.

### Step 5 — Prove recovery

- Replacement useful capacity.
- Affected workload rescheduled.
- Stateful ownership safe.
- User SLI and error-budget burn normal.
- No new nodes repeat the signature.

---

## 21. Common weak answers

### “Restart the unit forever”

This hides a systemic defect and converts repair into recurring disruption.

### “Always drain before termination”

Graceful drain is preferred when the node can cooperate. Terminal nodes require involuntary-loss design and fencing.

### “PDBs guarantee availability”

They constrain voluntary eviction only.

### “Terminate every unhealthy node immediately”

Without capacity checks and fleet circuit breakers, repair can create a larger outage.

### “SSH and patch the node”

Interactive access can collect evidence. Durable correction belongs in immutable image, configuration, or managed component.

### “Node Ready means healthy”

The runtime, network, storage, or one workload cohort may still be broken.

### “Cordon is fencing”

Cordon only blocks new scheduling. It does not stop traffic, writers, leases, credentials, or network access.

---

## 22. Adversarial interview questions

### Why not just reboot?

A reboot can recover some host states but destroys volatile evidence and may repeat. Use it only for a classified, trusted, repairable condition.

### What if drain is blocked by a PDB?

If the node is cooperative, create capacity and wait or repair the workload constraint. If the node is terminal, restore replicas elsewhere and fence stale ownership; the failed capacity is already gone.

### What if replacement capacity is unavailable?

Stop further removals, preserve remaining capacity, use diversified approved supply, relax noncritical placement, and escalate quota or infrastructure capacity. Do not consume the fleet.

### How do you preserve a failing node?

Quarantine one representative node, remove it from traffic and scheduling, fence storage and identity, collect evidence, and prevent automated deletion until the evidence objective is met.

### When is a process restart safe?

When the signature is known, restart is idempotent, evidence is preserved, customer capacity is safe, and repeat failure escalates.

### What if the node is partitioned and still serving writes?

Use resource-enforced fencing tokens, lease epochs, storage fencing, and network isolation. Control-plane belief alone cannot guarantee the old writer stopped.

### How do you stop a bad-image repair loop?

Correlate failure with image or launch wave, trip a fleet circuit breaker, pause rollout and repair, and replace with the last-known-good image.

---

## 23. Staff/Principal checklist

A strong answer includes:

- Unit versus node versus observation versus fleet failure.
- Kubernetes, systemd, kernel, runtime, network, storage, and platform evidence.
- Population correlation and denominators.
- Bounded repair state machine.
- One controlled restart for known transient failure.
- Cordon versus complete fencing.
- Drain preconditions and PDB limits.
- Reboot versus immutable replacement.
- Traffic, storage, writer, identity, and network fencing.
- Per-zone and fleet repair limits.
- Bad-image and multi-zone circuit breakers.
- Functional verification and user-SLI recovery.

---

## Primary references

- [Kubernetes monitoring node health](https://kubernetes.io/docs/tasks/debug/debug-cluster/monitor-node-health/)
- [Kubernetes node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Kubernetes disruptions and PodDisruptionBudgets](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [Kubernetes node status](https://kubernetes.io/docs/reference/node/node-status/)
- [systemd.service manual](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
