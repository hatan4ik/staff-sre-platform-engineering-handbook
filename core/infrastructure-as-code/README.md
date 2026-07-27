# Infrastructure as Code, Terraform, and Governance

This module owns reusable infrastructure-as-code principles shared by AWS, Netflix, Tesla, and future interview tracks.

## Current canonical chapter

1. [Terraform state integrity, locking, recovery, and governance](terraform-state-integrity.md)

The chapter covers:

- State bindings, lineage, serial, and sensitive data.
- Backend locking and split-brain writer prevention.
- Orphaned-lock investigation and safe force-unlock.
- Infrastructure mutation followed by state-write failure.
- Refresh-only reconciliation, imports, moved blocks, and state repair.
- Current S3 lock files and migration from legacy DynamoDB locking.
- State boundaries, multi-account and multi-region ownership.
- CI concurrency, stale plans, drift, audit, and break-glass recovery.

## Planned chapters

- Terraform versus platform-native IaC tools.
- Module contracts, provider aliases, and composition.
- Policy as code and change governance.
- Drift detection and reconciliation operating models.
- Testing, promotion, and reusable platform modules.

## Ownership rule

Reusable state, locking, module, policy, drift, and IaC-governance material belongs here. Platform tracks should add only cloud-specific services, failure behavior, commands, and interview scenarios.
