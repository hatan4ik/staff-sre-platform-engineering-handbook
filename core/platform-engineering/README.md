# Platform Engineering — Canonical Core Curriculum

Platform engineering builds and operates an internal product that makes safe software delivery easier for application teams. The platform is not merely a Kubernetes cluster, developer portal, Terraform repository, or collection of CI templates. It is a coherent set of capabilities, interfaces, guardrails, and support models designed around developer outcomes.

## Chapters

1. [Platform as a product, golden paths, and paved roads](01-platform-as-product-golden-paths.md)
2. [Internal Developer Platform architecture and control planes](02-internal-developer-platform-architecture.md)
3. [Software catalogs, developer portals, and Backstage](03-software-catalog-portal-backstage.md)
4. [Self-service infrastructure with APIs, Crossplane, Terraform, and GitOps](04-self-service-infrastructure-crossplane-gitops.md)
5. [Platform SLOs, adoption, economics, and operating model](05-platform-slos-adoption-economics.md)
6. [Policy as code, admission control, and governance](06-policy-as-code-admission-governance.md)
7. [Kubernetes platform multi-tenancy and isolation boundaries](07-kubernetes-platform-multitenancy.md)

## Hands-on labs

1. [Validate a golden-path service request](../../labs/platform-engineering/01-golden-path-contract/README.md) — separate developer intent, platform policy, validation, and provisioning.
2. [Stage a policy from audit to enforcement](../../labs/platform-engineering/02-policy-rollout/README.md) — compare audit, warn, enforce, and expiring exception behavior.
3. [Validate a tenant isolation contract](../../labs/platform-engineering/03-tenant-isolation-contract/README.md) — evaluate namespace, RBAC, identity, network, quota, storage, and workload controls.
4. [Verify artifact identity and provenance policy](../../labs/platform-engineering/04-artifact-trust-verification/README.md) — bind deployment digests to authorized signatures, provenance, SBOMs, scans, and release evidence.

All current labs use only Python's standard library.

## Staff and Principal expectations

A strong candidate can distinguish a platform product from a centralized operations team; define valuable golden paths; preserve developer autonomy without exporting infrastructure complexity; connect portals, catalogs, APIs, controllers, GitOps, CI/CD, policy, and cloud services; define ownership and tenancy boundaries; and measure developer and business outcomes rather than ticket volume.

## Core model

```text
Developer intent
  -> product interface: portal, CLI, API, or Git
  -> policy and workflow orchestration
  -> provisioning and delivery control planes
  -> runtime and managed services
  -> evidence: SLOs, telemetry, cost, security, and feedback
```

The platform team owns usability and reliability of the interfaces and control planes. Application teams own their services, business behavior, and choices intentionally exposed through those interfaces.

## Principles

1. Start with a painful developer journey, not a tool.
2. Offer opinionated defaults with documented escape hatches.
3. Treat every self-service action as a production API.
4. Keep desired state versioned and auditable.
5. Prefer reconciliation over fragile one-shot automation.
6. Make ownership, support, and lifecycle visible.
7. Build security and cost controls into the path.
8. Measure time-to-outcome, cognitive load, reliability, and adoption.
9. Retire paths that are not supportable.
10. Avoid making the platform mandatory before it is valuable.
11. Treat policy engines and tenant boundaries as production contracts with tested failure modes.
12. Verify artifact identity and provenance before deployment rather than trusting mutable names or pipeline location.

## Common traps

- "Our platform is Kubernetes."
- "We installed Backstage, so we have an Internal Developer Platform."
- "Developers can edit any Terraform module, so the platform is self-service."
- "The portal is the source of truth."
- "We standardize by prohibiting exceptions."
- "Adoption is measured by logins."
- "The platform team owns every production incident."
- "More abstraction is always better."
- "Namespaces provide hard tenant isolation."
- "Every policy should fail closed."
- "A signed image is automatically trusted."

## Source discipline

Check implementation details against current official Kubernetes, Backstage, Crossplane, OpenGitOps, Terraform, Argo CD, Flux, OPA Gatekeeper, Kyverno, SLSA, Sigstore, cloud-provider, policy-engine, and observability documentation. The module separates durable principles from tool-specific behavior.
