# Multi-Region Disaster Recovery, Write Fencing, Failover, and Failback

## Interview scenario

A critical service must survive regional failure, major dependency outage, destructive operator error, data corruption, or control-plane loss. The architecture spans global routing, regional application cells, databases, caches, queues, object storage, identity, secrets, observability, and deployment systems.

The Staff/Principal task is not to say “deploy in two regions and use DNS failover.” It is to define the business recovery contract, separate availability from data recovery, establish destination eligibility, prevent split brain, automate only evidence-backed transitions, and prove both failover and failback through repeated exercises.

---

## 1. Ninety-second Staff/Principal answer

> I begin with business impact analysis and assign each user journey an RTO, RPO, maximum tolerable disruption, degraded-mode contract, and dependency tier. Then I choose active-active, active-passive, warm standby, or pilot light based on write semantics, data technology, capacity, operational maturity, and cost rather than applying one topology to every service.
>
> I separate global routing, regional application cells, and data authority. A region is eligible to receive traffic only when application capacity, dependencies, identity, secrets, certificates, configuration, observability, and data are all within policy. DNS can participate in steering, but I do not rely on DNS alone because recursive caches, long-lived connections, and client behavior delay convergence.
>
> For stateful services, the first safety requirement is writer fencing. The old region must lose authority through quorum, lease epoch, storage-level fencing, or a resource-enforced token before the new region can write. Replication lag becomes a business recovery metric: I quantify the last durable position, potential loss, replayable work, duplicates, and required reconciliation.
>
> Failover is an idempotent state machine with prechecks, incident command, one decision log, explicit hold points, abort conditions, and user-SLI verification. Failback is a separate operation after the original region is rebuilt, patched, resynchronized, load-tested, and reintroduced gradually. Recovery is complete only when redundancy, backups, monitoring, and normal operating controls are restored.

### Fifteen-second version

> Define RTO and RPO per journey, make destination eligibility explicit, fence the old writer, shift traffic through a state machine, reconcile data, and test failback as seriously as failover.

---

## 2. Recovery vocabulary

### Recovery Time Objective

RTO is the target time to restore an acceptable service level after a qualifying disruption.

Clarify:

- Detection time included or excluded.
- Incident declaration included or excluded.
- Degraded mode versus full service.
- Per-journey and per-tier target.
- Whether backlog drain is part of RTO.

### Recovery Point Objective

RPO is the maximum acceptable data loss expressed as time, transaction count, offset, checkpoint, or another business position.

Examples:

```text
payments: zero committed transaction loss
profile preferences: up to 60 seconds of accepted update loss
analytics: replay from durable stream within four hours
cache: no durability requirement
```

### Maximum Tolerable Downtime or Disruption

The business limit beyond which impact becomes unacceptable. RTO should be meaningfully below it.

### Recovery Time Actual

The measured time achieved in an incident or exercise. Track distribution and dependencies rather than one best result.

### Recovery Point Actual

The measured data-loss or staleness position after recovery.

### Recovery debt

Temporary or incomplete conditions after service restoration:

- Reduced redundancy.
- Paused replication.
- Disabled policy or automation.
- Emergency credentials.
- Unreconciled backlog.
- Manual routing override.
- Missing backup or observability coverage.

Every item needs an owner and exit condition.

---

## 3. Tier the system

Do not give every service the same DR target.

Example:

| Tier | Example capability | RTO | RPO | Typical posture |
|---|---|---:|---:|---|
| Tier 0 | authorization, command authority, financial commit | minutes | zero or near-zero | active-active or hot passive with strong fencing |
| Tier 1 | customer API, checkout, playback start | tens of minutes | seconds to minutes | warm or active regional cells |
| Tier 2 | notifications, preferences, batch ingestion | hours | minutes to hours | warm standby or replayable queue |
| Tier 3 | analytics, development tooling | business-defined | replay or backup | pilot light or restore |

The values are illustrative. Product, legal, security, data, and engineering owners approve the real contract.

Dependencies inherit constraints. A Tier 0 service with a Tier 3 identity or secret dependency is not Tier 0 in practice.

---

## 4. Failure taxonomy

Design recovery for distinct events:

- Availability-zone failure.
- Complete regional application failure.
- Regional network isolation.
- Managed data-service failure.
- Identity, secret, certificate, or DNS failure.
- Control-plane outage while data plane continues.
- Bad deployment or configuration replicated everywhere.
- Data corruption replicated to the standby.
- Credential compromise.
- Account, subscription, or project isolation.
- Operator or automation error.
- Third-party dependency outage.
- Telemetry or incident-tooling failure.

Multi-region architecture does not solve common-mode software, configuration, identity, or corruption failures automatically.

---

## 5. Architecture patterns

## 5.1 Active-active

Multiple regions serve production traffic concurrently.

Strengths:

- Capacity already active.
- Continuous traffic proves many dependencies.
- Lower traffic-shift delay.
- Regional failure can be a routing adjustment.

Risks:

- Multi-writer consistency.
- Conflict resolution.
- Global coordination latency.
- Larger common-change blast radius.
- More complex data and cache behavior.
- Harder operational ownership.

Use when the data model and organization can support the required consistency and fencing.

## 5.2 Active-passive or hot standby

One region owns normal traffic; another is fully running and validated.

Strengths:

- Simpler write authority.
- Easier reasoning about consistency.
- Fast failover when standby is truly hot.

Risks:

- Standby drift.
- Idle-capacity cost.
- Untested rare dependencies.
- Failover may expose latent scale or configuration defects.

## 5.3 Warm standby

The secondary region runs at reduced capacity and scales during failover.

Strengths:

- Lower cost than hot standby.
- Most architecture and dependencies already exist.

Risks:

- Provisioning, quota, image, IP, and startup delay.
- Capacity may not become useful within RTO.
- Dependencies may have independent scaling limits.

## 5.4 Pilot light

Critical data and minimal control components exist; compute is restored during disaster.

Strengths:

- Lower standing cost.
- Appropriate for longer RTO.

Risks:

- More steps and dependencies during crisis.
- Unused automation can drift.
- Quota and artifact availability become critical.

## 5.5 Backup and restore

Restore from durable backups into a new environment.

Strengths:

- Protects against corruption and destructive change.
- Low standing cost.

Risks:

- Longest RTO.
- Restore throughput and validation dominate.
- Backups can be unusable without testing.

A mature design often combines patterns: active regional applications, replicated operational data, and independent backup for corruption recovery.

---

## 6. Separate control plane, data plane, and data authority

```text
global control plane
  routing intent, deployment, configuration, identity policy
        |
        v
regional data plane
  gateway, application, cache, queue consumers, local dependencies
        |
        v
data authority
  writer ownership, replication, durable log, backup, reconciliation
```

A control-plane outage may leave existing data-plane configuration working. DR automation should not depend exclusively on the failed control plane.

A data plane can appear healthy while data authority is unsafe. Readiness must not grant write ownership.

Keep break-glass and recovery tooling outside the failure domain it repairs.

---

## 7. Global traffic steering

Traffic steering can use:

- Anycast or global proxy.
- CDN origin groups.
- Global load balancer.
- DNS policies and health checks.
- Client endpoint discovery.
- Service-mesh or multi-cluster routing.
- Network route advertisement.

### Why DNS alone is insufficient

- Recursive resolvers cache answers.
- TTL is not a forced-expiration timer for all clients.
- Existing TCP, HTTP/2, WebSocket, and QUIC sessions persist.
- Mobile and enterprise clients cache aggressively.
- Negative caching can prolong failure.
- DNS health may not represent application or data readiness.
- Lowering TTL after the incident does not clear existing caches.

DNS remains useful for coarse location and fallback. Combine it with a routing layer that can stop sending new connections quickly, and design clients for bounded reconnect and rediscovery.

---

## 8. Destination eligibility

Do not send traffic to a region merely because compute instances or pods are running.

Eligibility gates:

### Application

- Correct artifact and configuration revision.
- Capacity available within policy.
- Business-path synthetic succeeds.
- Queues, pools, and caches are stable.

### Data

- Replication state within RPO.
- Writer authority can be transferred safely.
- Schema and migration compatible.
- Backup and point-in-time recovery healthy.
- Reconciliation path available.

### Dependencies

- Database, cache, queue, object store, search, and third parties ready.
- Quotas and connection limits sufficient.
- Regional endpoints and routes correct.

### Security and identity

- Certificates and trust bundles valid.
- Workload and customer identity paths functional.
- Secrets and keys available.
- Audit logging enabled.
- Emergency access tested.

### Observability and operations

- User SLIs and synthetics available.
- Logs, traces, metrics, and events export.
- On-call access and runbooks available.
- Incident command can communicate independently.

Represent eligibility as explicit machine-readable checks, not operator memory.

---

## 9. Write fencing and split-brain prevention

The most dangerous failover is two regions accepting authoritative writes.

### Fencing strategies

- Consensus or quorum elects one leader.
- Lease or epoch stored in a strongly consistent authority.
- Storage system supports one writable primary.
- Resource validates monotonically increasing fencing tokens.
- Network or account isolation removes old writer access.
- Manual dual-control promotes one writer after evidence.

### Fencing token model

```text
writer A owns epoch 41
failover authority issues epoch 42 to writer B
resource rejects all writes carrying epoch <= 41
```

The resource must enforce the token. A controller's belief that writer A is dead is insufficient when the node or region may be partitioned.

### Manual versus automatic promotion

Automatic promotion is appropriate only when:

- Failure detection is trustworthy.
- Old writer can be fenced automatically.
- Destination data and capacity are eligible.
- Repeated automation cannot oscillate.
- A clear abort path exists.

Otherwise require incident-command approval and dual control.

Availability should not be purchased with ambiguous ownership of critical data.

---

## 10. Replication and data recovery

Replication protects availability but can replicate corruption. Backups protect historical recovery but may have longer RTO.

Track:

- Durable commit position.
- Replication lag by time and bytes or transactions.
- Apply or replay lag.
- Failed or poisoned records.
- Last successful backup and restore test.
- Schema and encryption-key compatibility.

### Synchronous replication

Strengths:

- Low or zero RPO for committed writes.

Costs:

- Cross-region latency.
- Availability trade-offs under partition.
- Quorum complexity.

### Asynchronous replication

Strengths:

- Lower write latency.
- Regional independence.

Costs:

- Nonzero RPO.
- Promotion must quantify lost or unapplied writes.
- Reconciliation is required.

### Event-log and replay model

A durable append-only log can support:

- Rebuild of derived state.
- Consumer restart from checkpoint.
- Duplicate-tolerant replay.
- Audit of accepted operations.

Requirements:

- Stable identifiers.
- Idempotent consumers.
- Ordering boundaries.
- Retention longer than recovery horizon.
- Poison-message handling.
- Checkpoint integrity.

---

## 11. RPO is a business metric

Do not report only:

```text
replication lag = 37 seconds
```

Translate it:

- Which transactions may be absent?
- Were they acknowledged to users?
- Are they replayable from a queue or client retry?
- Could replay duplicate a side effect?
- Which tenants or shards are affected?
- Is the data security- or compliance-sensitive?

Example:

```text
last durable secondary position: offset 9,120,000
last acknowledged primary position: offset 9,123,500
potential gap: 3,500 events
2,900 remain in durable upstream queue
600 require reconciliation against source systems
```

This is more actionable than a time lag alone.

---

## 12. Failover state machine

```text
NORMAL
  |
  | qualifying impact
  v
ASSESS
  |
  +--> false alarm or local mitigation -> NORMAL
  |
  v
FREEZE CHANGES
  |
  v
CHECK DESTINATION ELIGIBILITY
  |
  +--> not eligible -> HOLD / DEGRADED MODE
  |
  v
FENCE OLD WRITER
  |
  +--> cannot prove fencing -> HOLD / READ-ONLY
  |
  v
PROMOTE DATA AUTHORITY
  |
  v
SHIFT SMALL TRAFFIC COHORT
  |
  +--> abort criteria -> ROLLBACK OR HOLD
  |
  v
EXPAND TRAFFIC
  |
  v
VERIFY USER SLI AND DATA
  |
  v
RECOVERED IN SECONDARY
```

Every state defines:

- Entry evidence.
- Authorized owner.
- Idempotent action.
- Timeout.
- Abort condition.
- Audit event.
- Verification signal.

Do not automate state transitions that cannot be made safe and observable.

---

## 13. Failover prechecks

Before shifting meaningful traffic:

- Incident commander and decision owner assigned.
- Change freeze active.
- Destination image, configuration, and schema approved.
- Required capacity and quotas available.
- Critical dependencies healthy.
- Data lag and potential loss within approved RPO or explicitly accepted.
- Old writer fenced.
- Destination writer promoted.
- Identity, secrets, keys, certificates, and audit verified.
- External business synthetic succeeds.
- Observability and support tooling available.
- Rollback or hold path understood.

Some incidents require degraded service instead of unsafe write promotion.

---

## 14. Traffic shift strategy

Prefer progressive exposure:

```text
internal synthetic
  -> employee or test cohort
  -> 1%
  -> 5%
  -> 25%
  -> 50%
  -> 100%
```

Advance only when:

- Journey availability and latency within guardrail.
- Protected cohorts healthy.
- Dependency saturation safe.
- Queue age stable.
- Data errors and reconciliation gap bounded.
- No writer ambiguity.
- Telemetry unknown rate acceptable.

Hold or abort on:

- Fast SLO burn.
- Error or latency regression.
- Data inconsistency.
- Dependency or quota pressure.
- Replication or checkpoint failure.
- Identity or security failure.
- Loss of observability.

For total primary unavailability, the initial shift may be larger, but the eligibility and fencing requirements remain.

---

## 15. Long-lived connections and clients

Failover must account for:

- WebSockets.
- Streaming sessions.
- HTTP/2 and QUIC connection reuse.
- Mobile reconnect backoff.
- Client-side endpoint cache.
- DNS cache.
- Tokens bound to region or issuer.
- Stateful sessions.

Controls:

- Bounded connection lifetime.
- Server-side drain.
- Retry budget and jitter.
- Endpoint rediscovery.
- Region-neutral or migratable session state.
- Idempotent reconnect.
- Client observability by version and network.

A global router can stop new connections immediately while old sessions remain attached to the failed path.

---

## 16. Degraded modes

Define safe degraded behavior before disaster:

- Read-only mode.
- Stale but bounded cache.
- Queue writes for later processing.
- Disable noncritical features.
- Limit high-risk operations.
- Serve maintenance or explicit retry response.
- Local device authority when cloud is unavailable.

A degraded result counts as good only when it meets the documented product, correctness, freshness, and security contract.

Do not hide failed writes behind generic success responses.

---

## 17. Identity, secrets, and keys

Regional recovery requires:

- Workload identity available in destination.
- Human break-glass roles independent of primary.
- Secret and certificate replication or independent issuance.
- Encryption-key access and policy.
- Audit logging.
- Revocation of compromised or stale credentials.
- Token issuer and audience compatibility.

Common-mode risks:

- One global identity service.
- One certificate authority path.
- Secrets replicated with the same corruption.
- Emergency access requiring the failed network.
- Keys available but policy absent.

Test identity and secret flows as business-path dependencies.

---

## 18. Infrastructure, artifacts, and configuration

Destination must have:

- Reproducible infrastructure definitions.
- Versioned regional parameters.
- Container images and packages available independently.
- Configuration and policy version.
- Database schema and migration state.
- Quotas and address capacity.
- DNS, certificates, and network routes.
- Security and observability agents.

Do not rebuild from unpinned mutable tags or a package repository available only in the failed region.

Continuously validate drift and restore from a known-good revision.

---

## 19. Observability and incident command

Required signals:

- Global and regional journey SLOs.
- Protected cohorts.
- Region eligibility state.
- Routing distribution.
- Available and useful capacity.
- Replication, apply, and checkpoint lag.
- Writer epoch or authority.
- Queue age and replay position.
- Identity, secret, and certificate health.
- Telemetry-pipeline health.
- Recovery state-machine transition and owner.

Incident command maintains:

- One UTC timeline.
- One decision log.
- Current state and next hold point.
- Risk and unknowns.
- Customer and leadership communication.
- Evidence and commands.

The failover controller emits structured audit events for every transition.

---

## 20. Failback is not reverse failover

The original region may contain:

- Stale or divergent writes.
- The initiating defect.
- Old configuration or certificates.
- Partial infrastructure.
- Reduced monitoring.
- Backlog and local side effects.

Failback sequence:

1. Repair or rebuild from known-good infrastructure and artifacts.
2. Patch the initiating failure.
3. Restore security, identity, observability, and dependencies.
4. Establish replication from the active recovery region.
5. Validate lag, schema, checksums, and reconciliation.
6. Load-test and run business synthetics.
7. Fence and define writer transfer.
8. Shift a small cohort.
9. Expand under SLO and data guardrails.
10. Restore redundancy and normal routing.
11. Remove temporary overrides and emergency access.
12. Verify backup and future failover posture.

Do not rush failback merely to return to the familiar topology.

---

## 21. Testing program

### Component tests

- Backup restore.
- Replica promotion.
- Fencing-token rejection.
- Queue replay.
- Secret and certificate issuance.
- Infrastructure recreation.

### Regional tests

- Traffic shift.
- Zone or region isolation.
- Dependency loss.
- Identity-plane loss.
- Control-plane loss while data plane serves.
- Destination capacity scale-up.

### Data tests

- Lag within RPO.
- Lost-write quantification.
- Duplicate replay.
- Conflict resolution.
- Corruption recovery from backup.
- Schema rollback and forward compatibility.

### Operational tests

- Incident command.
- Break-glass access.
- Communications.
- Runbook freshness.
- Manual approval and dual control.
- Telemetry during failure.

### Failback tests

- Reverse replication.
- Writer transfer.
- Progressive return.
- Re-protection and cleanup.

Measure actual RTO and RPO in every exercise.

---

## 22. DR scorecard

For each critical journey track:

| Dimension | Evidence |
|---|---|
| Business contract | approved RTO, RPO, degraded mode, owner |
| Architecture | failure domains and topology |
| Destination eligibility | automated health and capacity checks |
| Data | replication, backup, restore, reconciliation |
| Fencing | resource-enforced stale-writer rejection |
| Routing | new and long-lived connection behavior |
| Identity and security | regional independence and audit |
| Observability | SLI, state-machine, data and routing telemetry |
| Operations | runbook, access, incident command |
| Testing | last failover and failback result |
| Recovery debt | open risks and due dates |

A diagram without recent test evidence is not a DR capability.

---

## 23. Common weak answers

### “Use active-active everywhere”

This ignores consistency, conflict, operational maturity, and cost.

### “Use DNS failover”

DNS does not guarantee fast convergence for caches and long-lived connections, and it does not prove destination readiness.

### “Replication means zero data loss”

Asynchronous lag and unapplied transactions create nonzero RPO. Synchronous systems still need corruption recovery.

### “Promote the secondary if health check fails”

Health, fencing, data, capacity, identity, dependencies, and observability must all be eligible.

### “Failover is complete when traffic moves”

Data reconciliation, backlog, hidden cohorts, and recovery debt may remain.

### “Failback is just change the weights back”

The original region must be rebuilt, resynchronized, tested, and safely regain authority.

### “The cloud provider handles DR”

Managed services provide mechanisms. The application owns business semantics, routing, dependencies, consistency, recovery policy, testing, and operations.

### “Backups exist, so we can recover”

Only tested restore throughput and validation prove recoverability.

---

## 24. Adversarial interview questions

### How do you choose active-active versus active-passive?

Use write consistency, conflict model, latency, data technology, traffic, RTO/RPO, operational maturity, and cost. Choose per capability rather than globally.

### What if the primary is partitioned but still writing?

Do not promote until old authority is fenced through quorum, epoch, storage, or network controls that the resource enforces. Read-only degraded mode may be safer.

### What if the standby lag exceeds RPO?

Escalate business risk, determine whether accepted operations are replayable, quantify loss, and choose hold, degraded service, or explicit exception. Do not hide the gap.

### How do you know the destination has capacity?

Continuously measure useful serving capacity, quotas, dependency limits, pod or process startup, target health, cache warmup, and load tests. “Instances exist” is insufficient.

### How do you automate without causing oscillation?

Use an idempotent state machine, hysteresis, minimum hold times, one transition owner, explicit writer epochs, abort conditions, progressive traffic, and a global stop.

### When is automatic failover inappropriate?

When writer fencing is uncertain, data loss requires human acceptance, destination eligibility is incomplete, failure detection is ambiguous, or oscillation risk is high.

### What if both regions share one global dependency?

Treat it as a common-mode failure. Add regional independence, alternate path, safe degraded mode, or redefine the honest recovery contract.

### How do you test without risking customers?

Begin with component restores, isolated environments, shadow traffic, synthetic cohorts, small production cells, scheduled game days, and progressive blast-radius expansion with abort controls.

---

## 25. Staff/Principal checklist

A strong answer includes:

- Business impact analysis and tiered RTO/RPO.
- Active-active, active-passive, warm, and pilot-light trade-offs.
- Control plane, data plane, and data authority separation.
- Traffic steering beyond DNS alone.
- Explicit destination eligibility.
- Resource-enforced writer fencing.
- Replication, backup, replay, and reconciliation.
- Idempotent failover state machine.
- Progressive traffic and abort conditions.
- Long-lived connection and client behavior.
- Identity, secrets, keys, and artifact independence.
- User SLI, data, routing, and authority observability.
- Controlled failback and recovery-debt closure.
- Repeated failover and failback tests.

---

## Primary references

- [Google SRE Book — Managing Critical State](https://sre.google/sre-book/managing-critical-state/)
- [Google SRE Workbook — Incident Response](https://sre.google/workbook/incident-response/)
- [Kubernetes multi-cluster services](https://multicluster.sigs.k8s.io/)
