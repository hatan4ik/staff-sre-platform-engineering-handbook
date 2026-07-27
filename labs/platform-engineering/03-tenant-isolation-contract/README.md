# Lab: Validate a Tenant Isolation Contract

This lab checks whether a tenant namespace package and workload satisfy a small set of platform isolation controls.

## Learning objectives

- treat namespace provisioning as a complete product capability;
- connect RBAC, Pod Security, NetworkPolicy, quota, identity, and workload settings;
- distinguish a declared control from a tested boundary;
- reason about soft versus hard multi-tenancy.

## Files

- `tenant-package.json` — namespace-level platform controls.
- `workload.json` — tenant workload request.
- `validate_tenant.py` — standard-library conformance validator.

## Run

```bash
python3 validate_tenant.py tenant-package.json workload.json
```

## Exercises

1. Remove default-deny egress.
2. Change the workload service account so it no longer matches the cloud-role trust boundary.
3. Enable host networking or privileged execution.
4. Remove memory requests and discuss noisy-neighbor behavior.
5. Change the tenant trust level to `untrusted-external` and decide whether a namespace-only design should be accepted.
6. Add observability access that is based only on labels and explain why backend authorization is still required.

## Staff-level discussion

The lab validates declarations, not the real data plane. A production platform must also run active conformance tests proving that one tenant cannot read another namespace, assume another cloud role, reach protected services, access another tenant's telemetry, or bypass node and admission controls.
