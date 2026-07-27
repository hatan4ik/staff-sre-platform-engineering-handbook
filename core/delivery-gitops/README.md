# GitOps and Progressive Delivery

This module owns reusable delivery, reconciliation, promotion, rollback, and fleet-rollout principles shared by all interview tracks.

## Current canonical chapter

1. [GitOps, reconciliation, and progressive delivery](gitops-progressive-delivery.md)

The chapter covers:

- Build, promotion, and reconciliation boundaries.
- Pull versus push delivery.
- Source-of-truth protection and immutable artifacts.
- Resource and field ownership across Terraform, GitOps, HPA, operators, and cloud controllers.
- Repository topology, dependency ordering, CRDs, pruning, and drift.
- Secrets, bootstrap, multi-tenancy, and multi-cluster delivery.
- Canary, blue/green, ring, cohort, and feature-flag release strategies.
- Health analysis, pause, rollback, incident operation, observability, and SLOs.
- Tool-neutral mappings to Argo CD and Flux.

## Planned chapters

- Artifact integrity, provenance, and supply-chain policy.
- Database migration and backward-compatible release patterns.
- Multi-cluster fleet promotion and disconnected environments.
- Progressive-analysis automation and error-budget integration.
- Delivery incident labs.

## Ownership rule

Reusable GitOps, promotion, reconciliation, and progressive-delivery theory belongs here. Platform tracks should add only environment-specific services, commands, failure behavior, and interview scenarios.
