# 4. VFS, Filesystems, Block I/O, NVMe, and Latency

## 4.1 End-to-end I/O path

A storage operation can cross many independently queueing layers:

```text
application
  -> runtime / libc
  -> syscall
  -> VFS
  -> filesystem
  -> page cache or direct-I/O path
  -> block layer
  -> device mapper / encryption / RAID
  -> driver
  -> controller queue
  -> firmware
  -> media
```

Virtualized and cloud environments may add a hypervisor, network storage, replication, and provider-side throttling. A single “disk latency” metric rarely identifies the responsible queue.

## 4.2 VFS objects

The Virtual Filesystem Switch provides shared abstractions across filesystems.

- **Superblock:** a mounted filesystem instance and its metadata.
- **Inode:** metadata for a filesystem object, excluding its pathname.
- **Dentry:** a name-to-inode association used during path lookup.
- **File object:** one open instance with flags, offset, and operations.
- **File descriptor:** a process-local integer referencing an open file object.

A pathname is not the file. This explains why a process can continue writing after a file is unlinked: blocks are released only after no links and no open references remain.

```bash
lsof +L1
find /proc/*/fd -lname '*deleted*' 2>/dev/null
```

## 4.3 Path lookup and metadata pressure

Resolving `/a/b/c` walks directory components, mount points, dentries, inodes, symlinks, permissions, and security hooks.

Large small-file estates can be limited by metadata rather than bytes per second:

- Dentry and inode cache pressure.
- Random metadata I/O.
- Directory lock contention.
- Slow backups and scans.
- Inode exhaustion.

Measure operation shape and cardinality, not only throughput.

## 4.4 File descriptors and limits

```bash
ulimit -n
cat /proc/<pid>/limits
ls /proc/<pid>/fd | wc -l
cat /proc/sys/fs/file-nr
sysctl fs.file-max
```

Failure modes:

- Descriptor leak.
- Accept loop receives `EMFILE`.
- systemd service limits differ from the interactive shell.
- Host-wide file table exhaustion.
- Descriptor unintentionally inherited across `exec`.

A robust service retains enough operational capacity to emit diagnostics and recover safely.

## 4.5 Durability is end to end

A successful buffered `write()` generally means bytes reached kernel memory, not stable storage. Durability may require `fsync()`, `fdatasync()`, correct rename/create ordering, and syncing parent directories.

The complete contract includes:

- Application protocol.
- Filesystem ordering.
- Block-layer flushes.
- Controller cache behavior.
- Device firmware.
- Replication semantics.
- Power-failure behavior.

Do not equate successful writes, filesystem consistency, and application transaction durability.

## 4.6 Journaling

Journaling records enough metadata—and depending on mode, data—to recover filesystem consistency after a crash. It does not automatically provide application transaction semantics.

Ask:

- Which ordering guarantees apply?
- When is rename durable?
- Is the journal in the same failure domain?
- Are device caches power protected?
- Does the application issue the required sync operations?

## 4.7 ext4, XFS, and operational choice

Both are mature. Selection should consider:

- File sizes and metadata rate.
- Parallelism and allocation patterns.
- Growth and repair requirements.
- Snapshot/volume layer.
- Distribution support and operator familiarity.

Avoid blanket claims such as “XFS is always faster.” Benchmark representative workload and recovery behavior.

## 4.8 Copy-on-write and layered amplification

Copy-on-write appears in filesystems, snapshots, virtual disks, thin provisioning, and container layers.

Benefits:

- Snapshots.
- Clone efficiency.
- Space sharing.

Costs:

- Write amplification.
- Fragmentation.
- Metadata pressure.
- First-write latency.
- Deep layer chains.

A database writing through OverlayFS onto a snapshotting encrypted volume can cross several COW and translation layers.

## 4.9 OverlayFS and container storage

```text
lower read-only image layers
          +
upper writable layer
          =
merged container view
```

On first modification, a lower-layer file may be copied up.

Operational guidance:

- Put durable mutable data on explicit volumes.
- Treat the writable image layer as ephemeral.
- Avoid database workloads on overlay layers.
- Monitor inodes and metadata, not only bytes.

## 4.10 Capacity failure modes

“Disk full” can mean:

- No data blocks.
- No inodes.
- Reserved blocks unavailable to the workload.
- Thin-pool data or metadata exhaustion.
- Snapshot capacity exhaustion.
- Project/user quota.
- Deleted-open files retaining blocks.

```bash
df -hT
df -i
lsof +L1
findmnt
lvs -a -o +data_percent,metadata_percent 2>/dev/null
journalctl --disk-usage
```

Identify the growth source before deleting arbitrary files.

## 4.11 Page cache and read-ahead

Sequential access may trigger read-ahead; random access benefits less. Too much read-ahead wastes cache and bandwidth; too little underutilizes high-latency devices.

Evaluate:

- Access pattern.
- Device service time and bandwidth.
- Working-set size.
- Cache pollution.
- Cold-start and failover behavior.

## 4.12 Multi-queue block layer

Modern block I/O uses multiple software and hardware queues.

Key variables:

- Queue depth.
- In-flight operations.
- Request size.
- Sequential versus random access.
- Read/write mix.
- Flush/barrier frequency.
- Device/controller parallelism.

A device can reach harmful latency saturation before its advertised IOPS or throughput ceiling.

## 4.13 I/O schedulers

```bash
cat /sys/block/<device>/queue/scheduler
cat /sys/block/<device>/queue/nr_requests
```

Scheduler choice depends on the device and workload. In clouds, provider-side queues may dominate guest-visible behavior. Benchmark rather than copy a generic tuning guide.

## 4.14 Interpreting iostat

```bash
iostat -xz 1
```

Correlate:

- Operations per second.
- Throughput.
- Request size.
- Queue depth.
- Await/service latency.
- Device busy time.

Cautions:

- Averages hide tails.
- Device-mapper layers complicate attribution.
- NVMe “100% utilization” is not equivalent to a single spinning disk.
- Provider throttling may happen outside the guest.

## 4.15 Little's Law for storage

For a stable queue:

```text
concurrency ≈ throughput × latency
```

Example:

- 10,000 operations/s at 2 ms requires about 20 operations in flight.
- At 20 ms, the same throughput requires about 200.

If the stack permits only 64, throughput collapses or requests queue elsewhere. This is why rising service time often creates nonlinear application latency.

## 4.16 NVMe specifics

Operational concerns:

- Queue-depth mismatch.
- NUMA distance.
- IRQ affinity.
- Thermal throttling.
- Firmware resets.
- Wear and media errors.

```bash
nvme list 2>/dev/null
nvme smart-log /dev/nvme0 2>/dev/null
journalctl -k | grep -iE 'nvme|reset|timeout|I/O error'
```

Low average latency does not rule out rare multi-second reset pauses that destroy p99.99.

## 4.17 RAID, replication, and backups

Ask:

- Which failures are tolerated?
- What is rebuild impact?
- Does parity create read-modify-write amplification?
- Is controller cache protected?
- Do replicas share rack, zone, power, or control-plane dependencies?

RAID is not backup. Replication can replicate corruption or deletion.

## 4.18 Device mapper, LVM, thin provisioning, and encryption

```text
filesystem -> logical volume -> thin pool -> encryption -> multipath -> device
```

Each layer introduces queues, metadata, and failure modes.

```bash
lsblk -o NAME,TYPE,FSTYPE,SIZE,MOUNTPOINTS
lvs -a -o +devices,data_percent,metadata_percent
dmsetup ls --tree
```

Thin-pool metadata exhaustion can be catastrophic even when logical space appears available.

## 4.19 Network filesystems

NFS and similar systems combine storage and network failure semantics.

Common symptoms:

- D-state accumulation.
- Long hangs.
- Stale handles.
- Retransmission.
- Server overload.
- Host operations blocked by an unavailable mount.

Understand hard/soft behavior, retry policy, cache consistency, locking, and failover. Do not choose weak failure semantics solely to avoid hangs without understanding data-integrity risk.

## 4.20 Latency decomposition

Application-observed storage delay may include:

- Application queueing.
- Scheduler delay before issuing I/O.
- Filesystem locks and metadata work.
- Page-cache miss and reclaim.
- Block queue time.
- Device service time.
- Flush or replication.
- Scheduler delay before completion handling.

Tracing must separate issue-to-completion time from total application wall time.

## 4.21 Useful evidence

```bash
# Capacity and topology
lsblk -f
findmnt
df -hT
df -i

# Device performance
iostat -xz 1
sar -d 1
cat /proc/diskstats

# Process attribution
pidstat -d 1
cat /proc/<pid>/io

# Open files
lsof -p <pid>
lsof +L1

# Syscall timing
strace -f -ttT -e trace=file,read,write,fsync -p <pid>

# Experienced pressure
cat /proc/pressure/io
```

For deeper work, use eBPF latency histograms, filesystem-operation tracing, and off-CPU profiles.

## 4.22 Incident: 100% utilization with low throughput

Possible causes:

- Small synchronous random writes.
- Flush-heavy workload.
- Device error recovery.
- Cloud credit or provisioned-limit exhaustion.
- RAID rebuild.
- Thin-pool metadata pressure.
- Severe amplification.

Investigation:

1. Characterize request size and read/write mix.
2. Inspect latency distribution.
3. Review resets and errors.
4. Check provider limits.
5. Correlate with workload changes.
6. Inspect every translation layer.

Mitigation may include reducing write concurrency, batching safely, failing over, increasing provisioned performance, pausing noncritical work, or isolating the offender.

## 4.23 Incident: filesystem remains full after deletion

If `df` remains high while `du` falls, check deleted-open files.

```bash
lsof +L1
```

Gracefully reopen logs or restart the specific process. Do not reboot the fleet to solve a single leaked descriptor.

## 4.24 Interview drills

### Why can `du` and `df` disagree?

`du` walks named files; `df` reports allocated filesystem blocks. Deleted-open files, snapshots, reserved blocks, and metadata create differences.

### What does `fsync()` guarantee?

It requests persistence according to filesystem semantics. End-to-end durability still depends on correct directory handling, flush propagation, controller behavior, and the underlying failure model.

### Why can low IOPS saturate storage?

Operations may be synchronous, serialized, large, flush-heavy, or very slow. Saturation is a function of service time and concurrency, not IOPS alone.

### Why is average latency insufficient?

Rare multi-second operations can destroy customer tail latency while the mean remains acceptable.

## 4.25 Principal-level summary

> I debug storage as an end-to-end queueing system. I distinguish application queueing, filesystem work, page cache and reclaim, block-layer delay, device service, and external replication or throttling. I characterize operation size, durability, concurrency, locality, and tail latency before tuning. A fast benchmark does not prove safe crash behavior.