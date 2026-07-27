# Question 15 — Globally Distributed Secure Software Updates to Millions of Devices

## Interview prompt

Design a globally distributed platform on AWS capable of securely delivering software updates to millions of devices.

## What the interviewer is testing

The difficult part is not storing a binary in S3. A Staff/Principal design must cover:

- artifact provenance and cryptographic trust
- hardware and software compatibility
- rollout blast radius
- intermittent connectivity
- bandwidth shaping and regional delivery
- device-safe installation and rollback
- command and job state at fleet scale
- anti-replay and anti-downgrade controls
- observability without telemetry overload
- recovery when the update itself damages connectivity

The device, not the cloud, is the final safety authority.

---

## 90-second Staff/Principal answer

> I separate the release control plane from the artifact delivery data plane. CI produces one immutable artifact and SBOM, runs tests, signs the release manifest and binaries with a protected signing workflow, stores them in versioned encrypted S3, and registers package metadata in the AWS IoT Device Management Software Package Catalog. No production deployment references a mutable tag or unversioned object.
>
> AWS IoT Device Management Jobs targets devices or dynamic thing groups and tracks job execution. I use staged cohorts—internal, canary, 1%, 5%, 25%, then broad rollout—with rollout-rate limits, maintenance windows, timeout, and abort thresholds. Devices obtain time-limited S3 URLs or a controlled CloudFront path, download with resume and bandwidth limits, verify signature, hash, model, dependency, minimum bootloader, expiry, and anti-rollback version before installation.
>
> The device installs into an inactive A/B partition or comparable transactional mechanism, verifies health after reboot, and automatically rolls back when the new version fails. The cloud distinguishes notified, downloaded, verified, installed, rebooted, healthy, failed, and rolled back states.
>
> I partition the fleet by hardware generation, geography, network, and risk; keep the update service independent of the updated application; and preserve an out-of-band recovery path. I prove the design with signature corruption, expired URLs, interrupted downloads, power loss, failed boot, bad canary, regional outage, offline devices, and telemetry-storm tests.

---

## 1. Requirements and threat model

Clarify:

| Dimension | Questions |
|---|---|
| Fleet | Number of devices, active concurrency, growth, and geographical distribution? |
| Device | CPU, storage, A/B partitions, secure element, bootloader, and recovery mode? |
| Network | Wi-Fi, cellular, metered, intermittent, low-bandwidth, or offline for months? |
| Artifact | Firmware, OS, containers, application packages, models, or configuration? |
| Size | Full image and delta size? |
| Urgency | Routine feature release or emergency security patch? |
| Safety | Can a failed update cause physical or business harm? |
| Recovery | Remote rollback, local rollback, service visit, or factory recovery? |
| Compliance | Geography, export, audit, signing-key, or retention requirements? |

Threats include:

- malicious artifact substitution
- compromised CI or release role
- signing-key theft
- manifest tampering
- downgrade to vulnerable version
- replay of an old authorized job
- update sent to incompatible hardware
- compromised device impersonating another device
- one bad release reaching the whole fleet
- denial of service through synchronized download or telemetry
- device bricking after power loss
- recovery dependency on the software that just failed

---

## 2. Reference architecture

```text
Source commit / release request
       |
CI and release pipeline
       |
       +--> tests / hardware matrix / security scan
       +--> SBOM / provenance
       +--> immutable artifact and manifest
       +--> protected signing workflow
       |
       v
Versioned encrypted S3 artifact buckets
       |
       +--> replication / regional distribution strategy
       +--> CloudFront where appropriate
       |
Software Package Catalog
       |
Release orchestration service
       |
AWS IoT Device Management Jobs
       |
AWS IoT Core MQTT notifications and status
       |
Millions of uniquely identified devices
       |
       +--> download
       +--> signature/hash/compatibility verification
       +--> staged install
       +--> reboot and health validation
       +--> success or automatic rollback

Telemetry path:
IoT Core rules -> Kinesis / SQS -> processors -> data lake / metrics

Operational control:
CloudWatch, OpenTelemetry, AMP, Grafana, CloudTrail, IoT audit,
Security Hub, KMS, Organizations, incident command
```

---

## 3. Artifact and release model

### Immutable package identity

Every release has:

```text
package name
semantic or monotonic version
artifact digest
manifest digest
hardware compatibility
bootloader and dependency requirements
minimum allowed source version
size and chunk metadata
release channel
created time and expiry
signing identity and algorithm
SBOM and provenance references
```

The update job references a digest and versioned object, never `latest`.

### Software Package Catalog

Use AWS IoT Device Management Software Package Catalog to maintain package and version inventory and associate versions with devices or dynamic thing groups.

The catalog is metadata and fleet inventory. The device still verifies the package cryptographically and enforces local compatibility.

### Manifest

A signed manifest should bind:

- artifact hashes
- target model and hardware revision
- package version
- dependencies
- minimum bootloader
- installation instructions identifier
- anti-rollback counter
- release expiry
- allowed update path

Do not sign only the binary while leaving the compatibility metadata unsigned.

---

## 4. Build and release supply chain

```text
source revision
  -> reproducible or controlled build
  -> unit/integration/hardware tests
  -> dependency and vulnerability scan
  -> SBOM and provenance
  -> artifact hash
  -> release approval
  -> signing
  -> immutable S3 upload
  -> package catalog registration
  -> canary job
```

### Build identity

Use short-lived CI federation and isolated roles:

- build role cannot approve production
- release role cannot alter source
- signing role accepts only approved artifact digests
- rollout role cannot modify signing keys
- emergency release requires stronger approval and audit

### Artifact signing

Use AWS Signer or the appropriate managed signing integration for the device software format.

Protect signing with:

- dedicated account or strong boundary
- least-privilege IAM
- approval workflow
- CloudTrail
- restricted profile changes
- key rotation and revocation plan
- offline or hardware-rooted trust anchor on the device

The device trusts a controlled public-key chain, not an S3 bucket or TLS session alone.

### Reproducibility and provenance

Where practical, record:

- source commit
- builder image digest
- dependencies
- compiler/toolchain
- build parameters
- test evidence
- signer
- approval

A valid signature proves an authorized signer signed the artifact. Provenance helps prove what was built and from which source.

---

## 5. Artifact storage and delivery

### S3

Use:

- versioning
- KMS encryption where required
- Block Public Access
- TLS-only policies
- Object Lock or retention where compliance and release integrity require it
- exact-prefix write permissions
- replication according to regional recovery design
- lifecycle policies that do not delete artifacts still needed for rollback

### Presigned URLs

AWS IoT Jobs can replace S3 URL placeholders with time-limited presigned URLs when devices request the job document.

Control:

- short but usable expiry
- object version ID
- least-privilege presigning role
- device retry behavior
- clock-skew handling
- re-request of an expired URL without changing package identity

URL expiry must not force the device to accept a different artifact.

### CloudFront

Use CloudFront when global edge caching and controlled distribution materially improve delivery.

Design:

- origin access control
- signed URLs or cookies where required
- cache key based on immutable object path
- regional and ISP distribution monitoring
- cache invalidation unnecessary for immutable versions
- protection against one release causing an origin stampede

Do not use the CDN as the trust boundary. The device verifies the signed manifest and artifact digest.

### Bandwidth shaping

Avoid fleet-wide synchronized download.

Use:

- rollout rate
- randomized device jitter
- local maintenance windows
- network-type policy
- per-region concurrency limits
- chunked and resumable download
- delta packages where safe
- peer or local-site distribution only with an additional verified trust model

---

## 6. AWS IoT Jobs orchestration

AWS IoT Jobs defines remote operations for individual things or thing groups and supports rollout, abort, timeout, and execution tracking.

### Job document

The job document contains instructions and references such as:

```json
{
  "operation": "install-package",
  "package": "device-os",
  "version": "7.4.2",
  "manifestUrl": "${aws:iot:s3-presigned-url-v2:...}",
  "expiresAt": "2026-08-10T00:00:00Z",
  "releaseChannel": "production"
}
```

The exact schema is owned and versioned by the device platform.

### Snapshot versus continuous jobs

- **Snapshot job:** targets the current members of the target set.
- **Continuous job:** also applies to devices that later join a dynamic thing group.

Continuous jobs are useful for compliance groups such as “devices below minimum secure version,” but require careful removal and version logic to avoid repeated or unwanted installation.

### Rollout configuration

Control how many devices receive the job over time.

Cohorts:

```text
release engineers' lab devices
  -> employee/internal fleet
  -> known recoverable canaries
  -> 1% representative production
  -> 5%
  -> 25%
  -> 50%
  -> broad rollout
```

Each gate requires evidence, not just elapsed time.

### Abort configuration

Abort when failure thresholds are crossed.

Use multiple indicators:

- install failure
- boot rollback
- loss of heartbeat
- crash rate
- critical business SLI
- device-specific safety fault

A cloud-reported `FAILED` count alone may miss devices that lost connectivity after a bad install.

### Timeout

Execution timeout prevents jobs from remaining active forever. Device-local expiry separately prevents stale execution after reconnect.

---

## 7. Fleet segmentation

Segment by:

- exact hardware revision
- bootloader version
- current software version
- geography and legal boundary
- network type
- battery or power state
- storage capacity
- device health
- customer or operational criticality
- recoverability

### Representative canaries

A canary group must include:

- older hardware
- low storage
- slow network
- different carriers/ISPs
- multiple climates or operating profiles where relevant
- devices with optional peripherals
- realistic data and configuration

A canary fleet of only new lab devices is not representative.

### Cell-aware rollout

Roll out by regional or operational cell. Do not update every recovery cell simultaneously.

Keep one known-good population to preserve service and comparative telemetry.

---

## 8. Device-side update state machine

```text
NOTIFIED
  -> ELIGIBILITY_CHECK
  -> DOWNLOADING
  -> DOWNLOADED
  -> VERIFIED
  -> STAGED
  -> REBOOTING
  -> BOOT_VALIDATION
  -> HEALTHY
       or
     ROLLBACK
       -> PREVIOUS_VERSION_HEALTHY | RECOVERY_REQUIRED
```

Every transition is durable enough to survive power loss.

### Eligibility checks

Before download or install:

- model and hardware revision
- current software and allowed update path
- bootloader requirement
- storage
- power/battery
- temperature or operational state where relevant
- maintenance window
- network policy
- package expiry

### Download

- resumable chunks
- per-chunk integrity where useful
- final cryptographic hash
- bounded retry with jitter
- storage reservation
- cleanup of failed partial files

### Verification

Verify:

- manifest signature
- artifact signature
- artifact hash
- certificate or trust-chain validity according to device policy
- target device class
- version and anti-rollback counter
- expiry
- dependency versions

A valid signature on an artifact for another hardware model is not sufficient.

---

## 9. Safe installation and rollback

### A/B partitions

Preferred pattern for system images:

```text
active partition A
  -> write and verify inactive partition B
  -> set one-time boot target B
  -> reboot
  -> boot health checks
  -> commit B as active
  -> otherwise bootloader returns to A
```

### Transactional application update

For application packages:

- stage to a new directory or container image
- verify all files
- atomically switch a pointer
- preserve old version
- monitor health
- roll back atomically

### Health validation

Device-local health criteria can include:

- boot completed within deadline
- critical processes healthy
- filesystem valid
- network available, but do not require one fragile cloud dependency for boot success
- device-specific self-test
- no safety fault
- telemetry agent alive

### Anti-rollback

Prevent downgrade below a security floor through:

- monotonic secure counter
- bootloader-enforced minimum version
- signed manifest minimum
- emergency exception process with stronger trust

Rollback for availability must not silently reintroduce a revoked vulnerable version. Maintain approved rollback targets.

---

## 10. Device identity and authorization

Each device has a unique identity, commonly an X.509 certificate for AWS IoT Core.

Use:

- secure provisioning
- hardware-protected private keys where appropriate
- certificate rotation
- revocation
- device-specific IoT policy
- fleet indexing and inventory

A device may:

- subscribe only to its permitted job/command topics
- publish only its status and telemetry namespace
- retrieve only authorized artifacts or time-limited URLs

Do not use one shared fleet credential.

### Decommissioning

On retirement or compromise:

- revoke certificate
- remove group membership
- disable jobs
- remove package entitlement
- preserve audit according to retention policy

---

## 11. Update service independence

The update agent must be smaller, more stable, and more independent than the application it updates.

Avoid dependencies on:

- the new application process
- the main user interface
- the same network proxy configuration being replaced
- the same filesystem subtree being overwritten
- the same credential that the update rotates without overlap

Maintain an out-of-band recovery capability where product risk justifies it:

- bootloader recovery
- factory partition
- secondary communications path
- local service tool
- physical recovery procedure

If the update breaks the only update channel, cloud rollback is impossible.

---

## 12. Telemetry architecture at fleet scale

### Status events

Devices publish bounded state transitions, not constant high-volume progress spam.

Example:

```json
{
  "deviceId": "...",
  "jobId": "...",
  "packageVersion": "7.4.2",
  "state": "ROLLED_BACK",
  "reasonCode": "BOOT_HEALTH_TIMEOUT",
  "hardware": "rev-c",
  "timestamp": "..."
}
```

### Pipeline

```text
IoT Core rules
   |
   +--> Kinesis for high-volume ordered analytics
   +--> SQS for independent remediation work
   +--> Firehose/S3 for durable analytics archive
   +--> CloudWatch metrics for bounded operational signals
```

### Cardinality

Do not create one CloudWatch or Prometheus time series per device for millions of devices.

Aggregate by:

- release
- cohort
- hardware
- geography
- reason code
- stage

Use logs, streams, or a data lake for device-level drill-down.

### Telemetry storm control

A bad update can cause every device to reconnect and report simultaneously.

Use:

- client jitter
- bounded status retries
- broker and ingestion quotas
- queue buffering
- sampling for repetitive diagnostics
- separate critical status from verbose logs

---

## 13. Release gates and SLIs

### Rollout SLIs

- notification success
- download start and completion
- download throughput and error
- signature/hash failure
- install success
- reboot success
- healthy commit
- rollback rate
- heartbeat loss
- application crash or business failure

### Gate example

```text
Promote from 1% to 5% only when:
- at least N representative devices completed
- healthy commit >= 99.5%
- rollback <= 0.2%
- no severe safety reason code
- connectivity and crash SLIs within baseline
- observation window covers normal usage
```

Use confidence intervals and sample sufficiency. Zero failures among ten devices does not prove fleet safety.

### Abort versus pause

- **Pause:** stop new executions while preserving in-progress work for investigation.
- **Abort:** cancel according to job semantics and device behavior.

Devices must understand what cancellation means at every installation state. Do not interrupt a non-atomic flash operation unsafely.

---

## 14. Global and multi-Region design

### Regional artifact availability

Use S3 replication or another approved multi-Region artifact strategy. Verify:

- versioned object parity
- KMS key access
- manifest identity
- regional URL generation
- CloudFront origin failover where designed

### IoT endpoints and device routing

AWS IoT Core endpoints are regional. Design how devices select and fail over endpoints:

- provisioned primary and secondary endpoints
- regional device assignment
- DNS or bootstrap configuration
- certificate policy in both Regions
- duplicate session and status handling

Do not fail over devices to a Region without their registry, policy, job state, and package metadata being ready.

### Control-plane authority

Use one authoritative release decision per rollout. Avoid two Regions independently promoting the same release based on partial telemetry.

A global orchestrator or fenced regional leader coordinates:

- active job
- rollout stage
- pause/abort
- approved artifact
- cohort membership

### Regional isolation

A Region outage should not block devices in healthy Regions from:

- downloading an already approved artifact
- reporting critical status
- rolling back locally
- completing safe in-progress installation

---

## 15. Security incident response

### Signing key compromise

1. stop all rollout creation
2. revoke or disable compromised signing identity
3. distribute trust update through an independent trusted path if possible
4. identify artifacts and jobs signed during the exposure window
5. quarantine or block affected versions
6. rotate keys with overlap and device compatibility
7. preserve audit evidence

This scenario must be designed before the key is compromised.

### Malicious or incorrect release

- pause or abort rollout
- identify reached cohort
- invoke device rollback when safe
- block version in package policy
- preserve signed artifacts and approval history
- monitor devices that lost connectivity

### Device credential compromise

- revoke certificate
- remove from dynamic groups
- reject status or job access
- investigate lateral policy exposure
- re-provision through trusted recovery

---

## 16. Failure scenarios

### Download interrupted repeatedly

Resume chunks, renew URL for the same versioned object, enforce retry budget, and defer on unsuitable network.

### Power loss during installation

Transactional writes or A/B partition ensure one bootable version remains. Test power interruption at every write phase.

### Device offline for six months

On reconnect:

- authenticate and refresh inventory
- determine permitted update path
- avoid jumping across unsupported intermediate migrations
- apply current security floor
- use continuous job or orchestrated sequence

### Bad update disables normal application networking

Update agent and recovery channel remain functional; local boot validation rolls back without waiting indefinitely for cloud instruction.

### Telemetry says devices disappeared

Treat missing heartbeat as a possible failure signal. Compare carrier, geography, hardware, and release cohort; do not count only explicit `FAILED` reports.

### CDN or artifact Region unavailable

Select a verified alternate location for the same digest. Do not silently fall back to a different version.

---

## 17. Capacity and quota planning

Plan:

- IoT message and connection rates
- Jobs API and execution behavior
- S3 request and egress profile
- CloudFront distribution
- Kinesis shards or on-demand warm throughput
- queue backlog
- telemetry retention
- CloudWatch metric cardinality
- package size and global bandwidth

Load-test the control plane and data plane separately.

A million-device deployment does not mean a million simultaneous downloads. Rollout shaping is part of safety and capacity design.

---

## 18. Cost model

Major cost drivers:

- artifact egress
- IoT messaging
- telemetry ingestion
- stream retention
- CloudWatch logs and metrics
- device reconnect storms
- duplicate full-image downloads

Optimize through:

- immutable edge-cached artifacts
- delta updates after safety validation
- status-event aggregation
- controlled log verbosity
- lifecycle and retention policy
- regional traffic planning

Do not reduce rollback artifact retention below the operational recovery requirement.

---

## 19. Validation and game days

1. corrupt artifact bytes
2. alter unsigned manifest field
3. use wrong hardware target
4. replay an old signed job
5. attempt downgrade below security floor
6. expire presigned URL during download
7. disconnect and reconnect repeatedly
8. cut power during each installation phase
9. fail boot health and verify local rollback
10. release to a deliberately failing canary and verify abort
11. take artifact origin or Region offline
12. compromise a test device certificate
13. generate a fleet-wide reconnect/telemetry surge
14. test devices offline across multiple skipped releases
15. verify signing-key rotation and emergency revocation

---

## Adversarial follow-ups

### “Why use IoT Jobs instead of publishing one MQTT message?”

Jobs provide target selection, rollout control, timeout, abort configuration, execution state, and device status tracking. A raw message alone does not provide a fleet deployment control plane.

### “Does code signing prevent a bad release?”

It prevents unauthorized or modified code from being accepted when trust is correctly implemented. It does not prove the authorized software is functionally safe. Canary and device rollback remain essential.

### “Why not deploy to all devices immediately for a critical vulnerability?”

Urgency changes rollout speed, not the need for a canary and abort path. A broken security patch that bricks the fleet can create a larger and less recoverable exposure.

### “What if a device reports success but fails later?”

Use an observation window and post-install health telemetry before broad promotion. Success is not merely completion of the installer.

### “How do you support exactly-once update?”

The job notification may be repeated. The device makes installation idempotent by package digest/version, durable state machine, and committed active version. Repeated instructions return the existing result.

### “Why keep old artifacts?”

Rollback and long-offline upgrade paths may require them. Retention is governed by approved rollback targets, vulnerability policy, and device compatibility—not arbitrary storage cleanup.

---

## Weak answers to avoid

- “Put firmware in S3 and use CloudFront.”
- trusting TLS without artifact signing
- signing the binary but not compatibility metadata
- mutable artifact URLs
- no canary or abort threshold
- relying on explicit failure reports while ignoring disappeared devices
- cloud-only rollback with no local A/B or transactional mechanism
- shared device credentials
- no anti-downgrade control
- updating every Region and recovery cell simultaneously
- one metric per device in Prometheus
- update agent depends on the application being replaced

---

## Closing statement

> A fleet-update platform is a safety system. The cloud controls authorization, staging, and evidence; the artifact carries cryptographic provenance; and the device preserves a bootable trusted version and rejects incompatible, replayed, or downgraded software. Scale is achieved by controlled rollout, not by sending faster to everyone.