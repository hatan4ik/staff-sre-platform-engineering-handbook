# Kubernetes Autoscaling and Capacity Realization

This module owns reusable autoscaling principles shared by Kubernetes, EKS, AKS, GKE, and platform-engineering interview tracks.

## Canonical chapter

1. [Autoscaling control loops, scheduling, and capacity realization](control-loops-capacity-realization.md)

The chapter covers:

- HPA, VPA, KEDA, scheduler, and node-autoscaler ownership.
- CPU request semantics and HPA calculations.
- Resource, custom, and external metrics.
- Observation, calculation, mutation, scheduling, startup, and traffic-admission failures.
- Cluster Autoscaler and Karpenter operating models.
- NodePool, node-group, and capacity-supply boundaries.
- On-Demand baseline, Spot interruption tolerance, and disruption safety.
- Capacity-realization timelines and SLOs.
- Scale-up, scale-down, rollout, and failure-domain testing.
- Incident commands and adversarial interview questions.

## Ownership rule

Reusable autoscaling algorithms, control-loop interactions, scheduling constraints, capacity-realization analysis, and disruption principles belong here. Cloud tracks should add provider-specific capacity products, quota names, pricing mechanisms, and implementation commands.
