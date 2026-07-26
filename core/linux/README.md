# Linux Internals for Staff and Principal SREs

This is the canonical Linux curriculum shared by all interview tracks. It treats Linux as a production system and teaches reasoning from customer symptoms to kernel mechanisms, queues, evidence, mitigation, and prevention.

## Learning outcomes

By completing this module, you should be able to:

- Trace an operation from userspace through syscalls, scheduling, memory, storage, networking, security hooks, drivers, and hardware.
- Explain why a host can have high load with idle CPU, apparent free memory with OOM kills, or low throughput with severe I/O latency.
- Distinguish process, thread, namespace, cgroup, container, and virtual-machine isolation.
- Diagnose CPU saturation, scheduler delay, memory pressure, reclaim, I/O stalls, packet drops, lock contention, and kernel-level latency.
- Connect host behavior to Kubernetes requests/limits, QoS, eviction, CNI, storage, node health, and workload SLOs.
- Use `/proc`, PSI, `perf`, `strace`, `ss`, `ethtool`, `iostat`, and eBPF as hypothesis-testing tools rather than command trivia.

## Chapter map

1. [Architecture, boot, privilege boundaries, and syscalls](01-architecture-boot-syscalls.md)
2. [Processes, threads, scheduling, interrupts, and load](02-processes-scheduler.md)
3. [Virtual memory, page cache, NUMA, reclaim, and OOM](03-memory.md)
4. [VFS, filesystems, block I/O, NVMe, and latency](04-storage-io.md)
5. [Networking, namespaces, cgroups, containers, and Linux security](05-networking-containers-security.md)
6. [Observability, profiling, eBPF, and production debugging](06-observability-debugging.md)
7. [Linux incident labs and production failure scenarios](07-linux-incident-labs.md)

## Staff-level mental model

```text
application intent
      |
      v
runtime and libraries
      |
      v
system-call / exception boundary
      |
      +--> scheduler and CPU queues
      +--> virtual memory and page cache
      +--> VFS and block queues
      +--> socket and network queues
      +--> security hooks and resource controls
      |
      v
driver -> device -> firmware -> hypervisor -> hardware
```

A symptom is not a diagnosis. “The node is slow” must become a falsifiable statement such as:

- Runnable threads wait 40 ms because one CPU is overloaded by softirq processing.
- The workload is throttled by cgroup CPU quota despite idle host capacity.
- Allocating threads enter direct reclaim because the cgroup working set exceeds `memory.high`.
- Buffered writers stall behind dirty-page writeback because storage service time increased.
- Requests block in uninterruptible sleep on a failed network filesystem.

## Universal production-debugging sequence

1. **Define impact.** Which customers, workloads, nodes, zones, and SLOs are affected?
2. **Establish time.** When did it begin and what changed immediately before it?
3. **Identify the constrained domain.** Host, NUMA node, cgroup, process, device, filesystem, network namespace, or dependency.
4. **Locate the queue.** Run queue, futex, accept queue, socket buffer, dirty-page queue, block queue, reclaim, or application backlog.
5. **Separate utilization from saturation.** Busy time and queued demand are different signals.
6. **Correlate layers.** Application latency, kernel counters, container controls, Kubernetes state, and downstream behavior must form one story.
7. **Mitigate safely.** Shed load, isolate a tenant, rollback, expand capacity, or bypass a failed dependency without destroying evidence.
8. **Preserve evidence.** Capture profiles, kernel stacks, counters, logs, and timestamps before broad restarts.
9. **Prevent recurrence.** Add limits, tests, leading indicators, rollout controls, and a practiced runbook.

## Host-level USE plus latency model

| Resource | Utilization | Saturation / queue | Errors | Latency |
|---|---|---|---|---|
| CPU | busy time by mode and CPU | runnable tasks, scheduler delay, PSI CPU | machine checks, throttling | run-queue and off-CPU delay |
| Memory | working set and cache | reclaim, compaction, PSI memory | OOM and allocation failures | fault and reclaim latency |
| Storage | throughput and busy time | in-flight I/O and queue depth | resets, media errors, ENOSPC | operation and flush tails |
| Network | packets and bytes | backlog and socket queues | drops, retransmits, conntrack failures | RTT, handshake, and queue delay |

## Interview answer pattern

For any Linux question:

1. **Mechanism:** what the kernel is doing.
2. **Failure mode:** how it fails under load, skew, or partial failure.
3. **Evidence:** which counters, traces, and tools prove or reject the hypothesis.
4. **Mitigation:** how to stabilize production without destroying evidence.
5. **Prevention:** limits, architecture, tests, and observability.

Example:

> High load with idle CPU often means tasks are blocked in uninterruptible sleep rather than competing for CPU. I would separate runnable and D-state tasks, inspect PSI and per-device latency, and sample blocked kernel stacks. The immediate mitigation may be isolating a failed mount or reducing write pressure; prevention includes bounded I/O, dependency isolation, mount-timeout policy, and alerts on I/O pressure instead of load alone.

## Scope

The module focuses on modern production Linux and containerized server workloads. Commands may require elevated privileges and should be tested in disposable environments before production use.
