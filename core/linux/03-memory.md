# 3. Virtual Memory, Page Cache, NUMA, Reclaim, and OOM

## 3.1 Why memory incidents are deceptive

Linux intentionally uses idle RAM for caches and delays expensive work until necessary. Therefore:

- Low `MemFree` is often healthy.
- A cgroup can OOM while the host has abundant available memory.
- A host can have free base pages and still fail a contiguous high-order allocation.
- Swap and reclaim can damage p99 latency long before global OOM.
- Process RSS does not equal unique physical memory.
- Page cache can be both beneficial and a source of reclaim/writeback pressure.

The useful question is:

> Which memory domain is constrained, which page types dominate it, how expensive is reclaim, and which workload experiences allocation or fault delay?

## 3.2 Virtual address spaces

Each process sees a virtual address space whose pages are mapped to physical frames or nonresident state through page tables.

Common regions:

- Executable text and read-only data.
- Writable data and BSS.
- Heap.
- Anonymous mappings.
- File mappings and shared libraries.
- Thread stacks.

```bash
cat /proc/<pid>/maps
cat /proc/<pid>/smaps_rollup
pmap -x <pid>
```

Virtual size may greatly exceed physical usage because reservations do not consume equivalent RAM until pages are touched.

## 3.3 Page tables and TLB

The CPU translates virtual addresses through page tables and caches recent translations in the Translation Lookaside Buffer.

Performance depends on:

- Working-set size relative to TLB reach.
- Page size.
- Task migration.
- NUMA placement.
- Page-table footprint.
- TLB shootdowns after mapping changes.

Huge pages increase TLB reach but introduce allocation, fragmentation, compaction, and latency trade-offs.

## 3.4 Demand paging and faults

A page fault is a controlled exception.

### Minor fault

The page can be mapped without storage I/O, for example an already resident file page or copy-on-write.

### Major fault

Storage I/O is required. A small major-fault rate can destroy the tail of a latency-sensitive service.

```bash
pidstat -r 1
perf stat -e page-faults,minor-faults,major-faults -p <pid>
```

Fault rate must be interpreted with fault latency and workload behavior.

## 3.5 Anonymous and file-backed memory

- **Anonymous memory:** heaps, stacks, and anonymous mappings. Clean content cannot be reread from a file; reclaim generally requires swap or process termination.
- **File-backed memory:** executables, mapped files, and page cache. Clean pages can often be discarded and reread; dirty pages require writeback.

This distinction drives reclaim behavior.

## 3.6 RSS, PSS, USS, and working set

- **RSS:** resident mapped pages; shared pages are counted in each process.
- **PSS:** shared pages divided proportionally.
- **USS:** unique pages owned by one process.
- **Working set:** pages actively required in a time window.

Container dashboards often use an approximation such as total cgroup usage minus selected inactive file cache. Know the exact metric definition before using it for limits or capacity planning.

## 3.7 Page cache

Page cache improves read locality and absorbs/coalesces buffered writes.

Benefits:

- Lower read latency.
- Fewer device operations.
- Shared cached content.
- Write batching.

Risks:

- Dirty-page accumulation.
- Reclaim competition.
- Writeback bursts.
- Double caching with application caches.
- Confusing process-versus-cgroup accounting.

Routinely dropping caches is not a production fix. It discards useful state, can create an I/O storm, and hides the root cause.

## 3.8 Buffered, direct, and memory-mapped I/O

### Buffered I/O

Uses page cache and is often the correct default.

### Direct I/O

Bypasses normal page-cache data caching for the transfer. It can reduce double caching but imposes alignment and application-cache responsibility.

### mmap

Maps file pages into the address space. Storage delay can appear as page-fault latency in arbitrary instruction paths.

Choose according to locality, durability, memory budget, and operational visibility rather than ideology.

## 3.9 Dirty pages and writeback

Failure sequence:

1. The workload writes faster than storage persists.
2. Dirty pages accumulate.
3. Background writeback falls behind.
4. Writers enter throttling, reclaim, or synchronous writeback paths.
5. Tail latency rises sharply.

```bash
watch -n1 'grep -E "Dirty|Writeback|MemAvailable" /proc/meminfo'
vmstat 1
iostat -xz 1
cat /proc/pressure/io
```

Changing dirty ratios may only move the delay. Durable fixes include sufficient storage service capacity, batching, write shaping, backpressure, and workload partitioning.

## 3.10 Physical allocation

The buddy allocator manages page blocks by order. High-order allocations need contiguous ranges and may trigger compaction or fail despite free base pages.

Kernel objects commonly come from slab-family caches.

```bash
slabtop
cat /proc/buddyinfo
cat /proc/pagetypeinfo
```

Unexpected slab growth can involve dentries, inodes, sockets, conntrack, drivers, or a kernel leak.

## 3.11 Reclaim and compaction

### Background reclaim

Kernel threads reclaim as watermarks are crossed.

### Direct reclaim

The allocating task performs reclaim itself, directly adding latency to the request path.

### Compaction

The kernel moves pages to create contiguous free ranges. Compaction can consume CPU and stall allocation.

```bash
vmstat 1
cat /proc/vmstat | grep -E 'pgscan|pgsteal|allocstall|compact|workingset'
cat /proc/pressure/memory
```

Interpretation:

- High scans with low reclaim efficiency mean difficult reclaim.
- `allocstall` indicates request-path impact.
- Refaults show useful pages being evicted and needed again.
- PSI measures experienced delay.

## 3.12 Pressure Stall Information

```bash
cat /proc/pressure/cpu
cat /proc/pressure/memory
cat /proc/pressure/io
```

- `some`: at least one task is stalled.
- `full`: all non-idle tasks in scope are stalled simultaneously.

Per-cgroup PSI helps identify pressure hidden by healthy host-wide averages.

## 3.13 Swap

Swap provides another reclaim option for anonymous memory. It may protect file cache and avoid abrupt OOM, but faulting pages back introduces latency.

Distinguish:

- Swap configured versus active thrashing.
- Cold-page eviction versus sustained swap-in/out.
- Host swap policy versus container constraints.
- Disk swap versus compressed in-memory mechanisms.

```bash
swapon --show
vmstat 1
sar -W 1
```

Both “never use swap” and “swap fixes memory shortage” are weak blanket rules. Decide based on latency class and failure policy.

## 3.14 Overcommit

Linux may allow virtual commitments larger than physical RAM plus swap because many reservations remain sparse.

```bash
sysctl vm.overcommit_memory
sysctl vm.overcommit_ratio
cat /proc/meminfo | grep -E 'CommitLimit|Committed_AS'
```

Allocation success does not guarantee later physical backing. Memory-heavy platforms may require admission control rather than optimistic commitment.

## 3.15 NUMA

On NUMA systems, memory latency and bandwidth depend on which socket owns the page.

Problems arise when:

- One initialization thread first-touches memory on one node.
- Workers later run on another node.
- CPU affinity changes without memory rebalance.
- A local node exhausts memory while remote memory remains.
- NIC/storage and application threads are topologically distant.

```bash
numactl --hardware
numastat
numastat -p <pid>
lscpu -e=CPU,NODE,SOCKET,CORE
```

NUMA tuning must align CPU, memory, IRQ, NIC, storage, and container placement.

## 3.16 Huge pages

Transparent Huge Pages can reduce TLB misses but may add compaction delay and memory waste. Explicit huge pages provide predictability but require reservation and application support.

```bash
grep -R . /sys/kernel/mm/transparent_hugepage 2>/dev/null
cat /proc/meminfo | grep -i huge
```

Benchmark representative allocation and tail-latency behavior; do not follow folklore blindly.

## 3.17 OOM domains

OOM means the relevant allocation domain cannot make progress.

Possible domains:

- Global host.
- Cgroup.
- NUMA node or cpuset.
- High-order allocation.

Evidence:

```bash
journalctl -k | grep -i -A30 -B10 'out of memory\|oom-kill\|killed process'
cat /proc/<pid>/oom_score
cat /proc/<pid>/oom_score_adj
```

For cgroup v2:

```bash
cat /sys/fs/cgroup/<group>/memory.events
cat /sys/fs/cgroup/<group>/memory.current
cat /sys/fs/cgroup/<group>/memory.max
cat /sys/fs/cgroup/<group>/memory.high
cat /sys/fs/cgroup/<group>/memory.stat
```

The largest process is not guaranteed to be the victim; selection depends on badness heuristics and constraints.

## 3.18 cgroup v2 memory controls

Key controls:

- `memory.current`: current accounted usage.
- `memory.max`: hard limit.
- `memory.high`: reclaim/throttling pressure before the hard cliff.
- `memory.low`: best-effort protection.
- `memory.min`: stronger protection.
- `memory.swap.max`: swap cap.
- `memory.events`: high, max, OOM, and kill events.

In Kubernetes, distinguish cgroup OOM, kubelet eviction, and global node OOM. They require different evidence and prevention.

## 3.19 Leak versus cache versus backlog

Rising memory may be:

- A true heap leak.
- Intentional application cache.
- Page cache.
- Allocator fragmentation.
- Memory-mapped files.
- Kernel slab growth.
- Socket buffers.
- Queue or session backlog.

Investigation:

1. Identify the accounting domain.
2. Split anonymous, file, shared, socket, and kernel memory.
3. Correlate growth with workload cardinality.
4. Inspect allocator/runtime metrics.
5. Capture heap profiles where appropriate.
6. Observe whether memory returns after load drops.

A restart proves only that restart releases memory.

## 3.20 Incident: pod OOM on a healthy node

Symptoms:

- Pod is `OOMKilled`.
- Node has ample available memory.
- Process RSS appears below the limit.

Investigation:

1. Read `memory.events`.
2. Inspect `memory.stat`.
3. Check whether dashboards omit cache, socket, or kernel accounting.
4. Examine burst concurrency and buffering.
5. Verify recent limit changes.

Likely cause: total cgroup accounting crosses `memory.max` even though process-only RSS looks safe.

Mitigate by reducing concurrency/buffering, draining traffic, or raising a validated limit. Prevent by monitoring composition, pressure, and events and load-testing peaks.

## 3.21 Incident: p99 spikes before OOM

If memory PSI, `allocstall`, reclaim scans, dirty pages, major faults, or swap-ins rise, user impact is already occurring. OOM is a late-stage symptom.

## 3.22 Interview drills

### Why is low free memory not necessarily bad?

Linux uses otherwise idle RAM as reclaimable cache. `MemAvailable`, reclaim efficiency, pressure, and workload latency matter more than raw free pages.

### Can a host OOM with free memory?

Yes. The constrained domain may be a cgroup, NUMA node, cpuset, or contiguous high-order request.

### RSS versus working set?

RSS counts resident mappings and may double-count shared pages. Working set estimates actively required pages in a time window.

### What should be captured after OOM?

The exact OOM report, cgroup events/stats, limits, memory composition, workload cardinality, recent changes, and pressure history.

## 3.23 Principal-level summary

> I debug memory by identifying the constrained domain and memory type, then measuring experienced pressure. I separate anonymous memory, file cache, kernel objects, socket buffers, and allocator fragmentation. I inspect reclaim, refault, writeback, NUMA locality, and cgroup events before changing limits. OOM is usually the final symptom; reclaim-driven tail latency often damages the SLO much earlier.