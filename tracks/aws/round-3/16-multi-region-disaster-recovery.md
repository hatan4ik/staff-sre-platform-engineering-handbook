# Question 16 — Multi-Region Disaster Recovery with Minimal Downtime and Automated Failover

## Interview prompt

How would you architect a multi-Region disaster-recovery solution on AWS with minimal downtime and automated failover?

## What the interviewer is testing

The interviewer wants more than “Route 53 plus a secondary Region.” A Staff/Principal answer must define:

- business RTO and RPO
- failure scope and declaration authority
- regional independence
- traffic, compute, state, identity, secrets, and delivery recovery
- data conflict and write-fencing behavior
- automation safety
- failback
- proof through game days

The most dangerous DR system is one that automatically creates two writers or shifts traffic into an unready Region.

---

## 90-second Staff/Principal answer

> I begin with workload-specific RTO and RPO, because minimal downtime can mean active-active or a warm standby and has a large cost and consistency impact. I build complete regional cells with no synchronous dependency on the other Region: edge, API, compute, configuration, secrets, observability, queues, and adequate quota all exist locally.
>
> Traffic is fronted by Route 53, Global Accelerator, or CloudFront depending on protocol and caching. For controlled regional failover I use Amazon Application Recovery Controller routing controls or Region switch, with safety rules and a tested CLI/API runbook. ARC readiness checks help find capacity and configuration drift before an incident, but they are not the critical-path health signal for failover.
>
> Data recovery is selected per datastore. DynamoDB Global Tables support multi-Region access where conflict semantics fit. Aurora Global Database provides cross-Region replicas and controlled promotion, with a nonzero RPO possible during unplanned failover. S3 uses versioning and replication; ECR and configuration artifacts are replicated; queues and streams use an explicit replay or dual-ingestion design rather than assumed transparent failover.
>
> Automation evaluates multiple user-facing and infrastructure signals, verifies destination readiness, fences the old writer, shifts traffic in stages, and can stop on safety-rule violations. It does not fail over from one noisy alarm. Recovery is proven with external synthetics, data consistency checks, queue drainage, and SLOs. Failback is a new planned migration, not a reversal button.

---

## 1. Define the recovery objective

### RTO

Recovery Time Objective:

```text
maximum acceptable time from disaster impact to restored service
```

### RPO

Recovery Point Objective:

```text
maximum acceptable acknowledged data loss or rollback window
```

Define them by capability:

| Capability | Example RTO | Example RPO |
|---|---:|---:|
| Read-only catalog | 5 minutes | 15 minutes acceptable |
| Authentication | 2 minutes | user directory writes measured in seconds |
| Payment write | 1 minute | near-zero acknowledged write loss |
| Analytics | 4 hours | replay from durable event archive |
| Notification delivery | 30 minutes | no event loss, delay acceptable |

Do not declare one enterprise RPO without transaction semantics.

### Failure scenarios

Design separately for:

- one Availability Zone
- regional network or service impairment
- control-plane impairment while data planes continue
- application corruption
- bad global deployment
- credential or signing compromise
- data corruption
- operator error

Multi-Region infrastructure does not protect against bad code deployed everywhere or globally replicated corruption.

---

## 2. DR strategy selection

### Backup and restore

```text
primary Region active
secondary rebuilt from backups after disaster
```

- lowest steady-state cost
- highest RTO
- recovery depends on infrastructure recreation and restore testing

### Pilot light

```text
critical data and minimal services replicated
compute scales after declaration
```

- moderate cost
- RTO includes provisioning, warmup, and validation

### Warm standby

```text
complete secondary stack at reduced capacity
scale and shift traffic during recovery
```

- common balance for low-minute RTO
- destination capacity realization must be tested

### Active-passive hot standby

```text
complete secondary at full or near-full capacity, no normal writes/traffic
```

- faster failover
- easier write authority than active-active
- higher cost

### Active-active

```text
multiple Regions serve production concurrently
```

- low traffic-shift RTO
- highest data-consistency, routing, operational, and testing complexity
- failures can propagate through shared global systems

Choose per service, not by slogan.

---

## 3. Regional cell architecture

```text
Global entry
    |
    +--> Region A cell
    |     edge endpoint
    |     API/load balancer
    |     EKS/Lambda/ECS
    |     regional data/cache/queue
    |     secrets/config/observability
    |
    +--> Region B cell
          same independently operable stack
```

A regional replica is complete only when it can operate without the failed Region.

### Hidden cross-Region dependencies to eliminate

- one regional database writer
- one Secrets Manager secret without replica or recovery
- one regional KMS key path
- one CI or GitOps controller required for emergency operation
- one ECR repository without replicated images
- one regional NAT, transit, identity broker, or DNS dependency
- synchronous calls to the other Region
- monitoring and incident tooling only in the primary
- hardcoded regional endpoint in clients

### Stack boundaries

Keep Terraform or CloudFormation state and stacks regional where possible. A failed Region should not block deployment or recovery of the other Region because both are locked in one monolithic state.

---

## 4. Traffic management options

### Route 53

Use:

- failover records
- latency-based records
- weighted records
- health checks
- ARC routing-control health checks

Understand TTL and recursive resolver caching. DNS changes do not move every existing connection immediately.

### Global Accelerator

Useful for:

- static anycast IPs
- TCP/UDP traffic
- endpoint health-based routing
- rapid routing of new connections

Existing long-lived connections may still require client reconnect behavior.

### CloudFront

Useful for:

- global HTTP edge
- cached content
- origin groups or failover patterns
- reducing regional load

Origin failover does not solve stateful write routing or data authority.

### Client endpoint discovery

Mobile or device clients may need:

- multiple endpoints
- reconnect jitter
- endpoint cache expiry
- region-affinity token
- home-region or cell assignment
- recovery bootstrap endpoint

Do not rely solely on DNS when clients hold long-lived connections indefinitely.

---

## 5. Amazon Application Recovery Controller

### Routing controls

ARC routing controls are on/off switches integrated with Route 53 health checks and can redirect traffic between regional replicas.

Use:

- one routing control per regional cell
- control panels aligned with recovery units
- CLI or API against the routing-control data-plane endpoints
- least-privilege recovery roles
- tested endpoint selection

### Safety rules

Safety rules prevent dangerous control states.

Examples:

```text
at least one Region must remain enabled
only one writer Region may be active
secondary cannot be enabled until a readiness gate is satisfied
```

Safety rules are a guardrail against automation and operator error.

### Readiness checks

Readiness checks monitor configuration and capacity readiness such as quotas, resource parity, and routing policies.

Use them during normal operations to detect drift. Do not make readiness checks the sole critical-path failover decision during an active event.

### Region switch

Where supported and appropriate, ARC Region switch can orchestrate recovery plans composed of execution blocks, including traffic and supported resource operations.

Treat the plan as production code:

- version control
- review
- dry-run or plan evaluation
- dependencies
- step timeout
- rollback or pause points
- game-day verification

### Data-plane discipline

Recovery tooling must remain usable during a regional control-plane impairment. Pre-create resources, roles, endpoints, and runbooks.

---

## 6. Compute recovery

### EKS

Each Region has an independent EKS cluster with:

- tested Kubernetes version and add-ons
- system node capacity
- Karpenter or node-group configuration
- ingress and certificates
- workload identity
- policy and observability
- replicated immutable images
- GitOps desired state

Do not create the secondary cluster during the disaster for a low-minute RTO.

### Warm capacity

Measure:

```text
scale request
  -> EC2 capacity obtained
  -> node joined
  -> image pulled
  -> pod ready
  -> target healthy
  -> cache and connection pools warm
```

Destination quota and subnet IPs must cover full failed-over load.

### Lambda

Replicate:

- function versions
- aliases
- layers
- environment configuration
- IAM roles
- event sources
- concurrency quotas

Do not assume an infrastructure template proves package and dependency availability.

### ECR

Use cross-Region replication or a controlled release process so every required image digest exists in the destination before promotion.

A secondary cluster that must pull from the impaired Region is not independent.

---

## 7. DynamoDB recovery model

### Global Tables

Use when:

- multi-Region access is required
- key design distributes load
- application can tolerate and resolve concurrent-write conflicts
- table and index configuration is consistent

### Write conflict

Global replication does not create a universal strongly ordered multi-Region transaction.

Choose:

- active-active last-writer-wins where business semantics permit
- home-region ownership per key
- conditional and versioned writes
- command or transaction fencing
- event-sourced conflict resolution

### Failover

If applications already use regional endpoints with replicated data, traffic failover can be fast. Validate:

- replication health
- regional autoscaling capacity
- IAM/KMS
- streams and consumers
- global-secondary indexes
- TTL and backup behavior

### Data corruption

Global Tables can replicate logical corruption. Use point-in-time recovery, backups, validation, and controlled restore. Availability replication is not a corruption backup.

---

## 8. Aurora Global Database recovery

### Normal design

- primary writer cluster
- secondary clusters in other Regions
- local readers where useful
- application endpoints and secret configuration per Region

### Planned switchover

For maintenance or migration:

1. reduce or quiesce writes
2. verify replication lag
3. perform managed switchover
4. update routing and application writer configuration
5. validate

### Unplanned failover

An unplanned failover can have a nonzero RPO measured according to replication lag and failure conditions.

The application must handle:

- possible lost acknowledged writes within the documented recovery envelope
- duplicate client retries
- connection reset and DNS/endpoint change
- promoted secondary
- reconciliation of uncertain transactions

### Fencing

Before promoting a secondary, prevent the old primary from accepting writes if it becomes reachable again.

Use:

- network and routing control
- database role state
- application writer lease or epoch
- regional command fencing

Two active writers without a supported conflict model are worse than downtime.

### Failback

Re-establish replication and perform a planned migration. Do not immediately fail back simply because the old Region appears healthy.

---

## 9. S3 and object recovery

Use:

- versioning
- cross-Region replication
- replication metrics and failure notifications
- independent KMS access
- Object Lock where required
- lifecycle compatible with recovery

Decide:

- whether delete markers replicate
- whether old versions are retained
- how existing objects are backfilled
- what happens to writes during failover
- which Region is authoritative after failover

For globally writable object namespaces, avoid key collisions or define conflict ownership.

---

## 10. Queues, streams, and event recovery

### SQS

SQS queues are regional. Options:

- producer writes to a regional queue and durable event store
- dual publication through an outbox
- replicate events through a stream or archive
- replay unprocessed work after recovery

Do not pretend an SQS queue transparently fails over across Regions.

### Kinesis

Streams are regional. Design:

- dual-region ingestion
- replicated event archive in S3
- consumer checkpoint strategy
- idempotent replay
- sequence and partition semantics

### EventBridge

Use cross-Region event routing where appropriate, but design duplicate handling and failure of the forwarding path.

### Transactional outbox

For business events:

```text
business write + outbox record in one transaction
  -> publisher reads outbox
  -> regional event bus/stream
  -> replication or archive
  -> consumers idempotently process
```

This prevents a database commit without its recovery event.

---

## 11. Identity, secrets, and keys

### Cognito

Use multi-Region replication where available and test custom-domain or client endpoint failover.

Understand which directory and administrative writes remain authoritative.

### IAM

Pre-create:

- recovery roles
- workload roles
- break-glass access
- trust relationships
- permission boundaries

Do not depend on creating emergency IAM during an identity control-plane incident.

### Secrets Manager

Replicate secrets or maintain regional copies through an owned rotation workflow.

Test:

- version labels
- rotation
- application reload
- destination KMS permissions
- old/new credential overlap

### KMS

Use regional or multi-Region key architecture according to application and compliance requirements.

A multi-Region key does not automatically replicate every encrypted data object or grant. Test decrypt capability in the destination.

---

## 12. Failover decision model

### Signals

Use multiple independent signals:

- external synthetic transaction
- user SLI and burn rate
- regional endpoint health
- dependency health
- data replication lag
- destination capacity
- AWS Health events
- operator confirmation for ambiguous events

### Avoid one-alarm automation

One noisy metric can cause unnecessary failover and create a larger outage.

Use a state machine:

```text
SUSPECTED
  -> CONFIRMED
  -> DESTINATION_VERIFIED
  -> SOURCE_FENCED
  -> TRAFFIC_CANARY
  -> TRAFFIC_MIGRATING
  -> RECOVERED
  -> STABILIZING
```

### Automated versus human-authorized

Fully automatic failover is appropriate only when:

- signals are reliable
- source fencing is guaranteed
- destination capacity is proven
- data semantics support it
- repeated game days demonstrate safety

Otherwise automate evidence collection and execution while retaining an explicit human declaration.

---

## 13. Failover sequence

Example active-passive sequence:

1. declare regional disaster and incident commander
2. freeze deployments and nonessential writes
3. verify destination infrastructure, quota, images, config, and secrets
4. inspect data replication lag and select recovery point
5. fence old writer and command authority
6. promote destination datastore where required
7. enable destination application writes
8. shift a small traffic percentage or controlled cohort
9. verify user transaction and data consistency
10. move remaining traffic
11. monitor source stragglers and long-lived connections
12. drain/replay queues and reconcile uncertain writes
13. restore full redundancy

Each step has a timeout, evidence, abort rule, and owner.

---

## 14. Capacity planning for failover

### N+1 Region capacity

For active-active across two Regions at 50/50, each Region must be capable of taking 100% plus headroom after one fails.

Normal utilization cannot remain at 90% in both Regions.

### Warm standby scaling

Measure actual scale-up time. Include:

- service quotas
- EC2 capacity availability
- subnet IPs
- load-balancer targets
- database connections
- cache warmup
- third-party rate limits

### Dependency budget

If frontend capacity doubles after failover but the database writer does not, latency and errors can worsen.

Model the whole request path.

---

## 15. Observability and recovery SLIs

### Readiness

- resource parity
- image/config version
- quota headroom
- data lag
- secret and certificate validity
- synthetic transaction
- warm capacity

### Failover

- time to declaration
- time to fence
- time to promote data
- time to first successful destination transaction
- traffic-shift duration
- error rate during transition
- acknowledged write loss

### Recovery

- RTO achieved
- RPO achieved
- backlog and queue age
- duplicate transaction rate
- data-reconciliation count
- time to restore redundancy

### Alerting

Page on user impact and failover blockers. Ticket slower readiness drift before an incident.

---

## 16. Failback

Failback is a separate planned event.

1. root cause resolved and Region stable
2. infrastructure and security parity restored
3. data replication direction established
4. conflict and uncertain transactions reconciled
5. destination remains authoritative until planned switch
6. canary traffic moves
7. full traffic moves
8. old recovery Region returns to standby or active-active role
9. DR readiness is revalidated

Avoid oscillation through stability windows and explicit authority.

---

## 17. Data reconciliation

Identify:

- writes acknowledged before failure but absent after promotion
- duplicate retries
- operations with unknown outcome
- queues processed in both Regions
- object conflicts
- stale cache and session state

Use:

- idempotency records
- transaction IDs
- outbox/event log
- version vectors or epochs where designed
- customer-visible correction workflow
- audit trail

Do not hide data uncertainty behind an availability success metric.

---

## 18. Deployment and configuration safety

### Independent rollout

Deploy:

```text
secondary Region canary
  -> observe
  -> primary Region canary
  -> staged cells
```

Do not deploy the same breaking change everywhere simultaneously.

### Configuration

Version:

- feature flags
- secrets references
- routing
- database endpoints
- schemas
- IAM policies

### Schema migrations

Use expand/contract so old and new application versions can operate during failover and rollback.

A non-backward-compatible schema can invalidate the secondary even when infrastructure is healthy.

---

## 19. DR testing program

### Component tests

- backup restore
- database promotion
- secret access
- ECR image pull
- queue replay
- client endpoint failover

### Game days

- AZ evacuation
- regional traffic shift
- primary database unavailable
- primary control plane unavailable while workload data plane runs
- DNS and long-lived connection behavior
- destination quota shortage
- stale secondary configuration
- old Region returns unexpectedly after promotion
- failed failover step and rollback

### Full isolation test

Block the secondary from every primary-region endpoint and prove it still operates.

### Evidence

Record:

- actual RTO/RPO
- manual steps
- failed assumptions
- capacity bottlenecks
- runbook corrections
- customer and data validation

A tabletop exercise does not prove executable recovery.

---

## 20. Cost and trade-offs

Cost increases with:

- duplicate compute
- replicated databases
- cross-Region data transfer
- duplicate observability
- idle headroom
- test environments

Balance against:

- business outage cost
- contractual availability
- data-loss exposure
- recovery confidence

Optimize by capability. A globally active payment writer and a rebuildable analytics pipeline do not require the same DR tier.

---

## Adversarial follow-ups

### “Why not automatically fail over whenever Route 53 health checks fail?”

A health-check failure can be false, localized, or caused by the check itself. Before shifting writes I verify destination readiness and source fencing. Traffic automation without data-authority safety can create split brain.

### “Does DynamoDB Global Tables give zero RPO?”

It provides multi-Region replication, but replication and concurrent-write semantics must be reflected in the business design. I do not promise zero loss or conflict without workload-specific evidence and documented guarantees.

### “Aurora Global Database is replicated. Why can RPO be nonzero?”

During unplanned failover, asynchronous cross-Region replication may have lag. I measure lag, design idempotent transaction recovery, and state the achievable RPO honestly.

### “Why use ARC instead of editing Route 53 records?”

ARC routing controls provide a highly available recovery data plane, explicit controls, and safety rules. They reduce reliance on ad hoc control-plane edits during an incident.

### “Should readiness checks trigger failover?”

They identify configuration and capacity drift before incidents. AWS guidance does not position readiness checks as the critical-path failover health signal.

### “When do you fail back?”

After root cause, stability, data replication, and readiness are proven. Failback is a planned migration, not an immediate reaction to a green status page.

---

## Weak answers to avoid

- “Use Route 53 failover and replicate the database.”
- no explicit RTO/RPO
- secondary Region depends on primary ECR, secrets, identity, or monitoring
- automatic failover from one alarm
- traffic shift before destination capacity validation
- database promotion without fencing the old writer
- assuming queues transparently replicate
- confusing availability replication with corruption backup
- deploying bad code to all Regions simultaneously
- no failback or data-reconciliation plan
- tabletop-only DR testing

---

## Closing statement

> Multi-Region recovery is a controlled authority transfer. I build independent regional cells, choose data replication from transaction semantics, verify destination readiness, fence the old writer, and shift traffic through guarded stages. The architecture is credible only when measured RTO and RPO are repeatedly demonstrated under failure.