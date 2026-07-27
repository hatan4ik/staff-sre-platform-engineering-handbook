# User-Centered SLOs, Error Budgets, Burn Rates, and Ownership

## Interview scenario

An organization has dashboards, alerts, incidents, and reliability projects, but teams disagree about what “reliable enough” means. Product leaders push releases because infrastructure graphs are green. Platform teams own most pages but cannot influence roadmaps. Services advertise high availability without defining the user journey, measurement point, denominator, or error-budget policy.

The Staff/Principal task is to create a measurable reliability contract that changes product, engineering, capacity, and release decisions without turning SLOs into punishment.

---

## 1. Ninety-second Staff/Principal answer

> I begin with three to five critical user journeys, not hundreds of component dashboards. For each journey I define valid events, good events, correctness and latency requirements, measurement point, target, compliance window, protected cohorts, owner, and error-budget policy.
>
> The SLI is the measured ratio of good valid events to all valid events. The SLO is the target over a stated window. The error budget is the allowed bad fraction. I keep `GOOD`, `BAD`, `UNKNOWN`, and `EXCLUDED` explicit so missing telemetry cannot silently improve the objective. Component SLIs help diagnosis and dependency ownership, but they do not erase a failed user journey.
>
> I alert on fast and slow error-budget burn rather than waiting for the monthly objective to fail. The response depends on policy: a fast burn pages immediately; sustained budget exhaustion can freeze risky releases, prioritize corrective work, reduce rollout exposure, or require leadership risk acceptance.
>
> SRE or platform provides measurement, templates, and governance. The service engineering owner and product owner remain accountable for the reliability outcome and trade-offs. The SLO becomes real only when its burn changes a release, capacity, architecture, or investment decision.

### Fifteen-second version

> Define the user journey, count good and valid events correctly, alert on burn, and connect the remaining budget to explicit engineering and product decisions.

---

## 2. Reliability contract

### Service Level Indicator

An SLI is a quantitative measure of service behavior.

For an event-based SLI:

```text
SLI = good valid events / total valid events
```

For a time-based SLI:

```text
SLI = good eligible time / total eligible time
```

Event-based measurement usually aligns better with high-volume request or transaction systems. Time-based measurement may fit continuously evaluated systems or contractual uptime models.

### Service Level Objective

An SLO is the target range for an SLI over a defined compliance window.

Example:

```text
99.95% of valid checkout attempts complete correctly
within 2 seconds over a rolling 28-day window.
```

A complete SLO defines:

- User journey or capability.
- Good-event criteria.
- Valid-event denominator.
- Measurement point and source.
- Target.
- Compliance window.
- Exclusions and unknown handling.
- Protected segments or cohorts.
- Owner.
- Review cadence.
- Error-budget policy.

### Service Level Agreement

An SLA is an external or contractual commitment with consequences such as credits or penalties. Internal SLOs are commonly stricter than SLAs so the organization has operating margin.

### Error budget

```text
allowed bad fraction = 1 - SLO target
```

For a request-based objective:

```text
allowed bad events = total valid events × allowed bad fraction
```

The error budget represents risk the organization has decided to tolerate. It is not permission to create avoidable outages.

---

## 3. Begin with user journeys

A user does not experience individual internal services independently. They experience a journey.

Examples:

- Sign in.
- Search or open content.
- Complete checkout.
- Start and continue playback.
- Submit a job and receive a result.
- Send a device command and receive confirmed outcome.
- Publish an event and have it processed before a deadline.

Journey map:

```text
client
  -> edge
  -> identity
  -> gateway
  -> application
  -> data and dependencies
  -> user-visible confirmation
```

Measure the journey as close to the user as practical.

Component SLIs remain useful for:

- Diagnosis.
- Dependency contracts.
- Capacity planning.
- Team ownership.
- Internal control-plane reliability.

They are not substitutes for user success.

---

## 4. Good-event semantics

A technically successful response may still be bad.

Examples:

- HTTP `200` with malformed or empty content.
- A command is accepted but never executed.
- A response arrives after the user's deadline.
- The wrong data or entitlement is returned.
- A state transition is duplicated.
- A stream starts only after excessive retries.
- A queue acknowledges a message but loses the side effect.

Good events may require:

- Availability.
- Timeliness.
- Correctness.
- Freshness.
- Durability.
- Security or authorization correctness.
- User-visible completion.

Do not reduce semantic success to transport status alone.

---

## 5. Common SLI types

### Availability

```text
successful valid operations / total valid operations
```

Define whether these are bad:

- `5xx`.
- Gateway timeout.
- Connection reset.
- Under-capacity `429`.
- Semantically unusable response.
- Success after user deadline.

Do not automatically classify every `4xx`. A correct authorization denial may be good system behavior; a mistaken denial may be bad.

### Latency threshold

```text
valid operations completed within threshold / total valid operations
```

Threshold SLIs count bad events directly.

Possible dual thresholds:

```text
99% within 300 ms
99.9% within 1 second
```

Percentile graphs remain useful, but a percentile alone does not define the number of events beyond the business deadline across all segments.

### Correctness

Examples:

- Response satisfies schema and business rules.
- State transition is exactly once from the user's perspective.
- Entitlement decision matches source of truth.
- Checksum or signature is valid.
- Requested object maps to the intended version.

Correctness may need sampled validation, audit comparison, downstream confirmation, or synthetics.

### Freshness

```text
responses with data age <= threshold / valid responses
```

Useful for:

- Configuration propagation.
- Inventory.
- Catalog and metadata.
- Replicated reads.
- Search indexes.
- Analytics and recommendations.

### Durability

Examples:

- Accepted writes recover after failure.
- Events remain replayable.
- Backup and restore meet data-loss objective.

### Quality

Domain-specific examples:

- Rebuffer-free stream minutes.
- Notification delivered before deadline.
- Device command confirmation.
- Model inference meets quality floor.

Keep independently actionable quality dimensions rather than one opaque score.

---

## 6. Denominator engineering

The denominator determines whether the SLO represents a real opportunity to serve the user.

Potential valid exclusions:

- Deliberate test traffic with explicit classification.
- Malformed requests that could never succeed.
- Confirmed cancellation before service processing.
- Unsupported protocol versions outside the product contract.
- Approved maintenance only when the contract permits it.

Dangerous exclusions:

- All dependency failures.
- All overload responses.
- Errors during deployments.
- Regional incidents.
- Difficult device or customer populations.
- “Known issues” with no expiration.
- Telemetry gaps treated as success.

The user journey failed even when an internal dependency caused it. Dependency SLIs support attribution but do not remove user impact from the journey SLO.

---

## 7. Explicit event classification

Use:

```text
GOOD | BAD | UNKNOWN | EXCLUDED
```

### Good

Meets the documented user expectation.

### Bad

Valid opportunity that did not meet availability, latency, correctness, freshness, or quality requirements.

### Unknown

Telemetry is missing, contradictory, too late, or insufficient to classify.

### Excluded

Matches a documented, reviewed, and bounded exclusion.

Track unknown rate separately. If unknown silently becomes good, an observability outage can improve the SLO.

Exclusions should have:

- Reason.
- Owner.
- Query or rule.
- Review date.
- Maximum acceptable volume.

---

## 8. Prevent denominator dilution

High-volume easy traffic can hide low-volume critical traffic.

Example:

```text
billions of cached reads at 99.999%
small but critical write path at 98%
```

A combined ratio can look excellent.

Use:

- Separate journey SLOs.
- Protected route or operation slices.
- Protected tenant tiers where contractually or operationally required.
- Geography or device coverage where product behavior differs.
- Minimum sample rules.

Avoid creating so many slices that no one can operate the system. Protect distinct user intents and high-risk cohorts.

---

## 9. Measurement points

### Server-side

Strengths:

- High coverage.
- Consistent instrumentation.
- Correlation with traces and deployments.

Blind spots:

- Failures before request arrival.
- Response not received by client.
- Client deadline shorter than server completion.
- Semantic failure after transport.

### Edge or gateway

Strengths:

- Closer to user.
- Captures routing and upstream failure.
- Broad geography.

Blind spots:

- Deep semantic correctness.
- Client behavior after response.

### Client or device

Strengths:

- Strong view of actual experience.
- Captures local network, rendering, playback, and device behavior.

Blind spots:

- Telemetry may be blocked or delayed.
- SDK-version and sampling bias.
- Users may abandon before telemetry flush.

### Synthetic transaction

Strengths:

- Controlled and repeatable.
- Useful at low traffic.
- Can validate semantics.

Blind spots:

- Small sample.
- Limited real account, network, device, and data diversity.

### Recommended pattern

```text
primary user-journey source
  + corroborating edge/server/client signals
  + component diagnostic SLIs
  + independent synthetics
```

Document ingestion delay, deduplication, late-event handling, sampling, replay, and telemetry-loss policy.

---

## 10. Error-budget mathematics

Let:

```text
objective = S
allowed bad fraction = 1 - S
valid events = V
bad events = B
```

Then:

```text
allowed bad events = V × (1 - S)
budget remaining = V × (1 - S) - B
budget remaining percent = budget remaining / allowed bad events × 100
```

Example:

```text
objective:          99.95%
valid events:       2,000,000,000
allowed bad rate:   0.0005
allowed bad events: 1,000,000
observed bad events: 250,000
budget remaining:   750,000 = 75%
```

For a time-based `99.9%` target over 30 days:

```text
30 × 24 × 60 × 0.001 = 43.2 minutes
```

This conversion is useful for intuition. Do not convert an event-based objective to downtime minutes and imply false precision.

---

## 11. Burn rate

Burn rate compares observed bad rate with the allowed bad rate.

```text
burn rate = observed bad-event rate / allowed bad-event rate
```

For `99.9%`, the allowed bad rate is `0.1%`.

If observed bad rate is `1%`:

```text
burn rate = 1% / 0.1% = 10x
```

At a sustained `10x` burn, a full 30-day budget would be consumed in roughly three days, assuming no budget was already consumed and the rate remains constant.

Approximation:

```text
time to exhaustion ≈ compliance window / burn rate
```

Burn rate normalizes severity across objectives.

---

## 12. Multi-window burn alerting

A single short window is noisy. A single long window is slow.

Use paired windows:

```text
fast burn:
  high burn over short window
  confirmed by a longer short window
  -> page immediately

slow burn:
  moderate burn over longer window
  confirmed by a second long window
  -> ticket or page based on urgency
```

Example conceptual policy:

- Very high burn over minutes plus confirmation over an hour.
- High burn over an hour plus confirmation over several hours.
- Moderate burn over several hours plus confirmation over a day.

Exact thresholds depend on:

- Objective.
- Compliance window.
- Traffic and event volume.
- Detection and mitigation time.
- Paging policy.
- Product risk.

Alert on user-impacting burn, then attach component evidence for diagnosis.

Low-traffic services need synthetics, longer windows, Bayesian or minimum-count policy, or separate direct failure alerts.

---

## 13. Dependencies

Journey SLOs include dependency-caused failures because users experience them.

Use dependency SLIs to answer:

- Which dependency contributed?
- Was the failure within the dependency contract?
- Did retries, fallback, cache, or degradation work?
- Did our service amplify the dependency issue?

A service cannot claim reliability by excluding all dependency failures.

Reliability allocation may use budgets:

```text
journey budget
  -> edge allowance
  -> application allowance
  -> data and dependency allowance
  -> client allowance
```

Do not simply multiply service availability targets without accounting for parallel paths, fallback, correlation, and shared failure domains.

---

## 14. Partial degradation

Not every event is binary.

Possible policy:

- Full success: good.
- Safe degraded result meeting minimum product promise: good or separately budgeted.
- Degraded result below promise: bad.
- Unknown semantic outcome: unknown.

Define degradation before incidents.

Examples:

- Cached but sufficiently fresh response.
- Reduced recommendation quality.
- Lower video bitrate above minimum floor.
- Delayed noncritical notification.
- Read-only mode.

A “fallback succeeded” metric is not enough unless the fallback meets the product contract.

---

## 15. Multi-region and cell-based services

Measure:

- Global journey SLO.
- Regional and cell slices.
- Failover eligibility.
- Cross-region traffic shift.
- Data consistency and freshness.

A global aggregate can hide one broken region.

Do not exclude a region merely because traffic was shifted. Count user impact during detection, shift, and recovery.

Cell-level objectives support:

- Blast-radius detection.
- Capacity planning.
- Progressive delivery.
- Failover readiness.
- Ownership.

Global objective remains the user contract unless the product explicitly defines regional contracts.

---

## 16. SLO ownership model

### Product owner

- Defines journey importance and user promise.
- Approves trade-offs and degraded behavior.
- Participates in error-budget policy.

### Service engineering owner

- Owns implementation, operation, and corrective work.
- Maintains instrumentation and runbooks.
- Responds to burn.

### SRE or platform

- Provides framework, tooling, templates, and governance.
- Reviews indicator quality.
- Helps design alerts and policy.
- Challenges manipulation and unowned risk.

### Data or analytics owner

- Validates event semantics, pipeline quality, late events, and denominator integrity.

### Leadership

- Resolves priority conflicts.
- Accepts explicit risk.
- Funds systemic improvements.

SRE should not become the permanent owner of every service's reliability outcome.

---

## 17. Error-budget policy

Define actions before the budget burns.

Example policy:

### Healthy

- Normal release velocity.
- Continue planned reliability work.

### Elevated burn

- Incident review.
- Reduce rollout exposure.
- Confirm capacity and dependency risks.
- Prioritize near-term corrective work.

### Budget nearly exhausted

- Freeze high-risk changes.
- Require reliability review for exceptions.
- Focus engineering on containment and recovery gaps.
- Escalate unresolved cross-team dependencies.

### Budget exhausted

- Stop nonessential risky releases.
- Execute agreed corrective plan.
- Leadership may accept risk explicitly for a business-critical release.
- Restore normal policy only after recovery criteria are met.

Avoid absolute rules that ignore security patches, urgent customer fixes, and risk trade-offs. Exceptions should be explicit, owned, time-bounded, and reviewed.

---

## 18. SLOs and releases

Connect deployment telemetry to the journey SLO:

- Version and configuration in traces and logs.
- Error-budget burn by rollout cohort.
- Canary analysis on critical journeys.
- Automatic pause or rollback for fast burn.
- Capacity and dependency guardrails.

A rollout should not increase exposure based only on pod readiness and infrastructure health.

Example gate:

```text
advance from 5% to 25% only when:
  journey availability burn < threshold
  latency threshold SLI within objective
  no protected cohort regression
  dependency saturation within safe limit
  telemetry unknown rate below limit
```

---

## 19. SLOs and capacity

Capacity decisions should preserve the objective under expected failure.

Use:

- Safe throughput per pod.
- Demand forecast and burst shape.
- Capacity-realization time.
- Zone-loss headroom.
- Dependency limits.
- Error-budget risk.

If scaling takes five minutes but fast burn exhausts the operational tolerance in two minutes, warm capacity or admission control is required.

Capacity is not reliable merely because average utilization is low.

---

## 20. SLOs and incident response

During incidents:

- Page on fast burn and critical direct symptoms.
- Identify affected journey and cohort.
- Track budget consumption.
- Select mitigation based on user impact and recovery time.
- Confirm burn stops.
- Include budget impact in the postmortem.

SLOs should reduce debate during incidents:

```text
what is broken
how severe it is
which users are affected
how rapidly risk is accumulating
whether recovery is real
```

They do not replace incident command or diagnostic evidence.

---

## 21. Governance at scale

Provide reusable SLO-as-code templates containing:

- Name and description.
- Journey.
- Query or recording rule.
- Good and valid definitions.
- Objective and window.
- Owner and escalation.
- Protected cohorts.
- Unknown and exclusion policy.
- Burn alerts.
- Runbook.
- Error-budget policy.
- Review date.

Governance checks:

- Every tier-1 journey has an owner.
- Query compiles and produces data.
- Unknown rate is bounded.
- Alert routes to an accountable team.
- Objective is not looser than external promise.
- Exclusions are reviewed.
- SLO changes are versioned and approved.
- Burn affects decisions.

Do not require every internal service to create an SLO immediately. Start with journeys and critical dependencies.

---

## 22. Adoption roadmap

### Phase 1 — Discover

- Identify critical journeys.
- Inventory existing metrics and commitments.
- Find telemetry gaps.
- Assign product and engineering owners.

### Phase 2 — Pilot

- Define one or two journey SLOs.
- Backtest against incidents.
- Validate denominator and measurement bias.
- Create burn alerts in nonpaging mode.

### Phase 3 — Operationalize

- Publish error-budget policy.
- Page on validated fast burn.
- Connect deployment annotations and canary gates.
- Review budget in planning.

### Phase 4 — Scale

- SLO-as-code templates.
- Central catalog.
- Ownership and review automation.
- Dependency and cell slices.
- Executive reliability reporting based on journeys.

### Phase 5 — Improve

- Compare SLO behavior with customer reports.
- Remove noisy or nonactionable objectives.
- Improve semantics and telemetry.
- Exercise policy through incidents and game days.

---

## 23. Anti-patterns

### Arbitrary nines

Selecting `99.99%` because it sounds mature creates cost without product justification.

### Infrastructure-only SLO

CPU, node readiness, and pod availability are diagnostic signals, not user journeys.

### Percentile-only objective

A p99 graph alone does not directly count bad events and can hide protected cohorts.

### Dependency exclusion

Excluding all dependency-caused failures makes the objective meaningless to users.

### Unknown as good

Telemetry failure improves the score.

### SLO owned only by SRE

Product and service teams continue making decisions without reliability accountability.

### No budget policy

The dashboard changes color but no behavior changes.

### Punitive budget

Teams hide incidents or manipulate denominators because SLOs are used for blame.

### Hundreds of objectives before adoption

The organization spends time maintaining definitions that do not influence decisions.

---

## 24. Adversarial interview questions

### How do you choose the target?

Use user expectation, contractual promise, competitive requirement, safety or business risk, historical performance, architecture, and cost. Backtest the proposed target against incidents and product impact.

### Why not make every objective 100%?

Perfect reliability is usually impossible or disproportionately expensive. Error budgets make the trade-off explicit while preserving a high standard.

### What if the dependency has a worse SLO?

Redesign the journey with fallback, caching, redundancy, degraded behavior, or a lower honest objective. Do not advertise a target the architecture cannot support.

### What if product refuses a release freeze?

Present current burn, expected risk, mitigation options, and the documented policy. Leadership can accept risk explicitly, but the decision and owner should be recorded.

### What if traffic is too low for burn alerts?

Use synthetics, direct critical-failure alerts, longer windows, minimum event counts, and qualitative incident criteria.

### Can a successful fallback count as good?

Only when it meets the documented minimum user promise for correctness, latency, freshness, and security.

### How do you handle telemetry loss?

Classify it as unknown, alert on unknown rate, use corroborating sources, and prevent unknown events from silently entering the good numerator.

### Should internal control planes have SLOs?

Yes when their reliability affects delivery, security, recovery, or many services. Use component or platform-customer journeys such as deployment convergence or credential issuance.

---

## 25. Staff/Principal checklist

A strong answer includes:

- Precise SLI, SLO, SLA, and budget definitions.
- User journeys.
- Good-event semantics.
- Denominator and unknown handling.
- Multiple measurement points and bias.
- Error-budget and burn mathematics.
- Fast and slow burn alerting.
- Dependencies and protected cohorts.
- Multi-region and degraded behavior.
- Product, engineering, SRE, and leadership ownership.
- Predefined budget policy.
- Release and capacity integration.
- SLO-as-code governance.
- Adoption path.

---

## Related canonical material

- [`../../incident-response/README.md`](../../incident-response/README.md)
- [`../../observability/evidence-beyond-dashboards.md`](../../observability/evidence-beyond-dashboards.md)
- [`../../kubernetes/autoscaling/control-loops-capacity-realization.md`](../../kubernetes/autoscaling/control-loops-capacity-realization.md)
- [`../../distributed-systems/README.md`](../../distributed-systems/README.md)
