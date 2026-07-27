# GitOps, Reconciliation, and Progressive Delivery

This is the canonical, company-neutral chapter for GitOps operating models, Kubernetes reconciliation, promotion, rollback, secrets, multi-cluster delivery, and progressive release safety.

## 1. Principal-level framing

GitOps is not “put YAML in Git.” It is an operating model in which:

- Desired state is versioned and reviewed.
- An authenticated reconciler pulls approved artifacts.
- The reconciler compares desired and observed state.
- Drift is reported or corrected according to policy.
- Promotion, rollback, and evidence are explicit.

```text
reviewed desired state
        |
        v
versioned source or signed artifact
        |
        v
pull-based reconciler
        |
        v
cluster API
        |
        v
observed state and health
        |
        +----> status, events, metrics, alerts
```

The key design question is not:

> Argo CD or Flux?

It is:

> Which controller owns which resources, which changes may reconcile automatically, how is blast radius limited, and what evidence proves that the intended user outcome was achieved?

## 2. Separate build, promotion, and reconciliation

A reliable delivery system separates three concerns.

### Build

Produces immutable artifacts:

- Container image.
- Helm chart.
- OCI bundle.
- Kustomize base.
- Policy bundle.
- Machine image.

Build output should have provenance, digest, tests, and vulnerability results.

### Promotion

Changes which immutable artifact is approved for an environment.

Examples:

- Update image digest.
- Advance a release manifest.
- Merge an environment pull request.
- Promote an OCI artifact reference.

### Reconciliation

Makes observed cluster state converge toward the promoted desired state.

Do not let the deployment controller rebuild artifacts or resolve mutable tags during production reconciliation.

## 3. Source of truth

The source of truth must be explicit.

Possible sources:

- Git repository.
- OCI artifact registry.
- Object storage.
- Signed release manifest.

A source is trustworthy only when the pipeline also controls:

- Author identity.
- Review requirements.
- Branch protection.
- Artifact provenance.
- Commit or digest immutability.
- Secret handling.
- Audit retention.

Git records intent. It does not prove that the cluster is healthy.

## 4. Pull versus push

### Push model

```text
CI runner -> cluster credentials -> apply
```

Benefits:

- Simple mental model.
- Direct orchestration.
- Easy integration with existing CI.

Risks:

- CI holds broad cluster credentials.
- Drift may remain invisible between deployments.
- Failed runners can leave ambiguous state.
- Multi-cluster credentials become difficult to govern.

### Pull model

```text
controller in trusted environment -> fetch approved source -> reconcile locally
```

Benefits:

- CI does not require direct production-cluster credentials.
- Continuous drift detection.
- Reconciliation status is explicit.
- Cluster-local identity and RBAC can be narrow.

Risks:

- A bad commit can reconcile quickly.
- Controller compromise is powerful.
- Deletion and pruning are dangerous.
- Dependency ordering and secret delivery require design.
- Multi-controller ownership conflicts can create loops.

Pull is not automatically safer. Safety depends on source protection, controller permissions, rollout policy, and blast-radius controls.

## 5. Desired state and observed state

A reconciler repeatedly computes:

```text
diff = desired state - observed state
```

Possible outcomes:

- In sync and healthy.
- Out of sync but safe to apply.
- In sync but unhealthy.
- Reconciliation blocked by dependency.
- Apply failed.
- Health assessment failed.
- Drift intentionally ignored.
- Desired resource deleted and waiting for prune policy.

The distinction between synchronization and health is critical:

> A resource can exactly match Git and still fail customers.

## 6. Resource ownership

One resource should have one authoritative desired-state owner.

Common conflicts:

- Terraform and GitOps both manage the same Kubernetes object.
- Two GitOps applications include the same resource.
- Helm and Kustomize own overlapping fields.
- HPA modifies replicas while GitOps continually resets them.
- An operator owns fields also declared by the platform repository.
- Emergency `kubectl` changes are immediately reverted.

Create an ownership matrix:

| Resource or field | Authoritative owner | Allowed runtime actor |
|---|---|---|
| Namespace baseline | Platform GitOps app | Admission controller adds labels within contract |
| Deployment image | Application GitOps app | Rollout controller changes traffic, not image source |
| Deployment replicas | HPA | GitOps omits or ignores the runtime replica field |
| CRD | Platform lifecycle app | Operators consume the CRD |
| Secret value | External secret system | GitOps owns only reference and policy |
| Cloud load balancer | Cloud controller | GitOps owns Service intent, not provider-created child objects |

## 7. Repository topology

Common models:

### Application repository owns deployment manifests

Benefits:

- Application and deployment change together.
- Developer ownership is direct.

Risks:

- Production policy may be inconsistent.
- Promotion across environments can be harder to govern.

### Separate environment repository

Benefits:

- Clear production approvals.
- Environment-wide visibility.
- Promotion is explicit.

Risks:

- Additional pull requests and automation.
- Ownership split between app and platform teams.

### Generated environment repository

A promotion service updates environment declarations using immutable digests.

Benefits:

- Consistent promotion.
- Strong audit trail.

Risks:

- Generator becomes a critical control plane.
- Generated changes must remain reviewable.

Choose one model deliberately. Avoid invisible automation that edits Git without clear ownership.

## 8. Layering and dependencies

Typical order:

```text
cluster bootstrap
  -> CRDs and controllers
  -> platform namespaces and policies
  -> shared services
  -> application dependencies
  -> applications
  -> post-deployment verification
```

Dependencies should be explicit and minimal.

Mechanisms may include:

- Separate reconciliation units.
- Health checks.
- Declared dependencies.
- Sync phases or waves.
- Hooks or Jobs.

Do not encode one enormous global sequence. It creates a fleet-wide critical path and makes unrelated applications wait on one failure.

## 9. CRDs and controllers

CRD lifecycle is high risk because:

- Custom resources may exist across many namespaces.
- Schema changes can reject existing objects.
- Conversion webhooks can become availability dependencies.
- Deleting a CRD deletes or orphans its custom resources depending on behavior and recovery path.
- Controller and CRD versions must be compatible.

Safe pattern:

1. Install or upgrade CRD compatibility first.
2. Verify API discovery and conversion.
3. Upgrade controllers.
4. Verify custom-resource reconciliation.
5. Migrate stored versions when required.
6. Remove old versions only after inventory proves they are unused.

## 10. Pruning and deletion

Pruning removes objects no longer present in desired state. It is powerful and dangerous.

Failure modes:

- Repository path mistake appears as mass deletion.
- Generator produces an empty set.
- Branch or artifact fetch failure is interpreted incorrectly.
- Namespace deletion cascades to workloads.
- Finalizers block deletion indefinitely.
- Stateful resources are deleted before data migration.

Controls:

- Require explicit prune enablement.
- Protect critical namespaces and resources.
- Use deletion approval for high-risk objects.
- Test empty-output behavior.
- Separate stateful resources from rapidly changing app manifests.
- Alert on unusual deletion count.
- Preserve backups and restore evidence.

## 11. Self-healing and drift

Automated self-healing is appropriate when:

- Desired state is authoritative.
- Mutation is well understood.
- Reconciliation is reversible or low risk.
- Controller permissions are narrow.

Manual approval may be safer for:

- Destructive infrastructure changes.
- Stateful storage.
- CRD removal.
- Trust-bundle changes.
- Cluster-wide policy changes.
- Large fleet changes.

Classify drift:

- Unauthorized human mutation.
- Another controller's legitimate field ownership.
- Emergency break-glass change.
- Platform defaulting.
- Mutating admission behavior.
- Provider-generated status or child resources.

Do not “fix” drift until the intended owner is known.

## 12. Secrets in GitOps

Never assume base64 is encryption.

Common patterns:

- Encrypted secret manifests decrypted by the controller.
- External secret references resolved from a secret manager.
- CSI or agent-based runtime projection.
- Sealed or recipient-encrypted objects.

Evaluate:

- Who can decrypt?
- Where does plaintext exist?
- How are keys rotated?
- Can a pull request reveal secret values?
- How are secret references validated?
- What happens if the secret manager is unavailable?
- Does rollback reintroduce a revoked secret?

The preferred source repository often stores secret references and access policy, not long-lived plaintext values.

## 13. Multi-tenancy and RBAC

A multi-tenant GitOps control plane should constrain:

- Source repositories and paths.
- Target clusters.
- Target namespaces.
- Allowed resource kinds.
- Service accounts used for reconciliation.
- Cluster-scoped resource creation.
- Secret access.
- Impersonation behavior.

Avoid one fleet-wide controller with unrestricted cluster-admin permissions when tenants have different trust levels.

Partition by:

- Environment.
- Business domain.
- Trust boundary.
- Cluster fleet.
- Regulatory boundary.

## 14. Bootstrap and the root of trust

The GitOps controller itself must be installed somehow.

Bootstrap chain:

```text
cloud and cluster provisioning
  -> minimal identity and network
  -> controller installation
  -> source registration
  -> platform baseline reconciliation
  -> application reconciliation
```

Document:

- Who can change the bootstrap layer?
- How is the first controller credential established?
- How is source trust anchored?
- How can the controller be recovered if the repository is unavailable?
- How can reconciliation be paused safely?

Do not create a circular dependency where the broken controller is the only mechanism allowed to repair itself.

## 15. Promotion by immutable digest

Use immutable artifact references for production promotion.

```yaml
image: registry.example.com/payments@sha256:<digest>
```

Mutable tags can move without a Git change and break auditability.

Promotion should carry:

- Artifact digest.
- Source commit.
- Build identity.
- Test results.
- Vulnerability decision.
- Configuration version.
- Release owner.

## 16. Progressive delivery

Progressive delivery separates deployment from full exposure.

```text
reconcile new version
  -> verify readiness
  -> expose small traffic cohort
  -> evaluate SLIs
  -> expand or abort
```

Strategies:

- Canary.
- Blue/green.
- Ring deployment.
- Region or cluster waves.
- Tenant cohort.
- Feature flag.
- Shadow traffic.

The safest unit depends on the failure mode. A percentage-based canary may not detect failures isolated to one hardware generation, region, customer type, or data partition.

## 17. Rollout analysis

Do not promote using pod readiness alone.

Evaluate:

- Request success.
- Latency percentiles.
- Saturation and queueing.
- Dependency errors.
- Business transactions.
- Resource usage.
- Retry rate.
- Error-budget burn.
- Cohort-specific behavior.

Define:

- Analysis window.
- Minimum sample size.
- Baseline comparison.
- Abort threshold.
- Missing-data behavior.
- Maximum rollout duration.
- Manual override authority.

Missing telemetry should usually pause progression rather than be treated as success.

## 18. Readiness versus release safety

Kubernetes readiness answers:

> Should this endpoint receive traffic now?

It does not answer:

- Is the new version better than the old version?
- Are customers completing the transaction?
- Is a dependency retry storm beginning?
- Is only one tenant or region failing?
- Will memory leak after thirty minutes?

Use readiness for endpoint eligibility and rollout analysis for release decisions.

## 19. Database migrations

Database changes are often the hardest part of GitOps delivery.

Use expand-and-contract:

1. Add backward-compatible schema.
2. Deploy code that works with old and new schema.
3. Migrate data asynchronously.
4. Verify completion and correctness.
5. Remove old code paths.
6. Remove obsolete schema later.

Avoid a pre-sync migration that blocks every application rollout unless the migration is bounded, idempotent, observable, and safely retryable.

A failed database migration may not be reversible by reverting Git.

## 20. Rollback

Rollback means restoring a known safe operational state, not merely reverting a commit.

Possible actions:

- Revert desired-state change.
- Shift traffic to previous version.
- Disable a feature flag.
- Stop progression.
- Restore compatible configuration.
- Roll forward with a hotfix.
- Preserve irreversible data migration and redeploy compatible code.

A rollback plan must consider:

- Schema compatibility.
- Message compatibility.
- Cache and session state.
- Secret rotation.
- CRD version.
- Stateful workload identity.
- External API changes.

## 21. Reconciliation during incidents

During an incident, decide whether the controller helps or harms.

Options:

- Continue normal reconciliation.
- Suspend one application.
- Suspend one cluster or domain.
- Disable self-heal temporarily.
- Pin source revision.
- Apply an emergency change through the same source-of-truth path.
- Use audited break-glass mutation and immediately back-port it to desired state.

Do not stop every controller automatically. Unrelated controllers may be maintaining critical health.

## 22. Failure scenarios

### 22.1 Bad commit reconciles fleet-wide

Mitigation:

- Pause promotion.
- Bound affected clusters or waves.
- Revert or pin revision.
- Stop automated progression.
- Verify recovery through customer SLIs.

Prevention:

- Progressive fleet rings.
- Policy and schema checks.
- Environment canaries.
- Maximum-change and deletion guards.

### 22.2 Controller is healthy but applications do not update

Investigate:

- Source fetch and artifact revision.
- Repository credentials.
- Reconciliation queue.
- Application suspension.
- Dependency readiness.
- RBAC denial.
- Admission rejection.
- API server throttling.
- Health-assessment failure.

### 22.3 Application is in sync but customers fail

Investigate:

- Runtime health and business SLIs.
- Image digest.
- Config and secret versions.
- Dependency behavior.
- Traffic routing.
- Cohort differences.

“In sync” is not “successful.”

### 22.4 Manual repair keeps reverting

This indicates the GitOps controller remains authoritative. Either:

- Repair desired state.
- Suspend the correct reconciliation unit.
- Use the documented break-glass process.

Do not repeatedly fight the controller with `kubectl`.

### 22.5 Source repository unavailable

Already-applied resources normally continue running, but:

- New reconciliation stops.
- Drift is not corrected.
- Emergency desired-state changes cannot be fetched.
- Bootstrap and new clusters may fail.

Define acceptable source-unavailability duration and recovery sources.

## 23. Multi-cluster fleet delivery

Avoid one unbounded fleet-wide reconciliation blast radius.

Use:

```text
fleet
  -> environment
  -> region
  -> cluster ring
  -> namespace or application
```

Design for:

- Independent pause and rollback.
- Per-cluster health.
- Version skew.
- Disconnected or delayed clusters.
- Cluster-specific overrides.
- Regional dependencies.
- Maximum concurrent change count.

A central control plane should not require every cluster to be reachable for healthy clusters to continue reconciling.

## 24. Observability

### Source and artifact

- Fetch success and latency.
- Observed revision.
- Signature or provenance validation.
- Artifact age.

### Reconciliation

- Queue depth.
- Reconciliation duration.
- Success and failure rate.
- Apply errors.
- Health-check failures.
- Dependency-blocked time.
- Drift count.
- Prune count.
- Suspended resources.

### Delivery

- Commit-to-reconcile time.
- Reconcile-to-ready time.
- Ready-to-full-traffic time.
- Rollback frequency.
- Change failure rate.
- Cohort SLI difference.
- Error-budget burn during rollout.

### Governance

- Manual production mutations.
- Break-glass duration.
- Stale exceptions.
- Controller permission breadth.
- Mutable-tag usage.
- Unsigned artifact usage.

## 25. SLOs

Example SLOs:

- 99% of approved desired-state changes begin reconciliation within 2 minutes.
- 99% of low-risk changes reach healthy state within 10 minutes.
- 100% of production image references use immutable digests.
- 99.9% of reconciliations do not require manual intervention.
- Critical drift is detected within 5 minutes.
- Fleet rollout can be paused within 2 minutes.

Use different SLOs for low-risk application updates and high-risk platform or CRD changes.

## 26. Security model

Protect:

- Source repository.
- Artifact registry.
- Controller service account.
- Cluster API access.
- Secret decryption keys.
- Webhooks and notifications.
- Promotion automation.

Controls:

- Short-lived or workload identity.
- Narrow namespace and resource permissions.
- Signed commits or artifacts where required.
- Admission policy.
- Protected branches.
- Required reviews.
- Audit logs.
- Separate tenant controllers or impersonated identities.

## 27. Adoption strategy

1. Inventory current deployers and resource ownership.
2. Select a low-risk application.
3. Establish immutable artifacts and repository conventions.
4. Install controller with narrow permissions.
5. Run in observe or manual-sync mode.
6. Compare desired and observed state.
7. Enable automated reconciliation without prune.
8. Add health checks and rollback.
9. Enable pruning selectively.
10. Add progressive rollout and fleet rings.
11. Remove old push deployer credentials.
12. Measure lead time, failures, drift, and recovery.

## 28. Argo CD and Flux mapping

The architecture is tool-neutral, but common mappings include:

| Capability | Argo CD concept | Flux concept |
|---|---|---|
| Reconciliation unit | Application | Kustomization or HelmRelease |
| Desired source | Git, Helm, or supported source | GitRepository, OCIRepository, Bucket, HelmRepository |
| Automated convergence | Automated sync and self-heal options | Reconciliation interval and controllers |
| Ordering | Sync phases and waves | `dependsOn`, health checks, separate Kustomizations |
| Pause | Disable or alter automated sync / application control | Suspend reconciliation |
| Drift correction | Self-heal | Continuous reconciliation |
| Deletion | Prune policy | Prune and garbage collection |

Do not force identical operating models across tools. Standardize outcomes, ownership, security, and evidence.

## 29. Ninety-second interview answer

> I treat GitOps as a reconciliation operating model, not a repository layout. CI builds and signs immutable artifacts, promotion updates the approved digest, and a pull-based controller reconciles that desired state using narrow cluster-local identity. Git is evidence of intent; controller status, Kubernetes health, and customer SLIs prove the outcome.
>
> The first design rule is one authoritative owner per resource and field. Terraform owns cloud infrastructure, GitOps owns selected Kubernetes manifests, and runtime controllers such as HPA or operators own explicitly delegated fields. I separate bootstrap, CRDs, platform services, and applications into bounded reconciliation units with health-based dependencies rather than one global sequence.
>
> Automated sync, self-heal, and pruning are enabled according to risk. Fleet rollout proceeds through environment, region, and cluster rings with immutable digests, SLI-based analysis, pause thresholds, and rollback that accounts for databases, messages, secrets, and CRDs. During incidents I can suspend only the affected reconciliation domain, preserve evidence, and recover through the source-of-truth path or an audited break-glass process. Success is measured by reconciliation latency, drift detection, change failure rate, rollback time, and user-facing SLOs—not by an “in sync” badge.

## 30. Adversarial follow-ups

1. Why is Git not enough to prove deployment success?
2. When should self-heal be disabled?
3. How do HPA and GitOps avoid fighting over replicas?
4. How do you prevent an empty generated manifest set from deleting production?
5. How do you bootstrap the GitOps controller without circular dependency?
6. What happens when Git is unavailable?
7. How do you roll back an irreversible database migration?
8. Why can an application be in sync but unhealthy?
9. How do you limit one bad commit to one fleet ring?
10. How do you transfer ownership from CI push deployment to GitOps?
11. How do you secure secret decryption in a multi-tenant controller?
12. How do you upgrade CRDs safely?
13. What should missing rollout telemetry do?
14. When are sync waves or dependencies becoming an anti-pattern?
15. How do you prove GitOps improved reliability rather than merely adding controllers?

## Related canonical material

- [Infrastructure as Code tool selection and governance](../infrastructure-as-code/tool-selection-and-governance.md)
- [Terraform state integrity and recovery](../infrastructure-as-code/terraform-state-integrity.md)
- [Distributed systems and control-loop reasoning](../distributed-systems/README.md)
- [Service mesh control-plane and data-plane design](../service-mesh/README.md)
- [Migration and ownership plan](../../MIGRATION_PLAN.md)
