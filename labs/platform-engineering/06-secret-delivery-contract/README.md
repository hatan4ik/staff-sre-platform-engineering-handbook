# Lab: Validate a Secret Delivery and Rotation Contract

This lab validates a simplified platform contract for synchronizing a database credential from an external authority into a tenant namespace.

## Learning objectives

- distinguish the secret authority from the Kubernetes delivery cache;
- bind provider access to workload identity rather than static credentials;
- constrain tenant paths and namespace scope;
- make rotation, application reload, retention, and outage behavior explicit;
- understand that successful synchronization does not prove application adoption.

## Files

- `secret-contract.json` — authority, identity, synchronization, application, and recovery contract.
- `validate_secret_contract.py` — standard-library validator.

## Run

```bash
python3 validate_secret_contract.py secret-contract.json
```

Expected result:

```text
VALID: secret delivery contract is bounded and rotation-aware
```

## Exercises

1. Change the store scope to `Cluster` and remove namespace selectors.
2. Enable static provider credentials.
3. Change the remote path to another team's prefix.
4. Set the refresh interval longer than the rotation overlap.
5. Change consumption from mounted file to environment variable while keeping live reload.
6. Remove application version confirmation.
7. Mark the Kubernetes Secret as the authority.
8. Allow new pods to start indefinitely from stale cache during provider outage.

## Staff-level discussion

A production test must rotate the real credential, prove the application uses the new version, revoke the old version, test provider outage, restore the cluster, and verify that no stale or compromised value becomes authoritative.
