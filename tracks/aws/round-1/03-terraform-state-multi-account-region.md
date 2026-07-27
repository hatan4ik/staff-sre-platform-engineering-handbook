# Question 3 — Terraform State Across Multiple AWS Accounts and Regions

## Interview prompt

How do you manage Terraform state across multiple AWS accounts and Regions? Explain your approach using Amazon S3, DynamoDB state locking, and CI/CD pipelines.

## Current-version correction to state explicitly

The prompt reflects the long-established S3 plus DynamoDB backend pattern. That remains important in existing estates. For new Terraform S3 backends, HashiCorp supports native S3 lockfiles with:

```hcl
use_lockfile = true
```

HashiCorp marks DynamoDB-based locking as deprecated. A Staff-level answer should demonstrate both:

1. how to operate and recover the requested S3 plus DynamoDB design safely
2. how to migrate deliberately toward S3-native locking where the organization's Terraform version and compatibility requirements allow it

Do not embarrass the interviewer by dismissing the prompt. Show current knowledge while answering the operating problem they asked about.

---

## 90-second Staff/Principal answer

> I treat Terraform state as a production control-plane database, not as a file. I keep it in a dedicated infrastructure or tooling account, in S3 with versioning, encryption, public-access blocking, TLS-only bucket policy, CloudTrail data-event auditing, and least-privilege access to exact state prefixes. Existing environments may use a DynamoDB table with a `LockID` string key; for new supported versions I would evaluate S3 native lockfiles because DynamoDB locking is deprecated.
>
> I partition state by account, Region, environment, system, and lifecycle so a network change does not lock or endanger every application. The state key is explicit, for example `prod/us-east-1/network/terraform.tfstate`, and each state has one protected CI writer. CI assumes short-lived roles through OIDC, runs validation and a speculative plan on pull requests, performs policy and destructive-change checks, and allows a single approved production apply with concurrency controls and backend locking.
>
> The state bucket can be centrally governed, but the provider roles are in the target accounts. I do not use cross-Region replication as active-active state; one backend is authoritative. For recovery, I freeze writers, capture the lock and state version, determine whether an apply is still alive, back up state, run refresh-only reconciliation, and remove a stale lock only with evidence. S3 versioning is tested as part of a documented restore procedure.

---

## 1. State is control-plane data

Terraform state maps configuration addresses to real cloud resource identifiers and computed attributes.

It may include:

- resource IDs and ARNs
- dependency relationships
- provider-computed values
- output values
- state serial and lineage
- values marked sensitive in configuration
- secret material returned by providers

Consequences of state corruption include:

- attempting to recreate live resources
- deleting the wrong object
- losing ownership of real infrastructure
- destructive replacement plans
- leaking credentials or connection strings

The governing principle is:

> A delayed apply is safer than an uncoordinated state mutation.

---

## 2. Account model

A common organization layout is:

```text
AWS Organizations
├── security account
├── log archive account
├── infrastructure/tooling account
│   ├── Terraform state S3 bucket
│   ├── optional legacy DynamoDB lock table
│   └── CI OIDC trust and orchestration roles
├── development workload account
├── staging workload account
└── production workload account
```

### Why a dedicated state account?

It separates state administration from the workload being managed.

Benefits:

- a target-account incident does not automatically remove state access
- centralized encryption, audit, and retention controls
- fewer administrators with state write permissions
- clearer break-glass procedures
- reduced chance that a workload stack destroys its own backend

A centralized backend is not mandatory. The important properties are independent protection, explicit ownership, and recoverability.

---

## 3. State partitioning strategy

Use state boundaries that align with:

- blast radius
- ownership
- deployment frequency
- lifecycle
- privilege boundary
- recovery sequence

Example keys:

```text
organization/security-baseline/terraform.tfstate
prod/us-east-1/network/core/terraform.tfstate
prod/us-east-1/eks/cluster-a/terraform.tfstate
prod/us-east-1/data/payments/terraform.tfstate
prod/us-west-2/network/core/terraform.tfstate
shared/global/route53/terraform.tfstate
```

### Avoid one giant state

One enterprise-wide state causes:

- long refresh and plan duration
- lock contention
- broad credentials
- large failure blast radius
- tightly coupled release schedules
- difficult ownership

### Avoid uncontrolled state fragmentation

Thousands of tiny states cause:

- dependency sprawl
- output-discovery complexity
- difficult orchestration
- inconsistent standards
- orphaned backends

State boundaries should be intentional and cataloged.

### Workspaces versus directories or separate backends

Terraform workspaces can separate state keys, but they do not inherently create strong account, credential, policy, or review boundaries.

For production isolation, prefer explicit environment directories or stacks with separate backend keys and target roles. Use workspaces when their semantics are deliberately suitable, not merely to avoid repository structure.

---

## 4. S3 backend design

Example modern backend:

```hcl
terraform {
  backend "s3" {
    bucket       = "acme-terraform-state-prod"
    key          = "prod/us-east-1/network/core/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    kms_key_id   = "arn:aws:kms:us-east-1:111111111111:key/abcd..."
    use_lockfile = true
  }
}
```

Example legacy/requested backend:

```hcl
terraform {
  backend "s3" {
    bucket         = "acme-terraform-state-prod"
    key            = "prod/us-east-1/network/core/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:111111111111:key/abcd..."
    dynamodb_table = "terraform-state-locks"
  }
}
```

### Required controls

- S3 versioning enabled
- server-side encryption with KMS where organizational policy requires customer-managed control
- Block Public Access
- bucket policy denying non-TLS access
- narrow IAM permissions by prefix
- no public or anonymous principal
- CloudTrail data events for state-object access where audit requirements justify the cost
- access logging according to the organization's logging architecture
- retention and recovery policy for old object versions
- deletion protection and break-glass control around the backend infrastructure

### Credentials are not backend configuration

Do not hardcode access keys or secret values in the backend block or pass them through mechanisms that persist into `.terraform` metadata or plan artifacts.

Use the AWS credential chain and short-lived assumed roles.

---

## 5. KMS design

A customer-managed KMS key can provide:

- explicit key policy
- separation of key administration and data access
- auditable decrypt/encrypt use
- revocation control
- organizational policy enforcement

Required design questions:

- which CI role can use the key?
- which human break-glass role can decrypt state?
- can target workload accounts access the state key?
- how is key deletion protected?
- what happens if the KMS key is disabled during an incident?

Do not make the recovery procedure depend on a role that itself is provisioned only by the inaccessible state.

---

## 6. DynamoDB locking for existing estates

The legacy table requires a string partition key named:

```text
LockID
```

Typical permissions include:

- `dynamodb:DescribeTable`
- `dynamodb:GetItem`
- `dynamodb:PutItem`
- `dynamodb:DeleteItem`

Lock acquisition uses a conditional write. Only one writer should acquire the lock for a state path.

### Do not use TTL as a simplistic stale-lock solution

A legitimate apply may run longer than the TTL. Automatic expiry could allow a second writer while the first still mutates infrastructure.

That changes a fail-closed mechanism into a split-brain risk.

### Migration toward S3 lockfiles

A safe migration plan includes:

1. inventory Terraform versions and backend configurations
2. upgrade clients to a version supporting S3 lockfiles
3. test locking and recovery in non-production
4. configure both mechanisms during a compatibility window where supported and justified
5. ensure all writers have migrated
6. remove DynamoDB configuration
7. retain audit evidence and update runbooks

Never migrate locking while multiple uncontrolled Terraform versions can write the same state.

---

## 7. Multi-account provider access

The backend role and the target-resource role are separate concerns.

```text
CI workload identity
   |
   +--> assume state-access role in tooling account
   |
   +--> assume deployment role in target workload account
```

Example provider:

```hcl
provider "aws" {
  region = var.region

  assume_role {
    role_arn     = "arn:aws:iam::444444444444:role/terraform-deployer"
    session_name = "terraform-${var.environment}-${var.region}"
  }

  default_tags {
    tags = {
      ManagedBy   = "Terraform"
      Environment = var.environment
      Repository  = var.repository
    }
  }
}
```

### Role controls

- trust only the approved CI OIDC subject or orchestration role
- restrict repository, branch, environment, or workflow claims
- use short session duration appropriate to apply time
- separate plan/read role from apply/write role where useful
- permissions boundaries for delegated role creation
- explicit `iam:PassRole` boundaries
- deny unapproved Regions through organizational policy where applicable
- audit every `AssumeRole` and apply

Avoid chains so long that session duration and audit attribution become unclear.

---

## 8. Region strategy

Terraform state lives in one S3 Region even when it describes resources in another Region.

Example:

```text
state backend: us-east-1 tooling account
managed resources:
  - us-east-1 production
  - us-west-2 disaster recovery
  - global Route 53 resources
```

This can be valid, but it creates a control-plane dependency on the backend Region.

### Options

1. **One authoritative backend Region** with tested recovery and sufficient service availability.
2. **Separate backend per workload Region** for stronger regional isolation, accepting more backend administration.
3. **Separate backend by environment or account** where organizational boundaries dominate.

### Cross-Region replication caution

S3 cross-Region replication is asynchronous. A replica object is not automatically a safe active backend for concurrent Terraform writers.

Do not point one pipeline to the primary and another to a replica.

For disaster recovery:

- freeze all writers
- identify the last authoritative state version
- verify object version, serial, lineage, and infrastructure reality
- deliberately reconfigure the backend
- resume only one writer

The replica is recovery material, not an active-active database.

---

## 9. CI/CD pipeline

```text
Pull request
  |
  +--> formatting and validation
  +--> provider/module lock verification
  +--> lint and security scanning
  +--> policy checks
  +--> terraform plan
  +--> rendered plan summary
  +--> cost and destructive-change review
  |
Protected approval
  |
  v
Apply job
  |
  +--> OIDC authentication
  +--> state lock acquisition
  +--> one state-specific concurrency group
  +--> reviewed plan verification or controlled re-plan
  +--> apply
  +--> post-apply validation
  +--> state write and lock release
  +--> evidence retention
```

### Pull-request stage

Run:

```bash
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform providers lock -platform=linux_amd64
```

Then initialize the real backend only in a trusted pipeline context.

### Concurrency

Use a unique concurrency key per state:

```text
terraform:<account>:<region>:<environment>:<stack>
```

Do not use one global Terraform concurrency group. Independent states should deploy independently.

Do not allow parallel jobs to share a state merely because backend locking will serialize them. That creates stale approvals and confusing plans.

### Production approvals

Production apply should require:

- reviewed code
- reviewable plan
- policy success
- explicit approval for replacements or destructive actions
- known identity and change record
- no newer unreviewed commit
- one active writer

### Plan artifact caution

A saved plan can contain sensitive values. Encrypt it, restrict access, set short retention, and never expose it in public CI logs or artifacts.

---

## 10. Dependency handling between states

Avoid creating an invisible web of remote-state dependencies.

Options:

- publish selected outputs to SSM Parameter Store
- query stable resources by tags or data sources
- use a platform catalog or pipeline orchestration metadata
- use `terraform_remote_state` only with carefully scoped state access

`terraform_remote_state` gives the reader access to the state snapshot, not only the declared output abstraction at the storage layer. State may contain more sensitive information than the output list suggests.

Prefer explicit published interfaces for broad organizational consumption.

---

## 11. Failure and recovery workflow

### Scenario

An apply fails midway. Real AWS resources may have changed, the state may or may not have been written, and a lock remains.

### Step 1 — Freeze all writers

Pause pipelines and prevent automatic retries.

Identify the exact:

- AWS account
- Region
- backend bucket
- state key
- workspace, if used
- CI run
- assumed role
- Terraform version

### Step 2 — Preserve evidence

Capture:

- Terraform logs
- lock ID and owner
- S3 current object version
- state serial and lineage
- CloudTrail events
- CI runner status
- provider-side operations still in progress

### Step 3 — Determine whether the original writer is alive

A canceled CI UI status is not sufficient evidence. Confirm the process or runner is gone and that no provider operation is still being driven.

### Step 4 — Back up current state

```bash
terraform state pull > state-backup-$(date +%Y%m%d-%H%M%S).json
```

Store the backup securely.

List S3 versions:

```bash
aws s3api list-object-versions \
  --bucket acme-terraform-state-prod \
  --prefix prod/us-east-1/network/core/terraform.tfstate
```

### Step 5 — Inspect reality before changing state

Use read-only AWS queries and a refresh-only plan when safe:

```bash
terraform plan -refresh-only
```

Look for:

- cloud resources created but absent from state
- state objects whose resources no longer exist
- partially completed updates
- immutable changes that now require replacement
- changes in the wrong account or Region

### Step 6 — Remove a stale lock only with evidence

Use Terraform's lock ID mechanism where possible:

```bash
terraform force-unlock <LOCK_ID>
```

Only after proving:

1. the original writer is dead
2. all competing writers are frozen
3. the correct state key is identified
4. state is backed up
5. provider-side operations are understood

Do not routinely delete a DynamoDB item or `.tflock` object by hand.

### Step 7 — Reconcile

Possible actions include:

- import successfully created resources
- remove state entries only for genuinely absent or relinquished resources
- correct configuration to match approved reality
- complete the interrupted operation
- replace a resource deliberately after review

Then generate a normal plan and review every destructive action.

### Step 8 — Resume one writer

Run one controlled apply and observe state write and lock release.

---

## 12. State restore from S3 versioning

Do not blindly restore “the version before the incident.”

An older version may omit resources that were successfully created before a failed state write.

Before restore, compare:

- state lineage
- serial
- resource inventory
- last-modified time
- CloudTrail events
- real AWS resources
- provider operations

Restore is a controlled state-database recovery, not a file copy shortcut.

Test this runbook in a non-production environment.

---

## 13. Drift management

Use three categories.

### Expected externally managed change

Examples:

- ASG desired capacity controlled by an autoscaler
- autoscaling policy changes a target
- an AWS service updates a computed field

Configure Terraform lifecycle behavior only when another authoritative owner is documented.

### Unauthorized manual drift

Detect through scheduled plans, AWS Config, CloudTrail, and change governance. Decide whether to revert or codify based on intended state and incident context.

### Emergency break-glass drift

Allow a narrow, audited emergency role. After mitigation:

1. capture the exact mutation
2. update Terraform configuration or reverse the change
3. run refresh-only and normal plans
4. restore one source of truth
5. close elevated access

Never normalize permanent click-ops by simply adding `ignore_changes`.

---

## 14. Backup and recovery tests

At least periodically test:

- reading state from an isolated recovery role
- restoring a previous object version
- rebuilding the DynamoDB table or migrating locking, where relevant
- rotating backend roles and KMS access
- recovering after a failed state write
- recreating the CI runner from scratch
- operating when the normal identity provider is unavailable
- recovering backend configuration documentation

A backup that has never been restored is only a theory.

---

## 15. Security checklist

- no static AWS keys in CI
- OIDC trust constrained to approved repository and environment claims
- exact S3 prefix permissions
- KMS permissions separated from broad S3 administration
- state write denied to ordinary developers
- break-glass role requires strong authentication and audit
- S3 Block Public Access
- TLS-only bucket policy
- versioning enabled
- backend resources protected from workload-stack destruction
- plan and state artifacts treated as secrets
- CloudTrail records state and role activity
- state access reviewed periodically

---

## Adversarial follow-ups

### “One bucket or a bucket per account?”

Either can work. One central bucket simplifies governance but is a broad control plane. Per-account buckets improve isolation but multiply administration. I would choose based on trust boundaries, recovery requirements, and operational maturity, then scope access to exact prefixes or buckets.

### “Why not use one state for all Regions?”

It increases lock contention and regional blast radius. Global resources may need their own state, but regional infrastructure should normally be independently deployable and recoverable.

### “Can S3 replication give active-active Terraform?”

No. Replication is asynchronous and Terraform requires a single authoritative state and locking domain. A replica can support a controlled disaster-recovery procedure after writers are frozen.

### “Do you force-unlock when a release is urgent?”

Urgency does not prove the lock is stale. I first identify the owner, freeze writers, back up state, and verify provider activity. A visible delay is safer than silent concurrent state corruption.

### “What replaces DynamoDB locking?”

For supported modern Terraform versions, the S3 backend can use a native lockfile through `use_lockfile = true`. I would migrate only after proving every writer is compatible and the recovery runbook is updated.

### “How do you share outputs without exposing state?”

Publish an intentionally selected interface to SSM Parameter Store, a service catalog, DNS, or another controlled registry. I avoid giving broad consumers direct state-object read access.

---

## Weak answers to avoid

- “Put state in S3 and enable DynamoDB.”
- one state file for every account and Region
- long-lived CI access keys
- running plans from one identity and applies from another without explaining implications
- direct DynamoDB lock deletion as the first recovery step
- using `-lock=false` to unblock production
- treating S3 replication as active-active state
- restoring the oldest state version without comparing infrastructure reality
- putting backend credentials in Terraform code
- assuming `sensitive = true` removes values from state

---

## Closing statement

> I design Terraform state like a highly privileged control-plane database: independently protected, versioned, encrypted, serialized, narrowly partitioned, and continuously recoverable. Multi-account deployment roles may be distributed, but state ownership, writer identity, and recovery authority are always explicit.