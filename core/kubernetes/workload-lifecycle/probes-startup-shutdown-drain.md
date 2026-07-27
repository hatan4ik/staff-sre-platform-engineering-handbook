# Kubernetes Probes, Startup Safety, Graceful Shutdown, and Traffic Drain

This chapter is the canonical foundation for liveness, readiness, startup probes, business-aware traffic admission, pod termination, endpoint propagation, connection draining, and rollout safety.

## Interview answer in 90 seconds

> I use probes as control signals with distinct ownership. A startup probe protects slow initialization from premature liveness restarts. Liveness answers only whether restarting the container can recover a stuck process. Readiness answers whether this pod should receive new traffic now, including critical local dependencies but not every remote dependency that would remove all capacity during a shared outage. Business health is measured separately through end-to-end SLIs. For shutdown, the workload first becomes unready, stops accepting new work, drains connections and in-flight requests within a bounded deadline, releases leases or writer authority, and then exits before the termination grace period. I validate the entire propagation path from readiness change through EndpointSlice, proxy or load balancer removal, connection drain, and process exit. A green probe is not proof that the user transaction is healthy, and an aggressive liveness probe can turn latency into a restart storm.

## Probe roles

### Startup probe

Purpose: determine whether initialization has completed enough for liveness and readiness evaluation to begin.

Use for:

- long application startup;
- cache or model loading;
- schema or configuration initialization;
- JVM or runtime warm-up;
- dependency bootstrap with a known bounded window.

A startup probe should not hide unbounded startup. Measure and alert on startup duration.

### Liveness probe

Purpose: determine whether restarting the container is a safe and useful recovery action.

Good liveness signals:

- event loop or worker deadlock;
- process cannot make local progress;
- unrecoverable internal corruption;
- local health loop stopped advancing.

Bad liveness dependencies:

- shared database unavailable;
- external API unavailable;
- DNS transiently slow;
- cluster-wide control-plane issue;
- high request latency caused by overload.

If every replica fails liveness because one shared dependency is down, Kubernetes can restart the entire service and worsen the outage.

### Readiness probe

Purpose: decide whether the pod should receive new traffic.

Readiness may consider:

- application initialized;
- required local listener available;
- local queue or concurrency below a safety threshold;
- configuration loaded;
- required credential present;
- writer or shard ownership established;
- local cache warm enough for safe service;
- critical dependency reachable when removing this pod will not cause global collapse.

Readiness should fail quickly enough to stop new traffic, but not flap on brief noise.

## Probe versus user SLI

```text
startup probe  -> can initialization continue?
liveness probe -> would restart repair local process progress?
readiness probe-> should this instance receive new traffic?
user SLI       -> did the real user journey succeed correctly and on time?
```

Do not use one `/health` endpoint for every purpose unless it exposes intentionally different semantics.

## Probe mechanisms

Common mechanisms:

- HTTP GET;
- TCP socket;
- gRPC health check;
- exec command.

Trade-offs:

### HTTP or gRPC

- application-aware;
- can expose distinct endpoints;
- uses network stack and listener;
- may be affected by proxy interception or TLS configuration.

### TCP

- proves a connection can be established;
- does not prove request processing or correctness.

### Exec

- can inspect local state;
- consumes process and fork resources;
- shell commands can hang or behave differently under pressure;
- image changes may remove dependencies.

Probe resource consumption matters at large replica counts.

## Timing parameters

Understand:

- initial delay;
- period;
- timeout;
- success threshold;
- failure threshold;
- startup probe gating;
- termination grace behavior.

Conceptually, detection delay is bounded by periods, thresholds, timeout behavior, and scheduling jitter. The exact wall-clock timing can be affected by node pressure and probe execution delays.

Do not design a 30-second SLO around a probe that may require longer to remove endpoints and drain traffic.

## Business-aware readiness

A readiness check should answer whether this replica can safely serve its assigned work.

Examples:

- a read-only endpoint may remain ready when a write dependency is unavailable;
- a shard worker is ready only after ownership fencing succeeds;
- a service may serve cached data while personalization is degraded;
- a gateway may reject optional routes while remaining ready for critical routes;
- a pod may become unready when local queue age exceeds a bound.

Avoid all-or-nothing readiness when the service can expose route-specific degradation through gateways, feature controls, or application logic.

## Overload and readiness

Readiness can shed traffic from one overloaded instance, but removing many instances at once reduces total capacity and can create a death spiral.

Use:

- local concurrency limits;
- bounded queues;
- per-instance overload signals;
- hysteresis;
- gradual recovery;
- global load shedding;
- minimum serving capacity;
- protected critical traffic.

Do not use readiness as the only overload-control mechanism.

## Readiness gates

Readiness gates allow external or custom conditions to participate in pod readiness.

Potential uses:

- load balancer target registration;
- service-mesh or network readiness;
- application-specific ownership;
- security or configuration attestation.

Risks:

- external controller outage prevents readiness;
- stale status;
- circular dependency;
- missing owner or timeout;
- rollout deadlock.

Every gate needs an owner, SLO, failure mode, and break-glass procedure.

## Endpoint propagation

Readiness changes flow through:

```text
kubelet probe result
  -> Pod condition
  -> EndpointSlice controller
  -> EndpointSlice update
  -> kube-proxy / eBPF / proxy / gateway watch
  -> dataplane update
  -> new traffic stops
```

Measure propagation delay. During control-plane or watch degradation, a pod may be unready but still receive traffic from stale dataplane state.

## External load balancers

External load balancers may have separate health checks and deregistration delay.

Coordinate:

- Kubernetes readiness;
- target registration;
- external health-check path;
- load-balancer interval and threshold;
- deregistration delay;
- connection draining;
- `externalTrafficPolicy` behavior;
- node and pod termination.

A pod can stop being an EndpointSlice target while an external load balancer still sends traffic through a node or gateway.

## Pod termination sequence

A simplified sequence:

```text
deletion requested
  -> pod marked terminating
  -> endpoint readiness/serving state changes
  -> preStop hook may execute
  -> TERM signal sent to container process
  -> application stops accepting new work
  -> in-flight work drains
  -> leases/writer authority released safely
  -> process exits
  -> grace period expires if needed
  -> forced termination
```

Exact ordering and sidecar behavior are version- and runtime-sensitive. Test the deployed Kubernetes version and workload model.

## Application shutdown contract

The application should:

1. handle SIGTERM or the configured stop signal;
2. transition to draining state;
3. make readiness false promptly;
4. stop accepting new work;
5. drain or cancel in-flight work within a deadline;
6. stop background consumers safely;
7. flush or checkpoint only bounded critical state;
8. release leases or writer authority with fencing semantics;
9. close connections;
10. exit before the grace period.

Do not sleep blindly for the whole grace period. Observe actual traffic removal and drain state.

## `preStop` hooks

A preStop hook can signal or coordinate shutdown, but:

- it consumes part of the termination grace period;
- it can hang;
- network or shell dependencies may be unavailable;
- it may run while new traffic still arrives;
- it should be idempotent;
- it is not a substitute for proper signal handling.

Use hooks only when the application cannot own the transition directly or an external deregistration step is required.

## Long-lived connections

HTTP/2, gRPC, WebSocket, database, and streaming connections may outlive endpoint removal.

Drain behavior may require:

- GOAWAY or equivalent protocol signal;
- stop accepting new streams;
- max connection age;
- connection close after bounded drain;
- load balancer or proxy drain configuration;
- client reconnect with jitter;
- preservation of in-flight idempotency.

Killing every long-lived connection simultaneously can create a reconnect storm.

## Background workers and queues

For consumers:

- stop claiming new work;
- finish or abandon current work according to visibility/lease semantics;
- extend lease only within shutdown deadline;
- use idempotency for redelivery;
- checkpoint progress;
- release partition ownership;
- avoid acknowledging work before durable effect.

Readiness for queue consumers may not affect traffic. Use explicit worker-drain state.

## Stateful writers and leaders

A terminating writer must not create a dual-writer window.

Use:

- lease or consensus transfer;
- monotonically increasing fencing token;
- storage-system attachment fencing;
- application-level epoch;
- confirmation that old writer can no longer commit.

Graceful shutdown is helpful but not sufficient under crash or partition. The resource must reject stale writers.

## PodDisruptionBudgets

PDBs limit voluntary disruption, not every outage.

They do not guarantee:

- pod readiness;
- capacity during node failure;
- safe application quorum;
- successful drain;
- sufficient topology domains;
- protection from involuntary disruption.

Review PDBs with deployment replicas, topology, surge, autoscaling, maintenance, and application quorum.

## Deployment rollout interactions

Potential deadlocks:

- `maxUnavailable: 0` with no surge capacity;
- strict anti-affinity prevents surge pod placement;
- startup takes longer than progress deadline;
- readiness gate controller unavailable;
- old pods cannot drain long-lived connections;
- PDB blocks node maintenance;
- new version is ready at probe level but fails real traffic.

Use progressive delivery and user-SLI analysis, not readiness alone.

## Incident workflow

### Symptoms

- restart loop;
- deployment stuck;
- Ready pods return errors;
- unready pods still receive traffic;
- termination causes 502/503/reset spikes;
- long-running requests are cut off;
- all replicas become unready during dependency failure;
- external load balancer targets terminating capacity.

### Evidence

```bash
kubectl get pod <pod> -n <namespace> -o yaml
kubectl describe pod <pod> -n <namespace>
kubectl get endpointslice -n <namespace> -l kubernetes.io/service-name=<service> -o yaml
kubectl get events -n <namespace> --sort-by=.lastTimestamp
kubectl logs <pod> -n <namespace> --previous
kubectl rollout status deployment/<name> -n <namespace>
```

Also capture:

- probe latency and failures;
- container termination state;
- application drain logs;
- endpoint propagation timing;
- proxy and load-balancer target state;
- connection and request cohorts;
- user SLIs;
- recent probe or lifecycle changes.

### Stabilize

1. stop the rollout or disruption creating impact;
2. restore a known-good probe or shutdown configuration;
3. prevent liveness from restarting the fleet during shared dependency failure;
4. shed optional traffic and protect minimum capacity;
5. increase grace only when the application can use it and platform deadlines allow it;
6. drain a bounded cohort and observe endpoint propagation;
7. restore external target registration consistency;
8. verify real user traffic, not only readiness.

## SLOs and signals

Track:

- startup duration and failure;
- liveness restart rate and reason;
- readiness transition rate and duration;
- ready-but-failing request rate;
- unready-but-receiving-traffic rate;
- readiness-to-endpoint-removal latency;
- endpoint-removal-to-last-new-request latency;
- termination duration;
- forced-kill rate;
- in-flight request completion and cancellation;
- connection drain and reconnect rate;
- rollout progress and unavailable replicas;
- user SLI during deployment and node drain.

## Validation program

Test:

- slow startup;
- deadlocked local process;
- shared database outage;
- local overload;
- readiness flapping;
- EndpointSlice or control-plane propagation delay;
- SIGTERM under short and long requests;
- HTTP/2/gRPC/WebSocket drain;
- queue-worker shutdown and redelivery;
- leader transfer and stale-writer rejection;
- external load-balancer deregistration;
- deployment with strict topology and PDBs;
- node drain and forced termination.

## Weak answers to avoid

- “Liveness calls the database.”
- “Use the same `/health` endpoint for everything.”
- “Add a 30-second sleep in preStop.”
- “Increase terminationGracePeriodSeconds to ten minutes.”
- “Ready means the service is healthy.”
- “PDB guarantees high availability.”
- “Kill connections and clients will retry.”

## Adversarial follow-ups

### Why not include every dependency in readiness?

A shared dependency outage could remove every replica and eliminate degraded or cached service. Include dependencies according to instance-level serving safety and overall failure behavior.

### When should liveness fail?

When the local container cannot make progress and a restart is likely to repair it. It should not be a general dependency or latency monitor.

### Why can a terminating pod still receive traffic?

Endpoint, proxy, load balancer, client connection, DNS, or connection-pool state may lag. Existing long-lived connections may continue after new endpoint selection stops.

### How do you handle requests longer than the grace period?

Define a maximum supported duration, stop accepting new work, signal drain, let eligible work finish within a bounded deadline, checkpoint or make work idempotently resumable, and cancel the remainder explicitly.

### What proves recovery?

Probe transitions stabilize, endpoint and external target state converge, termination no longer creates error spikes, forced kills return to baseline, and real user journeys remain within SLO during rollout and drain.

## Principal-level review checklist

- startup, liveness, readiness, and user SLI semantics are distinct;
- liveness cannot create fleet-wide restart amplification;
- readiness includes hysteresis and minimum capacity considerations;
- endpoint and external load-balancer propagation are measured;
- applications own signal handling and bounded drain;
- long-lived connections have explicit protocol behavior;
- workers and stateful writers use idempotency and fencing;
- PDBs are reviewed with topology and capacity;
- rollout gates include user SLIs;
- game days exercise dependency outage, drain, and stale endpoint behavior.
