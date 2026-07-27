# Lab 4 — Workload Identity Claims, Trust Policies, and Credential Fallback

## Interview scenario

A Kubernetes workload is expected to use short-lived federation, yet cloud audit logs show inconsistent principals. Some requests use the intended workload role, some use an old access key, and others unexpectedly fall back to the node role.

The weak response is to inspect only whether a ServiceAccount annotation or identity association exists.

The Staff/Principal task is to prove:

1. which credential source the application actually selected;
2. whether issuer, audience, subject, environment, signature, and lifetime were validated;
3. whether a broader static or node credential can shadow the intended workload identity;
4. whether negative identities are rejected;
5. whether removal of the old credential path is complete.

## Safety invariant

> A workload-identity migration is complete only when the intended short-lived identity succeeds, unauthorized identities fail, static credentials are absent, and node-role fallback is impossible or explicitly bounded.

This lab is a safe standard-library simulation. It does not contact AWS, Azure, Google Cloud, Kubernetes, or a real identity provider.

## What the program models

```text
workload assertion
      |
      +--> signature validation
      +--> issuer validation
      +--> audience validation
      +--> exact subject validation
      +--> environment validation
      +--> issue/expiration validation
      |
      v
trust decision: ALLOW or DENY

credential provider order
      |
      +--> static environment key
      +--> local credentials file
      +--> workload identity
      +--> node-role fallback
      +--> no credentials
```

The HMAC-signed compact token is intentionally JWT-like but is not a production identity implementation. Its purpose is to make claim-validation and provider-chain mistakes observable without requiring a cloud account.

## Prerequisites

- Python 3.11 or newer.
- No third-party packages.

## Run the demonstration

```bash
python3 identity_lab.py --demo
```

Expected decision pattern:

| Scenario | Expected result |
|---|---|
| exact issuer, audience, subject, environment, and valid lifetime | `ALLOW` |
| wrong audience | `DENY` |
| wrong ServiceAccount subject | `DENY` |
| wrong environment | `DENY` |
| expired assertion | `DENY` |
| clean provider chain | `workload-identity` |
| static key still present | `static-environment-key` |
| federation invalid and node metadata reachable | `node-role-fallback` |

The exact JSON formatting is less important than the invariant: the workload identity must not silently lose precedence to a broader credential.

## Run the tests

```bash
python3 -m unittest -v test_identity_lab.py
```

The test suite proves:

- the exact trusted workload succeeds;
- the wrong audience fails;
- the wrong subject fails;
- another environment fails;
- an expired token fails;
- payload tampering fails signature validation;
- a static key can shadow federation;
- node-role fallback remains visible as an unsafe credential source.

## Production investigation mapping

### Step 1 — Identify the intended workload identity

Record:

- cluster and environment;
- namespace and ServiceAccount;
- pod UID and image digest;
- expected cloud role or managed identity;
- issuer and audience;
- expected session duration;
- resource and action the workload needs.

### Step 2 — Identify the credential actually used

Inspect:

- environment variables;
- local credential files;
- projected token mounts;
- SDK version and provider order;
- Pod Identity, metadata, or federation-agent path;
- cloud audit events and caller identity.

Examples in a controlled environment:

```bash
aws sts get-caller-identity
kubectl get pod -n <namespace> <pod> -o yaml
kubectl get sa -n <namespace> <service-account> -o yaml
```

A successful API call does not prove the intended principal was used. Verify the principal in audit records.

### Step 3 — Validate claims

Check:

- exact issuer;
- intended audience;
- exact subject;
- cluster or environment boundary;
- expiration and not-before time;
- token signature and current signing key;
- any session tags or workload attributes used for authorization.

Do not paste production tokens into public decoding websites.

### Step 4 — Separate authentication from authorization

```text
no token returned        -> assertion, agent, issuer, SDK, or network path
valid token, access denied -> target authorization or resource policy
valid token, request timeout -> DNS, network, firewall, endpoint, or service health
unexpected principal     -> provider-chain precedence or fallback
```

### Step 5 — Run negative tests

Prove that:

- another namespace fails;
- the default ServiceAccount fails;
- another environment fails;
- the wrong audience fails;
- an expired token fails;
- a pod cannot retrieve node credentials;
- the workload cannot perform actions outside its role.

### Step 6 — Remove the old path

Deleting an access key from one manifest is not enough. Search:

- secret stores;
- CI variables;
- image layers;
- Helm values;
- environment injection;
- home-directory credential files;
- node metadata access;
- application fallback configuration.

Then prove from audit logs that the old principal is no longer used.

## Failure modes this lab teaches

### Audience is ignored

A token minted for one relying party may be replayed to another system that should not accept it.

### Subject matching is broad

Trust such as `system:serviceaccount:*:*` converts one compromised pod into a cluster-wide or environment-wide trust bridge.

### Environments share the same apparent subject

`system:serviceaccount:payments:api` is not globally unique across clusters. The trust design must include issuer, project, account, pool, trust domain, or another environment boundary.

### Static credentials remain earlier in the provider chain

The new federation path can be healthy while never being used.

### Node role remains reachable

When workload federation fails, the SDK may obtain broader node credentials instead of failing closed.

### Long token lifetime is used as an availability fix

This reduces refresh pressure but increases the stolen-credential window. Identity-plane availability requires regional design, bounded caching, and tested degraded behavior rather than universal long-lived tokens.

## Production controls

- Audience-bound projected ServiceAccount tokens.
- Exact trust-policy subject conditions.
- Separate roles or identities by application security boundary.
- No static cloud keys in Kubernetes Secrets or images.
- IMDS and node-metadata protection.
- Controlled `iam:PassRole` or equivalent delegation.
- Cloud audit logs containing workload/session attributes.
- Admission and CI checks against wildcard trust.
- Rotation and issuer-key overlap tests.
- Alerts on unexpected principals and node-role use by pods.

## Interview answer drill

> I would not stop at checking that a Pod Identity association or IRSA annotation exists. I would identify the credential actually selected by the SDK, inspect issuer, audience, subject, environment, lifetime, and target authorization, and correlate the request with the cloud audit principal. I would then run negative tests for another namespace, ServiceAccount, environment, and audience, and prove the pod cannot retrieve node credentials. The migration is complete only when static credentials are gone and the old principal disappears from audit logs.

## Related material

- [`core/security/identity/workload-identity-federation.md`](../../../core/security/identity/workload-identity-federation.md)
- [`tracks/aws/round-1/04-securing-amazon-eks.md`](../../../tracks/aws/round-1/04-securing-amazon-eks.md)
- [`curriculum-map.md`](../../../curriculum-map.md)
