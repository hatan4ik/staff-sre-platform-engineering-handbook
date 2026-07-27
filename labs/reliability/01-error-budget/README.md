# Lab 1 — SLO, Error Budget, Burn Rate, and Protected Cohorts

## Interview scenario

An aggregate service dashboard appears healthy, but a critical low-volume user journey is failing. Teams disagree about whether to page, stop a rollout, or continue because the monthly SLO still has budget remaining.

The Staff/Principal task is to:

1. calculate the error budget correctly;
2. normalize current failure into burn rate;
3. apply paired fast- and slow-burn windows;
4. prevent a high-volume easy path from hiding a critical cohort;
5. treat missing telemetry as unknown rather than good;
6. convert the result into an explicit operational decision.

## Safety invariant

> A healthy aggregate cannot overrule a protected user journey, and missing telemetry cannot silently improve the reliability score.

This lab is a deterministic Python simulation and requires no cloud account.

## What the program models

```text
SLO objective and compliance window
      |
      v
valid, bad, unknown, and excluded events
      |
      v
allowed bad events and budget remaining
      |
      v
observed bad fraction and burn rate
      |
      +--> paired fast-burn windows
      +--> paired slow-burn windows
      +--> protected cohort analysis
      +--> telemetry trust check
      |
      v
release or incident decision
```

## Prerequisites

- Python 3.11 or newer.
- No third-party packages.

## Run the demo

```bash
python3 slo_budget.py --demo
```

The built-in scenario contains:

- a very high-volume majority path with a low failure rate;
- a low-volume critical write path with a severe failure rate;
- an aggregate result that can look healthy;
- a protected cohort that is violating policy;
- a fast-burn alert pair;
- an explicit decision to stop and mitigate.

## Run the tests

```bash
python3 -m unittest -v test_slo_budget.py
```

The test suite proves:

- error-budget mathematics;
- `10x` burn and approximate time to exhaustion;
- explicit unknown-event rate;
- invalid objectives and impossible event counts are rejected;
- one noisy short window does not page without confirmation;
- paired fast windows page;
- paired slow windows create a lower-urgency action;
- aggregate health can hide a critical cohort;
- protected-cohort regression pauses a release;
- untrusted telemetry takes precedence over a healthy score.

## Budget exercise

Given:

```text
objective:            99.95%
valid events:         2,000,000,000
allowed bad fraction: 0.05% = 0.0005
bad events:           250,000
```

Then:

```text
allowed bad events = 2,000,000,000 × 0.0005
                   = 1,000,000

budget remaining = 1,000,000 - 250,000
                 = 750,000
                 = 75%
```

## Burn exercise

For a `99.9%` objective:

```text
allowed bad rate = 0.1%
observed bad rate = 1%

burn rate = 1% / 0.1% = 10x
```

For a 30-day window, sustained `10x` burn would consume a full fresh budget in approximately three days.

This is an approximation. Production decisions must also consider budget already consumed, traffic changes, confidence, and whether the burn persists.

## Protected cohort exercise

Example:

```text
majority path:
  1,000,000,000 valid events
  10,000 bad events

critical minority:
  1,000,000 valid events
  20,000 bad events
```

The majority can dominate the aggregate denominator while the critical path fails badly.

Operationally, protect distinct user intents such as:

- writes versus cached reads;
- login versus content browsing;
- command execution versus telemetry ingestion;
- payment versus catalog view;
- one regulated or contracted tenant tier;
- one valid device or client population.

Use metrics for bounded slices and logs, traces, exemplars, or analytical systems for detailed high-cardinality cohorts.

## Unknown-event exercise

The lab calculates:

```text
unknown events / all observed events
```

If the unknown fraction exceeds policy, the decision becomes:

```text
PAUSE_TELEMETRY_UNTRUSTED
```

This prevents a broken client SDK, collector, log pipeline, or metric query from making the SLO appear healthier.

Production handling should define:

```text
GOOD | BAD | UNKNOWN | EXCLUDED
```

with explicit ownership and bounded exclusions.

## Multi-window alert exercise

The lab uses conceptual paired windows:

```text
fast page:
  short fast window exceeds threshold
  AND longer confirmation window exceeds threshold

slow action:
  short slow window exceeds threshold
  AND longer confirmation window exceeds threshold
```

The exact thresholds and windows are policy inputs. Production values should be derived from the objective, compliance window, traffic, time to mitigate, and paging expectations.

The important invariant is that one short spike does not page by itself, while sustained rapid burn does not wait for the monthly SLO to fail.

## Operational decision mapping

The simulator can return:

| Decision | Meaning |
|---|---|
| `STOP_AND_MITIGATE_FAST_BURN` | Page, stop harmful exposure, and stabilize users |
| `PAUSE_PROTECTED_COHORT_REGRESSION` | Aggregate is insufficient; protect the failing journey |
| `PAUSE_TELEMETRY_UNTRUSTED` | The score cannot support a safe release decision |
| `FREEZE_RISKY_CHANGES` | Budget is exhausted or critically low |
| `REDUCE_EXPOSURE_AND_PRIORITIZE_RELIABILITY` | Slow burn or at-risk budget requires action |
| `PROCEED_WITH_NORMAL_GUARDRAILS` | Continue with ordinary rollout and monitoring policy |

The names are illustrative. Real organizations should publish their policy before an incident or release conflict.

## Production implementation mapping

### Step 1 — Define the journey

Document:

- User operation.
- Good-event semantics.
- Valid-event denominator.
- Correctness and latency requirements.
- Measurement source.
- Protected cohorts.
- Owner.

### Step 2 — Backtest

Use historical incidents and normal periods to test:

- Does the SLI move when users report impact?
- Do exclusions hide real failures?
- Does unknown telemetry rise during pipeline incidents?
- Would burn alerts have paged at a useful time?
- Are critical cohorts visible?

### Step 3 — Run nonpaging

Observe burn decisions without paging while validating:

- Query correctness.
- Late events.
- Traffic seasonality.
- Low-volume behavior.
- Alert noise.

### Step 4 — Publish policy

Define:

- Fast and slow burn response.
- Release gates.
- Budget exhaustion behavior.
- Exceptions.
- Leadership risk acceptance.
- Recovery criteria.

### Step 5 — Integrate delivery and incidents

Add:

- Deployment and feature annotations.
- Burn by rollout cohort.
- Automatic pause for fast burn.
- Links from page to runbook, traces, and recent changes.
- Budget impact in the postmortem.

## Common weak answers

### “The monthly SLO is green, so no action is needed”

A current fast burn or protected cohort may require immediate action before the long window turns red.

### “Count every request in one ratio”

High-volume easy traffic can hide a critical journey.

### “Exclude dependency failures”

The user journey still failed. Use dependency signals for attribution and improvement, not denominator removal.

### “Missing data is success”

This rewards telemetry failure.

### “Freeze all releases whenever any budget is used”

Error budgets exist to enable explicit risk trade-offs. Policy should distinguish normal use, elevated burn, near exhaustion, exhaustion, security fixes, and approved exceptions.

### “SRE owns the SLO”

SRE can own the framework. Product and service engineering remain accountable for the promise and the decisions.

## Interview answer drill

> I would define good and valid events for the critical user journey, keep unknown and excluded events explicit, and calculate the remaining budget and current burn rate. I would use paired fast and slow windows so a noisy spike does not page but sustained rapid burn is detected early. Then I would inspect protected cohorts because an aggregate can hide a low-volume critical failure. The result must drive a predefined action such as pausing rollout, reducing exposure, or freezing risky changes. The SLO is operational only when it changes a decision.

## Related material

- [`core/reliability/slo/error-budgets.md`](../../../core/reliability/slo/error-budgets.md)
- [`core/incident-response/cohort-analysis.md`](../../../core/incident-response/cohort-analysis.md)
- [`core/incident-response/postmortems.md`](../../../core/incident-response/postmortems.md)
- [`core/observability/evidence-beyond-dashboards.md`](../../../core/observability/evidence-beyond-dashboards.md)
