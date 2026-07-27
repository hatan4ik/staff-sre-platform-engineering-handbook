# Infrastructure as Code, Terraform, and Governance

This module owns reusable infrastructure-as-code principles shared by AWS, Netflix, Tesla, and future interview tracks.

## Current canonical chapters

1. [Terraform state integrity, locking, recovery, and governance](terraform-state-integrity.md)
2. [Infrastructure as Code tool selection and governance](tool-selection-and-governance.md)

The module covers:

- State bindings, lineage, serial, and sensitive data.
- Backend locking and split-brain writer prevention.
- Orphaned-lock investigation and safe force-unlock.
- Infrastructure mutation followed by state-write failure.
- Refresh-only reconciliation, imports, moved blocks, and state repair.
- Current S3 lock files and migration from legacy DynamoDB locking.
- State boundaries, multi-account and multi-region ownership.
- Declarative, cloud-native, programming-language, GitOps, configuration-management, and control-plane tool categories.
- One authoritative owner per resource and control-loop composition.
- Module contracts, policy, testing, promotion, drift, rollback, and tool migration.
- CI concurrency, stale plans, audit, and break-glass recovery.

## Planned chapters

- Provider aliases, module composition, and dependency contracts.
- Policy as code and change governance.
- Drift detection and reconciliation operating models.
- Testing, promotion, and reusable platform modules.

## Ownership rule

Reusable state, locking, module, policy, drift, and IaC-governance material belongs here. Platform tracks should add only cloud-specific services, failure behavior, commands, and interview scenarios.
