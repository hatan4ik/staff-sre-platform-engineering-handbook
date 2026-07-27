# Lab 1 — Cohort-Specific Failure After a Successful Deployment

## Interview scenario

A deployment completed successfully, all Pods are `Running` and `Ready`, and aggregate availability still looks acceptable. A subset of users reports HTTP 503 responses.

The lab creates:

- three stable `v1` Pods;
- one canary `v2` Pod;
- one Kubernetes Service selecting both versions;
- a defect in `v2` that returns `503` only for requests with `X-Cohort: beta`.

The important lesson is that neither deployment success nor aggregate health proves that every cohort and code path works.

## Safety invariant

> A rollout must not expand while any protected cohort has a statistically meaningful regression in user-visible success rate or latency.

## Prerequisites

- a disposable Kubernetes cluster;
- `kubectl`;
- Python 3.11 or newer.

## 1. Deploy the healthy and defective versions

```bash
kubectl apply -f manifests.yaml
kubectl -n aws-incident-labs rollout status deployment/cohort-api-v1
kubectl -n aws-incident-labs rollout status deployment/cohort-api-v2
kubectl -n aws-incident-labs get pods -L version
```

Expected topology:

```text
Service cohort-api
  ├── v1 Pod
  ├── v1 Pod
  ├── v1 Pod
  └── v2 Pod  <-- beta requests fail here
```

## 2. Create a local request path

Run this in one terminal:

```bash
kubectl -n aws-incident-labs port-forward service/cohort-api 8080:80
```

Run the cohort probe in another terminal:

```bash
python3 probe.py --url http://127.0.0.1:8080 --requests 200
```

The probe groups results by both cohort and serving version. A typical result looks like:

```text
cohort=general version=v1 success=...
cohort=general version=v2 success=...
cohort=beta    version=v1 success=...
cohort=beta    version=v2 failure=...
```

Exact counts vary because Service routing is not a fixed 75/25 guarantee.

## 3. Investigate as an incident commander

Do not begin by restarting Pods. Build a cohort matrix.

```bash
kubectl -n aws-incident-labs get deployment,pod,service,endpointslice -o wide
kubectl -n aws-incident-labs get pods -L version,pod-template-hash
kubectl -n aws-incident-labs describe deployment cohort-api-v2
kubectl -n aws-incident-labs logs deployment/cohort-api-v2 --tail=100
```

Questions to answer from evidence:

1. Is failure correlated with geography, identity, tenant, device, request header, version, Pod, or node?
2. Can the same logical request succeed against `v1` and fail against `v2`?
3. Are readiness checks exercising the failing business path?
4. Did the rollout expand despite a cohort-specific regression?
5. Can the bad version be removed without changing unrelated infrastructure?

## 4. Apply the smallest reversible mitigation

Remove only the defective canary from service:

```bash
kubectl -n aws-incident-labs scale deployment/cohort-api-v2 --replicas=0
kubectl -n aws-incident-labs rollout status deployment/cohort-api-v2
python3 probe.py --url http://127.0.0.1:8080 --requests 100
```

Recovery is proven only when:

- beta success rate returns to baseline;
- general-cohort success remains stable;
- no new failing version is still receiving traffic;
- latency and saturation remain acceptable after capacity is reduced.

## 5. Restore the experiment

```bash
kubectl -n aws-incident-labs scale deployment/cohort-api-v2 --replicas=1
```

## Production controls

A Staff-level prevention plan includes:

- progressive delivery with explicit canary analysis;
- business-transaction and cohort dimensions in metrics;
- immutable version, image digest, Pod UID, node, AZ, and trace correlation;
- synthetic checks for protected user journeys rather than `/health` only;
- rollout abort criteria based on error-budget burn;
- schema and feature-flag compatibility checks;
- a tested one-command rollback or traffic-removal path;
- bounded metric cardinality through controlled dimensions and exemplars.

## Adversarial follow-ups

### Why did readiness remain green?

The readiness endpoint proved that the process could answer a shallow health request. It did not exercise the beta authorization or business path.

### Why not restart all Pods?

A broad restart destroys evidence, creates additional churn, and may redistribute the same defective version. The evidence points to a version-and-cohort intersection, so mitigation should target that boundary.

### What if the canary is only one percent of traffic?

Aggregate error rate may remain below a global alarm threshold while a protected cohort experiences severe failure. Rollout analysis needs per-cohort guardrails and minimum sample requirements.

### What if no version header is available?

Correlate through trace resource attributes, deployment annotations, Pod metadata, target health, access logs, and matched requests. Then make version identity a required telemetry attribute.

## Interview answer drill

> I would treat this as a cohort-isolation problem, not a generic deployment failure. I would freeze expansion, preserve evidence, and compare matched healthy and failing requests across version, Pod, AZ, tenant, geography, identity path, and feature flags. A successful deployment and green readiness prove only control-plane convergence and a shallow health check. Once evidence identifies a bad version-and-cohort intersection, I would remove only that version from traffic, prove recovery using cohort success rate and latency, and then add progressive-delivery checks that exercise the protected business path before future expansion.

## Cleanup

```bash
kubectl delete namespace aws-incident-labs
```

## Related chapter

- [`tracks/aws/round-2/09-subset-users-fail-after-deployment.md`](../../../tracks/aws/round-2/09-subset-users-fail-after-deployment.md)
