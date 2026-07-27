# Service Mesh Reliability Contract Lab

This standard-library Python exercise validates service-mesh control and recovery decisions.

## Covered invariants

- Invalid xDS state is rejected while last-known-good endpoints remain active.
- Valid xDS state is accepted.
- Certificate root rotation has an overlap window.
- Expired or no-longer-trusted certificates are rejected.
- DNS stale fallback has a strict time boundary.
- Remote traffic movement requires gateway health, identity health, fresh data, enough capacity, and valid writer ownership.
- Retries remain inside a fixed budget.

## Run

```bash
cd labs/service-mesh/01-xds-mtls-dns-failover
python3 mesh_contract_lab.py
python3 mesh_contract_lab.py --json
python3 -m unittest -v test_mesh_contract_lab.py
```

## Interview drill

Describe why:

1. rejected control-plane configuration must not erase working proxy state;
2. certificate rotation requires temporary trust overlap;
3. stale DNS data needs an expiration limit;
4. gateway availability alone does not make remote writes safe;
5. capacity and identity checks are separate from data-authority checks;
6. retries need a platform budget.

## Production mapping

Connect the same checks to Envoy configuration status, SDS delivery, certificate expiry, DNS cache metrics, east-west gateway saturation, regional routing controls, and application writer-fencing evidence.

This exercise validates decision logic; it does not simulate a full Envoy or Istio deployment.
