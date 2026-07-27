# Platform SLOs, Adoption, Economics, and Operating Model

## Why this exists

A platform can be technically elegant and still fail as a product. If developers cannot complete important journeys, do not trust the status, cannot get support, or cannot justify migration cost, adoption stalls. If the platform team measures only infrastructure uptime and ticket volume, it misses the outcomes it exists to improve.

Platform measurement must connect four views:

```text
Developer outcome
Operational reliability
Risk and governance
Economic value
```

## What the interviewer is testing

A strong Staff or Principal candidate can:

- define platform customers and critical journeys;
- create SLIs and SLOs for asynchronous platform capabilities;
- distinguish adoption from coercion;
- measure cognitive load and delivery outcomes;
- calculate platform value without fabricated precision;
- define support, ownership, funding, and roadmap mechanisms;
- use data to retire, improve, or split platform capabilities.

## Start with critical journeys

Platform SLOs should be attached to user outcomes, not only components.

Examples:

- create a production-ready service;
- create an ephemeral test environment;
- provision a managed database;
- deploy a change progressively;
- rotate a workload credential;
- discover the owner and runbook for a service;
- recover a service in another region;
- onboard an existing service to the supported path.

A portal can be healthy while these journeys are failing.

## Journey decomposition

For each journey, map:

```text
request accepted
  -> validation complete
  -> approval complete
  -> desired state recorded
  -> provisioning reconciled
  -> delivery configured
  -> runtime ready
  -> evidence visible
```

Each transition needs an owner, status, timeout, retry policy, and evidence source.

## Platform SLIs

### Availability

Measure whether users can perform the supported operation.

Examples:

- percentage of valid create requests accepted;
- percentage of catalog reads served successfully;
- percentage of deployment promotions processed;
- percentage of reconciliation cycles completing without platform-caused error.

Exclude invalid user input from platform availability, but report policy rejections separately so poor product design is not hidden.

### Latency

For asynchronous capabilities, measure end-to-end time and step latency.

Examples:

- request-to-ready duration;
- queue wait time;
- approval wait time;
- provisioning duration;
- reconciliation lag;
- status propagation delay;
- time to generate a rollback or recovery plan.

Use percentiles and separate workload classes. A database journey and a repository creation journey should not share one target.

### Correctness

Examples:

- percentage of resources created with correct ownership and policy metadata;
- percentage of portal status values matching authoritative systems;
- percentage of template outputs passing conformance tests;
- percentage of deletions honoring retention policy;
- drift rate;
- duplicate or orphan entity rate.

### Durability and recoverability

Examples:

- workflow state recovery success;
- successful restore of Terraform state or platform databases;
- successful reconstruction from Git and authoritative APIs;
- controller recovery after restart;
- completion rate of scheduled disaster-recovery exercises.

### Supportability

Examples:

- percentage of failures with an actionable error and owner;
- time to acknowledge platform incidents;
- time to provide a safe workaround;
- support requests per 100 active services;
- repeat incidents by capability and version.

## Example SLO set

For a production database capability:

```text
Request acceptance availability: 99.9% monthly
p95 accepted-to-ready: less than 45 minutes
Status freshness: 99% within 2 minutes
Policy correctness: 100% encryption and ownership tagging
Recovery: quarterly restore test succeeds within declared RTO
Manual intervention: less than 2% of valid requests
```

Targets must reflect user need, dependency behavior, and support capacity. Do not copy consumer-service SLOs onto every internal control plane.

## Error budgets

An error budget gives the platform team and users a shared decision mechanism.

Budget-consuming events can include:

- valid requests rejected by the platform;
- excessive time-to-ready;
- stale or incorrect status;
- platform-caused resource misconfiguration;
- failed upgrade or migration;
- control-plane incident blocking supported journeys.

When a capability burns its budget:

1. pause risky feature expansion;
2. reduce rollout velocity;
3. address dominant failure classes;
4. improve tests and rollback;
5. review dependency and tenancy blast radius;
6. communicate impact and recovery plan to users.

Do not use error budgets to excuse poor usability or chronic manual work.

## Adoption metrics

Adoption should show whether teams choose and successfully use the product.

Useful measures:

- percentage of eligible services using the supported path;
- new-service adoption rate;
- migration completion rate;
- repeat use by the same teams;
- successful journey completion;
- percentage of teams remaining on unsupported paths;
- time from first trial to production use;
- abandonment point within the journey;
- number and age of active exceptions.

Portal logins and page views are weak proxies.

## Developer experience measures

Combine telemetry with structured research.

Quantitative:

- active engineering time per journey;
- number of handoffs;
- waiting time;
- time spent finding owners, docs, and runbooks;
- failed attempts before success;
- support requests;
- local scripts required outside the path.

Qualitative:

- confidence in deployment and rollback;
- perceived cognitive load;
- clarity of error messages;
- trust in portal status;
- understanding of ownership boundaries;
- willingness to recommend the path to another team.

Survey a specific journey, not "Do you like the platform?"

## Delivery and reliability outcomes

Where data quality allows, correlate platform adoption with:

- lead time for changes;
- deployment frequency;
- change failure rate;
- time to restore;
- escaped security findings;
- percentage of services with SLOs and runbooks;
- incident detection and ownership time;
- cost variance and idle-resource rate.

Correlation is not automatically causation. Compare similar workloads and explain confounding factors.

## Economic model

The platform creates value through reduced duplicated work, shorter waiting time, fewer failures, faster recovery, better utilization, and lower governance cost.

A defensible model uses ranges and observable inputs.

### Capacity returned

```text
annual hours returned
  = eligible journeys per year
  x median active engineering hours removed per journey
```

Example:

```text
2,000 environment requests/year
x 3 active engineering hours removed
= 6,000 engineering hours returned
```

Do not immediately claim those hours become cash savings. State whether they become delivery capacity, avoided hiring, or reduced contractor spend.

### Incident value

```text
expected annual loss reduction
  = incident frequency reduction
  x expected impact per incident
```

Use ranges for customer impact, engineering time, contractual exposure, and recovery cost. Avoid invented revenue numbers.

### Platform cost

Include:

- platform engineering labor;
- infrastructure and software licenses;
- support and on-call;
- migrations;
- training and documentation;
- security review;
- upgrades and deprecation;
- opportunity cost of standardization.

A platform that saves application-team time by creating unsustainable platform-team toil is not successful.

## Unit economics

Useful ratios:

```text
platform cost per supported service
platform support hours per 100 services
control-plane cost per successful journey
migration cost per onboarded service
automation maintenance cost per capability
```

Track trends rather than using one number as a universal benchmark.

## Operating model

### Product ownership

A platform product manager or product-minded engineering leader owns customer discovery, prioritization, adoption, and outcome measurement. This does not eliminate engineering ownership.

### Engineering ownership

Capability teams own APIs, control planes, reliability, security, lifecycle, and support. Ownership should follow capability boundaries rather than tool names where possible.

### Embedded partnership

Use design partners from application teams for discovery, pilots, and roadmap validation. Avoid building the platform in isolation.

### Governance

Create a lightweight mechanism for:

- new capability proposals;
- exception review;
- API and template review;
- security and compliance requirements;
- deprecation decisions;
- reliability review;
- cost and capacity review.

Governance should reduce risk without recreating a ticket queue.

## Support tiers

Define support explicitly.

| Tier | Meaning |
|---|---|
| Supported | documented, monitored, on-call ownership, upgrade and migration path |
| Preview | limited adopters, changing contract, best-effort support |
| Experimental | no production guarantee, learning only |
| Deprecated | migration deadline and reduced change scope |
| Unsupported | application team owns operation and risk |

Do not let experimental capabilities become production dependencies by accident.

## Roadmap prioritization

Prioritize using evidence:

```text
value = journey pain x number of affected teams x risk reduction
        divided by delivery and lifecycle cost
```

Also consider strategic constraints such as regulatory deadlines, provider end-of-life, data-center exit, or acquisition integration.

A feature requested by many teams may still be a poor platform capability if it cannot be supported safely.

## Failure modes

- measuring platform success by resource count;
- forcing adoption before reliability is proven;
- hiding manual operations behind a portal;
- using one SLO for unrelated capabilities;
- counting invalid requests as platform outages without separate analysis;
- claiming all time saved as direct financial savings;
- ignoring migration and deprecation cost;
- funding only project delivery, not lifecycle operation;
- allowing preview features to become permanent production dependencies;
- rewarding teams for ticket closure rather than journey improvement.

## Review cadence

Monthly capability review:

- SLO and error-budget status;
- top failure and support classes;
- adoption and abandonment;
- manual-intervention rate;
- cost trend;
- roadmap experiments.

Quarterly product review:

- developer journey outcomes;
- platform reliability and disaster-recovery evidence;
- migration and exception portfolio;
- lifecycle and deprecation decisions;
- business and risk outcomes;
- capacity and staffing.

## 90-second interview answer

> I measure a platform around critical developer journeys, not around cluster uptime or portal traffic. For each journey I define acceptance availability, end-to-end time-to-ready, status freshness, correctness, recoverability, and manual-intervention rate. I attach error budgets to platform-caused failures and use budget burn to control rollout and reliability work. Adoption means eligible teams successfully and repeatedly choose the supported path; logins are not enough. I combine telemetry with journey-specific research on waiting time, handoffs, cognitive load, trust, and error clarity. I then connect adoption to delivery, reliability, security, and cost outcomes without claiming unsupported causality. Economically, I model engineering capacity returned, incident-risk reduction, and infrastructure efficiency against the full lifecycle cost of the platform, including support and migrations. Finally, I define support tiers, capability ownership, deprecation, and a product review cadence so the platform remains a maintained product rather than a one-time automation project.

## Adversarial follow-ups

### "What is the single best platform metric?"

There is no universal single metric. I choose one primary outcome for a specific journey, such as p95 idea-to-ready time, and pair it with guardrails for reliability, correctness, support load, and adoption.

### "How do you prove return on investment?"

Use observable before-and-after journey data, adoption, incident and support trends, and a range-based cost model. Separate delivery capacity returned from direct cash savings.

### "Should the platform be mandatory?"

Risk controls may be mandatory, but the product path should first be demonstrably safer and easier. Forced adoption can hide severe product defects.

### "Who owns an incident involving an application and the platform?"

Establish incident command based on customer impact, then assign technical workstreams. Ownership for corrective actions follows the failed contract: platform control plane, application behavior, or a shared interface gap.

## Dangerous answers

- "Our SLO is 99.99% because we are a platform."
- "Adoption is 90% because users logged in."
- "We saved 10,000 hours, so we reduced cost by 10,000 times the average salary."
- "The platform team owns all incidents on the platform."
- "Internal products do not need support tiers."
- "Once migrated, teams cannot leave the platform."

## Whiteboard summary

```text
Critical journey
  -> outcome SLI and SLO
  -> error budget
  -> adoption and experience
  -> delivery, reliability, risk, and cost outcomes
  -> roadmap and lifecycle decisions
```

## Primary references

Use official documentation for the platform's runtime, provisioning, delivery, portal, and observability systems. Measurement definitions should be versioned alongside the platform capability and reviewed when the journey or architecture changes.
