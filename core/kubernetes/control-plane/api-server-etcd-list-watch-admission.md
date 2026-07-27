# Kubernetes Control-Plane Scaling, API Latency, and Failure Isolation

This chapter is the canonical, provider-neutral foundation for Kubernetes API-server, etcd, admission, LIST/WATCH, controller, and control-plane latency questions.

## Interview answer in 90 seconds

> I first separate control-plane latency from application data-plane latency. Healthy nodes and running pods do not prove the Kubernetes API is healthy. I measure the user-visible API symptoms, then decompose the request path into authentication, authorization, admission, API-server queuing, storage, watch delivery, and controller reconciliation. I compare affected verbs, resources, clients, namespaces, and time windows. High LIST volume, slow or unavailable admission webhooks, expensive authorization, etcd latency, oversized objects, and controller retry storms are common causes. I stabilize by reducing nonessential writers and relisters, failing or bypassing only explicitly safe admission paths, restoring etcd headroom, and protecting critical control-plane traffic with API Priority and Fairness. Recovery is proven by API latency, watch freshness, controller work-queue depth, and successful end-to-end reconciliation—not by node health alone.

## The control-plane request path

```text
kubectl / controller / scheduler / operator
                 |
                 v
          load balancer or endpoint
                 |
                 v
             API server
      +----------+-----------+
      |          |           |
      v          v           v
 authentication authorization admission
      |          |           |
      +----------+-----------+
                 |
                 v
       API Priority and Fairness
                 |
                 v
       validation and conversion
                 |
                 v
          storage interface
                 |
                 v
               etcd
                 |
                 v
      watches and controller queues
                 |
                 v
      reconciliation and observed state
```

A request can be accepted quickly while the desired change takes a long time to become real. Therefore measure both API request latency and reconciliation latency.

## Start with scope, not guesses

Clarify:

- Is the slow endpoint the Kubernetes API or a customer application API?
- Are reads, writes, LISTs, WATCHes, or all verbs affected?
- Is latency global, resource-specific, namespace-specific, or client-specific?
- Did the issue begin after a deployment, CRD change, webhook change, operator rollout, or fleet event?
- Are failures timeouts, throttles, 429s, 5xx responses, expired watches, or stale reconciliation?
- Is this one cluster, one control-plane replica, one region, or a fleet-wide pattern?

## Primary latency domains

### 1. Client behavior

Bad clients can overload a healthy control plane.

Typical patterns:

- repeated full LIST operations instead of long-lived WATCHes;
- very short reconnect loops after watch closure;
- no jitter across replicas;
- broad cluster-wide watches when namespace scope is sufficient;
- controllers that retry failed writes without backoff;
- polling for status that is already available through watches;
- large concurrency after restart, leader election, or credential rotation.

Measure requests by user agent, service account, verb, resource, response code, and latency.

### 2. Authentication and authorization

Potential sources:

- slow external identity or webhook integrations;
- high-cost authorization checks;
- excessive SubjectAccessReview traffic;
- token validation or issuer failures;
- certificate expiry or trust-chain problems;
- node or workload identities generating unexpected request volume.

A security control must not be disabled casually. Preserve an auditable break-glass path and narrow any bypass to a known-safe operation.

### 3. Admission webhooks

Admission is synchronous on the API write path.

Failure signatures:

- CREATE or UPDATE latency rises while GET remains healthy;
- timeouts align with a specific webhook timeout;
- one resource type is affected more than others;
- webhook pods, services, endpoints, DNS, or certificates are unhealthy;
- a webhook has broad rules and receives objects it does not need;
- multiple serial webhooks multiply latency.

Design principles:

- scope rules narrowly by operation, resource, namespace, and selector;
- choose `failurePolicy` based on real risk, not convenience;
- set bounded timeouts;
- run multiple replicas across failure domains;
- avoid circular dependencies on the workloads the webhook blocks;
- test certificate rotation and control-plane-to-webhook network paths;
- use native admission features where they reduce external dependency risk.

### 4. API Priority and Fairness

API Priority and Fairness protects critical request classes from noisy clients.

Staff-level reasoning:

- identify which flows must retain capacity during overload;
- distinguish queueing from execution saturation;
- ensure critical controllers, nodes, and incident responders are not starved;
- test priority behavior under realistic relist and writer storms;
- monitor rejected, queued, and executing requests by flow schema and priority level.

Do not use priority to hide an unlimited client. Fix the source while preserving critical control-plane progress.

### 5. Conversion and object size

CRDs can create hidden control-plane cost.

Watch for:

- expensive conversion webhooks;
- very large custom resources;
- status fields that grow without bounds;
- excessive managed fields;
- high-cardinality object churn;
- controllers storing operational logs or history in API objects.

Kubernetes objects are coordination state, not a general-purpose event store.

### 6. etcd

Etcd health directly affects durable API operations.

Important evidence:

- request and commit latency;
- disk fsync latency;
- leader changes;
- database size and fragmentation;
- backend quota alarms;
- compaction and defragmentation behavior;
- network latency between API servers and etcd;
- resource contention on control-plane hosts;
- slow range queries caused by broad LISTs.

Never treat defragmentation as a reflexive incident command. It can consume I/O and should follow platform-specific operational guidance.

### 7. Watches and controller reconciliation

The API may recover before controllers catch up.

Measure:

- watch freshness and reconnect rate;
- resource-version age;
- controller work-queue depth;
- oldest queued item age;
- reconciliation latency;
- retries and rate-limiter delays;
- leader-election stability;
- scheduler pending-work latency;
- endpoint and configuration propagation time.

## Incident workflow

### Step 1 — State impact

Examples:

- deployments cannot progress;
- autoscaling decisions are delayed;
- nodes cannot renew state or publish status;
- operators are stale;
- application traffic remains healthy but change safety is degraded;
- the cluster cannot recover from unrelated failures because controllers are behind.

### Step 2 — Protect evidence

Capture:

- API latency and response-code distributions;
- request volume by verb, resource, user agent, and identity;
- audit samples where safe;
- webhook latency and rejection metrics;
- API Priority and Fairness queue metrics;
- etcd latency and alarms;
- controller and scheduler queue metrics;
- recent CRD, webhook, operator, and policy changes.

### Step 3 — Bound the blast radius

Compare:

- GET versus LIST versus WATCH versus writes;
- built-in resources versus CRDs;
- one namespace versus cluster scope;
- one client or controller versus all clients;
- one admission chain versus all writes;
- one cluster versus the fleet;
- one API-server replica or zone versus all replicas.

### Step 4 — Stabilize safely

Possible mitigations, in preferred order:

1. stop or scale down a confirmed noisy noncritical client;
2. pause a rollout or operator creating abnormal churn;
3. restore unhealthy webhook endpoints or DNS/certificate paths;
4. narrow an admission rule or use an approved bypass for a specific safe resource;
5. protect critical traffic through API Priority and Fairness;
6. reduce controller concurrency when it creates a retry storm;
7. restore control-plane storage or compute headroom using supported procedures;
8. block nonessential changes until reconciliation debt is cleared.

Avoid restarting every controller simultaneously; synchronized relists can worsen the incident.

## Useful investigation commands

```bash
# Identify slow client-side operations.
kubectl get --raw='/readyz?verbose'
kubectl get --raw='/livez?verbose'

# Inspect admission configuration.
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations
kubectl describe validatingwebhookconfiguration <name>

# Inspect APF objects.
kubectl get prioritylevelconfigurations,flowschemas

# Inspect APIService and aggregated API health.
kubectl get apiservices
kubectl describe apiservice <name>

# Look for controller symptoms.
kubectl get events -A --sort-by=.lastTimestamp
kubectl get pods -A -o wide
kubectl logs -n <namespace> deploy/<controller> --since=15m

# Inspect large resources carefully.
kubectl get <resource> -A -o json | wc -c
```

Managed Kubernetes providers may not expose etcd or API-server logs directly. In that case use provider control-plane metrics, audit logs, service-health evidence, and support escalation while still analyzing client and webhook behavior under your control.

## SLOs and operational signals

A mature control-plane reliability model includes:

- API request success rate by verb and resource class;
- p50, p95, and p99 latency by verb;
- watch freshness and reconnect rate;
- admission latency and timeout rate;
- APF queue wait and rejection rate;
- controller reconciliation latency;
- scheduler decision latency;
- oldest work-queue item age;
- desired-state-to-observed-state convergence time;
- etcd commit and range latency where visible.

Protect a small set of critical flows rather than relying on one aggregate API latency number.

## Capacity and scale testing

Test with realistic objects and clients:

- controller restart and fleet-wide relist;
- CRD conversion and schema changes;
- webhook failure and certificate rotation;
- large deployment waves;
- node churn and autoscaling bursts;
- secret or configuration rotation;
- watch disconnections and reconnect storms;
- incident-responder access during overload.

Record the maximum sustainable request mix, not just requests per second.

## Weak answers to avoid

- “Nodes are healthy, so EKS/Kubernetes is healthy.”
- “Restart the API server.”
- “Scale etcd” without evidence or provider control.
- “Disable all admission webhooks.”
- “Increase every timeout.”
- “Use more replicas” without identifying the saturated stage.
- “429 means the system is broken.” Controlled throttling may be protecting it.

## Adversarial follow-ups

### Why can application traffic remain healthy during a control-plane incident?

Existing proxies, endpoints, routes, and workloads may continue serving from previously converged state. The danger is that deployment, failover, autoscaling, repair, and policy changes stop progressing.

### Why are LIST storms dangerous?

They consume CPU, memory, serialization, network, and storage range-query capacity, then often trigger more watch setup and controller work.

### When is fail-open admission acceptable?

Only when the risk analysis says availability is safer than blocking, the bypass is bounded, the resulting objects remain auditable, and compensating detection exists. Security-critical or invariant-enforcing admission may need fail-closed behavior.

### What proves recovery?

User/API success and latency recover, watches are fresh, critical controller queues drain, desired state converges, and no hidden reconciliation debt remains.

## Principal-level design review checklist

- one owner for each controller and admission policy;
- bounded client concurrency and exponential backoff with jitter;
- narrow watches and admission rules;
- protected critical traffic classes;
- control-plane SLOs tied to reconciliation outcomes;
- tested webhook and aggregated-API failure modes;
- object-size and CRD lifecycle governance;
- provider escalation and evidence procedures;
- game days for relist storms, admission outage, and control-plane degradation.
