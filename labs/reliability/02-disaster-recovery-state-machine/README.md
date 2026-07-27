# Lab 2 — Disaster Recovery Failover, Fencing, and Failback State Machine

## Interview scenario

The primary region is failing. The secondary appears healthy, but responders must decide whether it is safe to promote data authority and move traffic.

The dangerous shortcuts are:

- route traffic because pods are running;
- promote the secondary before the old writer is fenced;
- ignore replication lag and business RPO;
- shift 100% immediately without a hold point;
- continue during fast error-budget burn or data inconsistency;
- return to the original region before rebuild and resynchronization.

The Staff/Principal task is to encode failover and failback as an idempotent state machine with explicit eligibility, authority, traffic, data, and observability gates.

## Safety invariants

> The destination may receive production traffic only when application, capacity, dependencies, identity, observability, schema, data lag, and business synthetics are within policy.

> The new region may accept authoritative writes only after the old writer is fenced and a newer epoch is issued.

> Fast SLO burn or data inconsistency aborts the traffic transition.

This lab is a deterministic Python simulation. It creates no infrastructure and contacts no cloud service.

## What the simulator models

```text
NORMAL
  -> ASSESS
  -> FREEZE CHANGES
  -> DESTINATION ELIGIBILITY
  -> FENCE OLD WRITER
  -> PROMOTE NEW WRITER EPOCH
  -> CANARY TRAFFIC
  -> EXPAND TRAFFIC
  -> RECOVERED IN SECONDARY
  -> REBUILD AND RESYNCHRONIZE ORIGINAL
  -> FAILBACK CANARY
  -> NORMAL RESTORED
```

Hold or abort states appear when:

- incident command is missing;
- replication lag exceeds RPO;
- capacity is insufficient;
- identity, dependency, observability, schema, or synthetic checks fail;
- old writer fencing is unproven;
- fast burn appears during traffic shift;
- data inconsistency is detected.

## Prerequisites

- Python 3.11 or newer.
- No third-party packages.

## Run the demo

```bash
python3 dr_failover.py --demo
```

Built-in scenarios:

1. **Safe failover**
   - primary fails;
   - destination passes eligibility;
   - old writer is fenced;
   - secondary receives epoch `42` after primary epoch `41`;
   - traffic expands from `5%` to `100%`;
   - stale epoch `41` is rejected.

2. **Replication lag exceeds RPO**
   - secondary lag is `120 seconds` while policy permits `30 seconds`;
   - state machine enters read-only hold instead of promotion.

3. **Old writer not fenced**
   - state machine stops in the fencing state;
   - promotion and traffic shift do not occur.

## Run the tests

```bash
python3 -m unittest -v test_dr_failover.py
```

The test suite proves:

- destination eligibility;
- replication, observability, and synthetic gates;
- safe promotion and full traffic recovery;
- old writer fencing requirement;
- read-only hold for ineligible destination;
- canary abort on fast burn;
- data inconsistency overrides normal automation;
- stale writer-token rejection;
- incident-command prerequisite;
- failback requires rebuild and replication;
- writer epoch advances again during failback;
- invalid regional definitions are rejected.

## Eligibility exercise

For the destination region record:

| Gate | Evidence |
|---|---|
| Application | approved image/configuration, business route succeeds |
| Capacity | useful serving capacity above peak or approved failover demand |
| Dependencies | database, cache, queue, object store, third parties |
| Identity | customer and workload identity, secrets, keys, certificates |
| Observability | SLI, logs, traces, metrics, audit, on-call access |
| Data | lag within RPO, schema compatible, checkpoints and backup healthy |
| Synthetic | external business transaction succeeds |

Compute running is not destination eligibility.

## Writer-epoch exercise

Before failover:

```text
primary writer epoch = 41
secondary accepting writes = false
```

After old-writer fencing and promotion:

```text
primary accepting writes = false
secondary writer epoch = 42
secondary accepting writes = true
```

Resource behavior:

```text
write token 41 -> reject
write token 42 -> accept
```

The resource—not only the controller—must enforce stale-writer rejection.

Production implementations may use:

- consensus term;
- strongly consistent lease epoch;
- storage primary generation;
- fencing token;
- network and identity isolation plus resource authority;
- dual-control manual promotion.

## Replication-lag exercise

Do not stop at:

```text
lag = 120 seconds
```

Translate it into:

- acknowledged transactions potentially absent;
- queue or log positions;
- replayable versus unrecoverable work;
- duplicate side-effect risk;
- affected tenants or shards;
- business acceptance or rejection of the RPO breach.

The lab blocks promotion when lag exceeds policy. A production incident may choose explicit risk acceptance, read-only mode, replay, or manual reconciliation, but the gap must be visible.

## Traffic-shift exercise

The lab starts at `5%` and advances in `25%` steps.

Production steps can be:

```text
internal synthetic
  -> employee/test cohort
  -> 1%
  -> 5%
  -> 25%
  -> 50%
  -> 100%
```

Advance only when:

- user availability and latency within guardrail;
- protected cohorts healthy;
- dependencies and quotas stable;
- no data inconsistency;
- authority unambiguous;
- telemetry unknown rate within policy.

Fast burn changes the lab state to read-only hold.

## Failback exercise

Failback is allowed only after:

- original region rebuilt or repaired;
- initiating defect removed;
- application, dependencies, identity, observability, and synthetics healthy;
- data replication from active recovery region healthy;
- schema compatible;
- capacity verified.

The original region receives a newer writer epoch (`43` in the built-in path), then traffic moves back progressively.

Failback completion also requires:

- redundancy restored;
- backups and replication normal;
- emergency access and routing overrides removed;
- recovery backlog reconciled;
- next failover posture tested.

## Production implementation mapping

### Step 1 — Define recovery contract

For each journey document:

- RTO;
- RPO;
- maximum tolerable disruption;
- degraded mode;
- owner and approver;
- dependency tier.

### Step 2 — Continuously evaluate destination

Do not wait for disaster to discover:

- insufficient quota;
- missing certificate;
- stale secret;
- broken artifact path;
- schema mismatch;
- unused dependency;
- failed observability export.

### Step 3 — Establish incident command

Maintain:

- one UTC timeline;
- one decision log;
- current state and next hold point;
- unknowns and risk;
- customer and leadership communication;
- exact promotion and routing actions.

### Step 4 — Fence and promote

- stop new writes in old region where possible;
- prove old authority cannot continue;
- issue new epoch or term;
- verify stale writes are rejected;
- promote data authority;
- run business synthetic.

### Step 5 — Shift traffic progressively

- start bounded;
- monitor SLO burn, cohorts, data, and dependencies;
- expand or abort;
- account for DNS cache and long-lived connections.

### Step 6 — Reconcile and re-protect

- quantify potential lost or duplicate operations;
- replay idempotently;
- reconcile source systems;
- restore backups, redundancy, security, observability, and normal automation.

## Common weak answers

### “Use DNS failover”

DNS does not fence writers, validate destination data, or move existing long-lived connections immediately.

### “Promote when the health check fails”

One health check cannot prove capacity, dependencies, identity, data, schema, observability, and authority.

### “Replication means no data loss”

Asynchronous replication has a gap. Synchronous replication still needs corruption recovery and fencing.

### “Shift everything immediately”

This can move all traffic into an under-capacity or inconsistent destination.

### “Traffic moved, so recovery is complete”

Backlog, data reconciliation, hidden cohorts, reduced redundancy, and emergency controls may remain.

### “Change weights back for failback”

The original region must be rebuilt, resynchronized, tested, promoted, and reintroduced safely.

## Interview answer drill

> I define RTO and RPO per user journey, then treat the secondary as eligible only when application, capacity, dependencies, identity, observability, schema, data lag, and business synthetics are within policy. Before promoting, I fence the old writer and issue a newer epoch that the resource enforces. Traffic moves through a progressive state machine with SLO, cohort, dependency, and data abort conditions. Failback is separate: rebuild, resynchronize, issue a new authority epoch, canary traffic back, and close recovery debt.

## Related material

- [`core/reliability/disaster-recovery/multi-region-failover.md`](../../../core/reliability/disaster-recovery/multi-region-failover.md)
- [`core/reliability/slo/error-budgets.md`](../../../core/reliability/slo/error-budgets.md)
- [`core/incident-response/postmortems.md`](../../../core/incident-response/postmortems.md)
- [`core/distributed-systems/03-replication-quorum-consensus.md`](../../../core/distributed-systems/03-replication-quorum-consensus.md)
- [`core/distributed-systems/05-time-leases-and-fencing.md`](../../../core/distributed-systems/05-time-leases-and-fencing.md)
