# Platform as a Product, Golden Paths, and Paved Roads

## Why this exists

Traditional operations teams often scale by adding tickets, meetings, specialists, and undocumented exceptions. The result is slow delivery, dependency on a small number of experts, and uneven production quality. Platform engineering changes the scaling model: recurring operational knowledge is turned into a supported product that teams can consume safely.

The key shift is not from virtual machines to Kubernetes. It is from **request fulfillment** to **product ownership**.

## What the interviewer is testing

The interviewer wants to know whether you can:

- identify a real internal customer and a painful journey;
- prioritize outcomes instead of tools;
- design an opinionated path without destroying autonomy;
- create a supportable contract between the platform and its users;
- decide what to standardize, expose, hide, or reject;
- prove that the platform improved delivery and reliability.

## Definitions

### Platform product

A maintained set of capabilities with:

- named customers;
- documented interfaces;
- reliability and support expectations;
- an adoption strategy;
- a roadmap driven by evidence;
- lifecycle and deprecation policies.

### Golden path

A recommended end-to-end way to achieve a common outcome, such as creating and operating a production HTTP service. It combines defaults, automation, documentation, controls, and production evidence.

### Paved road

A path that is easy, safe, observable, and supported. Teams may leave it, but they then accept explicit ownership for the additional complexity.

### Escape hatch

A controlled way to handle legitimate exceptions without weakening the default path for everyone. Escape hatches require an owner, a reason, an expiry or review point, and clear support boundaries.

## Start from the journey

Do not begin with "we need Backstage" or "we need Crossplane." Begin with a measurable user journey.

Example:

```text
Developer wants a new production service
  -> waits for repository creation
  -> copies an old pipeline
  -> opens network and IAM tickets
  -> guesses observability requirements
  -> deploys after multiple handoffs
  -> discovers ownership and cost gaps during an incident
```

A platform product rewrites the journey:

```text
Choose supported service type
  -> declare owner, data class, SLO tier, and dependencies
  -> generate repository and delivery configuration
  -> provision approved runtime and identities
  -> validate policy and readiness
  -> deploy progressively
  -> expose service, runbook, cost, SLO, and support metadata
```

## Product discovery questions

Ask:

1. Which developer journeys consume the most waiting time?
2. Which failures recur across teams?
3. Which controls are repeatedly implemented incorrectly?
4. Which decisions are genuinely variable, and which should be defaults?
5. Which user groups have materially different needs?
6. What is the smallest path that creates a complete production outcome?
7. What capability would teams voluntarily adopt because it is easier than the alternative?

## Designing a golden path

A production-grade path normally includes:

- repository and ownership metadata;
- build and test policy;
- artifact provenance;
- runtime and infrastructure declaration;
- workload identity;
- secrets integration;
- network and dependency controls;
- deployment strategy;
- telemetry and SLO defaults;
- cost allocation;
- operational readiness checks;
- rollback and recovery behavior;
- documentation and support routing.

The path should not expose every cloud option. It should expose the few choices that materially change business or reliability behavior.

## Opinionated defaults versus autonomy

Use three layers:

```text
Layer 1: safe default
  Most teams choose nothing.

Layer 2: bounded configuration
  Teams select from supported regions, sizes, SLO tiers, and data classes.

Layer 3: exception path
  Rare cases receive architecture review and explicit ownership.
```

This keeps the common path simple while preserving an accountable mechanism for unusual workloads.

## Platform contract

For each capability, document:

| Area | Platform owns | Application team owns |
|---|---|---|
| Interface | API, template, validation, status | Correct intent and metadata |
| Runtime | supported baseline and upgrades | application behavior and resource demand |
| Security | identity pattern, policy guardrails | authorization logic and data handling |
| Delivery | supported pipelines and rollback mechanism | release decision and application compatibility |
| Observability | telemetry path and default dashboards | meaningful service-level signals |
| Incident | platform control-plane incidents | application incidents unless shared failure exists |

Ambiguity here creates organizational outages.

## Adoption strategy

Do not mandate an immature platform. Use:

1. a narrow pilot with a willing team;
2. side-by-side measurement of the old and new journeys;
3. rapid correction of friction;
4. migration tooling for the next cohort;
5. documented support and escape hatches;
6. gradual policy enforcement only after the path is proven.

Adoption should be earned through value, then reinforced through standards where risk requires it.

## Failure modes

- building a portal before fixing the underlying workflow;
- creating templates that generate unowned code;
- hiding failures behind a friendly UI;
- forcing all teams into one runtime model;
- allowing unlimited template variation;
- measuring resource creation instead of production outcomes;
- treating support tickets as evidence of user failure rather than product friction;
- leaving deprecated paths available indefinitely.

## Evidence and acceptance criteria

A successful path should improve several of these:

- time from approved idea to first production deployment;
- active engineering time required for that journey;
- number of manual handoffs;
- change failure rate;
- time to restore;
- percentage of services with owner, SLO, runbook, and cost metadata;
- security-policy exceptions;
- developer satisfaction for a specific journey;
- platform support load per onboarded service.

Do not claim success based only on portal visits or number of generated repositories.

## 90-second interview answer

> I treat the platform as an internal product, not as a centralized ticket queue or a Kubernetes project. I start with a painful developer journey, identify the customer and measurable delay or risk, and build the smallest supported golden path that produces a complete production outcome. The path includes opinionated defaults for identity, delivery, observability, cost, and reliability, with bounded configuration for common variation and explicit escape hatches for legitimate exceptions. I define the ownership contract so teams know what the platform operates and what remains their responsibility. I pilot with willing teams, compare the old and new journeys, and earn adoption before making standards mandatory. I measure time-to-production, handoffs, change failure rate, support load, and coverage of operational metadata. The goal is not maximum abstraction; it is lower cognitive load and safer autonomy.

## Adversarial follow-ups

### "Why not let every team choose its own tools?"

Local choice can be valuable, but unconstrained variation transfers integration, security, upgrade, and incident cost to the organization. I standardize recurring undifferentiated work and preserve choice where it changes product outcomes.

### "What if a team refuses the golden path?"

I first determine whether the path lacks a required capability or the team is preserving accidental complexity. A valid exception gets explicit ownership, risk review, and a future review point. An invalid exception should not silently become a second supported platform.

### "How many golden paths should exist?"

As few as can serve materially different workload classes. Each path creates maintenance, support, security, and migration obligations.

## Dangerous answers

- "Developers are our customers, so we give them whatever they request."
- "The platform removes all infrastructure decisions."
- "Exceptions are forbidden."
- "Teams can leave the path and the platform team will still support them."
- "We know the platform works because provisioning is automated."

## Whiteboard model

```text
Customer journey
    |
Pain and risk inventory
    |
Small supported capability
    |
Defaults + bounded choices + escape hatch
    |
Ownership and support contract
    |
Pilot -> evidence -> adoption -> policy
    |
Continuous product feedback
```

## Primary references

Use current official documentation for the chosen implementation systems. Durable product principles should remain separate from the lifecycle of Backstage, Crossplane, Terraform, Kubernetes, or any cloud provider.
