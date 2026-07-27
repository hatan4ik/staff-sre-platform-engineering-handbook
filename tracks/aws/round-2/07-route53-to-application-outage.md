# Question 7 — Customers Cannot Access an AWS Application: Route 53 to the Application

## Interview prompt

Customers suddenly cannot access an application hosted on AWS. Walk me through your troubleshooting process from Route 53 to the application.

## What the interviewer is testing

The interviewer wants a disciplined request-path investigation, not a random checklist. The strongest answer:

- establishes impact before touching infrastructure
- separates DNS, edge, load balancing, network, Kubernetes, application, and dependency layers
- traces one failing request with timestamps and correlation identifiers
- compares failing and healthy cohorts
- mitigates safely before pursuing perfect root cause
- preserves evidence before restarts or rollbacks
- proves recovery through external user-facing signals

---

## 90-second Staff/Principal answer

> I start by declaring the incident, measuring customer impact, and identifying the failing cohort: all users or one geography, ISP, tenant, protocol, device type, AZ, or release version. I freeze unrelated changes and capture an external failing request with timestamp, resolver, resolved IPs, TLS result, HTTP status, and trace or request ID.
>
> I then follow the request path in order. At Route 53 I verify delegation, record values, routing policy, TTL, health-check state, DNSSEC, and public query logs where enabled. I test from multiple independent resolvers because local caching can hide or preserve stale answers. At CloudFront, Global Accelerator, WAF, or the load balancer, I inspect endpoint health, certificate and SNI behavior, WAF blocks, listener rules, target health, access logs, resets, and capacity or quota signals.
>
> For the VPC path, I use Reachability Analyzer for configuration-level blockers and VPC Flow Logs for observed accepts or rejects, then validate security groups, NACLs, routes, endpoints, NAT, and subnet IP capacity. In EKS I check ingress or Gateway resources, Services, EndpointSlices, ready endpoints, NetworkPolicies, pod placement, recent deployments, and application logs and traces. Finally I inspect downstream dependencies such as DNS, Secrets Manager, database, cache, and third-party APIs.
>
> I mitigate at the narrowest safe layer—revert a bad Route 53 or WAF change, shift traffic to a healthy cell, roll back the release, or remove unhealthy targets—and confirm recovery with synthetic probes and customer success rate, not only green component health checks.

---

## 1. Establish incident facts

Before running commands, answer:

| Question | Why it matters |
|---|---|
| What user action fails? | Distinguishes DNS, TLS, authentication, API, and business failures |
| When did it start? | Defines the evidence window and change correlation |
| Is failure total or partial? | Reveals cohort, AZ, Region, or version boundaries |
| What does the client observe? | Timeout, NXDOMAIN, SERVFAIL, TLS error, 403, 5xx, reset, or wrong content imply different layers |
| What changed? | DNS, WAF, certificate, deployment, network policy, IAM, database, or autoscaling changes |
| What is the business impact? | Drives incident severity and mitigation speed |
| Is another Region or cell healthy? | Creates a mitigation option and comparison baseline |

### Capture one authoritative failing sample

Record:

```text
timestamp in UTC
client geography and network
resolver used
queried hostname and record type
returned DNS answer and TTL
resolved endpoint IP or alias
TCP connect result
TLS protocol, SNI, certificate chain, and error
HTTP method, path, status, headers, and latency
request ID, trace ID, or correlation ID
```

A vague statement such as “the website is down” is not an incident datum.

---

## 2. External differential tests

Run tests from:

- at least two public resolvers
- more than one geography or synthetic location
- inside the VPC
- inside the EKS cluster
- directly against the load balancer hostname where safe
- directly against a known backend only when it does not bypass required Host, TLS, or authentication behavior

Useful commands:

```bash
dig +trace app.example.com

dig app.example.com @1.1.1.1

dig app.example.com @8.8.8.8

dig A app.example.com +noall +answer

dig AAAA app.example.com +noall +answer

curl -sv --connect-timeout 5 --max-time 20 https://app.example.com/health

openssl s_client \
  -connect app.example.com:443 \
  -servername app.example.com \
  -showcerts </dev/null
```

Interpretation matters more than command volume.

---

## 3. Route 53 and DNS layer

### Delegation

Verify the registrar delegates to the authoritative name servers for the active hosted zone.

```bash
dig NS example.com

dig +trace app.example.com
```

Common failures:

- record changed in an unused hosted zone
- registrar name servers do not match the active Route 53 zone
- expired or incorrect domain registration
- broken DS record after DNSSEC changes
- parent-zone delegation mismatch

### Record content

Check:

- A, AAAA, CNAME, or Alias target
- record name and trailing-domain assumptions
- routing policy
- record identifier
- weight, geolocation, geoproximity, latency, or failover configuration
- TTL and expected cache lifetime
- health-check association
- Evaluate Target Health behavior for aliases

### Resolver behavior

Do not assume every client sees the current authoritative answer.

Recursive resolvers and operating systems cache responses until TTL expiry. Negative responses can also be cached. A corrected record does not instantly fix clients holding an older answer.

Compare:

```bash
dig app.example.com @<affected-resolver>

dig app.example.com @<independent-resolver>
```

### Public query logs

When enabled, Route 53 public query logs show queries that reach Route 53, including name, type, edge location, and response code.

Important limitation: they show queries received from recursive resolvers, not every end-user query. Cached resolver responses never reach authoritative Route 53 and therefore do not appear.

### Resolver query logs

For VPC-originated DNS, Route 53 Resolver query logging can expose:

- source VPC and instance or ENI context
- queried name and type
- response code such as `NOERROR`, `NXDOMAIN`, or `SERVFAIL`
- answer data
- DNS Firewall action

Cached answers served within the resolver may not produce a new log entry for every client query.

### Health checks

Validate the health check independently from the routing record.

Questions:

- Does the health check use the correct protocol and port?
- Is the Host header correct?
- Is the health path meaningful but dependency-safe?
- Is the check endpoint reachable from Route 53 health-check locations?
- Is the check attached to the intended record?
- Are calculated health checks or CloudWatch-alarm health checks stale or misconfigured?

Do not configure a circular health check where the health-check domain equals the record whose routing depends on that same check.

### DNS mitigation

Possible mitigations:

- revert the last record change
- restore the previous alias target
- disable a faulty health-check association
- shift weighted traffic to a healthy endpoint
- correct delegation or DNSSEC records

Do not lower TTL after the outage and expect existing cached answers to expire sooner. TTL changes affect new answers, not already cached responses.

---

## 4. Edge layer: CloudFront, Global Accelerator, WAF, and certificates

### CloudFront

Check:

- distribution deployment state
- alternate domain name configuration
- ACM certificate in the required Region for CloudFront
- origin domain, protocol, Host header, and origin path
- cache behavior and function or Lambda@Edge changes
- origin response status and latency
- cache hit ratio and origin error rate
- invalidation or stale-content behavior
- access logs and real-time logs where enabled

Differentiate:

```text
viewer -> CloudFront failure
CloudFront -> origin failure
origin generated failure cached by CloudFront
WAF-generated block
```

A cached 5xx can make a recovered origin look broken until cache behavior is understood.

### Global Accelerator

Check:

- accelerator and listener state
- endpoint-group traffic dials
- endpoint health
- client affinity configuration
- security groups allowing accelerator traffic paths
- whether traffic is unexpectedly concentrated in one endpoint group

### AWS WAF

A newly deployed managed-rule version, custom rule, rate-based rule, IP set, or bot control can block only a subset of users.

Inspect:

- sampled requests
- WAF logs
- terminating rule ID
- action: block, count, CAPTCHA, or challenge
- labels applied by managed rules
- scope-down statements
- rate-limit keys and aggregation windows

Safe mitigation may be changing a suspect rule from `BLOCK` to `COUNT` while preserving visibility.

### TLS and certificates

Check:

- certificate expiration
- Subject Alternative Name coverage
- SNI hostname
- full certificate chain
- ACM renewal validation
- load-balancer listener certificate association
- TLS security policy
- client compatibility
- certificate attached to the wrong endpoint or Region

A health check using plain HTTP can remain green while every HTTPS client fails.

---

## 5. Load balancer layer

### ALB

Inspect:

- listener and rule priority
- host and path matching
- redirect loops
- target-group association
- healthy and unhealthy host counts
- target response time
- HTTP 4xx and 5xx split by load balancer versus target
- rejected connections and resets
- access logs
- target registration and deregistration delay
- cross-zone and zonal distribution behavior

Distinguish:

- `HTTPCode_ELB_5XX_Count`: generated by the load balancer
- `HTTPCode_Target_5XX_Count`: generated by targets

### NLB

Inspect:

- TCP/TLS listener configuration
- target health
- connection resets
- source-IP preservation implications
- proxy protocol configuration
- security-group support and rules where used
- zonal health and cross-zone behavior

### Target health is not application truth

A shallow `/health` endpoint can return 200 while:

- login fails
- database writes fail
- one tenant shard is unavailable
- certificate validation fails in the real path
- only a new API route is broken
- a dependency is timing out

Use both target health and transaction-level synthetic checks.

### Direct target test

When safe, test the target using the required Host header:

```bash
curl -sv \
  -H 'Host: app.example.com' \
  http://<target-ip>:<port>/health
```

Do not confuse a successful direct test with proof that the full Route 53, TLS, WAF, and load-balancer path is healthy.

---

## 6. VPC network path

### Reachability Analyzer

Use Reachability Analyzer to analyze configuration between a supported source and destination. It identifies path components and blockers such as:

- route tables
- security groups
- network ACLs
- load balancer configuration
- transit or peering paths where supported

It is a configuration analysis tool, not a packet capture and not proof of runtime application health.

### VPC Flow Logs

Use Flow Logs to determine whether observed traffic is accepted or rejected and to identify source, destination, ports, interface, and time window.

Questions:

- Does the expected traffic arrive at the ENI?
- Is it accepted or rejected?
- Is return traffic visible?
- Is the source IP what the security rule expects?
- Are flows asymmetric?
- Are logs delayed relative to the incident window?

An `ACCEPT` record proves the network policy allowed the flow, not that the application accepted or answered it.

### Security groups

Validate both directions through stateful behavior:

- load balancer to target
- node or pod to database
- control plane to webhooks or kubelet where relevant
- pod or node to AWS endpoints

Look for references to the wrong security group after resource replacement.

### Network ACLs

NACLs are stateless. Verify both request and response ports, including ephemeral ranges.

NACL mistakes often produce partial or asymmetric timeout symptoms.

### Routes and gateways

Check:

- route-table association for the actual subnet
- Internet Gateway route
- NAT Gateway route and health
- Transit Gateway or peering propagation
- return path
- blackhole routes
- more-specific route overriding the intended path

### NAT and egress

An inbound application can fail because it cannot call an external dependency.

Inspect:

- NAT gateway errors and port allocation
- per-destination connection concentration
- route changes
- firewall or proxy changes
- VPC endpoint DNS and endpoint policy
- third-party allow lists expecting a different source IP

### Subnet IP exhaustion

EKS pods, load balancers, and replacement nodes require IP addresses. Check available IPs per subnet and recent scaling or deployment surge.

A service can become partially unavailable when new pods cannot obtain IPs while existing pods remain healthy.

---

## 7. EKS and Kubernetes path

### Ingress or Gateway

Inspect:

```bash
kubectl get ingress,gateway,httproute -A
kubectl describe ingress -n <namespace> <name>
```

Check:

- class or controller ownership
- host and path rules
- annotations
- listener and certificate configuration
- controller reconciliation errors
- generated ALB/NLB resources
- recent manifest changes

### Service and EndpointSlices

```bash
kubectl get svc -n <namespace>
kubectl get endpointslice -n <namespace> -l kubernetes.io/service-name=<service>
kubectl describe svc -n <namespace> <service>
```

Common failures:

- Service selector does not match pod labels
- wrong `targetPort`
- no ready endpoints
- only endpoints in an impaired AZ
- named port mismatch
- stale target registration

### Pods

```bash
kubectl get pods -n <namespace> -o wide
kubectl describe pod -n <namespace> <pod>
kubectl logs -n <namespace> <pod> -c <container> --since=30m
```

Inspect:

- readiness
- restart count
- image and digest
- node and AZ placement
- resource pressure
- startup duration
- environment and mounted configuration
- termination events

### NetworkPolicy

Check both ingress and egress policies and the actual labels selected.

A policy change can affect only:

- one namespace
- one version label
- one dependency port
- pods on one dataplane mode

### CoreDNS and service discovery

Test from an affected pod:

```bash
kubectl exec -n <namespace> <pod> -- getent hosts dependency.namespace.svc.cluster.local
```

Inspect CoreDNS latency, errors, throttling, pod health, and upstream resolution.

### Node and AZ concentration

Compare failures by:

- node
- AZ
- instance type
- capacity type
- CNI mode
- kernel or AMI version

A healthy aggregate can hide one broken cohort.

---

## 8. Application and dependency layer

### Application evidence

Search by the captured request or trace ID.

Inspect:

- application logs
- distributed traces
- deployment events
- feature flags
- configuration revisions
- thread or connection pool saturation
- garbage collection
- retry volume
- business error codes

### Database

Check:

- connection count and pool saturation
- authentication failures
- writer or reader endpoint resolution
- failover events
- replication lag
- lock waits and slow queries
- storage and I/O pressure
- max connections

### Cache

Check:

- hit ratio
- evictions
- hot keys
- connection count
- node or shard failover
- client timeout and retry behavior

### Secrets and identity

Check:

- Secrets Manager or Parameter Store access errors
- KMS decrypt failures
- Pod Identity or IRSA association
- credential expiration and SDK refresh
- CloudTrail `AccessDenied` events

### Third-party dependencies

Validate from the workload's actual egress path, not a laptop.

Check:

- DNS
- TLS trust
- source IP allow list
- rate limits
- provider status
- timeout and retry policy

---

## 9. Mitigation decision tree

```text
DNS answer wrong?
  -> restore previous record or route to healthy endpoint

WAF blocks valid traffic?
  -> change suspect rule to COUNT or revert safely

One cell/AZ unhealthy?
  -> remove or reduce traffic to that failure domain

Bad release correlated?
  -> stop rollout and restore known-good digest

Target health false-negative?
  -> correct health path only after proving application health

Dependency saturated?
  -> shed optional traffic, disable expensive feature, increase safe capacity,
     or reduce retries

Unknown but rapidly worsening?
  -> reduce blast radius and preserve evidence before broad restarts
```

Prefer the smallest reversible mitigation that restores customers.

---

## 10. Prove recovery

Recovery evidence should include:

- external synthetic transaction succeeds
- DNS answers are correct from independent resolvers
- TLS succeeds with the expected certificate
- customer success rate recovers
- p95 and p99 latency recover
- error budget burn returns to normal
- affected cohort recovers, not only the majority
- queue and dependency saturation stabilize
- no new retry or reconnection storm appears

Do not close the incident because:

- pods are Running
- nodes are Ready
- the load balancer has healthy targets
- one engineer can curl from inside the VPC

---

## 11. Useful evidence sources

| Layer | Evidence |
|---|---|
| DNS | `dig`, delegation, Route 53 records, public query logs, Resolver query logs, CloudTrail |
| Edge | CloudFront logs and metrics, WAF logs, Global Accelerator endpoint health |
| TLS | `openssl s_client`, ACM status, listener certificate associations |
| Load balancer | metrics, access logs, listener rules, target health |
| VPC | Reachability Analyzer, VPC Flow Logs, routes, SGs, NACLs, subnet IPs |
| EKS | control-plane logs, audit logs, events, Services, EndpointSlices, controller logs |
| Application | structured logs, OpenTelemetry traces, profiles, deployment and feature-flag history |
| Dependencies | RDS/Aurora, ElastiCache, SQS, Secrets Manager, KMS, external-provider telemetry |
| Change history | CloudTrail, Git, GitOps sync history, CI/CD records, Config timeline |
| AWS service events | AWS Health events and account-specific notifications |

---

## Adversarial follow-ups

### “Route 53 is healthy. What next?”

A healthy authoritative DNS service only proves it can answer according to configuration. I still verify the answer, resolver caches, endpoint reachability, TLS, WAF, load balancer, targets, and the business transaction.

### “The ALB says all targets are healthy.”

I test the actual user path and inspect target-generated errors. A shallow health endpoint may not cover authentication, tenant data, writes, or downstream dependencies.

### “Would you restart the pods?”

Not as a first diagnostic step. Restarting destroys process state and may temporarily hide the symptom. I preserve previous logs, events, traces, memory or thread evidence where available, then restart only as a deliberate mitigation.

### “How do you distinguish DNS caching from a bad record?”

I compare authoritative answers and independent recursive resolvers, inspect TTLs and query logs, and test from the affected resolver. A corrected authoritative answer can coexist with stale cached client answers.

### “Why use Reachability Analyzer and Flow Logs?”

Reachability Analyzer explains whether configuration permits a modeled path. Flow Logs show observed network flows and accept or reject decisions. Neither alone proves application success.

---

## Weak answers to avoid

- “Check Route 53, then check the load balancer, then restart pods.”
- troubleshooting only from a corporate laptop
- changing DNS without checking TTL and resolver caching
- assuming a green health check proves the user transaction
- ignoring WAF, TLS, IPv6, and cohort-specific failures
- reading aggregate metrics without AZ, version, tenant, or geography dimensions
- broad security-group changes as a diagnostic shortcut
- bypassing the full path and declaring recovery from an internal curl
- failing to capture timestamps, request IDs, and change history

---

## Closing statement

> I troubleshoot availability as a request-path proof. At every boundary I ask whether the request arrived, whether policy allowed it, whether the component processed it, and whether the response returned. I mitigate at the narrowest reversible layer and declare recovery only from external customer evidence.