# Executable Distributed Systems Labs

This directory turns the canonical distributed-systems chapters into runnable failure experiments.

The labs intentionally use small, inspectable programs rather than hiding behavior behind large frameworks. Each exercise maps a production invariant to a failure mode, an experiment, evidence, and a repair.

## Lab map

1. [Retry amplification and jitter](01-retry-amplification/README.md)
   - Compare logical requests with physical attempts.
   - Observe layered retries, synchronized retry waves, jitter, and retry budgets.
   - Practice reasoning about deadlines and overload.

2. [Transactional outbox and idempotent inbox](02-transactional-outbox/README.md)
   - Create business state and an outbox event atomically.
   - Simulate a relay crash after publish but before acknowledgement.
   - Prove that the consumer remains correct under duplicate delivery.

3. [Leases and fencing tokens](03-fencing-tokens/README.md)
   - Demonstrate why a lease or distributed lock alone cannot stop a paused former owner.
   - Issue monotonically increasing fencing tokens.
   - Make the protected resource reject stale writers.

4. [Cache stale-fill races and stampedes](04-cache-races/README.md)
   - Reproduce a delayed reader repopulating stale data after invalidation.
   - Reject stale fills with a version fence.
   - Compare independent misses with single-flight request coalescing.

## Prerequisites

- Python 3.11 or newer
- No third-party Python packages
- A shell capable of running the commands shown in each lab

## Automated verification

Run all invariant tests from the repository root:

```bash
python3 -m unittest discover \
  -s labs/distributed-systems/tests \
  -p "test_*.py" \
  -v
```

The GitHub Actions workflow also compiles all lab programs, runs the test suite, and performs command-line smoke scenarios.

## Working method

For every lab:

1. State the safety invariant.
2. Run the healthy path.
3. Inject one specific failure.
4. Record the observable evidence.
5. Explain why the naïve design fails.
6. Apply the safer pattern.
7. Repeat the experiment and prove the invariant holds.

## Interview conversion

After completing a lab, practice explaining it in this order:

1. **Invariant** — what must never happen.
2. **Failure** — timeout, duplicate, pause, partition, race, or overload.
3. **Unsafe implementation** — why the obvious design fails.
4. **Control** — idempotency, fencing, versioning, bounded retries, transactional state, or reconciliation.
5. **Proof** — metrics, database constraints, audit records, versions, or rejected operations.
6. **Trade-off** — latency, availability, complexity, storage, or operational cost.

The goal is not only to run the code. The goal is to be able to defend the design at Staff or Principal level.
