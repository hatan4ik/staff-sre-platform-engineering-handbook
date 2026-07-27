# Fine-Grained Service Discovery with Envoy, Istio, and xDS

This is the canonical, company-neutral chapter for designing service discovery across hundreds or thousands of services. The central problem is not merely name resolution. It is distributing the smallest correct configuration to each data-plane proxy while keeping convergence fast, failure domains bounded, and already-programmed traffic resilient to control-plane disruption.

## 1. Principal-level framing

A weak design says:

> Put every service in one mesh and let Istio discover everything.

A strong design says:

> Treat service discovery as a configuration-graph, authorization, and failure-domain problem. Keep the registry authoritative, scope producer visibility and consumer imports, distribute only relevant xDS resources, isolate churn, preserve last-known-good data-plane behavior, and prove convergence under realistic endpoint and policy change rates.

The desired architecture is:

```text
service and endpoint truth
        |
        v
registry and platform APIs
        |
        v
mesh control plane
  select -> compute -> validate -> distribute
        |
        v
small workload-specific configuration views
        |
        v
proxies continue serving accepted state
```

## 2. Clarify the problem before designing

State two or three assumptions and proceed:

- More than 1,000 logical services and tens of thousands of endpoints.
- A workload normally depends on only a small subset of the total service graph.
- Multiple clusters, zones, environments, and trust boundaries exist.
- Endpoint and rollout churn is continuous.
- Workload identity and mTLS are required.
- L7 policy is required for selected traffic, not necessarily every path.
- A temporary discovery-control-plane outage must not stop already-programmed traffic.

Useful questions:

1. How many services, endpoints, proxies, clusters, and regions?
2. What is the steady-state and peak endpoint-change rate?
3. Are dependencies declared, observed, or both?
4. Which traffic requires L7 routing or policy?
5. What convergence time is acceptable?
6. Which organizational or regulatory boundaries must remain isolated?
7. Are VMs and external services part of the registry?
8. Is cross-region traffic normal, fallback-only, or forbidden?

## 3. Native Kubernetes discovery

Kubernetes provides stable logical service identities over changing backends.

```text
Service
  -> stable name and virtual destination
EndpointSlice
  -> current backend addresses, ports, readiness, and topology
CoreDNS
  -> name resolution
node datapath
  -> backend selection and forwarding
```

Example logical identity:

```text
ledger.payments.svc.cluster.local
```

Current endpoints might be:

```text
10.42.4.17:8080  zone-a  ready
10.42.8.23:8080  zone-b  ready
10.42.9.11:8080  zone-c  ready
```

EndpointSlices avoid one unbounded endpoint object, but endpoint changes still form a control-plane event stream. At scale, the key question becomes:

> Which consumers actually need this change?

DNS alone does not provide the complete route, identity, certificate, retry, timeout, locality, subset, outlier-detection, or authorization model used by a service mesh.

## 4. Registry, control plane, and data plane

Keep these roles distinct.

### Registry

The registry stores service and endpoint truth.

Examples:

- Kubernetes Services and EndpointSlices.
- ServiceEntry and WorkloadEntry resources.
- VM registrations.
- External-service catalogs.
- Multi-cluster registries.

### Control plane

The control plane:

- Watches registry and policy sources.
- Builds an internal service and policy model.
- Selects which configuration applies to each proxy.
- Generates xDS resources.
- Distributes identity and trust information.
- Tracks accepted and rejected versions.

### Data plane

The data plane:

- Accepts connections.
- Selects upstreams.
- Enforces routing and policy.
- Performs TLS or mTLS.
- Applies load balancing and resilience controls.
- Emits telemetry.
- Continues using accepted configuration during a temporary control-plane outage.

The core separation is:

> The control plane decides configuration; the data plane serves traffic.

## 5. xDS from first principles

Envoy receives dynamic configuration through the xDS family.

### LDS — listeners

Defines where a proxy accepts traffic and which filter chains process it.

Questions:

- Which addresses and ports are active?
- Is the protocol TCP, HTTP, TLS, or another protocol?
- Which network and HTTP filters run?

### RDS — routes

Defines HTTP routing decisions.

Examples:

- Host and path matching.
- Header or method matching.
- Weighted rollout.
- Redirects and rewrites.
- Retry and timeout policy.

### CDS — clusters

Defines logical upstream destinations, connection pools, TLS behavior, load-balancing policy, circuit breakers, and outlier detection.

### EDS — endpoints

Defines concrete addresses and locality information for each upstream cluster.

Endpoint churn often dominates at scale because pod readiness, scaling, rollouts, and failures continually change EDS state.

### SDS — secrets

Distributes dynamic certificates, keys, and trust material.

### ADS — aggregated delivery

Coordinates multiple resource types over a stream.

Operationally:

```text
control plane sends version
        |
        v
proxy validates
   |          |
  ACK        NACK
   |          |
accepted   old accepted state remains
```

A NACK means the proxy rejected an update. It may still be serving an older accepted configuration.

## 6. Endpoint-change propagation

When a new workload becomes ready:

```text
1. workload readiness becomes true
2. registry endpoint state changes
3. control plane receives the event
4. internal model is updated
5. affected consumers are selected
6. xDS resources are generated
7. updates are sent
8. proxies validate
9. proxies ACK or NACK
10. new endpoint becomes eligible
```

At every step ask:

- How many objects are watched?
- How many consumers are affected?
- How much computation is required?
- How many bytes are generated?
- How quickly do proxies converge?
- What happens during backpressure or reconnect storms?
- What happens if a proxy rejects the update?

## 7. Why configuration explodes

A naive mesh can create growth across several dimensions:

```text
services
× ports
× subsets
× routes
× endpoints
× policies
× proxies
× clusters
```

The exact implementation is not a simple multiplication, but the operational lesson is the same: broad visibility makes unrelated changes expensive.

Symptoms include:

- Large proxy bootstrap and steady-state memory.
- Slow proxy startup and readiness.
- High control-plane CPU and allocation rate.
- Large xDS responses.
- Long push queues.
- Endpoint churn triggering broad recomputation.
- Reconnect storms after control-plane or network disruption.
- Slow propagation of urgent security policy.
- One invalid resource causing widespread NACKs.

Do not measure only the number of services. Measure per-proxy configuration and change fan-out.

## 8. The three scoping layers

A scalable design applies scoping at multiple levels.

### 8.1 Control-plane input scope

Exclude namespaces or registries the mesh control plane does not need to watch.

Typical uses:

- Unmeshed namespaces.
- Platform infrastructure outside the mesh.
- Separate environments.
- Administrative or security boundaries.

This reduces watch volume and internal model size.

### 8.2 Producer-controlled export

A producer controls where its service or policy is visible.

Use this for:

- Namespace-local services.
- Domain-local APIs.
- Explicit shared-platform services.
- Preventing accidental global exposure.

This is both a scalability and governance control.

### 8.3 Consumer-controlled import

A consumer receives only the services it is expected to call.

With sidecars, this is commonly represented through dependency-scoped egress hosts.

Conceptual example:

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Sidecar
metadata:
  name: payments-default
  namespace: payments
spec:
  egress:
    - hosts:
        - "./*"
        - "shared-services/identity.shared-services.svc.cluster.local"
        - "ledger/*"
```

The exact object is less important than the model:

> The consumer imports a bounded dependency view instead of receiving the entire mesh graph.

## 9. Dependency declarations as platform data

Thousands of handwritten dependency objects will drift. Treat dependency scope as generated or validated platform data.

Possible sources:

- Service catalog ownership metadata.
- Deployment manifests.
- API gateway definitions.
- Code-level client declarations.
- Observed traffic.
- Security review and exception workflows.

A safe operating model combines declared and observed dependencies:

```text
declared graph
    +
observed traffic
    |
    v
validation and drift report
```

Do not automatically authorize every observed connection. Observed traffic may include compromise, accidental coupling, retries to obsolete services, or shadow traffic.

Recommended workflow:

1. Teams declare required dependencies.
2. CI validates names, ownership, and environment boundaries.
3. Policy is generated consistently.
4. Observed flows identify missing or obsolete declarations.
5. Exceptions have owners and expiry.
6. Removal is staged and monitored.

## 10. Sidecar and Ambient dataplanes

### Sidecar model

```text
application -> local Envoy -> destination Envoy -> application
```

Strengths:

- Per-workload L7 policy and routing.
- Mature traffic-management model.
- Strong per-workload isolation of proxy state.

Costs:

- Per-pod CPU and memory.
- Startup ordering and injection concerns.
- Large total proxy fleet.
- Broad configuration can become expensive.

### Ambient model

```text
application
   -> node-level secure L4 dataplane
   -> optional waypoint for L7
   -> destination dataplane
```

Strengths:

- Shared L4 identity and encryption path.
- Reduced sidecar footprint.
- L7 processing can be attached selectively.

Trade-offs:

- Shared node-level components create different capacity and failure domains.
- Waypoint placement and ownership matter.
- Traffic capture and policy semantics differ.
- xDS and control-plane scaling still exist.

Do not claim Ambient removes the discovery-scaling problem. It changes dataplane shape; it does not eliminate registry churn, policy computation, identity distribution, or convergence requirements.

## 11. Partition failure domains

A single global mesh is often an organizational convenience and an operational hazard.

Partition by boundaries that matter:

- Region.
- Environment.
- Trust domain.
- Business domain.
- Regulatory boundary.
- Cluster lifecycle.

Design rules:

- Prefer local endpoints.
- Make cross-region calls explicit.
- Avoid exporting every endpoint globally.
- Keep control-plane failure local where possible.
- Use stable gateways for intentional cross-domain traffic.
- Separate blast radius from administrative convenience.

The goal is not maximal isolation at any cost. The goal is intentional coupling.

## 12. Multi-cluster and multi-region discovery

Questions to answer:

1. Is service identity shared across clusters?
2. Are endpoints directly routable?
3. Is east-west traffic direct or gateway-mediated?
4. Which control plane owns endpoint truth?
5. How are trust bundles and identities federated?
6. What happens during cluster, region, or interconnect partition?
7. When are remote endpoints eligible?
8. How is failback controlled?

Avoid one global endpoint set when normal traffic should remain local. Global discovery can turn remote endpoint churn into local control-plane work and can accidentally make cross-region fallback the default.

## 13. Locality and load balancing

Locality-aware routing reduces latency and cross-zone or cross-region cost, but can overload a local failure domain if configured without capacity awareness.

A good policy distinguishes:

- Prefer local.
- Spill over when local capacity is exhausted.
- Fail over when local health is insufficient.
- Never cross a regulatory or trust boundary.

Locality is not only a proxy setting. It depends on accurate endpoint topology, capacity, health, and network reachability.

## 14. Control-plane high availability

High availability requires more than multiple replicas.

Design for:

- Topology spread across failure domains.
- Pod disruption budgets and controlled upgrades.
- Revisioned or canary control-plane rollout.
- Capacity headroom for peak push and reconnect rates.
- Bounded queueing and backpressure.
- Stable leader-election and certificate paths.
- Protection from noisy or malformed config sources.
- Separate staging for high-risk policy changes.

A control plane can be “up” while convergence is unusably slow. Availability must include freshness.

## 15. Last-known-good behavior

During a temporary control-plane outage, already-programmed proxies should continue serving accepted configuration.

What continues:

- Existing listeners and routes.
- Existing endpoint sets.
- Existing policy.
- Existing certificates until expiry or rotation is required.

What degrades:

- New endpoint discovery.
- New routes and policy.
- Certificate rotation.
- New workload bootstrap.
- Removal of failed or revoked destinations.

Therefore define a stale-configuration budget:

```text
maximum tolerable control-plane unavailability
<
minimum time before stale endpoints, policy, or certificates become unsafe
```

## 16. Configuration validation and rollout

Treat mesh configuration as production software.

Pipeline:

```text
schema validation
  -> semantic validation
  -> ownership and visibility checks
  -> isolated test
  -> canary control-plane revision
  -> canary workloads
  -> staged domain rollout
  -> fleet rollout
```

Validate:

- Unknown destinations.
- Conflicting routes.
- Invalid TLS modes.
- Policy that accidentally broadens access.
- Excessive proxy config growth.
- Cross-domain exports.
- Missing dependency declarations.
- Unsupported proxy-version combinations.

Rollback must restore a previously accepted configuration, not merely revert a source file and hope convergence succeeds.

## 17. Observability that matters

### Control-plane signals

- Connected proxy count.
- Push queue depth.
- Push requests and completion rate.
- Full versus incremental pushes.
- Push latency by percentile.
- Configuration generation CPU and memory.
- xDS response bytes.
- Reconnect rate.
- ACK and NACK rate.
- Distribution lag and stale proxies.
- Endpoint and policy event rate.

### Per-proxy signals

- Listener, route, cluster, and endpoint counts.
- Config memory footprint.
- Time to first accepted configuration.
- Proxy startup duration.
- Last accepted version.
- NACK reason.
- Certificate expiry and rotation state.
- Upstream connection and circuit-breaker pressure.

### Business and platform signals

- Service startup SLO.
- Endpoint-convergence SLO.
- Policy-propagation SLO.
- Request success during control-plane disruption.
- Cross-zone and cross-region traffic ratio.
- Number of undeclared observed dependencies.

## 18. Failure scenarios

### 18.1 Endpoint storm

A large rollout or autoscaling event creates rapid endpoint churn.

Investigate:

- Event rate.
- Number of affected proxies.
- Incremental versus broad pushes.
- Push queueing.
- Proxy ACK delay.

Mitigate:

- Slow the rollout.
- Reduce configuration fan-out.
- Isolate the noisy domain.
- Add control-plane capacity.
- Prefer incremental update paths where supported.

### 18.2 Reconnect storm

After a network or control-plane disruption, thousands of proxies reconnect together.

Mitigate with:

- Jittered reconnect behavior.
- Capacity for burst load.
- Load balancing across control-plane replicas.
- Backpressure and connection limits.
- Staged recovery if necessary.

### 18.3 Invalid configuration and NACKs

Symptoms:

- One proxy cohort remains on old state.
- Only one revision or architecture fails.
- Control plane appears healthy.

Response:

- Identify rejected resource and proxy cohort.
- Preserve old accepted state.
- Stop rollout.
- Correct or roll back the offending configuration.
- Add pre-merge semantic tests reproducing the incompatibility.

### 18.4 Stale endpoints during control-plane outage

Already-programmed proxies serve, but endpoint membership changes are not learned.

Mitigation depends on application behavior:

- Outlier detection may remove failing endpoints locally.
- Stable endpoints reduce churn sensitivity.
- Longer certificate lifetime increases availability but extends credential exposure.
- Emergency changes may require restoring the control plane before normal rollout.

### 18.5 Broad export creates accidental coupling

A service becomes globally visible and consumers begin depending on it without ownership agreement.

Prevention:

- Default-local export.
- Catalog ownership.
- Consumer imports.
- Observed dependency review.
- Time-limited exceptions.

## 19. Security model

Fine-grained discovery is part of authorization, not only performance.

Principles:

- Discovery visibility does not replace runtime authorization.
- Runtime authorization does not justify global discovery visibility.
- Workload identity should be stable and verifiable.
- Trust domains and certificate authorities need explicit boundaries.
- Policy must fail predictably during partial control-plane failure.
- Sensitive services should not be discoverable by unrelated workloads.

Use both:

```text
small visible dependency graph
+
explicit runtime authorization
```

## 20. Capacity model

Model at least:

- Number of proxies.
- Number of services and endpoints visible per proxy.
- Average and peak endpoint-change rate.
- Average xDS bytes per proxy.
- Full-push and incremental-push cost.
- Reconnect burst size.
- Proxy startup concurrency.
- Certificate rotation rate.
- Maximum acceptable convergence time.

A useful approximation is:

```text
control-plane work
≈ change rate × affected proxies × generation cost per affected view
```

The design objective is to reduce affected proxies and generation cost, not only add control-plane replicas.

## 21. Migration strategy

A safe migration from broad visibility:

1. Inventory services, endpoints, policies, and actual dependencies.
2. Measure current per-proxy configuration size and convergence.
3. Establish ownership and default visibility rules.
4. Generate dependency declarations in audit mode.
5. Compare declared and observed traffic.
6. Scope a low-risk domain first.
7. Canary changes by proxy revision and workload cohort.
8. Monitor NACKs, startup time, and denied traffic.
9. Expand by domain and environment.
10. Remove duplicated or obsolete global exports.
11. Test control-plane outage and reconnect behavior.
12. Enforce policy in CI after migration stabilizes.

## 22. Ninety-second interview answer

> I would treat discovery for more than 1,000 services as a configuration-distribution and failure-domain problem, not simply DNS. Kubernetes Services and EndpointSlices remain the endpoint source of truth. The mesh control plane watches selected registries and policies, computes workload-specific listeners, routes, clusters, endpoints, identity, and authorization state, and distributes them over xDS.
>
> The key rule is that a workload receives only the services and policies it is expected to use. I would reduce control-plane input scope, use producer-controlled exports, and generate or validate consumer dependency imports from a service catalog. I would partition the mesh by region, environment, trust boundary, and business domain, prefer local endpoints, and make cross-region traffic explicit.
>
> I would run revisioned control-plane canaries with topology spread and enough headroom for endpoint storms and proxy reconnects. I would measure push queueing, generation latency, xDS bytes, per-proxy resource counts, ACKs, NACKs, stale proxies, startup time, and endpoint-convergence SLOs. Already-programmed proxies must continue using their last accepted configuration during a temporary control-plane outage, while we explicitly manage the stale-config and certificate-rotation limits.
>
> Sidecars remain appropriate where per-workload L7 behavior is required. Ambient can reduce sidecar overhead for shared L4 identity and mTLS, with waypoints added selectively, but it does not remove xDS or discovery scaling. Success means local endpoint churn does not trigger mesh-wide work, each workload receives a small correct dependency view, and control-plane disruption does not interrupt already-programmed traffic.

## 23. Adversarial follow-ups

1. Why is CoreDNS not enough?
2. What exactly grows when service count increases?
3. Which event types cause broad versus incremental pushes?
4. How do you stop one namespace rollout from affecting every proxy?
5. What survives when the mesh control plane is unavailable?
6. How long can stale configuration remain safe?
7. How do you prevent generated dependency policy from authorizing compromised traffic?
8. What changes in Ambient mode, and what does not?
9. How do you detect proxies running an older accepted version?
10. How do you roll back a configuration that some proxies ACKed and others NACKed?
11. Why might multiple control-plane replicas still fail under a reconnect storm?
12. How do you test endpoint convergence without causing a production outage?
13. When should cross-region endpoints be visible?
14. How do you prevent service discovery from becoming an organizational coupling mechanism?
15. Which metrics prove the migration reduced blast radius rather than merely moving cost?

## 24. Review checklist

A production-ready design should answer yes to the following:

- Is the registry source of truth explicit?
- Are control-plane input scope, producer exports, and consumer imports defined?
- Is the dependency graph owned and validated?
- Are regional and trust failure domains partitioned?
- Is last-known-good behavior tested?
- Are startup, endpoint-convergence, and policy-propagation SLOs defined?
- Are ACK, NACK, stale-proxy, and config-size signals monitored?
- Is reconnect-storm capacity tested?
- Are configuration changes canaried and reversible?
- Are sidecar and Ambient choices based on required policy, not fashion?
- Does the design reduce affected consumers per change?
- Can the team explain what happens during control-plane, registry, certificate, and interconnect failure?

## Related canonical material

- [Linux networking, containers, cgroups, and security](../linux/05-networking-containers-security.md)
- [Linux observability and production debugging](../linux/06-observability-debugging.md)
- [eBPF, Cilium, Hubble, Falco, and Tetragon](../ebpf-security/cilium-hubble-falco-tetragon.md)
- [Consolidated curriculum map](../../curriculum-map.md)
