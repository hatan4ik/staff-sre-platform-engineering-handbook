# Executable Reliability Engineering Labs

These labs turn SLO, error-budget, overload, disaster-recovery, and chaos concepts into deterministic exercises.

## Current lab

1. [SLO, error-budget, burn-rate, and protected-cohort analysis](01-error-budget/README.md)

The current lab uses Python's standard library and requires no cloud account.

## Method

1. Define the user journey and event classification.
2. Calculate allowed bad events and remaining budget.
3. Normalize current failure rate into burn rate.
4. Compare aggregate and protected cohorts.
5. Apply fast- and slow-burn policy.
6. Convert the result into an explicit release or incident decision.

## Ownership rule

Labs must test reliability invariants rather than only produce charts. Every exercise should include positive cases, dangerous edge cases, and an operational decision.
