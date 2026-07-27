# Chapter 7 — Caching, Invalidation, CDNs, and Consistency at the Edge

Caching is the deliberate creation of additional copies of data so requests can be served faster, more cheaply, or closer to users.

Every cache creates another state-bearing component. That state can be stale, missing, corrupted, overloaded, inconsistent with its source, or unavailable during recovery.

The central Staff-level question is not:

> Should we add Redis or a CDN?

It is:

> What correctness guarantee does the user observe while multiple copies exist, and how does the system recover when invalidation, refresh, or origin access fails?

---

## 7.1 Why Cache

Caches are introduced to reduce:

- origin latency
- database load
- cross-region traffic
- compute cost
- repeated serialization or rendering
- external API calls
- tail latency

They may also absorb bursts and protect expensive dependencies.

### Cache benefits

- lower latency
- higher throughput
- better origin protection
- geographical proximity
- reduced cost

### Cache costs

- stale data
- invalidation complexity
- memory pressure
- stampedes
- partial outages
- consistency ambiguity
- operational state that is difficult to inspect

A cache is not free performance. It trades freshness and complexity for latency and capacity.

---

## 7.2 Cache Correctness Begins with the Invariant

Different data has different freshness tolerance.

### Usually tolerant of staleness

- product images
- public profiles
- recommendation results
- documentation
- analytics summaries
- static application assets

### Often sensitive to staleness

- authorization policy
- account balance
- inventory availability
- session revocation
- feature kill switches
- routing metadata
- encryption keys

The cache policy must follow the business invariant.

### Review questions

- How stale may the value be?
- Can stale data cause a security or financial violation?
- Must a user observe their own write immediately?
- Can the cache serve during origin failure?
- Can the value be recomputed?
- Is absence distinguishable from a negative result?

---

## 7.3 Cache Placement

Caches can exist at multiple layers.

```text
browser
  -> CDN edge
      -> regional reverse proxy
          -> service-local cache
              -> distributed cache
                  -> database buffer cache
                      -> storage cache
```

Each layer has different ownership and invalidation behavior.

### Client cache

Examples:

- browser HTTP cache
- mobile application cache
- SDK cache

Benefits:

- lowest latency
- no network request

Risks:

- difficult invalidation
- old application versions
- user-controlled state

### Edge cache

A CDN stores content near users.

Benefits:

- global latency reduction
- origin shielding
- DDoS absorption

Risks:

- regional propagation delay
- cache-key mistakes
- private-data leakage

### Service-local cache

In-process memory cache.

Benefits:

- fastest lookup
- no network dependency

Risks:

- inconsistent copies across instances
- cold cache on restart
- memory competition with application heap

### Distributed cache

Shared cache cluster.

Benefits:

- common view across instances
- larger capacity

Risks:

- network hop
- hotspot concentration
- cache cluster becomes a critical dependency

---

## 7.4 Cache-Aside

The application reads the cache first, then the source on miss.

```text
read cache
  |
  +-- hit --> return
  |
  +-- miss -> read database -> populate cache -> return
```

### Advantages

- simple
- application controls caching
- only requested values are cached

### Failure modes

- stale entry after source update
- race between concurrent fills
- cache stampede
- cache and database errors handled differently

### Write path

A common pattern is:

```text
update database
invalidate cache
```

If invalidation fails, stale data remains.

Reversing the order creates another race:

```text
invalidate cache
update database
```

A concurrent reader may repopulate the old value before the database commit.

This is why cache invalidation requires a protocol, not only a delete call.

---

## 7.5 Read-Through Cache

The cache itself loads missing values from the origin through a configured loader.

Benefits:

- application code is simpler
- centralized loading behavior

Risks:

- loader becomes hidden dependency logic
- timeout and retry behavior may be opaque
- difficult per-request consistency control

Read-through does not change the underlying freshness problem. It changes who owns the miss path.

---

## 7.6 Write-Through Cache

A write goes through the cache, which synchronously updates the source.

```text
client -> cache -> source of truth
```

Benefits:

- cache and origin updated in one path
- hot data remains present

Risks:

- cache becomes part of write availability
- partial failure between cache and source
- increased write latency

The system must define which component acknowledges success and which is authoritative.

---

## 7.7 Write-Behind Cache

The cache acknowledges the write and persists to the origin asynchronously.

Benefits:

- low write latency
- batching
- origin load smoothing

Risks:

- data loss if cache fails
- ordering issues
- complex recovery
- cache becomes temporary source of truth

Write-behind is safe only with durable buffering, replication, ordering, and recovery guarantees that match the business invariant.

For financial or security-critical data, casual write-behind is usually inappropriate.

---

## 7.8 TTL-Based Expiration

A time-to-live removes entries after a duration.

TTL provides bounded staleness only under specific assumptions.

If the cache stores a value for 60 seconds, a user may observe it almost 60 seconds after the source changes.

### TTL trade-off

Short TTL:

- fresher data
- more origin traffic
- more misses

Long TTL:

- lower origin load
- greater staleness
- slower correction after bad data

### TTL is not invalidation

TTL eventually removes stale data. It does not guarantee immediate visibility of updates.

### Jittered TTL

If millions of entries expire at the same time, the origin may be flooded.

Use randomized expiry:

```text
actual_ttl = base_ttl + random(-jitter, +jitter)
```

This spreads refresh load.

---

## 7.9 Explicit Invalidation

An update triggers cache deletion or replacement.

Mechanisms include:

- direct cache delete
- invalidation event
- change data capture
- versioned key
- CDN purge

### Invalidation event

```text
ProductUpdated(product_id=42, version=18)
```

Consumers invalidate or refresh the relevant key.

Failure modes:

- event lost
- consumer lag
- out-of-order invalidation
- one cache instance misses the event

Use durable delivery, version checks, and reconciliation where freshness matters.

---

## 7.10 Versioned Cache Keys

Instead of mutating one key, include a version.

```text
product:42:v18
```

The routing metadata or object record points to the current version.

Benefits:

- old and new values do not overwrite each other
- safe rollout
- immutable cached objects
- easy rollback

Costs:

- old entries remain until expiry
- version lookup may require another read
- garbage collection is needed

Versioned keys are especially effective for static assets and immutable representations.

---

## 7.11 Cache Key Design

A cache key must include every input that changes the response.

Potential dimensions:

- resource ID
- tenant ID
- user ID
- locale
- authorization scope
- query parameters
- API version
- content encoding
- feature flag
- device class

### Cache-key omission incident

Suppose a response varies by authenticated user but the cache key includes only the URL.

One user's private response may be served to another user.

### Staff-level rule

Cache-key correctness is a security boundary.

Review the key as carefully as an authorization policy.

---

## 7.12 Negative Caching

A cache can store that an item does not exist.

Benefits:

- protects the origin from repeated misses
- reduces abuse and random-key scans

Risks:

- newly created object remains invisible
- temporary origin error is mistaken for absence

A negative cache entry should distinguish:

- authoritative not found
- temporary failure
- permission denied

Do not cache transient 5xx responses as permanent absence.

---

## 7.13 Cache Penetration

Cache penetration occurs when requests target keys that are not cached and often do not exist.

The requests repeatedly reach the origin.

Mitigations:

- negative caching
- request validation
- rate limits
- probabilistic membership filters
- authentication

A Bloom filter can cheaply reject definitely absent keys, with a controlled false-positive rate.

It must be refreshed as the dataset changes.

---

## 7.14 Cache Stampede

A stampede occurs when many requests miss or observe expiration simultaneously and all query the origin.

```text
popular key expires
  -> 10,000 requests miss
  -> 10,000 database queries
  -> origin overload
```

### Mitigations

- request coalescing
- single-flight lock
- stale-while-revalidate
- probabilistic early refresh
- TTL jitter
- prewarming
- bounded origin concurrency

### Single-flight

One request refreshes the key. Others wait for or reuse the result.

Risks:

- refresh lock can become hot
- waiter timeout policy needed
- one slow loader delays all callers

---

## 7.15 Stale-While-Revalidate

The cache serves a stale value for a bounded period while one worker refreshes in the background.

```text
fresh window -> serve fresh
stale window -> serve stale and refresh
expired       -> block or fail according to policy
```

Benefits:

- stable latency
- origin protection
- resilience to short origin failures

Risks:

- explicit stale response window
- stale values may violate invariants

This pattern is excellent for content and recommendations, but usually not for authorization or exact inventory.

---

## 7.16 Stale-If-Error

During origin failure, a cache may serve stale data beyond normal freshness limits.

The business decision is:

> Is stale data safer than no data?

Examples:

- stale documentation: often acceptable
- stale product image: acceptable
- stale revocation list: dangerous
- stale price: depends on checkout validation

Fallback behavior should be data-class-specific.

---

## 7.17 Cache Consistency Models

Caches may provide different user-visible guarantees.

### Best-effort eventual freshness

Entries expire or are invalidated asynchronously.

### Read-your-writes

After a user updates data, route their reads to the source or update their session cache token.

Possible mechanisms:

- bypass cache after write
- write-through for that session
- version token in request
- sticky routing to a fresh replica

### Monotonic reads

A client should not observe version 18 and later version 16.

Store or propagate the minimum acceptable version.

### Strong cache coherence

All cache accesses coordinate with source state.

This can reduce the performance benefit and make the cache part of the critical consistency path.

Use only when the invariant requires it.

---

## 7.18 Cache Invalidation Race

Consider:

```text
Reader misses cache
Reader reads database value v1
Writer updates database to v2
Writer invalidates cache
Reader writes v1 into cache
```

The stale value is reintroduced after invalidation.

### Mitigations

- versioned values and compare-before-set
- delay double-delete pattern with caution
- write-through
- CDC-driven cache update
- short TTL
- source version validation

### Version check

The cache stores:

```text
value=v1, version=1
```

A fill should not overwrite an entry or source version newer than the read result.

---

## 7.19 Cache Coherence Through Change Data Capture

A database commit log can feed cache invalidation or refresh events.

Benefits:

- update follows committed source state
- durable replay
- decoupled producers

Risks:

- CDC lag
- duplicate events
- schema changes
- cache consumer outage

Consumers should use source versions and be idempotent.

A reconciliation scan may compare cache version with source version for critical datasets.

---

## 7.20 Distributed Cache Partitioning

A cache cluster partitions keys across nodes.

The same sharding concerns apply:

- consistent hashing
- hot keys
- replica placement
- node failure
- rebalancing
- stale routing

### Client-side sharding

Clients compute the cache owner.

Benefits:

- no proxy hop

Risks:

- clients need membership updates
- stale views
- difficult language consistency

### Proxy-based sharding

A proxy routes requests.

Benefits:

- centralized policy
- simpler clients

Risks:

- proxy availability and scaling
- extra hop

---

## 7.21 Cache Replication and Failover

Replicas improve availability but create consistency choices.

### Asynchronous replica

Low write latency, possible stale failover.

### Synchronous replica

Stronger durability, higher latency.

### Failover behavior

If a cache is derived and rebuildable, losing recent entries may be acceptable.

If the cache is used as durable session or write-behind state, the durability requirement is much higher.

### Staff-level rule

Do not call a state store “just a cache” when the system cannot safely rebuild or lose it.

Operational importance follows actual usage, not the component label.

---

## 7.22 Cache Eviction

Memory is finite. Eviction policies include:

- least recently used
- least frequently used
- random
- TTL-based
- size-aware
- admission-based

### Eviction failure mode

An overloaded cache may evict hot entries, causing origin traffic to rise, which slows the origin, causing retries and further cache misses.

This creates a feedback loop.

### Metrics

- hit rate
- byte hit rate
- eviction rate
- memory fragmentation
- item size distribution
- load latency
- rejected writes

Hit rate alone can hide large-object or expensive-miss behavior.

---

## 7.23 Cache Warming

A cold cache after deployment or failover can overload the origin.

Warming options:

- load top keys before traffic
- gradually shift traffic
- preserve cache across deployments
- copy snapshots where safe
- use CDN origin shield

### Risks

- warming stale data
- consuming origin capacity before launch
- loading low-value keys

Warm based on measured popularity and business criticality.

---

## 7.24 Multi-Level Caching

A service may use local and distributed caches.

```text
L1 in-process cache
  -> L2 distributed cache
      -> database
```

Benefits:

- very low local latency
- reduced distributed-cache traffic

Risks:

- L1 invalidation across instances
- multiple freshness windows
- debugging complexity

A common policy is:

- short L1 TTL
- longer L2 TTL
- versioned invalidation event

The total user-visible staleness is determined by the slowest invalidated layer.

---

## 7.25 CDN Fundamentals

A CDN caches responses at edge locations.

Important concepts:

- cache key
- freshness lifetime
- validation
- purge
- origin shield
- regional propagation
- private versus public content

### Cache-Control

HTTP response directives can express:

- public or private
- maximum age
- shared-cache maximum age
- no-store
- no-cache with revalidation
- stale-while-revalidate
- stale-if-error

The exact policy should be intentional and tested.

---

## 7.26 Validation with ETag and Last-Modified

A client or CDN can revalidate cached content.

```text
If-None-Match: "version-18"
```

If unchanged, the origin returns `304 Not Modified` without the full body.

Benefits:

- reduced bandwidth
- fresher content than blind long TTL

Risks:

- origin still receives validation traffic
- weak version generation can return wrong results

An ETag should change whenever the response representation changes for the cache key.

---

## 7.27 CDN Purge

A purge removes or invalidates edge entries.

Challenges:

- propagation delay
- partial regional success
- rate limits
- wildcard purge cost
- stale clients behind other caches

### Safer asset strategy

Use immutable versioned URLs:

```text
/app.7f23c1.js
/logo.v18.png
```

Deploy new references instead of purging old content.

This is more reliable than globally invalidating mutable asset names.

---

## 7.28 Origin Shielding

An origin shield is an intermediate cache layer that collapses misses from many edge locations.

Without shielding:

```text
100 edge POPs miss -> 100 origin requests
```

With shielding:

```text
100 edge POPs -> shield -> 1 origin refresh
```

Benefits:

- origin protection
- better cache efficiency

Risk:

- shield becomes concentrated dependency
- regional latency if placement is poor

Use redundancy and capacity planning.

---

## 7.29 Personalized and Private Content

Caching personalized responses is dangerous if keys and authorization are wrong.

### Required dimensions

- user or tenant identity
- authorization scope
- locale
- experiment assignment
- content negotiation

### Safer strategies

- mark response private
- cache only public fragments
- assemble personalized page at edge compute
- use signed URLs for private objects
- separate public and private origins

Never rely on an untrusted client-provided header as the sole cache isolation key without server validation.

---

## 7.30 Signed URLs and Tokens

Private CDN content may use time-limited signed URLs or cookies.

Review:

- expiration
- key rotation
- audience and path scope
- revocation behavior
- clock skew
- cacheability after authorization

A CDN may cache one object while validating authorization separately for each request.

The cache must not bypass access control.

---

## 7.31 Geo-Distributed Edge Consistency

Edge writes are harder than edge reads.

Read-heavy content can replicate widely with eventual consistency.

Writes may require:

- home-region routing
- local acceptance plus async replication
- conflict-free merge
- global coordination

### Example

A profile update accepted in Europe may take seconds to reach an edge cache in Asia.

For read-your-writes, the response can carry version 42 and subsequent reads require at least version 42 or route to the home region.

---

## 7.32 Cache as Resilience Layer

A cache can protect the origin during failure, but only if:

- stale data is safe
- entries remain available
- cache capacity survives increased demand
- miss paths are bounded

### Failure inversion

If the cache fails and every request falls back to the database, the database may collapse.

This is a cache-failure amplification event.

Mitigations:

- origin concurrency limits
- partial load shedding
- local fallback
- fail closed for expensive misses
- degraded static responses

Do not assume origin can handle full uncached traffic.

---

## 7.33 Cache Dependency Modes

### Optional cache

On cache failure, the system safely uses the source with bounded load.

### Required cache

The origin cannot support traffic without it.

### Authoritative cache

The cache temporarily or permanently owns data not elsewhere durable.

These modes require different SLOs and recovery plans.

Architecture documents should name the actual mode.

---

## 7.34 Security-Sensitive Caching

Authorization and revocation data require conservative policies.

Risks:

- revoked user retains access
- old role grants remain active
- policy change propagates slowly

Strategies:

- short TTL
- push invalidation
- versioned policy tokens
- deny on uncertainty
- critical-path source validation

### Token version

A user record contains `auth_version=17`.

A token or cache entry with version 16 is rejected after revocation increments the version.

This turns invalidation into a version check.

---

## 7.35 Incident: Cache Stampede Takes Down Database

### Scenario

A popular key expires at midnight on every instance.

Twenty thousand requests miss and query the database simultaneously.

### Failure chain

```text
synchronized expiry
  -> cache misses
  -> database overload
  -> timeout
  -> retries
  -> wider outage
```

### Mitigation

- single-flight refresh
- stale-while-revalidate
- TTL jitter
- origin concurrency limit
- prewarming

### Lesson

Cache expiry is a traffic event and must be capacity-modeled.

---

## 7.36 Incident: Private Response Leaked Through CDN

### Scenario

A user dashboard response is cached by URL only.

The CDN serves User A's response to User B.

### Root causes

- response marked public
- cache key omitted identity
- authorization performed only at origin

### Prevention

- `Cache-Control: private` or `no-store`
- separate public and private routes
- validated identity dimension where shared caching is intended
- automated tests with multiple identities

### Lesson

Caching configuration is part of the security model.

---

## 7.37 Incident: Stale Authorization After Revocation

### Scenario

Role membership is cached for 30 minutes. An employee is removed from an admin group but retains access through stale cache entries.

### Correction

- push invalidation
- shorter TTL
- policy version check
- deny high-risk action when freshness cannot be proven

### Lesson

TTL must be derived from security risk, not only performance.

---

## 7.38 Incident: Cache Cluster Failure Overloads Origin

### Scenario

A distributed cache loses quorum. Applications immediately send all traffic to the database.

### Failure chain

```text
cache outage
  -> 100% miss rate
  -> database connection exhaustion
  -> application retries
  -> total service outage
```

### Prevention

- origin admission control
- degraded response mode
- local emergency cache
- gradual recovery
- cache dependency SLO
- regular cold-cache load tests

---

## 7.39 Incident: Out-of-Order Invalidation

### Scenario

Update version 18 is followed by version 19.

The invalidation for 19 arrives first, then the delayed event for 18 refreshes the cache with old data.

### Safe design

Store versions and reject older refreshes.

```text
incoming version 18 < cached/source version 19 -> ignore
```

### Lesson

Invalidation events require ordering or version-aware idempotency.

---

## 7.40 Observability

Measure:

### Performance

- hit rate
- byte hit rate
- load latency
- origin latency
- cache operation latency

### Freshness

- entry age
- source version minus cache version
- invalidation lag
- stale response rate

### Capacity

- memory usage
- eviction rate
- item count
- fragmentation
- hot-key distribution

### Failure

- fallback rate
- origin amplification
- refresh errors
- purge failures
- cache-cluster health

### Business

- stale price incidents
- authorization freshness violations
- oversell caused by stale inventory
- expired content served

---

## 7.41 Design Review Checklist

Before approving a caching design, ask:

- What is the source of truth?
- How stale may the data be?
- Can stale data violate security or money invariants?
- What is the cache key?
- Does it include tenant, user, locale, and authorization dimensions?
- What is the TTL and why?
- Is explicit invalidation required?
- How are invalidation events delivered?
- Are values versioned?
- Can an old fill overwrite a newer value?
- What happens on cache miss?
- Can the origin survive a cold cache?
- Is request coalescing implemented?
- Is stale-while-revalidate safe?
- Are negative results cached correctly?
- What is the eviction policy?
- How are hot keys detected?
- What happens when the cache cluster fails?
- Is the cache actually optional?
- How are CDN purges verified?
- Can private data enter a shared cache?
- What is the read-your-writes mechanism?
- How is freshness measured in production?

---

## 7.42 Staff and Principal Interview Drills

### Question 1

A cache-aside service updates the database and deletes the cache key. What races remain?

Expected direction:

- stale concurrent fill
- invalidation failure
- retry ambiguity
- version checks
- CDC or write-through alternatives

### Question 2

The cache hit rate is 95%, but the database is overloaded. How can that happen?

Expected direction:

- high request volume
- expensive 5% misses
- large-object byte miss rate
- synchronized expiration
- hot-key stampede

### Question 3

When is stale-while-revalidate inappropriate?

Expected direction:

- authorization
- exact balances
- safety-critical routing
- inventory where stale values cause oversell

### Question 4

How would you provide read-your-writes with an eventually refreshed cache?

Expected direction:

- version token
- bypass cache after write
- session-local update
- source routing until version observed

### Question 5

Is a CDN purge enough to update static assets safely?

Expected direction:

- purge propagation uncertainty
- browser and intermediary caches
- immutable versioned URLs

### Question 6

What happens when a cache intended to be optional becomes required at scale?

Expected direction:

- origin cannot handle miss traffic
- cache has become critical dependency
- SLO, capacity, and recovery must reflect reality

### Question 7

How do you prevent private-data leakage through shared caching?

Expected direction:

- cache-control
- key dimensions
- authorization at edge
- separation and tests

### Question 8

How do you invalidate millions of related keys?

Expected direction:

- namespace or generation version
- immutable keys
- tag-based invalidation
- avoid large delete storms

---

## 7.43 Hands-On Labs

### Lab 1 — Cache Stampede

1. Cache one popular value.
2. Expire it under concurrent load.
3. Measure origin requests.
4. Add single-flight refresh.
5. Add stale-while-revalidate and TTL jitter.

### Lab 2 — Stale Fill Race

Reproduce:

1. reader misses
2. reader loads v1
3. writer commits v2 and invalidates
4. reader stores v1

Add version-aware compare-before-set.

### Lab 3 — Read-Your-Writes

Implement a response version token and require subsequent reads to return at least that version.

### Lab 4 — Negative Caching

Generate random absent-key traffic. Compare origin load with and without negative caching and a membership filter.

### Lab 5 — Cold-Cache Failure Test

Disable the cache under production-like traffic.

Measure:

- database connections
- origin latency
- fallback rate
- rejected requests

Add admission control and degraded behavior.

### Lab 6 — CDN Cache-Key Test

Create responses varying by:

- identity
- locale
- encoding

Verify that the cache key never mixes representations or users.

### Lab 7 — Invalidation Lag

Publish versioned updates and delayed invalidation events. Measure source-to-cache version gap and reject out-of-order refreshes.

---

## 7.44 Staff-Level Summary

Caching creates more copies of state.

A production-grade design must connect:

```text
business freshness requirement
  -> cache placement and key
  -> fill and write policy
  -> expiration and invalidation
  -> stampede protection
  -> failure fallback
  -> freshness observability
```

The strongest Staff-level answer treats the cache as a consistency and resilience protocol, not merely a faster dictionary.
