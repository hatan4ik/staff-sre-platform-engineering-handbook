# Lab 1 — Retry Amplification, Ownership, and Jitter

## Safety and availability objective

The system should recover from transient dependency failures without multiplying one logical request into an unbounded amount of physical work.

The key measurements are:

- logical requests
- physical calls at every layer
- dependency attempts per logical request
- completion latency
- retry-wave concentration over time

## Run the unsafe layered-retry design

```bash
python3 retry_simulator.py \
  --mode layered \
  --requests 1000 \
  --layers 3 \
  --retries 2 \
  --failure-rate 0.65
```

Every service layer retries the layer below it. One request may therefore create many dependency attempts.

Ask:

- How many physical dependency calls were created?
- How large is the amplification ratio?
- What happens to p95 and p99 completion time?
- Where do retry waves appear on the timeline?

## Compare with no retries

```bash
python3 retry_simulator.py \
  --mode none \
  --requests 1000 \
  --layers 3 \
  --retries 2 \
  --failure-rate 0.65
```

This provides a baseline for success rate, attempts, and latency.

The no-retry design avoids amplification but gives up recovery from transient failure.

## Assign retry ownership to one layer

```bash
python3 retry_simulator.py \
  --mode edge \
  --requests 1000 \
  --layers 3 \
  --retries 2 \
  --failure-rate 0.65
```

Only the outermost layer owns retries. Compare this result with the layered design.

A strong design normally chooses one retry owner with enough context to know:

- whether the operation is idempotent
- whether the failure is transient
- how much deadline remains
- whether the dependency is already overloaded
- whether a retry budget is available

## Add jitter

```bash
python3 retry_simulator.py \
  --mode edge \
  --jitter \
  --requests 1000 \
  --layers 3 \
  --retries 2 \
  --failure-rate 0.65
```

Then compare against layered retries with jitter:

```bash
python3 retry_simulator.py \
  --mode layered \
  --jitter \
  --requests 1000 \
  --layers 3 \
  --retries 2 \
  --failure-rate 0.65
```

Jitter spreads attempts over time. It does not solve retry multiplication by itself.

## Extreme overload experiment

```bash
python3 retry_simulator.py \
  --mode layered \
  --requests 5000 \
  --layers 4 \
  --retries 3 \
  --failure-rate 0.90 \
  --dependency-latency-ms 250
```

Treat this as an incident simulation. Explain how the following feedback loop forms:

```text
dependency slows
  -> callers time out
  -> multiple layers retry
  -> concurrency and queueing increase
  -> dependency becomes slower
  -> more timeouts and retries
```

## JSON output

```bash
python3 retry_simulator.py --mode layered --json > result.json
```

Use JSON output to compare scenarios programmatically or feed the data into a plotting tool.

## Production controls

A production-ready retry policy should include:

- one explicit retry owner
- end-to-end deadline propagation
- bounded attempts
- exponential backoff with jitter
- idempotency protection
- retry budgets
- concurrency limits
- overload-aware admission control
- metrics separating logical requests from physical attempts

## Interview drill

An interviewer says:

> We configured three retries in the application, service mesh, and SDK to improve reliability.

A Staff-level response should challenge the design:

1. Retries at multiple layers multiply rather than add.
2. A timeout does not prove the prior attempt failed.
3. Duplicate side effects require end-to-end idempotency.
4. Synchronized retries can create load waves.
5. Retry policy must fit inside the caller's deadline.
6. The dependency needs a retry budget and concurrency protection.
7. Dashboards must distinguish one customer operation from every generated attempt.
