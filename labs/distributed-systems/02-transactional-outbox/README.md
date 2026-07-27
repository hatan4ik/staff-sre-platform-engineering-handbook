# Lab 2 — Transactional Outbox and Idempotent Inbox

## Invariant

Creating an order must produce exactly one logical fulfillment effect, even when the event relay crashes and the broker delivers the same event more than once.

The transport is at least once. The business effect is effectively once.

## Why the naïve dual write fails

Unsafe sequence:

```text
1. commit order to database
2. publish OrderCreated to broker
```

A crash between steps leaves a committed order with no event.

Reversing the steps is also unsafe:

```text
1. publish OrderCreated
2. commit order to database
```

A crash or rollback after publication creates an event for business state that does not exist.

## Safe structure

The lab uses two SQLite files:

- `app.db` — orders, outbox, consumer inbox, and fulfillment state
- `broker.db` — simulated external broker deliveries

The application transaction writes both the order and outbox row:

```text
BEGIN
  INSERT order
  INSERT outbox event
COMMIT
```

The relay later publishes pending outbox events. Publication and marking the outbox row cannot be atomic across the two databases, so duplicate publication remains possible.

The consumer protects its side effect with a uniqueness constraint on the stable `event_id`.

## Run the complete demonstration

```bash
python3 outbox_lab.py demo
```

The demo performs these steps:

1. Resets both databases.
2. Creates an order and outbox row atomically.
3. Publishes the event to the broker.
4. Simulates a relay crash before marking the outbox row as published.
5. Restarts the relay and publishes the same stable event again.
6. Consumes both deliveries.
7. Shows that the consumer applies one logical fulfillment effect.

Expected evidence:

- two broker delivery rows
- one stable `event_id`
- one consumer inbox row
- one fulfillment row

## Run each phase manually

Initialize:

```bash
python3 outbox_lab.py reset
```

Create an order:

```bash
python3 outbox_lab.py create-order \
  --order-id order-2001 \
  --customer-id customer-88 \
  --amount-cents 24500
```

Publish and crash after the broker commit:

```bash
python3 outbox_lab.py relay --crash-after-publish
```

The process exits with code `75` to represent a deliberate crash point.

Restart the relay:

```bash
python3 outbox_lab.py relay
```

Consume deliveries:

```bash
python3 outbox_lab.py consume
```

Inspect all state:

```bash
python3 outbox_lab.py show
```

## Force additional duplicate deliveries

```bash
python3 outbox_lab.py reset
python3 outbox_lab.py create-order \
  --order-id order-3001 \
  --customer-id customer-99 \
  --amount-cents 9900
python3 outbox_lab.py relay --duplicate-each 5
python3 outbox_lab.py consume
python3 outbox_lab.py show
```

The broker contains five physical deliveries, but the inbox uniqueness constraint permits one logical consumer transition.

## What this lab proves

The transactional outbox does not create exactly-once delivery. It converts an unsafe distributed dual write into:

- one atomic local transaction
- asynchronous at-least-once publication
- duplicate-tolerant consumption
- durable evidence for reconciliation

## Production design checklist

A production implementation should define:

- stable event identifiers
- outbox retention and cleanup
- relay ownership and concurrency control
- ordering requirements per aggregate
- consumer idempotency scope
- poison-message handling
- schema evolution
- replay policy
- backlog and oldest-event-age metrics
- reconciliation when broker and database state disagree
- auditability of every state transition

## Interview drill

An interviewer asks:

> How do you update a database and publish to Kafka without losing events?

A Staff-level answer should include:

1. Avoid an uncoordinated dual write.
2. Write business state and outbox record in one local transaction.
3. Publish the outbox asynchronously.
4. Assume publication can be duplicated.
5. Use stable event IDs and idempotent consumers.
6. Explain ordering, cleanup, replay, lag, and reconciliation.
7. State that exactly-once is an end-to-end business property, not merely a broker configuration.
