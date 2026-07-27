# Multi-Cluster Fleet Architecture, Lifecycle, and Progressive Rollout

## Why this exists

A platform with many Kubernetes clusters is not a collection of independently administered snowflakes. It is a fleet with declared cluster classes, lifecycle states, compatibility contracts, rollout rings, failure-domain boundaries, and evidence-driven operations.

The central challenge is not creating cluster number one. It is keeping cluster number 100 consistent, upgradeable, recoverable, and safe when the fleet control plane itself is wrong.

## What the interviewer is testing

A Staff or Principal candidate should be able to:

- explain why an organization needs multiple clusters rather than one large cluster;
- define cluster classes and avoid per-team snowflakes;
- separate cluster lifecycle, add-on delivery, and application delivery control planes;
- choose centralized, regional, or per-cluster GitOps topology;
- design progressive fleet rollouts, compatibility gates, and rollback;
- operate Cluster API or managed-service automation without confusing reconciliation with safety;
- handle management-cluster failure, provider upgrades, API deprecations, and credential rotation;
- measure fleet health through convergence and user outcomes rather than cluster count.

## Why multiple clusters

Valid reasons include:

- regulatory, data-residency, or sovereignty boundaries;
- mutually untrusted tenants;
- regional latency and availability;
- independent upgrade or extension requirements;
- workload classes with different kernel, GPU, networking, or cost needs;
- containment of cluster-wide add-ons, admission, CRDs, or control-plane load;
- disaster recovery;
- acquisition or business-unit isolation;
- edge or disconnected environments.

Weak reasons include organizational preference, one cluster per microservice, or avoiding the work of multi-tenancy without understanding fleet cost.

Every cluster adds:

- control-plane and add-on cost;
- patch and upgrade obligations;
- identity and certificate lifecycle;
- observability and backup coverage;
- quota and capacity management;
- GitOps and policy fan-out;
- incident and recovery paths;
- version-skew testing.

## Cluster classes

Define a small catalog of supported cluster products.

Example:

```text
shared-standard
  Internal cooperative teams, default add-ons, standard SLO.

shared-restricted
  Stronger policy, dedicated node classes, tighter egress.

regulated-dedicated
  Separate account/project, keys, audit, and maintenance windows.

build-ephemeral
  Short-lived CI workloads, aggressive scale-down, no stateful services.

edge-disconnected
  Intermittent connectivity, local autonomy, delayed convergence.
```

Each class should declare:

- tenant and threat model;
- supported Kubernetes minor versions;
- cloud regions and infrastructure provider;
- network, DNS, ingress, storage, and identity patterns;
- required add-ons and versions;
- workload types and forbidden capabilities;
- upgrade cadence and maximum version skew;
- backup, restore, and replacement strategy;
- SLO, support tier, cost model, and owner;
- lifecycle and deprecation policy.

A request for a new class requires a materially different contract, not merely a preference for another tool.

## Fleet control-plane layers

```text
Cluster product API and inventory
            |
            v
Cluster lifecycle control plane
(Cluster API / managed-service automation / Terraform)
            |
            v
Bootstrap and baseline control plane
(identity / CNI / CSI / DNS / policy / observability / GitOps agent)
            |
            v
Fleet add-on delivery
(regional or central GitOps controllers)
            |
            v
Application delivery
(team or platform-owned deployment controllers)
            |
            v
Evidence and fleet decision engine
(version / conditions / SLO / cost / policy / rollout state)
```

These layers must have explicit ownership. The tool that creates a cluster should not silently become the owner of every application inside it.

## Fleet inventory

A trustworthy fleet inventory records:

```yaml
clusterId: prod-us-east-1-017
clusterClass: shared-standard
lifecycleState: Active
region: us-east-1
provider: aws
kubernetesVersion: v1.xx.y
controlPlaneOwner: platform-cluster-lifecycle
workloadOwners:
  - payments
  - orders
rolloutRing: production-2
maintenanceWindow: Sunday-04:00Z
createdFromVersion: cluster-template-v12.4.0
baselineVersion: baseline-v31.2.1
policyVersion: policy-v18.0.0
lastConformancePass: 2026-07-26T09:00:00Z
replacementDeadline: 2027-01-15
```

Inventory should come from authoritative lifecycle and runtime APIs, not a manually edited spreadsheet.

## Lifecycle states

Use a state machine rather than an `active: true` label.

```text
Requested
  -> Provisioning
  -> Bootstrapping
  -> ConformanceTesting
  -> Active
  -> UpgradeScheduled
  -> Upgrading
  -> Active
  -> Draining
  -> Decommissioning
  -> Deleted

Any stage may enter Degraded, Quarantined, or Failed.
```

Each state needs:

- allowed operations;
- owner;
- entry and exit conditions;
- timeout;
- retry policy;
- rollback or replacement path;
- user-visible status;
- audit evidence.

## Cluster API operating model

Cluster API (CAPI) provides Kubernetes-style declarative APIs and controllers for cluster creation, scaling, upgrading, and deletion across infrastructure providers.

A typical management cluster runs:

- core Cluster API controllers;
- infrastructure provider controllers;
- bootstrap provider controllers;
- control-plane provider controllers;
- optional add-on or topology controllers.

Workload clusters are represented through resources such as `Cluster`, control-plane objects, Machines, and MachineDeployments.

Current-version discipline matters. The current Cluster API documentation uses newer API contracts while older examples remain widespread. In the current support schedule, `v1beta2` is supported and `v1beta1` is deprecated, with removal planned in a later CAPI release. Provider and management-cluster upgrades must therefore include stored-object and manifest migration checks.

CAPI is not automatically the best choice when:

- the managed cloud service already exposes a safer and simpler organization-wide lifecycle API;
- the team cannot operate a privileged management cluster and multiple providers;
- the desired platform spans resources CAPI intentionally does not own;
- existing clusters cannot be adopted safely;
- cluster replacement is easier than introducing another reconciliation plane.

## Management-cluster risk

The management cluster can create, mutate, upgrade, and delete workload clusters. Treat it as a high-value control plane.

Controls:

- separate production and non-production management planes;
- narrow provider credentials by account, region, and cluster class;
- protect CAPI and provider CRDs, webhooks, and controllers;
- restrict `clusterctl`, provider, and infrastructure-resource access;
- back up management-cluster state and provider-specific recovery data;
- test management-cluster restoration;
- canary provider and CAPI upgrades;
- monitor reconciliation queues, errors, and API throttling;
- use deletion protection and approval for production clusters;
- prevent tenant workloads from running in the management cluster.

A management-cluster outage should pause convergence. It should not stop healthy workload clusters.

## Cluster creation flow

```text
1. User or automation submits a cluster product request.
2. Policy selects a supported class, region, account, and version.
3. Lifecycle plane records durable desired state and idempotency key.
4. Infrastructure and control plane reconcile.
5. Bootstrap installs minimal identity and GitOps access.
6. Baseline add-ons reconcile in dependency order.
7. Conformance suite validates API, DNS, network, storage, identity, policy, telemetry, and failure-domain placement.
8. Fleet inventory marks the cluster Active only after acceptance criteria pass.
9. Application placement becomes eligible.
```

Cloud API success or a reachable API server is not sufficient for `Active`.

## Bootstrap problem

A new cluster needs enough capability to receive the rest of its desired state.

Keep the bootstrap layer small:

- cluster identity and workload identity prerequisites;
- CNI or provider-required networking;
- DNS;
- minimal certificate and trust configuration;
- GitOps agent or secure registration mechanism;
- baseline policy needed to protect the bootstrap process;
- telemetry required to diagnose bootstrap.

Do not embed the entire platform stack in opaque bootstrap scripts. Move stable desired state into a reconciled delivery plane as early as possible.

## GitOps fleet topologies

### Centralized control plane

One or a few controllers manage many remote clusters.

Benefits:

- centralized policy and visibility;
- fewer controllers;
- consistent credentials and version management;
- easy global inventory.

Risks:

- broad credentials and blast radius;
- controller or regional outage affects many clusters;
- network dependency from controller to remote APIs;
- queue and reconciliation scaling;
- tenant isolation and project-boundary complexity.

### Per-cluster pull agents

Each cluster pulls its own desired state.

Benefits:

- failure isolation;
- cluster-local reconciliation during central network disruption;
- narrow credentials;
- natural regional or edge operation.

Risks:

- many controllers to upgrade;
- fragmented status and policy;
- bootstrap and registration complexity;
- inconsistent agent versions;
- harder fleet-wide emergency control.

### Regional or cell-based controllers

A middle ground partitions clusters into bounded cells.

```text
Global intent and release metadata
    -> regional fleet controller
        -> 20-100 clusters in a cell
```

This limits blast radius while preserving centralized product behavior.

## Argo CD ApplicationSet

ApplicationSet can generate Argo CD `Application` resources from cluster inventory, Git, lists, matrices, merges, and other generators. The Cluster generator uses clusters registered in Argo CD and can select them by labels.

Important boundary: ApplicationSet creates and reconciles `Application` objects. Argo CD performs the actual deployment to target clusters.

Security considerations:

- cluster registration secrets are privileged inventory and credentials;
- label changes can alter deployment targets;
- templated projects, repositories, paths, and destinations must be constrained;
- generator input is part of the release authorization boundary;
- deletion behavior must be tested;
- developers should not gain arbitrary destination or project selection through templating.

## Fleet rollout rings

Never update every cluster simultaneously.

Example rings:

```text
ring-0: disposable integration clusters
ring-1: platform development and test
ring-2: internal non-critical production
ring-3: representative production canaries
ring-4: broader production cells
ring-5: regulated, edge, or special-window clusters
```

Each ring should be representative enough to reveal relevant failures. A tiny test cluster with no real policies or traffic is not a production canary.

## Rollout decision model

```text
Candidate version
  -> static and compatibility tests
  -> disposable cluster creation
  -> upgrade and rollback rehearsal
  -> ring-0 rollout
  -> soak and SLO gate
  -> ring-1 and ring-2
  -> production canary cells
  -> progressive production batches
  -> special fleets
```

Gate on:

- cluster lifecycle success rate;
- API and etcd latency where visible;
- node readiness and replacement time;
- DNS, network, storage, ingress, and identity conformance;
- admission latency and policy errors;
- add-on health and reconciliation lag;
- application golden signals and protected cohort SLOs;
- support and incident rate;
- rollback viability.

A green controller condition is not enough.

## Compatibility matrix

Maintain a tested matrix for:

```text
Kubernetes version
x cloud provider and region
x node image and kernel
x CNI
x CSI
x ingress/gateway
x service mesh
x policy engine
x observability agents
x autoscaler/node provisioner
x workload runtime classes
```

The supported matrix should be smaller than the theoretically possible matrix.

## Upgrade strategy

Prefer:

- one minor version step at a time unless the provider explicitly supports otherwise;
- control plane before nodes where required by the platform;
- surge or replacement-based node rotation;
- PodDisruptionBudget and topology validation;
- drain timeout and stuck-pod policy;
- preflight checks for deprecated APIs and removed features;
- backup and restore verification;
- canary clusters and bounded concurrency;
- automatic pause on evidence failure;
- documented abort and replacement path.

An upgrade is complete only when workload SLOs, add-ons, and conformance recover.

## Replace versus repair

Clusters should be replaceable, but not every incident requires immediate replacement.

Replace when:

- control-plane or infrastructure integrity is uncertain;
- configuration drift is too large to reason about;
- the cluster is outside supported versions;
- recovery is slower or riskier than creating a known-good replacement;
- security compromise affects trust roots or cluster-wide identity.

Repair when:

- stateful data or external dependencies make migration riskier;
- the failure is isolated and reversible;
- replacement capacity or quota is unavailable;
- the cluster hosts workloads that cannot move within RTO.

The platform should continuously improve toward replacement, but should not pretend stateful migration is free.

## Decommission flow

```text
1. Stop new workload placement.
2. Inventory workloads, data, identities, DNS, load balancers, certificates, and external dependencies.
3. Migrate or retire applications.
4. Validate traffic and data cutover.
5. Revoke cluster and workload credentials.
6. Remove GitOps registration and fleet targets.
7. Retain required audit and backup evidence.
8. Drain and delete infrastructure under deletion protection.
9. Verify cloud resources, IPs, volumes, snapshots, DNS, and keys are handled.
10. Mark the inventory record Deleted; do not erase history.
```

## Failure modes

- a fleet label change targets every production cluster;
- a bad baseline add-on blocks API admission fleet-wide;
- provider upgrade breaks CAPI reconciliation;
- management-cluster credentials expire during an upgrade;
- GitOps pruning deletes shared or lifecycle-owned resources;
- node-image rollout combines kernel, Kubernetes, and CNI changes;
- cluster deletion leaves volumes, load balancers, DNS, or identities;
- fleet status is green while application traffic fails;
- rollback requires an image or chart that was garbage-collected;
- edge clusters miss multiple releases and exceed supported skew;
- one central controller exhausts API or SCM rate limits.

## Incident response

For a harmful fleet rollout:

1. Stop promotion and preserve controller, Git, API, cloud, and cluster evidence.
2. Identify exact candidate versions, rings, clusters, and affected workload cohorts.
3. Separate rollout-controller health from cluster and application health.
4. Pause or revert the narrow fleet selector or release pointer.
5. Protect unaffected rings from automatic convergence to the bad version.
6. Roll back or replace canary clusters first to validate recovery.
7. Expand recovery in bounded batches.
8. Confirm external user SLIs and cluster conformance.
9. Repair rollout gates, compatibility fixtures, and deletion or rollback assumptions.

Avoid manually editing every cluster; this creates untracked divergence and slows recovery.

## Fleet observability and SLOs

Useful fleet SLIs:

- cluster-request acceptance availability;
- p95 request-to-Active time by class and provider;
- percentage of clusters within supported Kubernetes and baseline versions;
- fleet convergence lag;
- lifecycle-controller queue age and reconciliation errors;
- upgrade success and rollback rate;
- conformance pass rate;
- clusters with stale or unknown status;
- time to quarantine a cluster or rollout ring;
- time to replace a cluster;
- add-on and policy version skew;
- cost per active cluster and per supported workload;
- application SLO regression caused by fleet changes.

## 90-second interview answer

> I treat multiple Kubernetes clusters as a product fleet, not as independent snowflakes. I define a small number of cluster classes with explicit tenant, version, network, identity, add-on, SLO, cost, and lifecycle contracts. I separate cluster lifecycle from baseline add-on delivery and application delivery. The lifecycle control plane may use Cluster API, managed-service APIs, or Terraform, but it must expose durable states, idempotency, conditions, and a replacement path. A cluster becomes Active only after DNS, network, storage, identity, policy, telemetry, and workload conformance pass. For GitOps, I choose centralized, per-cluster, or regional cell topology based on credential and outage blast radius. Fleet changes move through representative rollout rings with compatibility and application-SLO gates, automatic pause, and tested rollback. I protect the management plane, constrain cluster selectors, track version skew, and measure request-to-Active time, convergence lag, conformance, upgrade success, quarantine time, and user impact.

## Adversarial follow-ups

### "Why not one cluster per team?"

That may simplify some isolation, but it creates lifecycle, cost, policy, and version obligations for every team. I create separate clusters only for materially different trust, regulation, lifecycle, performance, or failure-domain needs.

### "Why not one central Argo CD for all clusters?"

It can work at moderate scale, but its credentials, network path, queue, and configuration become a broad blast radius. Regional cells or per-cluster agents may provide safer boundaries.

### "Does Cluster API solve cluster upgrades?"

It provides declarative lifecycle APIs and controllers. The platform still owns provider compatibility, rollout rings, workload disruption, add-on skew, conformance, rollback, and management-plane recovery.

### "How do you recover the management cluster?"

Restore authoritative desired state and provider data into a tested replacement management plane, re-establish credentials carefully, and ensure only one active reconciler owns the workload-cluster resources.

## Dangerous answers

- "Kubernetes clusters are cattle, so we can always delete them."
- "ApplicationSet makes multi-cluster deployment safe automatically."
- "A successful control-plane upgrade means the rollout succeeded."
- "All clusters should run the latest version immediately."
- "One global controller is simpler, so it is more reliable."
- "The management cluster can host tenant workloads to save money."

## Whiteboard summary

```text
Cluster classes
  -> lifecycle control plane
  -> minimal bootstrap
  -> baseline GitOps
  -> conformance
  -> Active inventory
  -> rollout rings
  -> SLO gates
  -> replace, repair, or decommission
```

## Primary references

- Cluster API official book, concepts, provider contracts, version-support policy, and upgrade documentation.
- Kubernetes version-skew, API deprecation, disruption, and cluster-administration documentation.
- Argo CD ApplicationSet official generators, cluster generator, security, and deletion documentation.
- Flux official fleet, multi-tenancy, bootstrap, and reconciliation documentation when Flux is used.
- Official managed Kubernetes service lifecycle, upgrade, backup, identity, networking, and quota documentation for each provider.
