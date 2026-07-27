# Lab 02 — Kubernetes Restart Forensics

## Objective

Diagnose four different workload failures that operators often describe as “the pod keeps restarting”:

1. the main process exits successfully under `restartPolicy: Always`;
2. the container is OOM-killed while simple probes had been passing;
3. a wrapper shell backgrounds the real server and exits as PID 1;
4. a sidecar restarts while the main application remains healthy.

The lab teaches you to distinguish:

- container restart inside one pod UID;
- pod replacement by a controller;
- sidecar-only failure;
- node or eviction-driven replacement;
- application, cgroup, kubelet, and controller evidence.

## Prerequisites

- `kubectl`
- a disposable kind, minikube, Docker Desktop, or test Kubernetes cluster
- permission to create and delete one namespace
- Bash and `jq`

Do not run these manifests in production.

## Quick start

```bash
./scripts/install.sh
kubectl get pods -n restart-lab -w
```

Wait until restart counts begin increasing, then collect evidence:

```bash
./scripts/collect.sh
```

Evidence is written under `.evidence/<UTC timestamp>/`.

Cleanup:

```bash
./scripts/cleanup.sh
```

---

## Scenario A — Exit code 0 under a Deployment

Manifest:

```text
manifests/10-exit-zero.yaml
```

The container:

- creates a readiness marker;
- passes readiness and liveness checks;
- sleeps for 20 seconds;
- exits with code 0.

Because a Deployment uses `restartPolicy: Always`, kubelet starts it again.

### Investigation

```bash
pod=$(kubectl get pod -n restart-lab -l scenario=exit-zero -o jsonpath='{.items[0].metadata.name}')

kubectl get pod -n restart-lab "$pod" \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{" restart="}{.restartCount}{" last="}{.lastState.terminated}{"\n"}{end}'

kubectl logs -n restart-lab "$pod" --previous --timestamps
```

Expected evidence:

- same pod UID;
- increasing restart count;
- terminated reason `Completed`;
- exit code `0`;
- probes may have passed before process completion.

### Interview lesson

Exit code 0 is successful process completion, but it is incorrect behavior for a long-running Deployment.

A finite process should normally use a Job or CronJob. A server wrapper must keep the intended process in the foreground.

---

## Scenario B — OOMKilled after readiness

Manifest:

```text
manifests/20-oom-after-ready.yaml
```

The Python process:

- starts an HTTP health server;
- becomes Ready;
- waits briefly;
- allocates memory until the 48 MiB container limit is exceeded.

### Investigation

```bash
pod=$(kubectl get pod -n restart-lab -l scenario=oom-after-ready -o jsonpath='{.items[0].metadata.name}')

kubectl describe pod -n restart-lab "$pod"
kubectl logs -n restart-lab "$pod" --previous --timestamps

kubectl get pod -n restart-lab "$pod" -o json \
  | jq '.status.containerStatuses[] | {name, restartCount, state, lastState}'
```

Expected evidence:

- `Reason: OOMKilled`;
- commonly exit code `137`;
- readiness and liveness were passing before the kernel kill;
- memory limit, not the probe, caused termination.

### Interview lesson

Do not increase the memory limit blindly. Determine whether this is:

- a leak;
- expected working set;
- excessive concurrency;
- sidecar overhead;
- node-level memory pressure;
- incorrect request/limit configuration.

---

## Scenario C — Wrapper shell exits while child server was healthy

Manifest:

```text
manifests/30-background-pid1.yaml
```

The shell starts an HTTP server in the background, sleeps, and exits. The child process is terminated with the container namespace when PID 1 exits.

### Investigation

```bash
pod=$(kubectl get pod -n restart-lab -l scenario=background-pid1 -o jsonpath='{.items[0].metadata.name}')

kubectl logs -n restart-lab "$pod" --previous --timestamps
kubectl get pod -n restart-lab "$pod" -o yaml
```

Unsafe wrapper:

```sh
python -m http.server 8080 &
sleep 20
exit 0
```

Correct foreground pattern:

```sh
exec python -m http.server 8080
```

### Interview lesson

PID 1 controls container lifetime and signal handling. A healthy child process does not keep the container alive after PID 1 exits.

---

## Scenario D — Sidecar restarts while main container remains Ready

Manifest:

```text
manifests/40-sidecar-restart.yaml
```

The main NGINX container serves traffic continuously. A separate sidecar exits every 15 seconds and restarts.

### Investigation

```bash
pod=$(kubectl get pod -n restart-lab -l scenario=sidecar-restart -o jsonpath='{.items[0].metadata.name}')

kubectl get pod -n restart-lab "$pod" \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{" ready="}{.ready}{" restart="}{.restartCount}{" lastReason="}{.lastState.terminated.reason}{"\n"}{end}'

kubectl logs -n restart-lab "$pod" -c unstable-sidecar --previous --timestamps
kubectl logs -n restart-lab "$pod" -c main --tail=20
```

### Interview lesson

Always inspect every container and init-container status. A pod-level Ready condition or healthy main process can hide sidecar instability and telemetry, proxy, secret, or policy failures.

---

## Distinguish restart from replacement

Capture pod UID and creation time repeatedly:

```bash
kubectl get pods -n restart-lab \
  -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,CREATED:.metadata.creationTimestamp,RESTARTS:.status.containerStatuses[*].restartCount,NODE:.spec.nodeName'
```

### Container restart

- same pod UID;
- restart count increases.

### Pod replacement

- new pod UID or pod name;
- restart count may be zero;
- inspect Deployment/ReplicaSet history, evictions, node drain, Karpenter, managed node-group update, or GitOps changes.

Inject a controlled pod replacement:

```bash
kubectl rollout restart deployment/exit-zero -n restart-lab
kubectl rollout status deployment/exit-zero -n restart-lab
```

Compare this with the same-pod restart evidence.

---

## Evidence order during a real incident

Use this order because evidence is ephemeral:

```text
1. pod UID and owner
2. container lastState, reason, exit code, signal, timestamps
3. previous container logs
4. pod events
5. current logs and rendered command/args
6. memory/CPU/cgroup metrics
7. node conditions, kubelet, runtime, and kernel logs
8. rollout, GitOps, Karpenter, node-group, Spot, and eviction history
9. configuration, secret, sidecar, and dependency changes
```

### Core commands

```bash
kubectl describe pod -n <namespace> <pod>
kubectl logs -n <namespace> <pod> -c <container> --previous --timestamps
kubectl get events -n <namespace> --sort-by=.lastTimestamp
kubectl describe node <node>
kubectl rollout history deployment/<name> -n <namespace>
```

---

## Hypothesis worksheet

| Hypothesis | Expected evidence | Disproving evidence | Safe test |
|---|---|---|---|
| Main process exits normally | exit 0, Completed, wrapper logs | OOMKilled or signal | run corrected foreground command |
| Container OOM | reason OOMKilled, memory reaches limit | stable memory and explicit exit | lower allocation or raise measured limit in test |
| Pod replacement | UID changes, controller/node event | same UID and increasing restart count | pause controller or compare rollout history |
| Sidecar only | one container restart count rises | main also terminates | inspect each container separately |
| Node pressure | MemoryPressure/DiskPressure, multiple evictions | isolated pod failure on healthy node | reschedule to clean node after evidence capture |

## Recovery proof

Do not declare success because a replacement pod currently shows zero restarts.

Verify:

- the same pod or corrected replacement survives longer than the historical failure interval;
- restart count remains stable;
- Ready and business transaction remain healthy;
- node pressure and controller disruption stop;
- no sidecar continues failing;
- current and previous logs contain no recurring fatal condition.

## AWS/EKS production mapping

| Lab evidence | Production source |
|---|---|
| `lastState` and exit code | Kubernetes API/pod status |
| `--previous` logs | CloudWatch Logs or other centralized container logs |
| OOMKilled | Container Insights, Prometheus/cAdvisor, node kernel evidence |
| pod replacement | EKS audit logs, Deployment/GitOps history, Karpenter or node-group events |
| node pressure | kubelet/runtime/kernel logs and EKS node monitoring |
| sidecar failure | service mesh, OTel agent, secret sidecar, or security-agent telemetry |

## Adversarial questions

1. How can probes remain healthy before an OOM kill?
2. Why does a Deployment restart a process that exits successfully?
3. What evidence disappears after another container restart?
4. How can a pod be replaced repeatedly with restart count zero?
5. What does exit 137 prove, and what does it not prove?
6. Would a PodDisruptionBudget prevent this?
7. When should you cordon and replace the node?
8. How do you distinguish Karpenter consolidation from an application crash?

## Completion standard

Without reading this guide, diagnose each scenario and explain:

- the terminating actor;
- the decisive evidence;
- one unsafe shortcut;
- the narrow mitigation;
- the production EKS evidence source;
- the permanent prevention.