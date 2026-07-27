# EKS API Latency Doubles While Nodes Remain Healthy

## Interview prompt

Amazon EKS API latency has doubled, but worker nodes and applications appear healthy. How do you investigate, mitigate, and prevent recurrence?

## 90-second Staff/Principal answer

I would first separate Kubernetes API-server latency from application latency. Healthy nodes do not prove that the control plane is healthy, and control-plane degradation may not immediately affect already-running workloads.

I would quantify which API operations are slow, whether the problem affects reads, writes, watches, admission, or authentication, and whether it is cluster-wide or associated with one client such as a controller, GitOps agent, CI pipeline, or observability collector. Then I would inspect EKS control-plane logs, Kubernetes API metrics where available, CloudTrail, client request rates, throttling, webhook latency, object counts, and recent changes.

The most common causes I would test are an API request storm, pathological LIST/WATCH behavior, slow or unavailable admission webhooks, excessive object cardinality, aggressive reconciliation loops, authentication or AWS API throttling, and large custom resources. I would stabilize by stopping the abusive client, scaling down nonessential controllers, bypassing or failing open a noncritical webhook only under an approved emergency procedure, and pausing deployments.

Recovery is confirmed by API latency and error rate by verb and resource, controller queue depth, successful reconciliation, and application safety. Prevention includes API budgets, client-side rate limits, webhook SLOs, controller load testing, object-count guardrails, and game days.

---

## Why healthy nodes can coexist with a slow API

Kubernetes separates the control plane from the data plane.

```text
Existing traffic:
Client -> Load balancer -> Pod
                    |
                    `-> often continues without API-server involvement

Control operations:
kubectl / controller / scheduler / operator
                    |
                    `-> Kubernetes API server
```

Already-running pods can continue serving while these operations degrade:

- deployments and rollouts
- scheduling replacement pods
- autoscaling reactions
- endpoint updates
- secret and configuration changes
- node lifecycle processing
- GitOps reconciliation
- operator-managed recovery

This creates a dangerous period in which the application looks healthy but the platform cannot safely adapt to failure.

## Assumptions

- Managed Amazon EKS control plane
- Multiple controllers and operators
- GitOps-based delivery
- EKS control-plane logging enabled or available to enable
- Applications currently serving traffic
- No assumption that AWS owns every cause merely because the control plane is managed

## Investigation model

Break the problem into five questions:

1. **What is slow?** Reads, writes, watches, authentication, admission, or all operations?
2. **Who is generating load?** Humans, CI, GitOps, controllers, agents, or compromised credentials?
3. **Where is time spent?** Client network, API server, admission webhook, storage path, or AWS identity call?
4. **What changed?** Controller version, CRD, deployment wave, audit collector, policy engine, or object volume?
5. **What is at risk now?** Scheduling, autoscaling, failover, endpoint propagation, or only administrative reads?

## STABILIZE flow

### S — State impact

Establish:

- API latency baseline and current p50/p95/p99
- error codes: `429`, `5xx`, timeouts, connection resets
- affected verbs and resources
- whether new pods can schedule
- whether HPA, Cluster Autoscaler, Karpenter, and endpoint updates still reconcile
- recent platform changes

Set an incident severity based on lost control-plane capability, not just current user traffic.

### T — Preserve evidence

Capture before restarting controllers:

```bash
kubectl get --raw='/readyz?verbose'
kubectl get --raw='/livez?verbose'
kubectl get events -A --sort-by=.lastTimestamp
kubectl get apiservices
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
kubectl get crd
```

Also preserve:

- controller logs and restart history
- GitOps reconciliation timestamps
- audit and authenticator logs
- CloudTrail events
- deployment history for platform add-ons
- request-rate metrics by client identity if available

### A — Analyze by symptom

## 1. Classify the slow operation

Examples:

```bash
time kubectl get --raw='/version'
time kubectl get pods -A --request-timeout=10s
time kubectl create --dry-run=server -f test-object.yaml
time kubectl auth can-i get pods
```

Interpretation:

| Observation | Likely direction |
|---|---|
| simple GET is slow | API saturation, network path, authentication, broad control-plane issue |
| writes slow but reads normal | admission webhook, storage/write pressure, policy engine |
| one resource type slow | large objects, CRD conversion webhook, excessive cardinality |
| one user/client slow | network, exec credential plugin, IAM/ST​S path, client throttling |
| `429 Too Many Requests` | API priority/fairness or client request overload |
| LIST slow, WATCH stable | large result sets, pagination misuse, cardinality |
| WATCH reconnect storm | controller bug, network instability, timeout configuration |

## 2. Look for abusive or malfunctioning clients

Common offenders:

- controller with a zero-delay reconciliation loop
- CI system repeatedly polling all namespaces
- observability agent performing full LIST calls
- GitOps controller managing too many resources in one wave
- custom operator losing watch state and relisting continuously
- scripts using `kubectl get ... -A` every few seconds
- clients without pagination, caching, backoff, or rate limiting

Review logs for repeated patterns and client identities. Where metrics are available, rank request volume by user agent, verb, resource, namespace, and response code.

## 3. Investigate admission webhooks

Every matching admission webhook adds a synchronous dependency to writes.

```bash
kubectl get validatingwebhookconfigurations -o yaml
kubectl get mutatingwebhookconfigurations -o yaml
kubectl get pods -A | grep -E 'webhook|policy|admission'
```

Check:

- webhook service has ready endpoints
- certificate validity and CA bundle
- timeout settings
- `failurePolicy`
- namespace and object selectors
- external dependency calls inside the webhook
- overloaded policy engine
- webhook matches more resources than intended

A webhook that calls an external database or API can turn a local cluster write into a distributed synchronous transaction.

## 4. Check aggregated APIs and conversion webhooks

```bash
kubectl get apiservice
kubectl describe apiservice <name>
```

Unhealthy aggregated API services can slow discovery and clients that refresh API resources. CRD conversion webhooks can similarly affect reads and writes for that resource.

## 5. Check object cardinality and object size

Look for:

- unusually high counts of Secrets, ConfigMaps, Events, Jobs, Pods, or custom resources
- failed cleanup controllers
- very large annotations or managed fields
- oversized CRDs
- namespace explosion
- event storms

Examples:

```bash
kubectl get pods -A --no-headers | wc -l
kubectl get events -A --no-headers | wc -l
kubectl get jobs -A --no-headers | wc -l
kubectl get secret -A --no-headers | wc -l
```

Counts alone do not prove root cause, but sharp growth correlated with latency is strong evidence.

## 6. Check identity and network path

For EKS, client access can involve AWS identity and token generation. Distinguish:

- delay before the request reaches the API
- API processing delay
- client-side credential plugin delay
- STS throttling or network issues
- private-endpoint DNS or routing issues
- proxy or firewall latency

Test from more than one network location and with a known-good identity.

## 7. Review EKS control-plane logs

Relevant log types include:

- API server
- audit
- authenticator
- controller manager
- scheduler

Search for:

- long-running requests
- admission delays
- throttling and priority/fairness behavior
- authentication failures
- repeated watch closures
- controller backlogs
- scheduler errors

Do not enable extremely verbose logging blindly during peak failure without considering cost and additional load. Use the lowest sufficient level and an approved incident procedure.

### B — Bound the blast radius

Segment by:

| Dimension | Questions |
|---|---|
| Verb | GET/LIST/WATCH vs CREATE/UPDATE/PATCH/DELETE |
| Resource | core resources vs one CRD |
| Client | controller, GitOps, CI, human, agent |
| Namespace | one tenant vs all namespaces |
| Authentication | one IAM principal vs all users |
| Network path | private endpoint vs public endpoint |
| Time | correlated with deployment, cron job, or reconciliation wave |

### I — Implement safe mitigation

Possible mitigations, in preferred order:

1. Pause nonessential deployments and automation.
2. Stop or scale down the confirmed abusive client.
3. Reduce reconciliation concurrency and client QPS/burst.
4. Disable a noisy scheduled job or polling script.
5. Restore a previous controller or webhook version.
6. Narrow webhook selectors to the intended resources.
7. Under emergency change control, change a noncritical webhook failure mode or remove it temporarily.
8. Delete runaway disposable objects in controlled batches.
9. Escalate to AWS Support with timestamps and evidence if the managed control plane remains degraded without a customer-controlled cause.

Do not restart every controller simultaneously. That can create a thundering herd of LIST/WATCH requests and worsen the incident.

### L — Validate recovery

Confirm:

- API p95/p99 returns near baseline
- `429` and timeout rates fall
- writes and reads both succeed
- scheduler and controllers drain queues
- endpoint updates propagate
- autoscaling controllers reconcile
- GitOps state converges
- a controlled test rollout succeeds
- external application SLIs remain healthy

## Failure-mode examples

### Admission webhook outage

```text
Deployment -> API server -> validating webhook -> timeout
                                      |
                                      `-> every matching write waits
```

Mitigation:

- restore webhook endpoints
- roll back webhook release
- narrow selectors
- use emergency bypass only if the policy is noncritical and risk is explicitly accepted

### Controller request storm

```text
Controller bug
  -> reconcile error
  -> immediate retry
  -> LIST all objects
  -> API latency rises
  -> watches disconnect
  -> more LIST operations
  -> positive feedback loop
```

Mitigation:

- scale controller to zero or previous version
- add exponential backoff, jitter, caching, and bounded concurrency

### Object leak

```text
CronJob creates resources
  -> cleanup fails
  -> object count grows
  -> LIST payload and watch initialization grow
  -> controllers fall behind
```

Mitigation:

- stop creator
- clean in batches
- repair retention and owner references

## API-client engineering standards

A production controller should use:

- shared informers or cached clients
- LIST pagination
- WATCH rather than frequent polling
- exponential backoff with jitter
- bounded concurrency
- explicit QPS and burst limits
- idempotent reconciliation
- context deadlines
- metrics for queue depth, retries, and reconcile duration
- leader election when only one active reconciler is required

## Admission-webhook standards

- no unnecessary external synchronous dependencies
- small timeout
- high availability across failure domains
- PodDisruptionBudget and appropriate topology spread
- narrow namespace/object selectors
- documented `failurePolicy`
- certificate-expiration monitoring
- request latency and error SLOs
- load tests at peak deployment volume
- emergency bypass procedure with security approval

## SLOs and alerts

Example control-plane SLOs:

- 99.9% of read requests complete within 1 second
- 99.9% of mutating requests complete within 2 seconds
- API error rate below 0.1%, excluding expected authorization failures
- critical controllers reconcile within 60 seconds
- endpoint changes propagate within an agreed bound

Alert on:

- sustained p99 latency by verb
- `429` rate
- webhook timeout/error rate
- controller queue depth
- watch reconnect rate
- object-count growth
- GitOps reconciliation delay
- scheduler pending-pod backlog

## AWS escalation packet

When escalating to AWS Support, provide:

- cluster ARN, Region, and Kubernetes version
- exact UTC start and end times
- affected API verbs and resources
- request IDs where available
- EKS control-plane log excerpts
- evidence that abusive clients and webhooks were checked
- public/private endpoint behavior comparison
- recent cluster configuration changes
- business impact and severity

A strong escalation is evidence-driven, not “the API feels slow.”

## Adversarial follow-ups

### “Why not restart the cluster?”

The EKS control plane is managed, and there is no customer-operated API-server pod to restart. Restarting clients without identifying the offender can amplify load through relists and watch reinitialization.

### “Nodes are healthy, so can this wait?”

No. The platform may be unable to replace failed pods, update endpoints, autoscale, or deploy fixes. Current traffic health can hide declining recovery capability.

### “Would you fail open every admission webhook?”

No. Security-critical policy may need to fail closed. The choice is a pre-approved risk decision per webhook, not an incident-time blanket action.

### “What if only `kubectl` is slow?”

I compare multiple clients and network paths. The delay may be local credential generation, proxying, DNS, or STS rather than the Kubernetes API server.

### “Would you enable all control-plane logs during the incident?”

Only with a cost and load-aware plan. I prefer already-enabled logs, targeted evidence, and minimal necessary changes.

## Weak answers to avoid

- “EKS is managed, so open an AWS ticket.”
- “Restart all controllers.”
- “Nodes are healthy, therefore production is healthy.”
- disabling security webhooks without explicit risk approval
- deleting large resource sets without rate limits and backups
- diagnosing from average latency alone
- ignoring client-side token and network delay

## Staff-level close

A managed control plane still has customer-controlled load, admission dependencies, clients, and object models. I identify the exact slow operation, attribute request pressure to a client or dependency, stabilize without causing a relist storm, and verify that the cluster has regained not only responsiveness but also its ability to schedule, reconcile, scale, and recover.