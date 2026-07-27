# Terraform State Integrity, Locking, Recovery, and Governance

This is the canonical, company-neutral chapter for Terraform state design and incidents. It separates the state model from backend-specific implementation, then adds current S3 locking guidance and a safe migration path from legacy DynamoDB locking.

## 1. Principal-level framing

Terraform state is not a disposable cache. It is the control plane's record of the binding between configuration addresses and real infrastructure objects.

```text
configuration address
        |
        v
state binding and metadata
        |
        v
provider object identity
        |
        v
real infrastructure
```

A blocked deployment is visible and inconvenient. Silent state corruption can cause Terraform to create duplicates, lose ownership, replace healthy resources, destroy the wrong object, or expose sensitive values.

The first operating rule is:

> Preserve state integrity before restoring delivery speed.

## 2. What state contains

State can contain:

- Resource addresses.
- Provider-specific object IDs.
- Instance keys from `count` and `for_each`.
- Dependency metadata.
- Provider configuration references.
- Computed attributes.
- Outputs.
- Sensitive values unless the architecture prevents them from entering state.
- State lineage and serial metadata.

State answers questions providers alone cannot reliably answer:

- Which remote object belongs to `module.network.aws_vpc.main`?
- Which instance key belongs to a specific `for_each` element?
- Which provider alias last managed the object?
- Which object must move when code is refactored?

## 3. State, plan, configuration, and dependency lock file

Do not confuse four different artifacts.

| Artifact | Purpose |
|---|---|
| Terraform configuration | Desired infrastructure and module logic |
| Terraform state | Bindings and metadata for managed remote objects |
| Saved plan | Proposed actions based on a configuration and prior-state snapshot |
| `.terraform.lock.hcl` | Selected provider versions and checksums |

The dependency lock file does not lock infrastructure state. State locking prevents competing writers; `.terraform.lock.hcl` makes provider installation reproducible.

## 4. Local and remote state

Local state is appropriate for disposable learning environments, but weak for team-operated production infrastructure.

A production remote backend should provide:

- Shared authoritative storage.
- Locking or serialized operations.
- Encryption in transit and at rest.
- Versioning or snapshot recovery.
- Fine-grained access control.
- Audit evidence.
- Durable availability.
- A documented break-glass procedure.

Do not store production state in Git. Version control does not provide Terraform state locking and may expose secrets.

## 5. Locking semantics

Terraform automatically attempts to lock state for operations that may write it when the selected backend supports locking.

The lock protects this sequence:

```text
acquire lock
  -> read latest state
  -> refresh and plan
  -> mutate remote infrastructure
  -> persist new state
  -> release lock
```

Without serialization, two writers can both read serial `N`, make independent changes, and then race to persist incompatible snapshots.

State locking does not solve every concurrency problem:

- Two separate state files can still manage the same remote object.
- A human can mutate infrastructure outside Terraform.
- A provider API can continue an asynchronous operation after the client dies.
- A CI system can enqueue stale plans.
- A state lock cannot coordinate an application-level database migration.

## 6. Lock failure taxonomy

### 6.1 Legitimate active writer

The apply is still running, paused, waiting on approval, retrying a provider API, or waiting for a long cloud operation.

Removing the lock permits split-brain writers.

### 6.2 Orphaned lock

The Terraform process died before releasing the lock because of:

- Runner termination.
- Laptop shutdown.
- Network loss.
- OOM kill.
- Pod eviction.
- Process crash.
- Canceled pipeline.
- Backend response failure.

### 6.3 Wrong backend, key, or workspace

The operator may be inspecting a different state than the failing job.

Confirm:

- Backend type.
- Storage location.
- State key or workspace path.
- Account, subscription, project, or tenant.
- Region.
- Assumed identity.
- Backend configuration supplied at initialization.

### 6.4 Permission failure

The client may be unable to read, create, or remove the lock. Treat access denial as an identity or policy incident, not proof of an orphaned lock.

### 6.5 Backend availability or throttling

State storage or the lock service may be unavailable, rate limited, partitioned, or misconfigured.

### 6.6 Infrastructure changed but state write failed

This is one of the most dangerous cases:

```text
provider API mutation succeeded
        |
        v
state persistence failed
        |
        v
remote reality is newer than authoritative state
```

The next run may propose duplicate creation, replacement, deletion, or import-like reconciliation.

### 6.7 Manual state mutation

Commands such as `state rm`, `state mv`, `import`, or `state push` change ownership metadata. Direct backend object replacement is even more dangerous.

### 6.8 Multiple pipelines share one state

Different repositories, branches, or environments may unknowingly target the same state location. This creates chronic contention and an unnecessarily large blast radius.

## 7. Production incident workflow

### Step 1 — Freeze competing writers

Pause every pipeline and scheduled job targeting the same state.

Record:

- Repository and commit.
- Pipeline and run ID.
- Workspace.
- Backend location.
- Execution identity.
- Terraform and provider versions.

Stop automatic retries while investigating.

### Step 2 — Capture evidence

Preserve:

- Exact lock error.
- Lock ID.
- Owner or runner identity.
- Operation type.
- Creation timestamp.
- State path.
- Backend errors.
- Provider logs.
- Cloud audit events.

Do not delete the lock record before capturing it.

### Step 3 — Confirm the actual backend

```bash
terraform version
terraform workspace show
terraform init -reconfigure
```

Also confirm the authenticated cloud identity and backend account. The local `.terraform` directory may contain initialized backend metadata; it is not the authoritative infrastructure state.

### Step 4 — Determine whether the original writer is alive

Check:

- CI job and runner state.
- Process, pod, or VM state.
- Approval gates.
- Terraform logs.
- Cloud audit activity from the writer identity.
- Provider-side asynchronous operations.

A job marked “canceled” is not enough proof. The process may still be terminating, and the provider-side change may still be progressing.

### Step 5 — Back up state securely

```bash
terraform state pull > state-backup-$(date +%Y%m%d-%H%M%S).json
```

Protect the backup as sensitive data. Also capture backend object version, generation, snapshot, or lease metadata where available.

### Step 6 — Verify lineage, serial, and inventory

Inspect without hand-editing:

```bash
jq '{lineage, serial, terraform_version}' state-backup-*.json
terraform state list
terraform state show <address>
```

Important concepts:

- **Lineage** distinguishes independently created state histories.
- **Serial** increases as state changes.

They help prevent some accidental overwrites but do not replace locking or operational review.

### Step 7 — Compare state with reality

Use a read-only or refresh-only plan when safe:

```bash
terraform plan -refresh-only
```

Look for:

- Objects changed remotely but not reflected in state.
- State entries whose remote objects no longer exist.
- Objects created by the failed apply but absent from state.
- Unexpected replacement caused by immutable attributes.
- Wrong account, region, or provider alias.
- Output changes that affect downstream states.

Do not jump directly from “unlock succeeded” to a normal apply.

### Step 8 — Force-unlock only with evidence

```bash
terraform force-unlock <LOCK_ID>
```

Use this only after proving:

1. The original writer is dead.
2. No provider operation is still controlled by that writer.
3. All competing writers are frozen.
4. The correct backend and state are confirmed.
5. State is backed up.
6. A reconciliation owner is assigned.

Force-unlock removes the lock. It does not repair state or infrastructure.

### Step 9 — Reconcile explicitly

Possible actions include:

- Refresh-only review.
- Configuration correction.
- `import` or `import` blocks for existing objects.
- `moved` blocks for refactoring.
- Carefully reviewed `state mv` or `state rm`.
- Provider-specific recovery.
- Restoring a backend object version only after proving it is the correct snapshot.

Create and review a saved plan:

```bash
terraform plan -out=recovery.tfplan
terraform show recovery.tfplan
```

Require explicit approval for deletion or replacement.

### Step 10 — Resume one writer

Re-enable one controlled execution path. Observe:

- Lock acquisition.
- State read.
- Refresh.
- Provider actions.
- State persistence.
- Lock release.

Only then restore normal delivery concurrency.

## 8. Why `-lock=false` is not incident recovery

```bash
terraform apply -lock=false
```

This removes the protection preventing competing writers. It should not be used to bypass a blocked production apply.

A strong interview answer is:

> I would rather delay an urgent change than replace a visible lock incident with silent state corruption.

## 9. Backend write failure and emergency local state

When Terraform cannot persist state to a remote backend after changing infrastructure, it may produce local recovery state to avoid losing the new bindings.

Response:

1. Freeze all writers.
2. Preserve the emergency state file and logs.
3. Pull the current remote state.
4. Compare lineage, serial, and resource inventory.
5. Compare both snapshots with real infrastructure.
6. Decide whether to push, import, move, or re-run under an approved recovery plan.
7. Never let another normal apply run first.

`terraform state push` can overwrite authoritative state and must be treated as a break-glass operation.

## 10. Restoring backend versions

Versioning is a safety net, not an automatic rollback mechanism.

Before restoring an older snapshot, prove:

- It belongs to the same lineage.
- Its serial and timeline are understood.
- It includes every successful infrastructure mutation that must remain owned.
- Newer snapshots are actually corrupt or incomplete.
- Restoring it will not orphan or duplicate resources.

The snapshot immediately before the incident may still be wrong if the provider mutation succeeded after that snapshot.

## 11. Current S3 backend locking

A current S3 backend can use a lock file in the same bucket as state:

```hcl
terraform {
  backend "s3" {
    bucket       = "company-terraform-state"
    key          = "platform/network/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
```

Conceptually:

```text
S3 state object:     platform/network/terraform.tfstate
S3 lock object:      platform/network/terraform.tfstate.tflock
```

The execution role needs read and write access to the state object and read, write, and delete access to the lock object. Scope permissions to the exact approved prefixes.

## 12. Legacy DynamoDB locking migration

DynamoDB-based S3 locking is deprecated. Existing estates may still use:

```hcl
terraform {
  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "platform/network/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-locks"
  }
}
```

A controlled migration should:

1. Inventory Terraform versions used by every writer.
2. Upgrade writers to versions supporting S3 lock files.
3. Freeze concurrent applies during the backend transition.
4. Configure both mechanisms temporarily when compatibility requires it.
5. Verify lock acquisition and release from the approved CI path.
6. Remove legacy writers.
7. Remove the deprecated DynamoDB configuration only after fleet compatibility is proven.
8. Retire the table through change control after audit and rollback windows expire.

Do not remove the lock table while older writers may still depend on it.

## 13. S3 backend hardening

Recommended controls:

- Bucket versioning.
- Encryption with appropriate key policy.
- Public-access block.
- TLS-only access.
- Least-privilege prefix access.
- Separate trust boundaries by account, bucket, or prefix.
- Audit logging for state and lock-object access.
- Retention sufficient for investigation and recovery.
- Break-glass role with strong authentication and review.
- Recovery tests.

State readers are privileged. State can contain credentials, tokens, connection strings, private data, or sensitive outputs even when CLI output marks values as sensitive.

## 14. Other backend patterns

The integrity model is backend-neutral even when mechanics differ.

Examples:

- Azure Blob Storage uses native blob locking behavior.
- Google Cloud Storage supports backend locking.
- HCP Terraform and Terraform Enterprise serialize runs and add workflow controls.
- Consul and other backends expose their own locking semantics.

For every backend document:

- What object stores state?
- What mechanism serializes writers?
- How is lock ownership identified?
- What is the recovery command?
- What snapshot or version history exists?
- Which permissions are required?
- What happens if infrastructure changes but state persistence fails?

## 15. State boundaries and blast radius

One enormous state creates:

- Large plans and refresh cost.
- Long lock hold times.
- Broad credentials.
- High contention.
- Wide failure and rollback domains.
- Coupled release schedules.

Too many tiny states create:

- Cross-state dependency sprawl.
- Output coupling.
- Operational overhead.
- Ordering problems.
- Difficult ownership discovery.

Choose boundaries by:

- Team ownership.
- Lifecycle and deployment cadence.
- Privilege boundary.
- Failure domain.
- Region and account.
- Data sensitivity.
- Expected change rate.

A useful rule:

> Resources that must change atomically may belong together; resources that require different credentials, owners, or failure domains should usually be separated.

## 16. Multi-account and multi-region design

Avoid one global state with unrestricted credentials across every account and region.

Prefer:

```text
bootstrap / organization state
  -> shared-network state
  -> regional platform states
  -> workload states
```

Each state should have:

- Explicit owner.
- Approved execution role.
- Unique backend key.
- Narrow output contract.
- Independent lock.
- Recovery runbook.
- Clear downstream consumers.

Use remote-state outputs sparingly. Published APIs, service catalogs, parameter stores, or explicit data sources may reduce hidden coupling.

## 17. Refactoring ownership safely

For configuration refactors, prefer declarative `moved` blocks when possible.

```hcl
moved {
  from = aws_instance.old
  to   = module.compute.aws_instance.main
}
```

Use imports for adopting existing remote objects into Terraform ownership.

Every ownership change should prove:

- Source and destination addresses.
- Remote object identity.
- Provider account and region.
- No second state still owns the object.
- The resulting plan contains no unintended create or destroy.

Two states managing the same object is a split-brain ownership bug even if both state files are internally valid.

## 18. Plan freshness and stale approvals

A saved plan is based on a particular configuration, provider set, variables, and prior-state snapshot. Long approval delays create risk:

- Infrastructure drifts.
- Another apply changes state.
- Credentials or policies change.
- Provider-side defaults change.
- The business intent changes.

CI should bind an apply to the reviewed commit and plan artifact, enforce plan expiry, and re-plan after material state change.

## 19. CI concurrency model

A mature pipeline provides more than backend locking.

Recommended controls:

- One logical writer queue per state.
- Concurrency key derived from canonical backend identity.
- Cancellation policy that does not kill an active apply blindly.
- Separate plan and apply identities when appropriate.
- Reviewed saved-plan artifact.
- Commit and module provenance.
- Provider version pinning.
- Policy checks for destructive actions.
- Short-lived cloud credentials.
- Audit trail for force-unlock and state mutation.

Backend locking is the final safety boundary, not the entire delivery orchestration system.

## 20. Drift and refresh governance

Drift can be:

- Authorized emergency change.
- Unauthorized human mutation.
- Cloud-service automatic behavior.
- Provider interpretation change.
- Resource recreation outside Terraform.
- Wrong-account execution.

Use scheduled read-only plans, inventory comparisons, and cloud audit logs. Do not automatically apply every drift correction; some changes require understanding which system is authoritative.

## 21. Sensitive data strategy

Treat state as highly sensitive.

Controls:

- Minimize secrets entering state.
- Prefer secret references over secret values where providers support it.
- Encrypt state and backups.
- Restrict read access as strongly as write access.
- Avoid printing state in CI logs.
- Sanitize incident artifacts.
- Rotate credentials exposed through a state leak.
- Define retention and destruction policy.

Marking an output `sensitive` hides normal display but does not remove the value from state.

## 22. Observability and audit

Track:

- Lock wait time.
- Lock failures.
- Apply duration and lock hold time.
- Backend read and write failures.
- Force-unlock events.
- State object version changes.
- Manual state command use.
- Plan age at apply time.
- Concurrent pipeline attempts.
- Drift size and age.
- Destructive action count.
- State size and refresh duration.

Alerting must include ownership and backend identity. “Terraform lock failed” without the state key and current writer is not actionable.

## 23. Prevention checklist

- Remote backend with locking enabled.
- Versioning or snapshots tested.
- State and lock access restricted by exact path.
- One CI writer queue per state.
- No routine human production apply.
- State boundaries aligned to ownership and failure domains.
- State backups protected as secrets.
- Force-unlock runbook with evidence requirements.
- Emergency state-write failure runbook.
- Declarative refactoring with `moved` and import blocks.
- Scheduled drift review.
- Stale-plan expiry.
- Audit of manual state mutations.
- Migration away from deprecated lock mechanisms planned and tested.

## 24. Ninety-second interview answer

> Terraform state is the control plane's ownership map between configuration addresses and real infrastructure, so I treat a lock incident as a state-integrity incident, not a reason to delete a lock quickly. First I freeze all writers targeting the exact backend key, capture the lock owner, operation, timestamp, pipeline, identity, and backend errors, and determine whether the original process or provider operation is still alive. I pull and protect the current state, verify lineage and serial, inspect backend version history, and compare state with reality using a refresh-only plan.
>
> I force-unlock only after proving the writer is dead, all competing writers are stopped, the correct state is backed up, and no asynchronous provider change is still progressing. Unlocking does not repair state, so I reconcile imports, moved addresses, failed writes, or drift and review a saved recovery plan before allowing one writer to resume.
>
> Structurally, I use a remote backend with encryption, versioning, narrow access, audit, and one CI concurrency queue per state. State boundaries follow ownership, credentials, lifecycle, and failure domain. On AWS I use current S3 lock-file support and migrate legacy DynamoDB locking carefully because older writers may still depend on it. I never use `-lock=false` to bypass a production apply blockage.

## 25. Adversarial follow-ups

1. How do you prove a lock is orphaned?
2. Why is a canceled CI job not enough proof?
3. What if the provider created a resource but the state write failed?
4. Why can restoring the previous state object be wrong?
5. What do lineage and serial protect, and what do they not protect?
6. When is `state push` justified?
7. Why does backend locking not prevent two states from managing one object?
8. How do you divide state without creating excessive cross-state coupling?
9. What is the difference between `.terraform.lock.hcl` and state locking?
10. How do you protect secrets already present in state?
11. How do you migrate from DynamoDB locks without allowing old writers to bypass locking?
12. Why can a saved approved plan become unsafe?
13. How would you design a break-glass state-recovery role?
14. Which metrics reveal that state size is becoming an operational problem?
15. How do you handle an urgent production change while the state backend is unavailable?

## Related canonical material

- [Consolidated curriculum map](../../curriculum-map.md)
- [Migration and ownership plan](../../MIGRATION_PLAN.md)
- [Distributed-systems partial failure and coordination module](../distributed-systems/README.md)
- [Linux observability and production debugging](../linux/06-observability-debugging.md)
