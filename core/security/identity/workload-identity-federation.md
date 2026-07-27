# Workload Identity, Federation, SPIFFE, and Cloud-Native Authorization

## Interview scenario

Design workload identity for Kubernetes services running across AWS, Azure, Google Cloud, and private infrastructure. The system must avoid long-lived credentials, restrict every workload to least privilege, support cross-cloud access, survive partial identity-plane failure, and produce evidence strong enough for incident response and audit.

The Staff/Principal task is not to name an identity product. It is to define the complete trust chain, every authorization boundary, credential lifetime, failure behavior, rollout strategy, and proof that a compromised workload cannot become a platform-wide principal.

---

## 1. Ninety-second Staff/Principal answer

> I separate human identity, workload identity, node identity, and service-to-service authentication because they have different subjects, lifetimes, and blast radii. Every workload receives a short-lived identity derived from attributes that the platform can verify, such as cluster, namespace, ServiceAccount, node, process, environment, and trust domain. Static cloud keys do not belong in images, Git, CI variables, or Kubernetes Secrets.
>
> In Kubernetes, I use bounded projected ServiceAccount tokens with an explicit audience. The cloud or workload-identity system validates issuer, audience, subject, and other attributes before returning short-lived credentials. On EKS I choose Pod Identity or IRSA according to account topology and operational constraints; on AKS I use Microsoft Entra Workload ID; on GKE I use Workload Identity Federation for GKE. For portable service identity and mTLS, I use SPIFFE-compatible identities and an implementation such as SPIRE where the operating model justifies it.
>
> Authentication is not authorization. After proving who the workload is, the target resource still grants only the exact actions and resources required. I prevent fallback to broad node credentials, constrain role-passing and federation trust, separate environments, protect metadata endpoints, and treat the credential-provider chain as part of the threat model.
>
> I design token refresh, clock-skew tolerance, issuer-key rotation, regional survivability, and degraded behavior explicitly. The proof is an automated negative test: the intended workload succeeds, a different namespace or ServiceAccount fails, node credentials are unreachable, expired and wrong-audience tokens fail, and revocation or policy changes converge within the documented objective.

### Fifteen-second version

> Bind short-lived credentials to an exact workload identity, keep authentication separate from authorization, eliminate node-role and static-key fallback, and prove the entire issuer-to-resource chain with positive and negative tests.

---

## 2. Identity taxonomy

### Human identity

Represents a person or interactive operator.

Typical controls:

- Enterprise identity provider.
- MFA and device/risk policy.
- Short-lived sessions.
- Just-in-time elevation.
- Separate production roles.
- Break-glass workflow.
- Central audit.

### Workload identity

Represents a running application, controller, job, function, or process.

Desired properties:

- Short lifetime.
- Automatic issuance and rotation.
- Bound to verifiable runtime attributes.
- No human sharing.
- No reusable key file.
- Least-privilege authorization.
- Strong audit attribution.

### Node identity

Represents the VM, bare-metal host, or Kubernetes node.

A node identity is usually broader than an application identity because the node must bootstrap, join the cluster, pull images, manage networking, and operate storage or telemetry components.

A pod should not inherit the node identity merely because it runs on the node.

### Service identity

Represents the logical service participating in authenticated network communication.

It may be expressed through:

- Cloud IAM principal.
- SPIFFE ID.
- X.509 certificate SAN.
- OAuth/OIDC subject.
- Service-mesh identity.

### Device and CI identity

Devices, runners, deployment controllers, and automation systems need independent identities. Do not reuse an application runtime role for CI or a human administrator role for a controller.

---

## 3. The complete trust chain

```text
runtime workload
      |
      | obtains local projected token or SVID
      v
workload identity issuer / federation service
      |
      | validates issuer, subject, audience, attributes
      v
short-lived credential or authenticated channel
      |
      | target-side authorization policy
      v
specific resource and permitted action
```

A secure design answers these questions:

1. Who signs or vouches for the initial workload assertion?
2. How is the workload distinguished from another workload on the same node?
3. Which issuer, audience, and subject are accepted?
4. Which environment, cluster, namespace, or trust domain is included?
5. What credential is returned?
6. How long is it valid?
7. Which target resource accepts it?
8. Which exact actions are authorized?
9. What prevents fallback to a broader credential?
10. How quickly can trust be revoked or narrowed?
11. What survives if the issuer or network path is unavailable?
12. Which logs prove every step?

---

## 4. Kubernetes ServiceAccount identity

A Kubernetes ServiceAccount is an identity used by processes in pods when interacting with Kubernetes and, through federation, with external systems.

It is not automatically a cloud identity. A separate trust relationship maps the Kubernetes subject into a cloud or external principal.

### Projected ServiceAccount tokens

Modern Kubernetes workloads should use projected, time-bounded ServiceAccount tokens rather than manually created long-lived Secret-based tokens.

Conceptual claims:

```json
{
  "iss": "https://cluster-issuer.example",
  "sub": "system:serviceaccount:payments:ledger-api",
  "aud": ["sts.example"],
  "exp": 1785100000,
  "kubernetes.io": {
    "namespace": "payments",
    "serviceaccount": {"name": "ledger-api"},
    "pod": {"name": "ledger-api-7d9f"}
  }
}
```

Security-relevant claims:

- `iss` — who issued the token.
- `sub` — the ServiceAccount subject.
- `aud` — which recipient is intended to consume it.
- `exp` — expiration.
- Bound object information where configured and supported.

### Audience restriction

A token intended for the Kubernetes API should not automatically be accepted by a cloud STS, Vault, or another service.

Example projection:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ledger-api
  namespace: payments
spec:
  serviceAccountName: ledger-api
  automountServiceAccountToken: false
  containers:
    - name: app
      image: example/ledger@sha256:...
      volumeMounts:
        - name: identity-token
          mountPath: /var/run/identity
          readOnly: true
  volumes:
    - name: identity-token
      projected:
        sources:
          - serviceAccountToken:
              path: token
              audience: sts.example
              expirationSeconds: 3600
```

The exact audience and lifetime must match the relying system and platform constraints.

### Namespace and ServiceAccount reuse risk

The subject commonly includes namespace and ServiceAccount name. If multiple clusters or environments trust the same issuer or identity pool, identical subjects can collide unless cluster, project, trust domain, or environment boundaries are included elsewhere.

Do not assume:

```text
system:serviceaccount:payments:api
```

is globally unique.

---

## 5. Authentication is not authorization

Authentication answers:

> Which workload is this?

Authorization answers:

> May this workload perform this action on this resource now?

A valid workload identity must not imply broad access.

Example:

```text
Authenticated principal:
  payments/ledger-api in production cluster A

Authorized:
  read secret payments/ledger-db
  connect to database payments-writer
  publish to topic ledger-events

Not authorized:
  enumerate all secrets
  assume platform-admin
  access development signing keys
  modify IAM trust policy
```

Strong designs apply authorization at multiple boundaries:

- Cloud IAM role or policy.
- Resource policy.
- KMS/key policy.
- Database authorization.
- Service API authorization.
- Network policy.
- Service-mesh authorization.
- Admission policy.

Network reachability is not authorization, and mTLS identity is not authorization by itself.

---

## 6. AWS: EKS Pod Identity and IRSA

### EKS Pod Identity

Conceptual flow:

```text
Pod + Kubernetes ServiceAccount
      |
      v
EKS Pod Identity Agent on node
      |
      v
EKS Auth API
      |
      v
short-lived IAM role credentials
      |
      v
AWS SDK credential provider chain
```

Operational characteristics:

- Association is managed through the EKS API.
- It does not require a separate IAM OIDC provider for every cluster.
- The Pod Identity Agent is part of the credential path.
- Supported AWS SDK versions are required.
- The directly associated role is normally in the same account as the cluster.
- Cross-account access can use role chaining.
- Session tags can support attribute-based authorization.
- `iam:PassRole` for association management must be tightly controlled.

Example association command:

```bash
aws eks create-pod-identity-association \
  --cluster-name prod-a \
  --namespace payments \
  --service-account ledger-api \
  --role-arn arn:aws:iam::111122223333:role/prod-ledger-api
```

Failure modes:

- Agent absent or unhealthy.
- Unsupported SDK.
- Proxy intercepts or blocks the agent endpoint.
- Wrong association.
- Role trust or authorization policy denies access.
- Association operator can pass an unintended role.
- Application chooses static environment credentials earlier in the provider chain.

### IRSA

Conceptual flow:

```text
projected ServiceAccount token
      |
      v
IAM OIDC provider trust
      |
      v
STS AssumeRoleWithWebIdentity
      |
      v
short-lived role credentials
```

Example trust-policy intent:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111122223333:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
          "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:payments:ledger-api"
        }
      }
    }
  ]
}
```

Operational characteristics:

- Mature and broadly used.
- OIDC provider lifecycle is per cluster/trust design.
- Direct cross-account trust can be expressed.
- Trust policy must constrain exact subject and audience.
- STS request behavior and SDK credential caching matter at scale.

### Choosing between them

Use Pod Identity when:

- Same-account role association fits.
- Central association management is desirable.
- Supported SDKs and the agent are acceptable dependencies.
- Session tags and simplified cluster setup are useful.

Use IRSA when:

- Existing fleets already operate it safely.
- Direct web-identity trust across accounts is valuable.
- Avoiding the Pod Identity Agent is important.
- The OIDC-provider operating model is already mature.

Do not present the choice as a religious preference. State the account topology, failure model, SDK constraints, and migration cost.

### Protect the node role

Controls:

- Keep node permissions limited to node functions.
- Move add-on permissions to workload identity where supported.
- Require IMDSv2.
- Restrict pod access to instance metadata.
- Validate that an unauthorized pod cannot obtain node credentials.
- Separate sensitive workloads onto stronger node boundaries where justified.

Workload identity does not help if the application silently falls back to a broad node role.

---

## 7. Azure: Microsoft Entra Workload ID for AKS

Conceptual flow:

```text
AKS projected ServiceAccount token
      |
      v
Microsoft Entra federated identity credential
      |
      v
short-lived Entra access token
      |
      v
Azure resource authorization
```

The federated identity credential binds:

- OIDC issuer.
- Subject such as `system:serviceaccount:payments:ledger-api`.
- Audience, commonly `api://AzureADTokenExchange` for this flow.
- User-assigned managed identity or application registration.

Example intent:

```bash
az identity federated-credential create \
  --name prod-ledger-api \
  --identity-name prod-ledger-api \
  --resource-group identity-prod \
  --issuer "$AKS_OIDC_ISSUER" \
  --subject system:serviceaccount:payments:ledger-api \
  --audience api://AzureADTokenExchange
```

Then grant the Azure identity only the required resource role.

Failure modes:

- Issuer changed after cluster replacement.
- Subject or audience mismatch.
- Federated credential attached to the wrong identity.
- Role assignment too broad in scope.
- Multiple environments share one identity.
- Application uses a client secret or another credential earlier in its chain.
- SDK version or configuration does not support workload identity.
- Key Vault, Storage, or resource firewall blocks the path after authentication succeeds.

A successful token exchange does not prove resource authorization or network reachability.

---

## 8. Google Cloud: Workload Identity Federation for GKE

Conceptual flow:

```text
Kubernetes ServiceAccount identity
      |
      v
GKE metadata server / federation path
      |
      v
Security Token Service
      |
      v
short-lived federated token
      |
      v
direct IAM principal binding or service-account impersonation
```

Design choices:

- Grant the Kubernetes principal direct access where supported.
- Or allow it to impersonate a Google IAM service account when that compatibility boundary is required.

Security considerations:

- Namespace and ServiceAccount identifiers can collide across clusters in the same identity pool.
- Use project and trust boundaries deliberately.
- Avoid service-account key files.
- Protect against legacy credential files or environment variables overriding federation.
- Account for metadata-server startup, limits, and per-node behavior.
- Separate node service-account permissions from workload permissions.

Failure modes:

- GKE metadata server not ready.
- IAM binding references the wrong principal format.
- Cross-project role missing.
- Unsupported API requires service-account impersonation.
- Token request concurrency or timeout pressure.
- Node credential fallback.
- A cluster operated by another trust domain can create the same namespace and ServiceAccount identity.

---

## 9. Cross-cloud federation

Cross-cloud access should exchange short-lived assertions rather than copy a target-cloud secret into the source cloud.

Example:

```text
AWS workload identity
      |
      | signed assertion
      v
Microsoft Entra federated trust
      |
      | short-lived token
      v
specific Azure API
```

Required controls:

- Exact issuer.
- Exact audience.
- Exact subject or bounded attribute expression.
- Environment and cluster boundary.
- Minimal target permission.
- Short session duration.
- No static-secret fallback.
- Rate limits and anomaly detection.
- Revocation and trust-removal procedure.
- Audit on both sides.

Cross-cloud federation removes keys but creates a trust bridge. A compromised issuer or broad subject condition can become a cloud-to-cloud escalation path.

Prefer a small number of explicit federation relationships over one universal identity broker trusted by every environment.

---

## 10. SPIFFE and SPIRE

SPIFFE defines a portable workload-identity framework.

Core elements:

- **SPIFFE ID:** workload name in a trust domain.
- **SVID:** verifiable identity document, commonly X.509-SVID or JWT-SVID.
- **Workload API:** local API through which a workload obtains and rotates identity material.
- **Trust bundle:** material used to validate identities from a trust domain.

Example SPIFFE ID:

```text
spiffe://prod.example.com/ns/payments/sa/ledger-api
```

SPIRE is an implementation of SPIFFE that performs node and workload attestation and issues SVIDs according to registration and selector policy.

Conceptual flow:

```text
SPIRE Agent proves node identity to SPIRE Server
      |
      v
local workload connects to Workload API
      |
      v
agent attests process / workload attributes
      |
      v
workload receives rotating SVID and trust bundle
```

### Node attestation

Establishes that the agent is running on an approved node or platform instance.

### Workload attestation

Uses selectors and runtime attributes to determine which identity a process may receive.

### X.509-SVID

Useful for mTLS and certificate-based authentication.

### JWT-SVID

Useful for token-based authentication where the relying party validates issuer, audience, signature, and subject.

### Federation between trust domains

Federation lets workloads in one trust domain authenticate workloads in another. It must not automatically grant authorization.

Risks:

- Broad selector rules.
- Compromised node attestor.
- Workload API socket exposed across hosts.
- Trust-bundle distribution failure.
- Clock skew.
- One online signing authority becoming a global dependency.
- Confusing identity acceptance with application permission.

---

## 11. Credential-provider chain as a security boundary

Applications often search for credentials in a provider-specific order.

Possible sources:

- Environment variables.
- Local credential file.
- Explicit application configuration.
- Web-identity token.
- Pod Identity or metadata endpoint.
- Node instance profile.

A platform migration can appear successful while the application is still using an old static key.

Validation must record the actual caller identity and disable competing credential sources.

Examples:

```bash
aws sts get-caller-identity
az account get-access-token --resource https://management.azure.com/
gcloud auth print-access-token >/dev/null
```

Provider commands prove only part of the chain. Also inspect cloud audit logs to confirm the intended principal and session attributes.

---

## 12. Token lifecycle and failure behavior

### Lifetime

Shorter tokens reduce exposure but increase dependency on refresh infrastructure.

Choose lifetime from:

- Expected isolation period.
- Revocation objective.
- Issuer availability.
- Application refresh behavior.
- Clock-skew tolerance.
- Risk of credential theft.

### Refresh

Test:

- Refresh before expiry.
- Issuer latency.
- Temporary network failure.
- Token file rotation.
- SDK cache behavior.
- Process suspension and resume.
- Large-scale simultaneous refresh.

### Issuer-key rotation

Relying parties must refresh signing keys or trust bundles without accepting unknown keys indefinitely.

Test:

- Old and new key overlap.
- Cached JWKS behavior.
- Rollback.
- Stale cache.
- Regional distribution delay.

### Identity-provider outage

Define separately:

- Existing workload with cached valid credentials.
- New pod startup.
- Credential refresh.
- Cross-region or cross-cloud token exchange.
- Break-glass operation.

Do not extend all token lifetimes as an automatic availability fix. That trades an availability problem for a larger compromise window.

---

## 13. Identity and secrets are different systems

A cloud API credential should usually be replaced by workload identity.

Other secrets may still exist:

- Third-party API token.
- Database password.
- Signing key.
- Encryption key.
- TLS private key where another identity system is not used.

Preferred patterns:

| Requirement | Preferred control |
|---|---|
| Cloud API authentication | Workload identity |
| Service mTLS identity | Short-lived certificate or SPIFFE SVID |
| Database access | Dynamic or identity-based authentication where supported |
| Signing operation | KMS/HSM operation rather than key export |
| Third-party static token | Regional secret store with rotation and bounded access |

Do not call a replicated static access key “workload identity.”

---

## 14. Least-privilege design

Default to one role, managed identity, service account, or policy boundary per application security domain.

A boundary may contain several replicas because replicas of the same service generally share one authorization identity.

Avoid:

- One role per namespace with unrelated applications.
- One cluster-wide cloud role.
- Wildcard subjects across all namespaces.
- Resource permissions using `*` without a documented requirement.
- Trust policies editable by application workloads.
- Broad `iam:PassRole` or equivalent identity delegation.
- Production and development sharing one principal.

At very large scale, ABAC can reduce role count, but only when resource policies enforce bounded attributes and operators can prove that tags or claims cannot be forged.

---

## 15. Incident investigation workflow

### Step 1 — Establish impact

- Which workload cannot authenticate?
- Is failure limited to one node, namespace, cluster, account, region, or cloud?
- Are existing sessions working while new sessions fail?
- Which customer journey is affected?

### Step 2 — Identify the credential actually selected

Inspect:

- Environment variables.
- Mounted token files.
- SDK version and provider order.
- Metadata access.
- Sidecars or agents.
- Actual caller identity.

### Step 3 — Decode the initial assertion safely

Validate:

- Issuer.
- Subject.
- Audience.
- Expiration and not-before.
- Namespace and ServiceAccount.
- Cluster or trust-domain context.

Do not paste production tokens into public websites.

### Step 4 — Inspect trust mapping

AWS:

```bash
aws eks list-pod-identity-associations --cluster-name <cluster>
aws eks describe-pod-identity-association \
  --cluster-name <cluster> --association-id <association-id>
aws iam get-role --role-name <role>
```

Kubernetes:

```bash
kubectl get sa -n <namespace> <service-account> -o yaml
kubectl get pod -n <namespace> <pod> -o yaml
kubectl create token <service-account> \
  -n <namespace> --audience=<audience> --duration=10m
```

Azure:

```bash
az aks show -g <resource-group> -n <cluster> --query oidcIssuerProfile
az identity federated-credential list \
  --identity-name <identity> --resource-group <resource-group>
az role assignment list --assignee <principal-id>
```

GCP:

```bash
gcloud container clusters describe <cluster> \
  --region <region> \
  --format='value(workloadIdentityConfig.workloadPool)'
gcloud projects get-iam-policy <project>
```

### Step 5 — Separate authentication, authorization, and networking

Classify:

```text
No token issued          -> assertion, issuer, agent, SDK, or federation
Token issued, API denied -> authorization or resource policy
Token issued, timeout    -> DNS, route, firewall, proxy, endpoint, or service health
Wrong principal used     -> provider-chain or fallback issue
```

### Step 6 — Preserve evidence

Capture:

- Token-exchange request ID.
- Cloud audit event.
- Principal and session attributes.
- Policy version.
- Issuer and trust-bundle version.
- Pod UID, node, namespace, ServiceAccount, image digest.
- Deployment and identity changes around incident start.

### Step 7 — Mitigate without widening trust

Possible mitigations:

- Restore failed agent or metadata path.
- Roll back a trust-policy change.
- Reissue a correct association.
- Restore a regional issuer dependency.
- Pin a working SDK version.
- Move workload to a healthy node pool.
- Use a narrowly scoped break-glass role through audited automation.

Do not fix an outage by wildcarding the subject or attaching administrator access.

---

## 16. Validation matrix

Positive tests:

- Correct workload obtains a short-lived credential.
- Correct resource operation succeeds.
- Credential rotates without restart where expected.
- Audit event identifies the workload.

Negative tests:

- Same ServiceAccount name in another namespace fails.
- Same namespace and ServiceAccount in another environment fails when required.
- Default ServiceAccount fails.
- Wrong audience fails.
- Expired token fails.
- Tampered token fails.
- Unauthorized resource action fails.
- Pod cannot obtain node credentials.
- Static key and local credential file are absent.
- Revoked trust stops new sessions within objective.

Availability tests:

- Issuer temporarily unavailable.
- Agent restarted.
- Node isolated.
- JWKS or bundle rotation delayed.
- Clock skew.
- Large simultaneous token refresh.
- Region or inter-cloud link unavailable.

---

## 17. Rollout strategy

1. Inventory all static credentials and current node-role usage.
2. Classify human, CI, node, controller, and application identities.
3. Define naming and trust domains.
4. Create one least-privilege workload identity for a low-risk service.
5. Add explicit audience-bound token projection where needed.
6. Remove competing static credentials from the application.
7. Prove the actual caller identity in audit logs.
8. Block node credential access and run negative tests.
9. Introduce rotation and issuer-failure tests.
10. Migrate one namespace, cluster, and environment at a time.
11. Revoke old credentials only after evidence shows no use.
12. Add policy checks preventing regression.

Migration success is not “the new role exists.” It is “the old credential path can no longer be used.”

---

## 18. Observability and SLOs

Identity signals:

- Token issuance success and latency.
- Refresh success and latency.
- Failure by issuer, audience, subject, and policy reason.
- Credential age.
- Use of static credentials.
- Node-role credential requests from pods.
- Role assumption and role chaining.
- Agent and metadata-service availability.
- Trust-bundle and JWKS age.

Authorization signals:

- Denied actions by principal and resource.
- Unexpected resource scope.
- Wildcard-policy findings.
- Privilege-escalation attempts.
- Role-passing or delegation events.

Example objectives:

- 99.99% successful token issuance for valid workloads.
- p99 credential acquisition below the application startup budget.
- No static cloud keys detected in runtime inventory.
- 100% of privileged role assumptions attributable to workload, environment, and deployment.
- Trust-policy revocation effective for new sessions within the documented target.

---

## 19. Common weak answers

### “Use Kubernetes Secrets for cloud keys”

This protects neither credential lifetime nor reuse and creates another copy in etcd and pod memory.

### “mTLS solves authorization”

mTLS authenticates peers and protects transport. Authorization still needs explicit policy.

### “All pods can use the node role”

This makes any pod compromise a node-wide credential compromise.

### “Use one identity per cluster”

This destroys workload-level attribution and least privilege.

### “Make tokens long-lived so identity outages do not matter”

This increases the stolen-credential window and postpones rather than solves availability design.

### “SPIFFE replaces cloud IAM”

SPIFFE can provide portable workload authentication. Cloud APIs still require a supported trust exchange and resource authorization.

### “Pod Identity always replaces IRSA”

The correct choice depends on account topology, SDK support, agent dependency, cross-account trust, and migration state.

---

## 20. Adversarial interview questions

### Why not put a cloud access key in a secret manager?

Because secure storage does not remove the key's long lifetime, replayability, copying, rotation burden, or weak workload attribution. Prefer federation into short-lived credentials.

### What if the identity issuer is down?

Separate existing cached sessions, new workload startup, and refresh. Keep critical serving paths regionally survivable, use bounded credential lifetimes, and avoid making one global online issuer the only dependency.

### How do you prove the pod is not using the node role?

Remove static credentials, inspect provider-chain configuration, call the identity endpoint from the pod, inspect cloud audit logs, and run a negative test against an action available only to the node role.

### Why is audience important?

It prevents an assertion created for one relying party from being replayed to another relying party that should not accept it.

### Does a SPIFFE certificate authorize access?

No. It proves the presented workload identity under a trust bundle. The receiving service still applies authorization policy.

### How do you prevent identical Kubernetes subjects in two clusters from colliding?

Use separate issuers, projects, pools, trust domains, environment-bound policies, cluster attributes, or other explicit isolation. Do not assume namespace and ServiceAccount alone are globally unique.

---

## 21. Staff/Principal answer checklist

A strong answer includes:

- Clear identity taxonomy.
- Exact trust chain.
- Audience-bound short-lived tokens.
- Separate authentication and authorization.
- Cloud-native mechanism comparison.
- Node-role and metadata protection.
- Provider-chain analysis.
- Cross-cloud federation constraints.
- SPIFFE/SPIRE role and limitations.
- Rotation and issuer-outage behavior.
- Negative tests.
- Migration proof that old credentials are gone.

---

## Primary references

- [Kubernetes ServiceAccounts](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [Kubernetes projected volumes](https://kubernetes.io/docs/concepts/storage/projected-volumes/)
- [Amazon EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [Amazon EKS identity and access management best practices](https://docs.aws.amazon.com/eks/latest/best-practices/identity-and-access-management.html)
- [Microsoft Entra Workload ID for AKS](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Workload Identity Federation for GKE](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/workload-identity)
- [SPIFFE standard](https://spiffe.io/docs/latest/spiffe-specs/spiffe/)
- [SPIRE concepts](https://spiffe.io/docs/latest/spire-about/spire-concepts/)
