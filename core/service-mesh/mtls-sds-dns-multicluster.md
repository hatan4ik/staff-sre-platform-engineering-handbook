# Service-Mesh mTLS, SDS, DNS Capture, and Multi-Cluster Reliability

This chapter is the canonical foundation for service-mesh identity, certificate delivery, DNS capture, east-west gateways, multi-cluster discovery, and failover incidents.

## Interview answer in 90 seconds

> I separate service identity, certificate delivery, name resolution, discovery, and traffic routing because each fails differently. Workload identity is derived from an authenticated platform identity, certificates are short-lived and delivered through SDS or an equivalent agent path, and authorization uses the authenticated peer identity rather than source IP alone. DNS capture must have explicit fallback and cache behavior, and multi-cluster discovery must define which services are exported, imported, and reachable through which gateway. During an incident I compare healthy and affected workloads by trust domain, certificate serial and expiry, mesh revision, DNS mode, cluster, network, locality, and gateway. I inspect effective proxy secrets, clusters, endpoints, transport sockets, DNS evidence, and control-plane ACK/NACK state. Mitigation is bounded: restore certificate delivery, remove a bad trust bundle, route around a gateway or cluster, or temporarily reduce strictness only through an approved, narrow break-glass policy. Recovery is proven by successful authenticated handshakes, authorized requests, fresh discovery, and client-facing SLIs.

## Identity and traffic path

```text
platform workload identity
          |
          v
certificate authority / issuer
          |
          v
SDS or node/workload agent
          |
          v
proxy secret and trust bundle
          |
          v
mTLS handshake
          |
          v
peer identity extraction
          |
          v
authorization policy
          |
          v
service request
```

Name resolution and endpoint discovery run alongside this path:

```text
application name
   -> DNS capture or resolver
   -> service registry / control plane
   -> cluster and endpoint selection
   -> local or east-west gateway
   -> remote workload
```

## Identity principles

A robust mesh identity system has:

- a verifiable workload identity source;
- short-lived credentials;
- bounded trust domains;
- explicit federation rules;
- automatic rotation;
- revocation or rapid expiry strategy;
- workload-to-certificate binding;
- authorization based on authenticated identity;
- no dependence on mutable source IP as the primary identity;
- audit evidence for issuance and policy changes.

## mTLS modes

Common operating modes include:

- strict mTLS;
- permissive migration mode;
- plaintext for explicitly excluded traffic;
- egress origination to external TLS services;
- passthrough where the proxy does not terminate TLS.

### Strict mode

Advantages:

- rejects unauthenticated peers;
- supports identity-based authorization;
- reduces accidental plaintext.

Risks:

- migration or bootstrap failure can become an outage;
- workloads outside the mesh need explicit integration;
- policy and destination configuration must agree;
- certificate-delivery failure blocks new connections.

### Permissive mode

Useful only as a bounded transition or compatibility mechanism. Long-lived permissive mode can hide missing identity and policy coverage.

## SDS and secret delivery

SDS or equivalent dynamic secret delivery allows proxies to receive certificates and trust bundles without embedding long-lived files in images.

Failure modes:

- issuer unavailable;
- workload identity exchange fails;
- node or workload agent unavailable;
- authorization prevents secret delivery;
- certificate is expired or not yet valid;
- trust bundle is stale or wrong;
- secret name mismatch;
- proxy rejects the secret;
- rotation occurs but long-lived connections keep old credentials;
- clock skew breaks validity checks;
- root transition is incomplete.

## Certificate rotation

Rotation should be tested as a state transition:

```text
old leaf + old trust
  -> new leaf issued
  -> old and new roots overlap where required
  -> proxies receive new secret
  -> new connections use new leaf
  -> old connections drain
  -> old root or leaf expires/retired
```

Measure:

- time to issue;
- time to deliver;
- time to active use;
- failed handshakes;
- percentage of proxies with the intended trust bundle;
- long-lived connection age;
- expired-certificate count;
- rotation lag by cluster and mesh revision.

## Trust-domain design

Use separate trust domains when compromise, administration, compliance, or environment boundaries require them.

Federation must define:

- which identities are accepted;
- namespace or service mapping;
- trust anchors;
- certificate path validation;
- authorization policy;
- rotation and root transition;
- audit ownership;
- failure and revocation behavior.

Do not merge all environments into one global trust domain merely to simplify configuration.

## Authorization

Authorization should consider:

- authenticated principal;
- service account or workload identity;
- namespace;
- source and destination service;
- method, path, and port where appropriate;
- environment and trust domain;
- request claims only when the proxy can validate them;
- explicit deny before broad allow where supported;
- default-deny posture for sensitive services.

Authorization denial and TLS failure are different. Preserve evidence for both.

## mTLS incident workflow

### Symptoms

- new connections fail while old ones continue;
- one mesh revision or node pool fails;
- only cross-cluster traffic fails;
- plaintext clients fail after strict-mode rollout;
- certificate rotation aligns with handshake errors;
- one trust domain or namespace is denied;
- upstream cluster shows transport failures.

### Compare cohorts

- source and destination identity;
- certificate serial, issuer, expiry, and trust bundle;
- proxy and mesh revision;
- node and cluster;
- strict/permissive policy;
- destination rule or transport-socket config;
- new versus reused connections;
- local versus remote cluster.

### Evidence

Use protected debug paths to inspect:

- active proxy secrets;
- certificate chain and validity;
- listener and cluster transport sockets;
- TLS handshake error counters;
- authorization denial logs;
- SDS delivery status;
- control-plane ACK/NACK;
- issuer and agent health;
- time synchronization;
- recent policy and root-bundle changes.

Useful patterns:

```bash
istioctl proxy-config secret <pod> -n <namespace>
istioctl proxy-config clusters <pod> -n <namespace>
istioctl proxy-status
openssl s_client -connect <host>:<port> -servername <sni> -showcerts
```

Do not copy private keys into incident tickets or chat.

## DNS capture

Service meshes may intercept DNS requests to resolve service names, synthesize addresses, or support service entries and virtual interfaces.

Benefits:

- service discovery beyond native cluster DNS;
- reduced resolver load;
- consistent mesh-aware names;
- support for external and multi-cluster services;
- local caching.

Risks:

- capture rules differ by protocol or workload mode;
- stale local cache;
- search-domain and `ndots` surprises;
- name collision;
- fallback resolver unavailable;
- synthetic address conflicts;
- UDP/TCP handling differences;
- host-network or privileged workload exceptions;
- split-horizon behavior differs across clusters.

## DNS debugging flow

1. record the exact queried name and application resolver behavior;
2. compare application, proxy, node, and upstream resolver results;
3. inspect search domains, `ndots`, and resolver configuration;
4. determine whether DNS is captured;
5. inspect mesh service registry and service-entry state;
6. compare healthy and failing clusters or proxy revisions;
7. test UDP and TCP DNS where relevant;
8. verify TTL, negative caching, and stale entries;
9. correlate with endpoint discovery and routing.

Commands:

```bash
cat /etc/resolv.conf
getent hosts <name>
dig <name>
dig +tcp <name>
kubectl get service,endpointslice -A
istioctl proxy-config clusters <pod> -n <namespace>
```

A successful DNS answer does not prove the selected endpoint or route is reachable.

## Multi-cluster models

### Independent clusters with shared services

Each cluster owns local traffic and selectively accesses remote services.

### Primary-remote control plane

One control plane manages proxies in remote clusters. This simplifies policy but expands control-plane failure impact and network dependency.

### Multi-primary

Each cluster has a control plane. This improves local autonomy but requires consistent trust, export, policy, and discovery behavior.

### Multi-network

Clusters communicate through east-west gateways because pod networks are not directly routable.

## Service export and import

Define explicitly:

- which services are exported;
- which consumers may import them;
- naming and collision policy;
- locality preference;
- failover priority;
- health and endpoint freshness;
- identity and authorization across clusters;
- gateway and network reachability;
- ownership of remote dependencies.

Implicit global service visibility creates uncontrolled dependency graphs and blast radius.

## East-west gateways

Gateways introduce:

- connection and TLS termination points;
- network and load-balancer dependencies;
- capacity and quota limits;
- certificate and identity scope;
- routing and SNI configuration;
- cross-zone or cross-region cost and latency;
- new observability boundaries.

Run multiple replicas and failure-domain-aware frontends, but also ensure remote endpoints and authority are valid.

## Locality and failover

Preferred order may be:

```text
same zone -> same region/cluster -> remote cluster -> remote region
```

Failover must consider:

- destination capacity;
- data locality and consistency;
- write authority;
- network cost and latency;
- gateway capacity;
- certificate trust;
- dependency topology;
- retry and connection storms;
- failback behavior.

Do not make every service globally fail over by default.

## Control-plane outage behavior

Desired data-plane properties:

- continue serving last-known-good listeners, routes, clusters, endpoints, and secrets;
- reject invalid updates rather than replacing good state;
- retain credentials long enough for the tested outage window;
- expose stale configuration and expiry risk;
- reconnect with backoff and jitter;
- avoid simultaneous fleet-wide resync storms;
- prioritize critical updates after recovery.

Last-known-good behavior has a limit: expiring certificates, stale endpoints, and changed policy eventually require the control plane.

## Multi-cluster incident workflow

### Bound the fault

Compare:

- local versus remote traffic;
- one source or destination cluster;
- one network or gateway;
- one trust domain;
- one service export/import;
- one locality or subset;
- one proxy/control-plane revision;
- new versus existing connections.

### Stabilize

1. stop bad discovery, trust, or policy rollout;
2. prefer healthy local endpoints where safe;
3. remove or deprioritize a failed remote cluster;
4. restore gateway, certificate, or network path;
5. reduce cross-cluster retries and connection pressure;
6. use a narrow break-glass identity or policy only with approval and expiry;
7. verify destination capacity before shifting traffic;
8. prove authenticated end-to-end recovery.

## SLOs and signals

Track:

- mTLS handshake success and latency;
- authorization allow/deny by policy and principal;
- certificate expiry horizon and rotation lag;
- SDS delivery success;
- trust-bundle version convergence;
- DNS resolution success and latency;
- negative-cache and stale-answer rate;
- service discovery and endpoint freshness;
- xDS ACK/NACK and convergence;
- east-west gateway success, latency, saturation, and resets;
- local versus remote traffic percentage;
- failover and failback duration;
- client journey success by cluster and trust domain.

## Security safeguards

- protect proxy admin and secret-debug endpoints;
- never log private key material;
- use short-lived operator credentials;
- require approval for permissive-mode or policy bypass;
- scope trust federation narrowly;
- separate production and nonproduction roots where appropriate;
- audit issuer, root, policy, and export changes;
- test compromised-workload containment;
- preserve identity during gateway traversal.

## Weak answers to avoid

- “Turn off mTLS.”
- “Restart all sidecars to rotate certificates.”
- “DNS is healthy because `dig` works from my laptop.”
- “Multi-cluster means all services are globally reachable.”
- “The control plane is highly available, so the data plane is safe.”
- “Fail over all traffic to the other cluster.”
- “Source IP is the service identity.”

## Adversarial follow-ups

### Why do old connections work while new connections fail?

Existing TLS sessions or pooled connections may continue using previously valid state, while new handshakes require a current certificate, trust bundle, endpoint, or gateway path.

### When is permissive mTLS acceptable?

During a bounded migration or explicitly approved compatibility exception with telemetry, ownership, and expiry. It should not be the unexamined permanent default for sensitive traffic.

### How do you prevent control-plane loss from expiring every proxy?

Use sufficiently short but operationally safe certificate lifetimes, early rotation, cached last-known-good secrets, resilient issuers/agents, expiry monitoring, and game days that exceed the expected control-plane outage window.

### How do you decide whether to use a remote endpoint?

Only when service policy permits it, data and write authority are compatible, destination capacity exists, identity and network paths are healthy, and the latency/cost trade-off is acceptable.

### What proves recovery?

New and existing connections authenticate, authorization behaves as intended, DNS and discovery are fresh, gateways are healthy, the affected cross-cluster journey meets SLO, and temporary bypasses are removed.

## Principal-level review checklist

- workload identity is anchored to a trusted platform source;
- leaf and root rotation are tested;
- strict/permissive policy has explicit lifecycle;
- trust domains and federation boundaries are intentional;
- DNS capture and fallback behavior are documented;
- service exports/imports are least privilege;
- east-west gateways have capacity and failure-domain analysis;
- remote failover includes data, identity, capacity, and failback safety;
- data planes have bounded last-known-good behavior;
- mTLS, DNS, discovery, and gateway failure modes have game days.
