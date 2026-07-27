# Nathanel Sulimanov — Personal Production Story Bank

This file maps the AWS Staff/Principal interview curriculum to Nathanel's real engineering experience.

## Truth boundary

Use only facts that can be defended from Nathanel's CV, project records, repositories, or direct recollection.

Three confidence labels are used:

- **Verified:** the exact fact, scale, date, or technology is already documented.
- **Supported:** the experience is documented, but the precise metric or outcome needs a source before quoting it.
- **Fill before interview:** the story is real, but the missing decision, number, timeline, or outcome must be added by Nathanel.

Never convert a lab, interview assignment, or hypothetical design into a production claim.

---

# Master positioning

## 30-second career frame

> I have more than 20 years in infrastructure, cloud, DevOps, SRE, and platform engineering. From 2012 through 2025 at SES/O3b Networks, I worked as a senior cloud engineer, Principal SRE, cloud architect, and platform leader across AWS, Azure, private cloud, and 11 data centers. I built automation, observability, CI/CD, GitOps-style delivery, and operational tooling across roughly 2,500 managed systems, and I led complex production investigations across engineering, security, infrastructure, product, program management, customers, and NOC teams. Earlier, I owned high-traffic Linux and database infrastructure at Alexander Street Press and Pipl.

**Confidence:** Verified, except the exact preferred job-title sequence should match the submitted CV version.

## Principal-level frame

> My strongest value is not one AWS product. It is connecting architecture, operations, incident evidence, and organizational ownership. I have operated large heterogeneous estates, built repeatable automation, transferred operational capability to lower support tiers, led multidisciplinary teams, and handled production issues where cloud, Linux, networking, databases, security, and application behavior crossed ownership boundaries.

**Confidence:** Verified.

---

# Story 1 — Global platform operations across 2,500 systems and 11 data centers

## Best interview questions

- Q1 — Multi-AZ EKS for millions of users
- Q2 — GitOps and platform delivery
- Q4 — Securing EKS
- Q6 — Capacity and autoscaling
- Q17 — Observability platform
- Leadership — platform ownership and influence

## Facts already supported

- SES/O3b Networks role from November 2012 through July 2025.
- AWS, Azure, and private-cloud infrastructure.
- Operations across 11 data centers.
- Approximately 2,500 managed systems.
- Monitoring across more than 1,000 devices/platforms.
- Terraform, Ansible, Puppet, Helm, Argo CD/GitOps-style workflows, Jenkins, GitLab CI/CD, GitHub Actions, Azure DevOps, and JFrog.
- Built observability, remediation automation, runbooks, and operational tools.
- Led multidisciplinary DevOps, cloud, data, and automation work; managed a team of five SRE/DevOps engineers in at least one documented role version.

## Interview-ready story

### Context

> At SES/O3b Networks, the operational estate included AWS, Azure, private cloud, and 11 data centers, with approximately 2,500 managed systems and monitoring across more than 1,000 devices and platforms. The environment was heterogeneous, globally distributed, and supported by several engineering and operations groups.

### Risk

> The main risk was not one failed server. It was inconsistent delivery, fragmented ownership, slow diagnosis across technology boundaries, and too much operational knowledge concentrated in senior engineers.

### Decision

> I focused on repeatable platform mechanisms: infrastructure automation, standardized delivery paths, observability, remediation workflows, runbooks, and clear escalation boundaries. The goal was to reduce one-off administration and make production behavior easier to reason about across teams.

### Execution

> I used Terraform, Ansible, Puppet, Helm, Jenkins, GitLab CI/CD, GitHub Actions, Azure DevOps, JFrog, and GitOps-style reconciliation patterns. I also built monitoring and operational tooling that gave engineering and NOC teams better evidence and repeatable response procedures.

### Result

> The documented result is broad adoption across the managed estate and transfer of operational tools and runbooks to Level 1 NOC. The exact deployment-frequency, incident-reduction, or toil-reduction metric must be added before quoting one.

### Principal lesson

> Platform value is created when the operating mechanism becomes reusable by other teams. The technical implementation matters, but adoption, ownership, evidence, and escalation design determine whether it changes the organization.

## Missing facts to fill

- [ ] Number of engineering teams using the platform or tooling.
- [ ] Before/after deployment time.
- [ ] Before/after incident escalation volume.
- [ ] Percentage of incidents resolved by Level 1 after transfer.
- [ ] One architectural disagreement and how it was resolved.
- [ ] One specific failure prevented by the standardized mechanism.

---

# Story 2 — Level 3/4 production escalation and permanent-fix leadership

## Best interview questions

- Q7 — Route 53-to-application outage
- Q8 — API latency
- Q9 — Partial-user failure
- Q10 — Evidence beyond dashboards
- Q12 — Restart forensics
- Q13 — Postmortem
- Leadership — severe incident and cross-team influence

## Facts already supported

- Served as Level 3/4 escalation authority and trusted technical advisor.
- Led complex production and product investigations.
- Identified root causes and developed permanent fixes.
- Coordinated customers, product, software engineering, security, infrastructure, project/program management, and NOC teams.
- Performed incident reviews and knowledge transfer to prevent repeat failures.

## Interview-ready story

### Context

> In the SES/O3b environment, complex incidents frequently crossed infrastructure, networking, software, security, product, and customer boundaries. I was a Level 3/4 escalation authority and was expected to convert ambiguous symptoms into a defensible technical explanation and permanent correction.

### Risk

> The risk during a multi-team incident was uncontrolled parallel change, each team proving only its own component looked healthy, and loss of evidence before the true boundary was identified.

### Decision

> I used one incident timeline and followed the request or control path across systems. I separated facts from hypotheses, assigned evidence collection by boundary, and kept mitigation narrower than the suspected root cause until the evidence was strong.

### Execution

> I coordinated customer-facing, product, software, security, infrastructure, program-management, and NOC stakeholders. The technical work included Linux, network, DNS, load-balancing, databases, application behavior, monitoring, and cloud infrastructure depending on the event.

### Result

> The documented outcome is root-cause identification, permanent fixes, incident reviews, and knowledge transfer. A specific incident should be selected and quantified before the interview.

### Principal lesson

> Senior incident leadership is not about personally typing every command. It is about creating one evidence model, controlling change, ensuring customer impact drives priority, and turning the failure into a mechanism that prevents recurrence.

## Fill before interview

Select one real incident and add:

- [ ] User or business impact.
- [ ] Duration.
- [ ] First misleading signal.
- [ ] Decisive evidence.
- [ ] Narrow mitigation.
- [ ] Permanent correction.
- [ ] Number of teams involved.
- [ ] Measured result after correction.
- [ ] What Nathanel initially believed that turned out to be wrong.

---

# Story 3 — Monitoring and remediation adopted by Level 1 NOC

## Best interview questions

- Q10 — Evidence beyond dashboards
- Q13 — Postmortem and corrective actions
- Q17 — Actionable observability
- Leadership — platform adoption and reducing toil

## Facts already supported

- Built monitoring for more than 1,000 devices/platforms.
- Built remediation automation, runbooks, and operational tools.
- Tools and procedures were adopted by Level 1 NOC.
- Performed knowledge transfer to prevent repeat failures.

## Interview-ready story

### Context

> The operations environment included more than 1,000 monitored devices and platforms. Many issues reached senior engineering because the first response layer lacked enough context, automation, or safe procedures.

### Risk

> Senior engineers becoming the default first responder creates slow resolution, high interruption cost, weak scalability, and poor knowledge distribution.

### Decision

> I treated observability and remediation as an operational product. The goal was not another dashboard; it was to give the NOC enough evidence and bounded automation to identify known failure classes, execute safe actions, and escalate with useful context.

### Execution

> I built monitoring, runbooks, remediation automation, and tools; then transferred the operating knowledge to Level 1 NOC. The design separated actions that could be automated safely from conditions requiring escalation.

### Result

> Adoption by Level 1 NOC is verified. Exact reductions in escalation, mean time to acknowledge, mean time to restore, or after-hours interruption must be sourced before quoting.

### Principal lesson

> Alert quality is measured by the decision it enables. The best platform outcome is not more telemetry; it is better ownership, faster safe action, and fewer unnecessary escalations.

## Missing metrics

- [ ] Percentage or count of alerts handled by NOC after adoption.
- [ ] MTTR before and after.
- [ ] Reduction in Level 3/4 pages.
- [ ] One remediation deliberately not automated because of risk.
- [ ] One failure where the runbook prevented a larger incident.

---

# Story 4 — Large-scale MySQL migration and resumable data processing

## Best interview questions

- Q8 — Latency and dependency saturation
- Q11 — Partial apply and recovery thinking
- Q13 — Postmortem/recovery
- Q16 — DR, RTO/RPO, data reconciliation
- Q18 — High-volume streams, backpressure, replay, and idempotency

## Facts already supported

- Approximately 45 TB uncompressed data and approximately 6 TB compressed.
- MySQL 5.7.
- Multiple databases following an `AMCxx_x` naming pattern.
- Ubuntu, XFS, LVM, two approximately 31 TB volumes.
- Production-like import workflow.
- Migration from MyISAM to InnoDB.
- Required removal of `DATA DIRECTORY` and `INDEX DIRECTORY` clauses.
- Streaming transformation was required to avoid memory exhaustion.
- Resume and per-database progress were required.
- Encountered and corrected `No database selected`, unsupported variables, memory errors, and InnoDB configuration issues.
- Observed storage and copy throughput constraints.

## Interview-ready story

### Context

> I had to import roughly 45 TB of uncompressed MySQL data, about 6 TB compressed, into a MySQL 5.7 environment on Ubuntu with XFS and LVM. The source included many databases, legacy MyISAM definitions, and `DATA DIRECTORY` and `INDEX DIRECTORY` clauses that could not be used in the target layout.

### Risk

> A one-shot import would have an enormous failure and restart cost. Loading or rewriting the entire dump in memory was not viable, and a partially imported database estate could become difficult to reason about.

### Decision

> I designed the process as a streaming, per-database, resumable workflow. SQL was transformed while streaming: engines converted to InnoDB, unsupported directory clauses removed, databases created explicitly, and `USE` statements inserted so each unit could be replayed independently.

### Execution

> I used shell streaming tools, generated structure and import commands, monitored MySQL process state, separated structure-only work where needed, and tuned the target from measured CPU, memory, storage, and I/O behavior. When a transformation caused memory pressure, I replaced it with a true streaming method rather than increasing memory blindly.

### Result

> The workflow successfully addressed the identified blockers and enabled controlled progress across a very large data set. Final completion duration, effective sustained throughput, failure-recovery time, and data-validation result must be added from the project records.

### Principal lesson

> At this scale, restartability and observability are architecture. A fast path that cannot resume safely is slower than a controlled pipeline once the first failure occurs.

## Fill before interview

- [ ] Final imported data volume.
- [ ] Total elapsed time.
- [ ] Sustained throughput range.
- [ ] Number of databases/tables.
- [ ] Validation method: counts, checksums, application queries, or sampling.
- [ ] Maximum recovery point after failure.
- [ ] Exact performance bottleneck and the final tuning decision.
- [ ] Business reason for the migration.

---

# Story 5 — Azure AKS platform assignment with Terraform, networking, identity, and recovery

## Classification

**Hands-on engineering assignment/lab, not a production story.**

Use it to prove current command-level skill. Do not present it as an employer production deployment.

## Best interview questions

- Q1 — EKS platform architecture
- Q2 — GitOps/CI/CD boundaries
- Q3 — Terraform state
- Q4 — Kubernetes security
- Q6 — autoscaling and capacity
- Q7 — request-path troubleshooting
- Q11 — Terraform recovery

## Facts already supported

- Terraform deployed an Azure resource group, Ubuntu Jenkins VM, Key Vault, AKS, ACR, VNet, multiple subnets, NAT gateway, and public IP.
- AKS used Azure networking, policy controls, private-endpoint subnet planning, ingress-nginx, cert-manager, Secrets Store CSI, Redis Sentinel, and HPA.
- ACR image `myapp` exposed port 3000.
- Static ingress IP and resource-group annotations were configured.
- RBAC assignments included Network Contributor, AcrPull, and Key Vault Secrets User.
- Encountered an `AuthorizationFailed` error reading the public IP.
- Resolved with the required Network Contributor permissions.
- Encountered ingress service-account/role issues and corrected them.

## Interview-ready story

### Context

> In a current hands-on platform engineering assignment, I built an end-to-end AKS environment with Terraform: network segmentation, NAT, Jenkins, ACR, Key Vault, ingress, certificates, workload secret delivery, Redis Sentinel, application deployment, and HPA.

### Risk

> The difficult part was not creating individual resources. It was ownership and identity across Azure control planes: the cluster identity needed network permissions, the kubelet identity needed registry pull, workloads needed secret access, and the load balancer needed permission to use the static IP.

### Decision

> I separated identities and permissions by function, kept the infrastructure declarative, and traced failures from the Kubernetes object to the Azure resource and principal performing the operation.

### Execution

> When the ingress controller could not read or bind the public IP, I inspected the actual principal and resource scope, corrected Network Contributor assignment, and verified that the service reconciled to the expected static address. I also corrected service-account and RBAC gaps affecting ingress components.

### Result

> The environment reached a working state with the static load-balancer IP preserved and the application, ingress, TLS, and platform add-ons deployed. This proves current hands-on capability but should be labeled as an assignment.

### AWS translation

- AKS managed identity -> EKS cluster/node/workload IAM boundaries.
- ACR `AcrPull` -> ECR pull permissions.
- Key Vault Secrets User -> Secrets Manager/KMS access through Pod Identity or IRSA.
- Azure load-balancer resource-group permission -> AWS Load Balancer Controller IAM and subnet/security-group permissions.
- Azure subnet/IP planning -> VPC CNI, subnet IPs, load-balancer and pod capacity.

---

# Story 6 — Azure DevOps to GitHub repository migration

## Best interview questions

- Q2 — GitOps and delivery
- Q3 — state and source-of-truth discipline
- Q5 — tool migration and governance
- Leadership — platform migration and adoption

## Facts already supported

- Migrated multiple Azure DevOps repositories to GitHub under `hatan4ik`.
- Rewrote remotes.
- Created repositories through API.
- Preserved tags.
- In selected cases retained only the last two commits using history rewriting.
- Removed `dev.azure.com` references.
- Resolved PAT authentication failures, pre-existing repositories, missing push destinations, and forced tag issues.

## Interview-ready story

### Context

> I migrated multiple repositories from Azure DevOps to GitHub, including remote rewriting, repository creation, tags, and selective history reduction where only the final history was required.

### Risk

> Repository migration is a source-of-truth transfer. A careless process can lose tags, push to the wrong destination, expose old platform references, or leave teams writing to both systems.

### Decision

> I treated the migration as an authority cutover: inventory repositories and refs, create the target, rewrite history only when explicitly required, validate the new remote, push branches and tags, search for stale source-platform references, and verify the destination before declaring completion.

### Execution

> I automated repository creation and remote changes, used `filter-repo` for controlled history reduction, corrected PAT and API failures, handled existing repositories, and fixed missing push destinations and tag behavior.

### Result

> The known repositories were transferred to GitHub with required tags and cleaned references. Exact repository count, team adoption, CI migration, cutover downtime, and decommissioning timeline must be added before quoting.

### Principal lesson

> Tool migration is not complete when bytes move. It is complete when authority, identity, automation, integrations, and user workflow move—and the previous control plane is no longer an accidental writer.

## Missing facts

- [ ] Number of repositories.
- [ ] Number of contributors/teams.
- [ ] CI/CD workflows migrated.
- [ ] Cutover method and downtime.
- [ ] Rollback plan.
- [ ] Security and branch-protection changes.
- [ ] Measured delivery or administration improvement.

---

# Story 7 — High-traffic Linux/database infrastructure and approximately $100K annual cost reduction

## Best interview questions

- Q1 — capacity architecture
- Q5 — platform/tool trade-offs
- Q6 — capacity and cost
- Q8 — performance analysis
- Leadership — cost and modernization decisions

## Facts already supported

- Alexander Street Press role from October 2010 through October 2012.
- Owned high-traffic production infrastructure.
- RHEL/Debian Linux, Apache, MySQL, MSSQL, HAProxy, virtualization, networking, security, automation, backup.
- Approximately 100 TB iSCSI storage.
- Reduced annual infrastructure cost by approximately $100,000.

## Interview-ready story

### Context

> At Alexander Street Press I owned high-traffic production infrastructure across Linux, Apache, MySQL/MSSQL, HAProxy, virtualization, networking, backup, and approximately 100 TB of iSCSI storage.

### Risk

> The environment had to balance reliability, performance, storage growth, backup, and operating cost. Cost reduction could not weaken capacity or recoverability.

### Decision

> I evaluated infrastructure and operational changes through total cost and production risk rather than raw purchase price. The work combined consolidation, automation, performance tuning, and better use of the existing platform.

### Result

> The documented annual infrastructure cost reduction was approximately $100,000. The exact technical changes and the reliability/capacity guardrails must be reconstructed before using this as a detailed architecture story.

### Principal lesson

> Cloud and platform economics are credible only when the cost decision includes capacity, failure recovery, operational labor, and future constraints.

## Fill before interview

- [ ] Which costs were removed or reduced.
- [ ] One rejected cost-saving option and why it was unsafe.
- [ ] Capacity before and after.
- [ ] Availability or performance before and after.
- [ ] Backup/restore validation.
- [ ] Stakeholders and approval process.

---

# Story 8 — 120+ server platform with HAProxy, caching, MySQL HA, and AWS integration

## Best interview questions

- Q1 — scalable request path
- Q7 — network/application outage
- Q8 — latency
- Q16 — recovery architecture
- Q18 — distributed-system foundations

## Facts already supported

- Pipl.com role from February 2008 through October 2010.
- Managed and troubleshot more than 120 Linux/Windows servers.
- HAProxy, caching, MySQL high availability, AWS/EC2 integration, monitoring, backup, and shell automation.

## Interview-ready story

### Context

> At Pipl, I managed and troubleshot a platform of more than 120 Linux and Windows servers with HAProxy, caching, MySQL HA, AWS/EC2 integration, monitoring, backup, and shell automation.

### Risk

> The request path crossed load balancing, caches, application servers, databases, networks, and a mixed on-premises/AWS environment. A component could appear healthy while a user-facing path failed.

### Decision

> I used layered request-path analysis, capacity and cache awareness, database availability, and automation rather than treating each server as an isolated unit.

### Result

> The scale and technologies are verified. A specific outage, architecture change, or performance improvement must be selected and quantified before interview use.

## Fill before interview

- [ ] Peak traffic or user scale.
- [ ] Specific failure.
- [ ] Cache/load-balancer/database interaction.
- [ ] Recovery action.
- [ ] Measured improvement.

---

# Story 9 — Hybrid cloud and network architecture across AWS, Azure, and private infrastructure

## Best interview questions

- Q1 — EKS architecture
- Q4 — security
- Q7 — request-path outage
- Q16 — multi-Region and hybrid recovery
- Leadership — architecture standardization

## Facts already supported

- AWS, Azure, private cloud, and 11 data centers.
- VPC, VNet, security groups, NSGs, load balancing, DNS, Anycast, DHCP, VPN, SSH, LDAP/SSO/OIDC, certificates, firewalls.
- Hub-spoke, transit gateways, ExpressRoute/VPN, and multi-account governance are present in documented role versions.
- Complex network/system integration troubleshooting.

## Interview-ready story skeleton

### Context

> The platform crossed AWS, Azure, private cloud, and global data-center networks. Connectivity, identity, DNS, certificates, and routing were shared operational dependencies.

### Risk

> Hybrid failures are often asymmetric: control-plane access works but data traffic fails, one route or identity path differs, or every team validates only its local component.

### Decision

> I treated the network as an end-to-end service with explicit routing domains, identity boundaries, DNS ownership, encryption, observability, and failure tests.

### Result

> The technology scope is verified, but one architecture project must be selected with exact topology, decision, outage or migration, and measurable result.

## Fill before interview

- [ ] One specific AWS/Azure/private-cloud topology.
- [ ] Traffic and critical applications.
- [ ] Routing or DNS failure encountered.
- [ ] Security boundary.
- [ ] DR/failover method.
- [ ] Measured latency, availability, or cost result.

---

# Story 10 — Leading a team of five SRE/DevOps engineers

## Best interview questions

- Q13 — postmortem and corrective-action ownership
- Q17 — platform operating model
- Behavioral — team leadership, conflict, delegation, performance, hiring

## Facts already supported

- Managed a team of five SRE/DevOps engineers in a documented role version.
- Led multidisciplinary DevOps, cloud, data, and automation teams.
- Coordinated across engineering, security, infrastructure, product, customers, PM, and NOC.

## Interview-ready skeleton

### Context

> I led a five-person SRE/DevOps team in a broader multidisciplinary environment covering cloud, infrastructure, automation, data, and operations.

### Leadership invariant

> My responsibility was not to become the bottleneck. I needed to create clear ownership, technical standards, review mechanisms, and escalation paths so engineers could act independently without increasing production risk.

### Evidence to add

- [ ] Team charter.
- [ ] Hiring or mentoring example.
- [ ] Technical disagreement.
- [ ] Delegation decision.
- [ ] Underperformance or missed commitment handled.
- [ ] Measurable team outcome.
- [ ] Platform or runbook that reduced dependence on Nathanel.

---

# Mapping the 18 AWS questions to truthful stories

| Question | Primary story | Secondary story | Important boundary |
|---:|---|---|---|
| 1. Multi-AZ EKS | Story 1 global estate | Story 9 hybrid network | Do not claim the exact AWS design was deployed unless documented |
| 2. GitOps | Story 1 platform delivery | Story 6 repo migration | Separate production experience from GitOps design details not directly implemented |
| 3. Terraform state | Story 5 AKS assignment | Story 1 automation estate | Assignment can prove current hands-on skill, not production scale |
| 4. EKS security | Story 1 cloud/security scope | Story 5 identity/RBAC assignment | Use principles and direct identity experience; avoid claiming a specific EKS breach response |
| 5. IaC selection | Story 1 multi-tool estate | Story 6 source migration | Focus on ownership and governance |
| 6. Autoscaling | Story 1 large estate | Story 5 HPA/AKS assignment | Do not invent Karpenter production adoption |
| 7. Outage path | Story 2 escalation | Story 8 mixed platform | Select one real incident before interview |
| 8. Latency | Story 4 MySQL scale | Story 2 escalation | Add one measured latency/root-cause case |
| 9. Partial users fail | Story 2 escalation | Story 9 hybrid network | Needs a real cohort-specific incident to become personal evidence |
| 10. Evidence beyond dashboards | Story 3 observability/NOC | Story 2 escalation | Strong real match |
| 11. Terraform partial apply | Story 5 assignment | Story 4 resumable recovery | Label the Terraform example as a lab/assignment |
| 12. Restart forensics | Story 2 escalation | Hands-on Kubernetes lab | Do not claim a real OOM incident unless one is selected |
| 13. Postmortem | Story 2 escalation | Story 3 NOC transfer | Select one incident review and corrective action |
| 14. Mobile backend | Architecture answer | SimDream/device integration may supply adjacent ownership | Do not claim this exact backend was deployed |
| 15. Secure software update | Architecture answer | Story 1 distributed platform operations | Do not claim fleet OTA unless documented |
| 16. Multi-Region DR | Story 9 hybrid/cloud | Story 4 recovery discipline | Add one tested DR or restore story |
| 17. Observability platform | Story 3 NOC tooling | Story 1 monitoring at scale | Strong real match |
| 18. Events at scale | Story 4 data pipeline | Local event lab | Do not claim Kinesis production scale without evidence |

---

# Required five-story interview set

Prepare these first because together they cover most of the loop.

## A. Platform transformation

Use Story 1.

Required missing data:

- deployment or operational metric;
- adoption count;
- one disagreement;
- one measurable result.

## B. Severe incident

Use Story 2.

Required missing data:

- exact incident;
- impact/duration;
- decisive evidence;
- mitigation;
- permanent fix;
- personal learning.

## C. Observability and toil reduction

Use Story 3.

Required missing data:

- escalations or MTTR before/after;
- alert-quality decision;
- one safe automation boundary.

## D. Large migration

Use Story 4.

Required missing data:

- final duration/throughput;
- validation;
- recovery point;
- business outcome.

## E. Leadership and influence

Use Story 10 supported by Story 1 or 3.

Required missing data:

- team goal;
- conflict;
- delegation;
- measurable outcome;
- mechanism that outlasted Nathanel's direct involvement.

---

# Answer format for personal stories

Use this six-part structure.

```text
1. Context and scale
2. User/business risk
3. Invariant and decision
4. Execution and cross-team leadership
5. Measured result
6. Learning and durable mechanism
```

## Example opening

> I will use a real example from SES/O3b Networks. The environment crossed AWS, Azure, private cloud, and 11 data centers, with roughly 2,500 managed systems. The immediate technical issue was X, but the larger risk was Y.

## Example trade-off statement

> We considered A and B. I rejected A because it would have reduced short-term work but created one shared failure domain. I chose B, accepted the additional operational cost, and measured it through C.

## Example uncertainty statement

> I do not want to invent the exact peak value. The documented estate size was approximately 2,500 systems; for the interview design I would separately state a hypothetical traffic assumption.

This is a stronger signal than presenting an unsupported number.

---

# Claims to avoid until documented

Do not state these as facts without a source:

- exact 99.99% availability attributable to one Nathanel-designed platform;
- exact number of incidents reduced;
- exact deployment-frequency increase;
- exact cloud cost saving beyond the documented approximately $100K annual infrastructure reduction at Alexander Street Press;
- exact number of systems migrated to cloud unless present in the selected CV/source;
- production Karpenter, EKS Pod Identity, ARC, IoT Jobs, Kinesis millions-per-second, or Cognito multi-Region experience;
- zero downtime or zero data loss;
- exactly-once delivery;
- a specific AWS quota from memory.

Use the curriculum for architecture judgment and the story bank for truthful experience. Keep those evidence classes separate.