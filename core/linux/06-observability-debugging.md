# 6. Linux Observability, Profiling, eBPF, and Production Debugging

This chapter turns Linux observability into a disciplined production-debugging method. The objective is to connect customer-visible symptoms to measurable kernel and application behavior without defaulting to random tuning or destructive restarts.

## 6.1 The observability hierarchy

Use the least invasive tool that can answer the question.

```text
service SLI and traces
  -> host and cgroup metrics
  -> process metrics and /proc
  -> logs and kernel events
  -> syscall tracing
  -> sampling profiles
  -> scheduler/off-CPU analysis
  -> targeted eBPF/ftrace instrumentation
  -> crash dump or invasive reproduction
```

A stronger tool is not automatically a better first tool. Every tool has overhead, blind spots, privilege requirements, and interpretation risks.

## 6.2 The production investigation contract

Before collecting data, state:

- Customer impact.
- Time window.
- Scope: workload, node, zone, region, tenant.
- Current hypothesis.
- Evidence that would confirm or reject it.
- Collection overhead and duration.
- Stop condition.

This prevents observational data from becoming an unstructured dump.

## 6.3 USE, RED, and queue-first reasoning

### USE for resources

For each resource inspect:

- Utilization.
- Saturation.
- Errors.

### RED for services

For each service inspect:

- Rate.
- Errors.
- Duration.

### Queue-first extension

Find where work waits:

- Run queue.
- Futex or lock wait.
- Socket accept/send/receive queue.
- Dirty-page queue.
- Block queue.
- Reclaim or compaction.
- Application backlog.
- Dependency queue.

The same latency symptom can arise from any of these queues.

## 6.4 `/proc` as a live kernel interface

Important process files:

```bash
/proc/<pid>/status
/proc/<pid>/stat
/proc/<pid>/sched
/proc/<pid>/limits
/proc/<pid>/io
/proc/<pid>/fd
/proc/<pid>/maps
/proc/<pid>/smaps_rollup
/proc/<pid>/stack
/proc/<pid>/net
```

Important system files:

```bash
/proc/meminfo
/proc/vmstat
/proc/pressure/*
/proc/interrupts
/proc/softirqs
/proc/net/softnet_stat
/proc/diskstats
/proc/slabinfo
/proc/loadavg
```

Treat procfs values as counters or snapshots with specific scope and semantics. Do not compare values across time without understanding whether they are cumulative, instantaneous, per-CPU, or namespace-scoped.

## 6.5 Pressure Stall Information

PSI measures lost execution time caused by CPU, memory, or I/O pressure.

```bash
cat /proc/pressure/cpu
cat /proc/pressure/memory
cat /proc/pressure/io
```

- `some`: at least one task is stalled.
- `full`: all non-idle tasks in the scope are stalled simultaneously.

PSI is often a better leading indicator than raw utilization because it measures experienced contention.

Examples:

- High CPU PSI with moderate average CPU can indicate hot-core concentration or constrained cgroups.
- High memory PSI before OOM indicates reclaim is already damaging latency.
- High I/O PSI with moderate device utilization can indicate serialized or latency-dominated paths.

## 6.6 `strace`

`strace` observes system calls and their results.

Useful patterns:

```bash
strace -f -ttT -p <pid>
strace -f -e trace=network -p <pid>
strace -f -e trace=file -p <pid>
strace -f -e futex -p <pid>
strace -c -p <pid>
```

Use it to answer:

- Which syscall blocks?
- Is the process repeatedly retrying?
- Are failures `EAGAIN`, `ECONNREFUSED`, `ETIMEDOUT`, `ENOENT`, or `EPERM`?
- Is the application polling, sleeping, or waiting on futexes?

Risks:

- High event volume.
- Stop/trace overhead.
- Timing perturbation.
- Sensitive arguments in output.

Prefer a short, scoped capture on selected threads.

## 6.7 `ltrace`

`ltrace` observes dynamic library calls. It can reveal library-level behavior not visible in syscall names, but modern static linking, language runtimes, inlining, and symbol stripping limit coverage.

Use it only when the question is specifically about userspace library behavior.

## 6.8 `perf stat`

`perf stat` counts hardware and software events.

```bash
perf stat -p <pid> sleep 10
perf stat -e cycles,instructions,cache-misses,branches,branch-misses -p <pid> sleep 10
```

Interpretation examples:

- Low instructions per cycle may indicate stalls, branches, cache misses, or insufficient parallelism.
- High context switches may be normal or pathological depending on throughput and scheduler delay.
- High page faults require distinction between minor and major faults.

Counters can be multiplexed and hardware-dependent. Do not compare unlike machines without normalization.

## 6.9 On-CPU profiling

Sampling profiles answer where CPU time is spent.

```bash
perf record -F 99 -g -p <pid> -- sleep 30
perf report
```

A flame graph visualizes aggregated stacks. Wide frames consume more sampled CPU time.

Common findings:

- Serialization or compression hotspot.
- Excessive allocator work.
- Kernel networking or filesystem cost.
- Lock owner consuming CPU.
- Unexpected logging or telemetry overhead.

A CPU profile does not explain time spent sleeping. For that, use off-CPU analysis.

## 6.10 Off-CPU profiling

Off-CPU profiles aggregate where threads block.

Typical reasons:

- Futex waits.
- Disk I/O.
- Socket receive.
- Scheduler delay.
- Sleep and timers.
- Remote filesystem waits.

This is critical when CPU utilization is low but latency is high.

A complete latency model often combines:

```text
on-CPU execution
+ scheduler wait
+ lock wait
+ I/O wait
+ network wait
+ dependency wait
```

## 6.11 `perf sched`

Scheduler tracing helps diagnose runnable delay, wakeups, migrations, and contention.

```bash
perf sched record -p <pid> -- sleep 10
perf sched latency
perf sched timehist
```

Questions:

- How long did runnable tasks wait?
- Which threads wake one another?
- Are tasks migrating excessively?
- Is one CPU overloaded?
- Does cgroup throttling align with tail latency?

## 6.12 Lock analysis

```bash
perf lock record -- <command>
perf lock report
```

For userspace mutexes, combine:

- `strace -e futex`.
- Off-CPU profiles.
- Runtime-specific lock metrics.
- Owner-thread CPU profile.

Adding CPUs or threads can worsen a serialized bottleneck.

## 6.13 ftrace

ftrace is the kernel's built-in tracing framework.

Capabilities include:

- Function tracing.
- Function graph tracing.
- Tracepoints.
- Event filters.
- Per-CPU buffers.

It is powerful but easy to overuse. A broad function trace on a busy production host can generate enormous volume and overhead.

Use narrow filters, short duration, and a clear hypothesis.

## 6.14 Tracepoints, kprobes, and uprobes

### Tracepoints

Kernel-defined events with relatively stable semantics.

Good for:

- Scheduling.
- Syscalls.
- Block I/O.
- Networking.
- Process lifecycle.

### Kprobes

Dynamic probes on kernel functions.

Advantages:

- Broad coverage.

Risks:

- Internal function changes.
- Argument interpretation errors.
- Version sensitivity.

### Uprobes

Dynamic probes on userspace functions or offsets.

Useful for:

- Application/runtime internals.
- Library calls.
- Custom latency histograms.

Symbol resolution, optimization, inlining, and stripped binaries complicate use.

## 6.15 eBPF observability

eBPF programs can attach to supported hooks, filter in kernel, aggregate in maps, and emit selected events.

Benefits:

- Lower event volume through in-kernel filtering.
- Histograms and aggregation.
- Cross-layer correlation.
- Dynamic instrumentation without rebuilding applications.

Risks:

- Privileged loader attack surface.
- Kernel compatibility.
- Verifier failures.
- Map pressure.
- Ring-buffer drops.
- Excessive hook cost.
- Misinterpreted kernel internals.

A dropped-event metric is part of the observability SLI. Silent loss can produce false confidence.

## 6.16 BPF maps and event transport

Maps can store:

- Counters.
- Histograms.
- Stack traces.
- Correlation state.
- Per-process or per-cgroup data.

Event transport can use ring buffers or perf event arrays.

Design questions:

- What is the maximum event rate?
- What happens when userspace cannot keep up?
- Are events dropped, overwritten, or backpressured?
- How is cardinality bounded?
- How much kernel memory is consumed?

## 6.17 bpftrace and BCC

### bpftrace

High-level dynamic tracing language suitable for targeted questions.

Example patterns:

```bash
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { @[comm] = count(); }'
bpftrace -e 'kprobe:tcp_retransmit_skb { @[comm] = count(); }'
```

### BCC

Toolkit and libraries for building eBPF tracing tools.

Use prebuilt tools when possible, but understand their assumptions, kernel dependencies, and field meanings.

## 6.18 Packet capture

```bash
tcpdump -nn -i any host <peer>
tcpdump -nn -i <iface> port 443
```

Capture considerations:

- Correct namespace and interface.
- Inner versus outer overlay packet.
- Snap length.
- Ring-buffer size.
- File rotation.
- Sensitive payload.
- Offload artifacts.

A missing packet at one interface does not prove it never existed elsewhere. Capture at multiple path points.

## 6.19 `ss`, `nstat`, and socket evidence

```bash
ss -s
ss -lntp
ss -tinp
nstat -az
```

Useful fields include:

- Retransmissions.
- RTT and variance.
- Congestion window.
- Send and receive queues.
- Backlog overflows.
- Socket state counts.

Interpret socket state with application behavior and packet evidence.

## 6.20 Storage observability

```bash
iostat -xz 1
pidstat -d 1
cat /proc/<pid>/io
cat /proc/pressure/io
```

Do not equate `%util` with universal saturation. For parallel devices and virtual volumes, queueing and latency distribution matter more.

Decompose:

- Application queue.
- Filesystem lock/metadata.
- Reclaim/writeback.
- Block queue.
- Device service time.
- Provider-side throttling.

## 6.21 Memory observability

```bash
vmstat 1
pidstat -r 1
cat /proc/meminfo
cat /proc/vmstat
cat /proc/pressure/memory
slabtop
```

Questions:

- Which domain is constrained: host, cgroup, NUMA node?
- Anonymous, file cache, slab, socket, or allocator fragmentation?
- Background or direct reclaim?
- Major faults or swap-ins?
- `memory.high` events or hard OOM?

## 6.22 CPU observability

```bash
mpstat -P ALL 1
pidstat -u -t 1
vmstat 1
cat /proc/pressure/cpu
```

Global CPU averages hide:

- Hot cores.
- Softirq concentration.
- Cgroup throttling.
- Real-time interference.
- Steal time.
- Affinity mistakes.

## 6.23 Kernel logs and crash evidence

```bash
dmesg -T
journalctl -k -b
journalctl -k -b -1
cat /proc/sys/kernel/tainted
```

For severe failures, consider:

- pstore.
- kdump and vmcore.
- Watchdogs.
- Machine-check telemetry.
- Persistent remote journal.

Rebooting may restore service but destroys volatile evidence.

## 6.24 Observability overhead and safety

Every collection method should have an overhead budget.

Potential costs:

- CPU sampling interrupts.
- Trace buffer memory.
- Lock contention in tracing path.
- Disk writes from captures.
- Network egress from telemetry.
- Cardinality explosion.
- Sensitive data exposure.

Production safeguards:

- Time-bounded commands.
- Narrow PID/cgroup/interface filters.
- Sampling.
- File-size limits and rotation.
- Privilege separation.
- Audit logs.
- Approved runbooks.

## 6.25 Incident: p99 latency with normal averages

### Symptoms

- p50 stable.
- p99 periodically spikes.
- Host average CPU 40%.
- Dependency latency normal.

### Investigation

1. Correlate spikes with cgroup `cpu.stat`.
2. Inspect per-CPU utilization and softirq.
3. Measure scheduler delay.
4. Profile on-CPU and off-CPU paths.
5. Compare request timestamps with quota periods.

### Finding

Bursty parallel work exhausts cgroup CPU quota early in the period. Threads are throttled while host CPUs remain idle.

### Prevention

Alert on throttled time and CPU PSI, load-test burst concurrency, and define CPU policy by latency class.

## 6.26 Incident: low CPU, service hangs

### Symptoms

- CPU mostly idle.
- Load average high.
- Requests hang.

### Investigation

```bash
ps -eo state,pid,wchan:32,comm
cat /proc/pressure/io
cat /proc/<pid>/stack
```

### Finding

Many tasks are in D state waiting on a failed network filesystem.

### Prevention

Bound remote filesystem dependencies, test failover, monitor D-state counts and I/O PSI, and isolate mounts from unrelated workloads.

## 6.27 Incident: observability says healthy, users fail

### Symptoms

- Host metrics normal.
- Application metrics show low error rate.
- Users report intermittent failures.

### Possible causes

- Sampling misses rare failures.
- Metrics aggregate away one tenant or zone.
- Telemetry drops under load.
- Health checks exercise a simpler path.
- Traces exclude failed early requests.

### Principal lesson

Observability is itself a distributed system with loss, lag, sampling, cardinality limits, and partial failure. Monitor the telemetry pipeline and validate with independent synthetic transactions.

## 6.28 Interview drills

### When would you use `strace` instead of `perf`?

Use `strace` when the question concerns syscall behavior, errors, retries, or blocking calls. Use `perf` when the question concerns CPU execution, hardware counters, call stacks, scheduler behavior, or lock contention.

### Why can a flame graph be misleading?

It shows sampled on-CPU time, not total wall-clock latency. Sleeping, blocked, throttled, or off-CPU time may dominate.

### Why is low observability overhead not guaranteed with eBPF?

Programs still execute at hook frequency, maps consume kernel memory, events can overwhelm userspace, and poor filters or high-cardinality keys can create significant cost.

### Why preserve evidence before restarting?

A restart destroys process state, queues, stacks, counters, and timing relationships that may be essential to root cause.

## 6.29 Hands-on labs

1. Use `strace -ttT` to classify a program's wait time.
2. Capture an on-CPU profile and render a flame graph.
3. Build an off-CPU profile for a lock-heavy workload.
4. Use `perf sched` to measure runnable delay.
5. Trace block I/O latency with an eBPF tool and compare with `iostat` averages.
6. Generate TCP retransmissions and observe `ss`, `nstat`, and packet capture.
7. Trigger memory reclaim and correlate PSI, `vmstat`, and request latency.
8. Create a high-cardinality eBPF map in a lab and observe memory pressure and event loss.
9. Capture a short multi-interface packet trace across a network namespace.
10. Practice an evidence-preserving incident collection bundle.

## 6.30 Principal-level summary

> I begin with customer impact and a falsifiable hypothesis, then use the least invasive tool that can locate the queue or failure boundary. I correlate service SLIs with host, cgroup, process, kernel, and dependency evidence. I separate on-CPU execution from scheduler, lock, I/O, network, and reclaim delays. I treat observability as a production system with overhead, loss, lag, and security constraints. The goal is not to collect everything; it is to gather enough trustworthy evidence to mitigate safely, explain the mechanism, and prevent recurrence.
