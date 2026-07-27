# AWS Interview Hands-On Labs

The written curriculum explains production reasoning. These labs convert the most important failure modes into repeatable practice.

> Run the local labs on a development workstation or disposable environment. Review every command before running it. The initial labs avoid billable AWS infrastructure unless explicitly stated.

## Lab sequence

| Lab | Environment | Primary interview skills |
|---|---|---|
| [01 — Terraform partial-apply recovery](01-terraform-partial-apply-recovery/) | Local Terraform | state evidence, partial apply, import, reconciliation, one-writer discipline |
| [02 — Kubernetes restart forensics](02-kubernetes-restart-forensics/) | kind, minikube, or disposable cluster | container vs pod restart, previous logs, exit codes, OOM, sidecars, node/controller evidence |
| [03 — Event-stream backpressure simulator](03-event-stream-backpressure/) | Python 3.11+ | partitioning, hot keys, bounded queues, retry, DLQ, idempotency, replay-safe processing |

## Lab operating model

Every lab follows the same sequence:

```text
1. Establish the healthy baseline.
2. Inject one controlled failure.
3. Preserve evidence before changing the system.
4. State at least two hypotheses.
5. Use the smallest query that can disprove each hypothesis.
6. Apply the narrowest reversible mitigation.
7. Prove recovery with the original user or control-plane signal.
8. Record the preventive mechanism.
```

## Evidence journal

Create a journal for every run:

```markdown
# Lab run
Date/time UTC:
Git revision:
Environment:

## Expected behavior

## Failure injected

## First user/control-plane symptom

## Preserved evidence

## Hypotheses
1.
2.

## Disproving tests

## Mitigation

## Recovery proof

## Permanent prevention
```

Interview preparation improves when the candidate can explain **what evidence changed their mind**, not only the final diagnosis.

## Safety rules

- Do not use production credentials.
- Do not point the Terraform lab at an AWS backend.
- Do not run restart-failure manifests in a shared production cluster.
- Use a dedicated Kubernetes namespace and remove it after the exercise.
- Treat Terraform state and Kubernetes logs as potentially sensitive.
- Do not run high event rates until the local simulator works at low rate.
- Preserve failing evidence before cleanup.

## Mapping to the interview curriculum

### Round 1

- Terraform state and recovery
- one writer per state
- control-loop and backpressure reasoning

### Round 2

- Terraform partial apply
- pods restarting despite healthy probes
- evidence beyond dashboards
- hypothesis-driven incident response

### Round 3

- millions of events per second
- hot partition behavior
- exactly-once business effect through idempotency
- poison-event isolation
- overload and queue-age reasoning

## Completion standard

A lab is complete when the candidate can:

- reproduce the failure without reading the guide;
- capture the correct evidence before destructive action;
- explain at least one tempting but unsafe shortcut;
- recover the system;
- map the local behavior to the equivalent AWS/EKS production mechanism;
- answer five adversarial follow-ups.