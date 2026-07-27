# Secret Authority, Delivery, Rotation, and Kubernetes Integration

## Why this exists

Secrets are not configuration strings that happen to be hidden. They are authorization material with a lifecycle: issuance, delivery, use, rotation, revocation, expiry, audit, and incident response.

A platform must prevent developers from copying long-lived credentials into Git, CI variables, images, Helm values, Terraform state, or shared Kubernetes Secrets. It must also deliver credentials reliably enough that security controls do not become the reason production cannot start or recover.

## What the interviewer is testing

A Staff or Principal candidate should be able to:

- identify the authoritative secret system and distinguish it from delivery caches;
- prefer workload identity and dynamic credentials over stored static secrets;
- choose between direct retrieval, sidecar/agent, CSI-mounted files, and synchronized Kubernetes Secrets;
- design authorization, namespace isolation, rotation, reload, revocation, and audit;
- explain External Secrets Operator, Secrets Store CSI Driver, Vault integrations, and cloud-native providers without treating them as equivalent;
- model failure during provider outage, controller outage, cluster restore, and regional failover;
- prevent secret-delivery controllers from becoming cross-tenant exfiltration paths;
- create measurable acceptance criteria and a safe migration from existing static credentials.

## Definitions

### Secret authority

The system that owns the credential value or can issue it. Examples include a cloud secret manager, Vault, a certificate authority, a database credential broker, or an identity provider.

### Secret reference

A non-sensitive pointer describing what a workload is authorized to retrieve. References can still be sensitive because they expose naming, tenancy, or architecture information, but they are not the credential value.

### Delivery cache

A copy created for consumption, such as a Kubernetes Secret, mounted file, process environment, agent cache, or node-local volume. A cache is not automatically authoritative.

### Static secret

A credential remains valid until explicitly rotated or revoked.

### Dynamic secret

A credential is issued on demand with a lease or expiry, commonly scoped to a role and workload identity.

### Rotation

Replacing or renewing credential material while maintaining service availability.

### Revocation

Invalidating credential use before its natural expiry.

## First principle: eliminate secrets where possible

Prefer this order:

```text
1. Native workload identity and direct authorization
2. Short-lived federated token exchange
3. Dynamic credential issued to workload identity
4. Automatically rotated static secret
5. Manually managed static secret as a temporary exception
```

Examples:

- A pod uses cloud workload identity to call object storage directly rather than retrieving a cloud access key.
- CI exchanges an OIDC token for a short-lived deployment role rather than storing a cloud key.
- An application receives a leased database credential from Vault rather than sharing one password across a team.
- A certificate is issued for a workload identity and rotated automatically rather than copied into a repository.

The best-managed long-lived secret is still usually worse than eliminating it.

## End-to-end model

```text
Workload starts
  -> obtains projected or platform workload identity
  -> authenticates to secret authority or delivery controller
  -> authorization maps identity to an exact secret path or dynamic role
  -> secret is fetched or issued
  -> delivered through file, API, memory, or Kubernetes Secret
  -> application confirms usable version
  -> lease is renewed or value rotates
  -> old version remains valid only for bounded overlap
  -> revocation and audit evidence remain available
```

Every arrow is a security and availability boundary.

## Source-of-truth matrix

| State | Authority | Cached or observed by |
|---|---|---|
| Secret value | secret manager, Vault, CA, credential broker | agent, CSI mount, Kubernetes Secret, process memory |
| Workload identity | Kubernetes and cloud identity systems | secret provider and audit logs |
| Access policy | secret authority and cloud IAM | platform catalog and policy reports |
| Desired secret reference | versioned workload or platform declaration | operator or CSI driver |
| Current delivered version | delivery controller and workload runtime | status, annotations, metrics |
| Rotation schedule | secret authority or owning service | platform inventory and alerts |
| Application reload state | application or rollout controller | telemetry and readiness evidence |

Do not let a generated Kubernetes Secret become the only copy of a credential that must survive cluster loss.

## Delivery patterns

## 1. Direct application retrieval

The application authenticates to the secret authority and retrieves or renews its credential through an SDK or API.

Benefits:

- secret may remain only in application memory;
- dynamic credentials and leases are natural;
- no Kubernetes Secret copy is required;
- application can react precisely to expiry and renewal.

Costs:

- every application must implement provider integration, retries, caching, and renewal correctly;
- provider SDK and authentication logic enter application code;
- startup and runtime depend directly on provider availability;
- migration across providers may be harder.

Use when the application can own credential lifecycle safely and the direct dependency is acceptable.

## 2. Agent or sidecar delivery

An agent authenticates on behalf of the pod, retrieves or renews secrets, and writes files or exposes a local API.

Benefits:

- application uses files or localhost interface;
- renewal logic is centralized;
- dynamic credentials are supported;
- secret can avoid Kubernetes etcd.

Costs:

- sidecar startup and lifecycle coupling;
- shared filesystem permissions;
- reload signaling;
- agent resource and upgrade overhead;
- race conditions between application and initial render;
- a compromised application may still read its delivered secret.

## 3. CSI-mounted secret files

The Secrets Store CSI Driver and provider plugins can mount external secrets into pod volumes. Some configurations can also synchronize mounted content into Kubernetes Secret objects.

Benefits:

- application consumes files;
- secret value can avoid being stored in Kubernetes Secret objects when sync is disabled;
- provider-specific authentication remains outside application code;
- rotation can update mounted content when supported and configured.

Costs:

- node plugin and provider components become part of pod startup;
- rotation behavior varies by provider and application file handling;
- environment variables populated from a synchronized Kubernetes Secret do not update inside a running process;
- mounted files still need correct ownership and application reload behavior;
- provider or node failure may affect new pod starts.

## 4. Operator synchronization to Kubernetes Secrets

External Secrets Operator, Vault Secrets Operator, and similar controllers reconcile external values into Kubernetes Secret objects.

Benefits:

- applications use native Kubernetes Secret references;
- existing workloads require fewer changes;
- controller status exposes synchronization conditions;
- templating and refresh policies can be centralized;
- rollout restart can be integrated in some systems.

Costs:

- secret values are copied into Kubernetes etcd and API objects;
- anyone with Secret read access, node access, or broad backup access may gain the values;
- controller permissions and external-provider access can create broad exfiltration paths;
- refresh and application reload are separate problems;
- deleting the external reference may not immediately revoke an already delivered value.

Use synchronized Secrets as a compatibility and product choice, not as the default for every workload.

## 5. CI-time secret injection

Secrets are obtained by CI and inserted into artifacts or deployment values.

This is usually dangerous. Build artifacts, logs, caches, provenance, and pull requests can preserve values beyond intended lifetime.

Acceptable cases are narrow, such as signing through a remote KMS operation where the key never enters CI. Prefer workload identity and runtime retrieval for runtime credentials.

## Kubernetes Secret risk model

Kubernetes Secrets are API objects. Base64 encoding is not encryption.

Protect them through:

- etcd encryption at rest with managed and rotated keys;
- strict RBAC and avoidance of broad `list` or `watch` permissions;
- separation of tenant and platform operator access;
- audit logging for Secret reads and policy changes;
- node and kubelet hardening;
- admission restrictions on service-account and volume references;
- encrypted backups and controlled restore access;
- short-lived values and frequent rotation;
- avoiding environment variables where process inspection, crash dumps, or child-process inheritance create risk;
- preventing secrets in logs, events, metrics, traces, or support bundles.

A namespace administrator who can create pods may often be able to consume service accounts or Secrets in that namespace unless policy prevents it.

## External Secrets Operator

External Secrets Operator (ESO) reconciles `ExternalSecret` resources through `SecretStore` or `ClusterSecretStore` configuration and writes Kubernetes Secrets.

Security boundaries:

- Prefer namespaced `SecretStore` resources where tenant isolation matters.
- Treat `ClusterSecretStore` and `ClusterExternalSecret` as privileged cluster-wide capabilities.
- Restrict who may create or modify secret stores and external secret references.
- Constrain namespaces allowed to use a cluster store.
- Disable unused providers and cluster-wide features where possible.
- Restrict controller egress to required APIs and private endpoints.
- Protect the controller, webhook, and cert-controller pods and credentials.
- Validate remote secret path prefixes so a tenant cannot reference another tenant's secret.
- Use controller classes or separate installations for materially different trust boundaries.

Current ESO APIs support different refresh policies, including periodic, change-driven, and create-once behaviors. The platform must choose deliberately because rotation expectations differ.

### ESO failure scenarios

- provider returns throttling or authorization errors;
- controller is unavailable;
- secret reference is valid but target template is malformed;
- old Kubernetes Secret remains after provider access is revoked;
- a cluster-wide store selector grants broader access than intended;
- target secret changes outside the controller and drift behavior surprises the user;
- rotation succeeds at the provider but the application continues using an old environment variable;
- external secret deletion removes or retains the target unexpectedly.

## Secrets Store CSI Driver

The driver mounts values from external providers into pod volumes through CSI integration.

Operational questions:

- Does the provider support rotation and what is the polling or renewal model?
- What happens to mounted content when the provider is unavailable?
- Can a new pod start from cached material, and is that acceptable?
- Is secret sync to Kubernetes enabled?
- How does the application detect atomic file replacement or changed symlink target?
- Are file permissions, `fsGroup`, SELinux, and read-only mounts correct?
- What is the behavior during node restart or provider plugin outage?
- How are provider identities scoped by namespace and service account?

Mounted rotation is not application rotation until the application reopens or reloads the file successfully.

## Vault integration choices

Vault can support:

- direct API retrieval;
- agent injection;
- CSI mounts;
- Vault Secrets Operator synchronization;
- dynamic database, cloud, PKI, and other leased credentials.

The choice depends on whether values may be copied into Kubernetes Secrets, whether the application can reload, and whether dynamic leases are required.

Vault authentication should use short-lived workload identity where possible. Avoid shared AppRole secret IDs or static tokens distributed across workloads.

Dynamic secret design must include:

- lease renewal behavior;
- maximum TTL;
- revocation propagation;
- database or provider cleanup;
- outage behavior if renewal fails;
- overlapping credential support;
- rate and quota limits on issuance;
- audit storage and privacy.

## Cloud-native secret managers

AWS Secrets Manager, Azure Key Vault, Google Secret Manager, and other providers offer managed storage, IAM integration, encryption, auditing, and rotation features.

The platform still owns:

- workload identity mapping;
- path and resource naming;
- tenant authorization boundaries;
- private network access and DNS;
- regional replication and failover expectations;
- provider quotas and throttling;
- delivery and reload mechanism;
- application fallback behavior;
- deletion and recovery;
- audit correlation.

A managed service does not automatically make every secret globally available or every rotation safe.

## Authorization model

Authorization should bind:

```text
workload identity
  + namespace or environment
  + secret path or dynamic role
  + allowed operation
  + audience and region
  + maximum TTL
```

Example conceptual contract:

```yaml
subject:
  cluster: prod-us-east-1-017
  namespace: payments-prod
  serviceAccount: payments-api
permissions:
  - read: secret/payments/prod/database
  - issue: database-role/payments-readwrite
constraints:
  maxTtl: 1h
  audience: vault.payments.internal
  region: us-east-1
```

Avoid identity policies that allow wildcard reads across every application in an environment.

## Secret naming and ownership

A secret catalog entry should include:

- owner;
- consuming service identities;
- authority and region;
- purpose and data classification;
- static or dynamic type;
- creation source;
- rotation owner and period;
- last successful rotation;
- maximum age;
- revocation procedure;
- dependencies and reload method;
- disaster-recovery behavior;
- deletion and recovery policy.

Do not put the value, sample value, or recoverable transformation into the catalog.

## Rotation is a distributed-system change

Rotation involves at least two versions:

```text
authority creates version N+1
  -> delivery systems propagate N+1
  -> applications load and prove N+1
  -> dependent service accepts N+1
  -> version N remains valid during bounded overlap
  -> N is revoked
```

Failure can occur at every step.

### Rotation strategies

#### Dual-read or dual-accept

The server accepts old and new credentials while clients migrate. This is safest for shared static secrets when supported.

#### New credential before old revocation

Issue a second database user, API key, certificate, or token; migrate clients; then remove the old credential.

#### Lease renewal

Dynamic credentials renew before expiry. Applications must stop or degrade safely when renewal cannot be completed.

#### Rolling restart

A controller updates a Kubernetes Secret and restarts workloads progressively. This is simple but can create broad disruption and does not prove the application connected successfully with the new value.

#### Live reload

Applications detect file or API changes and reload without restart. Test atomicity, partial reads, connection pools, and rollback.

## Application consumption patterns

### Environment variables

Benefits:

- widely supported;
- simple startup behavior.

Problems:

- values do not update in a running process;
- inherited by child processes;
- may appear in debugging, crash, or process-inspection paths;
- rotation usually requires restart;
- accidental logging is common.

### Files

Benefits:

- can be updated atomically;
- restrictive permissions are possible;
- common for certificates and keys.

Problems:

- application must reopen or reload;
- symlink and file-replacement semantics matter;
- backups or support tools may capture them;
- filesystem sharing and sidecars add boundaries.

### Local agent API

Benefits:

- can return short-lived or renewed values;
- avoids persistent file in some designs.

Problems:

- application depends on agent availability;
- local authorization and process isolation matter;
- caching and retry behavior must be defined.

### Direct remote API

Benefits and costs match direct retrieval: strongest lifecycle control but highest application integration burden.

## Startup and readiness

Do not make liveness depend directly on a temporarily unavailable secret provider. That can create restart storms.

Recommended model:

```text
startup probe:
  wait for required initial credential within bounded time

readiness:
  fail if the application cannot serve safely with current credential

liveness:
  fail only if the process cannot recover locally

background health:
  expose lease expiry, refresh errors, delivered version, and reload status
```

A service with a still-valid cached credential may remain ready during a provider outage, while alerting on shrinking expiry margin.

## Secret-provider outage

Design questions:

- Can existing workloads continue using a valid cached credential?
- Can new pods start?
- Can leases renew?
- What happens when a credential expires during the outage?
- Is there a regional replica or secondary authority?
- Does failover preserve identity and authorization policy?
- Can emergency credentials be issued without bypassing audit?
- How is stale-cache use bounded and visible?

Do not retry aggressively against a degraded authority. Use bounded exponential backoff, jitter, and provider-aware rate limits.

## Regional and disaster-recovery design

Secrets are often the hidden blocker in regional failover.

Validate:

- secret authority availability in the recovery region;
- replicated values or independently issuable dynamic roles;
- regional KMS and key access;
- workload identity issuer and audience;
- DNS and private endpoint availability;
- certificate chain and trust bundle;
- policy and secret-reference replication;
- backup restore without restoring obsolete credentials;
- ability to revoke compromised regional credentials;
- application reload after failover.

A replicated encrypted blob is useless if the recovery region cannot access its encryption key or identity policy.

## CI/CD secrets

- use OIDC workload federation for cloud and registry access;
- separate pull-request and protected-release identities;
- never expose production credentials to untrusted forked code;
- mask logs but assume masking can fail;
- avoid secret values in command arguments, environment dumps, cache keys, test fixtures, or artifacts;
- pin reusable workflows and actions;
- rotate credentials after runner compromise;
- use KMS or remote signing operations rather than exporting private keys;
- restrict who can modify workflows that can request privileged tokens.

The pipeline definition is part of the secret authorization boundary.

## Terraform and secrets

Terraform state can persist secret values even when output is marked sensitive.

Controls:

- prefer references and identity configuration over fetching values into Terraform;
- avoid data sources that materialize secret values unless necessary;
- use remote encrypted state with strict access and audit;
- separate state by trust and lifecycle boundary;
- redact plans and logs;
- rotate any value exposed during debugging;
- understand provider behavior for write-only and sensitive fields;
- avoid generating application secrets with Terraform when a dedicated authority should own rotation.

"Sensitive" typically controls display, not whether the value exists in state.

## Policy controls

Validate:

- no literal secret values in manifests or Git;
- approved secret provider and store type;
- namespace and service-account binding;
- allowed remote path prefix;
- target Secret type and name;
- refresh and deletion policy;
- maximum static-secret age;
- no cross-tenant cluster store use;
- required owner and rotation metadata;
- restricted environment-variable use for high-risk material;
- no wildcard export of all remote keys;
- no unapproved push from Kubernetes back into the authority.

Policy errors must name the exact field and remediation path without echoing secret material.

## Failure modes

- a shared controller can read every tenant secret;
- a tenant changes a remote reference to another team's path;
- an operator syncs secrets correctly but the application never reloads;
- rotation revokes the old credential before all clients move;
- Kubernetes restore resurrects expired or compromised Secrets;
- an environment variable remains stale after Secret update;
- an external provider outage blocks every new pod;
- a secret appears in logs, traces, events, or Terraform state;
- certificate rotation omits the trust bundle or intermediate chain;
- dynamic credential issuance overwhelms a database or provider quota;
- deletion of an `ExternalSecret` unexpectedly deletes or preserves the target;
- a regional failover uses a secret value that the destination cannot decrypt;
- broad CI identity can retrieve production credentials from feature branches.

## Incident response

For suspected secret exposure:

1. Declare impact and identify the exact credential, versions, authority, consumers, and environments.
2. Preserve authority audit logs, identity-token exchanges, Kubernetes audit, CI logs, and runtime evidence without copying values unnecessarily.
3. Stop further exposure: disable the workflow, revoke access policy, quarantine the workload, or block the exfiltration path.
4. Issue a replacement credential through a trusted path.
5. Migrate consumers and prove the new version is in use.
6. Revoke old versions and related sessions or leases.
7. Search logs, artifacts, state, backups, images, and support bundles for copies.
8. Evaluate downstream access performed with the credential.
9. Repair authorization, delivery, and detection controls.
10. Run a rotation and revocation game day.

Rotation without session revocation may not contain an already-issued token or database connection.

## Observability and SLOs

Useful signals:

- secret retrieval and issuance availability;
- p95 initial delivery time;
- refresh and renewal success rate;
- remaining lease or certificate lifetime;
- delivered version versus authority version;
- application reload confirmation;
- controller queue age and provider throttling;
- authorization denials by workload identity;
- stale secret count;
- rotation completion time;
- percentage of credentials that are dynamic or automatically rotated;
- static-secret age and exception count;
- cross-tenant reference attempts;
- time to revoke a credential and identify every consumer;
- new-pod startup success during provider degradation.

A secret platform SLO should distinguish existing-workload continuity from new-workload startup.

## Rollout and migration

1. Inventory secret values, owners, consumers, and copies.
2. Eliminate cloud keys through workload identity.
3. Move remaining values to an authoritative secret system.
4. Introduce references and a delivery pattern for one workload class.
5. Add status, audit, and reload evidence.
6. Rotate the credential through the new path.
7. remove copies from Git, CI, Terraform state where possible, images, and documentation.
8. Enforce policy against new literal secrets.
9. Migrate by tenant and environment.
10. Test provider outage, regional recovery, rotation, and revocation.

Deleting a secret from Git does not remove it from history. Treat exposed values as compromised and rotate them.

## 90-second interview answer

> I start by eliminating secrets through workload identity and short-lived federation. For remaining credentials, I define one authority, exact workload-to-path authorization, a bounded delivery mechanism, rotation and revocation behavior, and evidence that the application loaded the current version. I choose direct retrieval or dynamic leases when applications can own renewal, CSI or agent-mounted files when I want to avoid Kubernetes Secret copies, and operator synchronization when native Kubernetes compatibility is worth storing the value in etcd. External Secrets Operator, the Secrets Store CSI Driver, and Vault operators solve different delivery problems and have different controller, node, and reload failure modes. I prefer namespaced stores, restrict cluster-wide controllers and remote path prefixes, and use workload identity rather than static provider credentials. Rotation uses overlapping versions or leased renewal, followed by application proof and old-version revocation. I measure delivery latency, renewal success, expiry margin, stale versions, reload confirmation, revocation time, and startup behavior during provider outage.

## Adversarial follow-ups

### "Are Kubernetes Secrets secure?"

They can be protected, but they are API objects accessible through RBAC, nodes, backups, and controllers. Base64 is not encryption. I use etcd encryption, strict access, audit, short lifetimes, and avoid copying values there when the risk does not justify it.

### "Why not use External Secrets Operator for everything?"

It creates Kubernetes Secret copies and introduces a privileged reconciliation plane. It is excellent for compatibility, but dynamic credentials, high-risk keys, or workloads that can retrieve directly may need another pattern.

### "Does CSI rotation update the application?"

It can update mounted content when supported, but the application must reopen or reload the file. Environment variables derived from a Secret remain unchanged in a running process.

### "What happens when Vault or the cloud secret manager is down?"

Existing workloads may continue with valid cached credentials, while new starts or renewals can fail. I expose expiry margin, use bounded retry, design regional authority access, and define behavior when validity expires rather than restarting endlessly.

### "How do you rotate a database password without downtime?"

Create a second credential or dynamic role, distribute and verify it, allow bounded overlap, move connection pools, then revoke the old credential and sessions. A single in-place overwrite is risky unless both client and server behavior are proven.

## Dangerous answers

- "Kubernetes Secrets are encrypted because they are base64 encoded."
- "We rotate the secret by updating it in the secret manager."
- "The sidecar handles everything."
- "All workloads can use one cluster-wide secret store."
- "Environment variables update when the Secret changes."
- "Sensitive Terraform values are not stored in state."
- "If the provider is down, liveness should restart the pod."
- "Deleting the Git commit removes the leaked secret."

## Whiteboard summary

```text
Eliminate secret where possible
  -> workload identity
  -> exact authorization
  -> authority
  -> delivery cache
  -> application reload proof
  -> overlap and rotation
  -> revocation
  -> audit and outage behavior
```

## Primary references

- Kubernetes Secret, ServiceAccount token, RBAC, encryption-at-rest, audit, and security checklist documentation.
- External Secrets Operator API, refresh policy, multi-tenancy, threat model, and security best-practice documentation.
- Secrets Store CSI Driver concepts, provider, rotation, synchronization, and security documentation.
- HashiCorp Vault authentication, agent, CSI, Vault Secrets Operator, dynamic secret, lease, and audit documentation.
- Official AWS Secrets Manager, Azure Key Vault, Google Secret Manager, workload identity, private endpoint, replication, and rotation documentation for deployed providers.
