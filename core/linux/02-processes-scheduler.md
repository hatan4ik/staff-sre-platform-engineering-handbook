# 2. Processes, Threads, Scheduling, Interrupts, and Load

## 2.1 Linux task model

The scheduler operates on tasks. Processes and threads are represented by the same fundamental schedulable abstraction; the difference is which resources are shared.

A task may share or own:

- Virtual address space.
- File-descriptor table.
- Filesystem context.
- Signal handlers.
- Credentials.
- Namespace membership.
- Thread-group identity.

`clone()` exposes these sharing choices. Higher-level `fork()` and thread APIs build on related mechanisms.

```text
process / thread group
  shared address space
  shared open files
  shared signal dispositions
       |
       +-- task A
       +-- task B
       +-- task C
```

## 2.2 Creation, execution, exit

### fork and copy-on-write

`fork()` creates a logically separate address space, but physical pages are initially shared through copy-on-write. It is conditionally cheap, not free.

Large-memory processes may experience:

- Page-table duplication cost.
- TLB disruption.
- Copy-on-write amplification after writes.
- Latency spikes from allocation.
- Unexpected memory pressure after child creation.

### exec

`execve()` replaces the program image while preserving process identity and selected inherited resources. Security depends on controlling file descriptors, environment, credentials, interpreter paths, and executable provenance.

### zombies

A terminated child retains a minimal record until the parent collects its exit status. Zombies consume PID table entries rather than the original process memory. Growth indicates broken child reaping.

```bash
ps -eo pid,ppid,state,comm | awk '$3 ~ /Z/'
```

## 2.3 Task states

Common states:

- `R`: running or runnable.
- `S`: interruptible sleep.
- `D`: uninterruptible sleep inside a kernel path.
- `T`: stopped or traced.
- `Z`: zombie.

`D` state matters because ordinary signals generally cannot be acted upon until the kernel operation completes. Common causes include block I/O, remote filesystems, drivers, and other kernel waits.

Do not assume “disk problem” from state alone. Capture the wait channel and kernel stack.

```bash
ps -eo state,pid,ppid,wchan:32,comm | awk '$1 == "D"'
cat /proc/<pid>/stack
```

## 2.4 Context switching

A context switch saves one task's execution state and restores another's. Cost includes:

- Scheduler bookkeeping.
- Cache and branch-predictor disruption.
- TLB and address-space effects.
- Cross-CPU wakeups.
- Lost locality after migration.

Types:

- **Voluntary:** the task blocks or yields.
- **Involuntary:** the scheduler preempts it.

```bash
pidstat -w 1
vmstat 1
perf stat -e context-switches,cpu-migrations,page-faults -p <pid>
```

A high switch rate is not automatically bad. Correlate it with throughput, scheduler delay, CPU use, and tail latency.

## 2.5 Scheduling classes

Linux supports normal fair scheduling, batch/idle policies, real-time FIFO and round-robin, and deadline scheduling.

Real-time policies are dangerous when misused. A runaway high-priority task can starve ordinary workloads and operational access. Use reservations, affinity, watchdogs, and a tested rollback path.

## 2.6 Run queues and fairness

Normal tasks are distributed across per-CPU run queues. The scheduler attempts to allocate CPU according to weights while balancing locality and fairness.

Key principles:

- Nice values influence relative weight, not fixed percentages.
- Per-CPU queues reduce global coordination.
- Load balancing can trade cache locality for fairness.
- Wakeup placement affects latency.
- Cgroup controls create hierarchical competition.

Do not overfit interview answers to one kernel version's exact data structure. Explain invariants and observable behavior.

## 2.7 Utilization versus saturation

Utilization is busy time. Saturation is queued demand.

A CPU may be:

- Highly utilized without harmful queueing.
- Moderately utilized while one hot core is saturated.
- Globally idle while a cgroup is throttled.
- Idle while tasks wait on I/O, locks, or memory.

Evidence:

```bash
mpstat -P ALL 1
pidstat -u -t 1
cat /proc/loadavg
cat /proc/pressure/cpu
top -H
```

Look for per-CPU skew, run-queue delay, steal time, softirq concentration, quota throttling, and CPU affinity.

## 2.8 Load average

Linux load average includes runnable tasks and tasks in uninterruptible sleep. It is not direct CPU utilization.

Consequences:

- High load with idle CPU can be caused by many D-state tasks.
- A burst remains visible because the metric is smoothed.
- A value of 8 differs radically on 2 CPUs versus 128 CPUs.
- Container-visible load may not represent only that container.

Strong answer:

> I interpret load alongside CPU count, runnable tasks, D-state tasks, PSI, and the latency of the suspected resource. I do not alert on load alone.

## 2.9 Affinity and NUMA locality

Affinity can improve cache and memory locality, but static pinning can also create hot cores and stranded capacity.

```bash
taskset -cp <pid>
numactl --hardware
numastat -p <pid>
cat /proc/<pid>/status | grep -E 'Cpus_allowed|Mems_allowed'
```

End-to-end locality may involve:

```text
NIC queue -> IRQ CPU -> softirq CPU -> application CPU -> NUMA-local memory
```

Common mistakes:

- Pinning application threads and interrupts to the same CPU.
- Using quotas without topology awareness.
- Creating thread pools larger than the effective CPU allocation.
- Moving CPU affinity without considering memory placement.

## 2.10 cgroup v2 CPU controls

Important controls:

- CPU weight: relative share during contention.
- CPU quota/period: hard bandwidth limit.
- Cpuset: eligible CPUs and memory nodes.

A multithreaded process may consume its quota early in a period and then be throttled even while other host CPUs are idle.

```bash
cat /sys/fs/cgroup/<group>/cpu.stat
cat /sys/fs/cgroup/<group>/cpu.max
cat /sys/fs/cgroup/<group>/cpu.pressure
```

In Kubernetes, tight CPU limits can produce severe p99 latency despite moderate average usage. Monitor throttled periods and throttled time.

## 2.11 Interrupts and softirqs

Devices generate hardware interrupts. The kernel acknowledges them and commonly defers heavier work.

Network RX/TX, timers, and other deferred work can run as softirqs. When immediate processing cannot keep up, `ksoftirqd` threads process the backlog.

```bash
watch -n1 'grep -E "NET_RX|NET_TX|TIMER" /proc/softirqs'
watch -n1 'grep -E "eth|ens|enp|nvme" /proc/interrupts'
```

Poor IRQ or RSS configuration can overload one core while others appear idle.

## 2.12 Frequency, thermal limits, and steal

A host can be 100% busy yet deliver less compute because of:

- Reduced frequency.
- Thermal or power throttling.
- Hypervisor steal.
- SMT sibling interference.
- Changed CPU allocation.

```bash
lscpu
mpstat 1
journalctl -k | grep -iE 'thermal|thrott|mce|hardware error'
```

Compare achieved work per CPU-second, not only utilization.

## 2.13 Lock contention and futexes

Most userspace mutexes avoid syscalls while uncontended. Under contention, futex operations allow waiters to sleep.

Symptoms:

- Low throughput with incomplete CPU use.
- High tail latency.
- Threads blocked in futex waits.
- One owner thread hot or stalled.

```bash
strace -f -e futex -p <pid>
perf lock record -- <command>
perf lock report
perf sched record -p <pid> -- sleep 10
perf sched latency
```

Fixes include shortening critical sections, sharding locks, reducing oversubscription, or removing a serialized dependency. Adding CPUs can worsen contention.

## 2.14 Scheduler latency

CPU utilization does not show how long a runnable task waited before executing.

Potential causes:

- Oversubscription.
- Real-time interference.
- IRQ/softirq storms.
- Cgroup throttling.
- Affinity mistakes.
- VM steal.
- Long nonpreemptible kernel sections.

Use `perf sched`, run-queue eBPF tools, PSI, and request-trace correlation.

## 2.15 Incident: high p99 with normal average CPU

### Symptoms

- p50 unchanged.
- p99 rises from 100 ms to 2 s.
- Host CPU averages 45%.
- Downstream latency is normal.

### Investigation

1. Inspect per-CPU and per-thread behavior.
2. Check cgroup `cpu.stat`.
3. Measure run-queue delay.
4. Inspect IRQ/softirq distribution.
5. Compare slow requests with quota periods.

Likely finding: a low CPU quota is consumed by burst concurrency, then all threads are throttled until the next period.

Mitigation: raise/remove the invalid limit, reduce concurrency, or move the workload to a suitable service class.

Prevention: alert on throttled time and CPU PSI; test bursty load rather than only steady averages.

## 2.16 Incident: high load and idle CPU

### Symptoms

- Load 80 on a 32-vCPU node.
- CPU 70% idle.
- Requests hang.

```bash
ps -eo state,pid,wchan:32,comm | sort
cat /proc/pressure/io
cat /proc/pressure/memory
iostat -xz 1
```

Capture blocked stacks. A cluster of tasks in an NFS or block-driver path points away from CPU.

Mitigate by fencing or isolating the dependency, stopping new work, and preserving evidence. Prevent with bounded remote-filesystem dependencies, leading indicators, and tested failure behavior.

## 2.17 Interview drills

### Process versus thread?

Both are schedulable tasks. Threads share selected resources such as address space and descriptors; separate processes generally do not.

### Why can more threads reduce throughput?

Oversubscription increases queueing, cache misses, lock contention, memory footprint, and scheduler work. Optimal concurrency is bounded by actual parallelism and downstream capacity.

### How can CPU be idle while a workload is CPU-throttled?

A cgroup can exhaust its quota for the period and be throttled despite spare host capacity.

### Why is per-CPU analysis mandatory?

Global averages hide hot cores, IRQ concentration, single-thread limits, affinity mistakes, and NUMA-local saturation.

## 2.18 Principal-level summary

> I separate CPU utilization from runnable demand, scheduler delay, softirq work, lock waits, and cgroup throttling. I inspect per-CPU behavior because global averages hide the queue that matters. I tune only after I have located and measured that queue.