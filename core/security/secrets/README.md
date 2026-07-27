# Secrets Management and Secure Delivery

This module owns reusable principles for secret authority, workload authentication, retrieval, synchronization, rotation, revocation, audit, and incident response across Kubernetes, CI/CD, cloud platforms, and internal developer platforms.

## Canonical chapter

1. [Secret authority, delivery, rotation, and Kubernetes integration](secret-delivery-rotation-kubernetes.md)

## Core model

```text
Workload identity
  -> authorization to a secret path or dynamic credential role
  -> secret authority
  -> bounded delivery mechanism
  -> application reload or lease renewal
  -> audit, rotation, revocation, and incident response
```

## Ownership rule

Reusable secret-lifecycle and delivery patterns belong here. Cloud and company tracks should add only provider-specific identity, API, policy, rotation, quota, and failure behavior.
