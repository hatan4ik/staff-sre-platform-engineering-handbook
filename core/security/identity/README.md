# Workload Identity, Federation, and Access Boundaries

This module owns reusable workload-identity principles for Kubernetes, cloud platforms, service meshes, CI systems, and multi-cloud environments.

## Canonical chapter

1. [Workload identity, federation, SPIFFE, and cloud-native authorization](workload-identity-federation.md)

The chapter covers:

- The difference between human, workload, node, and service identity.
- Kubernetes projected ServiceAccount tokens and audience restrictions.
- EKS Pod Identity and IRSA.
- Microsoft Entra Workload ID for AKS.
- Workload Identity Federation for GKE.
- Cross-cloud token exchange without static access keys.
- SPIFFE IDs, SVIDs, the Workload API, and SPIRE attestation.
- Identity-versus-authorization boundaries.
- Credential-provider-chain risks, node-role fallback, and metadata protection.
- Token lifetime, rotation, regional survivability, and identity-provider failure.
- Evidence, rollout, incident response, and adversarial interview questions.

## Ownership rule

Reusable identity, token, federation, attestation, authorization-boundary, and credential-lifecycle material belongs here. Company and cloud tracks should add only platform-specific commands, service limits, trust-policy syntax, and scenario context.
