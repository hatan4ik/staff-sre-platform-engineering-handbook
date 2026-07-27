# Service Level Objectives and Error Budgets

This module owns the reusable reliability contract between product, engineering, platform, SRE, and leadership.

## Canonical chapter

1. [User-centered SLOs, error budgets, burn rates, and ownership](error-budgets.md)

The chapter covers:

- SLIs, SLOs, SLAs, and error budgets.
- User journeys and good-event semantics.
- Availability, latency, correctness, freshness, and quality indicators.
- Denominator engineering and `GOOD | BAD | UNKNOWN | EXCLUDED` classification.
- Measurement points and telemetry bias.
- Error-budget and burn-rate mathematics.
- Multi-window alerting concepts.
- Protected cohorts, low traffic, dependencies, and multi-region services.
- Ownership, release policy, governance, adoption, and anti-patterns.
- Interview drills and implementation roadmap.

## Ownership rule

Reusable SLO definitions, measurement, budget mathematics, alerting, policy, ownership, and governance belong here. Track adapters should add product-specific journeys and service-specific implementation details.
