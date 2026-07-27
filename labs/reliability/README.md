# Executable Reliability Engineering Labs

These labs turn SLO, error-budget, overload, disaster-recovery, and chaos concepts into deterministic exercises.

## Current labs

1. [SLO, error-budget, burn-rate, and protected-cohort analysis](01-error-budget/README.md)
2. [Disaster-recovery failover state machine](02-disaster-recovery-state-machine/README.md)
3. [Overload, retry budget, blast radius, and recovery](03-overload-blast-radius/README.md)

All current labs use Python's standard library and require no cloud account.

## Run examples

```bash
cd labs/reliability/01-error-budget
python3 -m unittest -v

cd ../02-disaster-recovery-state-machine
python3 -m unittest -v

cd ../03-overload-blast-radius
python3 overload_lab.py
python3 -m unittest -v test_overload_lab.py
```

## Method

1. Define the user journey and protected invariants.
2. Model the failure or policy decision explicitly.
3. Include a dangerous case, not only the happy path.
4. Bound retries, queues, failover, and recovery work.
5. Produce machine-readable evidence.
6. Convert results into an operational release, failover, or incident decision.

## Ownership rule

Labs must test reliability invariants rather than only produce charts. Every exercise should include positive cases, dangerous edge cases, and an operational decision.
