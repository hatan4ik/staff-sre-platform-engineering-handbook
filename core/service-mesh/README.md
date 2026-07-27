# Service Mesh, Envoy, Istio, and xDS

This module contains the canonical, company-neutral service-mesh material shared by Netflix-, Tesla-, AWS-, and future interview tracks.

## Canonical chapters

1. [Fine-grained service discovery with Envoy, Istio, and xDS](fine-grained-service-discovery.md) — registry, control-plane/data-plane separation, xDS resources, dependency scope, fan-out, sidecar and ambient trade-offs, last-known-good behavior, and multi-cluster design.
2. [Envoy request-path, timeout, reset, and 504 debugging](envoy-request-path-debugging.md) — error ownership, latency decomposition, response flags, effective proxy configuration, endpoint and connection state, retries, circuit breaking, outlier detection, protocol failures, mitigation, and SLOs.
3. [mTLS, SDS, DNS capture, and multi-cluster reliability](mtls-sds-dns-multicluster.md) — workload identity, certificate delivery and rotation, trust domains, authorization, DNS capture, service export/import, east-west gateways, locality, failover, and control-plane outage behavior.

## Executable and future labs

Current related labs live under Kubernetes, reliability, and distributed-systems modules. The next direct mesh exercises should cover:

- xDS ACK/NACK and last-known-good convergence;
- route timeout and retry amplification;
- certificate and trust-bundle rotation;
- DNS capture and stale-cache behavior;
- east-west gateway loss and bounded failover.

## Ownership rule

Reusable Envoy, Istio, xDS, request-path, service-discovery, mesh-identity, DNS, gateway, and mesh-security fundamentals belong here. Company tracks should add only domain-specific assumptions, failure modes, answer adapters, and mock interviews.
