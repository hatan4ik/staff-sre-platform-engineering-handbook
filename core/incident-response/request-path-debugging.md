# Request-Path Debugging from Client to Dependency

## Interview scenario

Users report that a production endpoint is unavailable, slow, or intermittently failing. The service crosses DNS, edge, TLS, load balancing, networking, Kubernetes, application, and downstream dependencies.

The Staff/Principal task is not to name every tool. It is to find the first layer where a failing request diverges from a healthy request, restore service with the smallest reversible change, preserve evidence, and prove recovery from the user perspective.

---

## 1. Ninety-second Staff/Principal answer

> I begin with customer impact, incident command, and one UTC timeline. I capture one failing transaction and one functionally equivalent healthy transaction, including client network, resolved addresses, TLS result, route, status, latency, request and trace IDs, serving region, zone, target, pod version, and dependency path.
>
> I then walk the request path from the outside inward: authoritative DNS and recursive answers, edge and WAF behavior, TLS and SNI, listener and routing rules, target health, network policy and routes, ingress and Service selection, EndpointSlices, pod readiness, application saturation, and downstream dependencies. At each layer I ask whether the request arrived, whether it was accepted, where time was spent, and which component generated the error.
>
> I avoid changing several layers at once. I bound the blast radius by resolver, IP family, geography, region, zone, version, target, tenant, and operation. The mitigation is the smallest tested action at the failed layer: stop a rollout, remove a bad target or cohort, restore a listener or route, shift traffic to a healthy cell, disable an expensive feature, or serve a safe degraded response.
>
> Recovery is confirmed with external synthetics and customer SLIs, not healthy pods alone. After stabilization, I preserve the causal chain, identify why detection or containment failed, assign corrective actions with owners and deadlines, and exercise the repaired design.

### Fifteen-second version

> Compare one failing request with one healthy request, find the first divergent layer, change one reversible thing, and prove recovery externally.

---

## 2. Request-path model

A generic path may look like:

```text
client application
      |
      v
local resolver and network
      |
      v
recursive DNS resolver
      |
      v
authoritative DNS
      |
      v
CDN / edge / global traffic manager
      |
      v
WAF / DDoS / authentication edge
      |
      v
TLS termination and listener routing
      |
      v
load balancer / gateway / reverse proxy
      |
      v
network route, firewall, NAT, overlay
      |
      v
Kubernetes ingress or Gateway
      |
      v
Service and EndpointSlice
      |
      v
pod / process / runtime
      |
      v
database / cache / queue / third party
```

Not every system contains every layer. Draw the real path before debugging it.

At every boundary ask four questions:

1. Did the request reach this layer?
2. Did the layer accept or reject it?
3. How long did the layer hold it?
4. What identity, route, version, and target did it select?

---

## 3. Establish incident command and impact

Record immediately:

- Incident start and detection source.
- Affected user journey and business operation.
- Error rate, latency, and availability objective.
- Geographic, tenant, device, or version scope.
- Whether failure is total, partial, intermittent, or slow.
- Whether new and existing sessions differ.
- Recent deployments, configuration, network, certificate, DNS, and dependency changes.

Assign roles appropriate to severity:

- Incident commander.
- Operations or technical lead.
- Communications lead.
- Scribe or timeline owner.
- Subject-matter responders.

The incident commander manages priorities and risk. They do not need to type every command.

---

## 4. Build one UTC timeline

```text
T0 last known healthy
T1 first measurable user impact
T2 first alert
T3 first customer report
T4 relevant change or dependency event
T5 incident declared
T6 mitigation begins
T7 recovery begins
T8 user SLI recovered
T9 incident downgraded
```

Normalize timestamps and account for:

- Metric windows.
- Log ingestion delay.
- Trace sampling.
- Resolver and CDN cache lifetime.
- Clock skew.
- Deployment and configuration propagation.
- Load-balancer registration and drain delay.

A change after impact began cannot be the initiating cause, although it may worsen or prolong the incident.

---

## 5. Capture paired transactions

Choose one failing and one successful transaction that should be equivalent.

Capture, using safe identifiers:

```text
UTC timestamp
client geography and network
resolver and DNS answer
IPv4 or IPv6
hostname and SNI
certificate chain result
edge or gateway identifier
HTTP method, route, status, and latency
request ID and trace ID
selected region, zone, target, node, and pod
application image digest and configuration version
tenant, feature, or shard cohort
dependency endpoint and result
```

Paired evidence is more useful than a broad dashboard because it exposes the first difference.

Do not put passwords, tokens, personal data, or raw sensitive payloads into incident artifacts.

---

## 6. Layer-by-layer investigation

## 6.1 Client and local network

Check:

- Exact client error.
- Client clock.
- Proxy, VPN, captive portal, or enterprise firewall.
- IPv4 versus IPv6 behavior.
- Client DNS cache.
- Old mobile or SDK version.
- Certificate trust store.
- Request size and timeout.

Useful tests:

```bash
curl -v --connect-timeout 5 --max-time 20 https://api.example.com/path
curl -4 -v https://api.example.com/path
curl -6 -v https://api.example.com/path
```

A server-side incident should reproduce from an independent external path. A client-only problem may not.

## 6.2 DNS and delegation

Check:

- Registrar delegation.
- Authoritative name servers.
- Record type and value.
- Split-horizon or private/public zone differences.
- Resolver-specific answers.
- A versus AAAA.
- DNSSEC validity where enabled.
- Health-check and failover-routing state.
- TTL and negative caching.

Useful commands:

```bash
dig api.example.com A +trace
dig api.example.com AAAA
dig @1.1.1.1 api.example.com A
dig @8.8.8.8 api.example.com A
dig api.example.com DNSKEY +dnssec
```

The management console showing a correct record does not prove that clients receive it.

A DNS correction does not instantly flush recursive caches. Lower TTL before planned changes, not after the outage has begun.

## 6.3 Edge, CDN, and WAF

Check:

- Edge result type.
- Cache status and stale behavior.
- Origin selected by path or host.
- Regional edge or point-of-presence correlation.
- WAF terminating rule and labels.
- Rate limits.
- Geo or bot policy.
- Header and body-size restrictions.
- Origin timeout.

Compare direct-origin access with edge access only when safe and authorized. Bypassing the edge can change authentication, routing, and security assumptions.

## 6.4 TLS and SNI

Check:

- DNS name in certificate SAN.
- Expiration and not-before.
- Complete chain.
- SNI route.
- Supported protocol and cipher.
- Client trust store.
- mTLS client certificate where applicable.
- Certificate rotation overlap.
- Time synchronization.

```bash
openssl s_client \
  -connect api.example.com:443 \
  -servername api.example.com \
  -showcerts
```

Different clients may fail selectively because of protocol, cipher, trust-store, or certificate-chain differences.

## 6.5 Listener, route, and gateway

Check:

- Listener exists on expected port.
- Host and path rule ordering.
- Default route.
- Redirect loops.
- Protocol translation.
- Authentication filter.
- Request and response timeout.
- Retry policy.
- Header mutation.
- Maximum request size.
- Gateway configuration revision.

Determine which component generated the status code. A `502`, `503`, or `504` from an edge, gateway, mesh proxy, and application means different things.

## 6.6 Load balancer and target health

Check:

- Healthy and unhealthy targets by zone.
- Health-check protocol, port, and path.
- Target registration and deregistration.
- Slow-start or warmup.
- Connection errors and resets.
- Target response time.
- Target type.
- Zonal distribution.
- Sticky sessions.
- Long-lived connection behavior.

A healthy target means its configured health check passed. It does not prove the complete business operation or dependency chain.

## 6.7 Network path

Check both forward and return path:

- Route tables.
- Security groups or firewalls.
- Network ACLs.
- NAT and source-address translation.
- Network policy.
- Overlay tunnel and underlay.
- MTU and PMTUD.
- Conntrack capacity.
- Subnet and pod IP exhaustion.
- Asymmetric routing.
- Service-mesh interception.

Evidence sources:

- Flow logs.
- Packet captures at bounded points.
- Modeled reachability tools.
- Host routes and policy rules.
- CNI or dataplane telemetry.
- Socket and retransmission counters.

A modeled route proves configuration, not live application response. A flow log proves observed flow metadata, not payload correctness.

## 6.8 Kubernetes ingress, Gateway, Service, and EndpointSlice

```bash
kubectl get ingress,gateway,httproute -A
kubectl get svc -n <namespace> <service> -o yaml
kubectl get endpointslice -n <namespace> \
  -l kubernetes.io/service-name=<service> -o yaml
kubectl get pods -n <namespace> -o wide
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

Check:

- Controller and class.
- Reconciliation errors.
- Service selector.
- Port and targetPort.
- Endpoint readiness.
- Zone and version mix.
- Readiness gates.
- NetworkPolicy.
- Sidecar or mesh revision.
- Configuration and Secret revision.
- Endpoint propagation delay.

A deployment may be available while a route, selector, port, or EndpointSlice is wrong.

## 6.9 Pod, process, and runtime

Check:

- Container status and previous termination.
- Current and previous logs.
- CPU throttling and scheduler delay.
- Memory pressure and OOM.
- File descriptors and sockets.
- Thread, event-loop, or worker-pool saturation.
- Connection acquisition.
- Garbage collection.
- Queue depth and lock contention.
- Configuration and credentials.
- Process-level health versus pod-level health.

Do not restart all pods before collecting evidence unless immediate safety requires it.

## 6.10 Application and dependency

Use RED plus saturation:

- Rate.
- Errors.
- Duration.
- Queueing.
- Concurrency.
- Retry count.
- Dependency latency.
- Pool utilization.
- Cache hit rate.
- Database locks and connections.
- Queue lag and oldest-message age.

Compare a failing trace with a healthy trace.

Common patterns:

```text
root span fails immediately
  -> validation, authentication, configuration, or code

one child span dominates
  -> downstream dependency or connection acquisition

repeated child spans
  -> retry amplification

large unexplained gap
  -> queueing, lock, GC, scheduler delay, or missing instrumentation

trace ends abruptly
  -> timeout, cancellation, process exit, or telemetry loss
```

---

## 7. Status-code ownership

Do not interpret an HTTP status without identifying its issuer.

| Symptom | Questions |
|---|---|
| `NXDOMAIN` | Which resolver? Which authoritative zone? Is negative cache involved? |
| TLS failure | Name, chain, SNI, protocol, trust store, clock? |
| `401` | Which authentication layer? Token issuer, audience, expiry, key ID? |
| `403` | WAF, gateway, application, resource authorization, network policy? |
| `429` | Which quota or limiter? Client, edge, service, dependency? |
| `502` | Which proxy could not obtain a valid upstream response? |
| `503` | No healthy target, overload rejection, maintenance, dependency? |
| `504` | Which proxy's upstream deadline expired? |
| Connection timeout | DNS, route, firewall, no listener, queue saturation? |
| Reset | Client, proxy, target, kernel, process restart, idle timeout? |

The component emitting the response should be visible in headers, logs, access records, or trace boundaries.

---

## 8. Bound the blast radius

Build a matrix before broad mitigation:

| Dimension | Comparisons |
|---|---|
| Geography | country, region, metro, ISP |
| DNS | resolver, answer, TTL age |
| Network | IPv4/IPv6, proxy, VPN, source path |
| Edge | point of presence, WAF rule, cache behavior |
| Platform | region, zone, cell, cluster, subnet |
| Compute | node pool, image, capacity type, target |
| Release | image digest, config, sidecar, feature flag |
| User | tenant, tier, account age, auth provider |
| Data | shard, partition, replica, cache segment |
| Operation | read/write, route, payload size, session age |

Use rates and denominators. Most failures occurring in a high-traffic cohort does not prove that cohort has a higher failure rate.

Control for confounding. If all new pods are in one zone, version and zone are not independently established.

---

## 9. Hypothesis discipline

For each hypothesis write:

```text
Hypothesis:
  IPv6 clients fail because the AAAA record points to an endpoint without the listener.

Predicted evidence:
  A requests succeed, AAAA requests time out, and the failing endpoint lacks port 443.

Disconfirming evidence:
  IPv6 succeeds through the same endpoint from an independent path.

Safe test:
  Query multiple resolvers and connect directly with SNI to each returned address.
```

Do not collect data without saying what decision it will change.

A plausible explanation is not a root cause until the evidence and timeline support it.

---

## 10. Mitigation hierarchy

Prefer the smallest reversible change that protects users.

1. Stop harmful automation or rollout.
2. Remove or drain only the bad target, version, zone, or cohort.
3. Disable a failing feature or expensive optional path.
4. Shift traffic to a tested healthy cell or region.
5. Restore the last known-good route, listener, policy, configuration, or deployment.
6. Shed load and preserve critical operations.
7. Serve a safe degraded or maintenance response.
8. Use broad rollback or failover only when narrower controls are insufficient.

Mitigation selection considers:

- Propagation time.
- Reversibility.
- Data correctness.
- Security exposure.
- Capacity in the destination.
- State and dependency readiness.
- Evidence destruction.

Changing DNS may be slower than changing a lower routing layer because caches already hold the old answer.

---

## 11. Recovery proof

Do not declare recovery based on internal health alone.

Require:

- External synthetic success from multiple paths.
- Affected cohort success rate restored.
- p95 and p99 latency normalized.
- Error-budget burn stopped.
- No hidden zone, version, resolver, or tenant remains degraded.
- Queue and retry backlog drains safely.
- Dependency saturation returns to a stable range.
- Change propagation is complete.
- Support and client retry volume decline.

Observe long enough to cover:

- Cache lifetime.
- Connection lifetime.
- Token refresh.
- Load-balancer drain.
- Deployment convergence.
- Scheduled traffic variation.

---

## 12. Evidence preservation

Capture before broad restarts or rollback where feasible:

- DNS answers and TTLs.
- Certificate and listener state.
- Gateway and load-balancer configuration.
- Target health and access logs.
- Flow logs and bounded packet evidence.
- Kubernetes manifests, EndpointSlices, events, and rollout history.
- Pod UID, image digest, node, zone, and previous logs.
- Traces and high-cardinality log samples.
- Dependency state and queue age.
- Change audit events.
- Exact commands and mitigation timestamps.

Store incident evidence securely with retention appropriate to sensitivity.

---

## 13. Observability requirements

A debuggable request path needs correlation fields that survive boundaries:

- Request ID.
- Trace ID and span ID.
- User-safe cohort identifier.
- Region, zone, cell, cluster, node, and pod.
- Application and configuration version.
- Route and operation.
- Dependency name.
- Status-code issuer.
- Retry attempt and remaining deadline.

Key signals:

- DNS answer correctness from outside the platform.
- TLS handshake success and latency.
- Edge, gateway, and load-balancer errors by rule and target.
- Target health by zone and version.
- EndpointSlice readiness and age.
- Request rate, error, duration, and saturation.
- Dependency latency and pool utilization.
- Change events.
- Synthetic business transactions.

Dashboards should accelerate detection and navigation. They cannot pre-aggregate every diagnostic dimension.

---

## 14. Common weak answers

### “Restart the pods”

This destroys evidence and helps only a subset of failure modes.

### “DNS is healthy because the console record is correct”

Clients may see a different resolver answer, delegation, negative cache, split horizon, or IP family.

### “All pods are Ready”

Readiness does not prove the gateway reaches the pod, the business path works, or dependencies are healthy.

### “The load balancer is healthy”

A configured health path may be shallow and may not represent every zone, version, or operation.

### “Roll back everything”

A broad rollback may increase impact, destroy evidence, or revert unrelated safe changes.

### “The cloud provider is down”

Check account-specific, zonal, configuration, and application evidence before declaring provider-wide failure.

### “The trace shows the root cause”

Sampling and missing instrumentation can hide rare failures and queueing. Correlate with logs, metrics, changes, and raw path evidence.

---

## 15. Adversarial interview questions

### Where do you start if everything is red?

Start with one real user transaction, identify the first externally observable failure, establish the last known-good boundary, and compare a healthy cohort. Do not open every console simultaneously.

### What if internal checks pass but users fail?

Test from outside the account and network. Inspect DNS, IPv6, edge, WAF, TLS, cache, client version, and resolver cohorts.

### What if the fix is obvious?

Apply an immediate fix only when the risk is understood, but capture enough pre-change evidence to verify causality and prevent recurrence. Obvious correlations are sometimes confounded.

### When do you packet-capture?

After less invasive evidence narrows the problem to a network boundary and the capture is authorized, bounded, and protected. Packet capture is not the first response to every timeout.

### How do you distinguish an application `504` from a proxy `504`?

Identify the response issuer through headers, access logs, trace boundaries, timeout configuration, and request timing. Then inspect the upstream deadline at that proxy.

### Why not immediately fail over regions?

Failover can move traffic into an unready or under-capacity destination and can create state conflicts. Validate data, dependency, capacity, and write authority before shifting.

---

## 16. Staff/Principal checklist

A strong answer includes:

- User impact and incident command.
- One UTC timeline.
- Paired failing and healthy transactions.
- Explicit request-path diagram.
- Status-code ownership.
- Cohort and failure-domain matrix.
- Falsifiable hypotheses.
- One reversible mitigation at a time.
- Evidence preservation.
- External and cohort-specific recovery proof.
- Corrective actions and game-day validation.

---

## Primary references

- [Kubernetes Services, Load Balancing, and Networking](https://kubernetes.io/docs/concepts/services-networking/)
- [Kubernetes EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/)
- [Google SRE Workbook — Incident Response](https://sre.google/workbook/incident-response/)
