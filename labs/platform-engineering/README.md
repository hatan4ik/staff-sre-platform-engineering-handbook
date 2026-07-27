# Platform Engineering Labs

Executable labs for Staff and Principal platform-engineering interviews. All current labs use Python's standard library and model control-plane decisions without requiring cloud credentials or a Kubernetes cluster.

## Run the validation set

From the repository root:

```bash
python3 labs/platform-engineering/run_all.py
```

The staged-policy scenario intentionally expects one production denial; the runner treats that expected exit code as a passing test.

## Labs

1. [Golden-path contract](01-golden-path-contract/README.md) — validate developer intent before provisioning.
2. [Policy rollout](02-policy-rollout/README.md) — stage audit, warn, enforce, and expiring exceptions.
3. [Tenant isolation contract](03-tenant-isolation-contract/README.md) — validate namespace and workload boundary declarations.
4. [Artifact trust verification](04-artifact-trust-verification/README.md) — verify digest binding, signer authorization, provenance, SBOM, vulnerability evidence, and release approval.
5. [Fleet rollout planner](05-fleet-rollout-planner/README.md) — classify fleet eligibility and construct bounded, failure-domain-aware rollout batches.
6. [Secret delivery contract](06-secret-delivery-contract/README.md) — validate authority, workload identity, path scope, delivery cache, rotation, reload, outage, and audit behavior.

## Practice loop

```text
read the canonical chapter
  -> run the valid fixture
  -> create one failing fixture
  -> explain the failure mode
  -> propose immediate mitigation
  -> design the permanent control
  -> state the SLI that proves the control works
```

## Important limitation

These labs validate simplified JSON models. Production systems must use the official policy, identity, cryptographic, Kubernetes, cloud, registry, secret-provider, and fleet-lifecycle implementations and must test real control-plane and data-plane behavior.
