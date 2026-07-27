# Route 53-to-Application Outage Troubleshooting

## Interview prompt

Users report that `api.example.com` is unavailable. The service runs on Amazon EKS behind an Application Load Balancer. Explain how you would diagnose and mitigate the incident from DNS through the application.

## 90-second Staff/Principal answer

I would first establish user impact, incident command, and a single timeline. Then I would test the request path layer by layer: Route 53 resolution, DNS delegation and health checks, edge or WAF behavior, ALB listener and target health, VPC routing and security controls, Kubernetes ingress and service endpoints, and finally pod readiness and dependency health.

I would avoid changing several layers at once. I would compare a failing request with a known-good path, segment by Region, Availability Zone, client resolver, IPv4 versus IPv6, and deployment version, and preserve evidence before mitigation.

The fastest safe mitigation depends on the failed layer. Examples include correcting an erroneous DNS record, lowering traffic to a broken Region, restoring a previous ALB or ingress configuration, rolling back a deployment, or temporarily routing to a known-good static maintenance response. Recovery is confirmed through external synthetic checks and user-facing success rate and latency, not merely healthy pods.

After stabilization, I would identify why existing controls failed: missing health-check coverage, unsafe DNS change procedure, ALB target-registration lag, stale endpoints, probe design, or an untested dependency. Corrective actions would have owners, deadlines, and a game day.

---

## Assumptions

- Public API endpoint: `api.example.com`
- Route 53 public hosted zone
- Optional CloudFront or AWS WAF layer
- ALB created by AWS Load Balancer Controller
- EKS workloads spread across three Availability Zones
- Service objective: 99.95% monthly availability
- Initial incident objective: restore service before performing deep root-cause analysis

## Request-path map

```text
Client
  |
  v
Recursive resolver
  |
  v
Route 53 hosted zone / alias record
  |
  v
CloudFront or direct ALB
  |
  v
WAF / ALB listener / listener rule
  |
  v
ALB target group
  |
  v
EKS node or pod target
  |
  v
Ingress -> Service -> EndpointSlice -> Pod
  |
  v
Database / cache / queue / external dependency
```

## STABILIZE incident flow

### S — State impact and command

Capture:

- start time and detection source
- affected endpoint, customer cohorts, and Regions
- status-code distribution and latency
- whether failures are total, intermittent, or resolver-specific
- recent DNS, ALB, ingress, network-policy, and application changes

Assign incident commander, operations lead, communications lead, and scribe.

### T — Time-box triage and preserve evidence

Before changing resources, preserve:

- Route 53 record values and TTLs
- ALB listener rules and target-health output
- ingress, service, and EndpointSlice manifests
- Kubernetes events
- deployment revision and rollout history
- CloudTrail events for DNS, ELB, IAM, and EKS changes
- external probe results from multiple networks

### A — Analyze from the user path inward

#### 1. DNS and delegation

```bash
dig api.example.com A +trace
dig api.example.com AAAA
dig @1.1.1.1 api.example.com
dig @8.8.8.8 api.example.com
```

Check:

- authoritative name servers match the registrar delegation
- record name and hosted zone are correct
- alias points to the expected ALB or CloudFront distribution
- no accidental `AAAA` path is broken while `A` works
- TTL and negative caching explain delayed recovery
- Route 53 health checks and failover-routing state are correct
- DNSSEC is valid if enabled

A frequent trap is assuming that because the Route 53 console contains the correct record, all recursive resolvers have the same answer. Verify externally.

#### 2. TLS, edge, and WAF

```bash
curl -vk https://api.example.com/health
openssl s_client -connect api.example.com:443 -servername api.example.com
```

Check:

- certificate name, expiration, and chain
- SNI behavior
- CloudFront origin health and cache behavior
- WAF blocks, rate-based rules, and bot-control changes
- whether a recent managed-rule update is rejecting valid traffic

#### 3. ALB listeners and target groups

```bash
aws elbv2 describe-load-balancers
aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN"
aws elbv2 describe-rules --listener-arn "$LISTENER_ARN"
aws elbv2 describe-target-health --target-group-arn "$TG_ARN"
```

Validate:

- listener exists on the expected port
- default and host/path rules are ordered correctly
- target group protocol, port, and health-check path match the workload
- unhealthy-reason codes
- deregistration delay and slow-start behavior
- target type (`instance` or `ip`) matches the controller configuration
- targets are registered in every intended Availability Zone

#### 4. VPC and security path

Check:

- ALB security-group ingress from the internet or CloudFront prefix list
- target security-group ingress from the ALB security group
- subnet routes and network ACLs
- public subnet Internet Gateway route for internet-facing ALBs
- IP exhaustion in ALB or worker subnets
- cross-zone behavior and zonal target distribution
- VPC Flow Logs for rejects

#### 5. Kubernetes ingress and service discovery

```bash
kubectl get ingress -A
kubectl describe ingress -n app api
kubectl get svc -n app api -o yaml
kubectl get endpointslice -n app -l kubernetes.io/service-name=api
kubectl get pods -n app -o wide
kubectl get events -n app --sort-by=.lastTimestamp
```

Validate:

- ingress class and annotations
- AWS Load Balancer Controller reconciliation errors
- service selector matches pod labels
- EndpointSlices contain ready pod IPs
- readiness gates are satisfied when target health is integrated
- pod ports match the service `targetPort`
- network policies allow ingress and dependency egress

#### 6. Application and dependencies

```bash
kubectl logs -n app deploy/api --since=15m
kubectl exec -n app deploy/api -- curl -sS http://127.0.0.1:8080/ready
kubectl exec -n app deploy/api -- curl -sS http://dependency.namespace.svc.cluster.local:8080/health
```

Inspect:

- error rate and saturation
- thread, connection, and file-descriptor exhaustion
- database or cache connection pools
- retry storms and timeouts
- dependency DNS failures
- expired credentials or secrets
- partial rollout by ReplicaSet or node group

### B — Bound the blast radius

Build a comparison matrix:

| Dimension | Example comparison |
|---|---|
| DNS resolver | ISP resolver vs public resolver |
| Network family | IPv4 vs IPv6 |
| Region | primary vs secondary |
| Availability Zone | `us-east-1a` vs `1b` vs `1c` |
| Target health | healthy vs unhealthy target group members |
| Version | old ReplicaSet vs new ReplicaSet |
| Client path | CloudFront vs direct ALB |
| Request type | read vs write, host/path rule A vs B |

This prevents a broad rollback when only one cohort is affected.

### I — Implement the safest mitigation

Preferred order:

1. Stop ongoing harmful automation or rollout.
2. Shift traffic away from the failed Region or target group if a tested path exists.
3. Roll back the smallest recent change correlated with failure.
4. Restore the last known-good DNS, listener rule, ingress, or deployment revision.
5. Reduce optional load and disable expensive features.
6. Use a maintenance endpoint only when the application cannot safely serve traffic.

DNS changes are not instantly reversible because recursive caches honor TTLs and may cache failures. Prefer traffic controls below DNS when they can restore service faster and more predictably.

### L — Look for recovery

Recovery criteria:

- external synthetic success from multiple networks and Regions
- customer request success rate returns to objective
- p95 and p99 latency normalize
- ALB healthy-host count stabilizes
- no Availability Zone or version remains degraded
- support volume and client retries decline

### IZE — Investigate, prevent recurrence, exercise

Examples of corrective actions:

- DNS-change review and automated validation
- pre-deployment synthetic probe against the new ALB hostname
- Route 53 Resolver query logging where appropriate
- ALB target-health alerts by Availability Zone
- admission policy validating service selectors and target ports
- load-balancer-controller SLOs and alerts
- externally hosted canary checks independent of the AWS account
- tested regional failover and rollback runbooks

## Decision tree

```text
Does DNS resolve externally?
  |-- No -> delegation, record, DNSSEC, resolver cache, health-check routing
  |
  `-- Yes
       |
       Does TLS connect?
       |-- No -> certificate, SNI, listener, edge/WAF, network path
       |
       `-- Yes
            |
            Does ALB return a response?
            |-- 4xx -> WAF, listener rule, auth, application routing
            |-- 5xx -> target health, app, dependency, timeout
            `-- timeout -> SG/NACL/routes, no healthy targets, saturation
```

## Key observability signals

### Route 53 and edge

- health-check status
- DNS answer correctness from external probes
- CloudFront 4xx/5xx rate and origin latency
- WAF allowed, blocked, and sampled requests

### ALB

- `HTTPCode_ELB_5XX_Count`
- `HTTPCode_Target_5XX_Count`
- `TargetResponseTime`
- `HealthyHostCount`
- `UnHealthyHostCount`
- `RejectedConnectionCount`
- `TargetConnectionErrorCount`

### EKS and application

- request rate, errors, duration, and saturation
- pod readiness and restart rate
- EndpointSlice readiness
- node and subnet IP pressure
- dependency latency and connection-pool utilization
- rollout revision and error rate by version

## Common failure signatures

| Symptom | Likely layer |
|---|---|
| `NXDOMAIN` | wrong zone, record deletion, delegation, negative cache |
| DNS resolves to old ALB | stale TTL, wrong alias, split-horizon DNS |
| TLS hostname mismatch | wrong certificate or edge origin |
| ALB `503` | no healthy registered targets |
| ALB `502` | target closed/reset connection or protocol mismatch |
| ALB `504` | target or dependency exceeded timeout |
| only one AZ fails | target distribution, subnet, route, NACL, zonal dependency |
| only IPv6 clients fail | broken `AAAA`, dual-stack path, security policy |
| pods ready but ALB targets unhealthy | health-check path/port, SG, readiness-gate mismatch |
| intermittent failures after deploy | mixed ReplicaSets, slow registration, bad subset |

## Adversarial follow-ups

### “Route 53 is healthy. Why continue checking DNS?”

A hosted zone can be healthy while delegation, resolver caching, DNSSEC, a specific record, or a client network path is wrong. I validate the answer externally from multiple resolvers.

### “All pods are Ready, so why are users failing?”

Kubernetes readiness proves only the configured probe. It does not prove that the ALB can reach the target, that the complete dependency chain works, or that every version and Availability Zone is healthy.

### “Would you immediately lower the TTL?”

Lowering TTL during the outage does not change answers already cached. TTL reduction is a preparedness action performed before planned migrations. During an incident I choose the fastest controllable layer.

### “Would you flush public DNS caches?”

There is no universal public cache flush. I correct the authoritative answer, account for TTL and negative caching, and use lower-layer traffic controls where possible.

## Weak answers to avoid

- “Restart the pods.”
- “Route 53 is probably down.”
- “The ALB says healthy, so the app is healthy.”
- changing DNS, security groups, ingress, and deployments simultaneously
- declaring recovery based only on internal dashboards
- performing root-cause analysis before restoring customer service

## Staff-level close

The differentiator is disciplined path isolation. I move from the customer-visible symptom inward, compare failing and healthy cohorts, make one reversible mitigation at a time, and validate recovery externally. The postmortem then improves both the architecture and the detection system so the same class of failure becomes faster to identify and safer to recover.