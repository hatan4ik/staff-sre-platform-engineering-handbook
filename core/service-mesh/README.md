# Service Mesh, Envoy, Istio, and xDS

This module contains the canonical, company-neutral service-mesh material shared by Netflix-, Tesla-, AWS-, and future interview tracks.

## Current chapter

1. [Fine-grained service discovery with Envoy, Istio, and xDS](fine-grained-service-discovery.md)

The chapter covers:

- Kubernetes Service and EndpointSlice foundations.
- Registry, control-plane, and data-plane separation.
- LDS, RDS, CDS, EDS, SDS, ADS, ACK, and NACK behavior.
- Configuration-graph growth and endpoint-churn fan-out.
- Control-plane input scope, producer exports, and consumer imports.
- Dependency declarations and service-catalog integration.
- Sidecar and Ambient dataplane trade-offs.
- Multi-cluster, multi-region, locality, trust, and failure-domain design.
- Last-known-good behavior during control-plane outages.
- Capacity modeling, migration, observability, and adversarial interview drills.

## Planned chapters

- Envoy request-path and 504 debugging.
- mTLS, SDS, trust-bundle, and identity failures.
- DNS capture and service-mesh name-resolution incidents.
- Multi-cluster east-west gateways and failover.
- Retry budgets, circuit breakers, outlier detection, and overload control.

## Ownership rule

Reusable Envoy, Istio, xDS, service-discovery, and mesh-security fundamentals belong here. Company tracks should add only domain-specific assumptions, failure modes, answer adapters, and mock interviews.
