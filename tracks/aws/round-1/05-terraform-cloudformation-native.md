# Question 5 — Terraform versus CloudFormation and AWS-Native Provisioning

## Interview prompt

How would you automate infrastructure provisioning using Terraform, CloudFormation, and AWS-native services? When would you choose one over the other?

## What the interviewer is testing

The interviewer is not looking for a favorite tool. They want to see whether you can select an ownership model based on platform scope, governance, team skill, failure behavior, state management, service coverage, and long-term operations.

---

## 90-second Staff/Principal answer

> I choose one authoritative provisioning engine per resource boundary and standardize the delivery controls around it. Terraform is my default when I need a consistent workflow across AWS accounts, Kubernetes, SaaS, or multiple clouds, and when the team benefits from its module ecosystem and plan-driven dependency graph. CloudFormation is a strong choice for AWS-only stacks, deep AWS governance, StackSets across accounts and Regions, Service Catalog products, and teams that want AWS to manage stack state and rollback semantics. CDK is a developer abstraction that synthesizes CloudFormation, not a separate runtime control plane.
>
> AWS-native automation complements either tool. Control Tower and Organizations establish account guardrails, StackSets distribute baselines, Service Catalog exposes approved products, Systems Manager Automation handles operational workflows, Config detects noncompliance, and EventBridge or Step Functions can orchestrate controlled remediation.
>
> I avoid having Terraform and CloudFormation own the same resource. Provisioning runs through pull requests, short-lived OIDC credentials, validation, policy checks, change previews, approvals, one writer per state or stack, post-deployment verification, and drift detection. The selection is based on the resource lifecycle and operating model, not ideology; a deliberate hybrid platform is valid when boundaries are explicit.

---

## 1. Decision principles

Evaluate each option against:

- cloud scope: AWS-only or multi-provider
- service and feature coverage
- state and rollback model
- multi-account and multi-Region deployment
- governance integration
- module or construct reuse
- team language and operational skill
- drift detection and import behavior
- testing and policy ecosystem
- deployment blast radius
- incident recovery
- long-term ownership

The wrong question is:

> Which tool is best?

The better question is:

> Which control plane should own this resource lifecycle, and how will we deploy, audit, recover, and eventually migrate it?

---

## 2. Terraform model

Terraform uses provider plugins, configuration, and state to calculate a dependency graph and converge infrastructure toward desired configuration.

### Strong fits

- AWS plus Kubernetes, GitHub, Datadog, Cloudflare, or other providers
- organizations operating more than one cloud
- reusable cross-account and cross-Region modules
- teams standardized on HCL and Terraform workflows
- plan-first review and policy tooling
- platform APIs assembled from multiple vendors

### Strengths

- broad provider ecosystem
- consistent language across many APIs
- explicit plan output
- reusable modules
- dependency graph
- strong community and tooling ecosystem
- mature import and state-manipulation capabilities

### Operational risks

- state is a highly privileged external control-plane database
- provider upgrades can change behavior
- a provider may lag or imperfectly model an API
- partial apply requires reconciliation
- module abstraction can hide dangerous defaults
- excessive `depends_on`, provisioners, or shell scripts can make plans unreliable
- one large state creates lock and blast-radius problems

### Appropriate Terraform boundaries

```text
Terraform
├── AWS Organizations support resources where chosen
├── VPC and connectivity
├── EKS cluster foundation
├── IAM roles and KMS keys
├── data services
├── DNS and certificates
└── external SaaS integrations
```

Do not automatically use Terraform for rapidly changing Kubernetes application releases when a GitOps controller is the better continuous reconciler.

---

## 3. CloudFormation model

CloudFormation stores stack state in the AWS service and operates resources through stack create, update, change set, rollback, drift, and delete operations.

### Strong fits

- AWS-only infrastructure
- deep integration with AWS account governance
- StackSets across organizational units, accounts, and Regions
- Service Catalog products
- vendor-delivered AWS templates
- AWS-native teams wanting managed stack state
- resource deployment tightly coupled to AWS services

### Strengths

- no customer-managed Terraform-style state file
- change sets for preview
- stack events and rollback behavior
- nested stacks and modules
- StackSets for fleet deployment
- tight integration with IAM, Organizations, Service Catalog, and CloudTrail
- direct support from AWS for the CloudFormation service

### Operational risks

- rollback can fail and leave `UPDATE_ROLLBACK_FAILED`
- resources with complex external mutations may drift
- large stacks create broad update blast radius
- cross-stack exports can create rigid dependencies
- custom resources introduce Lambda-backed code and failure modes
- template abstraction can become difficult to reason about
- service coverage and property support must be verified for required features

### Recovery mindset

A failed CloudFormation update is not solved by immediately deleting the stack.

Investigate:

- stack events
- failed resource status and reason
- IAM or service quota failure
- resource replacement behavior
- rollback status
- dependencies outside the stack
- retained resources

Use `continue-update-rollback` and resource skip options only with a documented reconciliation plan, because skipped resources may no longer match the template.

---

## 4. AWS CDK

AWS CDK lets developers define infrastructure using programming languages and constructs. It synthesizes CloudFormation templates and uses CloudFormation for deployment.

Therefore:

- CloudFormation stack state and rollback semantics still apply
- CDK code must be tested and reviewed
- construct upgrades can alter synthesized resources
- generated logical IDs and replacement behavior matter
- developers should inspect `cdk diff` and the synthesized template

### Strong fits

- application teams comfortable with TypeScript, Python, Java, C#, or Go
- organizations building reusable high-level AWS constructs
- teams wanting tests around infrastructure composition
- platforms distributing opinionated constructs

### Risks

- imperative-looking code can hide declarative replacement behavior
- construct abstractions can conceal generated IAM or networking
- dependency-version updates may create large diffs
- overly powerful constructs can standardize unsafe patterns

CDK is not “better CloudFormation”; it is an abstraction layer that changes authoring and reuse while retaining CloudFormation as the deployment engine.

---

## 5. CloudFormation StackSets

Use StackSets to distribute standardized AWS resources across accounts and Regions.

Common examples:

- audit and security roles
- Config recorders and rules
- CloudTrail support resources
- GuardDuty or Security Hub configuration support
- baseline IAM roles
- VPC endpoints or shared controls where standardized
- operational agents and logging destinations

### Organizational deployment

With AWS Organizations integration, StackSets can target organizational units and automatically include new accounts according to configuration.

### Safety controls

- stage by test OU before production OUs
- set operation concurrency and failure tolerance deliberately
- understand Region ordering
- monitor failed stack instances
- protect critical retained resources
- avoid a single untested template update across the entire organization

Fleet automation increases both consistency and blast radius.

---

## 6. AWS Service Catalog

Service Catalog provides approved, versioned products for self-service provisioning.

Use it when teams need to request standardized resources without receiving unrestricted infrastructure permissions.

Examples:

- approved S3 data bucket
- standard application VPC
- EKS namespace or account onboarding workflow
- compliant RDS pattern
- sandbox account product

A product can be backed by CloudFormation and governed through:

- portfolios
- launch constraints
- template constraints
- product versions
- tags and budgets

Service Catalog is an access and product-governance layer, not a replacement for good template engineering.

---

## 7. Control Tower and Organizations

Use Organizations for account hierarchy and service control policies. Use Control Tower where its landing-zone lifecycle and supported controls match the organization.

Typical responsibilities:

```text
Organizations / Control Tower
├── account creation and enrollment
├── organizational units
├── preventive and detective controls
├── centralized logging and audit foundations
├── identity integration
└── account lifecycle governance
```

Do not use Terraform or CloudFormation to fight Control Tower-managed resources. Document ownership and supported customization mechanisms.

### SCP caution

SCPs set maximum available permissions; they do not grant permissions. A change can block automation across many accounts, including recovery roles.

Stage and test SCP changes, preserve emergency access, and validate service-linked roles and required regional operations.

---

## 8. Systems Manager Automation

Systems Manager Automation is suited to operational procedures rather than desired-state infrastructure graphs.

Examples:

- rotate or replace instances
- apply a controlled remediation
- collect diagnostic evidence
- stop or start approved resources
- execute disaster-recovery steps
- run a maintenance workflow with approvals

Automation documents can include branching, approvals, AWS API calls, scripts, and rollback steps.

Use it for runbook execution, not as an unstructured substitute for infrastructure state management.

---

## 9. AWS Config remediation

AWS Config detects resource configuration and compliance against rules.

Possible workflow:

```text
resource drifts
   |
AWS Config rule evaluates noncompliant
   |
EventBridge / Config remediation
   |
Systems Manager Automation or controlled Lambda
   |
remediate, ticket, or quarantine
```

### Auto-remediation caution

Do not automatically mutate every noncompliant production resource.

Classify rules:

- safe deterministic remediation
- ticket and owner notification
- quarantine
- manual security approval
- Terraform or CloudFormation source correction required

If Config changes a resource that Terraform owns, the next plan may reverse it. The correct fix often belongs in the authoritative IaC source.

---

## 10. Step Functions and EventBridge orchestration

Use EventBridge for event routing and Step Functions for stateful workflow orchestration.

Examples:

- new account event triggers baseline deployment
- approved image triggers staged AMI promotion
- security finding triggers evidence capture and quarantine
- DR declaration runs ordered recovery tasks
- Service Catalog product approval launches provisioning

The workflow should call authoritative provisioning or operational systems, not create an undocumented second infrastructure engine.

---

## 11. Tool selection matrix

| Requirement | Terraform | CloudFormation | CDK | AWS-native orchestration |
|---|---:|---:|---:|---:|
| Multi-cloud or SaaS providers | Strong | Weak | Weak | Weak |
| AWS-only fleet baseline | Good | Strong | Strong authoring | Strong with StackSets |
| Managed state by AWS | No | Yes | Yes through CFN | Service dependent |
| Plan/change preview | `terraform plan` | change sets | `cdk diff` + change set | workflow-specific |
| Organizational StackSets | No native equivalent | Strong | Synthesizes CFN | Strong |
| General-purpose language | No, HCL | No, YAML/JSON | Yes | Lambda/Step Functions as needed |
| Kubernetes/SaaS ecosystem | Strong | Limited/custom | AWS-oriented | Service dependent |
| Operational runbooks | Not ideal | Not ideal | Not ideal | Systems Manager strong |
| Self-service product catalog | External platforms | Service Catalog backing | Service Catalog backing | Strong |

This table is directional. Validate actual service and provider support for the required resource properties.

---

## 12. A deliberate hybrid model

A mature AWS organization may use:

```text
Organizations + Control Tower
    own account guardrails and landing zone

CloudFormation StackSets
    own mandatory account baselines

Terraform
    owns shared network, EKS, data, and cross-provider platform resources

Argo CD / Flux
    owns Kubernetes add-ons and applications

Service Catalog
    exposes approved self-service products

Systems Manager Automation
    executes operational runbooks

AWS Config
    detects compliance drift
```

This is safe only when every resource type has one owner.

### Ownership register

Maintain a catalog with:

- resource class
- owning tool
- source repository
- state or stack identifier
- deployment role
- team owner
- recovery runbook
- migration status

---

## 13. Delivery workflow standards

Regardless of provisioning engine:

### Pull request

- lint and validate
- security scan
- policy evaluation
- module or construct tests
- plan, change set, or diff
- quota and replacement analysis
- cost-impact summary where material
- required approval

### Authentication

Use short-lived OIDC federation. Separate:

- read/plan role
- production deployment role
- break-glass role

### Deployment

- one writer per Terraform state or CloudFormation stack
- environment-specific concurrency controls
- immutable source revision
- explicit Region and account
- post-deployment health checks
- retained logs and change evidence

### Drift

- scheduled Terraform plan or managed drift workflow
- CloudFormation drift detection where supported
- AWS Config for policy compliance
- incident process for emergency changes

---

## 14. Testing infrastructure code

### Static tests

- formatting and syntax
- linting
- policy-as-code
- security scanning
- IAM policy analysis
- template validation

### Unit or composition tests

- Terraform module tests or test frameworks
- CDK assertions against synthesized templates
- CloudFormation template tests
- construct or module contract tests

### Ephemeral integration tests

Provision a temporary account, VPC, or stack and verify:

- resources exist with intended configuration
- network flows work
- IAM denies unauthorized actions
- deletion and replacement behavior
- upgrade from previous supported version
- cleanup succeeds

### Production-like tests

- canary account or Region
- StackSet staged deployment
- Terraform module promotion
- disaster-recovery exercise
- rollback or forward-fix procedure

A successful create test is insufficient. Test update, failure, and destroy behavior.

---

## 15. Import and migration

### Existing resources into Terraform

1. inventory resource and dependencies
2. write matching configuration
3. import into isolated state
4. run plan until no unintended change remains
5. protect against replacement
6. move deployment authority to CI
7. remove old owner only after verification

### Existing resources into CloudFormation

Use resource import where supported. Verify identifiers, required properties, deletion policy, and drift status.

### Migrating between tools

Never allow both tools to own the resource during migration.

A controlled pattern:

1. freeze changes
2. capture current configuration and dependencies
3. create destination code
4. import to destination state or stack
5. verify no-change preview
6. remove source ownership without deleting the resource
7. enable destination pipeline
8. test future update and recovery

Tool migration is a control-plane handoff.

---

## 16. Failure scenarios

### Terraform partial apply

- freeze writers
- preserve state and logs
- inspect real resources
- refresh-only plan
- import or reconcile
- review normal plan
- resume one writer

### CloudFormation rollback failure

- inspect stack events
- fix underlying permission, quota, or resource problem
- use controlled continue rollback
- reconcile skipped resources
- generate a new change set

### StackSet fleet failure

- stop rollout
- identify account/Region cohort
- verify failure tolerance behavior
- correct template or target prerequisites
- resume in a small wave

### Config remediation loop

- disable unsafe remediation
- identify authoritative owner
- restore intended configuration in IaC
- fix the rule or exception model
- verify no repeated mutation

---

## 17. Governance and policy

Policy examples:

- approved Regions
- mandatory tags and ownership
- encryption required
- public access denied
- restricted instance families
- no wildcard administrative IAM
- backup and retention standards
- production deletion protection
- approved AMIs and container registries
- network exposure controls

Policy enforcement layers:

- SCPs: maximum account permissions
- IAM and permission boundaries: principal authority
- Terraform policy checks: proposed plan
- CloudFormation hooks: resource provisioning controls
- Service Catalog constraints: product use
- AWS Config: deployed resource compliance
- admission policy: Kubernetes resources

Layer controls so one bypass does not eliminate governance, but avoid contradictory owners.

---

## Adversarial follow-ups

### “Why not standardize on one tool for everything?”

Standardization reduces cognitive load, but forcing one tool into every lifecycle can create worse operations. I standardize the delivery, identity, policy, and ownership model, then permit a small number of approved engines with explicit boundaries.

### “CloudFormation has rollback, so is it safer than Terraform?”

Not universally. Rollback can fail, and some resource changes are irreversible or external. Safety comes from stack boundaries, change preview, testing, permissions, and recovery procedures, not a feature label.

### “Why use CDK instead of Terraform?”

CDK is attractive for AWS-focused teams wanting reusable constructs and general-purpose-language tests while retaining CloudFormation operations. Terraform is stronger when the platform spans many providers or the organization is standardized on its state and module workflow.

### “Can Config auto-fix Terraform drift?”

It can remediate some conditions, but that may create a controller conflict. For Terraform-owned resources, the durable fix usually belongs in Terraform. Config can quarantine or trigger a pipeline rather than directly mutating every resource.

### “Would you use custom resources?”

Only when the required lifecycle is not natively supported and the team is willing to own Lambda code, idempotency, timeouts, retries, rollback, security, and upgrades. A custom resource is production software.

---

## Weak answers to avoid

- “Terraform is better because it is multi-cloud.”
- “CloudFormation is always safer because AWS manages it.”
- “CDK replaces CloudFormation.”
- letting Terraform and CloudFormation own the same resource
- using Lambda scripts as an undocumented infrastructure engine
- auto-remediating every Config finding without ownership analysis
- one giant Terraform state or CloudFormation stack
- skipping change sets or plans because the code was reviewed
- treating rollback as guaranteed
- selecting tools from personal preference rather than operating requirements

---

## Closing statement

> I optimize for clear authority and recoverable operations. Terraform, CloudFormation, CDK, and AWS-native automation are all valid tools, but each resource has one owner, every change has a preview and identity, and every control plane has a tested failure and migration path.