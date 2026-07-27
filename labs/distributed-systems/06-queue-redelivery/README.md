# Lab 6 — Queue Redelivery, Visibility Timeouts, Ordering, and DLQs

This lab demonstrates why at-least-once delivery is a business-processing problem, not only a broker configuration.

The safety invariant is:

> A redelivered message may execute more than once, but it must not create more than one externally visible business effect.

The simulator models:

- visibility timeouts
- receipt-handle replacement after redelivery
- consumer crash after committing a side effect but before acknowledgement
- idempotent consumer inboxes
- poison-message receive budgets
- dead-letter queues
- delayed negative acknowledgement
- per-group ordering and head-of-line blocking

It uses only Python's standard library.

## Duplicate delivery without idempotency

```bash
python3 labs/distributed-systems/06-queue-redelivery/queue_delivery_demo.py \
  unsafe \
  --json
```

The worker applies the side effect and crashes before acknowledging. After the visibility timeout expires, the broker redelivers the message. The second execution applies the effect again.

Expected result:

```text
logical message:       1
physical deliveries:   2
business side effects: 2
```

The broker behaved correctly. The consumer did not.

## Idempotent consumer inbox

```bash
python3 labs/distributed-systems/06-queue-redelivery/queue_delivery_demo.py \
  idempotent \
  --json
```

The consumer records the stable message ID in an inbox at the same atomic boundary as the business effect. On redelivery, it detects the existing ID, skips the side effect, and acknowledges the duplicate.

Expected result:

```text
logical message:       1
physical deliveries:   2
business side effects: 1
inbox records:         1
```

In a production service, the inbox insertion and state mutation must be committed together. A separate `SELECT`, effect, and later `INSERT` still has a race.

## Poison message and DLQ

```bash
python3 labs/distributed-systems/06-queue-redelivery/queue_delivery_demo.py \
  poison \
  --json
```

The message repeatedly fails processing. After the configured receive budget is exceeded, the broker removes it from the active queue and places it in the DLQ.

A DLQ is not a deletion policy. It is an operational workflow that needs:

- ownership
- alerting
- reason classification
- payload and schema inspection
- replay tooling
- a retention policy
- protection against replaying an unrepaired poison message

## Visibility timeout too short

```bash
python3 labs/distributed-systems/06-queue-redelivery/queue_delivery_demo.py \
  visibility \
  --json
```

Worker A receives a message with a five-second visibility timeout but needs ten seconds to finish. At second six, Worker B receives the same message with a new receipt token.

The result shows:

- two workers can execute the same message concurrently
- Worker A's old receipt token can no longer acknowledge the message
- an undersized visibility timeout creates duplicate work even without a crash

Production controls include:

- choose the timeout from observed processing percentiles
- extend visibility for known long-running work
- keep the handler idempotent anyway
- cap in-flight concurrency
- monitor receive count and processing duration together

## Ordered message groups

```bash
python3 labs/distributed-systems/06-queue-redelivery/queue_delivery_demo.py \
  ordering \
  --json
```

The simulator places two events in `account-1` and one event in `account-2`.

While the first `account-1` event is unacknowledged:

- the second event in that group remains blocked
- the independent `account-2` group can progress

Ordering creates a throughput and availability trade-off. One poison or slow message can block every later message in the same ordering group.

## Run every scenario

```bash
python3 labs/distributed-systems/06-queue-redelivery/queue_delivery_demo.py \
  all \
  --json
```

## Production telemetry

Track at minimum:

- logical messages published
- physical deliveries
- receive count distribution
- duplicate detections
- handler execution count per message ID
- visibility timeout expirations
- acknowledgement failures by receipt age
- queue age of oldest message
- active queue depth and DLQ depth
- DLQ arrival rate by error class
- consumer lag by partition or message group
- per-group head-of-line blocking time
- processing duration versus visibility timeout

A dashboard that shows only queue depth hides the distinction between healthy throughput, poison retries, and duplicate amplification.

## Staff/Principal interview answer

A strong answer should say:

> I assume an at-least-once broker will redeliver after crashes, timeouts, receipt loss, or acknowledgement ambiguity. I use a stable event ID, commit the consumer inbox and business state atomically, and acknowledge only after that commit. I size and extend visibility from observed processing time, isolate poison messages with a bounded receive budget and owned DLQ workflow, and monitor logical messages separately from physical deliveries. For ordered groups, I explicitly discuss head-of-line blocking and choose the narrowest ordering key that preserves the business invariant.

## Adversarial follow-ups

Be ready to answer:

1. What if the consumer calls an external provider that does not support idempotency?
2. How long should inbox records be retained?
3. What happens when message IDs are reused incorrectly?
4. Can a DLQ replay violate ordering?
5. How do you replay a million DLQ messages without causing an outage?
6. What if one tenant dominates one FIFO group?
7. How do you distinguish consumer lag from repeated poison delivery?
8. Where is the atomic boundary between state mutation and acknowledgement?
9. Does broker-level exactly-once remove the need for idempotent external effects?

Related canonical chapter:

- [`core/distributed-systems/06-messaging-streams-delivery-semantics.md`](../../../core/distributed-systems/06-messaging-streams-delivery-semantics.md)
