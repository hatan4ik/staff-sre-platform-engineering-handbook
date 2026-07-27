# Kubernetes Runtime Debugging: Restarts, OOM, Evictions, and Healthy Probes

## Interview scenario

A Kubernetes workload repeatedly restarts or disappears while readiness and liveness probes appear healthy. Some dashboards show normal nodes and low average utilization. The platform must identify exactly what restarted, who initiated the termination, preserve short-lived evidence, and restore the business transaction safely.

The Staff/Principal task is not to restart the Deployment or increase memory blindly. It is to classify the lifecycle event, identify the affected container or owner, correlate process, cgroup, kubelet, runtime, node, controller, configuration, and dependency evidence, and prove the failed path—not merely the health endpoint—has recovered.

---

## 1. Ninety-second Staff/Principal answer

> I first verify what “restart” means. A container can restart inside the same pod, a controller can replace the pod, a node can evict or lose it, and one sidecar can restart while the main application remains ready. I compare pod UID, owner, creation time, node, container restart counts, current state, and last terminated state.
>
> For a container restart I capture termination reason, exit code, signal, timestamps, previous logs, Kubernetes events, image digest, command, arguments, and PID 1 behavior before another restart overwrites the evidence. Healthy probes do not exclude an OOM kill, process exit between probe intervals, fatal background thread, wrapper-script completion, sidecar failure, credential refresh failure, or deliberate controller termination.
>
> I correlate the timestamp with cgroup memory and OOM events, CPU throttling and watchdogs, node pressure and evictions, kubelet and container-runtime logs, rollout and GitOps history, node disruption, configuration and Secret changes, identity failures, dependency timeouts, and application crash evidence. Then I mitigate by cause: roll back the image, correct entrypoint or signal handling, right-size or fix a memory leak, restore a dependency, stop disruptive automation, replace a bad node, or move finite work to a Job.
>
> Recovery requires restart rate to stop, the intended process to remain alive across the observation window, previous backlog to drain, and the real user transaction and SLO to recover.

### Fifteen-second version

> Distinguish container restart from pod replacement, capture the last termination and previous logs, identify the terminating authority, and verify the business path—not the probe.

---

## 2. Lifecycle taxonomy

### Container restart in the same pod

Evidence:

- Pod UID remains the same.
- One container's `restartCount` increases.
- `lastState.terminated` is populated.
- `CrashLoopBackOff` may appear.

### Pod replacement

Evidence:

- Pod name or UID changes.
- Container restart count may remain zero.
- Deployment, StatefulSet, Job, eviction, drain, or another controller creates a new pod.

### Node-driven rescheduling

Evidence:

- Multiple pods move together.
- Node becomes `NotReady`, drains, terminates, or is consolidated.
- Node lifecycle, autoscaling, interruption, or maintenance events exist.

### Sidecar-only restart

Evidence:

- One sidecar restart count increases.
- Main application container remains running.
- Pod may still be Ready depending on probes and readiness gates.

### Init-container retry

Evidence:

- Application containers have not started.
- Init-container state shows repeated termination or waiting.
- Pod remains `Init:*`.

### Ephemeral-container activity

Debug containers can be added without changing application restart counts. Record their presence to avoid confusing investigation artifacts with workload behavior.

---

## 3. Capture exact state

```bash
kubectl get pod -n <namespace> <pod> -o wide
kubectl describe pod -n <namespace> <pod>
kubectl get pod -n <namespace> <pod> -o yaml
```

Compact status:

```bash
kubectl get pod -n <namespace> <pod> \
  -o jsonpath='{range .status.initContainerStatuses[*]}INIT {.name}{" restart="}{.restartCount}{" current="}{.state}{" last="}{.lastState}{"\n"}{end}{range .status.containerStatuses[*]}APP {.name}{" restart="}{.restartCount}{" current="}{.state}{" last="}{.lastState}{"\n"}{end}'
```

Record:

- Pod UID and creation timestamp.
- Owner ReplicaSet, StatefulSet, Job, or custom controller.
- Node, zone, node pool, and image.
- Container and init-container names.
- Image digest.
- Restart count.
- Current state and waiting reason.
- Last termination reason.
- Exit code and signal.
- Start and finish timestamps.
- Ready state and readiness gates.
- QoS class.
- Resource requests and limits.
- Restart policy and workload controller.

Do not rely on the pod phase alone.

---

## 4. Preserve previous logs immediately

```bash
kubectl logs -n <namespace> <pod> \
  -c <container> --previous --timestamps
```

Current logs:

```bash
kubectl logs -n <namespace> <pod> \
  -c <container> --timestamps --since=30m
```

All current containers:

```bash
kubectl logs -n <namespace> <pod> \
  --all-containers=true --prefix --timestamps
```

Important limitation:

- `--previous` commonly exposes only the immediately previous container instance.
- Another restart can replace that evidence.
- Pod replacement can remove node-local logs.
- Logging agents may not flush before an abrupt kill.

Production systems need durable central logs, Kubernetes events, termination metadata, and crash artifacts.

---

## 5. Interpret termination evidence

| Evidence | Initial direction |
|---|---|
| `OOMKilled`, often exit `137` | cgroup memory limit or node-level memory event |
| exit `137` without explicit OOM | SIGKILL, forced termination, or pressure; correlate events and node logs |
| exit `143` | SIGTERM; rollout, drain, controller, or graceful shutdown path |
| exit `0` | main process completed; wrapper, finite workload, or intentional exit |
| exit `1` | generic application, dependency, or configuration failure |
| exit `126` | command found but not executable |
| exit `127` | executable or path not found |
| exit `134` | abort, assertion, or runtime fatal error |
| signal `11`, often exit `139` | segmentation fault |
| `Evicted` pod | kubelet eviction manager or node pressure |
| `ContainerStatusUnknown` | kubelet/runtime communication or node loss |
| `Error` plus stack trace | application crash |
| `Completed` with `restartPolicy: Always` | main process exited successfully and kubelet restarted it |

Exit codes are clues, not full causal explanations.

---

## 6. Why probes can remain healthy

### Crash between probe executions

A liveness probe can pass and the process can fail one second later.

### Probe checks the wrong capability

A `/health` handler or sidecar may remain alive while:

- Worker threads are dead.
- Queue consumption stopped.
- Background task crashed.
- Credential refresh failed.
- Database writes are impossible.

### Probe belongs to another container

Each container owns its probes. A sidecar can restart without the main application's probe failing.

### Pod replacement is external

Deployment rollout, drain, eviction, consolidation, or manual deletion can terminate a healthy pod.

### OOM kill is external to probe logic

The kernel or cgroup can kill a responsive process.

### Intentional fatal exit

The application may exit after:

- Lost leader lease.
- Invalid configuration refresh.
- Certificate or token refresh failure.
- Fatal background thread.
- Internal watchdog.
- Dependency policy declaring state unrecoverable.

### Probe timing hides the state

A process may restart and recover before the next monitoring sample. Restart counters and termination history are required.

---

## 7. Command, entrypoint, and PID 1

Inspect rendered command and arguments:

```bash
kubectl get pod -n <namespace> <pod> \
  -o jsonpath='{range .spec.containers[*]}{.name}{" command="}{.command}{" args="}{.args}{"\n"}{end}'
```

### Backgrounding the real process

Broken wrapper:

```sh
#!/bin/sh
my-server &
exit 0
```

The container ends when PID 1 exits.

Preferred pattern:

```sh
#!/bin/sh
exec my-server
```

### Signal handling

Without `exec`, the shell may:

- Fail to forward SIGTERM.
- Delay shutdown.
- Leave child processes.
- Fail to reap zombies.

Use an init process only when the runtime and application need it; do not add one without understanding signal and child-process behavior.

### Wrong controller type

Finite work belongs in:

- Job.
- CronJob.
- Workflow controller.

A Deployment expects a long-running main process. Exit code `0` with `restartPolicy: Always` produces an endless restart loop.

### Entrypoint drift

A new image can change its entrypoint while the manifest retains old arguments. Compare rendered image configuration and Kubernetes overrides.

---

## 8. Memory investigation

### Container cgroup OOM

Compare:

- Working set and RSS.
- Anonymous versus file-backed memory.
- Memory limit and request.
- Heap and non-heap memory.
- Allocation and retention rate.
- Page cache.
- Shared-memory use.
- Sidecar and init-container memory.
- OOM timestamp.

Prometheus-style examples:

```promql
max_over_time(
  container_memory_working_set_bytes{
    namespace="<namespace>",
    pod="<pod>",
    container="<container>"
  }[15m]
)
```

Compare with configured limits and the termination timestamp.

### cgroup v2 evidence

On the node or in an authorized debug context, inspect the affected cgroup:

```bash
cat memory.current
cat memory.max
cat memory.high
cat memory.events
cat memory.stat
cat memory.pressure
```

Useful `memory.events` counters include limit, high-pressure, OOM, and OOM-kill evidence depending on kernel and hierarchy.

### Node-level memory pressure

```bash
kubectl describe node <node>
kubectl get events --field-selector involvedObject.kind=Node,involvedObject.name=<node>
```

Look for:

- `MemoryPressure`.
- Eviction thresholds.
- System daemon use.
- Multiple pod evictions.
- Kernel OOM.
- Memory PSI.
- Swap configuration and policy.

A container may be killed or evicted during node pressure even when its own recent average looks acceptable.

### Leak versus legitimate peak

Compare old and new versions under the same workload.

Collect where safe:

- Heap profile.
- Allocation profile.
- Garbage-collector state.
- Native memory.
- Cache cardinality.
- Request or tenant correlation.

Increasing a limit can delay a leak and increase node blast radius. It is a mitigation only when headroom and mechanism are understood.

---

## 9. CPU, throttling, and watchdogs

CPU throttling usually causes latency rather than direct termination, but it can trigger:

- Missed leader lease.
- Watchdog expiry.
- Heartbeat failure.
- Event-loop starvation.
- Dependency timeout treated as fatal.
- Shutdown grace-period overrun.

Inspect:

```promql
rate(container_cpu_cfs_throttled_seconds_total[5m])
```

Correlate with:

- CPU limit and request.
- Scheduler delay and CPU PSI.
- GC pause.
- Thread-pool or event-loop saturation.
- Lease-renewal timestamps.
- Watchdog logs.
- Exit timestamp.

Do not infer that CPU limit caused restart solely because throttling exists.

---

## 10. Kubelet, runtime, and node evidence

### Kubernetes events

```bash
kubectl get events -n <namespace> \
  --field-selector involvedObject.name=<pod> \
  --sort-by=.lastTimestamp
```

Events are ephemeral and can be rate-limited. Export them durably.

### Kubelet and runtime

Inspect on the node or through provider-supported diagnostics:

- Kubelet journal.
- Container runtime journal.
- Runtime task and shim state.
- Image filesystem.
- Snapshotter and garbage collection.
- Pod sandbox creation.
- CNI and CSI logs.
- Kernel journal.

Generic examples:

```bash
journalctl -u kubelet --since '-30 min'
journalctl -u containerd --since '-30 min'
journalctl -k --since '-30 min'
crictl ps -a
crictl inspect <container-id>
crictl pods
```

Exact tools and permissions depend on platform and runtime.

### Node conditions

Check:

- `Ready`.
- Memory, disk, and PID pressure.
- Node reboot or kernel event.
- Image filesystem and inode use.
- Runtime health.
- Clock.
- Filesystem and mount state.
- Network and CNI health.

A node can remain Ready while a localized runtime, disk, or network defect affects one pod population.

---

## 11. Eviction and node pressure

Pod eviction is pod replacement, not a container restart.

Potential causes:

- Memory pressure.
- Disk or inode pressure.
- PID pressure.
- Ephemeral-storage limit.
- Node shutdown.
- Taint-based eviction after node condition.
- Administrative drain.

Inspect pod status and events for `Evicted` and the message explaining the resource threshold.

Check:

```bash
kubectl get pod -n <namespace> <pod> -o yaml
kubectl describe node <node>
df -hT
df -i
```

QoS class influences eviction priority but does not guarantee survival.

Local ephemeral storage includes more than application files. Logs, writable image layers, image storage, and empty directories can contribute.

---

## 12. Rollout and controller-driven termination

### Deployment or StatefulSet

```bash
kubectl rollout history deployment/<name> -n <namespace>
kubectl describe deployment/<name> -n <namespace>
kubectl get rs -n <namespace> -o wide
```

Look for:

- Pod-template hash changes.
- Image digest change.
- Annotation mutation.
- Rolling-update settings.
- Repeated sync.
- Manual rollout restart.
- Mutable tag resolving to new content.

### GitOps and operators

Inspect:

- Desired revision.
- Reconciliation events.
- Ownership of `spec.replicas` and pod template.
- Policy mutations.
- Custom resource state.

### Node lifecycle controllers

Healthy pods can be terminated by:

- Node-group update.
- Dynamic provisioner consolidation.
- Drift replacement.
- Node expiration.
- Spot or interruption handling.
- Descheduler.
- Cluster Autoscaler scale-down.
- Node repair.

Correlate pod deletion timestamp with controller and node events.

### PDB

A PodDisruptionBudget limits supported voluntary evictions. It does not prevent:

- OOM.
- Node crash.
- Forced deletion.
- Every interruption.
- Application process exit.

---

## 13. Configuration, Secret, and identity changes

Compare old and new pods:

- ConfigMap and Secret resource versions.
- Mounted file timestamps.
- Environment variables.
- Feature flags.
- Certificate and trust bundle.
- ServiceAccount.
- Cloud workload-identity association.
- External-secret refresh.
- Startup and background refresh behavior.

Common pattern:

```text
pod starts
probe passes
background client refreshes token or secret
refresh fails or returns incompatible value
application treats failure as fatal
process exits
```

Separate:

- Authentication failure.
- Authorization failure.
- Secret parsing.
- Network access to identity or secret service.
- Application policy choosing to terminate.

Do not attach broad credentials merely to stop restarts.

---

## 14. Dependency-triggered exits

Investigate:

- Database connection and credential refresh.
- Cache availability.
- DNS resolution.
- Queue or stream consumer fatal state.
- TLS trust change.
- External API rate limit.
- Leader election and lease.
- Disk or local state.

Ask:

- Is restart a deliberate recovery strategy?
- Is state cleanly discarded?
- Does restart amplify dependency load?
- Is there backoff and jitter?
- Does every replica restart together?
- Could degraded serving be safer?

A restart loop can become a retry storm:

```text
dependency slows
  -> every pod exits
  -> every pod restarts
  -> connection and cache storm
  -> dependency worsens
```

Use bounded retries, admission control, circuit breaking, and safe degraded behavior.

---

## 15. CrashLoopBackOff mechanics

`CrashLoopBackOff` means Kubernetes is delaying repeated restarts. It is not a root cause.

The backoff protects the node and dependency from tight restart loops, but:

- User capacity remains degraded.
- Previous logs can rotate.
- All replicas can align into restart waves.
- Rollout may stall.

Investigate the original termination before changing backoff or restarting the pod manually.

A manual pod deletion may reset some visible state and make the incident harder to understand.

---

## 16. Probes and lifecycle hooks

### Startup probe

Protects slow startup from liveness failure. It should represent startup completion, not merely an open port.

### Liveness probe

Answers whether restart is likely to restore the process. It should not depend on every downstream service.

### Readiness probe

Answers whether the pod should receive new traffic for the relevant capability.

### `preStop` and grace period

Verify:

- Readiness changes before shutdown.
- Endpoint and load-balancer propagation.
- Application stops accepting new work.
- In-flight work drains.
- Telemetry flushes.
- Process exits before `terminationGracePeriodSeconds`.

A failed `preStop` or insufficient grace can result in SIGKILL and exit `137` without being a memory problem.

### Per-container restart behavior

Kubernetes capabilities vary by version and feature state. Validate exact semantics before depending on container-specific restart behavior.

---

## 17. Evidence-preserving workflow

### Step 1 — Verify the lifecycle event

- Same pod UID or new pod?
- Which container?
- Which owner?
- Which node?
- Container restart, pod eviction, rollout, or node replacement?

### Step 2 — Capture ephemeral evidence

- Last state and exit information.
- Previous logs.
- Events.
- Pod YAML.
- Image digest and configuration.
- Node condition.
- Controller and rollout history.

### Step 3 — Correlate time

Align:

- Termination.
- OOM or pressure event.
- Deployment or config change.
- Node or controller action.
- Dependency and identity error.
- User SLI.

### Step 4 — Form a falsifiable hypothesis

Example:

```text
Hypothesis:
  new version leaks native memory and reaches the cgroup limit after 18 minutes.

Predicted evidence:
  working set rises with pod age only on the new digest,
  memory.events records OOM kill,
  old digest remains stable at equal traffic.
```

### Step 5 — Apply narrow mitigation

- Roll back image.
- Remove one faulty cohort.
- Increase memory temporarily with capacity validation.
- Correct command or workload type.
- Stop node disruption.
- Restore identity, Secret, or dependency.
- Quarantine or replace bad node.

### Step 6 — Prove recovery

- Restart count stable.
- No new pod replacements for the same cause.
- Process remains alive beyond previous failure interval.
- User transaction succeeds.
- Dependency and backlog stable.
- SLO burn stops.

---

## 18. Observability requirements

Container and pod:

- Restart count by container.
- Last termination reason, exit code, and signal.
- Pod UID and owner.
- Current and previous image digest.
- Pod replacement and eviction rate.
- Startup and readiness duration.
- Graceful shutdown duration.

Resources:

- Memory current, working set, limit, and OOM events.
- CPU usage, throttling, and scheduler pressure.
- Ephemeral storage and inode use.
- PID count and pressure.

Node and runtime:

- Kubelet and runtime health.
- Sandbox and image-operation latency.
- Node conditions and lease age.
- Disk, inode, kernel, and device errors.
- CNI and CSI failures.

Change and dependency:

- Image, configuration, Secret, feature, and identity revision.
- Node-image and controller rollout.
- Dependency error and latency.
- Leader lease and token refresh.

Product:

- Available serving replicas.
- Endpoint and target health.
- Request success and latency.
- Queue or stream lag.
- Error-budget burn.

Alert on impact and rapid loss of serving capacity; use restart signals for diagnosis and leading indicators.

---

## 19. Prevention

- Pin image digests.
- Validate entrypoint and command in CI.
- Use correct workload controller.
- Load-test memory, native allocations, and caches.
- Set requests and limits from evidence.
- Centralize previous logs and events.
- Record exit reason and image digest in telemetry.
- Make probes capability-aware.
- Test graceful shutdown and forced node loss.
- Bound fatal dependency policy and restart backoff.
- Canary configuration, Secret, identity, and sidecar changes.
- Monitor node pressure and runtime operation latency.
- Protect system components with durable capacity.
- Prevent overlapping rollout, consolidation, and repair controllers.

---

## 20. Common weak answers

### “The probes are healthy, so Kubernetes should not restart it”

Processes can exit, be OOM-killed, be evicted, or be terminated by controllers independently of probe results.

### “Delete the pod”

This can destroy previous logs and lifecycle evidence.

### “Increase the memory limit”

This may delay a leak, consume node headroom, or hide node-level pressure.

### “CrashLoopBackOff is the root cause”

It is a protective restart backoff state.

### “Exit 137 always means OOM”

It means SIGKILL conventionally; confirm OOM or another terminating authority.

### “All containers share one probe”

Probe configuration and restart history are per container.

### “PDB prevents restarts”

It governs voluntary eviction, not application crashes, OOM, or all node failures.

### “Node is Ready, so the runtime is fine”

Localized runtime, image, disk, CNI, CSI, or workload failures can exist on a Ready node.

---

## 21. Adversarial interview questions

### How do you distinguish restart from replacement?

Compare pod UID and creation time. Same UID plus increasing container restart count is a container restart; new UID indicates pod replacement.

### Why can exit code `0` loop in a Deployment?

The main process completed successfully, but the pod restart policy for normal workload pods is generally `Always`, so kubelet starts it again. Use a Job for finite work.

### How do you prove OOM?

Use terminated reason, cgroup `memory.events`, kernel or kubelet evidence, memory time series, limit, and timestamp correlation. Exit `137` alone is insufficient.

### What if previous logs are empty?

The process may have been killed before flush, logs may be on another stream, the pod may have been replaced, or node-local logs may be lost. Use events, termination state, central logs, crash dumps, and node/runtime evidence.

### When would you increase memory during the incident?

As a bounded mitigation when the failure is confirmed memory exhaustion, node capacity supports it, and the change will restore service while leak or sizing investigation continues.

### What if every pod restarts after a dependency outage?

Stop the restart storm, reduce retry and connection pressure, restore or bypass the dependency safely, and change the application to degrade or back off instead of synchronized fatal exit.

### Can a sidecar restart while the pod remains Ready?

Yes, depending on which container owns readiness and whether readiness gates include that sidecar capability. Inspect every container status.

### How long do you observe after the fix?

Longer than the previous time-to-failure and across relevant traffic, token-refresh, cache, and rollout intervals.

---

## 22. Staff/Principal checklist

A strong answer includes:

- Container restart versus pod replacement versus node event.
- Per-container current and last state.
- Previous logs and ephemeral evidence.
- Exit code, signal, and terminating authority.
- PID 1 and workload-controller semantics.
- cgroup memory and OOM proof.
- CPU watchdog and lease reasoning.
- Kubelet, runtime, CNI, CSI, kernel, and node evidence.
- Rollout, GitOps, autoscaler, and disruption correlation.
- Configuration, identity, Secret, and dependency refresh.
- Narrow mitigation.
- Business-path and SLO recovery proof.

---

## Primary references

- [Kubernetes pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Kubernetes container lifecycle hooks](https://kubernetes.io/docs/concepts/containers/container-lifecycle-hooks/)
- [Kubernetes configure liveness, readiness, and startup probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Kubernetes node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Kubernetes resource management for pods and containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
