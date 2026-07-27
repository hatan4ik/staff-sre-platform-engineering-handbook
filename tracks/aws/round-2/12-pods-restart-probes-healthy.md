# Question 12 — EKS Pods Restart Continuously While Readiness and Liveness Remain Healthy

## Interview prompt

Pods on Amazon EKS continuously restart after deployment, but readiness and liveness probes remain healthy. How would you troubleshoot the issue?

## What the interviewer is testing

Probes do not cause or explain every restart. A container can:

- exit cleanly with code 0
- crash between probe executions
- be OOM-killed
- be terminated by a rollout or node disruption
- be evicted
- lose its node
- have a sidecar restart while the main container stays healthy
- be killed by a lifecycle hook or external controller

The strongest answer identifies exactly which container restarted, who terminated it, why, and whether it was a process, pod, node, or controller event.

---

## 90-second Staff/Principal answer

> I first verify the symptom because “the pod restarts” can mean a container restart inside the same pod, a pod replacement by a Deployment, or a node-driven eviction. I compare pod UID, container restart counts, ReplicaSet, node, and creation timestamps.
>
> For a container restart, I inspect the last termination reason, exit code, signal, timestamps, events, and previous container logs using `kubectl describe`, pod status, and `kubectl logs --previous`. Healthy probes do not rule out OOMKilled, application exit, signal handling, sidecar failure, or a crash between probe intervals.
>
> I correlate the restart with cgroup memory, CPU throttling, node pressure, eviction events, kubelet and container-runtime logs, deployment history, ConfigMap or Secret changes, and external controllers such as Karpenter, managed node-group updates, or GitOps reconciliation. I also check whether PID 1 exits because a wrapper script finishes, a background process is not waited on, or the application intentionally terminates after losing a dependency.
>
> I preserve evidence before another restart overwrites it, then mitigate according to cause—roll back the image, correct command and signal handling, right-size memory, fix node pressure, stop disruptive automation, or repair the dependency. I validate that restart rate returns to zero and the business transaction remains healthy.

---

## 1. Define what is restarting

### Container restart in the same pod

Signs:

- pod UID remains the same
- `restartCount` increases
- container state changes from terminated to waiting/running
- `CrashLoopBackOff` may appear

### Pod replacement

Signs:

- pod name or UID changes
- restart count may stay at zero
- ReplicaSet, rollout, eviction, rescheduling, or controller action creates a new pod

### Node replacement

Signs:

- many pods disappear or move together
- node becomes NotReady, drains, or terminates
- Karpenter, managed node-group update, Spot interruption, or autoscaling event is present

### Sidecar-only restart

A pod can show Ready while one sidecar restarts depending on readiness gates and container configuration. Inspect every container and init container separately.

---

## 2. Capture the exact pod and container state

```bash
kubectl get pod -n <namespace> <pod> -o wide
kubectl describe pod -n <namespace> <pod>
kubectl get pod -n <namespace> <pod> -o yaml
```

Compact status query:

```bash
kubectl get pod -n <namespace> <pod> \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\n  restartCount="}{.restartCount}{"\n  state="}{.state}{"\n  lastState="}{.lastState}{"\n"}{end}'
```

Record:

- pod UID
- owner ReplicaSet and Deployment
- container name
- restart count
- current state
- last terminated state
- reason
- exit code
- signal
- started and finished timestamps
- node and AZ
- image digest

Do not rely on the pod phase alone.

---

## 3. Preserve previous logs immediately

```bash
kubectl logs -n <namespace> <pod> \
  -c <container> --previous --timestamps
```

Current logs:

```bash
kubectl logs -n <namespace> <pod> \
  -c <container> --timestamps --since=30m
```

For all containers:

```bash
kubectl logs -n <namespace> <pod> \
  --all-containers=true --prefix --timestamps
```

Important limitation: Kubernetes commonly retains only the immediately previous terminated container log through `--previous`. Another restart can overwrite the evidence. Central log shipping is essential for repeated crashes.

---

## 4. Interpret termination reason, code, and signal

| Evidence | Likely direction |
|---|---|
| `Reason: OOMKilled`, exit 137 | container memory limit or node-level memory event |
| exit 137 without clear OOM reason | SIGKILL, forced termination, or memory pressure; correlate events and node logs |
| exit 143 | SIGTERM; rollout, drain, controller, or graceful shutdown path |
| exit 0 | main process completed; wrong workload type, wrapper script, or intentional exit |
| exit 1 | generic application/configuration failure |
| exit 126/127 | command permission or executable/path error |
| signal 11 / exit 139 | segmentation fault |
| `Error` with application stack | application crash |
| pod `Evicted` | node pressure or eviction manager |
| `ContainerStatusUnknown` | node/runtime communication issue |

Exit codes are evidence, not a complete root cause.

---

## 5. Why probes can remain healthy

### Process exits after a successful probe

A liveness probe can pass at second 10 and the process can crash at second 11.

### Application exits intentionally

The process may decide to terminate after:

- configuration validation fails later
- credentials cannot refresh
- leader lease is lost
- dependency heartbeat fails
- a fatal background thread error
- an internal watchdog fires

### Probe checks the wrong process or port

A sidecar or lightweight health server can remain healthy while the real worker process exits.

### Probe is not applied to the restarting container

Each container has its own probes. The main container may be healthy while a sidecar restarts, or vice versa.

### Pod replacement is not a container restart

A Deployment rollout or node drain can replace a fully healthy pod. Probes may remain green until graceful termination begins.

### OOM kill is external to probe logic

The kernel can kill the process even when it responds correctly moments earlier.

### Exit code 0 with `restartPolicy: Always`

Deployments normally use `restartPolicy: Always`. If the main process completes successfully, kubelet restarts it even though no probe failed.

---

## 6. Application command and PID 1

Inspect the rendered command and args:

```bash
kubectl get pod -n <namespace> <pod> \
  -o jsonpath='{range .spec.containers[*]}{.name}{" command="}{.command}{" args="}{.args}{"\n"}{end}'
```

Common mistakes:

### Backgrounding the real process

```sh
#!/bin/sh
my-server &
exit 0
```

PID 1 exits, so the container exits even though the child briefly ran.

Correct pattern:

```sh
#!/bin/sh
exec my-server
```

### Shell does not propagate signals

Without `exec`, a wrapper shell may not forward SIGTERM correctly or reap child processes.

### Wrong workload controller

A finite batch command belongs in a Job or CronJob, not a Deployment expecting a long-running process.

### Entrypoint or argument mismatch

A new image can change its default entrypoint while the Kubernetes manifest still supplies old arguments.

---

## 7. Memory investigation

### Container-level OOM

Compare:

- memory working set
- memory limit
- allocation rate
- heap and non-heap memory
- page cache
- sidecar memory
- OOM kill timestamp

Prometheus examples:

```promql
max_over_time(
  container_memory_working_set_bytes{
    namespace="<namespace>",
    pod="<pod>",
    container="<container>"
  }[15m]
)
```

Compare with:

```promql
kube_pod_container_resource_limits{
  namespace="<namespace>",
  pod="<pod>",
  container="<container>",
  resource="memory"
}
```

### Node memory pressure

Inspect:

```bash
kubectl describe node <node>
kubectl get events --field-selector involvedObject.kind=Node,involvedObject.name=<node>
```

Look for:

- `MemoryPressure`
- eviction thresholds
- system and daemon memory
- multiple pod evictions
- kernel OOM events

A container can be killed because the node is under pressure even when its own usage appears reasonable.

### Memory regression after deployment

Compare old and new image versions under the same traffic. Capture heap or runtime diagnostics before increasing limits blindly.

Increasing a limit can delay but not solve a leak.

---

## 8. CPU and watchdog behavior

CPU throttling normally causes latency, but it can indirectly trigger restart if:

- internal watchdog concludes the process is stuck
- lease renewal misses its deadline
- event loop cannot process heartbeats
- dependency timeout is treated as fatal

Inspect:

```promql
rate(container_cpu_cfs_throttled_seconds_total[5m])
```

Correlate with:

- application watchdog logs
- leader-election events
- GC pauses
- thread-pool saturation
- process termination timestamp

---

## 9. Node and kubelet investigation

### Kubernetes events

```bash
kubectl get events -n <namespace> \
  --field-selector involvedObject.name=<pod> \
  --sort-by=.lastTimestamp
```

Events are ephemeral and can be rate-limited. Centralize them for durable evidence.

### Node logs

Investigate:

- kubelet
- containerd or runtime
- kernel journal
- CNI
- disk and inode pressure
- runtime garbage collection
- system OOM

On supported EKS nodes, use the EKS log collector when appropriate:

```bash
sudo /etc/eks/log-collector-script/eks-log-collector.sh
```

Preserve the resulting archive securely.

### Node health signals

Check:

- Ready condition
- memory, disk, and PID pressure
- node reboot or kernel error
- filesystem availability
- clock problems
- runtime health
- EKS node monitoring agent events where deployed

A node can remain `Ready` while a localized runtime or resource issue affects one container cohort.

---

## 10. Eviction and disruption investigation

### Deployment rollout

```bash
kubectl rollout history deployment/<name> -n <namespace>
kubectl describe deployment/<name> -n <namespace>
```

Inspect:

- repeated GitOps sync
- changing pod-template hash
- annotation updated by automation
- rollout restart commands
- image tag mutation

### Karpenter

Inspect controller logs and node claims for:

- consolidation
- drift
- expiration
- interruption
- disruption budget
- failed drain

Healthy pods can be deliberately terminated during node consolidation.

### Managed node-group update

Check EKS update status and node drain history.

### Spot interruption

Look for interruption signals and replacement activity. Determine whether termination grace and PDBs allowed safe handoff.

### Descheduler or policy controller

An external controller can evict healthy pods to improve placement or enforce policy.

### PodDisruptionBudget

PDBs limit voluntary evictions; they do not prevent node crash, OOM, or every forced termination.

---

## 11. Configuration and secret investigation

Compare between old and new pods:

- ConfigMap resource version
- Secret version or external-secret refresh
- mounted file timestamps
- environment variables
- feature flags
- certificate and trust store
- service-account identity

Common pattern:

```text
pod starts
probe passes
background client refreshes credentials
AccessDenied or malformed secret occurs
application treats failure as fatal
process exits
```

Inspect CloudTrail for AWS API access denial and identity changes.

---

## 12. Dependency-triggered exits

An application should usually degrade or retry safely rather than terminate on every dependency error, but some applications intentionally exit to obtain a clean restart.

Investigate:

- database connection and credential refresh
- cache availability
- DNS resolution
- queue consumer fatal errors
- TLS trust changes
- external API rate limits
- leader election and leases

Ask whether restart is a deliberate resilience strategy or an accidental crash loop.

A restart-on-dependency-failure policy can amplify an outage through connection storms and cold starts.

---

## 13. Sidecars and init containers

Inspect all statuses:

```bash
kubectl get pod -n <namespace> <pod> -o json \
  | jq '.status.initContainerStatuses, .status.containerStatuses'
```

Sidecar causes:

- proxy crash or memory limit
- telemetry agent restart
- secret or certificate sidecar failure
- native sidecar lifecycle mismatch
- incompatible mesh revision

A restarting sidecar can interrupt traffic even when the application process remains alive.

Init-container loops normally prevent the application from starting, but sidecar-style init containers and newer lifecycle features require careful status interpretation.

---

## 14. Image and architecture issues

Check image digest and platform:

```bash
kubectl get pod -n <namespace> <pod> \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{" imageID="}{.imageID}{"\n"}{end}'
```

Possible issues:

- mutable tag points to changed image
- amd64/arm64 incompatibility
- missing shared library
- CPU instruction not supported on one instance family
- file permission or read-only filesystem issue
- base-image certificate or timezone data change
- application binary segmentation fault

Compare failures by instance type and architecture.

---

## 15. Ephemeral debugging

If the container lacks tools or crashes too quickly, use a controlled debug copy or ephemeral container where permitted.

Examples:

```bash
kubectl debug -n <namespace> pod/<pod> -it \
  --image=<approved-debug-image> \
  --target=<container>
```

Or create a copy with a changed command for inspection.

Security requirements:

- approved image
- restricted RBAC
- no secret exfiltration
- audit trail
- clean up after use

Do not alter the production pod so heavily that the original failure disappears.

---

## 16. Mitigation by cause

### Bad image or command

- stop rollout
- restore known-good digest
- correct entrypoint and PID 1 behavior

### OOMKilled

- reduce memory use or concurrency
- raise request/limit only from measured evidence
- isolate workload from node pressure
- capture heap/profile for durable fix

### Node pressure or runtime issue

- cordon and drain affected node safely
- replace the node from a known-good AMI
- preserve node logs
- verify whether issue repeats on the replacement

### Disruptive controller

- pause consolidation, rollout, or automation within its safety controls
- correct budget or policy
- do not disable protections globally without review

### Dependency fatal exit

- restore dependency or credentials
- reduce restart amplification
- implement bounded retry, backoff, and degraded behavior

### Sidecar failure

- roll back sidecar or mesh revision
- adjust resources
- verify application/sidecar compatibility

---

## 17. Prove recovery

Require:

- restart count stops increasing
- new pods remain stable beyond the previous failure interval
- no replacement loop continues under a new pod UID
- memory, CPU, node pressure, and dependency signals normalize
- readiness and business transaction remain healthy
- rollout or node controller reaches stable state
- logs contain no recurring fatal condition

A zero restart count on newly recreated pods is not sufficient until they survive the historical failure window.

---

## Adversarial follow-ups

### “How can probes be healthy if the container restarts?”

Probes are periodic samples. The process can exit between samples, be killed by the kernel, complete with code 0, or be terminated by a controller. Probes do not explain external termination.

### “What is your first command?”

I inspect pod status and `lastState`, then immediately capture `kubectl logs --previous` for the restarting container before another restart overwrites it.

### “Would you increase the memory limit?”

Only after confirming OOM behavior and understanding working set and node pressure. A higher limit can mask a leak or cause wider node instability.

### “The restart count is zero, but users report pods restarting.”

I compare pod UIDs and creation times. The pods may be replaced rather than containers restarted, commonly due to rollout, eviction, or node disruption.

### “Would a PDB prevent this?”

Only some voluntary pod evictions. It does not prevent process crash, OOM kill, node loss, or all forced termination.

---

## Weak answers to avoid

- “Check the liveness probe configuration.”
- assuming every restart is CrashLoopBackOff
- looking only at current logs instead of `--previous`
- ignoring sidecars and init-container status
- confusing pod replacement with container restart
- increasing memory without checking OOM and node pressure
- restarting or deleting pods before preserving evidence
- assuming Ready nodes rule out kubelet, runtime, or pressure problems
- treating exit code 0 as success for a Deployment

---

## Closing statement

> I separate process restart, pod replacement, and node disruption. Then I identify the terminating actor from container state, previous logs, events, node evidence, and controller history. Probes tell me whether a sampled check passed; termination evidence tells me why the workload actually stopped.