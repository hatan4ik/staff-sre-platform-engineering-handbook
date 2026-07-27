# Internal Developer Platform Architecture and Control Planes

## Why this exists

An Internal Developer Platform (IDP) converts developer intent into safe, observable, and supportable production outcomes. The architecture must do more than present a friendly interface. It must preserve durable state, enforce policy, coordinate asynchronous work, reconcile drift, expose progress, and fail without corrupting production.

A portal is one possible interface to the platform. It is not the platform itself.

## What the interviewer is testing

The interviewer wants to hear whether you understand:

- the difference between user experience, orchestration, provisioning, and runtime layers;
- which system is authoritative for each kind of state;
- synchronous requests versus asynchronous reconciliation;
- idempotency, retries, partial failure, drift, and rollback;
- platform control-plane blast radius;
- tenancy, security, and ownership boundaries;
- how to evolve the platform without creating a single organizational bottleneck.

## Reference architecture

```text
                       +----------------------+
Developer ------------> Portal / CLI / API   |
Git pull request ------> Product interfaces  |
                       +----------+-----------+
                                  |
                                  v
                       +----------------------+
                       | Intent and metadata  |
                       | catalog / API / Git  |
                       +----------+-----------+
                                  |
                                  v
                       +----------------------+
                       | Workflow orchestration|
                       | validation / approval |
                       | templates / events    |
                       +----------+-----------+
                                  |
                +-----------------+------------------+
                |                                    |
                v                                    v
      +----------------------+             +----------------------+
      | Provisioning plane   |             | Delivery plane       |
      | Terraform/Crossplane |             | CI/CD/GitOps         |
      +----------+-----------+             +----------+-----------+
                 |                                    |
                 +-----------------+------------------+
                                   v
                        +----------------------+
                        | Runtime and services |
                        | cloud / K8s / data   |
                        +----------+-----------+
                                   |
                                   v
                        +----------------------+
                        | Evidence and feedback|
                        | status/SLO/cost/audit|
                        +----------------------+
```

## Layer responsibilities

### 1. Product interface layer

Provides a consistent experience through one or more of:

- web portal;
- CLI;
- API;
- Git pull request;
- chat or automation integration.

It collects intent, validates basic input, shows status, and links users to evidence. It should not become the only place where state exists.

### 2. Catalog and metadata layer

Tracks entities such as:

- services;
- systems and domains;
- teams and owners;
- APIs and dependencies;
- runtime environments;
- data classification;
- SLO tier;
- lifecycle state;
- documentation and runbooks.

The catalog is a discovery and relationship system. It must not silently replace authoritative runtime, identity, or cloud state.

### 3. Workflow orchestration layer

Coordinates multi-step actions:

- repository creation;
- approval and policy evaluation;
- generation of declarative configuration;
- provisioning requests;
- deployment enrollment;
- catalog registration;
- notification and status aggregation.

Long-running workflows need durable execution records, idempotency keys, resumability, and compensation or reconciliation behavior.

### 4. Provisioning control plane

Creates and maintains infrastructure. Typical implementations include Terraform runners, Crossplane controllers, cloud-native deployment systems, or specialized service APIs.

The provisioning plane must define:

- desired-state ownership;
- locking or single-writer rules;
- drift policy;
- credentials and workload identity;
- failure recovery;
- deletion and retention policy;
- provider and API quota behavior.

### 5. Delivery control plane

Builds, verifies, promotes, deploys, and rolls back software. It may combine CI, artifact registries, policy, progressive delivery, and GitOps reconcilers.

It owns delivery mechanics, not application correctness.

### 6. Runtime plane

Includes Kubernetes clusters, serverless platforms, virtual machines, managed databases, messaging, networking, and edge services. Runtime failure domains should not be identical to platform control-plane failure domains.

### 7. Evidence plane

Returns:

- workflow status;
- resource conditions;
- deployment health;
- service SLOs;
- cost and quota data;
- policy decisions;
- audit events;
- ownership and support routing.

Without this loop, self-service becomes "submit and hope."

## Source-of-truth matrix

Define one authoritative owner for every state class.

| State | Typical authority | Replicas and views |
|---|---|---|
| Service ownership | versioned catalog metadata or identity directory | portal and dashboards |
| Infrastructure desired state | Terraform configuration/state or Kubernetes custom resource | portal status |
| Runtime actual state | cloud API or Kubernetes API | inventory and telemetry |
| Deployment desired state | GitOps repository or release system | portal |
| Artifact identity | artifact registry and provenance store | catalog |
| SLO definition | service configuration repository | dashboards |
| Approval decision | workflow/audit system | pull request and portal |

Two active writers for the same field create race conditions and unclear recovery.

## Request flow

Example: create a production service.

```text
1. User submits intent with an idempotency key.
2. Interface authenticates the user and resolves team ownership.
3. Policy validates allowed workload type, region, data class, and SLO tier.
4. Orchestrator records a durable workflow instance.
5. Repository and metadata are created or reconciled.
6. Provisioning desired state is committed or submitted.
7. Provisioning controller reconciles cloud resources.
8. Delivery controller builds and deploys a minimal service.
9. Evidence plane waits for explicit readiness conditions.
10. Catalog displays ownership, runtime, cost, SLO, and support links.
```

A successful API response should usually mean "request accepted and tracked," not "all infrastructure is complete."

## API design principles

Self-service interfaces should provide:

- stable versioned schemas;
- idempotent create and update operations;
- explicit lifecycle states;
- machine-readable conditions and errors;
- correlation IDs;
- cancellation semantics where possible;
- safe deletion with retention controls;
- immutable audit history;
- documented compatibility and deprecation policy.

Example lifecycle:

```text
Accepted -> Validating -> Provisioning -> Configuring -> Ready
                   |             |             |
                   +----------> Failed <-------+
                                  |
                           Retryable or terminal
```

## Reconciliation versus orchestration

Use orchestration when order and business workflow matter. Use reconciliation when continuously converging desired and actual state matters.

A robust design often uses both:

```text
Workflow creates versioned desired state
        -> controller reconciles it
        -> workflow observes conditions
        -> workflow completes when acceptance criteria are met
```

Do not implement a long series of cloud API calls inside a web request and call it a platform.

## Failure domains

Consider failures in:

- portal frontend;
- catalog backend;
- identity provider;
- workflow engine;
- Git provider;
- Terraform runner or Crossplane controller;
- GitOps reconciler;
- cloud provider API;
- policy engine;
- telemetry pipeline.

The portal being unavailable should not stop already-running workloads. A catalog outage should not remove runtime configuration. A provisioning control-plane outage should delay convergence, not delete resources.

## Blast-radius controls

- partition control planes by environment, tenant, account, or region where justified;
- use least-privilege identities per capability;
- separate read, plan, apply, and administrative permissions;
- impose quotas and concurrency limits;
- isolate provider credentials;
- canary new templates, policies, providers, and controllers;
- pin versions and test migrations;
- back up authoritative state;
- provide emergency stop and break-glass procedures;
- avoid one global workflow queue for unrelated critical paths.

## Security interpretation

The platform is a high-value control plane. Compromise can create repositories, credentials, infrastructure, or deployments across the estate.

Controls include:

- strong human and workload identity;
- short-lived credentials;
- authorization based on team and resource ownership;
- policy enforcement at multiple boundaries;
- signed and reviewed templates;
- restricted custom actions;
- secret redaction;
- immutable audit trails;
- protected deployment branches;
- separation of duties for high-risk operations;
- regular review of plugins, providers, and third-party actions.

## Observability and SLOs

Platform telemetry should answer:

- Which journey is failing?
- Which step owns the delay?
- Is failure isolated by tenant, region, template version, provider, or workload type?
- Is the system unavailable, slow, backlogged, or returning terminal policy errors?
- Can the user safely retry?

Useful SLIs:

- request acceptance availability;
- p50/p95/p99 time to ready by capability;
- reconciliation lag;
- workflow queue age;
- percentage of requests requiring manual intervention;
- retry and compensation rate;
- status freshness;
- control-plane error rate by dependency;
- successful deletion and recovery tests.

## Rollout strategy

1. Map one journey and its authoritative systems.
2. Introduce a thin interface over existing reliable automation.
3. Record durable workflow state and expose status.
4. Add policy and evidence before expanding scope.
5. Pilot with one workload class and one environment.
6. Measure failure and support patterns.
7. Partition risky control planes before broad adoption.
8. Add migrations, versioning, and deprecation before v2.

## 90-second interview answer

> I design an Internal Developer Platform as several explicit layers. The portal, CLI, API, or Git workflow captures intent; a catalog tracks ownership and relationships; a durable orchestrator handles ordered business steps; provisioning and delivery control planes reconcile infrastructure and software; the runtime remains independent; and an evidence plane returns status, SLO, cost, and audit data. I define one source of truth for each state type and avoid two active writers. Long operations are asynchronous, idempotent, resumable, and expose machine-readable conditions. I partition high-risk control planes, use short-lived least-privilege identities, canary templates and controllers, and make a portal outage harmless to running workloads. I measure request availability, time-to-ready, reconciliation lag, manual-intervention rate, and status freshness. The design goal is safe autonomy, not a single UI that hides a fragile chain of scripts.

## Adversarial follow-ups

### "Should the portal call Terraform directly?"

Not through a synchronous web request. The portal may submit a durable request to an orchestrator or create reviewed desired state. A controlled Terraform execution plane then plans, applies, records evidence, and handles locking and recovery.

### "Is Git always the source of truth?"

No. Git can be authoritative for declared configuration, but runtime actual state remains in the runtime API, identity may be authoritative elsewhere, and workflow execution state belongs in a workflow system.

### "How do you avoid the platform becoming a bottleneck?"

Provide stable APIs, decentralized ownership of approved extensions, clear support tiers, bounded customization, and automated policy. The central team should own the product contract, not manually approve every routine action.

## Dangerous answers

- "Everything goes through Backstage."
- "The portal database is our infrastructure source of truth."
- "A 200 response means provisioning succeeded."
- "Retries make workflows reliable."
- "One global admin role is simpler."
- "The platform can own every application decision."

## Whiteboard summary

```text
Intent -> validate -> durable workflow -> desired state
       -> reconcile -> observe conditions -> return evidence

One authority per state class
Independent runtime failure domain
Idempotent and resumable operations
Least privilege and bounded blast radius
```

## Primary references

- Kubernetes documentation for custom resources, controllers, operators, admission, and multi-tenancy.
- Backstage official architecture and feature documentation.
- Crossplane official managed-resource, composition, and function documentation.
- OpenGitOps principles and the official documentation for the selected delivery and provisioning tools.
