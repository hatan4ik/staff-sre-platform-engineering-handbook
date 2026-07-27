# Policy as Code, Admission Control, and Governance

## Why this exists

A platform must turn security, reliability, cost, and ownership expectations into controls that are consistent, testable, explainable, and safe to change. Manual reviews do not scale, but careless admission policy can block every deployment or create a cluster-wide outage.

Policy as code is therefore both a governance capability and a production control plane.

## What the interviewer is testing

A Staff or Principal candidate should be able to:

- distinguish schema validation, admission policy, runtime detection, and cloud-side enforcement;
- choose between native Kubernetes policy, OPA Gatekeeper, Kyverno, and provider-native controls;
- explain validation, mutation, generation, image verification, and audit behavior;
- design fail-open versus fail-closed behavior from risk rather than convenience;
- test and roll out policy without breaking critical workloads;
- manage exceptions, ownership, versioning, and evidence;
- prevent policy engines from becoming a shared blast-radius amplifier.

## The policy control stack

```text
Developer workstation and CI
  -> schema and static checks
  -> policy unit tests
  -> admission dry-run or audit
  -> admission enforcement
  -> cloud and runtime enforcement
  -> continuous compliance and evidence
```

No single layer is sufficient.

- **Schema** checks shape and type.
- **Admission** evaluates an API request before persistence.
- **Cloud controls** prevent bypass through another interface.
- **Runtime detection** catches behavior that static declarations cannot prove.
- **Continuous audit** finds pre-existing drift and resources created before a policy existed.

## Policy categories

### Safety invariants

These should usually fail closed after a proven rollout:

- prohibit privileged containers outside explicit system namespaces;
- prevent public exposure of restricted services;
- require approved workload identity patterns;
- reject mutable image tags for protected environments;
- require encryption and deletion protection for critical data;
- prevent unauthorized changes to platform control-plane resources.

### Quality defaults

These may begin as warnings, mutations, or generated resources:

- add standard labels and annotations;
- inject default resource requests;
- attach telemetry configuration;
- generate baseline NetworkPolicies;
- require runbook or owner metadata.

Mutation must remain predictable. Hidden mutation that materially changes application behavior creates debugging and ownership problems.

### Detective controls

These produce reports, events, metrics, or findings without blocking:

- deprecated API usage;
- missing recommended topology spread;
- excessive resource limits;
- unsupported base images;
- stale exceptions;
- old policy versions.

## Native Kubernetes controls

### Pod Security Admission

Pod Security Admission enforces the Kubernetes Pod Security Standards at namespace level using `privileged`, `baseline`, or `restricted` profiles. Namespaces can independently configure `enforce`, `audit`, and `warn` modes and can pin the policy version.

Use it as the baseline pod hardening layer. It is intentionally not a general-purpose policy language.

Example namespace posture:

```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.36
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

Pinning versions makes upgrades explicit. Using `latest` can silently change enforcement when the cluster version changes.

### ValidatingAdmissionPolicy

ValidatingAdmissionPolicy is an in-process Kubernetes validation mechanism based on CEL. It separates policy logic, optional parameter resources, and bindings. Bindings can use `Deny`, `Warn`, or `Audit` actions.

It is a strong default when:

- validation is expressible against admission request data;
- no external service lookup is required;
- low latency and reduced webhook dependency are valuable;
- the organization can manage CEL policy safely.

Example:

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata:
  name: require-owner.platform.example.com
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: ["apps"]
        apiVersions: ["v1"]
        operations: ["CREATE", "UPDATE"]
        resources: ["deployments"]
  validations:
    - expression: >-
        has(object.metadata.labels) &&
        'platform.example.com/owner' in object.metadata.labels
      message: Deployment must declare platform.example.com/owner
      reason: Invalid
```

The policy has no effect until a matching `ValidatingAdmissionPolicyBinding` exists.

### MutatingAdmissionPolicy

Current Kubernetes releases also provide in-process CEL-based mutating admission policy. Use mutation only when the result is deterministic, visible to users, and safe under repeated evaluation. Prefer validation when preventing a change is sufficient.

## OPA Gatekeeper

Gatekeeper uses Kubernetes custom resources and OPA to enforce validation and mutation policy. Its audit capability evaluates existing resources and identifies current violations.

Core model:

```text
ConstraintTemplate
  -> defines policy logic and parameter schema
Constraint
  -> instantiates the policy for selected resources
Audit
  -> reports existing violations
Admission webhook
  -> evaluates new requests
```

Gatekeeper is appropriate when:

- the organization already uses Rego and OPA across domains;
- reusable parameterized policy templates are valuable;
- audit of existing cluster state is required;
- advanced matching or external-data integration is justified.

Costs include Rego expertise, webhook operation, template lifecycle, inventory synchronization, and policy latency.

External data must be treated as a dependency on the admission path. Bound timeouts, cache deliberately, secure provider communication, and decide whether unavailable data blocks or allows the request.

## Kyverno

Kyverno provides Kubernetes-native policy resources and can validate, mutate, generate, delete, and verify images. It also produces policy reports and supports background scanning for existing resources.

Kyverno is appropriate when:

- policy authors prefer Kubernetes resource patterns over Rego;
- mutation, generation, image verification, and policy reports are central requirements;
- the platform wants CLI-based policy tests in CI;
- policy ownership aligns with Kubernetes operations teams.

Current-version note: Kyverno's newer policy APIs separate validating, mutating, generating, deleting, and image-validating policy types. Older `ClusterPolicy`-based examples remain common, so always verify examples against the deployed Kyverno release and its deprecation schedule.

## Choosing the mechanism

| Need | Strong starting point |
|---|---|
| Standard pod hardening | Pod Security Admission |
| Simple in-process request validation | ValidatingAdmissionPolicy with CEL |
| Simple in-process deterministic mutation | MutatingAdmissionPolicy where supported |
| Rego-based reusable policy and audit | Gatekeeper |
| Kubernetes-native validate/mutate/generate/image policy | Kyverno |
| Organization-wide cloud resource guardrails | cloud organization policy, SCP, Azure Policy, or equivalent |
| Runtime process or network behavior | runtime security and network enforcement |

Do not deploy multiple engines to enforce the same invariant unless ownership and precedence are explicit.

## Policy ownership model

Every policy needs metadata such as:

```yaml
owner: platform-security
riskClass: critical
mode: audit
introduced: 2026-07-27
reviewAfter: 2026-10-27
exceptionProcess: SEC-EXCEPTION-01
runbook: https://internal.example/runbooks/policy-owner-label
```

Document:

- purpose and threat or reliability failure addressed;
- resources and environments in scope;
- enforcement mode;
- expected user remediation;
- policy owner and on-call route;
- test suite;
- exception process;
- rollout and rollback plan;
- evidence and success criteria.

## Policy development lifecycle

```text
Proposal
  -> threat or failure model
  -> representative fixtures
  -> unit and integration tests
  -> offline CI evaluation
  -> cluster audit
  -> warning mode
  -> narrow enforcement canary
  -> broader enforcement
  -> continuous evidence
  -> periodic review or retirement
```

### Test corpus

Include:

- valid golden-path resources;
- known invalid resources;
- update and delete operations;
- controllers and generated resources;
- system namespaces;
- emergency and recovery workloads;
- old API versions;
- missing optional fields;
- very large objects;
- policy-engine dependency failures.

A policy that passes five hand-written examples is not production-ready.

## Enforcement rollout

Use staged rollout:

1. Run policy in CI against repositories.
2. Audit existing resources and quantify violations.
3. Warn users with actionable messages.
4. Fix platform templates and shared controllers first.
5. Enforce for a small namespace or workload cohort.
6. Monitor latency, rejection rate, and support load.
7. Expand by environment and risk class.
8. Remove temporary exceptions.

Never begin with cluster-wide deny for a policy whose real impact is unknown.

## Fail-open versus fail-closed

The decision depends on the consequence of accepting an unverified request versus the consequence of blocking the control plane.

Fail closed when:

- the invariant prevents immediate high-impact compromise or data exposure;
- the policy has no unreliable external dependency;
- emergency paths are tested;
- policy availability is engineered to match the protected operation.

Fail open or degrade to audit when:

- the control is advisory;
- the policy depends on a fragile external service;
- blocking would prevent recovery during a larger incident;
- false positives are not yet characterized.

Do not label every security control "fail closed" without analyzing platform-wide availability risk.

## Exceptions

An exception is a governed resource, not an informal annotation.

Require:

- named owner;
- policy and resource scope;
- business and technical reason;
- compensating controls;
- approval authority;
- creation and expiry time;
- review history;
- telemetry and alerting;
- migration plan.

Avoid permanent wildcard exemptions for users, namespaces, controllers, or image registries.

## Admission bypass analysis

Admission policy protects only requests that traverse the relevant API path. Consider:

- cloud resources created outside Kubernetes;
- existing resources before enforcement;
- privileged users who can change policy configuration;
- system components or exempt resources;
- direct node or runtime access;
- mutation order and webhook ordering;
- controllers that continuously recreate denied objects;
- API subresources not covered by the rule.

Backstop high-risk invariants at cloud, identity, network, registry, and runtime boundaries.

## Failure modes

- malformed policy rejects all matching objects;
- a webhook timeout adds latency or blocks cluster operations;
- failure policy silently allows requests during outage;
- mutation conflicts with another controller;
- an exception selector matches more resources than intended;
- policy upgrade changes semantics;
- background reports are mistaken for historical audit records;
- external registry or directory lookup fails;
- policy messages do not tell users how to remediate;
- platform controllers violate the policy they install.

## Incident response

If policy blocks production changes:

1. Declare impact and freeze unrelated policy changes.
2. Identify the exact policy, binding, version, and request operation.
3. Preserve admission logs, audit events, metrics, and rejected manifests.
4. Bound impact by resource, namespace, user, and environment.
5. Prefer a narrow binding rollback or scoped exception over disabling the engine globally.
6. Validate the emergency change against the original risk.
7. Confirm API latency and deployment recovery.
8. Repair fixtures, rollout controls, and ownership before re-enforcement.

## Observability and SLOs

Measure:

- admission request latency by policy and engine;
- error and timeout rate;
- deny, warn, audit, and mutation count;
- violations by policy, namespace, owner, and age;
- exception count and expiry status;
- webhook availability;
- policy synchronization freshness;
- false-positive and manual-intervention rate;
- percentage of policies with tests and owners;
- time from violation to remediation.

Keep durable audit events outside ephemeral policy reports when history matters.

## 90-second interview answer

> I treat policy as code as a production control plane. I layer schema checks, CI evaluation, admission, cloud-side enforcement, and continuous audit rather than expecting one webhook to solve governance. I use Pod Security Admission for standard pod hardening and native CEL admission policy for simple in-process validation. I choose Gatekeeper when Rego reuse and audit are important, and Kyverno when Kubernetes-native validation, mutation, generation, image verification, and policy reporting fit the operating model. Every policy has an owner, risk class, tests, rollout mode, exception process, and rollback. I audit first, warn second, enforce by cohort, and measure latency, denials, false positives, and stale exceptions. Fail-open versus fail-closed is based on the risk of accepting the request versus blocking the platform. For incidents, I roll back the narrow binding or add a scoped expiring exception instead of disabling governance globally.

## Adversarial follow-ups

### "Why not standardize on one engine?"

One engine reduces complexity, but native controls can be safer and simpler for some invariants. I standardize policy ownership and lifecycle first, then use the smallest mechanism that meets the requirement.

### "Should policies mutate missing resource requests?"

Only if the default is safe, visible, deterministic, and owned. Otherwise validate and require the workload owner to choose intentionally.

### "How do you test a fail-closed image-signature policy?"

Use trusted and untrusted fixtures, unavailable registry and transparency dependencies, expired or wrong identities, digest changes, rollback images, emergency workloads, and a canary namespace before production-wide enforcement.

## Dangerous answers

- "All policies should fail closed."
- "Gatekeeper and Kyverno are interchangeable."
- "Audit mode means the policy is safe to enforce."
- "Mutation reduces developer cognitive load, so users do not need to know it happened."
- "Namespace exemptions are harmless."
- "A policy report is our immutable compliance history."

## Whiteboard summary

```text
Invariant
  -> choose enforcement boundary
  -> test corpus
  -> CI
  -> audit
  -> warn
  -> canary deny
  -> broad enforcement
  -> evidence and exception expiry

Policy engine availability is part of platform availability.
```

## Primary references

- Kubernetes Pod Security Standards and Pod Security Admission documentation.
- Kubernetes ValidatingAdmissionPolicy and MutatingAdmissionPolicy documentation for the deployed release.
- OPA Gatekeeper official documentation and policy library.
- Kyverno official policy type, CLI, image verification, background scan, and policy report documentation.
- Cloud-provider organization-policy documentation for controls outside Kubernetes.
