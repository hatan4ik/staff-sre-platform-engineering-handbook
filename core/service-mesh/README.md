# Service Mesh, Envoy, Istio, and xDS

This module contains the canonical, company-neutral service-mesh material shared by Netflix-, Tesla-, AWS-, and future interview tracks.

## Canonical chapters

1. [Fine-grained service discovery with Envoy, Istio, and xDS](fine-grained-service-discovery.md) — registry, control-plane/data-plane separation, xDS resources, dependency scope, fan-out, sidecar and ambient trade-offs, last-known-good behavior, and multi-cluster design.
2. [Envoy request-path, timeout, reset, and 504 debugging](envoy-request-path-debugging.md) — error ownership, latency decomposition, response flags, effective proxy configuration, endpoint and connection state, retries, circuit breaking, outlier detection, protocol failures, mitigation, and SLOs.
3. [mTLS, SDS, DNS capture, and multi-cluster reliability](mtls-sds-dns-multicluster.md) — workload identity, certificate delivery and rotation, trust domains, authorization, DNS capture, service export/import, east-west gateways, locality, failover, and control-plane outage behavior.

## Executable lab

- [`../../labs/service-mesh/01-xds-mtls-dns-failover/`](../../labs/service-mesh/01-xds-mtls-dns-failover/) — xDS ACK/NACK and last-known-good behavior, certificate-root overlap and retirement, bounded stale DNS, gateway/identity/data/capacity failover gates, writer ownership, and retry budgets.

## Remaining integration exercises

- real Envoy xDS rejection and convergence;
- real SDS certificate and trust-bundle rotation;
- DNS capture with cache expiry and resolver outage;
- east-west gateway loss with bounded remote failover;
- route timeout, connection-pool, and retry-amplification experiments.

## Ownership rule

Reusable Envoy, Istio, xDS, request-path, service-discovery, mesh-identity, DNS, gateway, and mesh-security fundamentals belong here. Company tracks should add only domain-specific assumptions, failure modes, answer adapters, and mock interviews.
