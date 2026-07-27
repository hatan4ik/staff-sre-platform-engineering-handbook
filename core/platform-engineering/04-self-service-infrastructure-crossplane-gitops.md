# Self-Service Infrastructure with APIs, Crossplane, Terraform, and GitOps

## Why this exists

Self-service infrastructure is not a form that runs cloud commands. It is a contract that lets users declare an outcome while the platform validates policy, creates or updates desired state, reconciles actual resources, reports conditions, and preserves auditability.

The implementation may use Terraform, Crossplane, cloud-native provisioning, GitOps, or a combination. The correct choice depends on the desired operating model, state boundary, lifecycle, team skills, and failure behavior.

## What the interviewer is testing

A strong answer should explain:

- how to design a stable infrastructure product API;
- the difference between a one-shot workflow and a continuously reconciled control loop;
- where desired state and execution state live;
- how Terraform and Crossplane differ operationally;
- how GitOps fits without becoming a universal answer;
- idempotency, drift, partial failure, deletion, and recovery;
- multi-tenancy, policy, credentials, and blast radius;
- how to publish new capabilities safely.

## Start with the product API

The platform should expose an outcome-oriented contract.

Weak API:

```yaml
resourceType: aws_db_instance
instanceClass: db.r6g.4xlarge
subnetGroup: prod-private-17
parameterGroup: pg16-prod-03
```

Stronger API:

```yaml
apiVersion: platform.example.com/v1
kind: PostgreSQLService
metadata:
  name: orders
spec:
  owner: team-orders
  environment: production
  serviceTier: critical
  storageClass: durable
  dataClassification: confidential
  recovery:
    rpo: 5m
    rto: 30m
  regionPolicy: primary-and-dr
```

The platform translates business and reliability intent into supported implementation details. Do not expose cloud-provider fields simply because they exist.

## API design rules

- use stable, versioned schemas;
- separate required intent from implementation detail;
- provide safe defaults;
- constrain choices to supported values;
- return explicit status and conditions;
- make updates and deletion semantics clear;
- define compatibility and migration policy;
- support dry-run or plan where useful;
- include ownership and data classification;
- avoid fields that cannot be honored consistently.

## Control-plane options

### Terraform execution plane

Terraform is strong when:

- mature modules and provider support already exist;
- plan review is important;
- infrastructure is organized into explicit state boundaries;
- teams understand state locking, drift, imports, and partial applies;
- execution can be centralized through a controlled runner.

A platform usually wraps Terraform with:

- a stable product API or module contract;
- versioned configuration generation;
- remote state and locking;
- plan and policy checks;
- controlled apply identity;
- durable run records;
- drift and reconciliation policy;
- state backup and recovery procedures.

Terraform is declarative, but a standard apply is not a continuously running reconciliation loop. External automation must decide when to plan, apply, detect drift, and retry.

### Crossplane control plane

Crossplane extends Kubernetes with managed resources and custom APIs. Composite Resource Definitions define platform-facing APIs; Compositions and composition functions translate those APIs into managed or Kubernetes resources.

Crossplane is strong when:

- the organization wants Kubernetes-style APIs and reconciliation;
- desired state should be continuously converged;
- platform capabilities benefit from composable custom resources;
- teams can operate controllers, providers, CRDs, upgrades, and cluster-level security;
- the control-plane blast radius is acceptable and intentionally partitioned.

Current Crossplane releases emphasize namespaced resources and composition functions. Claims were central to earlier Crossplane v1 designs; candidates should check the current release model rather than repeating old architecture from memory.

### Cloud-native provisioning

CloudFormation, CDK-based deployment, Azure deployment stacks, Google Cloud tooling, and service-specific APIs can be the right answer when provider-native integration, lifecycle behavior, or organizational skill makes them safer than adding another control plane.

### GitOps

GitOps stores declarative desired state in a versioned and immutable form and uses an automated pull-based reconciler to converge the target system.

GitOps is valuable for:

- auditable desired-state changes;
- review and separation of duties;
- environment promotion;
- continuous drift correction;
- disaster reconstruction;
- clear rollback to a previous declaration.

Git is not an execution engine, lock manager, secrets store, or universal workflow database. A pull request can approve intent, while a controller or provisioning system performs and observes the work.

## Combined architecture

```text
Portal / CLI / API
       |
       v
Product resource or request
       |
       +--> policy and approval
       |
       +--> versioned desired state in Git
       |           |
       |           v
       |      GitOps reconciler
       |
       +--> Terraform run request
       |
       +--> Crossplane custom resource
                    |
                    v
          provisioning control plane
                    |
                    v
              cloud and runtime APIs
                    |
                    v
          conditions, events, cost, SLO
```

One capability should have one authoritative writer. Do not let Terraform and Crossplane manage the same resource fields.

## Reconciliation contract

Every platform resource needs conditions that explain progress.

Example:

```yaml
status:
  observedGeneration: 12
  conditions:
    - type: Ready
      status: "False"
      reason: WaitingForDatabase
      message: Database endpoint is not available yet
    - type: PolicyCompliant
      status: "True"
    - type: Degraded
      status: "False"
```

Good conditions are:

- machine-readable;
- stable enough for automation;
- specific about retryability;
- correlated with provider or workflow evidence;
- safe to expose without leaking secrets.

## Terraform versus Crossplane

| Concern | Terraform execution plane | Crossplane control plane |
|---|---|---|
| Primary unit | configuration plus state | Kubernetes resource plus controller state |
| Execution | explicit plan/apply run | continuous reconciliation |
| Review | strong plan workflow | manifest/API review plus conditions |
| Drift | detected on plan or scheduled process | continuously observed by controller |
| Extensibility | modules and providers | XRDs, Compositions, functions, providers |
| Failure model | partial apply and state reconciliation | controller/provider backoff and convergence |
| Operational burden | runner, state, provider lifecycle | Kubernetes control plane, CRDs, controllers, providers |
| Best fit | existing IaC estates and reviewed changes | API-oriented platforms with control-loop expertise |

This is not a winner-takes-all comparison. Many organizations use both, with explicit ownership boundaries.

## State and ownership boundaries

Define state per capability, account, environment, or tenant according to blast radius and lifecycle.

Avoid:

- one Terraform state for the entire company;
- one Crossplane control plane with unrestricted provider credentials;
- platform resources that span unrelated ownership domains;
- two reconcilers fighting over the same object;
- hidden manual changes with no drift policy.

Use labels, tags, annotations, state metadata, and catalog relationships to preserve owner and provenance.

## Multi-tenancy and credentials

Controls include:

- namespace or project isolation;
- separate cloud accounts or subscriptions where risk warrants it;
- provider identities scoped by capability and tenant;
- short-lived workload identity;
- policy at API admission and provider boundaries;
- quotas and concurrency limits;
- network isolation for runners and controllers;
- separate production and non-production control planes;
- protected administrative operations;
- explicit break-glass access.

A namespaced API does not automatically create cloud-level tenant isolation.

## Policy design

Apply policy at several points:

```text
Input schema
  -> business policy
  -> code and manifest policy
  -> admission policy
  -> cloud-provider policy
  -> continuous compliance evidence
```

Examples:

- allowed regions and service tiers;
- mandatory encryption and ownership tags;
- prohibited public exposure;
- approved identity patterns;
- backup and retention requirements;
- maximum cost class;
- deletion protection for critical data;
- required SLO and runbook metadata.

Prefer fast, actionable errors near the user. Backstop with enforcement at the target system.

## Failure modes

- partial Terraform apply leaves real resources and incomplete state;
- provider API succeeds but response is lost;
- controller retries a non-idempotent external operation;
- Git desired state is valid but impossible due to quota;
- resource deletion removes data before retention checks;
- provider upgrade changes behavior across many tenants;
- CRD schema change breaks existing objects;
- a global credential expands blast radius;
- GitOps pruning deletes resources owned by another controller;
- portal reports failure after the resource actually succeeded.

## Recovery approach

1. Stop concurrent writers.
2. Preserve logs, workflow records, state, resource conditions, and cloud audit events.
3. Identify desired state, recorded state, and actual state separately.
4. Determine ownership for every affected resource.
5. Reconcile by import, refresh, state repair, controller retry, or desired-state correction.
6. Avoid blind destroy-and-recreate for stateful resources.
7. Validate service behavior, not only control-plane success.
8. Add a guardrail, test, or migration to prevent recurrence.

## Versioning and migration

Platform APIs need lifecycle discipline:

- publish versioned schemas;
- maintain conversion or migration paths;
- pin provider and function versions;
- test upgrades against representative resources;
- canary new compositions or modules;
- support rollback where state compatibility allows;
- publish deprecation dates and owner actions;
- prevent automatic global upgrades of privileged controllers.

## Observability and SLOs

Useful signals:

- API request availability;
- time from accepted intent to ready resource;
- reconciliation lag;
- queue age and apply duration;
- provider API errors and throttling;
- manual-intervention rate;
- drift rate;
- stale status rate;
- deletion completion and retention compliance;
- resource readiness by template/module/composition version;
- cost variance from the expected service tier.

## 90-second interview answer

> I expose self-service infrastructure through a stable outcome-oriented API, not raw cloud fields. The API captures ownership, environment, data class, reliability tier, and bounded choices, then returns explicit asynchronous conditions. I choose the control plane based on operating model. Terraform is effective for reviewed plan-and-apply workflows with mature modules and explicit state boundaries, while Crossplane is effective when we want Kubernetes-style APIs and continuous reconciliation through managed resources and compositions. GitOps can version and approve desired state, but a reconciler or provisioning system must execute and observe it. I define one authoritative writer per resource, use short-lived scoped identities, partition production blast radius, enforce policy at input and target boundaries, and treat deletion as a governed lifecycle operation. Recovery compares desired, recorded, and actual state before import, refresh, retry, or correction. I measure time-to-ready, reconciliation lag, drift, provider errors, and manual intervention.

## Adversarial follow-ups

### "Why not expose Terraform modules directly?"

Modules can be an implementation contract, but many expose provider complexity and unstable fields. A product API should remain stable even when the underlying module or provider changes.

### "Why not use Crossplane for everything?"

It adds a privileged Kubernetes-based control plane, provider lifecycle, CRD migration, and controller failure modes. It is appropriate only where those costs support a valuable API and reconciliation model.

### "Can Terraform and Crossplane coexist?"

Yes, with explicit resource and field ownership. They must not reconcile the same object.

### "Is a successful apply enough?"

No. The capability is ready only when downstream acceptance criteria, service connectivity, policy, backup, telemetry, and user-visible behavior are validated.

## Dangerous answers

- "Crossplane replaces Terraform everywhere."
- "Git is the only source of truth."
- "The controller will eventually fix anything."
- "Namespaces provide complete tenant isolation."
- "Deletion is just the inverse of creation."
- "If apply fails, rerun it until it works."

## Whiteboard summary

```text
Outcome API
  -> policy
  -> versioned desired state
  -> one provisioning owner
  -> reconciliation
  -> explicit conditions
  -> runtime acceptance evidence

No competing writers
No global credentials
No blind retry or destroy
```

## Primary references

- Crossplane official documentation for current composite resources, managed resources, Compositions, composition functions, providers, and release changes.
- Kubernetes official documentation for custom resources, controllers, operators, admission, and multi-tenancy.
- HashiCorp official Terraform documentation for state, plans, applies, refresh-only operations, imports, and state recovery.
- OpenGitOps principles and official Argo CD or Flux documentation when those reconcilers are used.
