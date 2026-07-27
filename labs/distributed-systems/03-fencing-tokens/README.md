# Lab 3 — Leases and Fencing Tokens

## Invariant

At most one current owner may mutate the protected resource. A former owner that resumes after a pause must not overwrite the new owner's state.

## Why a lease alone is insufficient

A coordinator may grant worker A a lease. Worker A then pauses because of:

- a long garbage-collection stop
- VM suspension
- CPU starvation
- debugger attachment
- process scheduling delay
- network isolation

The lease expires while A is paused. The coordinator grants a new lease to worker B.

Worker A later resumes. It still has the old credential and may continue writing because the coordinator cannot revoke a token already handed to a paused client.

```text
A gets lease 1
A pauses
lease 1 expires
B gets lease 2
B writes authoritative state
A resumes and writes using stale lease 1
```

If the resource accepts A's write, exclusive ownership has failed.

## Run the comparison

```bash
python3 fencing_demo.py compare
```

The first scenario uses a lease coordinator but an unsafe resource. The stale former owner overwrites the current owner.

The second scenario gives each ownership epoch a monotonically increasing fencing token. The resource remembers the highest accepted token and rejects lower tokens.

## Run scenarios separately

Unsafe lease-only design:

```bash
python3 fencing_demo.py unsafe
```

Resource-enforced fencing:

```bash
python3 fencing_demo.py safe
```

JSON output:

```bash
python3 fencing_demo.py compare --json
```

## Safety mechanism

The coordinator issues tokens:

```text
worker A -> token 1
worker B -> token 2
worker C -> token 3
```

Every protected write carries its token.

The resource enforces:

```text
reject write when token < highest_token_already_accepted
```

The correctness boundary is the resource, not the lock client.

## Examples of enforceable fencing

- Object storage writes using generation or version preconditions
- Database updates with an ownership epoch column
- Job execution with a shard epoch checked by the worker and database
- Message processing with partition generation IDs
- Storage controllers requiring a monotonically increasing primary term
- Kubernetes-style resource versions or compare-and-swap boundaries

## What does not count as fencing

These mechanisms may reduce risk but do not independently prevent a stale writer:

- checking the wall clock before writing
- assuming the old process was killed
- relying only on a TTL key in Redis
- trusting the client to stop after renewal failure
- using a random lock UUID without resource-side ordering
- sending a best-effort cancellation to the former owner

## Production checklist

A safe ownership protocol should define:

- how tokens are generated monotonically
- where the highest token is stored
- which resource enforces token ordering
- what happens during coordinator failover
- whether writes are atomic with the token check
- how ownership epochs appear in logs and traces
- how operators identify stale-write rejection
- how long-running work checks ownership before final commit
- whether external side effects support conditional execution

## Interview drill

An interviewer asks:

> We use a five-second distributed lock, so only one scheduler can run the job. Is that safe?

A Staff-level response should say that the lock limits concurrent ownership only while clients behave and timing assumptions hold. A paused owner may resume after expiration. The design needs a monotonically increasing ownership epoch and resource-enforced fencing. The answer should also cover renewal failure, coordinator quorum, clock assumptions, idempotency, and reconciliation for external side effects.
