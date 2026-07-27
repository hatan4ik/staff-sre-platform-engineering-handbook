# Disposable Kubernetes Scheduling, DNS, Probe, and Drain Conformance Lab

This lab creates or reuses a three-node Kind cluster and validates several real Kubernetes control loops rather than only simulating them.

## Invariants tested

- an impossible hard placement constraint produces `FailedScheduling` evidence;
- cluster DNS resolves the Service name;
- Service traffic reaches Ready EndpointSlice endpoints;
- forcing one pod unready removes it from new Service traffic while another endpoint remains;
- liveness failure restarts the container;
- startup protection allows a three-second warm-up without premature restart;
- SIGTERM makes readiness false, emits drain evidence, and exits within the termination grace period;
- the Deployment returns to two Ready endpoints after replacement;
- the PodDisruptionBudget preserves at least one available replica during voluntary disruption.

## Requirements

- Docker
- `kind`
- `kubectl`
- network access for the cluster to pull the pinned workload images

## Run

```bash
cd labs/kubernetes/02-kind-conformance
chmod +x run.sh
./run.sh
```

By default the Kind cluster remains available for inspection.

Delete it automatically after the run:

```bash
KEEP_CLUSTER=false ./run.sh
```

Use an existing cluster instead of creating Kind:

```bash
CREATE_CLUSTER=false ./run.sh
```

The current `kubectl` context is used when `CREATE_CLUSTER=false`; use a disposable cluster because the lab creates a namespace and intentionally injects probe and scheduling failures.

## Evidence to inspect

```bash
kubectl get pods -n sre-conformance -o wide
kubectl get endpointslice -n sre-conformance -o yaml
kubectl get events -n sre-conformance --sort-by=.lastTimestamp
kubectl logs -n sre-conformance deploy/probe-demo
```

## Safety

- all workload objects are isolated in the `sre-conformance` namespace;
- the impossible pod requests minimal resources and is deleted after evidence is captured;
- the liveness fault is a file inside one container and disappears on restart;
- the readiness fault affects one pod at a time;
- the graceful-drain test deletes one pod while the Deployment and PDB preserve service capacity;
- no cloud resources are created unless the selected Kubernetes environment does so independently.

## Interview exercise

Explain why:

1. a Pending pod is not automatically a capacity shortage;
2. pod readiness and EndpointSlice propagation are separate transitions;
3. liveness should test local recoverability rather than a shared dependency;
4. existing connections may outlive endpoint removal;
5. graceful shutdown needs application signal handling, not only a long grace period;
6. a PDB does not protect against every involuntary failure.
