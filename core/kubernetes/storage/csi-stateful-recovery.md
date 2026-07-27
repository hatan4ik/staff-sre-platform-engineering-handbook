# Kubernetes CSI, Persistent Volumes, and Stateful Recovery

This chapter is the canonical foundation for Kubernetes storage incidents involving PersistentVolumes, claims, StorageClasses, CSI provisioning, attach/detach, mount, topology, snapshots, writer fencing, and stateful recovery.

## Interview answer in 90 seconds

> I treat Kubernetes storage as a distributed state and ownership problem, not only a mount problem. I reconstruct the path from claim and StorageClass through provisioning, volume topology, scheduler placement, controller attachment, node staging and publishing, filesystem or block access, and application write authority. For an incident I classify whether the pod is pending, attachment is blocked, mount failed, filesystem is unhealthy, the device is saturated, or the application cannot establish safe writer ownership. I compare healthy and affected volumes by storage class, CSI driver and version, zone, node, volume mode, access mode, snapshot lineage, and workload release. Before force-detach or failover I fence the old writer and verify the storage system's real attachment state. Mitigation is bounded: restore the controller or node plugin, place the pod in a compatible topology, clear a confirmed stale attachment through supported procedures, restore capacity, or recover from a tested snapshot. Recovery is proven by application-level reads/writes, durability checks, replication or backup evidence, and no dual-writer condition.

## End-to-end storage path

```text
PersistentVolumeClaim
        |
        v
StorageClass and provisioner
        |
        v
PersistentVolume / storage object
        |
        v
scheduler topology decision
        |
        v
attach/detach controller and CSI controller
        |
        v
cloud or storage-system attachment
        |
        v
CSI node stage / publish
        |
        v
filesystem or block device in pod
        |
        v
application writer and durability contract
```

Each transition has distinct evidence and ownership.

## Core objects

### PersistentVolumeClaim

The workload's storage request:

- capacity;
- access modes;
- volume mode;
- StorageClass;
- selector or data source;
- retention and expansion semantics.

### PersistentVolume

Represents provisioned storage and binding information, including:

- CSI driver and volume handle;
- capacity;
- access modes;
- reclaim policy;
- node affinity and topology;
- mount options;
- claim reference.

### StorageClass

Defines provisioning policy:

- provisioner;
- parameters;
- reclaim policy;
- volume binding mode;
- expansion;
- allowed topologies;
- mount options.

### VolumeAttachment

Represents controller-managed attachment intent for attachable CSI volumes.

The object may say attachment is requested while the cloud or storage system is still converging—or vice versa after a partial failure.

## Dynamic provisioning

The external provisioner watches claims and creates storage through the CSI controller.

Failure patterns:

- provisioner unavailable or leader election unstable;
- storage API quota or permission failure;
- invalid StorageClass parameters;
- no capacity in an allowed zone;
- secret or credential failure;
- controller retries creating duplicate or orphaned resources;
- claim references an unsupported data source;
- volume creation succeeds externally but the API update fails.

Investigate configuration, Kubernetes objects, CSI controller logs, provider events, and actual storage inventory.

## Binding modes

### Immediate

Volume is provisioned or bound before pod scheduling. This can create topology mismatch if the selected zone has no compatible compute capacity.

### WaitForFirstConsumer

Provisioning or binding is delayed until the scheduler knows the pod's placement constraints. This is generally safer for topology-aware storage but still requires compatible node and storage capacity.

Do not switch binding mode casually for existing workloads; test provisioning and recovery behavior.

## Access modes are contracts, not universal guarantees

Common modes include:

- ReadWriteOnce;
- ReadOnlyMany;
- ReadWriteMany;
- ReadWriteOncePod where supported.

Actual enforcement depends on driver, filesystem, protocol, and platform.

A volume marked ReadWriteOnce may permit multiple pods on one node in some implementations. It does not automatically provide application-level leader election or prevent every dual writer.

## Volume modes

### Filesystem

Kubelet or CSI mounts a filesystem. Consider:

- filesystem type;
- mount options;
- fsck and recovery;
- ownership and permissions;
- resize behavior;
- inode exhaustion;
- journal and corruption evidence.

### Block

The pod receives a raw block device and the application owns formatting or block semantics. Recovery and safety require specialized handling.

## CSI controller and node components

### Controller service

May provide:

- create/delete volume;
- controller publish/unpublish;
- snapshot operations;
- expand volume;
- capacity reporting.

### Node service

May provide:

- node stage/unstage;
- node publish/unpublish;
- node expansion;
- volume statistics.

A healthy controller does not prove node mount behavior; a healthy node plugin does not prove the external attachment API is correct.

## Attach and detach

State transition:

```text
pod scheduled to node
  -> VolumeAttachment created
  -> CSI controller requests attachment
  -> storage system confirms attachment
  -> node plugin discovers/stages device
  -> volume mounted or published
```

Detach reverses the path, but node loss creates ambiguity: the control plane may not know whether the old host can still write.

## Writer fencing

Before moving a single-writer volume after node or network failure, prove the old writer cannot continue.

Possible fencing mechanisms:

- power off or terminate the old node;
- storage-system attachment fencing;
- lease epoch enforced by the application or storage service;
- SCSI or storage reservation mechanisms where supported;
- network isolation plus storage control-plane confirmation;
- application leader fencing.

Cordon or marking a node NotReady is not sufficient fencing. A partitioned node may still be alive and writing.

## Stale attachments

Symptoms:

- new pod waits on multi-attach error;
- VolumeAttachment points to old node;
- provider shows attachment still active;
- node is gone but detach never completed;
- force-detach appears available.

Safe workflow:

1. identify volume and intended writer;
2. verify application and storage consistency requirements;
3. fence the old node or writer;
4. inspect Kubernetes and external attachment state;
5. use supported detach or force-detach only after fencing;
6. attach to the new node;
7. verify filesystem and application consistency;
8. preserve timeline and evidence.

Force-detach before fencing can cause corruption.

## Topology

Storage may be constrained by:

- availability zone;
- region;
- rack or storage domain;
- node label;
- local disk ownership;
- replication group;
- latency policy.

The scheduler uses PV node affinity and CSI topology information. A pod can be pending because no node satisfies both compute and storage requirements.

Inspect:

```bash
kubectl get pvc,pv -A
kubectl describe pvc <claim> -n <namespace>
kubectl describe pv <volume>
kubectl get volumeattachment
kubectl get storageclass -o yaml
kubectl get nodes -L topology.kubernetes.io/zone
```

## Local persistent volumes

Local volumes provide predictable local performance but are tied to a node or topology domain.

Require:

- scheduler-aware node affinity;
- application replication;
- node failure and replacement procedure;
- disk inventory and health monitoring;
- data evacuation or rebuild process;
- capacity fragmentation management.

Do not treat a local PV like a portable network volume.

## StatefulSet behavior

StatefulSets provide stable pod identity and claim templates, but they do not automatically provide:

- data replication;
- safe leader election;
- backup;
- cross-region recovery;
- application consistency;
- volume fencing;
- zero-downtime schema changes.

Understand ordered or parallel pod management, update strategy, partitioning, retention policy, and application quorum semantics.

## Expansion

Volume expansion can involve:

1. claim size update;
2. controller-side storage expansion;
3. node-side device resize;
4. filesystem resize;
5. application recognition.

Failure can leave partial progress. Verify actual block device, filesystem, and claim status.

Do not shrink persistent volumes unless the storage system and migration procedure explicitly support it.

## Snapshots and backups

A snapshot is not automatically an application-consistent backup.

Define:

- crash-consistent versus application-consistent semantics;
- quiesce or database checkpoint procedure;
- snapshot controller and class;
- retention and immutability;
- encryption and access;
- cross-account or cross-region copy;
- restore testing;
- point-in-time recovery;
- catalog and ownership;
- deletion protection.

The only proven backup is one that has been restored and validated.

## Restore workflow

```text
select recovery point
  -> authorize and create restore volume
  -> validate size, topology, encryption, and identity
  -> mount in isolated recovery environment
  -> perform application consistency checks
  -> reconcile logs or transactions
  -> establish writer authority
  -> shift traffic gradually
  -> preserve old data for rollback window
```

Avoid attaching a recovery volume directly to production before validation.

## Data replication and DR

Kubernetes does not replace database or storage replication semantics.

For regional recovery define:

- replication direction and lag;
- write authority;
- RPO and RTO;
- fencing;
- data promotion;
- routing;
- application connection behavior;
- reconciliation after failback;
- test evidence.

See the canonical disaster-recovery module.

## Performance and saturation

Investigate:

- IOPS and throughput limits;
- burst credits;
- queue depth;
- latency distributions;
- filesystem cache and sync behavior;
- network path for remote storage;
- noisy neighbors;
- volume size and performance coupling;
- instance attachment bandwidth;
- request size and concurrency;
- throttling and retries.

Pod CPU may appear healthy while storage latency causes request timeouts and queue growth.

## Ephemeral storage

Node ephemeral storage includes writable layers, logs, and `emptyDir` depending on configuration.

Monitor:

- bytes and inodes;
- image filesystem and container filesystem;
- log growth;
- eviction thresholds;
- pod requests and limits;
- local volume consumption;
- cleanup behavior.

DiskPressure and ephemeral-storage eviction are different from persistent-volume failure.

## Incident workflow

### Classify the phase

- claim pending;
- provisioning failed;
- pod unschedulable due to topology;
- attachment pending or stale;
- device stage/publish failed;
- mount or filesystem failed;
- volume read-only;
- performance degraded;
- application writer or replication failed;
- snapshot or restore failed.

### Preserve evidence

```bash
kubectl get pod,pvc,pv,volumeattachment -A -o wide
kubectl describe pod <pod> -n <namespace>
kubectl describe pvc <claim> -n <namespace>
kubectl describe pv <volume>
kubectl get events -A --sort-by=.lastTimestamp
kubectl logs -n <csi-namespace> <csi-controller-pod> --since=30m
kubectl logs -n <csi-namespace> <csi-node-pod> --since=30m
```

Also capture external storage attachment, snapshot, quota, latency, and audit evidence.

### Bound the cohort

Compare:

- StorageClass;
- CSI driver and version;
- volume type and mode;
- zone and node;
- filesystem;
- workload version;
- new versus existing volumes;
- encryption key or credential;
- snapshot source;
- read versus write operations.

### Stabilize safely

1. stop rollouts creating more claims or moving writers;
2. preserve the current writer if it is healthy;
3. fence an ambiguous old writer before detach or failover;
4. restore CSI controller or node plugin health;
5. correct topology, credentials, quota, or StorageClass configuration;
6. restore known-good node or driver version;
7. attach or mount using supported procedures;
8. recover from a tested snapshot when repair is unsafe;
9. verify application consistency and durability.

## Storage SLOs

Track:

- claim provisioning success and latency;
- scheduling wait due to storage topology;
- attach and detach success and latency;
- stage, publish, and mount success;
- stale attachment count;
- filesystem and block error rate;
- volume read/write latency and throughput;
- throttling and queue depth;
- snapshot success and age;
- restore success and validation duration;
- replication lag;
- writer-fencing success;
- application transaction success and durability.

## Validation program

Test:

- new claim provisioning;
- zone-aware delayed binding;
- node loss with writer fencing;
- stale attachment recovery;
- CSI controller and node-plugin restart;
- driver upgrade and rollback;
- volume expansion;
- inode or capacity exhaustion;
- storage latency injection;
- snapshot and isolated restore;
- regional promotion and failback;
- application consistency after abrupt failure.

## Weak answers to avoid

- “Delete the pod and Kubernetes will remount it.”
- “Force-detach the volume.”
- “StatefulSet makes the database highly available.”
- “We have snapshots, so backup is complete.”
- “PVC is Bound, so storage is healthy.”
- “Scale the CSI controller.”
- “Move the pod to another zone” without data topology.

## Adversarial follow-ups

### Why is a NotReady node not necessarily fenced?

The node may be partitioned from the control plane but still alive with storage access. Fencing requires proof that it cannot continue writing.

### What is the difference between a snapshot and a backup?

A snapshot is a storage capture with specific consistency and failure-domain properties. A backup includes retention, isolation, catalog, restore procedure, and validated application recovery.

### Why can a Bound claim still fail?

Binding proves object association, not successful attachment, mount, filesystem health, performance, or application correctness.

### When would you prefer restoring rather than repairing?

When attachment or filesystem state is unsafe, corruption is suspected, the current writer cannot be trusted, or tested recovery provides a lower-risk path within RTO/RPO.

### What proves recovery?

The intended writer is uniquely fenced and active, the volume is attached and mounted correctly, application-level reads/writes and durability checks pass, latency normalizes, and backup/replication evidence remains valid.

## Principal-level review checklist

- storage classes express topology, reclaim, expansion, encryption, and ownership intentionally;
- writer fencing is documented and tested;
- force-detach is a governed break-glass action;
- application replication and Kubernetes objects are not conflated;
- snapshots have restore evidence and consistency semantics;
- CSI upgrades use canary and rollback procedures;
- storage and compute topology are capacity-planned together;
- regional recovery includes authority, data promotion, and reconciliation;
- SLOs cover provisioning through application durability;
- game days test node loss, stale attachment, restore, and failover.
