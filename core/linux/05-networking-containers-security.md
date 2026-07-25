# 5. Linux Networking, Namespaces, Cgroups, Containers, and Security

This chapter explains the Linux primitives beneath container platforms and Kubernetes. The goal is not to memorize commands. The goal is to trace packet flow, identify the exact queue or policy boundary involved, and reason about how isolation, resource control, and security interact under production load.

## 5.1 Principal-level mental model

```text
application process
  |
  +--> socket API
  |
  +--> network namespace
  |      +--> route table
  |      +--> neighbor table
  |      +--> conntrack / policy
  |      +--> veth / bridge / overlay
  |
  +--> cgroup resource and BPF hooks
  |
  +--> host network stack
  |
  +--> qdisc / driver / NIC queues
  |
  +--> physical or virtual network
```

A container is not a lightweight virtual machine. It is a set of ordinary Linux processes with selected namespace membership, cgroup membership, credentials, capabilities, filesystem views, seccomp policy, and LSM policy.

The practical implication is simple:

> When a pod cannot connect, the failure can be in the application, socket state, namespace route, neighbor resolution, policy, conntrack, bridge, overlay, host route, NIC queue, or external network. Debug the path in order.

---

## 5.2 From application syscall to wire

For a TCP client, the simplified path is:

```text
connect()
  -> socket lookup and route decision
  -> source address and ephemeral port selection
  -> neighbor resolution if required
  -> SYN queued for transmission
  -> qdisc
  -> driver TX ring
  -> NIC DMA
  -> network
```

For receive:

```text
NIC RX ring
  -> interrupt / NAPI poll
  -> skb creation or reuse
  -> protocol processing
  -> routing / policy / conntrack
  -> socket lookup
  -> socket receive queue
  -> application recv()
```

Important distinction:

- The network may have delivered the packet to the host.
- The application may still not have consumed it.
- Socket receive queue growth therefore indicates a different bottleneck from NIC drops or retransmissions.

Useful commands:

```bash
ss -s
ss -lntp
ss -tin
ip -s link
ethtool -S <iface>
cat /proc/net/softnet_stat
```

---

## 5.3 NICs, DMA, interrupts, and NAPI

Modern NICs use descriptor rings shared with the kernel. The NIC performs DMA to move packet data without the CPU copying every byte.

### Receive path

1. Driver prepares receive descriptors.
2. NIC DMA-writes packet data into memory.
3. NIC signals the CPU.
4. Driver schedules NAPI polling.
5. Kernel processes packets in batches.
6. If budget is exceeded, work continues through softirq context.

NAPI reduces interrupt storms by switching from interrupt-driven notification to bounded polling under load.

Failure patterns:

- RX ring exhaustion.
- Softirq CPU concentrated on one core.
- NAPI budget insufficient for offered packet rate.
- Driver drops before the IP stack.
- NUMA mismatch between NIC, IRQ CPU, and application memory.

Evidence:

```bash
cat /proc/interrupts
cat /proc/softirqs
mpstat -P ALL 1
ethtool -g <iface>
ethtool -l <iface>
ethtool -S <iface>
```

A Staff-level answer should ask where packets are dropped:

```text
switch -> NIC -> driver ring -> softnet backlog -> IP stack -> conntrack -> socket queue -> application
```

Each layer has different counters and mitigations.

---

## 5.4 RSS, RPS, RFS, and XPS

### RSS

Receive Side Scaling distributes flows across hardware receive queues, commonly by hashing the flow tuple.

Benefits:

- Parallel packet processing.
- Reduced single-core bottlenecks.
- Better scaling on multi-queue NICs.

Risks:

- Poor queue-to-CPU affinity.
- One elephant flow remains pinned to one queue.
- NUMA-remote processing.
- IRQ and application contention on the same CPU.

### RPS

Receive Packet Steering distributes receive processing in software after the packet enters the kernel.

Useful when hardware queues are insufficient, but it adds cross-CPU coordination.

### RFS

Receive Flow Steering attempts to steer processing toward the CPU consuming the flow.

### XPS

Transmit Packet Steering selects transmit queues based on CPU or receive-queue mapping.

Do not enable every mechanism blindly. Validate:

- Per-queue packet rate.
- Per-CPU softirq time.
- Cache locality.
- NUMA locality.
- Tail latency.

---

## 5.5 Offloads: GRO, LRO, GSO, TSO, checksum

Offloads reduce per-packet CPU cost.

- **GRO:** combines received packets in the kernel.
- **LRO:** hardware-oriented receive coalescing; not always compatible with forwarding use cases.
- **GSO:** lets the kernel carry large logical packets until later segmentation.
- **TSO:** NIC performs TCP segmentation.
- **Checksum offload:** checksum generation or validation is delegated.

Operational consequences:

- Packet captures on the host may show packets larger than wire MTU.
- A capture can appear to have invalid checksums because hardware has not filled them yet.
- Offload settings can affect overlays, firewalls, and performance.

```bash
ethtool -k <iface>
ethtool -K <iface> gro off gso off tso off  # lab only; understand impact
```

Never disable offloads in production merely to make packet captures easier without measuring CPU and throughput impact.

---

## 5.6 The socket lifecycle and queues

A listening TCP socket has two conceptually important queues:

- Incomplete handshakes.
- Established connections waiting for `accept()`.

Application symptoms can differ:

- SYN retransmissions: handshake path may be overloaded or filtered.
- Established connections but high accept latency: application accept loop is slow.
- Large receive queues: application is not reading fast enough.
- Large send queues: peer or network cannot drain data fast enough.

```bash
ss -lnt
ss -nt state syn-recv
ss -nt state established
ss -tinp
```

Key tunables exist, but tuning without identifying the queue only delays failure.

### Ephemeral ports

Outbound TCP connections require a source port. High churn can exhaust usable tuples, especially behind NAT.

Check:

```bash
sysctl net.ipv4.ip_local_port_range
ss -tan state time-wait | wc -l
cat /proc/sys/net/ipv4/tcp_tw_reuse
```

Do not treat TIME_WAIT as a bug. It protects protocol correctness. The right fix may be connection reuse, pooling, HTTP/2, reduced churn, more source IPs, or NAT scaling.

---

## 5.7 TCP state, retransmissions, and congestion control

TCP provides reliable ordered delivery, not fixed latency.

Important mechanisms:

- Three-way handshake.
- Sequence numbers and acknowledgements.
- Retransmission timeout.
- Fast retransmit.
- Congestion window.
- Receive window.
- Slow start.
- Congestion avoidance.
- Selective acknowledgement.

A retransmission can mean:

- Actual packet loss.
- Reordering.
- Receiver overload.
- Delayed acknowledgement behavior.
- Buffer pressure.
- Middlebox interference.

Useful evidence:

```bash
ss -ti
nstat -az | grep -E 'TcpRetransSegs|TcpExtTCPSynRetrans|ListenOverflows|ListenDrops'
sar -n TCP,ETCP 1
tcpdump -nn -i <iface> host <peer>
```

### CUBIC versus BBR

CUBIC is loss-based and widely used. BBR models bottleneck bandwidth and round-trip propagation time.

Do not answer “BBR is always faster.” Evaluate:

- Fairness.
- Buffering.
- RTT mix.
- Traffic policing.
- Kernel support.
- Interaction with application pacing and cloud networks.

---

## 5.8 MTU, fragmentation, PMTUD, and overlays

Encapsulation adds headers. A pod packet that fits the pod-interface MTU may exceed the underlay MTU after VXLAN, Geneve, IPsec, or WireGuard headers are added.

Symptoms of MTU mismatch:

- Small requests work; large responses hang.
- TLS handshake stalls after initial packets.
- ICMP works but application traffic fails.
- One network path fails while another succeeds.

Checks:

```bash
ip link show
ip route get <destination>
tracepath <destination>
ping -M do -s <size> <destination>
tcpdump -nn -i any 'icmp or icmp6'
```

Path MTU Discovery depends on relevant ICMP messages being delivered. Blocking all ICMP can create black holes.

---

## 5.9 Routing and policy routing

Linux route selection considers:

- Destination prefix.
- Routing table.
- Policy rules.
- Source address.
- Interface.
- Metric.
- Scope and protocol.

```bash
ip rule
ip route show table all
ip route get <destination> from <source>
```

In multi-homed systems, asymmetric routing can break stateful firewalls and conntrack assumptions.

Principal-level debugging sequence:

1. Resolve destination address.
2. Inspect route from the actual source namespace.
3. Verify neighbor resolution.
4. Check policy and conntrack.
5. Confirm egress interface and source address.
6. Capture both directions.

---

## 5.10 Neighbor discovery: ARP and NDP

IPv4 commonly uses ARP; IPv6 uses Neighbor Discovery.

A valid route does not guarantee a usable next hop. Neighbor state can be incomplete, failed, stale, or delayed.

```bash
ip neigh show
ip -6 neigh show
arping -I <iface> <address>
```

Large L2 domains, broken proxy ARP, duplicate IPs, exhausted neighbor tables, or silent network appliances can produce intermittent connectivity.

---

## 5.11 Network namespaces

A network namespace provides separate instances of:

- Interfaces.
- Routes.
- Neighbor tables.
- Sockets.
- Netfilter state.
- Selected sysctls.

```bash
ip netns add lab
ip netns exec lab ip addr
ip netns exec lab ip route
```

A process sees the network namespace it belongs to. Debugging only from the host namespace can miss pod-local routes, DNS configuration, or firewall rules.

To inspect a process namespace:

```bash
nsenter -t <pid> -n ip addr
nsenter -t <pid> -n ip route
nsenter -t <pid> -n ss -lntp
```

---

## 5.12 veth pairs and Linux bridges

A veth pair acts like a virtual cable. Packets entering one end emerge from the other.

Typical container path:

```text
container eth0
   |
   | veth pair
   v
host-side veth
   |
   v
Linux bridge or eBPF datapath
   |
   v
host route / overlay / physical NIC
```

A Linux bridge forwards Ethernet frames based on MAC learning.

```bash
ip link
bridge link
bridge fdb show
bridge vlan show
```

Failure modes:

- Host-side veth down.
- Missing bridge membership.
- Stale FDB entry.
- VLAN mismatch.
- MTU mismatch.
- CNI cleanup failure leaving orphan interfaces.

---

## 5.13 VXLAN, Geneve, and overlays

Overlay networks encapsulate tenant or pod traffic inside underlay packets.

Benefits:

- Address-space abstraction.
- Cross-subnet workload networking.
- Separation from underlay routing.

Costs:

- Encapsulation overhead.
- Reduced effective MTU.
- Additional control-plane state.
- More difficult packet attribution.
- Potential hotspotting at tunnel endpoints.

Debug both layers:

```text
inner packet: pod -> service/backend
outer packet: node -> remote node
```

A correct inner route is insufficient if the outer route, tunnel endpoint, VNI, or security policy is wrong.

---

## 5.14 Netfilter, nftables, iptables, and conntrack

Netfilter provides hooks through the packet path. iptables and nftables are user-facing rule systems built on that framework.

Conntrack records flow state for stateful firewalling and NAT.

Common failure modes:

- Conntrack table exhaustion.
- Hash pressure and high lookup cost.
- NAT tuple exhaustion.
- Rule explosion.
- Conflicting rule managers.
- Asymmetric routing causing invalid state.

```bash
conntrack -S
conntrack -L 2>/dev/null | head
sysctl net.netfilter.nf_conntrack_count
sysctl net.netfilter.nf_conntrack_max
nft list ruleset
iptables-save
```

Do not raise `nf_conntrack_max` without checking memory cost, hash sizing, flow churn, and the root cause of connection growth.

---

## 5.15 Linux namespaces beyond networking

Containers commonly use:

- **PID namespace:** isolated process IDs and namespace-local PID 1.
- **Mount namespace:** separate mount view.
- **UTS namespace:** hostname/domain identity.
- **IPC namespace:** SysV IPC and POSIX message queue isolation.
- **Network namespace:** interfaces, routes, sockets, and policy.
- **User namespace:** maps namespace IDs to host IDs.
- **Cgroup namespace:** virtualized cgroup view.
- **Time namespace:** selected clock offsets on supported systems.

Namespaces isolate views, not necessarily resource consumption. Resource control is primarily a cgroup responsibility.

---

## 5.16 Cgroups v2

Cgroups organize processes into a hierarchy for accounting, limits, and control.

Major controllers include:

- CPU.
- Memory.
- I/O.
- PIDs.
- Cpuset.
- HugeTLB.
- RDMA.

### CPU

```bash
cat cpu.max
cat cpu.weight
cat cpu.stat
cat cpu.pressure
```

Quota can create burst throttling even when the host has idle CPUs.

### Memory

```bash
cat memory.current
cat memory.high
cat memory.max
cat memory.events
cat memory.pressure
```

`memory.high` creates reclaim pressure before the hard cliff of `memory.max`.

### I/O

```bash
cat io.stat
cat io.max
cat io.pressure
```

I/O controls can limit bandwidth or IOPS per device, but storage stacks and cloud abstractions complicate attribution.

### PIDs

```bash
cat pids.current
cat pids.max
cat pids.events
```

PID limits protect a host from fork bombs and runaway thread creation.

---

## 5.17 OCI, runc, containerd, and CRI

A simplified container execution chain:

```text
Kubernetes kubelet
  -> CRI request
  -> containerd / CRI-O
  -> OCI runtime invocation
  -> runc creates namespaces, cgroups, mounts, credentials, seccomp
  -> exec container process
```

### OCI image

Defines image layout and metadata.

### OCI runtime specification

Defines the runtime bundle and process configuration.

### runc

Creates the container using Linux primitives.

### containerd

Manages images, snapshots, lifecycle, and runtime integration.

### CRI

Kubernetes interface used by kubelet to manage pod sandboxes and containers.

A pod sandbox commonly establishes shared networking and other pod-level context. Containers in the pod join selected namespaces.

---

## 5.18 OverlayFS and container filesystems

A container image often uses layered filesystems:

```text
lower read-only image layers
  + upper writable layer
  = merged container view
```

Failure modes:

- Copy-up latency.
- Inode exhaustion.
- Writable-layer growth.
- Deleted-open files.
- Overlay incompatibility with workload semantics.

Databases and durable state should use explicit volumes rather than relying on the container writable layer.

---

## 5.19 Linux capabilities

Capabilities divide root privilege into narrower units.

Examples:

- `CAP_NET_ADMIN`
- `CAP_SYS_ADMIN`
- `CAP_SYS_PTRACE`
- `CAP_NET_RAW`
- `CAP_SYS_TIME`

```bash
capsh --print
getpcaps <pid>
grep Cap /proc/<pid>/status
```

`CAP_SYS_ADMIN` is extremely broad and often described as the new root. Avoid granting it casually.

A strong design:

- Runs as non-root.
- Drops all capabilities.
- Adds only the minimum required.
- Prevents privilege escalation.
- Uses read-only filesystems where possible.

---

## 5.20 Seccomp

Seccomp filters system calls.

It is effective for reducing kernel attack surface, but policy must account for:

- Runtime and language behavior.
- Architecture-specific syscalls.
- Debugging tools.
- Upgrade compatibility.

Modes include strict filtering and BPF-based filters.

A seccomp denial often appears as `EPERM`, `SIGSYS`, or an application-specific startup failure. Preserve audit evidence before assuming the image is broken.

---

## 5.21 AppArmor and SELinux

Both are Linux Security Module policy systems.

### AppArmor

Path-oriented policy model, commonly used on Ubuntu-derived systems.

### SELinux

Label-based mandatory access control with type enforcement, common on Red Hat-derived systems.

The operational mistake is disabling enforcement to make an application start. Correct approach:

1. Capture denial evidence.
2. Confirm the expected access.
3. Adjust the narrowly scoped policy.
4. Retest in enforcing mode.

```bash
ausearch -m AVC,USER_AVC -ts recent
journalctl | grep -i apparmor
```

---

## 5.22 User namespaces and rootless containers

User namespaces map container user IDs to different host IDs.

Benefits:

- Container root is not host root.
- Improved isolation for rootless operation.

Trade-offs:

- Filesystem ownership complexity.
- Device and networking restrictions.
- Compatibility with volume plugins and privileged operations.

Rootless is a strong defense-in-depth measure, not a universal replacement for correct capabilities, seccomp, LSM, and workload policy.

---

## 5.23 Kubernetes mapped to Linux primitives

| Kubernetes concept | Linux implementation concepts |
|---|---|
| Pod | shared namespace and cgroup context managed by runtime |
| Container | process plus namespaces, cgroups, mounts, credentials, seccomp, LSM |
| CPU request | scheduler/admission signal; often maps to cgroup shares/weight indirectly |
| CPU limit | cgroup CPU quota |
| Memory limit | cgroup memory hard limit |
| NetworkPolicy | CNI/dataplane-specific policy using netfilter, eBPF, OVS, or cloud controls |
| Service | virtual IP/load-balancing implementation via iptables, IPVS, eBPF, or cloud LB |
| Pod IP | interface/address inside pod network namespace |
| EmptyDir | runtime-managed mount, possibly disk or memory-backed |
| SecurityContext | credentials, capabilities, seccomp, filesystem, privilege settings |

A Kubernetes symptom should be translated into its Linux mechanism before debugging.

Example:

> “Pod CPU is low but latency is high” may be cgroup quota throttling, softirq concentration, lock contention, run-queue delay, or downstream backpressure. Node-average CPU does not resolve the question.

---

## 5.24 Production incident: intermittent pod-to-pod failures

### Symptoms

- Only large responses fail.
- Small health checks pass.
- Failures occur across nodes but not on the same node.

### Hypothesis

Overlay MTU is too high for the underlay. Encapsulated packets exceed path MTU, and required ICMP messages are blocked.

### Investigation

1. Compare same-node and cross-node behavior.
2. Inspect pod, veth, tunnel, and physical MTUs.
3. Use `tracepath` and DF-marked probes.
4. Capture inner and outer packets.
5. Verify ICMP delivery.

### Mitigation

Reduce overlay/pod MTU to a validated value or fix the underlay/ICMP path.

### Prevention

Automated MTU validation, node-image tests, cross-zone synthetic transactions, and packet-size coverage in conformance tests.

---

## 5.25 Production incident: node has free CPU but drops packets

### Symptoms

- Node CPU average is 45%.
- One CPU is near 100% softirq.
- RX drops increase on one queue.
- Application p99 spikes.

### Root cause

IRQ/RSS distribution pins most receive work to one core, while the application and memory are placed elsewhere.

### Mitigation

Rebalance IRQs and queues, correct RSS configuration, move workload or affinity, and validate NUMA locality.

### Prevention

Per-queue and per-CPU dashboards, node qualification under packet-rate load, and topology-aware workload placement.

---

## 5.26 Production incident: new connections fail under load

### Symptoms

- Existing connections remain healthy.
- New outbound connections fail intermittently.
- TIME_WAIT and conntrack counts surge.
- NAT gateway or node source-port use is high.

### Possible causes

- Ephemeral port exhaustion.
- NAT tuple exhaustion.
- Conntrack capacity pressure.
- Excessive connection churn.

### Mitigation

Reuse connections, reduce churn, spread source addresses, scale NAT, and bound retries.

### Prevention

Connection-pool standards, port-capacity models, conntrack and NAT observability, and retry budgets.

---

## 5.27 Production debugging workflow

### Step 1: define the failing operation

- Source process and namespace.
- Destination address and port.
- Protocol.
- Packet size.
- Failure frequency.
- Same-node versus cross-node.

### Step 2: verify local application state

```bash
ss -lntup
ss -tinp
strace -f -e trace=network -p <pid>
```

### Step 3: inspect from the correct namespace

```bash
nsenter -t <pid> -n ip addr
nsenter -t <pid> -n ip route get <destination>
nsenter -t <pid> -n ip neigh
```

### Step 4: inspect policy and state

```bash
nft list ruleset
iptables-save
conntrack -S
```

### Step 5: inspect interfaces and queues

```bash
ip -s link
ethtool -S <iface>
cat /proc/net/softnet_stat
cat /proc/interrupts
```

### Step 6: capture packets at multiple points

```bash
tcpdump -nn -i any host <peer>
```

Capture inside the namespace, host veth, tunnel, and physical interface when necessary.

### Step 7: correlate with cgroups and Kubernetes

- CPU throttling.
- Memory pressure.
- PID limit.
- Pod restarts.
- CNI agent health.
- Node conditions.
- Policy changes.

---

## 5.28 Interview drills

### Why can a pod be unreachable while the node is reachable?

Because pod traffic may use separate namespaces, veth pairs, overlay tunnels, CNI policy, service translation, and pod-specific routes. Node reachability validates only part of the path.

### What is the difference between namespace isolation and cgroup isolation?

Namespaces isolate views and identifiers; cgroups account for and control resource consumption.

### Why can conntrack exhaustion break only new connections?

Existing tracked flows may continue while new state entries cannot be created.

### Why can packet drops occur with idle CPU?

One queue or CPU can be saturated while global CPU is idle. Drops may also occur in NIC rings, softnet backlog, conntrack, qdisc, or socket buffers.

### Why is `CAP_SYS_ADMIN` dangerous?

It grants a broad set of privileged operations and often defeats the intent of container isolation.

### Does killing a process prove an operation was prevented?

No. Depending on the hook and timing, side effects may already have occurred. Prevention must happen at an authorization point capable of denying the operation.

---

## 5.29 Hands-on labs

1. Build two network namespaces connected by a veth pair and route traffic between them.
2. Add a Linux bridge and connect multiple namespaces.
3. Create an MTU mismatch and reproduce a large-packet black hole.
4. Generate many short-lived TCP connections and observe TIME_WAIT, ephemeral ports, and conntrack.
5. Pin NIC interrupts and a workload to one CPU, then measure softirq and p99 effects.
6. Run a process with dropped capabilities and a restrictive seccomp profile.
7. Trigger an AppArmor or SELinux denial and diagnose it from audit logs.
8. Apply cgroup CPU, memory, I/O, and PID limits to a test workload and observe pressure and failure modes.
9. Use `nsenter` to compare host and container network views.
10. Trace one packet across namespace, veth, bridge, tunnel, and physical interface.

---

## 5.30 Principal-level summary

> I treat Linux networking as a sequence of queues, policy hooks, namespace boundaries, and state tables. I debug from the application and its actual namespace outward, verifying route, neighbor, policy, conntrack, interface queues, softirq distribution, and the external path. I treat containers as ordinary processes composed from namespaces, cgroups, mounts, credentials, capabilities, seccomp, and LSM policy. At Staff level, the objective is not merely to restore connectivity; it is to identify the exact failure domain, preserve evidence, bound blast radius, and prevent recurrence through capacity models, node qualification, policy tests, and layered isolation.
