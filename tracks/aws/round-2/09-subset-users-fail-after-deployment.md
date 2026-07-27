# Question 9 — Deployment Succeeds, but Only a Subset of Users Fail

## Interview prompt

A deployment succeeds, but only a subset of users experiences failures. How do you determine whether the issue is related to AWS infrastructure, networking, Kubernetes, or the application?

## What the interviewer is testing

This question tests cohort reasoning. Aggregate dashboards often look healthy because most users succeed. The strongest answer constructs a failure matrix, compares failing and healthy requests, and finds the first dimension that separates them.

The objective is not to prove one technology guilty. It is to identify the failure boundary with evidence and restore the affected cohort without widening impact.

---

## 90-second Staff/Principal answer

> I start by defining the subset precisely. I compare failing and successful users across geography, ISP, IPv4 versus IPv6, tenant, account age, authentication flow, feature flag, device or client version, AZ, cell, pod version, and data shard. I capture one failing and one successful request with timestamps, DNS answers, endpoint, HTTP status, request and trace IDs, and deployment version.
>
> I then build a cohort matrix from logs, traces, load-balancer access logs, WAF logs, and application telemetry. If failures correlate with geography or resolver, I inspect Route 53 routing, CDN behavior, TLS, and edge rules. If they correlate with AZ, subnet, target, or node, I inspect target health, security groups, NACLs, routes, VPC Flow Logs, pod placement, and dependency paths. If they correlate with pod version, feature flag, tenant, or data shard, I focus on the release, configuration, authorization, schema compatibility, and state.
>
> In Kubernetes I compare Service and EndpointSlice selection, readiness, rollout state, topology spread, NetworkPolicy, sidecars, and ConfigMap or Secret revisions. I do not trust “deployment succeeded” as proof; it only means the controller reached its rollout condition. I mitigate by stopping the rollout, routing away from the failing cell or version, disabling the feature flag, or restoring compatible configuration, and I verify recovery specifically for the affected cohort.

---

## 1. Define “subset” as measurable dimensions

Possible user-side dimensions:

- country, Region, metro, or ISP
- recursive DNS resolver
- IPv4 versus IPv6
- mobile versus desktop
- browser, operating system, or SDK version
- authenticated versus anonymous
- new versus long-lived session
- customer tier
- tenant, account, or organization
- feature-flag cohort
- language or locale
- request payload size or operation type

Possible platform-side dimensions:

- Route 53 answer or edge location
- CloudFront cache behavior
- WAF rule label
- load-balancer listener or target group
- Availability Zone
- subnet
- EKS cluster or cell
- node group, instance type, AMI, or capacity type
- pod version, replica, or sidecar revision
- database shard or read replica
- cache shard
- dependency endpoint

The first task is to convert “some users” into a queryable set.

---

## 2. Capture paired evidence

Choose one failing and one healthy transaction that should be functionally equivalent.

Record:

```text
UTC timestamp
user or tenant pseudonymous identifier
client geography and network
hostname and resolved address
IPv4/IPv6 path
edge location or accelerator endpoint
TLS result
HTTP route, status, and latency
load balancer request ID
application request ID
trace ID
cluster, namespace, pod, node, AZ, and application version
feature flags and configuration version
primary data shard or dependency endpoint
```

Do not put personal or secret data into incident artifacts. Use safe identifiers.

---

## 3. Build the cohort matrix

Example:

| Dimension | Failing | Healthy | Interpretation |
|---|---:|---:|---|
| App version `v2.14` | 96% | 8% | Release strongly implicated |
| AZ `us-east-1c` | 83% | 31% | Zonal or placement correlation |
| IPv6 | 100% | 0% | AAAA, listener, firewall, or client path |
| Feature `new-checkout` | 91% | 4% | Feature path or data compatibility |
| Tenant shard 7 | 88% | 6% | Data or shard-specific dependency |
| WAF rule `managed-xss` | 72% | 1% | Edge filtering false positive |

Use counts and rates. A dimension with many failures may simply carry most traffic.

### Conditional correlation

Suppose all `v2.14` pods are in one AZ. Version and AZ are confounded. Compare:

- `v2.14` in different AZs
- old version in the suspect AZ
- same tenant across versions
- same route across feature states

Avoid concluding from one coincidental dimension.

---

## 4. Start with the release topology

Inspect:

```bash
kubectl rollout status deployment/<name> -n <namespace>
kubectl rollout history deployment/<name> -n <namespace>
kubectl get rs,pods -n <namespace> -l app=<app> -o wide
kubectl describe deployment/<name> -n <namespace>
```

Questions:

- Are old and new ReplicaSets serving simultaneously?
- What percentage of endpoints run each image digest?
- Are versions evenly distributed across AZs and nodes?
- Did the rollout use max surge and max unavailable settings safely?
- Did canary analysis cover the affected route and cohort?
- Were configuration, schema, sidecar, or secret changes deployed separately?
- Did readiness become true before the application was functionally warm?

A rollout can be marked successful while a small but important business path is broken.

---

## 5. AWS infrastructure indicators

### Geography or resolver correlation

Inspect:

- Route 53 routing policy and record answers
- DNS query logs where enabled
- CloudFront edge and origin behavior
- Global Accelerator endpoint-group routing
- regional endpoint health
- certificate and TLS compatibility

Typical failures:

- one latency-routing Region points to an old endpoint
- stale weighted record
- one CloudFront behavior uses a different origin
- IPv6 answer points to an endpoint without equivalent policy
- geo restriction or WAF rule affects one country

### Availability Zone correlation

Inspect:

- load-balancer target health by AZ
- target response time and errors by target
- subnet free IPs
- NAT gateway and endpoint paths
- route-table association
- security groups and NACLs
- VPC Flow Logs
- node and pod placement
- zonal database or cache dependency

Use Reachability Analyzer for modeled configuration and Flow Logs for observed traffic.

### Account or tenant isolation correlation

Inspect:

- IAM policy conditions
- KMS grants
- resource policies
- API Gateway usage plans if present
- per-tenant quotas
- shard mapping
- Secrets Manager resource tags or ABAC

A production change can unintentionally deny only resources with one tag or path.

---

## 6. Networking indicators

### IPv4 versus IPv6

Check:

- A and AAAA records
- dual-stack load-balancer configuration
- IPv6 routes
- security-group IPv6 rules
- NACL IPv6 rules
- application bind addresses
- client libraries and proxy support

A successful IPv4 synthetic does not prove IPv6 health.

### MTU and payload-size correlation

Failures only for large requests or responses may indicate:

- Path MTU discovery problems
- blocked ICMP behavior
- proxy or load-balancer header/body limits
- application upload limits
- fragmentation behavior

Compare small and large payloads through the exact user path.

### Connection reuse and long-lived sessions

Only existing sessions may fail because of:

- deregistration and drain behavior
- WebSocket or gRPC connection handling
- expired certificate or token on reconnect
- sticky-session routing
- old endpoint DNS cache

Only new sessions may fail because of:

- authentication dependency
- cold connection pool
- DNS or TLS handshake
- new session state schema

### Source-IP policy

Inspect WAF, security-group, proxy, or downstream allow-list assumptions. Global Accelerator, CloudFront, load balancers, NAT, and proxies alter which source identity is visible at each layer.

---

## 7. Kubernetes indicators

### Service selectors and EndpointSlices

```bash
kubectl get svc <service> -n <namespace> -o yaml
kubectl get endpointslice -n <namespace> \
  -l kubernetes.io/service-name=<service> -o yaml
```

Check:

- expected pod labels
- ready condition
- endpoint zone
- port name and target port
- version mix

A selector mistake can include an unintended pod set or exclude the canary.

### Readiness

Readiness may be too shallow or become true before:

- configuration loads
- cache warms
- schema compatibility is confirmed
- external credentials are usable
- all route handlers are ready

Compare failures by pod age.

### Topology

Inspect:

- topology-spread constraints
- anti-affinity
- node selectors
- taints and tolerations
- zone skew

A rollout may accidentally place every new pod in one AZ or one node group.

### NetworkPolicy

A new version label may match a default-deny policy but not the allow policy.

Test from the affected pod to the dependency and inspect policy selectors.

### ConfigMap, Secret, and projected configuration

Compare checksums or revisions mounted by old and new pods.

Common failure:

```text
new image + old configuration = failure
old image + new configuration = failure
```

Deployments and configuration changes need compatibility contracts.

### Sidecars and mesh revision

Compare:

- sidecar image and control-plane revision
- route configuration
- mTLS identity
- retry and timeout policy
- egress restrictions

Only pods injected after the deployment may receive the new sidecar revision.

---

## 8. Application indicators

### Version correlation

Query error rate by image digest, not only tag.

A mutable tag can make two apparently identical pods run different content.

### Feature flags

Check:

- flag evaluation result
- targeting rule
- default behavior when the flag service is unavailable
- local cache age
- percentage rollout
- tenant attributes

A feature flag is a distributed configuration system and can create selective outages.

### Authentication and authorization

Failures may affect:

- tokens issued before or after key rotation
- one identity provider
- one tenant claim shape
- one role or permission set
- clock-skewed clients

Inspect token issuer, key ID, audience, expiry, and authorization decision without exposing token content.

### Schema compatibility

A subset may have older or unusual data.

Examples:

- null value not expected by new code
- old enum value
- tenant-specific customization
- partially migrated row
- read replica lag
- cache contains old serialization format

Compare the same operation against representative data cohorts.

### Session affinity

Sticky sessions can concentrate users on one bad pod or version.

Check:

- load-balancer cookie behavior
- application session store
- pod replacement
- cookie expiration
- WebSocket connection age

### Idempotency and duplicate behavior

Only users retrying after timeout may hit duplicate-key or state-transition failures. Inspect idempotency keys, retry count, and partial transaction state.

---

## 9. Data and dependency indicators

### Shard or partition correlation

Map failing tenants or keys to:

- database shard
- DynamoDB partition-key pattern
- cache shard
- Kafka or Kinesis partition
- regional dependency

Check throttling, latency, errors, and recent failover for that partition.

### Read/write split

Only write users may fail due to writer saturation while readers succeed.

Only read users may fail if a reader endpoint or replica is stale or unavailable.

### Third-party provider cohort

One geography or tenant may use a different payment, identity, notification, or compliance provider. Compare dependency spans by provider.

---

## 10. Logs and traces

### Load-balancer access logs

Group by:

- target IP
- target status
- request path
- user agent
- source range
- target group
- TLS protocol

### Structured application logs

Query by safe cohort dimensions:

```text
version
pod
AZ
route template
status code
error class
feature flag
shard
identity provider
```

### Distributed traces

Compare one failing and healthy trace for the same operation.

Ask:

- Do they enter the same service version?
- Does the failing trace stop at the edge or enter the application?
- Which dependency differs?
- Is there a retry or fallback only in one cohort?
- Is a span missing because instrumentation differs by version?

---

## 11. Decision framework by correlation

| Strongest correlation | First investigation direction |
|---|---|
| Geography/resolver | Route 53, CDN, edge, TLS, WAF |
| IPv6 | AAAA, dual-stack listener, IPv6 SG/NACL/routes |
| AZ/subnet | targets, routes, NACL, SG, NAT, pod placement, zonal dependency |
| Pod or node | runtime, CNI, kernel/AMI, local sidecar, connection pool |
| App version | code, configuration, schema, sidecar, feature behavior |
| Tenant/shard | data, partition, authorization, tenant customization |
| New sessions | auth, DNS/TLS, session creation, connection pools |
| Existing sessions | stickiness, drain, stale token, old connection, session schema |
| Payload size | MTU, proxy limits, application limits |

This table guides the first hypothesis; it does not replace evidence.

---

## 12. Mitigation options

### Version-specific failure

- pause rollout
- route canary weight to zero
- revert desired image digest
- preserve traces and logs from failed version

### Feature-specific failure

- disable the flag
- restore last known-good targeting rule
- verify cache propagation

### AZ or cell failure

- remove affected targets or reduce cell traffic
- ensure destination capacity before shifting
- validate stateful dependency routing

### WAF false positive

- switch suspect rule from block to count
- narrow the rule exception
- retain logs for security review

### Data-shard failure

- route to healthy replica only if consistency permits
- shed optional operations
- repair or fail over the shard using its documented procedure

### Authentication compatibility

- restore old and new signing keys during overlap
- accept compatible token versions
- revert audience or issuer change

Mitigation should target the failing cohort. A global restart or rollback may create unnecessary impact.

---

## 13. Prove recovery for the subset

Verify:

- affected geography, tenant, version, or shard succeeds
- aggregate success rate improves without hiding a remaining minority
- error rate by cohort returns to baseline
- no new traffic concentration overloads the healthy cohort
- latency and retries normalize
- rollout and routing state are stable
- synthetic tests cover the original failure dimension

---

## Adversarial follow-ups

### “The deployment is green. Why suspect the application?”

Kubernetes reports controller conditions such as available replicas. It does not execute every business transaction, tenant path, feature flag, or schema variant.

### “How do you know it is infrastructure and not the app?”

I do not begin with that binary. I find the earliest dimension that separates failing from healthy requests and trace both through the same layers. The failure boundary becomes evidence-based.

### “All failures are in one AZ. Is AWS infrastructure at fault?”

Not necessarily. All new-version pods may be in that AZ, or the AZ may use a different dependency path. I separate version, node, subnet, and dependency variables before concluding.

### “Would you roll back immediately?”

If the deployment timestamp and version correlation are strong and impact is material, rollback is a valid mitigation. I still preserve evidence and verify schema and configuration compatibility so rollback does not worsen state.

### “Why are aggregate dashboards dangerous?”

A 2% tenant or geography failure can disappear in a 98% success aggregate while still being a severe contractual or business outage. Alerts and dashboards need cohort-aware dimensions for critical boundaries.

---

## Weak answers to avoid

- “Check logs and compare pods.”
- treating “some users” as random noise
- analyzing counts without cohort rates
- assuming one-AZ correlation proves an AWS failure
- trusting rollout success as business success
- ignoring IPv6, resolver, WAF, feature flag, and data-shard dimensions
- rolling back code while leaving incompatible configuration or schema
- using raw user IDs as Prometheus labels
- declaring recovery from aggregate success only

---

## Closing statement

> Partial outages are classification problems. I build a cohort matrix, compare matched failing and healthy transactions, and follow the first separating dimension through edge, network, Kubernetes, code, and data. The mitigation and recovery proof are then scoped to the users who were actually failing.