# eBPF, Cilium, Hubble, Falco, and Tetragon Runtime Security

## Interview scenario

Design an eBPF-based network and runtime-security architecture for a large Kubernetes platform. Explain where policy is enforced, what evidence is available, how detection differs from prevention, how the system fails under load, and how to migrate without causing a node-wide outage.

## What the interviewer is testing

This is not a vocabulary test or an invitation to say “eBPF is faster than iptables.” A Staff/Principal answer demonstrates:

- Understanding of the Linux packet and process-execution paths.
- Knowledge of XDP, tc, cgroup/socket, tracepoint, kprobe, and LSM hooks.
- Program loading, verifier behavior, attachment, maps, BTF, and kernel compatibility.
- Separation of network enforcement, flow observability, runtime detection, and runtime prevention.
- Identity-aware policy rather than IP-only thinking.
- Awareness that L7 policy may require Envoy and adds new failure modes.
- Recognition that NetworkPolicy cannot determine whether an allowed request came from legitimate code or a compromised shell.
- Awareness that asynchronous event pipelines can lose security evidence under load.
- Careful distinction between terminating a process and preventing an operation.
- A migration plan with bounded blast radius, stop conditions, rollback, and evidence.

## Principal-level answer

> I separate four concerns. Cilium provides the Kubernetes network dataplane, identity-aware L3/L4 policy, service load balancing, and selective L7 policy. Hubble provides flow evidence from the same dataplane. Falco provides broad behavioral detection from kernel event streams and plugins. Tetragon provides process-, file-, capability-, and network-aware tracing with optional inline enforcement.
>
> I start from the threat model and a default-deny segmentation model. Cilium identities derive from workload labels, so policy remains stable as pod IPs change. I use portable Kubernetes NetworkPolicy where sufficient, and Cilium-specific policy only for identity, DNS, host, or selected L7 requirements. L7 proxying is reserved for controls whose value justifies Envoy latency and availability dependencies.
>
> Network reachability is not process integrity. If a compromised application is already allowed to contact a sensitive service, network policy alone cannot judge whether a particular allowed request is malicious. Falco can detect suspicious behavior, but asynchronous kernel-to-userspace event streams can overflow, so dropped-event counters are security SLIs. For high-value prevention I use narrowly scoped Tetragon or LSM controls at hooks that can actually deny the operation. Sending `SIGKILL` is not equivalent to preventing every side effect; the hook and action must match the invariant.
>
> I migrate through a canary node pool, validate kernel/BTF compatibility, compare policy behavior and connectivity, deploy runtime policies in monitor mode, and then canary enforcement by workload and node. Stop conditions include packet loss, DNS regression, BPF-map pressure, verifier or program-load failures, unexpected denies, dropped events, and customer-SLI degradation. The security system itself must have bounded failure domains.

## 1. Linux execution foundations

Containers are ordinary Linux processes constrained by namespaces, cgroups, credentials, capabilities, seccomp, LSMs, and filesystem/network isolation. Kubernetes does not bypass the kernel.

### Simplified inbound packet path

```text
NIC
 |
 v
network driver
 |
 +--> XDP hook
 |
 v
skb and normal network stack
 |
 +--> tc ingress
 +--> routing / netfilter / conntrack / service translation
 +--> cgroup and socket hooks where configured
 |
 v
socket receive queue
 |
 v
application recv()/read()
```

### Simplified pod egress path

```text
application connect()/send()
 |
 v
socket / cgroup hooks
 |
 v
endpoint eBPF policy
 |
 +--> allow -> direct path or L7 proxy redirect
 |
 +--> deny -> drop reason / counter / flow event
 |
 v
routing / encapsulation / encryption
 |
 v
host interface and NIC
```

The exact path depends on XDP mode, overlay versus native routing, kube-proxy replacement, host firewalling, encryption, socket acceleration, and L7 redirection.

## 2. eBPF program lifecycle

```text
source
  -> Clang/LLVM compilation
  -> bytecode + BTF relocation metadata
  -> privileged loader invokes bpf() syscall
  -> verifier accepts or rejects
  -> optional JIT compilation
  -> attach at XDP/tc/cgroup/tracepoint/kprobe/LSM/etc.
  -> programs execute and read/write maps
```

### Verifier

The verifier checks memory safety, pointer use, bounded control flow, allowed helper use, stack constraints, and program-type rules.

Do not claim the verifier proves operational safety. A valid program can still:

- Consume excessive CPU.
- Create map pressure.
- Drop legitimate traffic.
- Introduce lock contention.
- Amplify a policy-controller defect across a node.

Verifier or load failures are availability risks and belong in node-image qualification and rollout gates.

### BPF maps

Maps hold state shared by programs and control agents:

- Workload identity.
- Policy decisions.
- Service/backend tables.
- Conntrack and NAT state.
- Metrics and counters.
- Tail-call targets.
- Runtime selectors.

Map capacity is finite and consumes kernel memory. Monitor failed inserts, pressure, eviction, lookup latency, and workload impact.

### BTF and CO-RE

BPF Type Format and Compile Once–Run Everywhere reduce dependency on exact kernel structure layouts. They do not make every hook, helper, kernel configuration, or enforcement action universally available. Maintain a tested compatibility matrix.

## 3. Hook selection

### XDP

Runs early in RX processing.

Good for:

- High-rate early drops.
- DDoS filtering.
- Fast redirection.
- Simple packet classification.

Trade-offs:

- Less process and protocol context.
- Driver-mode compatibility differences.
- Early drops can occur before richer evidence exists.
- Generic and native XDP differ materially.

### tc ingress/egress

Runs later with skb context and is widely used by Cilium for endpoint policy, routing, service handling, encapsulation, and identity-aware decisions.

### cgroup and socket hooks

Useful for connection-time and workload-context decisions, socket-level policy, local service acceleration, and avoiding per-packet work in some paths.

### Tracepoints

Kernel-defined instrumentation points with relatively stable semantics. Strong for observation, but events commonly require asynchronous userspace processing.

### Kprobes

Attach to kernel functions and provide broad visibility. Risks include internal-function instability, argument interpretation, time-of-check/time-of-use mistakes, and weak suitability for universal prevention.

### LSM hooks

Security-specific decision points. Often preferable when the kernel is explicitly deciding whether an operation should be permitted.

Use alongside—not as an excuse to ignore—capabilities, seccomp, AppArmor/SELinux, read-only filesystems, user namespaces, and Kubernetes Pod Security controls.

## 4. Cilium architecture

```text
Kubernetes API
   |
   +--> Cilium operator
   |
   +--> Cilium agent on each node
          |
          +--> endpoint and identity discovery
          +--> policy calculation and regeneration
          +--> BPF loading and map management
          +--> service load balancing
          +--> optional Envoy L7 proxy
          +--> Hubble event production

Hubble Relay
   -> aggregates per-node flow streams
   -> CLI / UI / metrics / external consumers
```

### Security identity

Cilium maps selected workload labels to numeric identities. Policy targets identities instead of ephemeral pod IPs.

Operational questions:

- Which labels participate in identity?
- How quickly do identities propagate?
- What happens during API or kvstore unavailability?
- How are stale identities removed?
- How does policy behave during agent restart or regeneration?

### L3/L4 policy

Use default deny and explicit required paths. Include DNS, kube-apiserver, telemetry, time synchronization, certificate services, and infrastructure dependencies in the model.

### L7 policy

L7 enforcement can redirect traffic through Envoy. This adds:

- Userspace proxy CPU and memory.
- New latency.
- Certificate and protocol handling.
- Upgrade and configuration failure modes.
- Additional observability needs.

Use only when the control materially reduces risk.

### Egress and DNS

Domain-aware egress controls are useful but DNS names are not static identities. Consider:

- Multiple answers and CDNs.
- TTL changes.
- DNS poisoning and resolver trust.
- Direct-IP bypass.
- Fail-open versus fail-closed behavior.
- Resolver availability.

## 5. Hubble as evidence

Hubble observes flows from the Cilium dataplane and can expose:

- Source/destination identities.
- Verdict and drop reason.
- L3/L4 metadata.
- Selected L7 metadata.
- DNS and service context.
- Flow metrics.

It helps answer:

- Which policy denied a connection?
- Is traffic reaching the expected backend?
- Did a rollout change the path?
- Are retransmissions or drops concentrated by node, identity, or service?

Hubble is not an infinite forensic store. Define retention, aggregation, sampling, privacy, and export capacity. Monitor event loss.

## 6. Falco detection model

Falco consumes kernel events and plugin sources and evaluates behavioral rules in userspace.

Strong uses:

- Unexpected shell execution.
- Sensitive file access.
- Privilege changes.
- Container escape indicators.
- Suspicious process trees.
- Kubernetes audit or cloud-event correlation.

Limitations:

- Detection is commonly asynchronous.
- Rule quality and environment tuning matter.
- Event pipelines can overflow.
- Alerts require ownership and response.
- Excessive broad rules create noise and cost.

Dropped events are not merely a telemetry issue; they represent blind time in a security control.

## 7. Tetragon tracing and enforcement

Tetragon can observe and filter process execution, files, capabilities, syscalls/kernel functions, and network activity with Kubernetes-aware context.

### Detection versus enforcement

- **Observe:** emit evidence and alert.
- **Terminate:** send a signal to the triggering process.
- **Deny/override:** prevent a supported operation at an appropriate hook.

A process kill may occur after part of the triggering action has already happened. For a correctness invariant such as “this file must never be opened,” prefer a hook capable of authorization before the operation completes.

### Policy design

- Narrow selectors by namespace, labels, binary, capability, and path.
- Begin in monitor mode.
- Measure event volume and false positives.
- Canary enforcement on low-blast-radius workloads.
- Define emergency disable mechanisms.
- Protect the security agent from application resource exhaustion.

## 8. Threat-model layering

Example controls:

| Threat | Primary control | Supporting evidence/control |
|---|---|---|
| Unauthorized service-to-service traffic | Cilium L3/L4 identity policy | Hubble flow evidence |
| Unapproved external egress | Egress policy/gateway and DNS policy | DNS and flow auditing |
| Compromised process using an allowed path | Runtime process/file policy | Falco/Tetragon evidence, app authorization |
| Privileged container abuse | Pod Security, capabilities, seccomp, LSM | Runtime detection |
| Data-plane policy regression | Policy tests and canary | Hubble denies and SLOs |
| Event-pipeline overload | Capacity limits and drop metrics | Alerting and failover collectors |

No one control answers every threat.

## 9. Failure modes

### Agent unavailable

Already attached programs may continue to enforce existing state, but identity updates, policy regeneration, and map management may stop. Define expected behavior and test it.

### Policy regeneration failure

A syntactically valid change may fail to compile/load or may create transient inconsistency. Gate changes and retain last-known-good policy.

### Map exhaustion

Conntrack/NAT/service/policy map pressure may cause connection failures or inconsistent behavior. Capacity-plan using peak connection churn and failure traffic.

### Event loss

Ring/perf buffers and userspace consumers can fall behind. Monitor dropped-event counters and end-to-end lag.

### L7 proxy failure

Envoy failure may affect only L7-enforced flows or can become a broader bottleneck depending on design. Separate proxy capacity and health from generic pod readiness.

### Kernel incompatibility

A node image may lack required BTF, helpers, hooks, configuration, or verifier behavior. Block promotion before production.

### Bad enforcement policy

An overbroad selector can terminate or deny many workloads. Require peer review, dry run, canary, bounded selectors, and rapid disable.

## 10. Migration strategy

### Phase 0: inventory

- Kernel and distribution versions.
- Existing CNI and kube-proxy behavior.
- NetworkPolicy semantics in use.
- Overlay/native routing.
- Service mesh and encryption.
- Privileged workloads.
- Required throughput, PPS, and connection churn.

### Phase 1: qualification

- Validate kernel/BTF/helper support.
- Run Cilium connectivity tests.
- Benchmark datapath latency and throughput.
- Stress BPF maps and connection churn.
- Verify rollback and node replacement.

### Phase 2: canary node pool

- Taint and label canary nodes.
- Move low-risk workloads first.
- Compare network-policy behavior.
- Observe Hubble flows and drops.
- Verify DNS, service translation, host access, and egress.

### Phase 3: runtime monitoring

- Deploy Falco/Tetragon in observation mode.
- Measure event volume, loss, overhead, and false positives.
- Tune selectors and ownership.

### Phase 4: limited enforcement

- Choose narrow high-value invariants.
- Canary by workload and node.
- Define automatic and manual stop conditions.
- Exercise emergency disable.

### Phase 5: progressive expansion

Expand only after policy equivalence, SLO health, and operational response are demonstrated.

## 11. Stop conditions

Pause or rollback on:

- Packet loss or connection failure above baseline.
- DNS regression.
- Customer latency or availability degradation.
- BPF program-load or verifier errors.
- Map pressure or failed inserts.
- Unexpected policy denies.
- Flow/runtime event loss.
- Agent crash loops.
- L7 proxy overload.
- Unbounded enforcement impact.

## 12. Observability and SLOs

Track:

### Dataplane

- Packet/connection success by identity and node.
- Drop reasons.
- Service-translation failures.
- Conntrack/NAT/map pressure.
- Program execution overhead.

### Control plane

- Policy convergence time.
- Identity propagation delay.
- Regeneration success/failure.
- Agent and operator health.

### Hubble/runtime pipelines

- Event production rate.
- Dropped events.
- Export lag.
- Rule-evaluation latency.
- Alert delivery success.

### Customer

- Availability, p95/p99 latency, error rate, and retry amplification.

## 13. Interview follow-ups

### Why not use only Kubernetes NetworkPolicy?

It is valuable and portable for L3/L4 segmentation, but some environments need identity, DNS, host, richer observability, service translation, or selected L7 controls. Use extensions only where requirements justify them.

### Can Cilium stop a malicious request to an allowed service?

It can restrict network reachability and selected L7 attributes. It cannot generally determine whether application-level intent is legitimate. Strong service authorization and runtime controls remain necessary.

### Why is `SIGKILL` not always prevention?

A signal terminates the process, but the triggering operation may have partially completed. Prevention requires a hook and action capable of denying before the invariant is violated.

### What happens if the Cilium agent dies?

Existing programs and maps may continue serving the last-known state, while policy/identity updates stop. Exact behavior depends on configuration and must be tested rather than assumed.

### Why treat dropped Falco/Tetragon events as an SLI?

Because the security control is blind during event loss. Availability of the detector is not sufficient if evidence cannot be delivered and evaluated.

### What is the biggest rollout risk?

The security dataplane runs on every node and can affect every workload. A kernel, map, policy, or agent defect can create node-wide or cluster-wide impact, so migration and enforcement must be canaried with explicit stop conditions.

## 14. Hands-on labs

1. Inspect a Cilium endpoint's identity, policy, maps, and flow verdicts.
2. Create default-deny policy and prove required DNS/control-plane exceptions.
3. Generate allowed and denied flows and correlate Hubble output with application behavior.
4. Stress connection churn and observe conntrack/NAT map pressure.
5. Build a Falco rule for unexpected shell execution and measure false positives.
6. Deploy a Tetragon tracing policy in monitor mode, then canary a narrow enforcement rule.
7. Simulate an agent outage and document last-known-state behavior.
8. Qualify two kernel images and compare BTF, helper, verifier, and performance behavior.

## Principal-level summary

> eBPF provides programmable kernel hooks, not a universal security answer. I select hooks according to the context and enforcement semantics required, separate network policy from runtime process control, and treat maps, verifier compatibility, event loss, and agent behavior as production capacity and reliability concerns. The security platform itself is privileged, node-wide infrastructure, so I migrate it through tested images, canary pools, monitor mode, bounded enforcement, explicit stop conditions, and rapid rollback.