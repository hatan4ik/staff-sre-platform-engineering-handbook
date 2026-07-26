# Chapter 7 — Linux Incident Labs and Production Failure Scenarios

This chapter turns Linux knowledge into production judgment. The goal is not to memorize commands. The goal is to move from customer impact to a falsifiable kernel-level hypothesis, gather evidence, mitigate safely, and prevent recurrence.

## The incident reasoning model

```text
customer impact
      |
      v
application symptom
      |
      v
queue or pressure point
      |
      v
kernel mechanism
      |
      v
hardware, platform, or dependency
```

A Staff-level response should always answer five questions:

1. **Impact:** Who is affected, and which SLO is burning?
2. **Mechanism:** What is the kernel or network stack doing?
3. **Evidence:** Which counters, stacks, traces, or queues prove it?
4. **Mitigation:** How do we stabilize production without destroying evidence?
5. **Prevention:** What architectural, operational, or observability change prevents recurrence?

---

## Incident 1 — CPU is low, but the service is effectively dead

### Scenario

API latency rises from 22 ms to 4.8 s. CPU remains below 20 percent. Memory and network throughput look normal. Load average is above 40.

### Why this confuses people

Linux load average is not CPU utilization. It includes runnable tasks and tasks in uninterruptible sleep, typically `D` state.

### Evidence

```bash
uptime
ps -eo state,pid,comm,wchan:32 | awk '$1 == "D"'
cat /proc/pressure/io
cat /proc/<pid>/stack
journalctl -k --since '-20 min'
```

Typical blocked stack:

```text
nfs_wait_bit_killable
rpc_execute
schedule
```

### Diagnosis

Requests are not waiting for CPU. They are blocked inside the kernel on a stalled NFS, EBS, SAN, iSCSI, or other block-backed dependency.

### Safe mitigation

- Shift traffic away from affected nodes.
- Stop new work that touches the failed mount.
- Isolate or lazily unmount the dead filesystem only after preserving evidence.
- Avoid blind restarts; they may reproduce the stall during startup and erase useful process state.

### Prevention

- Dependency-specific timeouts and bounded retries.
- Separate critical request paths from network filesystems.
- Alert on PSI I/O and blocked-task growth, not load average alone.
- Test failover behavior for storage and mount dependencies.

### Interview answer

> High load with low CPU usually means many tasks are blocked rather than executing. I would distinguish runnable from `D`-state tasks, inspect PSI and blocked kernel stacks, then correlate them with device, mount, and kernel error data.

---

## Incident 2 — Kubernetes node is Ready, but pods time out

### Scenario

The node reports `Ready`. CPU is 30 percent and memory is 40 percent, yet users receive 504 errors during a traffic spike.

### Evidence

```bash
ss -s
ss -lnt
nstat -az | egrep 'ListenOverflows|ListenDrops|Syncookies'
sysctl net.core.somaxconn
sysctl net.ipv4.tcp_max_syn_backlog
```

A suspicious listener may show a full receive queue, while kernel counters show listen overflows.

### Mechanism

Two queues matter:

- **SYN backlog:** half-open handshakes.
- **Accept queue:** completed handshakes waiting for the application to call `accept()`.

A healthy node status does not imply healthy socket queues.

### Diagnosis

Traffic growth exceeds application accept capacity. The backlog fills, new connections are dropped or delayed, and upstream proxies surface timeouts.

### Safe mitigation

- Add replicas or shift load.
- Increase backlog settings only if the application can actually drain them.
- Reduce connection churn with keep-alive and connection pooling.
- Protect the service with admission control or load shedding.

### Prevention

- Autoscale on request concurrency or queue depth, not CPU alone.
- Load test handshake and accept behavior.
- Expose listen-overflow counters as service health signals.

---

## Incident 3 — Pod is OOMKilled while the host has free memory

### Scenario

The node has tens of gigabytes available, but a container is repeatedly `OOMKilled`.

### Evidence

```bash
kubectl describe pod <pod>
cat /sys/fs/cgroup/memory.current
cat /sys/fs/cgroup/memory.max
cat /sys/fs/cgroup/memory.events
cat /sys/fs/cgroup/memory.stat
```

### Mechanism

The host and the cgroup have different memory boundaries. A process can exceed `memory.max` even when the machine has substantial free memory.

### Diagnosis

The workload crosses its cgroup limit. The cgroup OOM path selects and kills a process within that control group.

### Safe mitigation

- Raise the limit only if capacity and node placement support it.
- Reduce concurrency or disable memory-heavy features.
- Roll back a version with an expanded working set.
- Capture heap, allocation, and cgroup evidence before restarting everything.

### Prevention

- Set requests from observed steady-state working set and limits from tested burst behavior.
- Distinguish leak, cache growth, burst allocation, and page-cache charge.
- Alert on `memory.events`, `memory.current / memory.max`, and PSI memory.

### Interview answer

> Kubernetes can kill a process while the host still has free RAM because cgroups enforce local limits independently of host-wide availability.

---

## Incident 4 — Disk utilization looks low, but the database is slow

### Scenario

Disk busy time is only 10 percent, yet database latency is high and commits stall.

### Evidence

```bash
iostat -xz 1
pidstat -d 1
cat /proc/pressure/io
lsblk -o NAME,SCHED,ROTA,DISC-MAX,DISC-GRAN
```

Focus on:

- `await`
- queue depth
- operation size
- read/write asymmetry
- flush and fsync behavior
- cloud-volume throttling metrics

### Mechanism

Utilization is not the same as latency. Cloud devices may throttle IOPS, bandwidth, burst credits, or flush operations while average busy time appears modest.

### Diagnosis

The database is blocked on high-latency storage operations, commonly WAL or fsync paths.

### Safe mitigation

- Reduce write pressure.
- Move WAL or journal traffic to a lower-latency device.
- Increase provisioned IOPS or throughput.
- Batch writes where durability requirements allow.

### Prevention

- Monitor latency percentiles and queue depth, not `%util` alone.
- Capacity-test sync-heavy workloads.
- Separate data, logs, and temporary I/O when failure domains and cost permit.

---

## Incident 5 — Conntrack exhaustion causes random packet loss

### Scenario

Pods intermittently fail to connect. CPU and memory look healthy. Failures are uneven and difficult to reproduce.

### Evidence

```bash
conntrack -S
sysctl net.netfilter.nf_conntrack_count
sysctl net.netfilter.nf_conntrack_max
dmesg | grep -i conntrack
```

### Mechanism

Stateful packet processing tracks flows in the conntrack table. When the table reaches capacity, new flows may be dropped.

### Diagnosis

High connection churn, poor connection reuse, NAT fan-out, or long timeouts fill conntrack faster than entries expire.

### Safe mitigation

- Increase table capacity only after checking memory cost.
- Reduce idle timeouts where appropriate.
- Enable connection reuse, keep-alive, HTTP/2, or multiplexing.
- Shift traffic from saturated nodes.

### Prevention

- Alert on occupancy ratio and insertion failures.
- Capacity-model NAT and connection churn.
- Avoid per-request TCP connections for high-QPS internal services.

---

## Incident 6 — CPU throttling with idle capacity on the host

### Scenario

A latency-sensitive pod suffers periodic pauses. Node CPU is below 50 percent.

### Evidence

```bash
cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/cpu.stat
cat /proc/pressure/cpu
kubectl top pod
```

Look for increasing `nr_throttled` and `throttled_usec`.

### Mechanism

CFS bandwidth control enforces a cgroup quota over a period. A container can consume its quota quickly and then be throttled until the next period, even when other CPUs are idle.

### Diagnosis

The service is quota-bound, not host-capacity-bound.

### Safe mitigation

- Raise or remove the CPU limit for latency-sensitive services.
- Reduce concurrency or expensive work per request.
- Move the workload to a less-contended node pool.

### Prevention

- Avoid restrictive CPU limits for critical low-latency workloads unless required.
- Monitor cgroup throttling directly.
- Test burst behavior, not only average CPU usage.

---

## Incident 7 — Softirq saturation creates a hidden single-core bottleneck

### Scenario

Overall CPU appears moderate, but one CPU is saturated and application latency spikes under network load.

### Evidence

```bash
mpstat -P ALL 1
cat /proc/softirqs
cat /proc/interrupts
ethtool -S <iface>
ps -eo pid,psr,comm | grep ksoftirqd
```

### Mechanism

Receive processing may concentrate on one queue or CPU because of IRQ affinity, RSS configuration, flow hashing, or disabled RPS/RFS.

### Diagnosis

Packet processing is imbalanced. One CPU spends most of its time handling network softirqs while application threads wait.

### Safe mitigation

- Rebalance IRQ affinity.
- Validate RSS queue count and queue-to-CPU mapping.
- Enable or tune RPS/RFS where appropriate.
- Scale out traffic or reduce packet rate.

### Prevention

- Monitor per-CPU softirq time and NIC queue drops.
- Align queues, IRQs, and NUMA locality.
- Load test packets per second, not only bits per second.

---

## Incident 8 — DNS storm after a dependency failure

### Scenario

A downstream service becomes unavailable. Soon afterward, node-local DNS and application latency collapse.

### Evidence

```bash
ss -uapn
conntrack -L -p udp 2>/dev/null | wc -l
tcpdump -ni any port 53
kubectl top pods -n kube-system
```

### Mechanism

Retry loops trigger repeated DNS lookups. Short TTLs, disabled caching, synchronized retries, and UDP loss amplify load.

### Diagnosis

The original dependency failure causes a retry-and-resolution storm that becomes a second outage.

### Safe mitigation

- Apply exponential backoff and jitter.
- Reduce retry concurrency.
- Restore caching or use node-local DNS caching.
- Shed noncritical traffic.

### Prevention

- Bound retries by time and budget.
- Cache both positive and appropriate negative responses.
- Load test DNS behavior during dependency failure.

---

## Incident 9 — Ephemeral port exhaustion

### Scenario

A proxy or NAT gateway cannot establish new outbound connections despite healthy downstream services.

### Evidence

```bash
sysctl net.ipv4.ip_local_port_range
ss -tan state time-wait | wc -l
ss -tan state established | wc -l
cat /proc/net/sockstat
```

### Mechanism

Each outbound connection consumes a local tuple. High churn, long `TIME_WAIT`, and a narrow ephemeral port range can exhaust available tuples.

### Diagnosis

The client side runs out of usable source ports for a particular destination pattern.

### Safe mitigation

- Reuse connections.
- Add source IPs or scale out clients.
- Widen the ephemeral range where safe.
- Reduce unnecessary retries.

### Prevention

- Prefer pools and multiplexed protocols.
- Capacity-model tuples per destination.
- Monitor socket-state growth.

---

## Incident 10 — Page-cache thrashing and reclaim stalls

### Scenario

A node has no obvious memory leak, yet latency rises as multiple large file-processing jobs run concurrently.

### Evidence

```bash
vmstat 1
cat /proc/pressure/memory
sar -B 1
cat /proc/vmstat | egrep 'pgscan|pgsteal|workingset|allocstall'
```

### Mechanism

Competing working sets exceed available memory. The kernel repeatedly evicts and refaults pages, while allocating threads enter reclaim.

### Diagnosis

The system is thrashing between active datasets rather than progressing efficiently.

### Safe mitigation

- Reduce concurrency.
- Isolate batch and latency-sensitive workloads.
- Increase memory or shrink per-job working set.

### Prevention

- Track refault and PSI signals.
- Use cgroup memory controls to prevent one workload from destabilizing the node.
- Schedule large jobs with memory-aware admission control.

---

## Incident 11 — NUMA imbalance produces remote-memory latency

### Scenario

A large in-memory service has enough CPU and RAM, but tail latency worsens after a deployment or CPU pinning change.

### Evidence

```bash
numactl --hardware
numastat -p <pid>
cat /proc/<pid>/numa_maps
perf stat -e node-loads,node-load-misses -p <pid> -- sleep 10
```

### Mechanism

Threads execute on one NUMA node while frequently accessing memory allocated on another. Remote access increases latency and consumes interconnect bandwidth.

### Diagnosis

CPU and memory placement are mismatched.

### Safe mitigation

- Align CPU affinity with memory locality.
- Rebalance or restart under corrected placement policy.
- Avoid pinning that ignores NUMA topology.

### Prevention

- NUMA-aware scheduling and benchmarking.
- Expose locality metrics for large memory-bound services.
- Validate huge-page and allocator behavior under placement constraints.

---

## Incident 12 — Inode exhaustion despite free disk space

### Scenario

Applications receive `No space left on device`, but `df -h` shows plenty of free capacity.

### Evidence

```bash
df -h
df -i
find /var -xdev -type f | wc -l
```

### Mechanism

A filesystem can exhaust inodes before exhausting data blocks, commonly because of millions of tiny files.

### Diagnosis

Metadata capacity, not byte capacity, is exhausted.

### Safe mitigation

- Remove safe temporary files.
- Rotate or compact pathological file sets.
- Redirect writes to a filesystem with available inodes.

### Prevention

- Monitor inode consumption.
- Avoid file-per-event designs at high scale.
- Select filesystem geometry appropriate to object count.

---

## Incident 13 — File-descriptor leak

### Scenario

A service degrades over hours and eventually fails to accept sockets or open files.

### Evidence

```bash
cat /proc/<pid>/limits | grep 'open files'
ls /proc/<pid>/fd | wc -l
lsof -p <pid> | awk '{print $5}' | sort | uniq -c
cat /proc/sys/fs/file-nr
```

### Mechanism

The process leaks descriptors or retains connections beyond their intended lifetime until it hits `RLIMIT_NOFILE` or system-wide limits.

### Safe mitigation

- Shed traffic and roll instances gradually.
- Increase limits only as temporary headroom.
- Capture descriptor type and stack evidence before restart.

### Prevention

- Track open descriptors by type.
- Add lifecycle tests and leak detection.
- Enforce bounded pools and idle cleanup.

---

## Incident 14 — Overlay MTU mismatch

### Scenario

Small requests work, but larger payloads hang or retransmit across Kubernetes nodes.

### Evidence

```bash
ip link
ip route get <destination>
tracepath <destination>
ping -M do -s 1400 <destination>
tcpdump -ni any 'icmp or tcp'
```

### Mechanism

VXLAN, Geneve, IPsec, or other encapsulation consumes header space. If pod MTU does not account for underlay MTU, larger packets fragment or disappear when Path MTU Discovery is broken.

### Diagnosis

The effective path MTU is smaller than endpoints assume.

### Safe mitigation

- Correct CNI or interface MTU.
- Allow required ICMP messages.
- Apply MSS clamping only as a deliberate compatibility measure.

### Prevention

- Standardize underlay and overlay MTU policy.
- Include large-payload and cross-node tests in network validation.

---

## Incident 15 — Lock contention with low CPU utilization

### Scenario

A multithreaded service has low CPU but poor throughput. Adding replicas helps; adding threads does not.

### Evidence

```bash
perf lock record -p <pid> -- sleep 20
perf lock report
perf sched record -p <pid> -- sleep 20
perf sched latency
```

For userspace runtimes, add language-specific contention profiling.

### Mechanism

Threads serialize on a mutex, futex, allocator lock, or shared data structure. They spend time sleeping or spinning rather than executing useful work.

### Diagnosis

Concurrency exists in configuration but not in the critical path.

### Safe mitigation

- Reduce pathological concurrency.
- Shard the contested resource.
- Roll back a contention-inducing change.

### Prevention

- Include lock and off-CPU profiling in performance tests.
- Prefer partitioned state over globally shared hot structures.

---

## Integrated incident workflow

### First five minutes

```bash
uptime
vmstat 1
mpstat -P ALL 1
pidstat -durwt 1
cat /proc/pressure/cpu
cat /proc/pressure/memory
cat /proc/pressure/io
ss -s
iostat -xz 1
```

Do not run every command blindly. Use this set to identify the pressured domain and then narrow the investigation.

### Queue-first decision tree

```text
Latency up?
  |
  +-- runnable queue growing? ------> scheduler, CPU quota, hot core
  |
  +-- blocked tasks growing? -------> storage, NFS, reclaim, locks
  |
  +-- socket queues growing? -------> accept rate, downstream slowness
  |
  +-- retransmits/drops growing? ---> congestion, MTU, NIC, conntrack
  |
  +-- PSI memory rising? -----------> reclaim, thrash, cgroup pressure
  |
  +-- block await rising? ---------> device latency, throttling, flushes
```

---

## Hands-on labs

Run these only in disposable environments.

### Lab 1 — Observe CPU pressure

Use `stress-ng` to create more runnable workers than CPUs, then compare CPU utilization, run-queue length, scheduler delay, and PSI CPU.

```bash
stress-ng --cpu 8 --timeout 60s
vmstat 1
cat /proc/pressure/cpu
```

### Lab 2 — Trigger cgroup CPU throttling

Create a cgroup with a restrictive `cpu.max`, run a CPU-heavy process, and observe `cpu.stat`.

### Lab 3 — Reproduce cgroup memory pressure

Apply a small `memory.max`, allocate memory gradually, and inspect `memory.events`, PSI, and OOM behavior.

### Lab 4 — Fill the accept queue

Run a deliberately slow server with a small backlog, generate connection bursts, and observe listen-overflow counters.

### Lab 5 — Simulate packet loss and latency

```bash
tc qdisc add dev eth0 root netem delay 100ms loss 2%
```

Observe retransmissions, RTT, application timeout behavior, and retry amplification. Remove the rule afterward:

```bash
tc qdisc del dev eth0 root
```

### Lab 6 — Create inode pressure

Use a small disposable filesystem, create many tiny files, and compare `df -h` with `df -i`.

### Lab 7 — Measure lock contention

Run a workload with a single shared lock, then compare throughput and off-CPU time as threads increase.

---

## Staff and Principal interview drills

1. Why can Linux show load 80 with CPU at 10 percent?
2. What is the operational difference between a runnable task and a task in `D` state?
3. Why can a pod be OOMKilled while the host has free memory?
4. Explain SYN backlog versus accept queue.
5. How does conntrack exhaustion appear from the application layer?
6. Why can storage latency be severe while `%util` looks low?
7. How would you prove CPU quota throttling?
8. Why can one hot softirq CPU bottleneck a multicore host?
9. How do retries turn one dependency failure into a DNS or connection storm?
10. Why do MTU problems often affect only large requests?
11. How do you distinguish a memory leak from page-cache thrashing?
12. What evidence proves NUMA locality is hurting performance?
13. How do you investigate a file-descriptor leak without immediately restarting?
14. What would make increasing a backlog harmful rather than helpful?
15. Which evidence must be preserved before mitigation?

---

## Principal-level incident answer template

> I would start from impact and time correlation, then identify the constrained scope: process, cgroup, node, device, namespace, or dependency. Next I would locate the queue rather than relying on average utilization. I would use PSI, scheduler, socket, block, and cgroup evidence to test a small number of hypotheses. The immediate mitigation should reduce customer harm while preserving state. The long-term fix should remove the unbounded queue, retry loop, shared bottleneck, or missing resource control that allowed the failure to amplify.

## Completion criteria

You have mastered this chapter when you can:

- Explain each incident from kernel mechanism to user impact.
- Name the minimum evidence required to prove the diagnosis.
- Separate mitigation from root-cause correction.
- Describe at least one dangerous but tempting response.
- Connect Linux evidence to Kubernetes and service-level behavior.
