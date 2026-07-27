# Lab 2 — Terraform Partial-Apply Reconciliation

## Interview scenario

`terraform apply` creates some infrastructure, then fails midway. The pipeline reports failure, but the environment now contains a mixture of:

- objects recorded in Terraform state;
- objects that may exist remotely but were not fully recorded;
- resources that were never attempted;
- configuration that still describes the desired end state.

This safe local lab models that condition with Terraform's built-in `terraform_data` resource and shell-created artifacts. It does not require an AWS account.

## Safety invariant

> Recovery must reconcile configuration, Terraform state, and real infrastructure without deleting authoritative state, inventing ownership, or causing an avoidable destructive replacement.

## What this lab teaches

- A failed apply is not an automatic rollback.
- Earlier successful resources can remain managed in state.
- The failed resource and later dependencies require evidence-based reconciliation.
- `terraform apply` is not a transaction across all resources.
- Provisioner side effects are not first-class provider-managed infrastructure.
- `-target`, `state rm`, import, force-unlock, and manual deletion are surgical tools, not default recovery steps.

## 1. Initialize

```bash
terraform init
terraform fmt -check
terraform validate
```

The configuration creates three logical stages:

```text
network
   -> database  <-- intentionally fails by default
        -> application
```

Each successful stage writes an artifact under `artifacts/` so configuration, state, and external reality can be compared.

## 2. Run the intentionally failing apply

```bash
terraform plan -out=failed-run.tfplan
terraform apply failed-run.tfplan
```

The apply should fail during `terraform_data.database`.

Do not delete `.terraform`, the state file, or the artifacts. Preserve evidence first.

## 3. Reconcile three sources of truth

### Configuration

```bash
terraform validate
sed -n '1,240p' main.tf
```

### Terraform state

```bash
terraform state list
terraform show
terraform show -json > state-after-failure.json
```

### External reality

```bash
find artifacts -maxdepth 1 -type f -print -exec cat {} \;
```

Record what actually happened. Do not assume the exact failed-resource state representation; inspect the version of Terraform you are running.

A useful reconciliation table is:

| Address | In configuration? | In state? | External artifact exists? | Intended action |
|---|---:|---:|---:|---|
| `terraform_data.network` | yes | inspect | inspect | retain |
| `terraform_data.database` | yes | inspect | inspect | repair/retry after cause fixed |
| `terraform_data.application` | yes | inspect | inspect | create only after dependency succeeds |

## 4. Preserve and inspect the plan lineage

```bash
cp terraform.tfstate terraform.tfstate.incident-backup 2>/dev/null || true
terraform plan -detailed-exitcode
```

Interpret `-detailed-exitcode` correctly:

- `0`: no changes;
- `1`: planning error;
- `2`: changes are proposed.

A new plan is evidence, not permission to apply blindly. Review whether it proposes create, update, replace, or destroy actions.

## 5. Fix the cause and recover

The injected failure is controlled by `fail_database`.

```bash
terraform plan -var='fail_database=false' -out=recovery.tfplan
terraform show recovery.tfplan
terraform apply recovery.tfplan
```

Validate convergence:

```bash
terraform plan -var='fail_database=false' -detailed-exitcode
terraform state list
find artifacts -maxdepth 1 -type f -print -exec cat {} \;
```

The final plan should report no changes.

## 6. Demonstrate a reconciliation boundary

Delete the file created by the `network` provisioner:

```bash
rm -f artifacts/network.txt
terraform plan -var='fail_database=false'
```

Terraform may report no infrastructure change because the file is a side effect of a provisioner, not a modeled attribute of a provider-managed resource.

This is the production lesson:

> Terraform can reconcile only the remote-object semantics exposed through its provider and recorded in state. Hidden shell side effects create unmanaged reality.

Do not use this toy behavior to infer that an AWS resource would be invisible. AWS provider resources normally refresh remote object attributes through AWS APIs. The lab isolates the danger of provisioner-driven side effects.

Restore the lab by replacing the network object deliberately:

```bash
terraform apply \
  -var='fail_database=false' \
  -replace='terraform_data.network'
```

Review the downstream effects before approving any replacement in a real environment.

## Unsafe shortcuts

### Delete the state and start over

This discards ownership and lineage. Existing infrastructure can then collide with create attempts or become orphaned.

### Run `terraform apply` repeatedly without reading the plan

The original cause may remain, and the new plan can include replacement or destruction that was not part of the failed run.

### Use `terraform state rm` to make the error disappear

Removing an address from state transfers it out of Terraform management; it does not delete or repair the remote object.

### Force-unlock immediately

A lock protects against concurrent writers. Force-unlock is appropriate only after proving the original writer is gone and the lock is stale.

### Use `-target` as routine deployment

Targeting can be useful for exceptional recovery when Terraform explicitly recommends it, but it can produce an incomplete view of the full dependency graph. Always return to a complete plan.

## Production recovery sequence

```text
1. Stop concurrent applies and identify the state writer.
2. Preserve logs, plan, state version, provider versions, and API errors.
3. Determine which remote operations succeeded.
4. Compare configuration, state, and cloud reality address by address.
5. Fix the original cause: quota, permission, dependency, invalid input, or provider/API failure.
6. Generate and review a fresh full plan.
7. Use import, moved blocks, state operations, or replacement only when evidence requires them.
8. Apply through the authoritative pipeline.
9. Prove convergence with a full no-change plan and application-level validation.
10. Add prevention: policy, preflight quota checks, smaller state boundaries, tests, and safer rollout order.
```

## Interview answer drill

> I would not describe a failed Terraform apply as rolled back. I would stop concurrent writers, preserve the plan, logs, provider versions, and state version, then reconcile configuration, state, and AWS reality for every affected address. I would fix the original permission, quota, dependency, or API problem and review a fresh full plan before applying. Import, state removal, replacement, targeting, or force-unlock are evidence-driven recovery tools, not defaults. Recovery is complete only when the authoritative pipeline produces a no-change plan and the workload passes functional validation.

## Cleanup

```bash
terraform destroy -var='fail_database=false' -auto-approve
rm -rf artifacts .terraform .terraform.lock.hcl \
  terraform.tfstate terraform.tfstate.backup \
  terraform.tfstate.incident-backup \
  failed-run.tfplan recovery.tfplan state-after-failure.json
```

## Related material

- [`tracks/aws/round-2/11-terraform-partial-apply-recovery.md`](../../../tracks/aws/round-2/11-terraform-partial-apply-recovery.md)
- [`core/infrastructure-as-code/terraform-state-integrity.md`](../../../core/infrastructure-as-code/terraform-state-integrity.md)
