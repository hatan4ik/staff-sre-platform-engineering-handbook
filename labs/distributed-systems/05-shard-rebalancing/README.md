# Lab 5 — Shard Maps, Online Rebalancing, and Ownership Epochs

This lab demonstrates why moving a shard is a protocol rather than a database copy.

A correct migration must preserve two invariants:

1. Every acknowledged write survives the move.
2. After cutover, a stale router or former owner cannot continue mutating the shard.

The simulator uses only Python's standard library and models:

- hash partitioning into virtual shards
- range partitioning examples
- a centrally versioned shard map
- cached router snapshots
- copy, catch-up, cutover, and cleanup phases
- monotonically increasing ownership epochs
- stale-router rejection at the storage boundary
- hot-shard and dominant-tenant detection

## Run the unsafe migration

From the repository root:

```bash
python3 labs/distributed-systems/05-shard-rebalancing/shard_rebalance_demo.py \
  unsafe \
  --json
```

The unsafe sequence is:

```text
source owns shard at epoch 7
  -> copy snapshot to target
  -> accept a newer write on source
  -> cut over without catch-up
  -> stale router writes to former owner
```

Expected evidence:

- the target becomes authoritative with `value-v1`
- `value-v2`, acknowledged during the copy, is absent from the target
- the stale post-cutover write is accepted by the former owner
- source and target diverge

This is both a lost-write failure and a split-ownership failure.

## Run the safe migration

```bash
python3 labs/distributed-systems/05-shard-rebalancing/shard_rebalance_demo.py \
  safe \
  --json
```

The safe sequence is:

```text
prepare
  -> copy snapshot and record a sequence watermark
  -> replay writes newer than the watermark
  -> atomically move ownership and increment the epoch
  -> reject old owner/epoch combinations
  -> clean up the source only after cutover
```

Expected evidence:

- the target contains `value-v2`
- the epoch advances from 7 to 8
- the router holding epoch 7 is rejected
- the former owner's copy is removed only after a safe cutover

## Compare both paths

```bash
python3 labs/distributed-systems/05-shard-rebalancing/shard_rebalance_demo.py \
  compare \
  --json
```

The comparison is intentionally sharp:

| Property | Unsafe | Safe |
|---|---|---|
| Catch-up before cutover | No | Yes |
| Ownership epoch advanced | Yes | Yes |
| Storage enforces epoch | No | Yes |
| Stale router accepted | Yes | No |
| Latest pre-cutover write preserved | No | Yes |
| Source cleanup | Unsafe/omitted | After verified cutover |

An epoch in the metadata service is not enough. The protected storage node must validate it. Otherwise, the old owner can still accept writes even though the control plane believes ownership moved.

## Inspect partition skew

```bash
python3 labs/distributed-systems/05-shard-rebalancing/shard_rebalance_demo.py \
  distribution \
  --json
```

The simulator creates a generally distributed workload and then repeats one hot key 500 times. It reports:

- request count per virtual shard
- average requests per shard
- hottest shard and its count
- shards exceeding the configured multiple of the average
- tenants contributing a dominant fraction of traffic
- sample range-partition results

## Design lessons

### Virtual shards are an operational tool

Mapping many virtual shards to fewer physical nodes makes movement smaller and more controllable than remapping an entire node-sized hash range. It does not remove skew. A single hot key still maps to one virtual shard unless the application can split or replicate that key's workload.

### Copy is not synchronization

A copy establishes a baseline. Writes continue while the copy runs, so the migration needs a durable change stream, log position, snapshot sequence, or another catch-up mechanism.

### Cutover must be an ownership transaction

A safe cutover changes the authoritative owner and increments the ownership epoch as one serialized metadata operation. Routers refresh asynchronously, so old routes must be expected rather than treated as exceptional.

### Cleanup is the last phase

Deleting the source before the target is caught up and authoritative turns a reversible migration into permanent data loss. Cleanup should require evidence that:

- the target reached the required sequence
- ownership changed successfully
- stale writes are rejected
- rollback policy is understood

## Production telemetry

A real implementation should expose:

- shard owner and epoch
- migration phase and duration
- snapshot watermark
- replay lag in records and seconds
- writes rejected for stale epochs
- routers using old map versions
- per-shard QPS, storage, CPU, and tail latency
- per-tenant contribution to each shard
- copy and catch-up throughput
- cleanup status and retained rollback copies

## Staff/Principal interview answer

A strong answer should say:

> I would not move a shard by copying data and changing DNS. I would treat movement as a state machine: prepare the target, take a consistent snapshot with a log watermark, replay the delta, atomically change the owner while increasing an epoch, require every storage write to carry that epoch, reject stale routers and former owners, verify invariants, and only then clean up. I would also cap concurrent moves and monitor replay lag because an aggressive rebalancer can overload the exact nodes it is trying to repair.

## Adversarial follow-ups

Be ready to answer:

1. What happens if the source fails during the snapshot?
2. What happens if writes continue faster than catch-up can replay them?
3. How do you roll back after the owner epoch advances?
4. Can reads move before writes?
5. How do cross-shard transactions behave during movement?
6. How do you stop two controllers from moving the same shard?
7. How do you split a single hot key that cannot be rehashed?
8. How many shard moves may run concurrently without violating recovery capacity?

Related canonical chapter:

- [`core/distributed-systems/05-partitioning-sharding-rebalancing.md`](../../../core/distributed-systems/05-partitioning-sharding-rebalancing.md)
