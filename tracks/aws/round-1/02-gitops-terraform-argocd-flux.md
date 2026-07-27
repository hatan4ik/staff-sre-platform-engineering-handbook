# Question 2 — GitOps on EKS with Terraform and Argo CD or Flux

## Interview prompt

Explain your GitOps workflow on Amazon EKS. How do you safely deploy infrastructure and applications using Terraform with Argo CD or Flux?

## What the interviewer is testing

The difficult part is not defining GitOps. It is defining ownership boundaries, bootstrap order, promotion, rollback, secret handling, and failure recovery without allowing Terraform, CI, and the GitOps controller to fight over the same resource.

---

## 90-second Staff/Principal answer

> I split the system into explicit control-plane ownership. Terraform owns AWS resources and the minimum EKS bootstrap layer: accounts, VPCs, clusters, IAM, KMS, ECR, state backends, and the initial GitOps controller installation. Argo CD or Flux owns Kubernetes add-ons and application desired state after bootstrap. No object has two reconcilers.
>
> CI validates changes but does not directly mutate production clusters. For application changes, CI runs tests, builds once, scans and signs an immutable image, pushes it to ECR, and updates an environment repository with the image digest. The GitOps controller pulls that signed desired state, applies it, reports health, and continuously detects drift.
>
> Promotion is by pull request from dev to staging to production, with policy checks, approvals, and the same artifact digest. I use Argo Rollouts or Flagger for canary or blue/green delivery, and rollback criteria are tied to service-level indicators. Secrets are never committed in plaintext; workloads retrieve them through Secrets Manager using External Secrets or the Secrets Store CSI driver with EKS Pod Identity or IRSA.
>
> Infrastructure changes run through isolated Terraform state, speculative plans, policy checks, manual approval for production, one writer per state, and post-apply verification. I sequence dependencies explicitly: network before cluster, cluster before controllers, CRDs before custom resources, and platform add-ons before applications. If GitOps is unhealthy, I restore reconciliation first rather than bypassing it with ad hoc kubectl changes.

---

## 1. Define control-plane ownership

A production design should have a written ownership table.

| Resource class | Primary owner | Examples |
|---|---|---|
| AWS organization/account baseline | Terraform or CloudFormation | SCPs, audit roles, account vending |
| Regional network | Terraform | VPC, subnets, transit routing, endpoints, NAT |
| EKS cluster foundation | Terraform | cluster, access entries, KMS, managed node groups |
| GitOps bootstrap | Terraform or a dedicated bootstrap process | Argo CD/Flux namespace and controller |
| Kubernetes platform add-ons | GitOps | ingress, cert-manager, external-dns, policy, observability |
| Application manifests | GitOps | Deployments, Services, HPAs, PDBs, NetworkPolicies |
| Application artifact | CI build system | immutable image digest in ECR |
| Runtime secret value | Secrets Manager | database password, API key, certificate material |

The governing rule is:

> One resource, one authoritative reconciler.

### Dangerous overlap examples

- Terraform creates a Helm release while Argo CD manages the same release.
- Terraform applies a Deployment while Flux applies a Kustomization containing it.
- CI runs `kubectl set image` while Git still contains the old image.
- an operator patches a Service annotation that GitOps immediately removes.

These are not merely tool conflicts. They make rollback and incident reasoning unreliable.

---

## 2. Repository model

A practical separation is:

```text
platform-infrastructure/
├── modules/
│   ├── network/
│   ├── eks/
│   ├── iam/
│   └── observability/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── prod/
└── policies/

application-source/
├── src/
├── tests/
├── Dockerfile
└── .github/workflows/build.yaml

platform-gitops/
├── clusters/
│   ├── dev-us-east-1/
│   ├── staging-us-east-1/
│   └── prod-us-east-1/
├── platform/
│   ├── ingress/
│   ├── external-secrets/
│   ├── policy/
│   └── observability/
└── applications/
    └── payments-api/
        ├── base/
        └── overlays/
            ├── dev/
            ├── staging/
            └── prod/
```

Separate repositories are not mandatory. The important properties are:

- clear ownership
- least-privilege access
- review boundaries
- environment promotion history
- no circular bootstrap dependency
- no secret material in Git

---

## 3. End-to-end application delivery flow

```text
Developer commit
      |
      v
CI: test -> SAST -> dependency scan -> build
      |
      v
Push immutable image to ECR
      |
      +--> vulnerability scan
      +--> SBOM
      +--> sign image / provenance
      |
      v
PR updates image digest in environment Git repo
      |
      +--> schema validation
      +--> policy checks
      +--> rendered-manifest diff
      +--> approval
      |
      v
Merge
      |
      v
Argo CD / Flux pulls desired state
      |
      v
Progressive rollout
      |
      +--> SLI analysis
      +--> promote or abort
      |
      v
Drift reconciliation and health reporting
```

### Build once, promote the digest

Do not rebuild separately for staging and production.

```yaml
image:
  repository: 123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api
  digest: sha256:4db7...
```

The promoted artifact should be the same digest that passed testing. Environment differences belong in configuration, not in a new binary.

---

## 4. CI responsibilities

CI should:

- run unit, integration, and contract tests
- lint Dockerfiles, Terraform, Helm, YAML, and policies
- build the application once
- generate an SBOM
- scan dependencies and images
- sign images and attach provenance
- push to ECR
- create a pull request updating the desired image digest
- run Terraform plan for infrastructure changes
- produce reviewable diffs and evidence

CI should generally **not**:

- hold long-lived AWS keys
- run unrestricted `kubectl apply` against production
- patch production resources outside Git
- rebuild a supposedly identical production artifact
- auto-approve its own high-risk infrastructure plan

Use GitHub Actions OIDC, GitLab OIDC, or the CI platform's workload federation to assume short-lived AWS roles.

---

## 5. GitOps controller responsibilities

Argo CD or Flux should:

- authenticate to approved Git sources
- render Helm, Kustomize, or plain manifests
- compare desired and live state
- apply changes in dependency order
- expose reconciliation and health status
- detect and repair drift according to policy
- verify signed sources or artifacts where supported by the selected design
- stop or surface unhealthy reconciliation

### Pull model benefits

The cluster initiates the pull from Git. This reduces the need to give an external CI runner broad inbound cluster credentials.

The pull model does not remove all security risk. The Git repository, controller service account, repository credentials, and admission path become critical control-plane assets.

---

## 6. Argo CD design

Argo CD is strong when teams want:

- a mature application-centric UI and API
- explicit application health and sync status
- ApplicationSets for fleet generation
- sync waves and hooks
- multi-cluster management
- integration with Argo Rollouts

### Example Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: payments-prod
  namespace: argocd
spec:
  project: production
  source:
    repoURL: ssh://git@github.com/example/platform-gitops.git
    targetRevision: main
    path: applications/payments-api/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: payments
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
      - PruneLast=true
```

### Argo CD safety controls

- use AppProjects to restrict source repositories, destinations, namespaces, and resource kinds
- avoid cluster-admin for every application
- separate platform and application projects
- use sync windows for controlled production periods where justified
- use sync waves for CRDs, controllers, and dependent custom resources
- require explicit approval for destructive or high-risk resources
- protect the Argo CD admin path and use SSO
- audit repository and application changes

### ApplicationSet caution

ApplicationSet can create many Applications quickly. A generator or template mistake can therefore have fleet-wide blast radius. Test generated output and use staged rollout across clusters.

---

## 7. Flux design

Flux is strong when teams want:

- Kubernetes-native composable controllers
- reconciliation through `GitRepository`, `Kustomization`, `HelmRelease`, and image automation resources
- dependency ordering through `dependsOn`
- a CLI- and Git-centered operating model
- integration with Flagger for progressive delivery

### Example Flux Kustomization

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: payments-prod
  namespace: flux-system
spec:
  interval: 5m
  path: ./applications/payments-api/overlays/prod
  prune: true
  sourceRef:
    kind: GitRepository
    name: platform-gitops
  wait: true
  timeout: 5m
  dependsOn:
    - name: platform-prerequisites
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: payments-api
      namespace: payments
```

### Flux safety controls

- scope service accounts and namespaces
- separate sources by trust boundary
- validate `HelmRelease` and `Kustomization` dependency graphs
- avoid broad cross-namespace references unless required and governed
- alert on stalled or failed reconciliation
- protect image automation from promoting unverified tags

---

## 8. Terraform workflow

```text
Pull request
  |
  +--> fmt / validate / lint
  +--> security and policy checks
  +--> terraform plan
  +--> cost and destructive-change summary
  |
Approval gate
  |
  v
One protected apply job
  |
  +--> acquire state lock
  +--> apply reviewed plan or re-plan under policy
  +--> post-apply checks
  +--> publish outputs needed by bootstrap
```

### State separation

Use separate state by lifecycle and blast radius, for example:

```text
org/account-baseline
network/us-east-1/prod
network/us-west-2/prod
eks/us-east-1/prod-cluster-a
data/us-east-1/payments
```

Do not place an entire enterprise in one state file. Do not create thousands of tiny states without ownership and dependency discipline.

### Plan integrity

Two common models exist:

1. create and approve a saved plan artifact, then apply that exact plan in a tightly controlled environment
2. re-plan immediately before apply and require policy/approval semantics that account for the refreshed plan

Whichever model is chosen, the pipeline must make stale plans and changed provider credentials visible.

### One writer per state

Use CI concurrency controls in addition to backend locking.

```yaml
concurrency:
  group: terraform-prod-network-us-east-1
  cancel-in-progress: false
```

Backend locking protects integrity. Pipeline serialization protects operators from noisy contention and confusing approvals.

---

## 9. Bootstrap sequence

The bootstrap problem is: GitOps cannot deploy into a cluster that does not yet exist, and Terraform should not permanently own all in-cluster resources.

A clean sequence is:

```text
1. account and state backend
2. VPC, subnets, endpoints, and DNS prerequisites
3. EKS cluster and initial system capacity
4. access entries, IAM, KMS, and controller identity
5. install minimal Argo CD or Flux bootstrap
6. register the cluster's desired-state path
7. GitOps installs platform add-ons
8. GitOps installs applications
9. Terraform relinquishes ownership of GitOps-managed objects
```

### Bootstrap implementation options

- Terraform Helm provider installs only the GitOps controller, then never manages application releases.
- Terraform applies the vendor bootstrap manifests.
- a tightly controlled bootstrap job runs `argocd` or `flux bootstrap` after Terraform outputs the cluster endpoint and identity.

The selected method must document how the controller is upgraded and how ownership is transferred.

---

## 10. Dependency ordering

Common ordering failures include:

- custom resources applied before their CRDs
- ingress resources before the ingress controller is ready
- ExternalSecret objects before the operator and identity exist
- ServiceMonitor objects before Prometheus CRDs
- workloads scheduled before required node taints or storage classes exist

Use explicit dependency mechanisms:

### Argo CD

- separate Applications
- sync waves
- health checks
- ApplicationSets by rollout stage

### Flux

- separate Kustomizations
- `dependsOn`
- `wait: true`
- health checks

Avoid arbitrary sleeps. Readiness should be based on observable conditions.

---

## 11. Secrets

Never store plaintext production secrets in Git, image layers, Terraform code, or CI logs.

### Preferred runtime flow

```text
Secrets Manager + KMS
       |
EKS Pod Identity / IRSA
       |
External Secrets Operator or Secrets Store CSI Driver
       |
Pod receives only the secret it is authorized to use
```

Options:

- **External Secrets Operator:** synchronizes external values into Kubernetes Secrets.
- **Secrets Store CSI Driver:** mounts external values into pod volumes; optional synchronization to Kubernetes Secrets depends on configuration.
- **SOPS:** encrypts Git-held configuration. Useful when encrypted desired state is required, but key access and decryption boundaries must be governed.

### Secret rotation questions

The design must answer:

- how rotation is detected
- whether the application reloads without restart
- how old and new credentials overlap
- how failed rotation is rolled back
- whether secret values appear in logs, diffs, or Terraform state

---

## 12. Drift handling

Classify drift before choosing automation.

### Expected transient drift

Examples:

- HPA changes Deployment replica count
- a controller adds generated annotations
- a mutating webhook changes pod specifications

Configure ignore rules only for fields with a documented alternate owner.

### Unauthorized drift

Examples:

- manual image patch
- deleted NetworkPolicy
- changed Service type
- disabled resource limit

GitOps should detect this. Whether it auto-repairs immediately depends on risk and resource class.

### Dangerous auto-prune

Auto-prune is powerful and can turn a repository mistake into deletion at scale. Protect it with:

- reviewed repository changes
- scoped projects/service accounts
- deletion protections for critical resources
- staged cluster rollout
- backups and recovery tests

---

## 13. Progressive delivery

A Deployment becoming Available is not proof that the release is safe.

Use Argo Rollouts, Flagger, or a comparable controller to shift traffic progressively.

```text
5% -> observe -> 25% -> observe -> 50% -> observe -> 100%
```

Evaluate:

- request success rate
- p95 and p99 latency
- business transaction success
- dependency saturation
- queue growth
- resource usage
- cohort-specific errors

Abort automatically when the defined SLI threshold is crossed.

### Rollback model

For application code, rollback usually means reverting the desired digest or promoting the previous known-good revision.

For database schema, rollback might not be possible. Use expand/contract migrations:

1. add backward-compatible schema
2. deploy code that handles old and new forms
3. migrate data
4. stop old writers
5. remove obsolete schema later

---

## 14. Multi-account and multi-cluster operation

Recommended trust boundaries:

- separate production and non-production AWS accounts
- dedicated tooling or platform account where justified
- cluster-specific controller roles
- least-privilege cross-account roles
- repository path and project restrictions per environment

### Central versus per-cluster controllers

**Central Argo CD** provides one management plane but creates a high-value and potentially broad blast radius.

**Per-cluster controllers** improve isolation and local autonomy but increase fleet-management overhead.

A hybrid model can use per-environment or per-cell controllers with centrally generated configuration.

The answer should tie controller topology to failure-domain and team-ownership requirements.

---

## 15. Recovery scenarios

### Git repository unavailable

Existing workloads continue running. Reconciliation and new deployments stop. Alert on source fetch failure and restore repository access without bypassing desired-state control.

### GitOps controller unavailable

Existing workloads normally continue. Repair or restore the controller from the bootstrap source. Avoid emergency manual changes unless the incident requires them; commit every emergency mutation back to Git immediately.

### Bad commit merged

- stop further promotions
- revert the commit
- allow the controller to reconcile
- verify user SLIs recover
- investigate why validation or rollout analysis failed

### CRD/controller incompatibility

Restore the compatible controller or CRD version in the documented order. Back up custom resources before risky CRD changes and test conversion webhooks.

### Terraform fails before GitOps bootstrap

Use Terraform recovery against the infrastructure state. Do not ask Argo CD or Flux to compensate for AWS resources it does not own.

### Terraform destroys the cluster

Recreate infrastructure from Terraform, bootstrap GitOps, and let Git reconstruct in-cluster desired state. Persistent data recovery must come from the relevant AWS backup and restore design, not from Git.

---

## 16. Observability

Monitor the delivery system itself.

### Terraform

- plan/apply duration and failure rate
- lock contention
- provider throttling
- drift detection results
- destructive changes
- age of unapplied approved change

### Argo CD

- application sync and health status
- reconciliation duration
- repository fetch failures
- comparison errors
- pending operations
- controller queue depth

### Flux

- source readiness
- Kustomization and HelmRelease readiness
- reconcile duration and failures
- stalled resources
- image automation failures

### Delivery SLIs

- commit-to-production lead time
- deployment frequency
- change failure rate
- rollback or recovery time
- percentage of production changes made through the approved path
- percentage of applications with verified immutable artifacts

---

## 17. Argo CD versus Flux

| Consideration | Argo CD | Flux |
|---|---|---|
| Operating model | application-centric | composable controller toolkit |
| UI | rich built-in UI | commonly CLI/Git first; ecosystem UIs available |
| Fleet generation | ApplicationSet | Kustomization and source composition |
| Progressive delivery | Argo Rollouts | Flagger commonly paired |
| Dependency tools | sync waves/hooks/app structure | `dependsOn`, health checks |
| Best fit | teams wanting application visibility and centralized workflows | teams wanting Kubernetes-native composability and controller primitives |

The strongest answer does not claim one is universally superior. It selects from organizational workflow, security, fleet size, and operational skill.

---

## Adversarial follow-ups

### “Why not let Terraform manage every Helm release?”

Terraform can manage Helm, but long-term application reconciliation, drift visibility, progressive delivery, and independent release cadence are usually better handled by a Kubernetes-native GitOps controller. I would keep Terraform ownership only where its lifecycle and dependency model are truly the best fit.

### “How do you make an emergency change?”

Use a documented break-glass path with strong identity, audit, time-bounded privilege, and incident approval. Apply the minimum mitigation, then immediately reconcile Git to the intended state. Break-glass must not become a second routine deployment system.

### “Should self-heal always be enabled?”

Not blindly. It is appropriate for well-scoped application resources where Git is unquestionably authoritative. For destructive, data-bearing, or shared platform resources, I may require explicit sync or additional safeguards.

### “What if the GitOps controller applies a bad change everywhere?”

Use environment and cell boundaries, staged promotion, controller scope restrictions, ApplicationSet or Kustomization rollout discipline, and SLI-based progressive delivery. GitOps improves consistency; without blast-radius controls it can also distribute a mistake consistently.

### “How do you roll back Terraform?”

Terraform is not an application rollback engine. I create a new reviewed configuration that safely converges from the current real state. I do not blindly reverse a commit when the infrastructure operation is irreversible or stateful.

---

## Weak answers to avoid

- “GitOps means GitHub Actions runs kubectl.”
- “Terraform creates the cluster, then Argo manages everything” without defining the bootstrap boundary.
- allowing Terraform and Argo CD to manage the same object
- storing plaintext secrets in a private Git repository
- promoting mutable tags such as `latest`
- treating a green Deployment as successful release evidence
- claiming every drift should be auto-repaired
- using manual production patches without reconciling Git

---

## Closing statement

> My GitOps design has one owner per resource, one immutable artifact promoted through environments, one auditable desired-state path, and multiple layers of blast-radius control. Terraform establishes AWS infrastructure; Argo CD or Flux continuously reconciles Kubernetes state; neither tool is allowed to silently compete with the other.