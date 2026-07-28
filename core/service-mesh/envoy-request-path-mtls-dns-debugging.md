# Envoy Request-Path, mTLS, and DNS Debugging

## Purpose

This chapter provides a repeatable method for diagnosing service-mesh failures without assuming the application, Kubernetes Service, DNS, certificate, or control plane is at fault prematurely.

## Staff/Principal answer

> I trace one failing request across the exact path: client application, local proxy, DNS or service discovery, outbound cluster selection, network route, destination proxy, inbound listener, and application. I compare a successful and failed cohort, inspect Envoy listeners, routes, clusters, endpoints, config versions, NACKs, connection pools, retries, and response flags, and verify certificate identity and trust separately from TCP reachability. I distinguish data-plane failure from stale or unavailable xDS control plane. The safest mitigation is usually narrow: restore endpoint discovery, correct one route or trust bundle, roll back one config, or bypass only a preapproved optional policy—not redeploy every application.

## Request path

```text
client process
  -> local DNS / service discovery
  -> Envoy outbound listener
  -> route and cluster selection
  -> endpoint load balancing
  -> TCP/TLS/mTLS handshake
  -> destination Envoy inbound listener
  -> destination application
```

At each hop ask:

1. What configuration should be active?
2. What configuration is actually active?
3. What network connection was attempted?
4. Which component generated the status code or reset?
5. Is the failure universal or cohort-specific?

## First evidence to collect

- one successful and one failed request with timestamps and trace/request IDs;
- source and destination workload identity, namespace, cluster, region, version, and node;
- Envoy access logs and response flags;
- listener, route, cluster, and endpoint dumps;
- proxy sync state and config version;
- xDS ACK/NACK and rejection reason;
- DNS answer, TTL, resolver path, and search suffixes;
- certificate subject/SAN, issuer, trust bundle, validity, and clock;
- packet or socket evidence when the ownership boundary remains unclear.

## Envoy response flags

Common flags provide direction, not complete root cause:

| Flag | Meaning to investigate |
|---|---|
| `UH` | No healthy upstream hosts |
| `UF` | Upstream connection failure |
| `UO` | Upstream overflow / circuit-breaker limit |
| `UT` | Upstream request timeout |
| `NR` | No route configured |
| `NC` | No cluster found |
| `DC` | Downstream connection termination |
| `UC` | Upstream connection termination |

Always correlate the flag with cluster health, route selection, endpoint state, TLS details, and application evidence.

## Configuration isolation

Inspect the active data-plane configuration rather than only the desired YAML.

Questions:

- Does the listener match the destination port and protocol?
- Which route matched the authority, path, headers, and method?
- Which cluster was selected?
- Which endpoints are active, unhealthy, draining, or absent?
- Is the proxy using the expected xDS version?
- Did it NACK a resource?
- Is an older last-known-good config still serving?
- Did a broad push increase config size, CPU, or convergence time?

Useful commands vary by mesh, but the evidence categories remain:

```bash
istioctl proxy-status
istioctl proxy-config listeners POD -n NAMESPACE
istioctl proxy-config routes POD -n NAMESPACE
istioctl proxy-config clusters POD -n NAMESPACE
istioctl proxy-config endpoints POD -n NAMESPACE
```

## DNS and service discovery

Identify the resolver boundary before changing the application.

Potential paths include:

- libc and application cache;
- node resolver;
- CoreDNS;
- NodeLocal DNSCache;
- mesh DNS capture;
- external resolver;
- ServiceEntry or equivalent external-service registration.

Compare:

- answer and TTL from the application context;
- answer from the proxy context;
- endpoint discovery in xDS;
- Kubernetes EndpointSlice state;
- destination cluster health.

A correct DNS answer does not prove Envoy has the correct cluster or endpoint set. Conversely, xDS endpoint discovery may make DNS irrelevant for a specific internal request path.

## mTLS isolation

Separate four questions:

1. Can the source connect at TCP level?
2. Does TLS negotiation complete?
3. Does the peer certificate represent the expected workload identity?
4. Does authorization permit that identity to call the destination?

Investigate:

- certificate expiry and clock skew;
- SAN or SPIFFE identity;
- trust-domain aliases;
- root and intermediate rotation overlap;
- strict versus permissive mode mismatch;
- plaintext-to-TLS or TLS-to-plaintext mismatch;
- SNI and destination-rule selection;
- authorization-policy principal and namespace matching;
- stale secrets in the proxy.

Do not disable mTLS globally to test a theory. Use a narrowly scoped diagnostic workload or preapproved policy exception.

## Control-plane versus data-plane failure

### Control-plane symptoms

- proxies stop receiving updates;
- xDS push latency or NACKs rise;
- only newly deployed workloads fail;
- stale proxies continue serving last-known-good config;
- config convergence differs by cluster or revision.

### Data-plane symptoms

- one proxy restarts or exhausts memory;
- connection pools overflow;
- listener or route is locally absent;
- one node or network path fails;
- certificate or secret is stale on a subset of proxies.

A resilient mesh should continue serving existing known routes during a temporary control-plane outage. New endpoints, certificates, and policy changes may still fail to converge.

## Retry, timeout, and circuit-breaker ownership

Map the full deadline tree:

```text
client deadline
  > gateway timeout
    > service timeout
      > per-try timeout
        > dependency timeout
```

Avoid retries at multiple layers. Track original requests separately from attempts. A `504` may be produced by a gateway or proxy after the upstream already completed too late.

Check:

- per-try and overall timeout;
- retry conditions and count;
- outlier detection;
- pending-request, connection, and request circuit-breaker thresholds;
- connection-pool reuse and exhaustion;
- whether retries cross zones or regions and amplify failure.

## Safe mitigation order

1. stop the bad configuration rollout;
2. roll back the smallest route, policy, certificate, or mesh revision;
3. restore missing endpoints or discovery;
4. narrow a failing policy selector;
5. reduce retries or concurrency causing amplification;
6. restart only a demonstrably stale or broken proxy cohort;
7. use bypass only for a documented noncritical path with expiry and owner.

## Recovery validation

- external and service-to-service synthetic probes succeed;
- failed and successful cohorts converge;
- proxies ACK the intended config version;
- xDS NACKs stop;
- endpoint health and connection pools normalize;
- certificate identities and authorization are correct;
- user-facing latency and success recover;
- no emergency plaintext or bypass rule remains.

## Preventive controls

- config validation and dry-run analysis in CI;
- staged mesh and trust-bundle rollout by revision/ring;
- xDS push, NACK, convergence, config-size, and proxy-memory SLOs;
- certificate-expiry and rotation-overlap tests;
- DNS-capture and NodeLocal DNSCache failure exercises;
- golden request-path probes across clusters and trust domains;
- route and retry ownership documentation;
- last-known-good behavior tests during control-plane outage.

## Weak answers to avoid

- “Restart all sidecars.”
- “It is probably DNS.”
- “Disable mTLS.”
- “The YAML is correct, so the proxy is correct.”
- “Add more retries.”
- “If the mesh control plane is down, all traffic must stop.”
