# Software Supply-Chain Security

This module covers how a platform establishes trust from source and build intent through artifact publication, deployment admission, runtime evidence, and incident response.

## Canonical chapter

1. [Artifact trust, SLSA provenance, SBOMs, Sigstore, and deployment verification](artifact-trust-slsa-sigstore.md)

## Core model

```text
Source revision and review
  -> isolated build platform
  -> immutable artifact digest
  -> signed provenance and attestations
  -> registry and transparency evidence
  -> deployment policy verification
  -> runtime inventory and response
```

## Ownership rule

Reusable artifact-integrity, provenance, signing, attestation, verification, and deployment-policy material belongs here. Cloud and company tracks add only provider-specific registry, identity, KMS, CI, and admission implementation details.
