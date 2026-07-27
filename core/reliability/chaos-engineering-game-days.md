# Chaos Engineering and Game-Day Governance

This chapter defines a safe, evidence-driven chaos-engineering program for Staff/Principal SRE and Platform Engineering.

## Interview answer in 90 seconds

> Chaos engineering is controlled experimentation against a reliability hypothesis, not random production breakage. I start with a steady-state metric tied to a critical user journey, define one failure assumption to test, bound the blast radius by environment, cell, tenant, traffic percentage, and duration, and establish automated abort conditions. The experiment must preserve safety, security, and data-integrity invariants. We run it first in a disposable or lower-risk environment, then progress through canary production scopes only after evidence supports it. During the exercise we validate detection, diagnosis, mitigation, ownership, communication, and recovery—not merely whether redundancy exists. Every game day produces an evidence package and owned corrective actions with verification tests. A mature program schedules recurring experiments for the highest-risk assumptions and blocks closure until the repaired behavior is demonstrated.

## Chaos is a scientific workflow

```text
reliability assumption
        |
        v
steady-state hypothesis
        |
        v
bounded fault injection
        |
        v
observe user and system behavior
        |
        v
abort, recover, or continue
        |
        v
analyze evidence
        |
        v
corrective action and re-test
```

The experiment is valuable when it changes confidence through evidence.

## Required experiment contract

Every experiment should declare:

- business and technical hypothesis;
- critical user journey and steady-state SLI;
- failure mechanism;
- expected system behavior;
- safety, security, and data-integrity invariants;
- exact target scope;
- maximum traffic, tenants, nodes, cells, or regions affected;
- duration and time window;
- automated and manual abort conditions;
- incident commander and experiment owner;
- communication plan;
- recovery procedure;
- evidence to capture;
- corrective-action and re-test expectations.

## Good hypotheses

Examples:

- “If one availability-zone node pool becomes unavailable, checkout success remains above the protected-cohort SLO and pending pods recover within ten minutes.”
- “If the identity provider adds 500 ms latency, optional personalization sheds before authentication exceeds its latency objective.”
- “If a service-mesh control plane becomes unavailable, existing data-plane proxies continue serving last-known-good configuration for at least the tested window.”
- “If the active region is fenced, writes move to the recovery region without dual authority and the measured RPO remains within objective.”
- “If a telemetry collector loses its exporter, application latency remains unchanged and telemetry loss is visible within five minutes.”

Bad hypothesis: “Let’s kill random pods and see what happens.”

## Steady-state definition

A steady state must be measurable and relevant.

Use:

- critical-journey success rate;
- latency distributions;
- data freshness;
- write correctness and duplicate rate;
- queue age;
- control-plane convergence;
- protected-cohort SLO;
- recovery time and recovery point;
- alert detection and acknowledgement time.

CPU or pod count alone is not a user-facing steady state.

## Blast-radius dimensions

Bound all applicable dimensions:

- environment;
- cluster;
- region and availability zone;
- cell or shard;
- node pool;
- service and dependency;
- tenant or customer cohort;
- request percentage;
- release version;
- data class;
- duration;
- operator permissions.

Use a kill switch independent of the system under test when possible.

## Progression model

```text
model or simulation
  -> unit and integration fault tests
  -> disposable environment
  -> staging with realistic load
  -> production shadow or synthetic traffic
  -> small production cell
  -> broader production ring
  -> recurring automated verification
```

Do not skip directly to broad production merely because the fault seems simple.

## Fault catalog

### Compute and Kubernetes

- process crash;
- pod deletion;
- node reboot or termination;
- kubelet or runtime failure;
- CPU, memory, disk, inode, and PID pressure;
- image-pull failure;
- scheduling constraint or capacity loss;
- control-plane API latency;
- admission webhook outage.

### Network

- packet loss;
- latency and jitter;
- connection reset;
- DNS timeout or stale answer;
- asymmetric route failure;
- one-zone path loss;
- TLS handshake failure;
- service-mesh control-plane or gateway loss.

### Data and messaging

- replica lag;
- leader loss;
- stale reads;
- write rejection;
- queue backlog;
- duplicate delivery;
- poison messages;
- hot partition;
- failover and failback;
- backup-restore delay.

### Dependency and third party

- elevated latency;
- intermittent errors;
- hard outage;
- quota exhaustion;
- credential expiry;
- certificate rotation failure;
- malformed response;
- partial regional failure.

### Delivery and control systems

- bad configuration;
- GitOps controller outage;
- registry unavailability;
- artifact-verification failure;
- secret rotation;
- observability pipeline loss;
- feature-flag service degradation.

## Abort conditions

Abort automatically or immediately when:

- safety, authorization, financial, or data-integrity invariants are threatened;
- protected-cohort SLO burns beyond the approved budget;
- impact exceeds the declared scope;
- recovery controls do not respond;
- telemetry required to judge safety is unavailable;
- an unrelated incident begins;
- the system enters an unknown state;
- the experiment owner or incident commander calls stop.

An abort is not an experiment failure. It is a safety mechanism and an evidence point.

## Production safeguards

Require:

- peer review;
- change and experiment records;
- least-privilege fault-injection identity;
- protected-resource deny lists;
- independent kill switch;
- tested recovery path;
- current backups for data-risk experiments;
- explicit customer and compliance considerations;
- no simultaneous conflicting changes;
- incident-response coverage;
- time-bounded credentials and automation;
- full audit logs.

## Game-day roles

- **Experiment lead:** owns hypothesis and injection.
- **Incident commander:** owns safety and may abort.
- **Operations lead:** performs mitigation and recovery.
- **Observer/scribe:** records facts, timestamps, and decisions.
- **Service owners:** respond as they would in a real event.
- **Safety reviewer:** verifies scope and invariants.

For some exercises, responders should not know the exact fault. The safety team still must know and retain the kill switch.

## What to measure during the game day

### Detection

- time to symptom alert;
- time to correct service ownership;
- false or noisy pages;
- telemetry gaps;
- whether dashboards expose only symptoms or enough evidence.

### Diagnosis

- time to first credible hypothesis;
- ability to isolate cohort and request path;
- access to logs, traces, profiles, events, and change history;
- misleading indicators;
- dependency and platform escalation time.

### Mitigation

- time to safe action;
- approval and permission delays;
- rollback or load-shedding effectiveness;
- blast-radius containment;
- operator error opportunities;
- automation behavior.

### Recovery

- user-SLI restoration;
- backlog and reconciliation drain;
- failback safety;
- data reconciliation;
- hidden degraded state;
- time to restore full redundancy.

## Evidence package

Retain:

- experiment contract and approvals;
- exact fault parameters;
- start, stop, and abort times;
- user and system telemetry;
- commands and automation output;
- incident timeline;
- screenshots only as secondary evidence;
- expected versus actual behavior;
- gaps and contributing conditions;
- corrective actions with owner and due date;
- verification and re-test result.

## Corrective-action quality

Weak actions:

- “monitor more”;
- “be careful”;
- “update documentation” without mechanism change;
- “train the team” as the only correction;
- “increase timeout” without analysis.

Strong actions:

- enforce bounded retries in shared client policy;
- add per-tenant concurrency limits;
- remove a global singleton;
- add write fencing;
- automate node repair;
- add a tested degraded mode;
- create a protected SLO and paging rule;
- add conformance tests to the promotion gate;
- narrow permissions and add a safe rollback workflow.

## Experiment scheduling

Prioritize assumptions by:

```text
risk = likelihood * impact * uncertainty
```

High-impact assumptions with low evidence should be tested first.

Recurring experiments should cover:

- region and zone failover;
- backup restore;
- identity and certificate rotation;
- queue replay;
- overload and load shedding;
- control-plane degradation;
- node-image rollout and rollback;
- observability loss;
- third-party dependency failure;
- incident-responder access.

## Chaos maturity model

### Level 1 — ad hoc

Manual lower-environment failures, little evidence, no recurring schedule.

### Level 2 — governed

Templates, scope review, steady-state SLIs, abort criteria, and action tracking.

### Level 3 — production canaries

Bounded production experiments with automated safety controls and SLO evidence.

### Level 4 — continuous verification

Experiments are attached to release, infrastructure, recovery, and platform conformance pipelines.

### Level 5 — organizational learning

Risk-based portfolio, shared patterns, cross-team game days, executive reporting, and demonstrated reduction of unknown failure modes.

## Weak answers to avoid

- “Use Chaos Monkey.”
- “Randomly kill pods in production.”
- “We have multi-AZ, so resilience is tested.”
- “If the service recovered, the game day passed.”
- “Only the SRE team participates.”
- “Run chaos after the design is complete.”

## Adversarial follow-ups

### When should you not run a production experiment?

When safety or data invariants cannot be bounded, recovery is untested, required telemetry is missing, an unrelated incident is active, or the potential impact exceeds approved risk.

### How do you test a catastrophic region failure safely?

First prove fencing, destination capacity, replication, routing, and recovery in lower-risk environments. In production, use a bounded cell or controlled region-switch mechanism with explicit safety rules rather than destroying the region.

### Who owns corrective actions?

The team that owns the failed mechanism or organizational control, with one accountable person, due date, verification method, and closure evidence.

### What proves the program is valuable?

Reduced uncertainty, discovered design gaps before incidents, faster detection and recovery, fewer repeated failure modes, verified RTO/RPO and overload behavior, and corrective actions that remain closed under re-test.

## Principal-level review checklist

- every experiment begins with a user-relevant hypothesis;
- blast radius is bounded across technical and customer dimensions;
- abort conditions are automated where possible;
- safety and data invariants override experiment completion;
- responders practice real ownership and communication;
- evidence includes detection, diagnosis, mitigation, and recovery;
- corrective actions change mechanisms and are re-tested;
- high-risk assumptions have recurring experiments;
- chaos results influence architecture, release, and investment decisions.
