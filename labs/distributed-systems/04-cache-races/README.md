# Lab 4 — Cache Stale-Fill Races and Stampedes

## Invariants

This lab protects two separate invariants:

1. A cache must not resurrect an older version after a newer database write commits.
2. A cold or expired key must not turn one cache miss into an uncontrolled burst of origin requests.

## Run all scenarios

```bash
python3 cache_race_demo.py all
```

## Stale-fill race

Run only the race:

```bash
python3 cache_race_demo.py race
```

Unsafe timeline:

```text
reader A misses cache and reads database version 1
reader A pauses before filling cache
writer commits database version 2
writer deletes cache key
reader A resumes and fills cache with version 1
```

Delete-only invalidation has no memory that version 2 exists. The delayed reader can therefore repopulate stale data after the invalidation completed.

The safe scenario advances a version fence when the writer invalidates the key. A later fill carrying version 1 is rejected because the cache knows version 2 is the minimum acceptable version.

## Cache stampede

```bash
python3 cache_race_demo.py stampede --requests 1000
```

The unsafe scenario models 1,000 concurrent requests observing the same miss before any fill completes. All 1,000 requests reach the origin.

The single-flight scenario elects one fill owner while followers wait. One origin request populates the cache and the remaining requests reuse the result.

## JSON evidence

```bash
python3 cache_race_demo.py all --requests 1000 --json > cache-results.json
```

## Production controls for stale fills

Depending on the system, controls include:

- versioned cache values
- compare-and-set fills
- write-through or write-behind protocols with explicit ordering
- invalidation fences or tombstones
- generation numbers embedded in keys
- source-of-truth commit positions
- bounded TTL as a final safety net
- read-your-writes routing for user-visible updates

A TTL limits how long stale state may survive. It does not eliminate the race.

## Production controls for stampedes

- single-flight request coalescing
- stale-while-revalidate
- probabilistic early refresh
- TTL jitter
- bounded refresh concurrency
- negative caching for repeated misses
- per-key admission control
- origin rate limits and overload shedding
- prewarming only when operationally justified

## Signals to monitor

- cache hit ratio by key class, not only globally
- origin requests per logical key request
- fill concurrency by key
- stale-read age and source version
- rejected stale-fill attempts
- hot-key concentration
- cache eviction and expiration reasons
- origin latency during cache degradation

## Interview drill

An interviewer asks:

> We update the database and then delete the cache key. Is that enough?

A Staff-level answer should explain the delayed-reader stale-fill race. The answer should define the consistency requirement, version or generation control, ordering of database commit and cache mutation, behavior during cache failure, stampede protection, and telemetry proving that the cache is not serving resurrected state.
