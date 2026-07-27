# Question 18 — Processing Millions of Real-Time Events per Second on AWS

## Interview prompt

How would you design a platform capable of processing millions of real-time events per second using Amazon Kinesis, SQS, SNS, EventBridge, Lambda, and Amazon EKS?

## What the interviewer is testing

A strong answer does not connect every named service in a decorative chain. It assigns each service a precise role based on:

- ordering and partition semantics
- fan-out and replay
- latency
- event size and throughput
- backpressure
- delivery guarantees
- consumer isolation
- state and idempotency
- failure recovery
- cost and operational ownership

The design must explain how one poison event, hot partition, retry policy, or slow consumer is prevented from stopping the platform.

---

## 90-second Staff/Principal answer

> I begin by defining event size, peak rate, ordering key, retention, replay, processing latency, number of independent consumers, and acceptable duplicate behavior. For a high-volume ordered log, Kinesis Data Streams is the ingestion backbone. I partition by a well-distributed business key, use batched producer APIs and aggregation, and select on-demand or provisioned capacity from traffic predictability and control requirements. Enhanced fan-out gives latency-sensitive consumers dedicated read throughput.
>
> I do not put every consumer directly on the same processing contract. Lambda handles stateless transformation and moderate-complexity event handlers. EKS consumers handle long-running, high-throughput, custom-runtime, stateful, GPU, or specialized workloads and scale from iterator age and processing rate. SQS creates independent work queues, absorbs bursts, isolates retries, and supports DLQs. SNS provides high-throughput pub/sub fan-out where replay and ordering are not required. EventBridge handles business-event routing, filtering, schema-oriented integration, SaaS/AWS events, and cross-account workflows—not the raw multi-million-event telemetry firehose unless quotas and economics prove it fits.
>
> Every consumer is idempotent, checkpoints only after durable side effects, and uses an outbox or transactional pattern where business state and event publication must agree. I monitor incoming rate, partition skew, write throttling, iterator age, queue age, Lambda concurrency, consumer lag, retry volume, and end-to-end freshness. Backpressure, bounded retries, poison-event quarantine, replay tooling, and load shedding are designed before launch.
>
> I validate the platform with hot-key injection, consumer slowdown, partial batch failure, downstream throttling, shard rebalance, Region isolation, duplicate replay, and a full restore from the retained stream or S3 archive.

---

## 1. Define the workload

Ask or state assumptions:

| Dimension | Example question |
|---|---|
| Peak rate | 1 million, 5 million, or 20 million events/second? |
| Event size | 200 bytes, 5 KB, or hundreds of KB? |
| Burst | Seconds, minutes, or sustained? |
| Ordering | Global, per device, per account, or none? |
| Latency | p99 under 1 second, 10 seconds, or minutes? |
| Consumers | Two, twenty, or hundreds of independent applications? |
| Replay | Minutes, days, or regulatory years? |
| Delivery | At-least-once acceptable? Exactly-once business effect required? |
| State | Stateless transform, aggregation, window, or joins? |
| Geography | One Region, dual ingestion, or global edge? |
| Data | Personal, financial, security, or operational telemetry? |

### Throughput math

Example:

```text
5,000,000 events/s × 1 KB average = about 5 GB/s raw payload
```

Then add:

- protocol overhead
- replication and retention
- multiple consumers
- compression behavior
- peak factor
- failed retries
- observability and archive writes

Event rate without byte rate is incomplete capacity planning.

---

## 2. Service role matrix

| Service | Primary role | Not the default choice for |
|---|---|---|
| Kinesis Data Streams | ordered partitioned stream, multiple consumers, replay | arbitrary global ordering or unlimited hot keys |
| SQS Standard | durable work queue, buffering, independent retries | replayable ordered event log |
| SQS FIFO | ordered/deduplicated message groups | unconstrained maximum-throughput telemetry without careful grouping |
| SNS | push fan-out to queues/endpoints | durable replay and consumer checkpoints |
| EventBridge | business-event routing, filtering, cross-account/SaaS integration | raw high-volume telemetry backbone without validated quotas/cost |
| Lambda | managed event processing and burst scaling | very long, specialized, stateful, or continuously saturated compute where economics/runtime do not fit |
| EKS | custom long-running consumers, specialized compute, stateful stream processors | simple event handlers that do not justify cluster operations |
| S3 | durable archive, batch analytics, replay source | low-latency per-event routing |

Use only the services whose semantics solve a requirement.

---

## 3. Reference architecture

```text
Producers
  |
  +--> regional ingestion API / IoT Core / direct Kinesis producer
              |
              v
       Kinesis Data Streams
       partitioned event log
              |
     +--------+---------+-------------------+
     |                  |                   |
Lambda consumer    EKS stream consumers   archive consumer
transform/filter   enrichment/aggregation  -> Firehose/S3
     |                  |                   |
     +--> EventBridge   +--> SQS work queues
     |    business bus       |
     |                       +--> Lambda workers
     |                       +--> EKS workers
     |
     +--> SNS topics -> isolated SQS subscriptions

Outputs:
DynamoDB / Aurora / OpenSearch / Timestream / S3 / downstream APIs

Control and evidence:
Glue Schema Registry or owned schema catalog
CloudWatch / OpenTelemetry / AMP / Grafana
CloudTrail / KMS / IAM / data quality and replay tooling
```

Do not force the raw stream through EventBridge or SNS before Kinesis when partitioned replay is the primary requirement.

---

## 4. Producer architecture

### Direct producer versus ingestion service

Use direct Kinesis producers when:

- trusted workloads have AWS identity
- client libraries support batching, retry, and partition strategy
- exposing stream identity is acceptable

Use an ingestion API when:

- internet/mobile clients cannot receive AWS stream credentials
- validation, authentication, quota, or transformation is required
- multi-tenant isolation needs a policy boundary

### Batching

Use `PutRecords` or an approved producer library to batch records.

Benefits:

- fewer API calls
- higher throughput
- better network efficiency

Handle partial success. A batch can contain both successful and failed records. Retry only failed entries with jitter and idempotent event IDs.

### Aggregation

Producer aggregation can package multiple logical events into one Kinesis record and improve efficiency. Consumers must deaggregate correctly.

### Event identity

Every event includes:

```text
event_id
event_type
schema_version
producer
produced_at
ingested_at
partition_key
correlation/trace context
business entity/version where relevant
```

Do not use ingestion timestamp as the only event identity.

### Admission control

Reject or quarantine:

- oversized events
- invalid schemas
- unauthorized tenant
- impossible timestamp skew
- abusive producer rate
- malformed partition key

Protect the stream from becoming a garbage archive.

---

## 5. Partition-key design

Kinesis ordering exists within a shard and is driven by the partition-key hash.

### Good partition key

- high cardinality
- evenly distributed load
- aligns with required ordering
- stable for related events

Examples:

```text
device ID when per-device ordering is required
account ID when per-account state transitions must be ordered
composite tenant#entity when tenant skew is controlled
```

### Hot-key problem

A single celebrity account, customer, device gateway, or constant key can overload one partition regardless of total stream capacity.

### Key sharding

If strict per-entity ordering is not required, add a controlled suffix:

```text
customer-123#0 ... customer-123#31
```

Downstream consumers merge or aggregate across suffixes.

If ordering is required, one logical key has a finite serial throughput ceiling. Redesign the business invariant rather than pretending more shards create parallel ordering for one key.

### Skew detection

Monitor:

- records and bytes by partition-key sample
- shard-level throughput
- throttles
- producer retry
- consumer lag by shard

Use sampled logs or Contributor Insights rather than one metric per key.

---

## 6. Kinesis capacity mode

Current Kinesis Data Streams modes include:

- On-demand Standard
- On-demand Advantage where available/configured
- Provisioned

### On-demand

Use when:

- traffic is variable or uncertain
- operational simplicity matters
- automatic shard management fits

A new or cold on-demand stream still requires load and burst validation. “On-demand” does not mean arbitrary instantaneous traffic without warm-throughput considerations, account quotas, or producer behavior.

### Provisioned

Use when:

- traffic is predictable
- explicit shard planning and economics are favorable
- the team wants deterministic control
- proactive scaling is integrated with forecasts

### Capacity math

Plan from:

- records/second
- bytes/second
- number and type of consumers
- enhanced fan-out
- peak and skew
- resharding time
- Region quotas

Load test the actual event-size distribution and keys.

---

## 7. Kinesis consumer models

### Shared-throughput consumers

Consumers poll shards and share read throughput.

Suitable for:

- cost-sensitive consumers
- fewer readers
- latency that tolerates polling and shared capacity

### Enhanced fan-out

Enhanced fan-out gives a registered consumer dedicated read throughput per shard and pushes records through `SubscribeToShard`.

Use for:

- low-latency independent consumers
- many readers that should not contend
- critical processing paths

Consumer registration quotas and cost still matter.

### Checkpointing

Checkpoint only after the consumer has safely completed or durably recorded the side effect represented by the batch.

If checkpoint occurs first and the process crashes, events are lost from that consumer's perspective.

If side effect occurs first and checkpoint fails, the event is replayed. Therefore the side effect must be idempotent.

---

## 8. Lambda consumers

Lambda event-source mappings read batches from Kinesis shards.

### Strong fits

- stateless transformation
- event validation and routing
- moderate per-record work
- managed scaling
- independent small consumers

### Concurrency model

Concurrency is related to shards, parallelization factor, batches, and execution duration.

Monitor:

- iterator age
- concurrent executions
- duration
- throttles
- errors
- batch size and processing rate

### Partial batch failure

Use partial batch response where supported and appropriate so a failure does not replay already successful records unnecessarily.

### Bisect and retry

For poison events:

- bisect failing batches where configured
- cap retry age/attempts
- send failure metadata to a destination or quarantine path
- preserve original event for repair/replay

Do not retry one permanent schema error forever while shard progress stops.

### Downstream protection

Set reserved or maximum concurrency and downstream rate control. Lambda can scale faster than a database or external API.

---

## 9. EKS consumers

Use EKS for:

- long-running stream processors
- custom runtimes or native libraries
- stateful windowing or joins
- GPUs or specialized instance types
- high sustained utilization
- custom checkpoint and partition assignment
- complex backpressure

### Consumer architecture

Options:

- Kinesis Client Library workers with lease coordination
- custom enhanced-fan-out consumers
- stream-processing frameworks validated for Kinesis

### Scaling signal

Scale from:

- iterator age
- records behind latest
- incoming versus processed rate
- active shard count
- per-pod processing throughput

CPU alone can miss backlog growth.

### Rebalance behavior

When scaling workers:

- shard leases move
- caches warm
- state restores
- duplicate processing can occur

Avoid rapid HPA oscillation. Use stabilization and observe rebalance duration.

### Node capacity

Karpenter or Cluster Autoscaler adds nodes, but end-to-end capacity includes:

```text
pending pod -> node launch -> join -> image pull -> consumer lease -> catch-up
```

Maintain warm capacity for strict freshness SLOs.

---

## 10. SQS work isolation

After stream-level parsing or routing, place independent work on SQS queues.

Benefits:

- per-consumer backlog
- visibility timeout
- independent scaling
- retry and DLQ
- downstream protection
- priority separation through different queues

### Visibility timeout

Set longer than normal processing plus retry margin, and extend for known long tasks.

If too short, duplicate concurrent execution increases.

### DLQ

A DLQ is not a disposal bin.

Define:

- alarm on first or thresholded arrival
- ownership
- payload inspection controls
- repair tool
- redrive policy
- retention longer than source investigation window

### Queue age

Age of oldest message is often a better user-impact signal than queue depth alone.

### FIFO

Use FIFO only when ordering and deduplication requirements justify its throughput and message-group design.

One message group serializes processing. Spread independent entities across groups.

---

## 11. SNS fan-out

Use SNS for push fan-out to:

- SQS queues
- Lambda
- HTTP/S endpoints
- mobile push

Strong pattern:

```text
SNS topic
  +--> SQS queue for consumer A
  +--> SQS queue for consumer B
  +--> SQS queue for consumer C
```

Each consumer gets independent buffering and retry.

Use subscription filter policies to reduce irrelevant delivery.

SNS is not a replayable ordered log. Preserve the source event in Kinesis or S3 if replay matters.

---

## 12. EventBridge role

Use EventBridge for:

- domain and business events
- content-based routing
- cross-account event buses
- SaaS and AWS service integration
- archive/replay where configured
- scheduler and workflow triggers
- schema discovery or registry workflows where appropriate

### Do not misuse it as the raw telemetry firehose

At millions of events per second, validate:

- service quotas
- event size
- routing-rule count
- target throughput
- cost
- retry and DLQ behavior

A common architecture is:

```text
raw telemetry -> Kinesis
meaningful derived business event -> EventBridge
```

This keeps business integration separate from raw ingestion mechanics.

### Cross-account buses

Use resource policies and Organizations boundaries. Prevent one producer account from flooding every consumer account.

---

## 13. Schema governance

Use AWS Glue Schema Registry or an owned schema registry/catalog where it fits.

Define compatibility:

- backward
- forward
- full
- none for deliberately versioned new event type

### Envelope versus payload

Stable envelope:

```json
{
  "eventId": "...",
  "type": "OrderAccepted",
  "schemaVersion": 3,
  "producer": "orders",
  "occurredAt": "...",
  "traceparent": "...",
  "data": {}
}
```

### Evolution

- add optional fields with defaults
- do not silently change meaning or units
- preserve unknown fields where clients need forwarding
- version breaking changes
- test old and new consumers

### Invalid event

Quarantine with reason and producer attribution. Do not block an entire shard indefinitely.

---

## 14. Delivery guarantees and idempotency

Assume at-least-once delivery through most event paths.

Duplicates arise from:

- producer retries after unknown result
- consumer crash after side effect before checkpoint
- visibility timeout
- replay
- regional replication
- manual redrive

### Idempotent consumer

Use:

- event ID deduplication record
- conditional write
- unique business constraint
- compare-and-set entity version
- idempotent external API key

### Inbox pattern

```text
begin transaction
  insert event_id into inbox if absent
  apply business change
commit
```

If insert already exists, return prior success.

### Outbox pattern

```text
business state update + outbox event in one transaction
publisher emits outbox records
consumer idempotently processes
```

This prevents committed state without its event.

### Exactly-once language

Do not claim end-to-end exactly-once transport. Describe exactly-once **business effect** and its storage/invariant boundary.

---

## 15. Backpressure and overload

### Detect

- Kinesis iterator age
- SQS oldest-message age
- incoming/processed rate ratio
- consumer CPU and saturation
- downstream throttling
- retry rate
- DLQ growth

### Respond

1. scale the correct consumer
2. protect downstream dependencies with concurrency limits
3. pause noncritical consumers
4. degrade enrichment or optional work
5. reject low-priority producers if contract permits
6. extend retention before backlog exceeds replay window

### Avoid retry amplification

Every layer should not retry independently.

Define retry ownership:

```text
producer retries ingestion
stream consumer retries transient processing
queue handles task retry
external client call has its own small bounded retry
```

Use deadlines and retry budgets.

---

## 16. Poison events

A poison event repeatedly fails because of:

- invalid schema
- unsupported version
- application bug
- impossible state
- downstream permanent rejection

Handling:

```text
classify transient vs permanent
  -> bounded retry
  -> quarantine original event and metadata
  -> advance checkpoint when policy permits
  -> alert owner
  -> repair processor or data
  -> replay through controlled path
```

Preserve ordering semantics. Skipping one event in an ordered entity stream can make later events invalid. The repair workflow may need to pause only that key or partition.

---

## 17. State and stream processing

For windows, joins, and aggregates, decide where state lives:

- embedded processor state with checkpoint to durable storage
- DynamoDB
- ElastiCache
- managed analytics/stream-processing service not named in the prompt where justified

### State recovery

Define:

- checkpoint interval
- replay start
- duplicate effect
- state schema version
- resharding behavior
- failover

### Event time versus processing time

Use event time for business windows where late events matter.

Handle:

- late arrival
- watermarks
- clock skew
- corrections
- retractions

Do not assume producer clocks are trustworthy.

---

## 18. Archive and replay

### Durable archive

Write immutable events to S3 through Firehose or an owned archival consumer.

Partition by bounded fields such as:

```text
event_date/hour/type/region
```

Avoid millions of tiny objects through buffering and compaction.

### Replay service

A controlled replay specifies:

- source range
- event types
- target environment/consumer
- rate limit
- transformation version
- idempotency mode
- dry-run or validation
- operator and approval

Replays should not publish blindly into every production consumer.

### Retention

Kinesis retention covers operational replay. S3 covers long-term recovery and analytics.

Set stream retention long enough to survive the maximum expected consumer outage plus investigation and restore time.

---

## 19. Multi-Region design

### Regional ingestion

Producers write to the nearest or assigned Region.

Options:

- process locally and replicate derived events
- dual publish with idempotency
- archive regionally and replicate S3
- route producer to secondary after failover

### Ordering

Global active-active ingestion cannot provide simple global ordering without a global sequencer and its availability trade-off.

Prefer:

- per-entity home Region
- per-key ordering
- causal/version semantics
- conflict resolution

### Regional failover

Before routing producers:

- destination stream capacity is warm
- schemas and IAM exist
- consumers are deployed
- checkpoint/replay strategy is selected
- duplicate region events are handled

### Event identity

Keep the same event ID across failover retries so consumers deduplicate.

---

## 20. Security

### Identity

- producer-specific IAM roles
- consumer-specific read roles
- EKS Pod Identity or IRSA
- OIDC for CI
- no shared access keys

### Encryption

- KMS encryption for streams, queues, topics, buses, and S3 where required
- TLS
- key policy and grant readiness
- regional recovery access

### Data minimization

Do not put secrets or unnecessary personal data into broad event buses.

Use tokenization or references for sensitive payloads where possible.

### Cross-account

- resource policies
- Organizations conditions
- explicit source accounts
- event-bus and topic policy review
- consumer isolation

### Audit

Record:

- stream and policy changes
- replay requests
- DLQ redrive
- schema changes
- producer identity
- KMS and IAM changes

---

## 21. Observability and SLOs

### Ingestion

- accepted and rejected rate
- bytes/second
- partial batch failures
- write throttling
- producer retry
- partition-key skew

### Kinesis

- shard-level capacity
- iterator age by consumer
- read throttling
- enhanced fan-out health
- resharding

### SQS

- visible/in-flight messages
- oldest-message age
- receive/delete rate
- visibility timeout
- DLQ arrivals

### Lambda

- concurrency
- throttles
- duration
- errors
- event age
- partial batch failures

### EKS

- processed rate
- consumer lag
- rebalance/lease churn
- HPA desired/available
- pending pods
- node capacity realization

### End-to-end

Use timestamps to measure:

```text
produced -> ingested -> processed -> durable side effect
```

Example SLO:

```text
99.9% of valid priority events produce their durable business side effect
within 5 seconds over a rolling 30-day window.
```

Page on freshness and business failure, not merely one shard's routine utilization.

---

## 22. Capacity testing

Test:

- realistic event-size distribution
- realistic partition keys and skew
- peak plus retry traffic
- producer partial failures
- multiple enhanced fan-out consumers
- Lambda concurrency and downstream limits
- EKS rebalance and scaling
- queue accumulation and drainage
- archive throughput
- KMS and API quotas

Do not use evenly random synthetic keys if production has tenant or device skew.

---

## 23. Cost model

Major drivers:

- Kinesis ingest/read mode and retention
- enhanced fan-out consumers
- Lambda invocations and duration
- EKS baseline and burst capacity
- SQS/SNS/EventBridge requests
- archive storage and queries
- cross-Region transfer
- telemetry cardinality

Optimize through:

- batching and aggregation
- correct service assignment
- filtering before expensive consumers
- archive compaction
- autoscaling from lag
- Graviton where validated
- retention tiers

Do not route every raw event through three buses simply because all services were named in the question.

---

## 24. Failure scenarios

### Hot partition

- identify key distribution
- rate-limit abusive producer
- apply key sharding only if ordering permits
- increase total capacity where broad load also requires it
- redesign single-key invariant if serial ceiling is fundamental

### Consumer down for hours

- extend or verify retention
- restore checkpoint
- add safe catch-up capacity
- protect downstream from burst
- monitor iterator age until zero

### Poison event blocks shard

- bounded retry and batch isolation
- quarantine
- preserve ordered-entity semantics
- advance only through approved policy

### Downstream database throttles

- reduce consumer concurrency
- buffer in SQS or retain in Kinesis
- stop retry amplification
- shed optional enrichment

### Lambda reaches account concurrency

- reserved concurrency per critical consumer
- isolate noncritical functions
- use EKS or queue buffering for sustained work
- request quota before launch

### Region unavailable

- route producers to prepared Region
- maintain event ID
- reconcile dual-published or uncertain events
- replay regional archive

---

## 25. Validation and game days

1. inject one extremely hot key
2. double event size without changing count
3. throttle producer APIs and test partial-batch retry
4. stop one consumer for longer than normal
5. insert permanent poison event
6. throttle downstream database
7. exhaust Lambda concurrency
8. remove EKS worker nodes during rebalance
9. reshard Kinesis under load
10. replay duplicate events
11. redrive DLQ through controlled tooling
12. break schema compatibility
13. isolate one Region
14. test archive restore into a clean consumer state
15. generate observability surge without harming processing

---

## Adversarial follow-ups

### “Why not use EventBridge for everything?”

EventBridge is excellent for business-event routing and integrations. Kinesis is the better backbone when the workload requires a partitioned high-volume log, ordered consumption, and replay. I validate quotas and cost rather than selecting by convenience.

### “Why put SQS after Kinesis?”

Kinesis preserves the shared ordered/replayable event log. SQS gives a specific downstream task independent retry, buffering, concurrency, and DLQ without blocking other stream consumers.

### “Can Lambda process millions of events per second?”

The answer depends on batching, shard count, execution time, concurrency quota, downstream limits, and cost. I model and load-test the whole path. Lambda is one consumer option, not the capacity proof.

### “How do you guarantee exactly once?”

I assume duplicate delivery and implement exactly-once business effect through event IDs, conditional writes, inbox/outbox patterns, and idempotent external operations.

### “What happens when one tenant creates 40% of traffic?”

I detect partition and tenant skew, enforce producer quotas, and use a partition strategy that distributes work where ordering permits. If all events require strict ordering for that tenant, the serial invariant has a finite ceiling and must be redesigned or accepted.

### “Why use EKS if Lambda is managed?”

EKS is appropriate for sustained high utilization, long-running or specialized processors, stateful frameworks, custom runtimes, GPUs, and explicit backpressure. Lambda is better for simpler managed handlers. The choice is workload-driven.

---

## Weak answers to avoid

- connecting Kinesis -> SNS -> SQS -> EventBridge -> Lambda -> EKS without semantic reason
- no event-size or byte-throughput math
- random partition key that breaks required ordering
- customer ID partition key without skew analysis
- checkpoint before side effect
- claiming exactly-once transport
- infinite retry of poison events
- autoscaling only on CPU instead of lag/age
- no archive or replay tool
- direct Lambda scaling that overwhelms the database
- treating EventBridge as a limitless raw telemetry bus
- no multi-Region event identity and duplicate strategy

---

## Closing statement

> At this scale, the platform is a set of controlled queues and logs, not one pipeline. Kinesis owns ordered replayable ingestion, SQS isolates work and retries, SNS and EventBridge route the right classes of events, and Lambda or EKS execute according to runtime needs. Idempotency, backpressure, partition design, and replay are the architecture—not cleanup details.