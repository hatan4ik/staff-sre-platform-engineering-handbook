# Executable Service-Mesh Labs

These exercises validate reusable service-mesh control-plane, identity, DNS, routing, and failover invariants.

## Current lab

1. [xDS, mTLS, DNS, and failover contract](01-xds-mtls-dns-failover/README.md) — ACK/NACK behavior, last-known-good state, certificate trust overlap, bounded stale DNS, remote capacity, writer ownership, and retry budgets.

## Run

```bash
cd labs/service-mesh/01-xds-mtls-dns-failover
python3 mesh_contract_lab.py
python3 -m unittest -v test_mesh_contract_lab.py
```

## Next integration layer

The deterministic contract should be followed by disposable-cluster or container integration using real Envoy or Istio components for:

- xDS rejection and convergence;
- SDS certificate rotation;
- DNS capture and cache expiry;
- east-west gateway loss;
- bounded cross-cluster failover.

## Ownership rule

A lab must prove safety and recovery behavior, not only show proxy commands. Every exercise should include a rejected or dangerous case, last-known-good behavior, explicit limits, and end-to-end recovery evidence.
