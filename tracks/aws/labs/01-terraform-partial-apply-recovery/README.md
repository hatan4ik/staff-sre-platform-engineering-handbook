# Lab 01 — Terraform Partial-Apply Recovery

## Objective

Practice the same recovery discipline used for an AWS Terraform incident without creating cloud resources.

The lab intentionally fails after Terraform creates a managed local file. You will then:

- identify the exact state and configuration;
- preserve state evidence;
- compare configuration, state, and real objects;
- recover from a partial apply;
- simulate a resource that exists outside state;
- import it rather than blindly recreate or delete it;
- verify one clean final plan.

## Prerequisites

- Terraform 1.6 or newer
- Bash
- `jq`
- a disposable checkout of this directory

## Files

```text
main.tf                 local resources and injected post-create failure
variables.tf            generation and failure controls
outputs.tf              evidence-friendly outputs
Makefile                repeatable commands
scripts/evidence.sh     state and filesystem evidence capture
scripts/reset.sh        cleanup for a new run
runtime/                 generated during the lab
.evidence/               generated evidence snapshots
```

## Safety

This configuration uses only the local and terraform providers. It does not configure an AWS provider or remote backend.

Do not replace the backend or provider while following the lab instructions.

---

## Scenario 1 — Partial apply after a resource is created

### 1. Initialize

```bash
make init
```

### 2. Review the plan

```bash
terraform plan \
  -var='generation=1' \
  -var='fail_after_create=true'
```

Predict what Terraform will create before applying.

### 3. Inject failure

```bash
make fail
```

Expected behavior:

- `runtime/managed.txt` is created;
- the post-create check exits with code 42;
- the apply returns nonzero;
- Terraform state contains evidence of completed and failed operations.

Do **not** immediately rerun apply.

### 4. Preserve evidence

```bash
make evidence
```

Inspect:

```bash
ls -la .evidence
jq '.values.root_module.resources[] | {address, mode, type, values}' \
  .evidence/terraform-show-*.json
cat .evidence/filesystem-*.txt
```

Answer:

1. Which objects exist on disk?
2. Which resources are represented in state?
3. Which resource is tainted or pending replacement?
4. What was the exact failing command?
5. Would a second concurrent writer be safe?

### 5. Generate a recovery plan

```bash
terraform plan \
  -var='generation=1' \
  -var='fail_after_create=false' \
  -out=recovery.tfplan

terraform show recovery.tfplan
```

The correct recovery is to allow Terraform to complete the failed post-create check while preserving the successfully managed file.

### 6. Recover through one controlled writer

```bash
make recover
```

### 7. Prove convergence

```bash
make verify
```

Expected result:

```text
No changes. Your infrastructure matches the configuration.
```

Also verify:

```bash
cat runtime/managed.txt
cat runtime/check.txt
```

---

## Scenario 2 — Real object exists but state no longer owns it

This simulates an AWS resource that exists after a state-write or ownership failure.

### 1. Start from healthy state

```bash
make reset
make init
make healthy
```

### 2. Back up state

```bash
make evidence
terraform state pull > .evidence/pre-state-rm.json
```

### 3. Simulate loss of ownership

```bash
terraform state rm local_file.managed
```

The file remains:

```bash
test -f runtime/managed.txt && echo 'real object still exists'
```

But Terraform no longer tracks it:

```bash
terraform state list
```

### 4. Inspect the dangerous plan

```bash
terraform plan \
  -var='generation=1' \
  -var='fail_after_create=false'
```

Terraform now proposes creating the managed object again because its control-plane memory no longer contains it.

In AWS this could mean:

- duplicate generated resources;
- create failure because a name already exists;
- accidental replacement;
- loss of ownership of a live resource.

### 5. Re-import the existing object

The local provider supports import by filename in current supported versions. Run:

```bash
terraform import local_file.managed runtime/managed.txt
```

Then review:

```bash
terraform plan \
  -var='generation=1' \
  -var='fail_after_create=false'
```

If the imported state exposes a content or permission difference, review the exact diff rather than automatically applying.

### 6. Prove final ownership

```bash
terraform state show local_file.managed
make verify
```

---

## Scenario 3 — Manual drift

### 1. Change the managed file outside Terraform

```bash
printf 'manual-emergency-change\n' > runtime/managed.txt
```

### 2. Preserve the mutation

```bash
cp runtime/managed.txt .evidence/manual-change.txt
```

### 3. Compare desired and real state

```bash
terraform plan \
  -var='generation=1' \
  -var='fail_after_create=false'
```

Decide deliberately:

- Was the manual change an emergency mitigation that must be codified?
- Should Terraform restore the original desired content?
- Is another controller the real owner?

Do not add `ignore_changes` merely to hide unexplained drift.

---

## AWS production mapping

| Local lab concept | AWS/Terraform equivalent |
|---|---|
| `terraform.tfstate` | S3 state object and lineage |
| local apply process | protected CI writer |
| generated local file | AWS resource created or modified by provider |
| injected `local-exec` failure | quota, IAM, timeout, provider, or service-operation failure |
| `.evidence` state pull | encrypted state backup and S3 version capture |
| object exists after `state rm` | resource exists in AWS but is absent from Terraform state |
| import by file path | import by AWS resource ID/ARN |
| manual file edit | click-ops or emergency AWS mutation |

## Unsafe shortcuts to explain in the interview

- rerunning apply without checking what completed;
- using `-lock=false`;
- force-unlocking without proving the writer is dead;
- deleting the real object because state is confused;
- restoring an older state solely because it predates the incident;
- using `state rm` to silence an error;
- running two repair sessions simultaneously.

## Adversarial questions

1. What if the provider timed out but the AWS operation continued?
2. When is `terraform state rm` legitimate?
3. Why is an older S3 state version not automatically correct?
4. When would `-target` be acceptable during recovery?
5. What evidence is required before `force-unlock`?
6. How do you ensure a second repository does not use the same backend key?
7. What if import proposes replacement immediately afterward?

## Cleanup

```bash
make reset
```

The cleanup script removes only local runtime and evidence files in this lab directory.