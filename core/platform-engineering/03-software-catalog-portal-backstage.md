# Software Catalogs, Developer Portals, and Backstage

## Why this exists

As organizations grow, engineers lose time discovering who owns a service, where it runs, how it is deployed, which APIs it exposes, what its SLO is, and where its runbook lives. A software catalog creates a consistent model of the software estate. A developer portal uses that model to provide navigation, documentation, actions, and evidence.

Backstage is a widely used framework for building this experience. It provides a Software Catalog, Software Templates, TechDocs, and a plugin architecture. It does not automatically solve ownership, metadata quality, workflow reliability, or platform product design.

## What the interviewer is testing

A strong answer should cover:

- catalog entities, ownership, relationships, lifecycle, and metadata governance;
- the difference between discovery metadata and authoritative runtime state;
- ingestion, freshness, reconciliation, and deletion behavior;
- portal plugins and backend integrations;
- template security and workflow ownership;
- how to avoid creating a stale internal wiki with buttons;
- adoption, search quality, and measurable developer outcomes.

## Catalog model

A useful catalog normally represents:

```text
Domain
  -> System
      -> Component / Service / Website / Library
          -> API
          -> Resource
          -> Owner
          -> Dependencies
          -> Documentation
          -> SLO and runbook links
```

The exact entity kinds matter less than consistent semantics.

Every production component should answer:

- Who owns it?
- What business or technical system does it belong to?
- What lifecycle state is it in?
- Where is its source repository?
- How is it deployed?
- Where does it run?
- Which APIs and dependencies does it have?
- What data classification applies?
- What SLO tier applies?
- Where are the runbook, dashboard, alerts, and cost view?

## Metadata ownership

Prefer metadata stored close to the code when the application team owns it. Examples include a catalog descriptor, service manifest, or repository configuration.

Use automated providers for metadata that is authoritative elsewhere, such as:

- identity groups from the corporate directory;
- cloud accounts and resources from cloud inventory;
- Kubernetes workloads from cluster APIs;
- API definitions from registries;
- build and deployment data from CI/CD systems;
- SLO status from observability systems.

Do not require humans to manually maintain facts that machines can discover reliably.

## Source-of-truth rule

A catalog should reference or ingest authoritative data; it should not pretend to own everything.

| Data | Better authority | Catalog role |
|---|---|---|
| Team membership | identity directory | display and relationship |
| Repository | source-control provider | link and metadata |
| Current deployment version | delivery/runtime system | display current status |
| Infrastructure actual state | cloud or Kubernetes API | inventory view |
| Service ownership declaration | versioned service metadata | indexed relationship |
| SLO status | observability platform | summary and deep link |
| Cost | billing/cost platform | attributed view |

## Ingestion architecture

```text
Repository descriptors ----+
Identity provider ----------+
Cloud and cluster inventory +--> ingestion and validation
API registries -------------+            |
Delivery systems -----------+            v
                                  normalized catalog graph
                                             |
                                             v
                                search / portal / API / plugins
```

Ingestion needs:

- stable entity identity;
- schema validation;
- ownership validation;
- conflict resolution;
- freshness timestamps;
- deletion and orphan policy;
- audit history;
- rate limiting and backoff;
- clear error reporting to the entity owner.

## Backstage components

### Software Catalog

Backstage's Software Catalog tracks ownership and metadata for software entities. It commonly ingests YAML descriptors stored with source code and can also use providers and processors.

### Software Templates

The Scaffolder can collect parameters, render skeleton content, call actions, publish repositories, and register entities. A template is an executable supply-chain asset and must be reviewed accordingly.

### TechDocs

TechDocs supports documentation-as-code. For production, build documentation in CI and publish generated static content to durable object storage rather than depending on a single portal instance to build and store everything locally.

### Plugins

Plugins integrate delivery, observability, cost, security, incident, and cloud systems. Plugins improve discoverability, but every integration adds upgrade, permission, availability, and support obligations.

## Template design

A good software template creates a complete supported starting point, not merely a repository.

It should establish:

- owner and system metadata;
- repository protections;
- build and test workflow;
- artifact naming and provenance;
- deployment configuration;
- workload identity;
- telemetry and SLO defaults;
- documentation skeleton;
- runbook and support metadata;
- lifecycle and update mechanism.

Avoid copying static boilerplate that immediately forks from the maintained path. Prefer reusable workflows, centrally versioned actions, policy, and automated update mechanisms.

## Template security

Treat custom template actions as privileged code.

Controls include:

- allow-listed actions;
- least-privilege service identities;
- short-lived credentials;
- protected template repositories;
- mandatory review and automated tests;
- input validation;
- output and log redaction;
- restricted repository destinations;
- egress controls where feasible;
- audit records for every action;
- canary rollout of new template versions.

Never allow arbitrary shell commands or unreviewed third-party actions in a high-privilege scaffolding environment.

## Portal authorization

Authentication identifies the user. Authorization determines which entities, actions, and data the user may access.

Important questions:

- Can a developer create resources for another team?
- Can users see sensitive service metadata?
- Who may execute production-affecting actions?
- Does portal authorization match the target system's authorization?
- Are permissions enforced in the backend or only hidden in the UI?
- How are group and ownership changes propagated?

The target control plane must enforce its own authorization. UI hiding is not a security boundary.

## Freshness and trust

A portal loses credibility quickly when information is stale.

Expose:

- last successful synchronization time;
- source system;
- validation errors;
- stale or unknown status;
- entity owner;
- correction workflow.

A useful catalog prefers "unknown, last checked 30 minutes ago" over a confident but stale green status.

## Failure modes

- duplicate entities with inconsistent names;
- orphaned services after team changes;
- stale runtime data presented as current;
- templates that create repositories but not operational ownership;
- plugins with broad credentials;
- portal availability becoming a deployment dependency;
- manual metadata becoming a compliance checkbox;
- search returning hundreds of nearly identical entities;
- no process for deprecation and deletion;
- custom plugins that cannot be upgraded.

## Observability and acceptance criteria

Catalog and portal SLIs may include:

- search and entity-read availability;
- p95 search latency;
- ingestion success rate;
- metadata freshness by provider;
- percentage of production services with valid owner;
- percentage with documentation, SLO, runbook, and repository links;
- orphan and duplicate rate;
- template workflow success rate;
- time to create a ready service;
- percentage of failures with actionable owner-facing errors;
- portal-assisted journey completion rate.

Do not use monthly active users as the only success metric. A portal can be frequently visited because the underlying systems are confusing.

## Rollout path

1. Define a small entity model and naming rules.
2. Ingest ownership and repositories for one domain.
3. Add validation and freshness reporting.
4. Link existing delivery, observability, and runbook systems.
5. Introduce one production-grade template.
6. Measure a complete journey and fix friction.
7. Add plugins only where they shorten a real journey.
8. Establish lifecycle, deprecation, and metadata quality ownership.

## 90-second interview answer

> I use a software catalog to answer ownership, lifecycle, dependency, documentation, SLO, and runtime-discovery questions consistently. The catalog is a graph and discovery layer, not the authority for every fact. Team membership stays authoritative in identity, actual deployment state in delivery or runtime systems, and cost in the billing platform. I ingest versioned service metadata from repositories and machine-owned facts from providers, with schema validation, freshness timestamps, conflict handling, and an orphan policy. In Backstage, I treat the Catalog, Scaffolder, TechDocs, and plugins as product building blocks. Templates are privileged supply-chain code, so actions are allow-listed, reviewed, tested, and run with short-lived least-privilege identities. Portal permissions are enforced in backend and target systems, not just the UI. I measure metadata coverage and freshness, orphan rate, template success, and time-to-ready for real developer journeys. The goal is trusted discovery and safer self-service, not installing a portal.

## Adversarial follow-ups

### "Should all metadata live in catalog-info.yaml?"

No. Team-owned declarations can live with code, while machine-owned facts should come from authoritative providers. Duplicating runtime or identity facts in YAML creates drift.

### "Can the portal be used during an incident?"

Yes as a navigation and evidence surface, but incident-critical runbooks and control paths should remain accessible if the portal is unavailable.

### "How do you keep templates current?"

Minimize generated static logic, reference centrally maintained workflows and libraries, publish versioned templates, test upgrades, and provide automated migrations or update pull requests.

## Dangerous answers

- "Backstage is the platform."
- "The catalog database is the source of truth for production."
- "Anyone who can see a button can execute the action."
- "Templates are safe because only employees use them."
- "Every tool should have a portal plugin."
- "A service is compliant because it has a catalog entry."

## Whiteboard summary

```text
Authoritative systems
  -> validated ingestion
  -> normalized ownership and relationship graph
  -> search, docs, actions, and evidence

Catalog discovers
Workflow acts
Target control plane authorizes
Runtime remains independent
```

## Primary references

- Backstage official technical and architecture overviews.
- Backstage Software Catalog documentation.
- Backstage Software Templates and Scaffolder documentation.
- Backstage TechDocs architecture and production deployment guidance.
- Official permission and plugin documentation for the deployed Backstage release.
