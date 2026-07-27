# Cohort Analysis for Partial and Selective Failures

## Interview scenario

A deployment, configuration change, dependency incident, or infrastructure event affects only some users. Aggregate availability remains near normal, most dashboards look healthy, and the release controller reports success.

The Staff/Principal task is to turn “some users are failing” into a measurable population, find the first dimension that separates failing and healthy transactions, avoid confounded conclusions, mitigate only the affected cohort, and verify that the hidden failure is gone.

---

## 1. Ninety-second Staff/Principal answer

> I define the failing subset before choosing a technology hypothesis. I capture one failing and one successful transaction with the same intended operation and compare geography, resolver, IP family, client version, authentication path, tenant, feature flag, region, zone, cell, target, pod image, configuration revision, data shard, dependency, session age, and request shape.
>
> I build a cohort matrix using rates and denominators, not raw counts. Then I find the first dimension with a materially different failure rate and control for confounding. If all new-version pods are in one zone, version and zone are correlated; I need old and new versions across multiple zones or another controlled comparison before claiming cause.
>
> I use logs, traces, gateway and load-balancer access records, deployment metadata, feature evaluation, and data-partition mapping to join the user transaction to the actual serving path. “Deployment succeeded” only proves the controller met its rollout condition; it does not prove every route, tenant, data shape, client, or long-lived session works.
>
> I mitigate at the narrowest safe boundary: stop rollout, remove a bad version or target, disable a feature flag, route away from one cell, restore compatible configuration, or isolate a shard. Recovery is measured specifically for the affected cohort and for aggregate guardrail SLIs.

### Fifteen-second version

> Define the subset, compare equivalent failing and healthy requests, control for confounding, and remove only the first proven bad cohort.

---

## 2. Why aggregate dashboards hide selective outages

Suppose:

```text
99% of traffic succeeds at 99.99%
1% of traffic fails at 80%
```

The aggregate success rate is:

```text
0.99 × 99.99% + 0.01 × 80% ≈ 99.79%
```

The overall graph may appear only slightly degraded while a specific tenant, country, device version, or shard experiences a severe outage.

Raw failure count can also mislead. A high-traffic cohort may generate the most failures even when its failure rate is lower.

Always retain:

```text
failures
requests
affected unique users or operations
failure rate
latency distribution
```

---

## 3. Define the population precisely

User and client dimensions:

- Country, region, metro, ISP, or enterprise network.
- Recursive resolver.
- IPv4 versus IPv6.
- Device type, operating system, browser, SDK, or app version.
- Authenticated versus anonymous.
- Identity provider.
- New versus existing session.
- Customer tier.
- Tenant, organization, or account age.
- Language, locale, or regulatory region.
- Feature-flag assignment.
- Payload size, operation, or content type.

Platform dimensions:

- Edge location.
- DNS answer.
- WAF or gateway rule.
- Region, zone, cell, cluster, or namespace.
- Load-balancer target.
- Node, node pool, image, architecture, or capacity type.
- Pod, image digest, sidecar revision, or configuration checksum.
- Database shard or replica.
- Cache shard.
- Queue or stream partition.
- Dependency provider or endpoint.

Time dimensions:

- Before versus after release.
- Connection established before versus after change.
- Token issued before versus after key rotation.
- Cache entry age.
- Pod age.
- First request versus reused connection.
- Warm versus cold path.

The incident question becomes:

> Which combinations of these dimensions have a statistically and operationally meaningful change in failure rate or latency?

---

## 4. Capture paired evidence

Choose a failing and healthy transaction that should be equivalent.

Record:

```text
UTC timestamp
safe user or tenant identifier
operation and route
request shape and payload class
client and SDK version
geography, ISP, resolver, and IP family
session and token age
DNS answer and edge path
request ID and trace ID
region, zone, cell, cluster, node, and pod
image digest, configuration, feature flags, and sidecar revision
data shard, cache shard, queue partition, and dependency
status-code issuer and latency breakdown
```

Paired transactions reduce noise and make the first divergent boundary visible.

Do not record unbounded personal data or secrets merely to improve debugging.

---

## 5. Build a cohort matrix

Example:

| Dimension | Failing requests | Total requests | Failure rate | Healthy baseline | Interpretation |
|---|---:|---:|---:|---:|---|
| version `v2.14` | 9,600 | 10,000 | 96% | 0.4% | Strong release correlation |
| zone `c` | 8,300 | 12,000 | 69% | 0.6% | Strong zonal correlation |
| IPv6 | 5,000 | 5,000 | 100% | 0.2% IPv4 | IP-family path |
| feature enabled | 9,100 | 10,000 | 91% | 0.4% disabled | Feature or data path |
| shard 7 | 8,800 | 10,000 | 88% | 0.5% other shards | Partition-specific |

The table is illustrative. Production analysis should include confidence, sample size, and the expected baseline.

Useful queries:

```sql
SELECT
  app_version,
  availability_zone,
  COUNT(*) AS requests,
  SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END) AS failures,
  AVG(CASE WHEN status >= 500 THEN 1.0 ELSE 0.0 END) AS failure_rate
FROM request_events
WHERE timestamp BETWEEN :start AND :end
GROUP BY app_version, availability_zone;
```

For latency, compare distributions rather than averages.

---

## 6. Control for confounding

Correlation is not sufficient when dimensions move together.

Example:

```text
All v2 pods happen to be in zone-c.
All v1 pods happen to be in zones-a and b.
```

Observed failure could be caused by:

- v2 code.
- Zone-c network or dependency.
- Node image used only in zone-c.
- Configuration injected only into v2.
- Traffic type routed only to zone-c.

Disambiguating comparisons:

- v2 in another zone.
- v1 in zone-c.
- Same tenant and operation across versions.
- Same version across node pools.
- Same data shard through another application cell.
- Feature on and off within one version.

Use natural experiments and controlled routing carefully. Do not expose more users merely to improve statistical certainty when the current evidence supports safe mitigation.

---

## 7. Find the first separating dimension

A useful ordering:

1. Client-visible path.
2. Geography and resolver.
3. IP family and TLS.
4. Edge, WAF, gateway, listener, or route.
5. Region, zone, and cell.
6. Target, node, pod, and version.
7. Configuration and feature evaluation.
8. Authentication and authorization.
9. Data shard and dependency.
10. Request shape and business state.

The first separating dimension is often closer to the failure boundary than the final stack trace.

Example:

```text
Only IPv6 clients fail.
  -> inspect AAAA answer, dual-stack listener, firewall, routes, and application bind.

Only one pod image fails.
  -> inspect release, configuration, schema, and sidecar revision.

Only one tenant shard fails across all versions.
  -> inspect data partition, replica, cache, and tenant-specific policy.
```

---

## 8. Release and rollout cohorts

Inspect:

```bash
kubectl rollout status deployment/<name> -n <namespace>
kubectl rollout history deployment/<name> -n <namespace>
kubectl get rs,pods -n <namespace> -l app=<app> -o wide
kubectl get endpointslice -n <namespace> \
  -l kubernetes.io/service-name=<service> -o yaml
```

Compare:

- Image digest, not only image tag.
- ReplicaSet and revision.
- Configuration checksum.
- Secret or certificate version.
- Sidecar and service-mesh control-plane revision.
- Node image and runtime.
- Zone distribution.
- Pod age and readiness transition.
- Per-pod request and error rate.

A deployment can satisfy availability conditions while:

- One route is broken.
- A rare data shape fails.
- Readiness is shallow.
- Sticky sessions trap users on one bad pod.
- Only existing connections use old behavior.
- A canary metric excludes the affected cohort.

---

## 9. Network and edge cohorts

### Resolver and DNS answer

Compare answers from:

- Public resolvers.
- ISP resolvers.
- Enterprise resolvers.
- Internal resolvers.
- Different geographic locations.

Potential causes:

- Stale or split DNS.
- Negative cache.
- One weighted or latency-routed endpoint.
- Broken AAAA path.
- DNSSEC validation difference.

### IPv4 versus IPv6

A successful IPv4 synthetic does not prove IPv6 health.

Compare:

- A and AAAA answers.
- Listener support.
- Firewall and ACL rules.
- Routes.
- Application bind address.
- Proxy and SDK support.

### Edge location or rule

Compare:

- Edge point of presence.
- Cache behavior.
- Origin selected.
- WAF rule and label.
- TLS protocol.
- Geo restriction.
- Header and body-size path.

### Payload size

Selective failures for large requests or responses can indicate:

- MTU or PMTUD.
- Gateway body limits.
- Header limits.
- Upload policy.
- Proxy buffering.
- Application memory pressure.

---

## 10. Kubernetes cohorts

### Service and EndpointSlice

Inspect selectors, ready conditions, ports, zones, and versions.

A selector can include the wrong pod population or omit the new version.

### Readiness and pod age

Compare failures by time since startup.

A pod may become ready before:

- Cache warmup.
- Configuration load.
- Identity acquisition.
- Schema compatibility check.
- Model or dataset load.
- All route handlers are usable.

### Node and topology

Compare:

- Zone.
- Node pool.
- Architecture.
- Kernel and image.
- CNI state.
- Capacity type.
- Taints and affinity.

A rollout may place all new pods onto one new node image or capacity pool.

### Network policy and identity

A new version label or ServiceAccount can change:

- NetworkPolicy selection.
- Mesh authorization.
- Cloud workload identity.
- Secret authorization.
- Egress path.

### Configuration

Test the compatibility matrix:

```text
old code + old config
old code + new config
new code + old config
new code + new config
```

A deployment and configuration system must preserve supported combinations during rollout.

---

## 11. Application cohorts

### Feature flags

A feature flag is a distributed configuration system.

Capture:

- Flag name and evaluated value.
- Rule version.
- Targeting attributes.
- Cache age.
- Default behavior when the flag service is unavailable.
- Percentage bucket.

A successful deployment can still create a selective outage through a flag change.

### Authentication and authorization

Compare:

- Token issuer.
- Audience.
- Key ID.
- Token issue and expiry time.
- Identity provider.
- Claim shape.
- Role or entitlement.
- Authorization policy version.

A key rotation can affect tokens issued in only one time window. A policy condition can affect only one tenant tag.

### Session age

Only old sessions may fail because of:

- Sticky endpoint.
- Long-lived connection drain.
- Old token or key.
- Incompatible session schema.
- Cached DNS or configuration.

Only new sessions may fail because of:

- Authentication dependency.
- TLS handshake.
- New schema.
- Cold pool.
- New endpoint selection.

### Data shape

A new version may fail only for:

- Null or old enum value.
- Large object.
- Tenant customization.
- Partially migrated record.
- Unicode or locale edge case.
- Historical state transition.

Representative test data must include rare but valid production shapes.

---

## 12. Data and dependency cohorts

Map each failing transaction to:

- Database shard and replica.
- Cache shard.
- Queue or stream partition.
- Search index shard.
- Object-storage region or bucket.
- Third-party provider.
- Encryption key or policy boundary.

Compare:

- Latency.
- Error and throttle rate.
- Connection pool.
- Replication lag.
- Failover state.
- Hot key or partition.
- Credential or quota.

Selective read/write behavior matters:

```text
writes fail, reads succeed
  -> writer, lock, quota, consistency, or authorization

reads fail, writes succeed
  -> replica, cache, index, or read path
```

---

## 13. Joining evidence

The analysis needs a common join key.

Preferred fields:

- Trace ID.
- Request ID propagated through proxies.
- Safe tenant or cohort ID.
- Image digest.
- Configuration version.
- Region, zone, cell, node, pod.
- Shard and dependency.

Logs without consistent fields force responders to infer relationships from timestamps and text.

Example trace comparison:

```text
healthy:
  edge -> gateway -> api v1 -> cache -> database shard 2

failing:
  edge -> gateway -> api v2 -> cache -> database shard 7 timeout
```

Now test whether the separator is version, shard, or their interaction.

---

## 14. Statistical and operational cautions

### Small sample size

A 100% failure rate across two requests is not equivalent to 100% across 100,000.

### Multiple comparisons

Searching hundreds of dimensions will find accidental correlations. Require mechanism and timeline support.

### Simpson's paradox

Aggregate direction can reverse when cohorts are combined. Analyze within meaningful strata.

### Cardinality cost

Do not emit unbounded customer IDs as metric labels. Use logs, traces, exemplars, or bounded cohorts for high-cardinality analysis.

### Privacy

Pseudonymize identifiers, restrict access, and retain only what incident response requires.

### Survivorship bias

If failed clients never reach the application, application logs cannot represent them. Include edge and synthetic evidence.

---

## 15. Mitigation choices

Narrow mitigations:

- Stop rollout.
- Set canary weight to zero.
- Remove a bad target or node pool.
- Disable one feature flag.
- Route away from one zone or cell.
- Restore one configuration revision.
- Remove a bad DNS or edge route.
- Isolate a shard and use a tested replica or degraded path.
- Block a malformed client version only when safe and communicated.

Broad mitigations:

- Full rollback.
- Regional failover.
- Global feature disable.
- Traffic shedding.

Choose the narrowest action that restores the affected cohort without violating correctness or safety.

Avoid “fixing” the graph by removing cohort labels or excluding affected traffic.

---

## 16. Recovery proof

Verify both:

### Affected cohort

- Failure rate returns to baseline.
- Tail latency normalizes.
- Existing and new sessions work.
- Backlog or retries drain.
- Multiple representative tenants and data shapes succeed.

### Global guardrails

- Aggregate error rate does not worsen.
- Other regions, zones, versions, and shards remain healthy.
- Capacity and dependencies are stable.
- No write conflict or data inconsistency appears.
- Security controls remain enforced.

Continue observation long enough to cover session, cache, token, deployment, and DNS lifetimes.

---

## 17. Prevention

- Canary analysis by critical cohort and route.
- Image digest and configuration version in telemetry.
- Zone, cell, target, pod, feature, and shard dimensions in logs and traces.
- Synthetic checks across geography, resolver, IP family, auth flow, and business path.
- Compatibility testing for code, schema, configuration, and clients.
- Progressive delivery with explicit abort conditions.
- Topology spread for versions.
- Feature-flag ownership and rollback.
- Representative historical data tests.
- Controlled shard and dependency game days.
- Bounded high-cardinality investigation tooling.

An alert that only detects the aggregate may be insufficient even when its threshold is technically correct.

---

## 18. Common weak answers

### “Roll back because it started after deployment”

The deployment may be correlated with a zone, node image, configuration, feature, or data migration. Rollback may still be the safest mitigation, but the causal claim needs evidence.

### “Only one percent is affected, so severity is low”

The cohort may contain a critical tenant, country, safety operation, or all users of one valid client type.

### “The rollout succeeded”

Controller success does not prove every business path and cohort.

### “Look at logs”

State which fields, comparison, and falsifiable hypothesis the query tests.

### “Errors are highest in zone-c, so zone-c is broken”

Use failure rates and control for version, traffic, and shard placement.

### “Add user ID as a metric label”

This creates unbounded cardinality and privacy risk. Use safer high-cardinality evidence systems.

---

## 19. Adversarial interview questions

### How do you start when you do not know the cohort?

Start with paired failing and healthy requests, enumerate dimensions present in edge, gateway, application, and data telemetry, and find the first divergent field.

### What if the bad version and bad zone are perfectly correlated?

Mitigate safely, then create a controlled comparison in a disposable or very small canary environment. Do not claim the independent cause until the dimensions can be separated.

### How do you detect clients that never reach the application?

Use external synthetics, DNS and edge logs, WAF logs, gateway access records, client telemetry, and support reports.

### Would you route traffic to reproduce the failure?

Only through a bounded experiment with explicit exposure, rollback, and safety limits. Never increase customer impact solely to improve diagnosis.

### How do you handle high-cardinality cohort analysis?

Keep low-cardinality operational dimensions in metrics; use structured logs, traces, exemplars, columnar analytics, and time-bounded queries for detailed cohorts.

### When is full rollback correct?

When release correlation is strong, rollback is compatible and safer than continued exposure, and no narrower control restores service fast enough. Preserve evidence before or during rollback.

---

## 20. Staff/Principal checklist

A strong answer includes:

- Precise cohort definition.
- Paired failing and healthy transactions.
- Rates and denominators.
- Confounding analysis.
- Release, network, Kubernetes, application, and data dimensions.
- Common correlation fields.
- Narrow reversible mitigation.
- Cohort-specific recovery proof.
- Global guardrails.
- Privacy and cardinality controls.
- Prevention through progressive delivery and representative testing.

---

## Related canonical material

- [`request-path-debugging.md`](request-path-debugging.md)
- [`../delivery-gitops/gitops-progressive-delivery.md`](../delivery-gitops/gitops-progressive-delivery.md)
- [`../distributed-systems/README.md`](../distributed-systems/README.md)
