# Canonical Security Curriculum

The `core/security/` tree contains reusable identity, authorization, secret-lifecycle, artifact-trust, and security-control-plane material shared by all company and cloud tracks.

## Modules

1. [Workload identity, federation, and access boundaries](identity/README.md)
2. [Secrets management and secure delivery](secrets/README.md)
3. [Software supply-chain security](software-supply-chain/README.md)

## Security model

```text
Human and workload identity
  -> authorization and policy
  -> secret or credential issuance and delivery
  -> trusted build and artifact evidence
  -> deployment verification
  -> runtime isolation and detection
  -> audit, rotation, revocation, and incident response
```

## Ownership rule

Canonical security principles remain here. Company tracks add only provider-specific commands, service behavior, limits, trust-policy syntax, and interview scenario context.
