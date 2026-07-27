# Question 14 — Highly Available Mobile Backend for Authentication, Notifications, Remote Access, and Preferences

## Interview prompt

Design a highly available backend on AWS for a mobile application supporting authentication, notifications, remote access, and user preferences.

## What the interviewer is testing

This is not merely an API Gateway diagram. The interviewer is testing whether you can separate four workloads with different consistency and security requirements:

- authentication and session establishment
- ordinary mobile API requests
- asynchronous notification delivery
- remote commands to a device or protected resource
- durable user-preference synchronization

A Staff/Principal answer defines the command trust model, handles mobile retries and intermittent connectivity, and distinguishes “accepted by the cloud” from “executed by the remote device.”

---

## 90-second Staff/Principal answer

> I would first clarify scale, geography, latency, data residency, RTO/RPO, and what “remote access” controls. A remote unlock or device-control operation has a stronger authorization and audit model than updating a theme preference.
>
> I would front the service with Route 53, CloudFront where caching applies, WAF, and either API Gateway or ALB into regional EKS or Lambda services. Amazon Cognito provides user authentication, federation, MFA, and token issuance; for authentication disaster recovery I would evaluate Cognito multi-Region user-pool replication and design the mobile client or backend to route authentication to the healthy Region.
>
> I keep the synchronous API stateless. DynamoDB stores user preferences, command state, idempotency records, device registrations, and notification preferences; Global Tables are appropriate when multi-Region active access and the data-conflict model fit. EventBridge, SNS, SQS, and Lambda or EKS workers decouple notifications and background work. Mobile push goes through SNS mobile push or AWS End User Messaging Push to APNs and FCM, with token lifecycle and delivery-status handling.
>
> Remote commands use a separate command service. It authenticates the user, checks device ownership and policy, creates a short-lived unique command with an idempotency key and monotonic sequence or fencing token, then delivers it through AWS IoT Core MQTT. The device validates identity, expiry, replay protection, and local safety conditions before execution and returns an acknowledgement. The API reports `accepted`, `delivered`, `executed`, or `expired`; it never claims success simply because a message was published.
>
> I deploy independent regional cells, use progressive delivery, protect every dependency with deadlines, bounded retries, queues, and load shedding, and prove the architecture with authentication failover, regional evacuation, push-provider failure, duplicate command, offline-device, and stale-preference tests.

---

## 1. Clarify the system before selecting services

State assumptions or ask:

| Dimension | Example design question |
|---|---|
| Users | Millions registered, hundreds of thousands concurrently active? |
| Regions | One market, global, or regulatory residency boundaries? |
| API latency | p99 target for reads, writes, and remote-command acceptance? |
| Remote target | Vehicle, appliance, workstation, building, or another user session? |
| Command semantics | Best effort, exactly-once business effect, or safety-critical? |
| Offline duration | Seconds, hours, or weeks? |
| Notification type | Transactional, marketing, critical alert, silent data refresh? |
| Preferences | Last-write-wins acceptable, or field-level merge required? |
| Authentication | Passwordless, social/OIDC/SAML federation, MFA, passkeys? |
| Recovery | Regional RTO/RPO and acceptable degraded mode? |

Do not use one availability objective for every capability.

Example:

```text
Authentication: 99.99% availability, low write volume, strict security
Preference reads: 99.95%, eventual consistency often acceptable
Remote-command acceptance: 99.99%, full audit and replay resistance
Push notification: asynchronous, provider-dependent delivery objective
```

---

## 2. Reference architecture

```text
Mobile clients
     |
Route 53 / Global Accelerator where useful
     |
CloudFront -- WAF -- Shield
     |
API Gateway or ALB
     |
Regional application cell
+-------------------------------+
| Auth adapter / token verifier |
| Mobile API services           |
| Preference service            |
| Command service               |
| Notification service          |
+-------------------------------+
     |          |          |
     |          |          +--> EventBridge / SNS / SQS
     |          |                    |
     |          |                    +--> push workers
     |          |                         |
     |          |                         +--> SNS mobile push or
     |          |                              End User Messaging Push
     |          |                              -> APNs / FCM
     |          |
     |          +--> AWS IoT Core MQTT
     |                    |
     |                    +--> remote devices
     |                           |
     |                           +--> command acknowledgements
     |
     +--> DynamoDB / Global Tables
          ElastiCache where justified
          S3 for durable objects

Identity:
Cognito user pools / federation / MFA

Observability:
OpenTelemetry -> CloudWatch / X-Ray
Prometheus -> AMP -> Managed Grafana
CloudTrail / WAF / IoT audit logs
```

For high scale, repeat the regional cell and assign users or devices to a home cell to bound failure and consistency complexity.

---

## 3. Edge and API entry

### Route 53

Use Route 53 for DNS ownership, latency or failover records, and controlled regional routing.

DNS failover is not instantaneous for every client because recursive resolvers and mobile operating systems cache answers. Design connection retry and endpoint discovery accordingly.

### Global Accelerator

Consider Global Accelerator when stable anycast IP addresses, rapid endpoint-health routing, or long-lived TCP connection behavior justify it. It does not solve data replication or authentication failover.

### CloudFront

Use CloudFront for:

- static mobile configuration
- public assets
- cacheable read APIs
- signed or authenticated object delivery where designed

Do not cache user-specific responses without a correct cache key and authorization boundary.

### WAF and Shield

Apply:

- managed rules
- rate-based rules
- bot and abuse controls where needed
- per-operation limits
- explicit monitoring before high-risk block changes

Remote-command endpoints should have stronger rate and anomaly controls than ordinary preference reads.

### API Gateway versus ALB

Use **API Gateway** when the product needs managed API keys or usage plans, request validation, throttling, WebSocket APIs, direct integrations, and serverless-style routing.

Use **ALB** when routing primarily to EKS/ECS HTTP services, cost and connection patterns favor a load balancer, and the application owns more API policy.

A hybrid is valid, but avoid duplicating authentication, throttling, and routing rules across multiple uncoordinated gateways.

---

## 4. Authentication architecture

### Cognito user pools

Use Cognito for:

- user directory
- OIDC/OAuth token issuance
- federation
- MFA and adaptive controls where configured
- managed login or application-integrated authentication

Validate tokens locally through cached public keys where appropriate. Do not call Cognito synchronously on every API request merely to validate a JWT.

### Multi-Region authentication

Cognito multi-Region user-pool replication can create a replica user pool for continuity. The design must still account for:

- authoritative administrative and directory writes
- custom-domain failover
- regional API endpoint selection for SDK-based clients
- third-party identity-provider configuration
- client configuration and token issuer behavior
- failover testing

The mobile client should not hardcode one regional endpoint without a recovery mechanism.

### Token strategy

- short-lived access tokens
- refresh-token rotation according to the product threat model
- audience and issuer validation
- clock-skew tolerance within policy
- key rotation
- token revocation or risk response for high-value operations

### Step-up authentication

Require recent or stronger authentication for sensitive remote commands:

```text
normal session
  -> user requests remote unlock
  -> policy requires recent MFA or device-bound proof
  -> command authorization token issued with narrow scope and short expiry
```

A valid broad mobile session should not automatically authorize every remote action.

---

## 5. Authorization model

Authentication proves an identity. Authorization proves that identity may perform this operation on this target now.

Check:

- user owns or is delegated access to the device
- requested command is allowed for the device state and user role
- account is not suspended
- geographic or regulatory condition
- risk score and recent authentication
- command rate and velocity
- device certificate and registration state
- command expiry and sequence

Use a policy service or consistent authorization library. Avoid embedding slightly different ownership rules in every microservice.

### Prevent confused-deputy behavior

Every internal request carries:

- authenticated subject
- target resource
- intended action
- original request ID
- authorization decision or policy version

A downstream worker must not infer authorization solely from being able to read an SQS message.

---

## 6. Ordinary mobile API services

Keep request-serving services stateless.

Use:

- EKS for long-running services, custom networking, sidecars, or a broad microservice platform
- Lambda for bursty event handlers and simple APIs when cold-start and runtime limits fit
- ECS/Fargate where Kubernetes is unnecessary

Do not select EKS only because the interview title says DevOps. Explain the operating trade-off.

### Mobile retry behavior

Mobile networks cause retries, reconnects, and request duplication.

Every mutating API should support:

- idempotency key
- request expiry
- bounded server-side retry
- stable operation result lookup
- explicit conflict response

Example:

```text
POST /commands
Idempotency-Key: 8bf2...

same identity + same key + same request hash
  -> return original command result

different request hash with same key
  -> reject as conflict
```

---

## 7. User preferences

### DynamoDB data model

Example keys:

```text
PK = USER#<user-id>
SK = PREFS#<namespace>
```

Store:

- preference document or bounded groups
- schema version
- update timestamp
- logical version
- writer region or device ID where needed

### Conditional writes

Use optimistic concurrency:

```text
update where version = expected_version
set version = version + 1
```

Return a conflict instead of silently overwriting important concurrent edits.

### Global Tables conflict model

Global Tables provide multi-Region replication, but application conflict semantics remain your responsibility.

Determine whether:

- last-writer-wins is acceptable
- preferences can be merged by field
- one home Region should own writes
- some fields require a stronger workflow

Do not put security-critical authorization state in a casual last-writer-wins preference document.

### Offline mobile changes

The client should carry:

- local mutation ID
- base version
- mutation timestamp for UX only, not sole conflict authority
- merge behavior

Server response distinguishes accepted, conflict, and invalid schema.

---

## 8. Notification architecture

### Event flow

```text
business event
   |
EventBridge or SNS topic
   |
   +--> SQS notification queue
   |       |
   |       +--> push worker
   |              |
   |              +--> APNs / FCM through AWS notification service
   |
   +--> audit / analytics / email / SMS consumers
```

Use SQS between event production and provider delivery to absorb bursts and provider throttling.

### Service selection

- **SNS mobile push** supports direct or topic-based delivery to platform endpoints for APNs, FCM, and other supported providers.
- **AWS End User Messaging Push** is the current name for the push capabilities formerly associated with Amazon Pinpoint and supports transactional push channels.

Choose one operational model deliberately; do not store the same device token independently in multiple notification systems without a lifecycle owner.

### Device-token lifecycle

Tokens change after reinstall, device restore, provider changes, or application lifecycle events.

The mobile app re-registers its token idempotently. The backend:

- associates token with user, app, platform, and environment
- handles token replacement
- disables invalid endpoints
- processes delivery failure events
- removes stale associations
- prevents one token from leaking notifications across users

### Delivery semantics

Push provider acceptance is not user receipt.

Track:

```text
event created
queued
provider accepted
provider rejected
expired
opened or acknowledged, only when application telemetry supplies it
```

Use TTL so obsolete notifications are not delivered late.

### Notification preference enforcement

Apply user preference, legal consent, quiet hours, and critical-message policy at a deterministic point before provider send.

Critical security notifications should not be accidentally disabled by a marketing preference flag.

---

## 9. Remote-command architecture

### Separate command state machine

```text
REQUESTED
  -> AUTHORIZED
  -> QUEUED
  -> DELIVERED
  -> ACKNOWLEDGED
  -> EXECUTING
  -> SUCCEEDED | FAILED | EXPIRED | REJECTED
```

The API response must name the state precisely.

### Command record

Store:

```text
command_id
idempotency_key
user_id
resource/device_id
action
parameters hash
created_at
expires_at
sequence/fencing token
policy decision/version
status
status revision
acknowledgement evidence
```

### AWS IoT Core MQTT

Use device-specific topics with least-privilege IoT policies.

Conceptual topics:

```text
commands/<device-id>/request
commands/<device-id>/ack
commands/<device-id>/result
```

Policies should constrain a device certificate to its own topic namespace. Avoid wildcard policies that let one compromised device subscribe to another device's commands.

### AWS IoT Jobs versus immediate commands

Use IoT Jobs for tracked long-running remote operations such as firmware update, reboot, certificate rotation, or diagnostics. Use a dedicated command protocol for low-latency interactive actions.

Do not use Device Shadow desired state as a simplistic exactly-once command queue. Shadows are useful for desired state and synchronization; commands need unique identity, expiry, replay protection, and explicit result semantics.

### Device-local authority

The remote device independently validates:

- cloud and command signature or authenticated MQTT source
- target device identity
- command expiry
- sequence or nonce
- prior execution
- local safety and physical conditions
- software compatibility

The cloud requests an operation; the device remains authoritative for local safety.

### Replay and duplicate protection

- unique command ID
- device-maintained recent-command journal
- monotonic sequence or fencing token where ordering matters
- short expiration
- parameter hash
- idempotent device handler

At-least-once message delivery must not create repeated physical action.

### Offline device

Return:

```text
accepted by cloud; device offline; command expires at <time>
```

Decide per command whether it may execute after reconnect. A remote unlock requested now should normally expire quickly; a configuration update may remain pending.

---

## 10. Regional architecture

### Cell model

```text
Global routing
   |
   +--> Region A / cell A
   |      API, command, notification, preferences
   |
   +--> Region B / cell B
          API, command, notification, preferences
```

Assign users or devices to a home cell when practical. Benefits:

- bounded blast radius
- simpler command ordering
- lower cross-Region write conflict
- independent deployment
- controlled evacuation

### Data choices

| Data | Potential strategy |
|---|---|
| Authentication | Cognito multi-Region replication and tested client/backend routing |
| Preferences | DynamoDB Global Tables or home-Region writes plus replica reads |
| Command state | home-cell writer with replicated audit; deliberate failover fencing |
| Notification events | regional queues with replayable source events |
| Device registry | replicated inventory with single authority per device |
| Audit | immutable regional ingestion and centralized archive |

### Avoid hidden regional dependencies

A “secondary” Region is not independent if it still requires:

- primary-region cache
- primary KMS key or secret path
- one regional CI control plane
- primary database writer
- primary IoT endpoint without failover behavior
- primary notification-token database

Test with the primary Region deliberately unavailable.

---

## 11. Security architecture

### Human and service identity

- federated short-lived AWS access
- workload identity per service
- no static AWS keys
- least-privilege KMS, DynamoDB, SNS, SQS, and IoT permissions
- separate production and non-production accounts

### Device identity

- unique certificate per device
- secure provisioning
- certificate rotation and revocation
- device registry ownership
- IoT policy variables or explicit topic restrictions
- hardware-backed key storage where product risk justifies it

### Data protection

- TLS in transit
- KMS encryption at rest
- field-level protection for highly sensitive data
- log and trace redaction
- no access or refresh tokens in logs
- explicit retention and deletion workflows

### Abuse protection

- per-user and per-device command rates
- impossible-travel or unusual-command detection where relevant
- notification-spam protection
- account takeover response
- WAF and API throttling
- command velocity and high-risk-operation alerts

### Audit

Record every remote command with:

- requesting identity
- authorization result
- device
- action
- timestamps
- status transitions
- policy version
- device acknowledgement

Audit data should be tamper resistant and access controlled.

---

## 12. Reliability controls

### Timeouts and retries

Every synchronous call has a deadline shorter than the caller's remaining deadline.

Retries are:

- bounded
- exponential with jitter
- limited by a retry budget
- used only for retryable operations
- paired with idempotency

### Bulkheads

Separate capacity and queues for:

- login
- preference API
- remote commands
- push notifications
- analytics

A marketing-notification burst must not starve remote commands.

### Load shedding

During overload:

1. preserve authentication and high-value commands
2. serve cached preference reads where safe
3. defer noncritical notification and analytics work
4. reject excess work explicitly with retry guidance

### Backpressure

Queue consumers scale from backlog and age while respecting provider and database limits.

Scaling workers without downstream rate control can amplify failure.

---

## 13. Observability and SLOs

### Authentication

- login success by provider and Region
- token refresh success
- MFA challenge success
- p95/p99 latency
- failover state

### API

- success, latency, traffic, saturation
- version, cell, AZ, and route dimensions
- mobile retry and duplicate rate

### Commands

- authorization success/failure
- accepted-to-delivered latency
- delivered-to-acknowledged latency
- execution success
- expiry and duplicate suppression
- offline-device rate

### Notifications

- queue age
- provider acceptance and rejection
- invalid-token rate
- delivery backlog
- provider-specific throttling

### Preferences

- read/write latency
- conditional-write conflict
- replication lag
- stale-read or merge metrics

### Example SLOs

```text
99.99% of valid remote-command requests accepted within 500 ms
99% of online-device commands acknowledged within 3 seconds
99.95% preference reads succeed within 250 ms
99.99% authentication transactions succeed excluding documented IdP failures
```

Define provider-dependent exclusions carefully; do not exclude every failure you cannot control.

---

## 14. Failure scenarios

### Cognito primary Region unavailable

- route managed login or client API selection to replica
- verify existing token validation
- constrain administrative writes if the service has primary-authority limitations
- test sign-in, refresh, MFA, federation, and recovery

### APNs or FCM degradation

- queue with TTL
- avoid infinite retry
- surface delayed-notification status
- preserve critical in-app inbox or polling fallback where product requirements justify it

### Device offline

- expire short-lived commands
- retain suitable long-running jobs
- show honest command status
- avoid reconnect storms through jitter

### Duplicate command delivery

- device journal rejects already executed command ID
- cloud returns original result for the idempotency key

### Region evacuation

- fence the old command writer
- switch home-cell routing
- verify replicated state freshness
- avoid two Regions concurrently issuing ordered commands without a conflict protocol

### Preference conflicts

- return or resolve conditional-write conflict
- merge only fields with defined semantics
- never use client wall-clock alone as authority

---

## 15. Validation plan

1. load test API, authentication, command, and notification paths independently
2. replay duplicate mobile requests
3. test expired and reordered commands
4. disconnect devices during delivery and reconnect after expiry
5. rotate device and push-provider credentials
6. fail one AZ
7. evacuate one Region
8. fail Cognito primary routing and exercise replica authentication
9. throttle APNs/FCM path and verify queue TTL behavior
10. inject preference write conflicts across Regions
11. test account takeover and command abuse controls
12. verify audit completeness under load

---

## Adversarial follow-ups

### “Why not use one Lambda and one DynamoDB table?”

It can be a valid small-system start, but I would still separate authorization, command state, queues, and capacity boundaries. The logical architecture and failure domains matter even if initially deployed in fewer compute units.

### “Does MQTT guarantee the remote operation happened?”

No. Publish success proves broker acceptance, not device execution. The device returns authenticated acknowledgements and results through an explicit command state machine.

### “Would you use a Device Shadow for remote unlock?”

Not as the only command mechanism. Desired state is different from a unique short-lived action. A command needs identity, expiry, replay protection, authorization evidence, and explicit execution result.

### “How do you get exactly-once remote execution?”

Transport is generally at-least-once. I create exactly-once business effect through unique command IDs, idempotent handlers, a device-side execution journal, sequence or fencing controls, and durable result lookup.

### “Cognito is managed. Why discuss multi-Region?”

Managed regional availability does not automatically provide application-level regional continuity. Endpoint routing, directory write authority, federation, client behavior, and failover testing still matter.

### “Why not send notifications directly from the request handler?”

Provider latency and throttling would couple user requests to an external asynchronous service. A durable event and queue isolate failure and support retry, TTL, and independent scaling.

---

## Weak answers to avoid

- listing Cognito, API Gateway, DynamoDB, and SNS without request flows
- claiming a published MQTT message means the device executed the command
- using Device Shadow as an exactly-once command queue
- no command expiry or replay protection
- storing push tokens without lifecycle and invalidation handling
- one retry policy for every operation
- treating Global Tables as conflict-free strong consistency
- active-active command writers without fencing
- returning “success” while the device is offline
- no regional authentication test

---

## Closing statement

> I separate identity, ordinary API state, asynchronous notification delivery, and remote command execution because they have different trust and consistency models. The backend is highly available only when the mobile client, regional data, notification providers, and remote device all have explicit failure and recovery semantics.