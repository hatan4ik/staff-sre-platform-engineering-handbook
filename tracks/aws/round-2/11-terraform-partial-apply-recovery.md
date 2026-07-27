# Question 11 — Terraform Apply Fails Midway and Leaves Partial AWS Infrastructure

## Interview prompt

A Terraform deployment fails midway, leaving AWS resources partially provisioned. How do you recover while preventing infrastructure drift?

## Required prerequisite

Read the deeper state chapter first:

- [`../round-1/03-terraform-state-multi-account-region.md`](../round-1/03-terraform-state-multi-account-region.md)

This chapter focuses on the incident answer and recovery decision tree.

---

## 90-second Staff/Principal answer

> I treat a partial Terraform apply as a control-plane integrity incident. I stop all writers for the exact state, preserve the failed job logs and lock metadata, confirm the AWS account, Region, backend key, workspace, provider version, and identity, and determine which resource operations actually completed.
>
> I back up the current state and S3 object version, inspect CloudTrail and service-side operation status, and run a read-only refresh-oriented plan to compare configuration, Terraform state, and real AWS resources. I do not immediately rerun apply, delete resources manually, use `-lock=false`, or restore an older state version.
>
> For each partial resource I choose an explicit reconciliation action: import a successfully created object, fix configuration and continue, remove a state entry only when Terraform should relinquish a genuinely absent object, or deliberately destroy an orphan after dependency and data review. I review all replacement and deletion actions before a single controlled apply.
>
> After recovery I restore one writer, verify state write and lock release, run drift detection, and fix the systemic cause—pipeline serialization, quota prechecks, provider pinning, state partitioning, idempotent modules, or better rollback and import runbooks.

---

## 1. Understand what “failed midway” means

Terraform walks a dependency graph and performs operations concurrently when dependencies allow it.

At failure time, the environment may contain:

- resources created and written to state
- resources created but not written to state
- resources modified but state still reflects old attributes
- resources deleted but state still contains them
- operations still running asynchronously in AWS
- resources created by a provider after the client timed out
- a valid or orphaned state lock
- outputs that are stale or incomplete

The terminal error is not a complete inventory of what happened.

---

## 2. Immediate containment

### Freeze all writers

Stop:

- CI retries
- scheduled applies
- local engineer sessions
- dependent pipelines that could mutate the same resources
- drift-remediation automation that competes with Terraform

Identify the exact state identity:

```text
repository
commit SHA
pipeline run
AWS account
AWS Region
assumed role
backend bucket
backend key
workspace
Terraform version
provider lock file
```

### Preserve evidence

Capture:

- full stdout/stderr and debug logs where safely enabled
- saved plan and checksum, if used
- lock ID or lockfile
- S3 current object version
- state serial and lineage
- CloudTrail events
- service-specific operation status
- timestamps in UTC

Do not destroy the failed runner until local artifacts are preserved.

---

## 3. Confirm the backend and identity

```bash
aws sts get-caller-identity
terraform version
terraform workspace show
terraform init -reconfigure
```

Inspect backend configuration and pipeline variables.

Common incident cause:

```text
operator believes this is staging/us-east-1
but backend or provider targets production/us-west-2
```

Do not run repair commands until account, Region, and state key are proven.

---

## 4. Determine whether the lock is legitimate

A lock can remain because:

- the Terraform process is still running
- the runner UI says canceled but the process is terminating
- a provider operation is still being polled
- the process died before release
- backend permissions prevent lock deletion

Check:

- runner, pod, VM, and process state
- CI job and cancellation status
- CloudTrail activity from the deployment role
- provider-side operation state
- lock creation time and owner

Only force-unlock after proving the original writer is dead and all competing writers are frozen.

Never use:

```bash
terraform apply -lock=false
```

as a production unblocking method.

---

## 5. Back up state before repair

```bash
terraform state pull \
  > state-backup-$(date -u +%Y%m%dT%H%M%SZ).json
```

List S3 object versions:

```bash
aws s3api list-object-versions \
  --bucket <state-bucket> \
  --prefix <state-key>
```

Protect backups because state may contain sensitive values.

Record:

- object version ID
- ETag
- last modified
- state serial
- lineage
- resource count

An older S3 version is recovery evidence, not automatically the correct state to restore.

---

## 6. Build the operation inventory

Create a table from Terraform logs, state, CloudTrail, and AWS service APIs.

| Terraform address | Intended operation | AWS result | In state? | Dependencies | Recovery decision |
|---|---|---|---:|---|---|
| `aws_iam_role.app` | create | created | yes | none | keep |
| `aws_eks_node_group.blue` | update | still updating | yes, old attrs | launch template | wait and reconcile |
| `aws_lb_target_group.api` | create | created | no | VPC | import |
| `aws_security_group_rule.db` | create | denied | no | SG | fix policy and continue |
| `aws_route.cutover` | replace | old deleted, new failed | uncertain | TGW | incident mitigation first |

This inventory prevents blanket actions.

---

## 7. Compare configuration, state, and reality

There are three sources to reconcile:

```text
configuration: what should exist
state: what Terraform believes it owns
AWS APIs: what actually exists
```

Use a refresh-only plan when safe:

```bash
terraform plan -refresh-only -out=refresh.tfplan
terraform show refresh.tfplan
```

Important distinction:

- `terraform plan -refresh-only` previews state reconciliation.
- applying a refresh-only plan changes state, not remote resources.
- do not apply refresh-only automatically before reviewing whether external changes are intended.

Then create a normal plan:

```bash
terraform plan -out=recovery.tfplan
terraform show recovery.tfplan
```

Review every create, update, replace, and destroy action.

---

## 8. Reconciliation actions

### Case A — Resource created and present in state

If configuration and real resource are correct, no special action may be needed.

Verify dependencies and continue through a reviewed plan.

### Case B — Resource created in AWS but absent from state

Import it when Terraform should own it.

Modern configuration-driven import example:

```hcl
import {
  to = aws_lb_target_group.api
  id = "arn:aws:elasticloadbalancing:...:targetgroup/api/..."
}
```

Or controlled CLI import:

```bash
terraform import aws_lb_target_group.api <resource-id>
```

Before import:

- write matching configuration
- verify resource identity
- confirm no other state owns it
- protect against unintended replacement

### Case C — State contains resource, but AWS object is absent

Determine why it is absent.

Options:

- recreate it through a normal plan
- restore it through service-specific recovery
- remove the state entry only if Terraform should no longer own it

Do not use `terraform state rm` merely to silence an error. It tells Terraform to forget ownership and may cause duplicate recreation later.

### Case D — AWS resource was partially modified

Examples:

- EKS node group update failed
- RDS modification entered a transitional state
- CloudFront deployment still propagates
- Auto Scaling refresh is in progress

Wait for or resolve the AWS-side operation before asking Terraform to issue another conflicting action.

### Case E — Orphan resource should not exist

Delete only after checking:

- data retention
- traffic or DNS references
- security and IAM dependencies
- billing impact
- whether another stack owns it
- whether deletion is reversible

Prefer codifying the cleanup and applying it through the controlled workflow where possible.

### Case F — State address changed during refactor

Use a `moved` block or controlled state move rather than destroy/recreate.

```hcl
moved {
  from = aws_security_group.old
  to   = module.network.aws_security_group.app
}
```

---

## 9. Do not blindly rerun apply

A rerun can be safe only after understanding the failed operations and plan.

Blind rerun risks:

- duplicate resources with generated names
- conflicting asynchronous updates
- replacement of a partially modified resource
- destructive cleanup based on stale state
- repeated API throttling or quota failure
- loss of original evidence

Terraform resources and providers should be idempotent, but external APIs, custom provisioners, scripts, and partial state writes can violate that assumption.

---

## 10. Dangerous recovery shortcuts

### `-target`

`-target` can be useful in exceptional recovery, but it creates an incomplete graph plan.

Use only when:

- the narrow operation is understood
- omitted dependencies are reviewed
- a full plan follows immediately

It is not a normal deployment strategy.

### Manual console fixes

A manual change can restore service, but it creates drift.

When break-glass is necessary:

1. record the exact action
2. capture before and after configuration
3. update Terraform or reverse the action
4. run refresh-only and normal plans
5. restore one authority

### Restoring old state

Never restore an older state solely because it predates the incident.

Compare:

- lineage
- serial
- resource inventory
- real AWS resources
- CloudTrail operations

The older version may omit successfully created infrastructure.

### Direct backend mutation

Avoid manual S3 object replacement, lock-item deletion, or `.tflock` deletion unless the documented break-glass procedure requires it and Terraform-native recovery is impossible.

---

## 11. Service-specific partial-operation examples

### EKS

- node-group update may continue after client timeout
- add-on update may conflict with unmanaged fields
- access-entry or IAM propagation may lag

Check AWS operation status and cluster health before retrying.

### RDS/Aurora

- modifications can remain pending or enter maintenance
- instance replacement or failover may affect endpoints
- deletion and snapshot operations are stateful and irreversible

Protect data before Terraform reconciliation.

### IAM

- policy or role may exist even if propagation caused the apply to fail
- generated names can create duplicates
- trust policy and permissions boundary may be partially updated

### Route 53

- record change may have completed before the provider returned an error
- clients may cache old values

Do not create competing records without checking change status and hosted-zone state.

### CloudFront

- distribution updates take time and cannot be treated like instantaneous object changes

---

## 12. Resume delivery safely

Before apply:

- correct the root configuration or permissions issue
- ensure one state writer
- confirm lock ownership
- review saved recovery plan
- require approval for replacement or deletion
- ensure service quotas and dependencies are ready

Run one controlled apply.

Observe:

```text
lock acquired
state read
resource operations
state write
lock released
post-apply validation
```

Then run a fresh plan and expect no unintended changes.

---

## 13. Prove recovery

Recovery is complete when:

- Terraform plan is empty or contains only known accepted drift
- state serial and object version advance normally
- lock is released
- every managed resource has one owner
- no orphan resources remain without disposition
- application or platform health is restored
- dependent stacks and outputs are correct
- CI concurrency and credentials are normal

---

## 14. Prevention controls

### Pipeline

- one concurrency group per state
- OIDC short-lived credentials
- saved plan or controlled re-plan policy
- no automatic retry of ambiguous partial apply
- timeout longer than known service operations where appropriate
- evidence retention

### State design

- partition by blast radius and lifecycle
- S3 versioning and encryption
- supported locking mechanism
- backup and restore tests
- narrow state-prefix permissions

### Code and providers

- pin Terraform and provider versions
- commit dependency lock files
- avoid non-idempotent provisioners
- use stable resource names where import and recovery matter
- use `moved` blocks for refactors
- test create, update, failure, and destroy paths

### Preflight

- quota checks
- policy and IAM simulation where practical
- change windows for long stateful operations
- service readiness and dependency validation

### Operations

- documented import and force-unlock runbooks
- break-glass access
- scheduled drift detection
- ownership catalog
- game day for state restore and partial apply

---

## Adversarial follow-ups

### “Why not rerun apply? Terraform is idempotent.”

Terraform aims for convergence, but the state may not reflect completed AWS operations, and providers or scripts can be non-idempotent. I first reconcile state and reality, then rerun from a reviewed plan.

### “When do you use force-unlock?”

Only after proving the original writer is dead, freezing every competing writer, backing up state, and confirming the exact backend key and lock ID.

### “When would you restore an old S3 state version?”

Only as a controlled state-database recovery after comparing serial, lineage, resource inventory, and real infrastructure. It is not the default repair.

### “Would you destroy all partial resources and start again?”

Only for an isolated disposable environment where dependency and data risk are understood. In production, partial resources may already carry traffic, data, identities, or external references.

### “How do you prevent drift after a manual emergency fix?”

I immediately record the change, update Terraform configuration or reverse the mutation, and run refresh-only and normal plans until configuration, state, and reality converge.

---

## Weak answers to avoid

- “Run terraform apply again.”
- “Delete the partial resources in the console.”
- `terraform apply -lock=false`
- force-unlocking without proving the writer is dead
- restoring old state without checking real infrastructure
- using `state rm` to hide missing resources
- treating `-target` as a standard deployment workflow
- ignoring asynchronous AWS operations
- allowing CI and laptops to write the same production state

---

## Closing statement

> A partial apply is not a failed script; it is a reconciliation problem across configuration, state, and real infrastructure. I preserve evidence, inventory completed operations, choose an explicit disposition for every resource, and resume only when one controlled writer can converge safely.