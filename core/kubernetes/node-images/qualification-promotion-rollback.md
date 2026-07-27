# Kubernetes Node Image Qualification, Promotion, and Rollback

This chapter defines the canonical lifecycle for Linux and Kubernetes worker-node images across managed and self-managed clusters.

## Interview answer in 90 seconds

> I treat a node image as a versioned platform release, not as a mutable server template. The image has a declared bill of materials, signed build provenance, kernel and runtime compatibility, security controls, kubelet configuration, and a tested upgrade and rollback path. It moves through build, static verification, boot tests, Kubernetes conformance, workload compatibility, failure injection, canary pools, rollout rings, and broad promotion. New capacity uses the new image first; existing nodes are replaced rather than patched indefinitely. Promotion is gated by node readiness, bootstrap time, pod-start success, network and storage checks, drain behavior, application SLIs, and rollback viability. A failed image is contained by node-pool and failure-domain boundaries, stopped automatically, and rolled back by restoring the previous launch template or node class and replacing affected nodes safely.

## Why node images are production software

A node image determines:

- kernel behavior and security posture;
- container runtime and cgroup behavior;
- kubelet compatibility and configuration;
- CNI, CSI, and device-plugin compatibility;
- systemd unit ordering and bootstrap behavior;
- certificate trust and package sources;
- observability agents and log paths;
- disk layout, filesystem, and mount options;
- time synchronization and DNS behavior;
- shutdown, drain, and reboot semantics.

A change that passes an image build can still fail only under pod density, network policy, storage attach, pressure, or disruption.

## Immutable lifecycle

```text
source and policy
      |
      v
reproducible build
      |
      v
SBOM + provenance + signature
      |
      v
static and vulnerability checks
      |
      v
boot and bootstrap tests
      |
      v
Kubernetes conformance and workload tests
      |
      v
failure injection and drain tests
      |
      v
canary node pool
      |
      v
ringed fleet promotion
      |
      v
retirement and evidence retention
```

Do not promote by manually changing live nodes. Produce a new version and replace nodes through an orchestrated lifecycle.

## Required image contract

Every image version should declare:

- immutable image identifier and semantic release label;
- source commit and build pipeline identity;
- operating-system release;
- kernel version and configuration;
- container runtime version and configuration;
- kubelet version and flags;
- CNI, CSI, GPU, accelerator, and device dependencies;
- enabled systemd units;
- package and repository inventory;
- CA trust bundle and certificate policy;
- hardening profile and exceptions;
- filesystem, disk, and ephemeral-storage layout;
- bootstrap inputs and expected outputs;
- supported Kubernetes minor versions;
- supported instance, architecture, and hardware classes;
- rollback predecessor and support window.

## Qualification layers

### 1. Build integrity

Require:

- reproducible or controlled builds;
- trusted builders and short-lived build identity;
- pinned inputs or approved repositories;
- SBOM generation;
- vulnerability and malware scanning;
- signature and provenance verification;
- no embedded long-lived credentials;
- policy checks for prohibited packages and configuration.

### 2. Boot and bootstrap

Test:

- cold boot and reboot;
- cloud-init or equivalent bootstrap;
- network availability before kubelet startup;
- time synchronization;
- DNS and certificate trust;
- container runtime startup;
- kubelet registration;
- node labels, taints, topology, and capacity;
- log and metric agent startup;
- behavior when metadata, package, or identity endpoints are slow or unavailable.

Record bootstrap latency distributions, not only success.

### 3. Kubernetes conformance

Validate:

- node readiness and lease renewal;
- pod sandbox creation;
- image pull and unpack;
- Service and DNS connectivity;
- network policy;
- volume attach, mount, resize, and detach;
- secret and projected-volume delivery;
- probes and lifecycle hooks;
- cgroup CPU and memory enforcement;
- eviction and disk-pressure behavior;
- PodDisruptionBudget-aware drain;
- graceful shutdown and termination;
- metrics and logs required for incident response.

### 4. Representative workload compatibility

Use a workload matrix:

- latency-sensitive services;
- memory-intensive services;
- high-connection-count proxies;
- stateful workloads;
- privileged or host-integrated agents;
- GPU or device workloads;
- service-mesh sidecar and ambient workloads;
- security and observability agents;
- workloads with unusual sysctls, mounts, or kernel dependencies.

A generic conformance suite does not prove every platform workload is compatible.

### 5. Failure tests

Inject:

- kubelet restart;
- container runtime restart;
- network interruption;
- disk pressure and inode exhaustion;
- memory pressure and OOM;
- stale or failed bootstrap dependency;
- CNI or CSI restart;
- node reboot under workload;
- drain with strict disruption budgets;
- abrupt termination and replacement;
- partial zone or node-pool loss.

Verify that the node either recovers safely or is fenced and replaced.

## Promotion topology

A practical rollout uses isolated rings:

```text
build validation
   -> disposable test cluster
   -> internal canary pool
   -> noncritical production pool
   -> one zone or small cell
   -> broader production rings
   -> default for new clusters
```

Each ring has:

- explicit eligible clusters and node pools;
- maximum concurrent nodes and failure domains;
- maintenance windows;
- hold time;
- automatic stop conditions;
- named approver or automated policy;
- rollback target;
- evidence retention.

Avoid replacing all nodes in one Availability Zone or one workload class simultaneously.

## Rollout strategy

Preferred approach:

1. create a new node pool, launch template, machine class, or node class;
2. launch a bounded canary set;
3. verify bootstrap and workload SLIs;
4. shift ordinary scale-out to the new version;
5. cordon and drain old nodes within disruption budgets;
6. replace by failure domain and workload risk;
7. hold and observe;
8. retire the old pool only after rollback confidence is no longer required.

In-place package updates create mixed, hard-to-reproduce states and should be limited to exceptional emergency procedures.

## Promotion gates

Minimum signals:

- node bootstrap success and p95 time;
- Ready and lease-renewal stability;
- pod sandbox and startup success;
- image pull latency and failure rate;
- CNI address allocation and network-policy success;
- DNS lookup success and latency;
- storage attach/mount/detach success;
- kubelet and runtime restart rate;
- kernel warnings, panics, soft lockups, and filesystem errors;
- memory, CPU, disk, and network pressure;
- drain duration and blocked-eviction count;
- workload error, latency, saturation, and availability SLIs;
- observability completeness;
- successful rollback rehearsal.

## Rollback

Rollback is not “change the label back.”

A safe rollback requires:

- previous image and launch configuration still available;
- previous version still compatible with the current control plane and workload configuration;
- capacity to launch replacement nodes;
- disruption budgets and topology constraints understood;
- new nodes cordoned or launch disabled;
- affected nodes drained or fenced;
- stateful attachments and singleton workloads protected;
- recovery verified through workload SLIs.

If the image can corrupt durable data or violate safety, stop scheduling and fence first; graceful drain may not be the first action.

## Incident workflow

### Symptoms

- nodes fail to join;
- nodes become Ready but pods cannot start;
- only new nodes have DNS, CNI, CSI, or image-pull failures;
- kernel or runtime crashes increase;
- one architecture or instance family fails;
- drain or shutdown hangs;
- application latency rises only on the new image cohort.

### Bound the cohort

Compare:

- image ID and release label;
- node pool, cluster, zone, architecture, and instance family;
- bootstrap version;
- kernel and runtime version;
- CNI/CSI/agent versions;
- workload type;
- node age and launch time.

### Stabilize

1. stop promotion and scale-out on the suspect image;
2. keep healthy old capacity available;
3. cordon suspect nodes when continued scheduling is unsafe;
4. move workloads using bounded drain or selective rescheduling;
5. restore the prior node source;
6. replace by failure domain;
7. preserve boot, kernel, kubelet, runtime, and bootstrap evidence;
8. verify end-to-end recovery.

## Example evidence commands

```bash
kubectl get nodes -L node.kubernetes.io/instance-type,topology.kubernetes.io/zone,platform.example.com/image
kubectl describe node <node>
kubectl get events -A --field-selector involvedObject.kind=Node --sort-by=.lastTimestamp
kubectl get pods -A -o wide --field-selector spec.nodeName=<node>
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data --dry-run=server

# On the node or through an approved debug path:
journalctl -u kubelet --since '-30 min'
journalctl -u containerd --since '-30 min'
journalctl -b -p warning
systemctl --failed
cat /proc/cmdline
uname -a
```

## Governance

Maintain:

- one authoritative image pipeline;
- documented emergency patch process;
- compatibility matrix;
- supported-version and retirement policy;
- signed evidence for every release;
- fleet inventory by exact image ID;
- exception ownership and expiry;
- promotion and rollback audit trail;
- periodic rebuilds even without visible package changes;
- tests for end-of-life repositories and certificate expiry.

## Weak answers to avoid

- “Patch nodes with Ansible.”
- “Build an AMI and update the node group.”
- “If nodes are Ready, the image is good.”
- “Roll back the deployment” when the failure is below the workload.
- “Drain every node at once.”
- “Use latest packages.”
- “Vulnerability scan passed, therefore production qualification is complete.”

## Adversarial follow-ups

### Why not patch in place?

It creates drift and mixed states, weakens reproducibility, and makes rollback uncertain. Immutable replacement gives an auditable, testable release boundary.

### What if a critical kernel vulnerability appears?

Use an emergency lane with the same identity, provenance, bounded canary, compatibility, and rollback controls, but shorter hold periods and risk-based approvals. Urgency changes the timeline, not the need for evidence.

### How do you detect a problem affecting only one workload?

Correlate node image with workload identity, kernel/runtime dependencies, pod-start and application SLIs. Include representative workload qualification before broad promotion.

### What proves completion?

The fleet inventory shows intended convergence, old vulnerable versions are retired, workload and node SLIs remain healthy, and rollback or recovery evidence is preserved.
