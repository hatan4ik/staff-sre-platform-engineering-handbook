# Incident Response, Request-Path Isolation, and Causal Analysis

This module owns reusable incident-response methods shared by AWS, Netflix, Tesla, and future platform tracks.

## Canonical chapters

1. [Request-path debugging from client to dependency](request-path-debugging.md)
2. [Cohort analysis for partial and selective failures](cohort-analysis.md)
3. [Postmortems, causal analysis, and corrective-action governance](postmortems.md)

Planned additions:

- Incident command and communications.
- Change correlation and rollback decisions.
- Multi-region failover incident command.
- Security-incident integration.

Evidence-system design is canonical in [`core/observability/evidence-beyond-dashboards.md`](../observability/evidence-beyond-dashboards.md).

## Core method

```text
customer impact
      |
      v
precise scope and paired evidence
      |
      v
first divergent request-path layer or cohort
      |
      v
falsifiable hypothesis
      |
      v
smallest reversible mitigation
      |
      v
user-facing recovery proof
      |
      v
causal analysis and owned prevention
      |
      v
verified corrective actions
```

## Ownership rule

Reusable request-path isolation, cohort reasoning, incident command, evidence preservation, mitigation, recovery proof, postmortem, and corrective-action methods belong here. Cloud and company tracks should add only platform-specific services, commands, business invariants, and failure context.
