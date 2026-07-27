# Kubernetes Platform Multi-Tenancy and Isolation Boundaries

## Why this exists

A shared Kubernetes platform can reduce operational duplication, improve utilization, and standardize delivery. It can also create dangerous coupling between teams that do not share the same trust level, availability requirements, or change cadence.

Multi-tenancy is not a checkbox or a namespace naming convention. It is a set of explicit control-plane, data-plane, identity, network, resource, and operational boundaries derived from a threat and failure model.

## What the interviewer is testing

A Staff or Principal candidate should be able to:

- define the tenant and trust relationship;
- distinguish soft and hard multi-tenancy;
- choose namespace, node, cluster, account, or virtual-control-plane boundaries;
- design RBAC, workload identity, network, storage, quota, and admission controls together;
- explain noisy-neighbor and shared-control-plane failure modes;
- create an onboarding, exception, incident, and migration model;
- know when not to share a cluster.

## Start with the tenant model

A tenant may be:

- an application team;
- a business unit;
- an environment;
- an external customer;
- a regulated workload class;
- a build or CI workload;
- a platform capability team.

Ask:

1. Do tenants trust each other?
2. Can one tenant obtain cluster-wide privileges?
3. Is data confidentiality required between tenants?
4. Can one tenant's load disrupt another tenant?
5. Do tenants require independent Kubernetes versions or extensions?
6. What is the legal or compliance boundary?
7. Who is allowed to investigate tenant workloads?
8. What is the tolerated shared blast radius?

## Soft versus hard multi-tenancy

### Soft multi-tenancy

Tenants belong to the same organization and are broadly trusted, but accidental interference must be controlled.

Typical controls:

- namespace per team or service group;
- least-privilege RBAC;
- ResourceQuota and LimitRange;
- default-deny NetworkPolicy;
- Pod Security Admission;
- workload identity boundaries;
- standard admission policy;
- fair scheduling and capacity controls.

### Hard multi-tenancy

Tenants are mutually untrusted or require strong confidentiality, integrity, and availability separation.

A shared namespace-based cluster may not provide the required isolation. Consider:

- separate clusters and cloud accounts;
- virtual control planes;
- dedicated nodes plus sandboxed runtimes;
- stronger network and storage isolation;
- tenant-specific encryption and keys;
- separate policy and operational credentials.

Namespaces are an administrative boundary inside one control plane, not a universal security boundary.

## Isolation decision tree

```text
Mutually untrusted tenants?
  |
  +-- yes --> regulatory or strong availability boundary?
  |              |
  |              +-- yes --> separate account/project and cluster
  |              |
  |              +-- no --> evaluate virtual control planes or dedicated clusters
  |
  +-- no --> materially different lifecycle or extension needs?
                 |
                 +-- yes --> separate cluster class
                 |
                 +-- no --> namespace-based tenancy with defense in depth
```

The decision is revisited as trust, scale, and regulation change.

## Namespace-based tenancy

A namespace-per-tenant model needs more than namespace creation.

A complete tenant namespace package should include:

- owner and lifecycle metadata;
- tenant RBAC groups and service accounts;
- ResourceQuota and LimitRange;
- default-deny ingress and egress policy;
- approved DNS and platform-service egress;
- Pod Security Admission labels;
- workload identity configuration;
- secrets and encryption model;
- cost allocation labels;
- policy bindings;
- monitoring, log, and audit access;
- backup and deletion policy;
- support and escalation route.

Provision this package through a versioned platform API or controller so controls do not drift across namespaces.

## Control-plane isolation

All tenants in a standard cluster share:

- API server capacity;
- etcd storage and latency;
- admission webhooks;
- controllers and operators;
- CRDs and API aggregation;
- scheduler behavior;
- cluster-wide RBAC and policy;
- upgrade and maintenance windows.

One tenant may harm the control plane through:

- excessive object creation;
- high-rate list and watch clients;
- huge secrets or ConfigMaps;
- pathological custom resources;
- controllers that continuously retry;
- large numbers of Jobs or Events;
- API priority and fairness misuse;
- webhook dependency failure.

Controls include quotas on object-producing capabilities, API Priority and Fairness, rate limits, controller backoff, event retention discipline, CRD governance, and separate clusters for extreme control-plane load.

## Virtual control planes

A virtual-control-plane design gives tenants separate Kubernetes API surfaces while sharing some underlying infrastructure.

Potential benefits:

- separate API objects and RBAC domains;
- tenant-specific CRDs and controllers;
- reduced control-plane naming conflict;
- independent policy and lifecycle in some designs.

Costs and risks:

- more control planes to upgrade and observe;
- complex networking and service discovery;
- shared worker-node or data-plane exposure may remain;
- unclear responsibility for storage, DNS, ingress, and node services;
- debugging spans host and virtual clusters;
- ecosystem compatibility varies.

Virtual control planes are an architectural option, not automatic hard isolation.

## Identity and authorization

### Human access

- federate cluster authentication to the corporate identity provider;
- map groups to tenant roles;
- avoid direct user bindings where possible;
- separate read, deploy, debug, and administrative permissions;
- restrict impersonation, token creation, and `bind` or `escalate` privileges;
- review access on team changes;
- use short-lived credentials and auditable break-glass access.

### Workload identity

- use projected service-account tokens and cloud workload identity;
- never use a shared node role as the tenant authorization boundary;
- scope trust to namespace and service account;
- protect metadata-service credentials;
- separate identities by workload capability;
- deny cross-tenant role assumption unless explicitly required.

A pod that can reach another tenant's cloud role has escaped the namespace boundary even if Kubernetes RBAC is correct.

## RBAC design

Tenant administrators should not receive permissions that allow privilege escalation.

High-risk permissions include:

- creating or binding arbitrary ClusterRoles;
- creating privileged pods;
- modifying admission or policy resources;
- creating validating or mutating webhooks;
- modifying namespaces or node objects;
- reading secrets in other namespaces;
- creating pods that use protected service accounts;
- accessing `pods/exec`, `pods/attach`, or ephemeral containers without governance;
- managing CRDs or cluster-scoped operators.

Use automated RBAC tests and periodically evaluate effective permissions.

## Pod and node isolation

Use Pod Security Admission as a baseline, normally `restricted` for standard tenants.

Additional controls:

- run as non-root;
- drop Linux capabilities;
- use seccomp and AppArmor or SELinux where supported;
- prohibit host networking, host PID, host IPC, and hostPath;
- prevent privileged containers;
- use read-only root filesystems where feasible;
- restrict unsafe sysctls;
- constrain RuntimeClass usage.

For higher-risk tenants, consider:

- dedicated node pools;
- taints and tolerations controlled by policy;
- node affinity injected by the platform;
- sandboxed runtimes such as gVisor or Kata where validated;
- separate clusters for kernel-level distrust.

Dedicated nodes reduce co-residency but do not isolate the shared Kubernetes control plane.

## Network isolation

Start from default deny for ingress and egress.

Define approved paths:

```text
Tenant workloads
  -> tenant-local services
  -> platform DNS
  -> approved shared platform APIs
  -> explicitly declared external dependencies
```

Controls:

- namespace and pod selectors owned by the platform;
- egress policy and DNS-aware controls where needed;
- ingress gateways with tenant ownership and certificate boundaries;
- service mesh authorization where it adds value;
- cloud security groups or firewall policies as backstops;
- separate load balancers or gateways for high-risk tenants.

Kubernetes NetworkPolicy behavior depends on the network implementation. Test actual enforcement, including DNS, host-network pods, node traffic, and egress through proxies or gateways.

## Storage and data isolation

- use tenant-scoped StorageClasses or policy;
- prevent arbitrary hostPath and local-path access;
- define volume snapshot and restore authorization;
- separate encryption keys when risk requires it;
- restrict cross-namespace secret and PVC access;
- define reclaim policy and deletion retention;
- validate backup ownership and restore destinations;
- prevent one tenant from exhausting storage quotas or volume attachments.

A deleted namespace may not imply deleted cloud data, and a deleted PVC may delete more than the tenant expects. Make lifecycle explicit.

## Resource fairness and noisy neighbors

Controls include:

- ResourceQuota for CPU, memory, storage, object count, and extended resources;
- LimitRange for default and maximum requests or limits;
- admission rules requiring realistic requests;
- priority classes controlled by the platform;
- topology and disruption policies;
- autoscaler and node-provisioner limits;
- tenant-specific capacity reservations where required;
- fair queueing for shared external services.

Failure patterns:

- one tenant schedules all available memory;
- low-priority pods trigger expensive scale-out;
- bursty workloads exhaust IP addresses;
- too many load balancers or volumes hit cloud quotas;
- high-priority abuse evicts critical platform components;
- a tenant's DaemonSet lands on every node.

## Shared platform services

DNS, ingress, service mesh, certificate management, secrets integration, observability agents, policy engines, and node provisioning are shared dependencies.

For each service define:

- tenant-facing contract;
- capacity and quotas;
- failure domain;
- data exposure model;
- upgrade strategy;
- emergency bypass or degradation mode;
- cost allocation;
- SLO and support owner.

Do not let tenant teams install arbitrary cluster-wide operators into a shared production cluster.

## Observability boundaries

Tenants need enough evidence to operate their services without accessing other tenants' data.

Design:

- tenant-scoped log and metric access;
- trace authorization and data redaction;
- cluster and namespace views;
- audit access through approved workflows;
- cost and capacity attribution;
- platform incident status;
- detection of cross-tenant access attempts.

Labels are not a complete authorization system for observability backends. Enforce tenant identity and query boundaries in the backend.

## Cluster lifecycle and fleet design

A platform should provide a small number of cluster classes rather than one immortal cluster or one bespoke cluster per team.

Example classes:

```text
shared-standard
shared-restricted
regulated-dedicated
build-ephemeral
edge-specialized
```

Each class defines:

- trust assumptions;
- Kubernetes and add-on versions;
- allowed workloads;
- tenancy controls;
- SLO and recovery target;
- upgrade cadence;
- cost model;
- exception policy.

Use fleet-level automation and conformance tests to prevent cluster snowflakes.

## Onboarding workflow

```text
Tenant request
  -> classify trust, data, availability, and scale
  -> choose cluster class
  -> create identity and namespace package
  -> apply quota, network, pod, and policy controls
  -> validate workload identity
  -> run isolation conformance tests
  -> expose tenant evidence and support contract
```

Do not approve tenancy solely from a questionnaire. Test the deployed boundary.

## Isolation conformance tests

Verify that a tenant cannot:

- list or read another tenant's resources;
- use another tenant's service account;
- reach another tenant's protected service;
- assume another tenant's cloud role;
- schedule privileged or host-access pods;
- escape dedicated node placement;
- exceed object and compute quotas;
- query another tenant's logs or traces;
- modify cluster-scoped policy;
- restore backup data into an unauthorized namespace.

Run tests after cluster upgrades, CNI changes, policy changes, and identity-provider changes.

## Failure modes

- namespace exists without default-deny egress;
- tenant admin can create role bindings to a stronger role;
- node credentials are reachable from pods;
- an observability query leaks cross-tenant data;
- shared ingress certificates or routes are misbound;
- resource quota ignores external cloud quotas;
- a policy exemption applies to all controller-created pods;
- a cluster-wide operator watches or mutates all namespaces;
- tenant deletion leaves cloud resources and data behind;
- one noisy client degrades API server latency for everyone.

## Incident response

For suspected cross-tenant impact:

1. Establish incident command and preserve audit, network, identity, and runtime evidence.
2. Identify affected tenants, identities, nodes, namespaces, and external resources.
3. Stop the narrow access path: revoke identity, quarantine namespace, isolate node pool, or block network route.
4. Avoid deleting workloads before collecting evidence.
5. Rotate affected credentials and evaluate node compromise.
6. Validate that other tenants were not reached through shared services.
7. Restore from trusted artifacts and configuration.
8. add an automated isolation test and repair the platform contract.

## SLOs and metrics

Measure:

- tenant onboarding time;
- percentage of namespaces with complete control package;
- quota and cloud-quota exhaustion events;
- API latency and throttling by tenant workload class;
- cross-tenant policy violations;
- network-policy and identity conformance success;
- noisy-neighbor incidents;
- shared-service error budget by tenant impact;
- exception count and age;
- cluster-class upgrade consistency;
- time to quarantine a tenant safely.

## 90-second interview answer

> I begin Kubernetes multi-tenancy by defining the tenant and trust model. For cooperative internal teams, namespace-based tenancy can work if the platform provisions a complete boundary: least-privilege RBAC, workload identity, Pod Security Admission, default-deny networking, quota, storage policy, observability authorization, and lifecycle controls. For mutually untrusted or regulated tenants, I do not assume namespaces are enough; I evaluate separate clusters and cloud accounts, virtual control planes, dedicated nodes, and sandboxed runtimes based on confidentiality, availability, and control-plane independence. I treat the API server, etcd, admission, CRDs, operators, DNS, ingress, and node provisioning as shared failure domains. Tenant admins cannot create cluster-wide policy or escalate RBAC. I run automated isolation conformance tests after every significant platform change and measure cross-tenant violations, quota pressure, noisy-neighbor incidents, and quarantine time. The goal is an explicit, tested isolation contract, not maximum cluster density.

## Adversarial follow-ups

### "Does a namespace isolate tenants?"

It scopes many API resources, but it does not isolate the shared control plane, node kernel, cloud credentials, observability backend, or network unless those boundaries are configured separately.

### "When do you require a separate cluster?"

When trust, regulation, lifecycle, extension, availability, or kernel-isolation requirements exceed what the shared cluster can prove and operate safely.

### "Are dedicated nodes enough for untrusted workloads?"

They reduce co-residency, but the Kubernetes control plane and often networking, storage, and shared services remain common. Dedicated nodes are one layer, not complete isolation.

### "How do you prevent noisy neighbors?"

Use requests, quotas, priority governance, node and autoscaler limits, API fairness, object limits, cloud quota monitoring, and separate cluster classes for extreme workloads.

## Dangerous answers

- "Namespace equals tenant isolation."
- "NetworkPolicy secures everything by default."
- "RBAC prevents cloud-role theft."
- "Dedicated nodes provide hard multi-tenancy."
- "One large cluster is always more efficient."
- "Separate clusters eliminate the need for policy and identity controls."

## Whiteboard summary

```text
Tenant and trust model
  -> choose namespace, virtual control plane, or cluster boundary
  -> identity + RBAC
  -> pod + node
  -> network + storage
  -> quota + control-plane fairness
  -> observability authorization
  -> conformance tests and incident quarantine
```

## Primary references

- Kubernetes official multi-tenancy documentation.
- Kubernetes namespace, RBAC, Pod Security Admission, NetworkPolicy, ResourceQuota, LimitRange, API Priority and Fairness, and security checklist documentation.
- Official cloud-provider workload-identity and network-isolation documentation.
- Documentation for the selected CNI, CSI, sandboxed runtime, virtual-control-plane implementation, and observability backend.
