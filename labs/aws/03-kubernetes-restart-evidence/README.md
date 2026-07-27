# Lab 3 — Kubernetes Restarts While Health Probes Appear Healthy

## Interview scenario

EKS Pods restart continuously, yet the configured HTTP probes appear healthy whenever engineers test them. The weak conclusion is that Kubernetes is randomly restarting healthy Pods.

This lab demonstrates two different causes:

1. the primary application is OOM-killed while its `/health` endpoint continues returning `200` until termination;
2. a secondary container exits repeatedly while the primary application container and its probes remain healthy.

The incident task is to identify **which container terminated, why it terminated, and which component initiated or observed the restart**.

## Safety invariant

> A restart investigation must preserve the previous termination reason, exit code, previous logs, events, resource evidence, and node context before broad restarts or redeployments destroy the evidence.

## Failure-domain model

```text
process exits
   -> container runtime records termination
      -> kubelet applies restart policy
         -> container restartCount increases

Possible initiators or causes:
- application exit or signal
- OOM kill from a container memory limit
- failed liveness or startup probe
- lifecycle hook failure or wrapper-process behavior
- another container in the Pod
- Pod replacement by Deployment, eviction, preemption, node drain, or node loss
```

A green readiness check answers only whether that probe succeeded at that moment. It does not prove that:

- the process will not exit one second later;
- memory usage is below the cgroup limit;
- another container is healthy;
- the Pod was not replaced;
- the node is stable;
- a rollout controller is not creating new Pods.

## Prerequisites

- a disposable Kubernetes cluster;
- `kubectl`;
- optional Metrics Server for `kubectl top`.

## 1. Deploy the experiments

```bash
kubectl apply -f manifests.yaml
kubectl -n aws-restart-lab get pods -w
```

Wait until restart counts increase.

## 2. Identify Pod replacement versus container restart

```bash
kubectl -n aws-restart-lab get pods \
  -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,PHASE:.status.phase,RESTARTS:.status.containerStatuses[*].restartCount,NODE:.spec.nodeName'
```

Interpretation:

- same Pod UID with increasing `restartCount` indicates a container restart inside the existing Pod;
- a new Pod name or UID indicates Pod replacement by a controller, eviction, rollout, or node event;
- inspect each container independently in a multi-container Pod.

## 3. Recover the last termination evidence

```bash
kubectl -n aws-restart-lab get pod \
  -l scenario=oom-probes-healthy \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .status.containerStatuses[*]}  {.name}{" restarts="}{.restartCount}{" reason="}{.lastState.terminated.reason}{" exit="}{.lastState.terminated.exitCode}{" signal="}{.lastState.terminated.signal}{" finished="}{.lastState.terminated.finishedAt}{"\n"}{end}{end}'

kubectl -n aws-restart-lab get pod \
  -l scenario=sidecar-crash \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{range .status.containerStatuses[*]}  {.name}{" ready="}{.ready}{" restarts="}{.restartCount}{" reason="}{.lastState.terminated.reason}{" exit="}{.lastState.terminated.exitCode}{"\n"}{end}{end}'
```

Expected evidence:

- the OOM experiment should eventually report `reason=OOMKilled` for container `app`;
- the sidecar experiment should report exit code `42` for container `crashing-sidecar` while the `app` container remains running.

Do not rely only on Pod phase or the total restart column.

## 4. Read current and previous logs

```bash
OOM_POD=$(kubectl -n aws-restart-lab get pod -l scenario=oom-probes-healthy -o jsonpath='{.items[0].metadata.name}')
SIDE_POD=$(kubectl -n aws-restart-lab get pod -l scenario=sidecar-crash -o jsonpath='{.items[0].metadata.name}')

kubectl -n aws-restart-lab logs "$OOM_POD" -c app --tail=50
kubectl -n aws-restart-lab logs "$OOM_POD" -c app --previous --tail=100

kubectl -n aws-restart-lab logs "$SIDE_POD" -c app --tail=50
kubectl -n aws-restart-lab logs "$SIDE_POD" -c crashing-sidecar --previous --tail=100
```

`--previous` is critical because the current container instance may look healthy after restart while the failed instance's output contains the useful evidence.

## 5. Inspect events, limits, and ownership

```bash
kubectl -n aws-restart-lab describe pod "$OOM_POD"
kubectl -n aws-restart-lab get events --sort-by='.lastTimestamp'

kubectl -n aws-restart-lab get pod "$OOM_POD" \
  -o jsonpath='{range .spec.containers[*]}{.name}{" requests="}{.resources.requests}{" limits="}{.resources.limits}{"\n"}{end}'

kubectl -n aws-restart-lab get pod "$OOM_POD" \
  -o jsonpath='owner={.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}{" node="}{.spec.nodeName}{" qos="}{.status.qosClass}{"\n"}'
```

With Metrics Server installed:

```bash
kubectl -n aws-restart-lab top pod --containers
```

A point-in-time metric may miss the peak immediately before OOM. Combine it with termination reason, historical telemetry, limit configuration, and application allocation behavior.

## 6. Prove probes are not the whole story

While the OOM application is running between restarts:

```bash
kubectl -n aws-restart-lab port-forward service/oom-app 18080:80
curl -i http://127.0.0.1:18080/health
```

The endpoint can return `200` while the process is steadily consuming memory toward its limit. The probe validates one request path, not resource safety.

For the sidecar experiment:

```bash
kubectl -n aws-restart-lab port-forward service/sidecar-app 18081:80
curl -i http://127.0.0.1:18081/health
```

The primary application remains healthy even though another container repeatedly exits.

## 7. Apply evidence-specific mitigation

### OOM case

Immediate mitigation options depend on evidence:

- scale out to reduce per-Pod working set only if load causes the growth;
- temporarily raise the memory limit if capacity exists and the risk is understood;
- reduce concurrency, cache size, batch size, or payload size;
- roll back a version associated with the memory regression;
- fix the leak or unbounded allocation before declaring permanent recovery.

Do not treat a larger limit as proof of root-cause removal.

Pause this experiment:

```bash
kubectl -n aws-restart-lab scale deployment/oom-probes-healthy --replicas=0
```

### Sidecar case

The failing component is not the primary application. Inspect its command, configuration, credentials, dependency, and intended lifecycle. A helper that is expected to finish may need a Job or init container rather than a perpetually restarted sidecar.

Pause this experiment:

```bash
kubectl -n aws-restart-lab scale deployment/sidecar-crash --replicas=0
```

## Production observability requirements

Capture and retain:

- Pod UID, container name, image digest, restart count, and last termination reason;
- exit code, signal, start time, and finish time;
- current and previous container logs;
- requests, limits, working set, throttling, and OOM counters;
- node pressure, kernel/runtime events, drain and interruption signals;
- Deployment, ReplicaSet, rollout revision, and change annotations;
- liveness, readiness, and startup probe failures separately;
- Pod replacement rate separately from in-place container restart rate.

For Amazon EKS, map the Kubernetes evidence to CloudWatch Container Insights, control-plane logs where relevant, node/runtime telemetry, deployment changes, and application traces. Dashboards accelerate correlation but do not replace raw evidence.

## Adversarial follow-ups

### The probe never failed, so why did the container restart?

Liveness failure is only one restart cause. The process can exit, receive a signal, exceed its memory limit, or be replaced independently of probe results.

### Why does `kubectl get pods` show `Running`?

Pod phase is coarse. A container can restart repeatedly inside a Pod that returns to `Running`. Read `containerStatuses`, `lastState`, restart counts, and events.

### Why not just increase the memory limit?

That can be a bounded mitigation when capacity and failure risk are understood, but it may only delay a leak and can increase node-level blast radius. Recovery needs stable memory behavior under representative load.

### What if `kubectl logs --previous` is empty?

The old container logs may already be rotated or unavailable. Use centralized logs, runtime logs, node evidence, termination metadata, core dumps where approved, and reproduce safely. Then fix retention so the next incident preserves the failed instance.

## Interview answer drill

> I would first distinguish container restart from Pod replacement and identify the exact container. I would preserve `lastState.terminated`, exit code, signal, previous logs, events, resource limits, Pod UID, node, owner, and rollout version before restarting anything. Healthy readiness proves only that a probe succeeded at a point in time; it does not exclude OOM, process exit, sidecar failure, eviction, node disruption, or controller replacement. I would mitigate the evidenced cause, then prove recovery through restart rate, memory stability, user-facing SLIs, and a representative load window.

## Cleanup

```bash
kubectl delete namespace aws-restart-lab
```

## Related material

- [`tracks/aws/round-2/12-pods-restart-probes-healthy.md`](../../../tracks/aws/round-2/12-pods-restart-probes-healthy.md)
- [`core/linux/03-memory.md`](../../../core/linux/03-memory.md)
- [`core/linux/06-observability-debugging.md`](../../../core/linux/06-observability-debugging.md)
