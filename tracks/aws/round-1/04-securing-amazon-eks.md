# Question 4 — Securing Amazon EKS with IAM, Pod Identity, VPC Controls, Security Groups, and Secrets Manager

## Interview prompt

Describe how you secure an Amazon EKS cluster using IAM, IRSA, VPC networking, Security Groups, and AWS Secrets Manager.

## Current-version note

IRSA remains fully supported. For many new workloads, EKS Pod Identity is now the preferred default because it avoids creating a separate OIDC provider per cluster and simplifies role association. The correct answer compares both rather than pretending only one exists.

---

## 90-second Staff/Principal answer

> I secure EKS in layers: human control-plane access, workload identity, network segmentation, pod and node hardening, secret delivery, supply-chain security, and detective controls.
>
> Humans authenticate through federated IAM roles with short-lived credentials. I use EKS access entries and least-privilege Kubernetes RBAC, separate admin from read-only and deployment roles, and keep break-glass access rare and audited. The cluster API is private where the operating model supports it, or the public endpoint is restricted to approved CIDRs and protected by strong identity.
>
> Pods never inherit broad node-role permissions. I assign one least-privilege role per application through EKS Pod Identity or IRSA, require IMDSv2, restrict pod access to instance metadata, and constrain `iam:PassRole` and cross-account trust. Network controls include private subnets, tightly scoped cluster and node security groups, VPC endpoints, Kubernetes NetworkPolicy, and Security Groups for Pods where AWS-resource-level segmentation is needed.
>
> Secrets remain in Secrets Manager encrypted with KMS and are delivered through External Secrets or the Secrets Store CSI driver. I design rotation, reload, and failure behavior explicitly and prevent values from entering Git, images, Terraform state, or logs. I also enforce Pod Security Standards, non-root execution, read-only filesystems, image digest pinning and scanning, admission policy, audit logging, CloudTrail, GuardDuty, Config, Security Hub, and tested incident-response procedures.

---

## 1. Threat model first

State what you are protecting against:

- stolen developer or CI credentials
- overprivileged cluster administrators
- compromised application pods
- pod-to-pod lateral movement
- pod escape to the node
- access to node instance-profile credentials
- malicious or vulnerable container images
- secret theft from Git, logs, volumes, or Kubernetes Secrets
- exposed Kubernetes API endpoints
- compromised GitOps or admission controllers
- data exfiltration through unrestricted egress
- unsafe multi-tenancy
- supply-chain tampering
- destructive automation or ransomware-like API activity

Security is not one IAM policy. It is a set of independent controls designed so one compromised layer does not grant the entire platform.

---

## 2. Human access to the cluster

### Federated IAM identities

Use AWS IAM Identity Center or another enterprise identity provider to issue short-lived sessions.

Avoid:

- IAM users with long-lived access keys
- shared kubeconfig files
- permanent `system:masters` access
- one cluster-admin role used by CI and humans

### EKS access entries

Use EKS access entries and access policies where they fit the cluster version and operating model. They provide an AWS API-managed association between IAM principals and EKS access.

Separate roles such as:

- platform administrator
- security auditor
- application deployer
- read-only incident responder
- GitOps controller
- break-glass administrator

Then combine with Kubernetes RBAC for namespace and resource-level authorization.

### Kubernetes RBAC

Apply least privilege:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: payments
  name: deployer
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "patch", "update"]
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
```

Do not give application teams permission to create arbitrary:

- ClusterRoles and ClusterRoleBindings
- privileged pods
- hostPath volumes
- mutating or validating webhooks
- CRDs
- namespaces with unrestricted labels
- LoadBalancer Services in every namespace

### Break-glass access

A break-glass role should have:

- strong MFA or equivalent enterprise authentication
- explicit incident approval
- short session duration
- full CloudTrail and Kubernetes audit trail
- immediate post-incident review
- no routine use

Test it before an incident.

---

## 3. Kubernetes API endpoint exposure

### Private endpoint

Prefer a private API endpoint when administrators and automation can reach it through:

- VPN
- Direct Connect
- Transit Gateway
- approved VPC peering
- private CI runners
- a controlled management VPC

This reduces internet exposure but adds operational dependencies. Validate access during network incidents.

### Restricted public endpoint

When a public endpoint is required:

- restrict public access CIDRs
- use federated short-lived IAM authentication
- monitor failed access attempts
- avoid broad `0.0.0.0/0`
- keep a tested private or emergency access path

A private endpoint does not replace authorization. A compromised internal principal can still be dangerous.

---

## 4. Workload identity

### Do not rely on the node role

If every pod can inherit the EC2 instance profile, compromise of any pod may expose permissions intended for the node or other workloads.

Use workload-specific identity and restrict access to instance metadata.

### EKS Pod Identity

EKS Pod Identity associates a Kubernetes service account with an IAM role. The Pod Identity Agent runs on eligible nodes and supplies temporary credentials through supported AWS SDK credential chains.

Benefits:

- no separate OIDC provider per cluster
- simplified association management
- session tags useful for attribute-based access control
- no use of the account's normal STS request quota for pod credential vending

Constraints to discuss:

- the directly associated role is in the same account as the cluster
- cross-account access uses role chaining
- the person or automation creating the association needs controlled `iam:PassRole`
- supported SDK versions are required
- the Pod Identity Agent becomes a critical add-on

### IRSA

IRSA uses a cluster OIDC provider and projected service-account token. The AWS SDK calls `sts:AssumeRoleWithWebIdentity` to obtain temporary credentials.

Benefits:

- mature and broadly deployed
- direct cross-account trust can be expressed through web-identity role trust
- no Pod Identity Agent dependency

Constraints:

- OIDC provider configuration per cluster
- trust policy must tightly constrain namespace and service account
- STS usage and SDK session reuse matter at high scale

### Example IRSA trust policy intent

```json
{
  "Effect": "Allow",
  "Principal": {
    "Federated": "arn:aws:iam::111111111111:oidc-provider/oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE"
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE:aud": "sts.amazonaws.com",
      "oidc.eks.us-east-1.amazonaws.com/id/EXAMPLE:sub": "system:serviceaccount:payments:payments-api"
    }
  }
}
```

Do not use a wildcard allowing every service account in every namespace unless that is a deliberate and reviewed trust boundary.

### One role per application

Default to one role per workload or security boundary.

This improves:

- least privilege
- isolation
- audit attribution
- independent rotation and policy changes
- blast-radius analysis

At very large scale, carefully designed ABAC with Pod Identity session tags may reduce role proliferation, but it must not weaken resource authorization.

---

## 5. Node role and instance metadata

The node role should contain only node-required permissions.

Move permissions for components such as the VPC CNI to workload identity where supported.

### IMDS controls

- require IMDSv2
- set metadata hop limit according to the network model
- block pod access to IMDS when workloads do not need it
- do not assume workload identity automatically prevents fallback to the node profile in every configuration

Validate with an actual pod test that unauthorized workloads cannot obtain node-role credentials.

### Node isolation

Use separate node pools for trust boundaries such as:

- system components
- general applications
- sensitive workloads
- GPU or specialized workloads
- third-party agents

Apply taints, tolerations, labels, and admission policy. Remember that scheduling isolation alone is not a hard security boundary if the node is compromised.

---

## 6. VPC and subnet architecture

```text
VPC
├── public subnets
│   └── internet-facing load balancers when required
├── private EKS subnets
│   ├── managed nodes
│   └── pod IPs
└── isolated data subnets
    ├── databases
    └── caches
```

### Private worker nodes

Run worker nodes without public IPs unless a documented workload requires otherwise.

Use NAT or VPC endpoints for controlled outbound access.

### VPC endpoints

Consider endpoints for:

- ECR API
- ECR Docker registry
- S3
- STS
- CloudWatch Logs
- Secrets Manager
- Systems Manager
- KMS where supported and useful

Endpoints reduce dependence on public paths and NAT, but endpoint policies and DNS must also be secured.

### Egress governance

Unrestricted egress allows compromised pods to exfiltrate data.

Options include:

- Kubernetes NetworkPolicy
- egress proxy or firewall
- AWS Network Firewall
- VPC endpoints with endpoint policies
- DNS policy and logging
- service mesh egress control where justified

Design emergency and package-repository access rather than assuming all outbound traffic can be denied immediately.

---

## 7. Security Groups

### Cluster security group

The EKS cluster security group controls communication associated with control-plane elastic network interfaces and nodes. Do not leave broad inbound or outbound rules without understanding the required control-plane, kubelet, DNS, and webhook paths.

### Node security groups

Separate node security groups by workload boundary when it provides meaningful control.

Allow only required flows:

- control plane to kubelet and webhook endpoints
- node-to-node traffic required by the CNI and applications
- load balancer to targets
- pods/nodes to approved data services
- required egress

### Security Groups for Pods

Use Security Groups for Pods when individual pods need AWS VPC-level security-group rules, for example:

- only the payments service may reach the payments database
- only a specific workload may call an internal NLB service
- namespace-level Kubernetes policy is insufficient for the AWS resource boundary

Operational considerations include:

- supported instance types and CNI configuration
- branch ENI capacity
- pod startup latency and scale behavior
- interaction with NetworkPolicy
- troubleshooting complexity

Do not deploy it merely because it sounds more secure. Use it where the VPC security boundary is valuable and test at scale.

---

## 8. Kubernetes NetworkPolicy

Security groups and NetworkPolicy solve different layers.

- Security groups govern VPC network interfaces and AWS resource paths.
- NetworkPolicy governs pod ingress and egress according to Kubernetes identity and labels, when enforced by a compatible dataplane.

Start with namespace or workload default deny:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: payments
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
```

Then allow explicit flows.

Do not forget:

- DNS access
- telemetry endpoints
- secret providers
- identity endpoints
- health checks
- webhooks
- time synchronization and package access where applicable

Test policies with real connectivity checks and flow observability.

---

## 9. Secrets Manager and secret delivery

### Source of truth

Keep secret values in Secrets Manager, encrypted with KMS.

Examples:

- database credentials
- third-party API tokens
- signing keys
- TLS private keys where the certificate workflow requires it
- application encryption material

### Delivery options

#### Secrets Store CSI Driver

Mount secrets as files in a pod volume.

Benefits:

- application can read a file without broad Kubernetes Secret replication
- direct integration with external secret provider
- rotation can update mounted content depending on configuration

Questions:

- does the application reload changed files?
- does it require restart?
- what happens if the provider is unavailable during pod start?
- are mounted files copied into logs or crash dumps?

#### External Secrets Operator

Synchronize Secrets Manager values into Kubernetes Secrets.

Benefits:

- familiar Kubernetes Secret consumption
- reconciliation and refresh controls

Risks:

- secret value now exists in etcd as a Kubernetes Secret
- more principals may access it through Kubernetes RBAC
- rotation behavior depends on refresh and workload reload

### Kubernetes Secret encryption

Use EKS envelope encryption with KMS where required, but remember:

- base64 is not encryption
- etcd encryption does not protect a secret after a pod reads it
- broad RBAC can still expose values
- logs, environment dumps, and support bundles can leak secrets

### Rotation design

For a database credential:

1. create new credential
2. allow old and new during overlap
3. update Secrets Manager
4. confirm workloads reload or roll safely
5. verify new authentication succeeds
6. revoke old credential
7. alert on old credential use

Rotation is a distributed-systems workflow, not only a Secrets Manager setting.

---

## 10. Pod security

Enforce Kubernetes Pod Security Standards at an appropriate level, typically `restricted` for application namespaces unless a reviewed exception exists.

Application pod baseline:

```yaml
securityContext:
  runAsNonRoot: true
  seccompProfile:
    type: RuntimeDefault
containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
```

Control or deny:

- privileged containers
- host PID, IPC, or network namespaces
- hostPath mounts
- arbitrary device access
- added Linux capabilities
- root execution
- writable root filesystems
- unsafe sysctls
- host ports

Exceptions should be isolated, owned, documented, and time-bounded.

---

## 11. Admission control and policy

Use a policy engine such as Kyverno, Gatekeeper, or another validated admission mechanism to enforce:

- approved registries
- image digest pinning
- required resource requests and limits
- restricted security contexts
- required labels and ownership metadata
- prohibited Service types or external exposure
- required NetworkPolicy and PDB patterns
- signed image or attestation policy where integrated

### Admission webhook availability

A failed webhook can block cluster operations.

Design:

- multiple replicas across zones
- PDB and topology spread
- explicit failure policy selected by risk
- short timeouts
- monitoring
- emergency bypass procedure
- no dependency on the workload it is admitting

Security controls must not become an untested single point of failure.

---

## 12. Image and software supply chain

- use private ECR repositories
- scan images and dependencies
- generate SBOMs
- sign images and provenance
- deploy immutable digests, not mutable tags
- minimize base images
- patch through rebuild and redeploy, not in-place node mutation
- restrict who can push and retag
- protect release workflows with OIDC and environment approvals
- monitor ECR access and image deletion

### Runtime is not build trust

A vulnerability scanner finding no known CVEs does not prove the image came from the approved source. Provenance and signature verification address different threats from vulnerability scanning.

---

## 13. Node and AMI hardening

- use EKS-optimized or validated custom AMIs
- pin tested AMI versions for production NodePools
- require IMDSv2
- minimize installed packages
- use read-only or immutable operational patterns where possible
- disable unnecessary services
- collect host and runtime telemetry
- rotate nodes rather than patching indefinitely in place
- test node upgrades with canaries
- use Bottlerocket where its operational model fits

Do not let Karpenter automatically introduce an untested latest AMI into production.

---

## 14. Logging and detective controls

Enable and centralize relevant logs:

### EKS control-plane logs

- API
- audit
- authenticator
- controller manager
- scheduler

### AWS logs and findings

- CloudTrail organization trails
- VPC Flow Logs
- Route 53 Resolver query logs where justified
- WAF logs
- load-balancer access logs
- GuardDuty, including EKS-related detections where enabled
- AWS Config
- Security Hub aggregation
- KMS and Secrets Manager access events

### Runtime detections

Use tools such as Falco or Tetragon where the threat model justifies runtime behavior detection.

Alert on behaviors such as:

- unexpected shell execution in production containers
- access to service-account tokens by unusual processes
- writes to sensitive host paths
- privilege escalation attempts
- unexpected outbound destinations
- secret enumeration
- creation of privileged workloads

---

## 15. Multi-tenancy

Namespaces are organizational boundaries, not always sufficient security boundaries.

For soft multi-tenancy within a cluster:

- namespace RBAC
- default-deny NetworkPolicy
- resource quotas and limit ranges
- Pod Security enforcement
- workload identity per tenant
- node isolation where needed
- admission policy
- separate secrets and KMS policies

Use separate clusters or accounts when tenants have strong adversarial isolation, regulatory, or operational independence requirements.

The strongest boundary in AWS is often the account, followed by separate clusters and VPCs, not merely a namespace label.

---

## 16. CI/CD security

- use OIDC federation instead of static keys
- constrain trust by repository, branch, workflow, and environment claims
- separate build, deploy, and infrastructure roles
- protect production environments with approval
- prevent pull-request code from obtaining production credentials
- sign artifacts in a protected job
- retain audit evidence
- scan Terraform and Kubernetes changes
- make destructive actions explicit
- do not expose kubeconfig or state in logs

A compromised CI system is a production identity incident.

---

## 17. Incident scenarios

### Compromised pod

1. isolate traffic and credentials
2. capture pod, node, identity, and network evidence
3. revoke or disable workload role access
4. rotate accessed secrets
5. determine whether node compromise occurred
6. replace affected nodes if trust is lost
7. search for lateral movement
8. restore from a known-good artifact and desired state

### Leaked secret

1. revoke or rotate immediately
2. identify every consumer and access event
3. remove the value from logs, artifacts, and history where possible
4. confirm workloads use the new value
5. investigate the leak path
6. add preventive controls

### Stolen administrator session

1. revoke sessions and disable the identity path
2. preserve CloudTrail and audit logs
3. inspect access entries, RBAC, webhooks, secrets, and workloads created or modified
4. rotate high-value credentials
5. restore known-good policy and Git state
6. validate no persistence remains

---

## 18. Security validation

Run recurring tests:

- can an unauthorized pod reach the database?
- can a pod access node instance-profile credentials?
- can a namespace admin create a privileged pod?
- can a CI pull request assume the production role?
- can an application read another application's secret?
- do NetworkPolicies still work after CNI upgrades?
- does the cluster remain operable if an admission webhook fails?
- can break-glass access be used and audited?
- can secret rotation occur without an outage?
- can a malicious image bypass policy?

Security architecture is credible only when controls are exercised.

---

## Adversarial follow-ups

### “IRSA or EKS Pod Identity?”

For new same-account workloads using supported SDKs and node types, I generally prefer EKS Pod Identity for simpler association and operations. I use IRSA where its OIDC trust model, direct cross-account behavior, existing platform investment, or agent independence is a better fit. Both require least-privilege roles and restricted node credentials.

### “Private endpoint means the cluster is secure, correct?”

No. It reduces network exposure but does not replace identity, authorization, workload security, or audit. An overprivileged internal identity remains dangerous.

### “Why not store secrets only as Kubernetes Secrets?”

Kubernetes Secrets are useful delivery objects but are not an enterprise secret source of truth by themselves. Secrets Manager provides controlled lifecycle, KMS integration, audit, and rotation workflows. If synchronization to Kubernetes Secrets is used, RBAC and etcd encryption still matter.

### “Security Groups for Pods or NetworkPolicy?”

Often both. Security Groups for Pods enforce VPC-level access to AWS resources; NetworkPolicy enforces pod-level flows based on Kubernetes identity. I choose based on the required boundary and test their interaction.

### “What is the biggest identity mistake?”

Allowing pods to inherit broad node-role permissions or creating wildcard IRSA trust across namespaces. Compromise of one workload then becomes compromise of the cluster's AWS authority.

---

## Weak answers to avoid

- “Use IAM and private subnets.”
- assigning all pods the node instance profile
- wildcard IRSA trust policies
- giving every developer cluster-admin
- claiming Kubernetes Secrets are encrypted because they are base64 encoded
- storing secrets in Git because the repository is private
- enabling NetworkPolicy without confirming the CNI enforces it
- using mutable image tags in production
- deploying a fail-closed admission webhook without HA or recovery procedure
- treating namespaces as a hard tenant boundary in every threat model

---

## Closing statement

> My EKS security model assumes that credentials, pods, and automation can fail or be compromised. Human and workload identities are short-lived and least privileged, network paths are explicitly allowed, secrets remain externally governed, artifacts are verifiable, and every high-value control has monitoring and a tested recovery path.