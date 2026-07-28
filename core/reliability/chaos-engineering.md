# Chaos Engineering: Hypotheses, Safety, and Recovery Evidence

## Purpose

Chaos engineering is controlled experimentation on socio-technical systems. Its goal is not to break production for spectacle; it is to discover whether reliability claims, failover controls, degradation paths, and operational ownership hold under realistic failure.

## Staff/Principal answer

> I start with a falsifiable reliability hypothesis tied to a critical user journey—for example, losing one Availability Zone must not violate the checkout or command SLO. I define steady-state metrics, blast-radius limits, abort conditions, owners, rollback, and evidence collection before injecting failure. I begin in a disposable environment, then staging, then a narrowly scoped production cohort only after lower-risk tests pass. The experiment must test detection, mitigation, recovery, and organizational response—not merely infrastructure redundancy. A successful game day either validates the hypothesis with evidence or produces owned corrective actions and a scheduled retest.

## Experiment contract

Every experiment must document:

1. **User journey:** what customer outcome matters?
2. **Hypothesis:** what should remain true under failure?
3. **Fault:** what controlled condition will be introduced?
4. **Scope:** region, AZ, cluster, namespace, service, tenant, or cohort.
5. **Steady state:** exact SLIs and acceptable bounds.
6. **Abort conditions:** automatic and human stop triggers.
7. **Rollback:** how the fault is removed and state reconciled.
8. **Owners:** experiment lead, incident commander, service owners, communications.
9. **Evidence:** metrics, traces, logs, events, audit records, timelines.
10. **Learning:** decisions, corrective actions, verification, retest date.

## Maturity ladder

```text
static review
  -> unit and integration fault tests
  -> disposable environment
  -> staging under representative load
  -> production shadow or tiny cohort
  -> bounded production game day
  -> continuous automated verification
```

Do not jump directly to a broad production test because the architecture diagram looks redundant.

## Failure categories

### Compute and orchestration

- terminate a pod, node, or node pool;
- delay node provisioning;
- block image pulls;
- fail readiness or startup dependencies;
- disrupt leader election;
- exhaust a resource quota.

### Network and discovery

- add latency, loss, reset, or partition;
- fail DNS resolution or return stale records;
- break one AZ path;
- expire or rotate certificates;
- isolate service-mesh control-plane connectivity while preserving last-known-good data plane.

### Data and messaging

- slow a database replica;
- remove a quorum member;
- create a hot partition;
- delay replication;
- duplicate or reorder messages;
- pause consumers and build backlog;
- inject poison messages.

### Dependency and control plane

- fail an admission webhook;
- throttle the Kubernetes API;
- deny cloud API calls;
- delay identity-provider responses;
- make an observability pipeline unavailable;
- fail a GitOps controller or deliver invalid configuration.

### Regional recovery

- withdraw traffic from a region;
- fence writes;
- promote a replica;
- validate routing convergence;
- test failback and data reconciliation.

## Safety controls

- default-deny experiment permissions;
- explicit target selectors and maximum affected count;
- TTL on injected faults;
- independent kill switch;
- prevalidated rollback command;
- no destructive data experiment without recovery proof;
- no simultaneous uncontrolled change window;
- customer-support and communications awareness when production impact is possible;
- protected tenants, safety functions, and compliance boundaries;
- automatic abort on SLO burn, error threshold, queue age, or data-integrity signal.

## Steady-state design

Infrastructure health is insufficient. Use user-centered indicators:

- success and latency for the critical journey;
- freshness and consistency;
- command completion or transaction finality;
- queue age and duplicate rate;
- failover and convergence time;
- percentage of users in degraded mode;
- recovery-point and recovery-time objectives;
- operator detection and mitigation time.

A system can have healthy nodes while users fail because routing, data authority, identity, or dependencies are broken.

## Example experiment: lose one Kubernetes node

**Hypothesis:** terminating one worker node does not violate the protected API success-rate SLO, and affected pods become Ready elsewhere within the declared recovery objective.

**Preconditions:**

- replicas span topology domains;
- PodDisruptionBudgets are reviewed;
- capacity exists or node provisioning time is understood;
- stateful workloads have fencing and attachment rules;
- external synthetic probes are active.

**Fault:** terminate one selected non-control-plane node.

**Observe:**

- user success and latency;
- endpoint removal time;
- pod rescheduling and readiness;
- volume detach/attach;
- load-balancer target health;
- autoscaler reaction;
- controller and API pressure.

**Abort:** protected journey exceeds burn threshold, data-integrity signal fires, or recovery exceeds the safe experiment window.

**Pass:** user objectives remain within bounds and the platform converges without manual repair.

## Example experiment: dependency slowdown

Inject 500 ms latency into a noncritical enrichment dependency.

Expected behavior:

- caller deadline expires before the overall request deadline;
- circuit breaker or concurrency limiter prevents worker exhaustion;
- optional enrichment is omitted;
- critical response succeeds;
- retries remain within budget;
- degradation is visible in telemetry.

This validates overload and graceful-degradation design better than simply killing the dependency.

## Game-day execution

1. Read the contract aloud and confirm stop authority.
2. Record baseline steady state.
3. Inject only the approved fault.
4. Observe without immediately coaching responders.
5. Abort when a condition is met—do not negotiate with the guardrail.
6. Remove the fault and verify convergence.
7. Reconcile any durable state or backlog.
8. Compare actual behavior with the hypothesis.
9. Assign corrective actions with owners and due dates.
10. Retest before claiming closure.

## What a failed experiment means

A failed hypothesis is useful when the experiment remained controlled. Classify the gap:

- design assumption was false;
- detection was late or noisy;
- mitigation was unsafe or undocumented;
- capacity or topology was insufficient;
- data fencing or reconciliation failed;
- ownership was unclear;
- observability disappeared during the fault;
- rollback recovered infrastructure but not the user journey.

## Program governance

Track:

- critical journeys with a tested failure hypothesis;
- experiment recency;
- pass/fail and unresolved findings;
- mean time to detect and mitigate during exercises;
- percentage of corrective actions verified by retest;
- coverage by failure domain;
- production incidents that should become regression experiments.

Chaos coverage is not the number of faults injected. It is the percentage of important reliability claims that have recent evidence.

## Adversarial follow-ups

**Would you run chaos in production?**  
Only after lower environments pass, the production hypothesis requires real conditions, the cohort and guardrails are narrow, and accountable owners approve the risk.

**What if observability fails during the experiment?**  
That may itself invalidate the safety contract. Abort unless independent external evidence remains sufficient to protect users.

**Is killing random pods chaos engineering?**  
Not by itself. Without a hypothesis, steady state, guardrails, recovery validation, and learning loop, it is random failure injection.

## Weak answers to avoid

- “Use Chaos Monkey in production.”
- “The goal is to prove the system never fails.”
- “Healthy infrastructure means the test passed.”
- “Run the test during an incident.”
- “A rollback completed, so users recovered.”
- “Repeat the same pod-kill test and call coverage complete.”
