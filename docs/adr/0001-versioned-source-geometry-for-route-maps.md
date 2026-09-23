# ADR 0001: Version authoritative source geometry for route maps

- Status: Accepted
- Date: 2026-09-23
- Decision owners: Wayproof maintainers
- Related: `PRODUCT.md`, `ARCHITECTURE.md`, `DATA_LICENSE.md`

## Context

Wayproof already represents named routes independently from their physical
segments. Sourced relationships connect route segments to endpoints and named
routes, and the traversal resolver uses those relationships to produce ordered
stages and supported distance totals. The website is generated from the same
canonical read boundary used by other consumers.

While deepening Lassen Volcanic National Park route coverage, we discovered two
public federal geometry services that can accelerate route modeling:

- the National Park Service Public Trails FeatureServer, which publishes
  visitor-use trail geometry and fields such as feature identity, trail name,
  status, map method, map source, source date, and positional accuracy; and
- the USGS National Digital Trails service, which aggregates public trail data
  and publishes stable-looking identifiers, source attribution, service
  versions, geometry, and calculated `lengthmiles` values.

Both services can return GeoJSON. The NPS service is the stronger source for NPS
trail identity and geometry; USGS is useful for distance-bearing features and
independent reconciliation. NPS route descriptions and official maps remain
necessary to establish visitor-facing route semantics such as the intended
sequence, signed turns, named junctions, alternatives, and published cumulative
milepoints.

The Warner Valley investigation also demonstrated an important limitation. A
GIS feature network is not necessarily a visitor itinerary. Some described
junctions align with source feature endpoints, while others fall within a
longer feature or cannot be uniquely matched. Converting the same geometry to
GPX does not resolve that ambiguity. A third-party recorded GPX may help a
reviewer investigate a route, but it does not become authoritative merely
because it contains a continuous track.

Wayproof needs to use this geometry for two purposes:

1. evidence-assisted route topology and traversal; and
2. human-readable route maps generated for the website and other consumers.

It must do so without making page rendering depend on a mutable external
service, presenting proximity as route evidence, silently changing historical
maps, or creating a second hand-maintained route database.

## Decision drivers

- Preserve the reviewed geometry associated with a published ChangeSet.
- Keep source identity, provenance, precision, licensing, and uncertainty
  inspectable.
- Make route maps fast and reliable even when an upstream service is slow,
  unavailable, or changed.
- Generate maps through the canonical read/service boundary rather than a
  parallel website catalog.
- Reuse general route and evidence primitives instead of introducing
  destination-specific schema.
- Allow automated discovery and matching without allowing automation to infer
  route semantics from proximity alone.
- Keep Git as the review, concurrency, history, and publication system.
- Avoid importing or mirroring an entire national trail graph when a bounded
  route requires only a small subset.

## Options considered

### 1. Query the upstream service in every visitor's browser

The page would request live GeoJSON from NPS or USGS and render the returned
features directly.

Advantages:

- little local storage;
- upstream changes appear immediately; and
- minimal build-time processing.

Disadvantages:

- website correctness and availability depend on a third-party service;
- upstream geometry can change without a Wayproof ChangeSet or review;
- historical ChangeSets could render using geometry different from what was
  reviewed;
- requests add latency and may encounter CORS, rate, query, or service changes;
- feature selection logic would leak into the presentation adapter; and
- a page could combine current geometry with older claims and distances.

This option is rejected as the publication path. A live query remains useful
for ingestion, upstream comparison, and explicit pre-publication rechecks.

### 2. Store only upstream feature identifiers and fetch geometry when building

Canonical claims would retain service and feature identifiers, while each site
build would query current upstream geometry.

Advantages:

- the generated website does not require client-side upstream access;
- canonical records remain small; and
- builds automatically see source updates.

Disadvantages:

- builds are not reproducible;
- an upstream edit can change published output without a domain review;
- old commits cannot reliably recreate their maps; and
- upstream deletion or identifier changes can break the build.

This option is rejected because a feature identifier is not a historical
geometry snapshot.

### 3. Version a minimal source-geometry snapshot and generate route GeoJSON

During controlled ingestion, Wayproof retrieves only the selected public-domain
features needed by the bounded route. The reviewed response is normalized into
an immutable GeoJSON evidence artifact. Canonical observations and claims
reference that artifact and the source feature identities. The website build
uses promoted route membership and the snapshot to generate route-specific
GeoJSON.

Advantages:

- reproducible maps and historical review;
- no runtime dependency on NPS or USGS;
- small, bounded artifacts rather than a national graph mirror;
- exact linkage between displayed geometry and published evidence;
- automatic page generation through the canonical service layer; and
- upstream changes become reviewable proposals rather than silent mutations.

Disadvantages:

- selected geometry is duplicated from the upstream service;
- snapshots and hashes require ingestion and validation tooling;
- geometry can become stale until it is compared with upstream; and
- Git repositories are not efficient stores for unbounded or frequently
  changing binary/geospatial datasets.

This is the selected option. GeoJSON is text, diffable, directly published by
both government services, and adequate for the bounded feature subsets in
scope.

### 4. Import the complete NPS or USGS trail network

Advantages:

- broad offline graph availability;
- simpler discovery across many destinations; and
- fewer per-route upstream queries.

Disadvantages:

- large and frequently changing repository footprint;
- substantial entity resolution and update complexity;
- most imported features would not support a current product question;
- a physical trail network still would not establish route-specific semantics;
  and
- it would encourage treating an imported graph as canonical knowledge before
  review.

This option is rejected for the current product stage. It may be reconsidered
as a generated research index outside canonical storage if scale provides
concrete evidence for it.

### 5. Use third-party GPX tracks as the primary route geometry

Advantages:

- convenient interchange with navigation tools;
- often continuous from a user's start to destination; and
- useful for discovering gaps in an official network.

Disadvantages:

- collection method, date, accuracy, selected path, and licensing may be
  unclear;
- a recorded trip can include mistakes, detours, or off-trail movement;
- GPX usually lacks authoritative feature identity and route semantics; and
- converting official GeoJSON to GPX adds no new evidence.

This option is rejected as the primary source. A GPX trace may be retained as
properly attributed supporting or conflicting evidence when its provenance and
license allow it.

## Decision

Wayproof will use a build-time, versioned-source-geometry approach.

1. Prefer the land manager's public geometry service for feature identity and
   geometry. For NPS routes, the NPS Public Trails FeatureServer is primary.
2. Use USGS National Digital Trails as a distance-bearing source and for
   reconciliation where its fields support the claim. Do not silently treat a
   USGS aggregation as more authoritative than its identified originator.
3. Use official route descriptions and maps for route-specific semantics. GIS
   geometry alone does not prove access, membership, order, direction, a named
   junction, or an intended visitor itinerary.
4. Retrieve and retain only the features required for a bounded, reviewed
   route or shared corridor. Do not mirror the complete upstream dataset.
5. Normalize the reviewed subset as an immutable GeoJSON evidence artifact.
   Retain its source service and layer, query or selection context, retrieval
   time, upstream version when exposed, coordinate reference system, and a
   content hash.
6. Canonical claims will identify the source feature and snapshot, preserve
   available mapping method/source/date/accuracy, and state the supported route
   role, endpoints, distance, and uncertainty. An observation links the source
   statement or dataset response to those claims.
7. Route membership and topology remain canonical entities, claims, and sourced
   relationships promoted through a validated ChangeSet. A geometry snapshot
   does not create those relationships by itself.
8. The site builder and future adapters will obtain geometry through a general
   read/projection service. They will generate route-specific GeoJSON from
   promoted membership and the reviewed snapshot. Generated map GeoJSON is a
   replaceable presentation artifact, not a second canonical catalog.
9. Website visitors will normally load Wayproof's generated static GeoJSON, not
   query NPS or USGS directly.
10. A later upstream comparison may propose a new ChangeSet and snapshot. It
    must not mutate an already published snapshot or silently change a
    historical route map.
11. When a prose junction or route decision cannot be uniquely matched to an
    official feature or position, Wayproof will retain partial topology and an
    explicit gap. It will not cut a feature at an inferred location merely to
    complete the graph.

## Schema and architecture impact

No Schema v0 migration is required for the pilot.

- `Source` identifies the upstream service or artifact.
- `Observation.artifact_refs` identifies the reviewed snapshot and relevant
  feature selection.
- Structured `Claim.value` can retain source feature identity, snapshot
  reference and hash, coordinates, distance, accuracy, and qualifiers.
- `Entity(kind="route_segment")` supplies durable segment identity.
- sourced `Relationship` records supply endpoints and route membership.
- `SpatialScope` remains geometry-format-neutral.
- the existing ChangeSet lifecycle governs the canonical records that interpret
  the artifact.

This uses the current schema's deliberately general evidence and structured
claim boundaries. It does not make GeoJSON a universal spatial representation
for every `SpatialScope`.

`Observation.artifact_refs` are currently strings rather than first-class
artifact records. For the pilot, a structured claim value plus validation may
carry the snapshot path, media type, and hash. A future first-class `Artifact`
record requires a separately reviewed schema decision only if demonstrated
needs—such as multiple renditions, independent retention policy, signatures,
redaction, or richer licensing—outgrow that boundary.

The exact snapshot directory layout, map rendering library, geometry
simplification algorithm, and refresh schedule are implementation choices.
They must be deterministic and general, but this ADR does not freeze their
spellings before the pilot supplies evidence.

## Required safeguards

The geometry ingestion and publication implementation must validate that:

- the artifact is an allowed public-domain or compatibly licensed source;
- the referenced artifact exists and its content hash matches;
- every referenced feature identifier exists in the artifact;
- geometry types and coordinate reference systems are supported;
- generated route features correspond to promoted canonical claims and
  relationships;
- geometry is not used to manufacture access or topology from proximity;
- source precision and unknown accuracy remain visible;
- a route with unresolved membership or a missing connector remains partial;
- both supported traversal directions continue to resolve where applicable;
- generated GeoJSON and map pages are deterministic and work without upstream
  network access; and
- a source refresh reports added, removed, changed, and unmatched features for
  review rather than overwriting the previous artifact.

## Consequences

Positive consequences:

- route ingestion can use official APIs instead of manually tracing every map;
- shared approaches and alternatives can be discovered and reconciled more
  efficiently;
- humans can inspect the same evidence-backed route graph used by planning;
- map availability and historical output remain under Wayproof's publication
  control;
- selected feature snapshots are small, diffable, and auditable; and
- the approach generalizes across NPS destinations and other compatible public
  land datasets.

Negative consequences:

- geometry ingestion, hashing, comparison, projection, and rendering add code
  and tests;
- source refreshes require review even when changes are harmless;
- some authoritative geometry has unknown age or accuracy;
- official datasets can contain topology errors, duplicated lines, inconsistent
  names, or features that do not align with narrative milepoints; and
- the product still cannot promise navigation-grade accuracy.

Wayproof maps remain planning and evidence interfaces, not turn-by-turn
navigation products. Consumers must be able to inspect sources, precision,
uncertainty, current-condition rechecks, and knowledge gaps alongside the map.

## Initial pilot

The first implementation should use the Warner Valley routes in Lassen
Volcanic National Park:

- preserve the NPS route descriptions for Devils Kitchen, Boiling Springs Lake,
  and Terminal Geyser;
- retrieve the relevant NPS Public Trails features and reconcile USGS
  `lengthmiles` values;
- correct the shared approach where the evidence supports it;
- retain unmatched narrative junctions as explicit gaps;
- generate static route GeoJSON and a reusable route-map presentation; and
- verify provenance, deterministic offline builds, traversal behavior, and
  human-readable display before generalizing the pipeline.

Success means the pilot reduces manual geometry work without reducing
Wayproof's evidence standard. It does not mean every Warner Valley trail line
has been promoted into a complete visitor route.
