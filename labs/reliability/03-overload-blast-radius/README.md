# Overload, Retry Budget, Blast Radius, and Recovery Lab

This dependency-free Python lab turns the canonical reliability chapter into executable invariants.

## What it demonstrates

- independent layered retries amplify one original request into many attempts;
- a retry budget bounds extra load;
- critical work is admitted before optional work;
- reserved capacity prevents optional work from consuming every slot;
- per-tenant limits prevent one tenant from monopolizing the service;
- regional or cell failover is blocked when destination headroom is unsafe;
- backlog recovery expires obsolete work and replays the remainder in bounded batches.

## Run

```bash
cd labs/reliability/03-overload-blast-radius
python3 overload_lab.py
python3 overload_lab.py --json
python3 -m unittest -v test_overload_lab.py
```

Expected human output ends with every invariant marked `PASS`.

## Interview exercise

Explain:

1. why three layers with two retries each can create 27 attempts;
2. why concurrency limits protect a slowed dependency better than request-rate limits alone;
3. why failover needs destination capacity plus a safety margin;
4. why stale backlog should expire instead of being replayed blindly;
5. how per-tenant and priority admission reduce global blast radius.

Then modify the scenario so the destination cell has enough headroom and verify the failover decision becomes safe.

## Production translation

The lab is deliberately small. In a real platform, connect the same invariants to:

- gateway and service concurrency limits;
- tenant and endpoint quotas;
- retry policies and service-client libraries;
- queue age and expiration;
- regional routing controls;
- error-budget and protected-cohort policies;
- game-day stop conditions.

The lab proves decision logic, not cloud-provider or cluster behavior.
