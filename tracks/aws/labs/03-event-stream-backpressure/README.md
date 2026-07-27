# Lab 03 — Event-Stream Partitioning, Backpressure, Retry, and Idempotency

## Objective

Run a local simulator that models the engineering semantics behind:

- Kinesis partitioned ingestion;
- SQS-style bounded work queues;
- Lambda or EKS consumer concurrency;
- hot partition keys;
- producer and consumer backpressure;
- transient retries with jitter;
- poison events and a dead-letter queue;
- duplicate delivery;
- exactly-once business effect through an idempotency inbox;
- end-to-end freshness and queue-depth signals.

The simulator does **not** emulate AWS APIs. It is intentionally small so the candidate can see the control loops and failure behavior without provisioning billable resources.

## Prerequisites

- Python 3.11 or newer
- no third-party Python packages

## Files

```text
pipeline.py          simulator and command-line interface
test_pipeline.py     unit and async integration tests
GNUmakefile          common scenarios
runtime/             generated SQLite idempotency state
```

## Quick start

```bash
make test
make baseline
```

The simulator prints one operational snapshot per second and a final JSON report.

Final fields include:

- produced/admitted/routed events;
- producer backpressure count;
- processed and duplicate events;
- transient and permanent failures;
- retries and DLQ count;
- p50/p95/p99 end-to-end latency;
- per-shard admitted-event count;
- SQLite inbox rows.

---

## Architecture being modeled

```text
producer
  |
  +--> stable hash(partition key)
          |
          +--> bounded shard queue 0
          +--> bounded shard queue 1
          +--> ...
          |
       routers
          |
       bounded work queue
          |
       worker pool
          |
          +--> transient retry with exponential backoff and jitter
          +--> permanent poison event -> DLQ
          +--> SQLite inbox -> idempotent durable side effect
```

Production mapping:

| Simulator | AWS architecture |
|---|---|
| per-shard bounded queue | Kinesis shard and finite write/read capacity |
| stable hash | partition-key hash |
| router | stream consumer transforming/routing work |
| bounded work queue | SQS queue or internal bounded consumer queue |
| worker pool | Lambda concurrency or EKS consumer replicas |
| SQLite inbox | DynamoDB/Aurora conditional idempotency record |
| DLQ queue | SQS DLQ or quarantine stream |
| latency from produce to process | event freshness SLI |

---

## Scenario 1 — Healthy baseline

```bash
make baseline
```

Equivalent command:

```bash
python3 pipeline.py \
  --rate 500 \
  --duration 10 \
  --shards 8 \
  --workers 16 \
  --downstream-ms 2
```

Questions:

1. Is processed rate close to admitted rate?
2. Are shard counts reasonably distributed?
3. Does queue depth return to zero?
4. What is p99 freshness?
5. How many duplicate deliveries were safely suppressed?

---

## Scenario 2 — Hot partition key

```bash
make hot-key
```

The producer sends 60% of events with the same partition key.

Observe:

- one shard receives a disproportionate count;
- total worker count does not change the serial assignment of one key;
- queue pressure can concentrate even when total nominal capacity appears sufficient.

### Interview lesson

Adding shards cannot parallelize one business key if strict per-key ordering is required.

Options:

- rate-limit the producer or tenant;
- shard the key only when ordering semantics allow it;
- redesign the invariant;
- isolate a heavy tenant;
- accept and capacity-plan the serial ceiling.

Do not add a random suffix if the business requires strict per-entity ordering.

---

## Scenario 3 — Downstream slowdown and backpressure

```bash
make slow-downstream
```

The downstream operation takes longer while producer rate remains high.

Observe:

- bounded queues fill;
- the producer blocks rather than allocating unlimited memory;
- p95/p99 freshness increases before events are lost;
- additional workers can help only until the downstream capacity limit is reached.

### Interview lesson

Queue age and incoming/processed rate are better overload signals than CPU alone.

In production, safe actions may include:

- scale consumers from iterator age or queue age;
- reduce concurrency to protect a database;
- pause optional consumers;
- extend retention;
- shed low-priority input;
- degrade expensive enrichment;
- stop retry amplification.

---

## Scenario 4 — Duplicate delivery

```bash
make duplicates
```

Every logical event is submitted twice.

The SQLite inbox has a primary key on `event_id`, so only the first copy creates the durable effect.

Verify:

```text
processed == inbox_rows
duplicates > 0
```

### Interview lesson

At-least-once delivery is normal. Exactly-once business effect requires an idempotency boundary such as:

```text
begin transaction
  insert event_id if absent
  apply business state change
commit
```

A broker feature alone cannot guarantee end-to-end exactly-once behavior across external side effects.

---

## Scenario 5 — Transient failure and bounded retry

```bash
make transient-failures
```

Observe:

- transient failure count;
- retry count;
- jittered delay;
- eventual success or DLQ after maximum attempts;
- increasing freshness during repeated failures.

### Interview lesson

Define retry ownership. Producer, stream consumer, queue, and external client must not each perform large independent retry loops.

Every retry policy needs:

- retryable error classification;
- maximum attempts or age;
- exponential backoff;
- jitter;
- idempotency;
- a final quarantine or operator path.

---

## Scenario 6 — Permanent poison event

```bash
make poison
```

The simulator periodically assigns partition key `poison`, which always fails and goes directly to the DLQ.

Observe:

- permanent failure count;
- DLQ count and depth;
- healthy events continue processing.

### Interview lesson

A poison event must not retry forever and stop an entire shard.

However, in a strictly ordered business stream, skipping one event may invalidate later events for that key. The production design may need to quarantine or pause the affected key while other keys continue.

A DLQ requires:

- owner;
- alert;
- original payload and metadata;
- repair tooling;
- controlled redrive;
- retention long enough for investigation.

---

## Scenario 7 — Combined pressure

```bash
make stress
```

This combines:

- higher rate;
- hot-key skew;
- duplicates;
- transient failures;
- slower downstream processing;
- poison events.

Before running it, predict:

- which queue fills first;
- which metric changes first;
- whether increasing workers helps;
- how many events reach the DLQ;
- how p99 freshness changes.

---

## Reset durable idempotency state

```bash
make reset
```

The SQLite inbox persists processed event IDs. A new scenario should normally use a fresh state database unless the purpose is to test replay and deduplication.

---

## Replay exercise

1. Run a baseline scenario and preserve `runtime/inbox.sqlite3`.
2. Re-run the same event IDs by modifying the producer or using a captured test fixture.
3. Confirm the inbox rejects duplicate side effects.
4. Explain how the same logic would use DynamoDB conditional writes or an Aurora unique constraint.
5. Add a new consumer version and prove replay does not create duplicate external operations.

The simulator generates random UUIDs by default, so a complete replay exercise requires adding an input-file producer. That is an intentional extension task.

---

## Extension tasks

### Easy

- export operational snapshots to JSON Lines;
- add a queue-age metric;
- add per-partition queue depth;
- add a priority event type;
- add graceful shutdown and checkpoint output.

### Intermediate

- add an input-file replay mode;
- add a circuit breaker for the downstream operation;
- add separate queues and worker pools by event type;
- add tenant rate limits;
- add a repair and DLQ redrive command;
- add a schema registry with backward-compatibility checks.

### Advanced

- replace local queues with LocalStack Kinesis and SQS;
- write a Lambda-style consumer with partial batch failure;
- write an EKS worker and scale it from queue age;
- persist the inbox in DynamoDB with conditional writes;
- archive events to S3 and build a controlled replay job;
- add OpenTelemetry traces and Prometheus metrics;
- simulate regional failover while preserving event IDs.

---

## Metrics-to-action table

| Signal | Likely interpretation | Safe first action |
|---|---|---|
| one shard dominates | partition-key skew | identify key and ordering requirement |
| all shard queues rise | broad ingest exceeds routing | scale/partition or reduce admission |
| work queue rises | worker/downstream capacity deficit | inspect processing rate and dependency |
| retries rise before queue | transient dependency failure | bound retry and protect dependency |
| DLQ rises | permanent data/code failure | quarantine and alert owner |
| p99 rises, depth still low | per-event processing latency | trace/profile the worker/dependency |
| processed rises but inbox rows do not | duplicate delivery | verify idempotency is intentional |

## Interview questions

1. Why does more worker concurrency not fix one hot ordered key?
2. When should Kinesis enhanced fan-out be used?
3. Why place SQS after Kinesis?
4. When does Lambda scaling make an outage worse?
5. When may a consumer advance past a poison event?
6. How do you replay six hours without overwhelming the database?
7. What is exactly-once business effect?
8. How should the design change across Regions?
9. Which event belongs on EventBridge instead of the raw Kinesis stream?
10. What is the first user-facing SLI for an asynchronous system?

## Completion standard

The lab is complete when you can:

- explain the per-key ordering ceiling;
- induce and identify backpressure;
- prove duplicate suppression;
- show bounded retry and DLQ behavior;
- map each simulator component to Kinesis, SQS, Lambda/EKS, and a durable inbox;
- describe a safe replay;
- explain why one universal event pipeline is an anti-pattern.