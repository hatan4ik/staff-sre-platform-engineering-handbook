# Infrastructure as Code Tool Selection and Governance

This chapter provides a company-neutral framework for choosing and governing infrastructure automation. The objective is not to declare one tool universally superior. The objective is to select the smallest coherent toolchain that matches the resource lifecycle, control-plane ownership, failure model, organizational skills, and audit requirements.

## 1. Principal-level framing

A weak answer compares syntax:

> Terraform is multi-cloud, CloudFormation is AWS-native, and Ansible is imperative.

A strong answer begins with ownership and failure behavior:

> I select an infrastructure tool based on the control plane it owns, how it stores or derives desired state, how it previews and serializes change, how it detects drift, how it handles partial failure, and whether the organization can test, operate, and recover it. I avoid overlapping writers and define one authoritative owner for every resource.

The most important rule is:

> One resource must have one authoritative reconciliation owner at a time.

## 2. Separate the automation categories

Many “which IaC tool?” discussions compare tools that solve different problems.

| Category | Primary responsibility | Typical examples |
|---|---|---|
| Declarative infrastructure provisioning | Create and manage cloud or platform resources | Terraform, OpenTofu, CloudFormation, ARM/Bicep |
| Programming-language IaC | Generate and manage infrastructure using general-purpose languages | AWS CDK, Pulumi, CDK for Terraform |
| Configuration management | Configure operating systems and software after provisioning | Ansible, Puppet, Chef, Salt |
| Image construction | Build immutable machine or container images | Packer, image pipelines, Docker build systems |
| Kubernetes reconciliation | Manage Kubernetes resources through controllers | Kubernetes operators, Helm, Kustomize, Crossplane |
| GitOps delivery | Reconcile declared application or platform state from Git | Argo CD, Flux |
| Workflow orchestration | Coordinate approvals, dependencies, and multi-step operations | CI/CD systems, workflow engines, run platforms |
| Policy and governance | Validate or block unsafe changes | OPA, Sentinel, admission controls, cloud policy engines |

A mature platform may use several categories, but each category needs explicit ownership boundaries.

## 3. Desired state, observed state, and convergence

Every automation system implements some version of:

```text
desired state
     |
     v
comparison or execution engine
     |
     v
provider / API / agent
     |
     v
observed state
```

Questions to ask:

- Is desired state declarative or encoded as imperative steps?
- Is observed state refreshed from the real system?
- Is ownership stored in a state database, inferred from resource identity, or held by a long-running controller?
- Does convergence happen once per pipeline run or continuously?
- What happens when execution stops halfway?
- What evidence proves the system converged?

## 4. Tool-selection dimensions

### 4.1 Resource coverage

Evaluate:

- Required cloud and platform APIs.
- Maturity of providers or resource types.
- Support for new service features.
- Import and adoption behavior.
- Lifecycle and replacement semantics.
- Support for custom resources or extensions.

Do not choose a tool solely because it can technically call an API. Production suitability also requires stable ownership and recovery behavior.

### 4.2 State and ownership model

Ask:

- Does the tool maintain an external state database?
- Does the provider control plane itself store desired state?
- Is reconciliation continuous?
- How are concurrent writers prevented?
- How is resource adoption handled?
- How are renames and refactors represented?
- Can two stacks accidentally own the same object?

State is not automatically bad. Hidden or ambiguous ownership is bad.

### 4.3 Change preview

A useful preview should show:

- Creates.
- In-place updates.
- Replacements.
- Deletions.
- Unknown values.
- Dependency ordering.
- Policy violations.
- Potential blast radius.

A plan is evidence, not certainty. Provider behavior, eventual consistency, external mutation, and stale data can still produce different runtime outcomes.

### 4.4 Failure and recovery

Investigate:

- What happens after a partial apply?
- Is state persisted incrementally?
- Can the tool resume safely?
- How are asynchronous cloud operations observed?
- Is rollback automatic, replacement-based, or manual?
- How are failed resources imported or reconciled?
- Can a failed deployment leave an ambiguous owner?

### 4.5 Drift behavior

Possible models:

- Drift detected during the next plan.
- Continuous reconciliation repairs drift.
- Cloud-native drift detection reports divergence.
- Imperative scripts do not know whether drift exists.

Decide whether drift should be:

- Reverted automatically.
- Reported for approval.
- Accepted and imported.
- Escalated as unauthorized change.

### 4.6 Testing model

Evaluate support for:

- Static validation.
- Unit tests for modules or libraries.
- Policy checks.
- Plan assertions.
- Integration tests in disposable environments.
- Upgrade compatibility tests.
- Recovery tests.
- Contract tests for shared modules.

A tool is not production-ready for an organization merely because it can provision resources successfully once.

### 4.7 Security and access

Ask:

- Which identity executes changes?
- How broad are its credentials?
- Can plan and apply use different roles?
- Are credentials short-lived?
- Does state contain secrets?
- Is code execution sandboxed?
- Can third-party modules or providers execute arbitrary code?
- Are policy and approval controls bypassable?

### 4.8 Organizational fit

Consider:

- Existing language skills.
- Operational ownership.
- Hiring and training cost.
- Module ecosystem quality.
- Review readability.
- Debugging experience.
- Upgrade discipline.
- Vendor support requirements.

Do not choose a complex programming-language framework merely because the engineering team likes the language. Infrastructure code still needs deterministic review, constrained abstractions, and operational recovery.

## 5. Declarative provisioning tools

Strengths:

- Explicit desired-resource graph.
- Change preview.
- Dependency ordering.
- Repeatability.
- Import and drift workflows.
- Module composition.

Risks:

- State or ownership complexity.
- Provider behavior differences.
- Replacement surprises.
- Large graph refresh and plan time.
- Overly generic modules.
- False confidence in rollback.

Good use cases:

- Cloud resources.
- Network topology.
- Managed databases.
- Identity and policy.
- Shared platform infrastructure.

## 6. Cloud-native declarative tools

Cloud-native tools may provide:

- Faster support for provider-specific features.
- Tight integration with cloud policy, events, and audit.
- Provider-managed stack state.
- Native rollback or change-set mechanisms.

Trade-offs:

- Provider lock-in.
- Different tooling across clouds.
- Cloud-specific expression and extension models.
- Cross-account or organizational orchestration complexity.
- Stack lifecycle and rollback semantics that still require deep knowledge.

“Native” does not mean “operationally simple.”

## 7. Programming-language IaC

Benefits:

- Rich abstraction.
- Reusable libraries.
- General-purpose testing tools.
- Familiar language ecosystem.
- Easier generation of repeated structures.

Risks:

- Hidden side effects.
- Abstractions that obscure resource behavior.
- Non-deterministic code.
- Complex dependency logic.
- Reviewers must understand both the language and the infrastructure model.
- Large internal frameworks become difficult to upgrade.

Governance principles:

- Keep constructs small and opinionated.
- Expose operationally meaningful inputs.
- Avoid arbitrary application logic during synthesis.
- Generate stable, reviewable output where possible.
- Test replacement and deletion behavior.

## 8. Configuration management

Configuration-management tools remain useful for:

- Transitional estates.
- Network appliances.
- Bare metal.
- OS configuration not baked into images.
- Emergency repair under controlled conditions.

Risks:

- Mutable hosts drift over time.
- Ordering and idempotency bugs.
- Long convergence windows.
- Difficult rollback.
- Differences between newly built and long-lived systems.

Prefer immutable images for stable fleet baselines, then use configuration management only for narrowly defined dynamic concerns.

## 9. GitOps controllers

GitOps continuously reconciles declared state, commonly for Kubernetes resources.

Strengths:

- Continuous drift detection.
- Pull-based deployment.
- Versioned desired state.
- Clear reconciliation status.
- Reduced direct cluster credentials in CI.

Risks:

- Multiple controllers fighting over the same object.
- Secret-delivery complexity.
- Bad commits reconciling quickly across a wide fleet.
- Deletion propagation.
- Dependency and promotion ordering.
- Confusion between infrastructure provisioning and in-cluster delivery.

GitOps is an operating model, not simply storing YAML in Git.

## 10. Crossplane and control-plane patterns

A Kubernetes-native control plane can expose higher-level platform APIs and reconcile external resources.

Strengths:

- Continuous reconciliation.
- Kubernetes API and RBAC model.
- Composable platform abstractions.
- Self-service through custom resources.

Risks:

- Kubernetes becomes a critical infrastructure control plane.
- Provider controllers and CRDs require lifecycle management.
- External resource deletion semantics are powerful.
- Debugging crosses Kubernetes, provider controllers, and cloud APIs.
- State and ownership migration from existing tools is non-trivial.

Use this model when the organization is prepared to operate a control plane, not merely because Kubernetes is familiar.

## 11. One owner per resource

Overlapping writers create the most dangerous IaC failures.

Examples:

- Terraform manages a Kubernetes object while Argo CD also reconciles it.
- CloudFormation owns a resource later imported into Terraform without removing original ownership.
- An autoscaler changes capacity while Terraform continuously resets it.
- A human changes a resource while a controller reverts it.
- Two Terraform states contain the same remote object.

Define ownership in a registry:

| Resource domain | Authoritative owner | Allowed secondary actors |
|---|---|---|
| Cloud network | Terraform stack | Cloud controller may attach interfaces |
| Kubernetes workload manifests | GitOps controller | HPA may change replicas |
| Node group desired baseline | IaC | Autoscaler changes runtime capacity within contract |
| Secrets | Secret manager | Delivery controller reads and projects |
| DNS records | DNS automation owner | Emergency break-glass role |

Secondary actors need explicit fields or scopes they are allowed to mutate.

## 12. Control-loop composition

Modern platforms have many reconcilers:

```text
Terraform
GitOps controller
Kubernetes controllers
HPA
Cluster Autoscaler or node provisioner
cloud service controllers
security policy controllers
operators
```

A correct design defines:

- Which fields each controller owns.
- Which controller is authoritative during conflict.
- Expected convergence time.
- Safety bounds.
- Pause and override mechanisms.
- Evidence for controller fights.

Repeated changes to the same field are often an ownership conflict, not random drift.

## 13. Module and abstraction governance

A module should represent a stable product contract, not merely reduce duplicated syntax.

Good module properties:

- Clear owner.
- Narrow purpose.
- Explicit lifecycle.
- Safe defaults.
- Minimal outputs.
- Versioned interface.
- Upgrade guide.
- Tested replacement behavior.
- Escape hatch with review.

Bad module patterns:

- Hundreds of unrelated options.
- Passing raw provider arguments through every layer.
- Hidden resource creation.
- Cross-region or cross-account behavior without explicit inputs.
- Outputs that expose entire resource objects.
- Breaking changes under the same version.

## 14. Policy as code

Policy should evaluate both configuration and proposed behavior.

Useful checks:

- Public exposure.
- Encryption.
- Region restrictions.
- Required tags and ownership.
- Destructive changes.
- Privileged identities.
- Network paths.
- Backup and retention.
- State-backend configuration.
- Provider and module provenance.

Policy levels:

```text
advisory
  -> warning
  -> approval required
  -> hard deny
```

Roll out new policies in audit mode first unless the risk is immediate and well understood.

## 15. Change pipeline

A robust pipeline separates stages:

```text
format and validate
  -> static analysis
  -> module tests
  -> security and policy checks
  -> plan / change set
  -> human or automated approval
  -> apply with one writer
  -> post-apply verification
  -> drift and SLO observation
```

Bind the apply to:

- Reviewed commit.
- Approved plan artifact.
- Approved module versions.
- Approved provider versions.
- Exact target environment.
- Short-lived execution identity.

## 16. Promotion model

Do not promote by copying infrastructure manually.

Prefer:

- Versioned modules.
- Environment-specific inputs.
- Progressive account, region, or cluster rollout.
- Canary resources where practical.
- Explicit stop conditions.
- Replacement-based rollback where mutable rollback is unsafe.

Production should not be the first environment to exercise a provider or module upgrade.

## 17. Rollback reality

Infrastructure rollback differs from application rollback.

Examples:

- A database migration may be irreversible.
- Recreating a resource may lose data or identity.
- Restoring an old template may trigger replacements.
- Deleting a newly created network may fail because dependencies attached to it.
- A cloud service may continue an asynchronous update.

Plan both:

- **Configuration rollback:** restore previous desired code.
- **Operational recovery:** reconcile actual remote state safely.

## 18. Partial-apply recovery

When an execution fails midway:

1. Freeze other writers.
2. Capture logs, state, change-set status, and cloud audit evidence.
3. Identify completed, in-progress, failed, and unstarted operations.
4. Confirm whether the automation state was persisted.
5. Compare desired state, tool state, and real infrastructure.
6. Repair ownership before rerunning.
7. Review a new plan or change set.
8. Resume one writer.

Never assume rerunning is safe until the state and provider operations are understood.

## 19. Tool migration

Migrating between tools is an ownership transfer.

Safe sequence:

```text
inventory existing ownership
  -> freeze changes
  -> model target configuration
  -> import or adopt resources
  -> prove no create/delete
  -> remove old owner
  -> enable new owner
  -> observe convergence
```

Avoid both tools actively reconciling the same resource during migration.

Use staged domains rather than a “big bang” migration.

## 20. Multi-cloud strategy

Multi-cloud does not automatically require one universal IaC abstraction.

Possible models:

1. One declarative tool with cloud-specific modules.
2. Cloud-native tools behind a shared platform API.
3. Kubernetes control plane with provider-specific compositions.
4. Separate cloud stacks with common governance and delivery standards.

Standardize where it creates leverage:

- Repository conventions.
- Identity and approval model.
- Policy language.
- Module quality standard.
- Audit and evidence.
- SLOs and recovery exercises.

Do not erase provider differences behind an abstraction that operators cannot debug.

## 21. Decision matrix

Score each option against the actual environment.

| Dimension | Questions |
|---|---|
| Coverage | Does it support required resources and lifecycle behavior? |
| Ownership | Is authoritative ownership clear and recoverable? |
| Preview | Can reviewers understand create, update, replace, and delete? |
| Concurrency | How are writers serialized? |
| Drift | How is divergence detected and resolved? |
| Recovery | How are partial failures and state loss handled? |
| Security | How are credentials, state, and code execution protected? |
| Testing | Can modules, policies, integrations, and recovery be tested? |
| Scale | Can it handle graph size, account count, and change rate? |
| Skills | Can the organization operate it during an incident? |
| Ecosystem | Are providers, modules, and upgrades trustworthy? |
| Cost | What are platform, licensing, and operating costs? |
| Exit | Can ownership migrate without recreating infrastructure? |

## 22. Example tool-boundary architecture

```text
Terraform or cloud-native IaC
  owns cloud accounts, networks, clusters, databases, and IAM

Image pipeline
  owns machine and container image production

GitOps
  owns Kubernetes workload and platform manifests

Kubernetes controllers
  own runtime fields within explicit contracts

Configuration management
  owns narrowly scoped legacy host configuration

Policy engine
  validates changes across all layers
```

The exact tools can change. The ownership boundaries must remain explicit.

## 23. Governance and platform product model

A central platform team should provide:

- Approved templates and modules.
- Provider and tool upgrade cadence.
- State and backend standards.
- Policy packs.
- CI workflow templates.
- Documentation and examples.
- Migration paths.
- Office hours and support SLOs.
- Telemetry on adoption, failure, and lead time.

Measure platform success through developer and operational outcomes:

- Provisioning lead time.
- Change failure rate.
- Recovery time.
- Policy violation rate.
- Module adoption.
- Upgrade lag.
- Manual exception volume.
- Drift age.

## 24. Common weak answers

Avoid:

- “Terraform is always best because it is multi-cloud.”
- “Cloud-native tools cannot manage large estates.”
- “Programming languages make infrastructure easier.”
- “GitOps means every resource belongs in Git.”
- “Rollback is just applying the previous commit.”
- “Ansible is not IaC.”
- “Stateful tools are bad.”
- “Controllers will eventually figure it out.”

Each statement ignores ownership, failure behavior, and organizational context.

## 25. Ninety-second interview answer

> I would not select an IaC tool by syntax or brand. I would start by defining the resource lifecycle, authoritative control plane, drift model, credentials, failure domain, and recovery requirements. Then I would compare coverage, state and locking, preview quality, partial-apply behavior, import and refactoring, policy, testing, scale, and the team's ability to operate the tool under pressure.
>
> The core architecture rule is one authoritative owner per resource. Terraform or a cloud-native declarative engine can own cloud resources; GitOps can own Kubernetes manifests; autoscalers and operators may own explicit runtime fields; image pipelines own immutable artifacts. I would document those boundaries because overlapping reconcilers create controller fights and split-brain ownership.
>
> I would standardize state backends, short-lived execution identity, one writer per state or stack, reviewed plans, policy checks, post-apply verification, drift detection, and recovery runbooks. Modules are versioned platform products with narrow contracts and tested replacement behavior. Tool migration is an ownership transfer: freeze, import or adopt, prove no unintended create or delete, remove the old owner, then enable the new one. The result may use more than one tool, but it should remain one coherent operating model.

## 26. Adversarial follow-ups

1. Why is one tool for every layer often a mistake?
2. How do you detect two controllers fighting over one field?
3. When is cloud-native IaC better than a cloud-neutral tool?
4. When is programming-language IaC too powerful?
5. How do you test destructive replacement behavior?
6. What makes a reusable module a platform product?
7. How do you migrate a live resource between tools safely?
8. What should happen when drift is an authorized emergency change?
9. Why is applying the previous commit not always rollback?
10. How do you separate autoscaler ownership from IaC ownership?
11. When should configuration management remain in the architecture?
12. How do you avoid hiding provider differences in multi-cloud abstractions?
13. Which evidence proves an IaC platform improved delivery?
14. How do you expire stale approved plans?
15. What is your break-glass model when the automation control plane is unavailable?

## Related canonical material

- [Terraform state integrity, locking, recovery, and governance](terraform-state-integrity.md)
- [Distributed systems module](../distributed-systems/README.md)
- [Service mesh control-plane and data-plane reasoning](../service-mesh/README.md)
- [Migration and ownership plan](../../MIGRATION_PLAN.md)
