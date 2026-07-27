# Lab: Plan a Bounded Multi-Cluster Rollout

This lab converts fleet inventory and release policy into deterministic rollout batches. It rejects clusters whose lifecycle, version, conformance, maintenance, or compatibility state makes the rollout unsafe.

## Learning objectives

- distinguish cluster inventory from deployment intent;
- use rollout rings and bounded concurrency;
- enforce compatibility and conformance prerequisites;
- separate eligible, deferred, and blocked clusters;
- prove that a global rollout can pause before broad production impact.

## Files

- `clusters.json` — representative fleet inventory.
- `release-policy.json` — candidate versions, ring order, batch size, and gates.
- `plan_rollout.py` — standard-library planner.

## Run

```bash
python3 plan_rollout.py clusters.json release-policy.json \
  --now 2026-07-27T12:00:00Z
```

Expected result:

```text
PLANNED: rollout contains bounded batches
```

The planner deliberately defers a cluster outside its maintenance window and blocks a cluster with stale conformance evidence.

## Exercises

1. Increase `maximumBatchSize` to the full production fleet and explain the blast radius.
2. Remove the production canary ring.
3. Change the candidate baseline to one incompatible with a cluster class.
4. Mark a cluster `Degraded` or `Quarantined`.
5. Set every cluster to the same failure domain and discuss correlated risk.
6. Add a disconnected edge cluster and define its evidence and rollback contract.
7. Decide whether a blocked special fleet should stop all standard-fleet promotion.

## Staff-level discussion

A real rollout controller must consume live authoritative status and stop on SLO regression. This lab plans eligibility only; it does not claim that a successful controller reconciliation proves workload safety.
