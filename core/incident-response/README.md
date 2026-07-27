# Incident Response, Request-Path Isolation, and Causal Analysis

This module owns reusable incident-response methods shared by AWS, Netflix, Tesla, and future platform tracks.

## Canonical chapters

1. [Request-path debugging from client to dependency](request-path-debugging.md)
2. [Cohort analysis for partial and selective failures](cohort-analysis.md)

Planned additions:

- Incident command and communications.
- Postmortems, causal analysis, and corrective-action governance.
- Change correlation and rollback decisions.
- Evidence preservation and investigation beyond dashboards.
- Multi-region failover incident command.
- Security-incident integration.

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
```

## Ownership rule

Reusable request-path isolation, cohort reasoning, incident command, evidence preservation, mitigation, recovery proof, postmortem, and corrective-action methods belong here. Cloud and company tracks should add only platform-specific services, commands, business invariants, and failure context.
