# Consolidation and Migration Plan

This file is the coordination point for all overlapping interview-preparation work.

## Objective

Maintain one canonical technical explanation for every reusable engineering topic while keeping Tesla- and Netflix-shaped scenarios in their own repositories.

The intended flow is:

```text
canonical technical chapter
        |
        +--> Tesla connected-vehicle adapter
        +--> Netflix streaming-platform adapter
        +--> future company or role adapters
```

## Source repositories

- `hatan4ik/tesla-sre-interview`
- `hatan4ik/netflix-devops-interview`
- `hatan4ik/staff-sre-platform-engineering-handbook` — canonical shared source

## Ownership rules

### Canonical handbook owns

- Linux internals and production debugging.
- Networking, DNS, TLS, load balancing, NAT, and service discovery.
- Kubernetes internals, scheduling, autoscaling, probes, networking, storage, and security.
- eBPF, Cilium, Hubble, Falco, Tetragon, and runtime security.
- Envoy, Istio, service-mesh control/data planes, and mTLS.
- Terraform state, locking, drift, recovery, modules, and policy.
- GitOps, CI/CD, artifact integrity, and progressive delivery.
- Observability, OpenTelemetry, Prometheus, tracing, profiling, and alerting.
- SLOs, error budgets, incident command, postmortems, capacity, DR, and chaos.
- Distributed systems, queues, consistency, idempotency, backpressure, and multi-region design.

### Tesla track owns

- Connected-vehicle command lifecycle and local vehicle authority.
- Remote unlock and mobile-feature reliability.
- Vehicle session ownership, command expiry, replay resistance, and fencing.
- Fleet telemetry and OTA architecture.
- Driver-profile synchronization and intermittent-connectivity behavior.
- Tesla-shaped mock interviews and behavioral stories.

### Netflix track owns

- Streaming request paths and playback-oriented availability.
- Discovery across very large microservice estates.
- Cache-sidecar and tail-latency scenarios.
- Streaming-scale DNS, mesh, NAT, and failover scenarios.
- Major-release chaos exercises and graceful degradation.
- Netflix-shaped mock interviews, modernization ROI, and leadership framing.

## Migration status

| Shared topic | Existing source | Canonical destination | Status |
|---|---|---|---|
| Linux architecture, boot, and syscalls | Tesla Linux chapter | `core/linux/01-architecture-boot-syscalls.md` | Migrated and normalized |
| Processes, scheduling, interrupts, and load | Tesla Linux chapter | `core/linux/02-processes-scheduler.md` | Migrated and normalized |
| Memory, page cache, NUMA, reclaim, and OOM | Tesla Linux chapter | `core/linux/03-memory.md` | Migrated and normalized |
| VFS, filesystem, and block I/O | Tesla Linux chapter | `core/linux/04-storage-io.md` | Migrated and normalized |
| Networking, containers, cgroups, and Linux security | Tesla Linux plan | `core/linux/05-networking-containers-security.md` | Next |
| Linux observability, eBPF, and incident debugging | Tesla Linux plan | `core/linux/06-observability-debugging.md` | Next |
| eBPF/Cilium/Hubble/Falco/Tetragon | Netflix chapter 2 | `core/ebpf-cilium-runtime-security/README.md` | Consolidated canonical chapter created |
| Fine-grained Envoy/Istio discovery | Netflix chapter 1 | `core/service-mesh/fine-grained-service-discovery.md` | Planned |
| Terraform state and recovery | Both tracks | `core/terraform/state-integrity-and-recovery.md` | Planned |
| SLOs, incidents, multi-region, and chaos | Both tracks | `core/reliability/` | Planned |

## No-duplication workflow

Before creating a chapter:

1. Search this repository by topic and failure mode.
2. Search `curriculum-map.md` for an existing canonical owner.
3. Extend the canonical chapter rather than creating a second textbook.
4. Put only domain-specific assumptions and trade-offs in the company track.
5. Link the track chapter to exact canonical prerequisites.
6. Record the ownership decision in this migration plan.

## Transitional policy

Existing duplicate chapters in company repositories are not deleted immediately. They remain as historical source material until the canonical replacement is reviewed for coverage.

During transition, company READMEs must label shared chapters as legacy/migration sources and point readers to this handbook as the source of truth. Once coverage parity is confirmed, duplicated theory may be replaced with short adapters and links.