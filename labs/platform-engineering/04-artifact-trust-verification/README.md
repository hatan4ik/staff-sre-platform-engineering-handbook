# Lab: Verify Artifact Identity and Provenance Policy

This lab models a deployment gate that verifies more than the presence of a signature.

## Learning objectives

- bind deployment intent to an immutable artifact digest;
- distinguish cryptographic identity from authorization;
- compare provenance against expected source and builder policy;
- require SBOM and vulnerability evidence with bounded age;
- understand why attestations without semantic verification provide weak protection.

## Files

- `deployment.json` — the exact artifact requested for production.
- `evidence.json` — simplified signature, provenance, SBOM, scan, and release evidence.
- `trust-policy.json` — approved issuer, identity, source, builder, and predicate rules.
- `verify_artifact.py` — standard-library verifier.

## Run

```bash
python3 verify_artifact.py \
  deployment.json evidence.json trust-policy.json \
  --now 2026-07-27T12:00:00Z
```

Expected result:

```text
TRUSTED: production deployment evidence satisfies policy
```

## Failure exercises

1. Change the deployment digest without changing the evidence subject.
2. Broaden the trusted identity expression to accept any repository from the issuer.
3. Change the source revision or builder identity.
4. Remove the SBOM digest.
5. Move `scannedAt` outside the allowed age.
6. Add one critical vulnerability and decide whether an emergency exception or rejection is appropriate.
7. Change the artifact from a digest to a mutable tag.

## Staff-level discussion

A real verifier must perform cryptographic signature and certificate-chain validation using the deployed Sigstore/Cosign libraries and trusted roots. This lab begins after that primitive and focuses on the authorization and semantic checks teams often omit.
