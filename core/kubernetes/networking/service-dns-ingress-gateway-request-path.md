# Kubernetes Service, DNS, Ingress, and Gateway Request Paths

This chapter is the canonical foundation for Kubernetes networking incidents involving Services, EndpointSlices, kube-proxy or eBPF dataplanes, CNI, CoreDNS, Ingress, Gateway API, and external load balancers.

## Interview answer in 90 seconds

> I debug Kubernetes networking from the client journey inward and identify the exact layer that owns the failure. The path may include public DNS, CDN or load balancer, Ingress or Gateway, Service VIP, kube-proxy or eBPF service translation, EndpointSlice selection, pod networking, NetworkPolicy, and the application listener. I compare a working and failing request by source, DNS answer, IP family, node, zone, route, service port, endpoint, and release. I verify desired objects and effective dataplane state because a Service and Ready pod do not prove packets reach the right socket. Common failures are stale or empty EndpointSlices, readiness removing endpoints, wrong targetPort, CNI address exhaustion, network policy, asymmetric routes, conntrack or NAT pressure, DNS cache behavior, and gateway configuration mismatch. Mitigation is narrow—restore endpoints, route around one zone or gateway, correct a policy or port, reduce retry pressure, or roll back the networking change. Recovery is proven from outside the cluster and through endpoint, connection, DNS, and user SLI evidence.

## End-to-end path

```text
client
  |
  v
public DNS / resolver cache
  |
  v
CDN / external load balancer
  |
  v
Ingress or Gateway listener
  |
  v
route match and backend reference
  |
  v
Kubernetes Service VIP or headless discovery
  |
  v
kube-proxy / IPVS / nftables / eBPF service translation
  |
  v
EndpointSlice endpoint
  |
  v
CNI route, overlay, underlay, or VPC path
  |
  v
pod network namespace and application socket
  |
  v
downstream dependency
```

The exact implementation varies, but the diagnostic method remains: prove each handoff.

## Kubernetes networking model

The Kubernetes model expects:

- every pod has an address;
- pods can communicate without per-pod NAT in the abstract model;
- nodes can communicate with pods;
- Services provide stable discovery and virtual addressing;
- network plugins implement the real routes, encapsulation, policy, and address management.

Cloud and CNI implementations may use native VPC addresses, overlays, eBPF, IPVS, nftables, iptables, or combinations.

## Service types

### ClusterIP

Provides a virtual service address reachable through the cluster dataplane.

### Headless Service

Returns endpoint addresses directly through DNS rather than a Service VIP. This changes load balancing, connection behavior, and stale-DNS risk.

### NodePort

Exposes a port on nodes. Often used beneath external load balancers; health-check and traffic-policy behavior matter.

### LoadBalancer

Triggers provider or controller integration to create an external or internal load balancer.

### ExternalName

Maps service discovery to an external DNS name and inherits external DNS/TLS semantics.

## Service and target ports

A Service may define:

- listener `port`;
- backend `targetPort` by number or named port;
- protocol;
- optional application-protocol hints.

Common failures:

- targetPort does not match the container listener;
- named port missing or renamed;
- protocol mismatch;
- application listens only on loopback;
- readiness succeeds on a different port than traffic;
- dual-stack family mismatch;
- gateway backend reference uses the wrong port.

## EndpointSlices

EndpointSlices represent backend membership and may include readiness, serving, terminating state, topology, hints, and address type.

Investigate:

```bash
kubectl get service <service> -n <namespace> -o yaml
kubectl get endpointslice -n <namespace> -l kubernetes.io/service-name=<service> -o yaml
kubectl get pods -n <namespace> -l <selector> -o wide
```

Failure patterns:

- Service selector matches no pods;
- pod labels changed during deployment;
- readiness removes every endpoint;
- endpoint controller or API watch is delayed;
- terminating endpoints remain under special traffic policy;
- wrong address family;
- topology hints interact with missing local capacity;
- manually managed endpoint data is stale.

## Dataplane implementations

### kube-proxy iptables/nftables

Rules translate Service traffic to endpoint addresses. Large rule sets, delayed sync, or host firewall conflicts can affect behavior.

### IPVS

Uses kernel virtual-server state and connection scheduling. Inspect virtual services and real servers when available.

### eBPF service dataplane

Programs maps and kernel hooks for service translation, policy, and load balancing. Inspect agent health, map state, endpoint identity, and program attachment with implementation-specific tools.

Do not mix commands and assumptions from one dataplane with another.

## Session affinity and connection persistence

Existing connections can continue using a removed or unhealthy endpoint until reset or drained.

Potential sources of cohort-specific failure:

- client keepalive;
- HTTP/2 multiplexing;
- load-balancer target stickiness;
- Service session affinity;
- NAT or conntrack entries;
- DNS caching for headless services;
- proxy connection pools.

Compare new and existing connections.

## `externalTrafficPolicy`

`Local` may preserve client source address and avoid extra hops but requires healthy local endpoints on load-balancer target nodes.

Failure modes:

- load balancer sends traffic to a node with no local endpoint;
- health-check port or policy mismatch;
- endpoint topology changes faster than load-balancer health;
- one zone lacks eligible endpoints;
- source-address preservation changes policy behavior.

`Cluster` allows cross-node forwarding but can add hops and source-NAT behavior depending on implementation.

## `internalTrafficPolicy` and topology

Locality policies can reduce latency and cross-zone cost but may fail when a node or zone has no local endpoint.

Define whether fallback is allowed. A strict local policy may intentionally fail rather than route remotely.

## CNI and address management

CNI responsibilities can include:

- pod address allocation;
- route or overlay setup;
- network namespace wiring;
- policy enforcement;
- cloud interface attachment;
- encryption;
- service translation;
- observability.

Common incidents:

- subnet or prefix exhaustion;
- interface or address quota;
- stale IP allocation;
- CNI agent unavailable;
- route table or tunnel failure;
- MTU mismatch;
- node bootstrap race;
- policy-programming lag;
- address reuse with stale neighbor or conntrack state.

A node can be Ready while pod networking cannot create a sandbox.

## MTU and fragmentation

Overlays, encryption, and tunnels reduce effective MTU.

Symptoms:

- small requests succeed but large responses hang;
- TLS handshake or certificate transfer fails;
- one path or zone fails;
- retransmissions rise;
- ICMP needed for path-MTU discovery is blocked.

Test with realistic packet sizes and protocols. Do not assume ping success proves application traffic is healthy.

## Conntrack, NAT, and port exhaustion

High connection churn or asymmetric routing can exhaust or confuse stateful translation.

Evidence:

- conntrack table usage and drops;
- NAT source-port utilization;
- connection states;
- retransmissions and resets;
- one node or gateway cohort;
- short-lived connection rate;
- retry storms;
- cross-zone path changes.

Connection reuse, bounded retries, and distributed egress can reduce pressure, but fix the actual ownership model.

## NetworkPolicy

NetworkPolicy behavior depends on CNI support and policy model.

Investigate:

- selected source and destination pods;
- ingress and egress direction;
- namespace and pod selectors;
- ports and protocols;
- DNS egress;
- default deny;
- host-network and node-local exceptions;
- policy propagation time;
- identity-based extensions outside the core API.

A policy object accepted by the API is not proof it is enforced as intended.

## DNS path

```text
application resolver
  -> pod /etc/resolv.conf
  -> node-local cache if used
  -> CoreDNS Service
  -> CoreDNS pod
  -> Kubernetes plugin or upstream resolver
  -> response cache
```

### Common DNS failures

- CoreDNS unavailable or saturated;
- EndpointSlice or Service path to DNS broken;
- node-local DNS cache failure;
- search-domain and `ndots` expansion;
- negative caching;
- stale external answer;
- upstream resolver failure;
- UDP fragmentation or blocked TCP fallback;
- excessive query volume from retrying applications;
- headless Service endpoint churn;
- split-horizon mismatch.

### DNS evidence

```bash
cat /etc/resolv.conf
getent hosts <name>
dig <name>
dig +tcp <name>
kubectl get pods,service,endpointslice -n kube-system
kubectl logs -n kube-system deploy/coredns --since=15m
```

Run tests from an affected pod, a healthy pod, a node where appropriate, and outside the cluster.

## Ingress and Gateway API

Ingress and Gateway resources describe intent; a controller programs actual load balancers and proxies.

### Gateway concepts

- GatewayClass — controller implementation;
- Gateway — listeners and infrastructure attachment;
- HTTPRoute, GRPCRoute, TCPRoute, TLSRoute, or related route types;
- parent references;
- backend references;
- cross-namespace reference permissions;
- status conditions showing acceptance and resolution.

### Failure patterns

- route not attached to intended Gateway;
- hostname or path match does not select;
- listener protocol or TLS mode mismatch;
- backend reference invalid or forbidden;
- controller has not reconciled;
- certificate missing or expired;
- health checks do not match application behavior;
- external load balancer targets the wrong nodes or ports;
- one controller revision programs different state;
- conflicting routes or precedence.

Inspect status conditions, controller logs, effective proxy/load-balancer configuration, and provider target health.

## TLS and SNI

At each hop determine:

- where TLS terminates;
- certificate and hostname;
- SNI value;
- ALPN and protocol;
- whether TLS is re-originated upstream;
- trust bundle and client identity;
- plaintext or encrypted backend expectation.

A DNS or route change can select an endpoint whose certificate does not match.

## Dual stack

IPv4 and IPv6 introduce cohort-specific behavior:

- client preference and Happy Eyeballs;
- Service IP families;
- endpoint address type;
- CNI and node-route support;
- external load-balancer family;
- network policy;
- DNS A and AAAA answers;
- NAT64 or proxy translation where used.

Compare failures by IP family explicitly.

## Incident workflow

### 1. State the client-visible symptom

- resolution failure;
- connection timeout;
- reset;
- TLS failure;
- 404 or route miss;
- 502/503/504;
- only one zone, node, IP family, or client cohort fails.

### 2. Trace the path

Record:

- resolved addresses and TTL;
- external load-balancer target and health;
- gateway listener and route;
- Service and port;
- EndpointSlice membership;
- selected endpoint;
- node and CNI path;
- application listener and dependency.

### 3. Compare healthy and affected cohorts

Dimensions:

- source network and resolver;
- IPv4 versus IPv6;
- gateway or load-balancer target;
- cluster, zone, node, and CNI agent;
- route and service;
- endpoint and release;
- new versus reused connection;
- policy and dataplane version.

### 4. Preserve evidence

Use:

```bash
kubectl get gateway,httproute,ingress -A -o wide
kubectl describe gateway <name> -n <namespace>
kubectl describe httproute <name> -n <namespace>
kubectl get service,endpointslice -A
kubectl get networkpolicy -A
kubectl get events -A --sort-by=.lastTimestamp
ss -s
ip route
ip addr
```

Implementation-specific tools may include eBPF flow observability, proxy config dumps, load-balancer target health, packet capture, conntrack inspection, and cloud route evidence.

### 5. Stabilize safely

Preferred order:

1. stop the rollout or configuration change that aligns with the failure;
2. route away from one failed gateway, node, zone, endpoint, or IP family;
3. restore endpoint readiness or correct Service/route ports;
4. repair CNI address, route, or policy state;
5. reduce retry and connection pressure;
6. restore known-good DNS or gateway configuration;
7. add compatible capacity at the constrained layer;
8. restart a bounded agent or dataplane cohort only with evidence;
9. prove recovery externally and internally.

## SLOs and signals

Track:

- DNS success, latency, and cache behavior;
- external and internal connection success;
- TLS handshake success and latency;
- gateway route acceptance and reconciliation time;
- load-balancer healthy target count;
- Service-to-endpoint propagation latency;
- endpoint count and readiness;
- CNI address allocation success;
- policy programming latency and drops;
- conntrack and NAT saturation;
- retransmissions and resets;
- per-zone and per-IP-family user SLIs.

## Validation program

Test:

- deployment label and readiness changes;
- Service targetPort mistakes;
- one-zone endpoint loss;
- `externalTrafficPolicy: Local` behavior;
- CNI address exhaustion;
- default-deny policy and DNS egress;
- CoreDNS or node-local cache loss;
- UDP/TCP DNS fallback;
- Gateway route attachment and certificate rotation;
- IPv4/IPv6 asymmetry;
- MTU-sensitive payloads;
- connection and retry storms.

## Weak answers to avoid

- “Restart CoreDNS.”
- “The Service exists, so networking is fine.”
- “Pods are Ready, so the load balancer is healthy.”
- “Open all NetworkPolicies.”
- “Flush conntrack everywhere.”
- “Increase DNS replicas” without identifying query or dataplane pressure.
- “Use host networking.”

## Adversarial follow-ups

### Why can one zone fail with healthy pods?

The external load balancer, local-traffic policy, topology hints, CNI path, route, gateway, or node-local endpoint distribution may be zone-specific.

### Why does a headless Service behave differently?

Clients receive endpoint addresses and own DNS caching and connection selection. There is no Service VIP to rebalance each new connection through the cluster dataplane.

### Why do small requests work but large responses fail?

MTU, fragmentation, path-MTU discovery, proxy buffering, or firewall behavior may affect larger packets or TLS records.

### How do you prove a NetworkPolicy issue?

Show the selected pods, intended policy semantics, effective dataplane enforcement or flow evidence, and a paired request that changes only the relevant identity or port.

### What proves recovery?

External client journeys succeed, DNS and TLS normalize, gateway and route status is healthy, Service-to-endpoint state is fresh, connection and drop metrics recover, and the previously affected cohort works without a broad bypass.

## Principal-level review checklist

- every request path has known ownership and evidence points;
- Service and Gateway ports are validated in CI;
- EndpointSlice propagation and readiness semantics are understood;
- dataplane implementation is explicit;
- CNI address and route capacity are monitored;
- DNS has bounded caching and overload behavior;
- NetworkPolicy is tested, not merely declared;
- local traffic and topology policies include failure-mode analysis;
- IPv4/IPv6 and MTU are in conformance tests;
- external recovery is proven from the actual client journey.
