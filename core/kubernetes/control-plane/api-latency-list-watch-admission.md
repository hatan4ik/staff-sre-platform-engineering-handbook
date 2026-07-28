# Kubernetes Control-Plane Latency: API Server, LIST/WATCH, Admission, and Controllers

## Purpose

This chapter provides a company-neutral method for diagnosing Kubernetes API latency when worker nodes and application data paths remain healthy. It separates API-server pressure, etcd latency, admission latency, controller behavior, client misuse, and telemetry distortion.

## Staff/Principal answer

> I first determine whether this is a control-plane incident, a client-specific problem, or a symptom of a broader dependency issue. I compare API-server request latency and inflight requests by verb, resource, user agent, and response code; inspect etcd commit and backend latency; identify expensive LIST operations, watch churn, admission webhook delays, and controller retry storms; and correlate the onset with deployments, CRD changes, GitOps reconciliation, or automation. I protect the control plane before chasing root cause: pause noisy reconcilers, reduce concurrency, disable or fail open only an explicitly approved noncritical webhook, and preserve read and write capacity for recovery operations. Recovery is validated with external API probes, LIST/WATCH convergence, controller queue depth, and deployment completion time—not node health alone.

## Failure-domain model

```text
kubectl / controllers / operators / GitOps / CI
                    |
               API endpoint
                    |
     authentication -> authorization -> admission
                    |
              API server handlers
                    |
                   etcd
                    |
      watches, caches, controllers, schedulers
```

A healthy node proves only that the kubelet and workload data plane may still operate. It does not prove that new pods can be scheduled, leases can renew on time, controllers can converge, or operators can perform recovery actions.

## First five minutes

1. State impact: which operations are slow or failing—reads, writes, exec/logs, deployments, scheduling, leader election, or all API calls?
2. Establish a known-good external probe from outside the cluster and a second probe from an in-cluster client.
3. Split by verb and resource: GET versus LIST versus WATCH versus mutating requests.
4. Split by user agent and identity to identify one noisy controller or automation client.
5. Freeze nonessential changes and preserve evidence before restarting components.

## Evidence hierarchy

### API-server evidence

Inspect:

- request duration histograms by verb, resource, scope, and response code;
- inflight mutating and read-only requests;
- API Priority and Fairness queueing and rejection;
- request terminations, timeouts, and 429 responses;
- audit events for expensive or repeated operations;
- user-agent and identity concentration;
- admission webhook duration and failure counts.

Example PromQL patterns:

```promql
histogram_quantile(
  0.99,
  sum by (le, verb, resource) (
    rate(apiserver_request_duration_seconds_bucket[5m])
  )
)
```

```promql
sum by (request_kind) (apiserver_current_inflight_requests)
```

```promql
sum by (name, type) (
  rate(apiserver_admission_webhook_admission_duration_seconds_count[5m])
)
```

Metric names and labels vary by Kubernetes version and managed-service exposure. Verify the available schema rather than copying a dashboard blindly.

### etcd evidence

Look for:

- leader changes;
- commit and WAL fsync latency;
- backend commit latency;
- database size and fragmentation;
- slow range requests;
- network latency between API servers and etcd;
- quota or storage alarms.

Do not assume every API-server latency event is an etcd event. Authentication, authorization, admission, serialization, LIST response size, and APF queueing can dominate before storage.

### Client and controller evidence

Common causes include:

- unbounded LIST polling instead of shared informers;
- watches repeatedly disconnecting and relisting;
- controllers with excessive worker concurrency;
- retry loops without jitter or backoff;
- GitOps tools reconciling too many objects simultaneously;
- operators writing status too frequently;
- CRDs with very large objects or high cardinality;
- automation scanning all namespaces and resources;
- clients using an empty or stale resourceVersion incorrectly.

Inspect controller work queues, reconciliation duration, retries, rate limits, and user-agent request volume.

## LIST/WATCH failure mechanics

A watch is efficient only while it remains established and consumers process events fast enough. Repeated disconnects can create a relist storm:

```text
watch disconnects
    -> client performs LIST
    -> large response consumes API/etcd/network/CPU
    -> API latency rises
    -> more watches time out
    -> more clients relist
```

Containment options:

- reduce controller concurrency;
- pause a noisy deployment or GitOps Application;
- increase client timeout only after removing overload, not as the first fix;
- use shared informer caches;
- scope watches by namespace or label where correct;
- paginate large LIST operations;
- avoid frequent full-cluster discovery scans.

## Admission webhook isolation

A webhook can delay every matching write even when applications are healthy.

Check:

- webhook service endpoints;
- DNS and network reachability;
- certificate validity and CA bundles;
- webhook duration and timeout;
- `failurePolicy`, `timeoutSeconds`, `matchPolicy`, namespace selectors, and object selectors;
- whether the webhook is required for safety or merely advisory.

Safe mitigation order:

1. restore the webhook service;
2. narrow its match scope;
3. reduce timeout where appropriate;
4. scale or roll back the webhook;
5. use a preapproved fail-open path only for noncritical policy;
6. never bypass a security or safety control casually during an incident.

## API Priority and Fairness

APF protects high-value flows only when flowschemas and priority levels reflect operational priorities.

Design principles:

- isolate system-critical controllers from bulk automation;
- give recovery and break-glass identities protected capacity;
- bound queues and concurrency for low-priority clients;
- monitor rejected and queued requests by priority level;
- test overload behavior before an incident.

## Safe mitigation matrix

| Evidence | Likely cause | Safer first mitigation |
|---|---|---|
| One user agent dominates LIST | Polling/relist storm | Pause or rate-limit that client |
| Mutating requests slow; webhook latency high | Admission dependency | Restore, scale, narrow, or approved fail-open |
| Read and write latency plus etcd commit latency | Storage/control-plane pressure | Stop change load; engage managed-control-plane support; reduce noisy clients |
| 429s concentrated in low-priority flows | APF saturation | Reduce client concurrency and correct APF policy |
| CRD requests dominate payload and latency | Oversized/high-churn CRDs | Pause writer, reduce status churn, redesign schema |
| Deployments slow but raw GET remains fast | Controller/scheduler queues | Inspect controller queues, leader election, scheduler and webhooks |

## Recovery validation

Declare recovery only after:

- external API probe latency and success rate recover;
- mutating and read-only latency return below objectives;
- 429s and timeouts stop burning the control-plane SLO;
- watches remain stable without relist spikes;
- controller and scheduler queues drain;
- a canary deployment, scale operation, and rollback complete successfully;
- no temporary bypass remains undocumented.

## Preventive controls

- control-plane SLOs for read, write, watch stability, scheduling, and deployment convergence;
- request budgets per controller and automation identity;
- load tests for CRDs, admission, GitOps, and fleet-wide changes;
- APF policy with protected recovery identities;
- dashboards that preserve verb/resource/user-agent dimensions;
- alerts on relist amplification, webhook latency, and controller retry storms;
- runbooks with explicit pause and rollback commands;
- managed-service escalation paths and evidence packages.

## Adversarial follow-ups

**Why not restart every controller?**  
Because restarting can synchronize relists and amplify load. Pause or reduce the identified noisy client first and preserve evidence.

**Nodes are Ready, so why is this severe?**  
Existing workloads may continue, but scheduling, deployments, scaling, lease renewal, policy, and recovery actions can fail. The system is operationally frozen and may degrade further.

**Would you increase API-server capacity?**  
In a self-managed cluster that may be one lever; in a managed control plane it may require provider action. In either case, adding capacity without stopping pathological clients can only postpone recurrence.

## Weak answers to avoid

- “Restart the control plane.”
- “Nodes are healthy, so Kubernetes is healthy.”
- “Increase all client timeouts.”
- “Disable every webhook.”
- “It must be etcd.”
- “Use one average API latency graph.”
