# Wayproof Architecture

## Status and scope

This document records the implemented foundation and remaining target
architecture for Canonical Schema v0. The repository is currently hybrid: the
existing CSV-backed planner remains operational while canonical JSON and the
new domain services run alongside it. Schema v0 is frozen for initial
implementation after reference-fixture review, an 8/8 adversarial audit, and a
complete legacy-corpus audit that found no case requiring a redesign.

The architecture is domain-first and storage-independent. Names below identify
durable concepts, not final Python classes, files, tables, or enum spellings.
The canonical website now exercises the shared read boundary at publication
scale; the remaining hybrid boundary is primarily the legacy CLI and the
not-yet-implemented constrained MCP proposal adapter.

## Architecture decision records

Focused implementation decisions that refine this architecture are recorded in
`docs/adr/`. [ADR 0001](docs/adr/0001-versioned-source-geometry-for-route-maps.md)
selects bounded, versioned public-source geometry snapshots and build-generated
route GeoJSON while retaining Schema v0's geometry-neutral spatial scopes and
the controlled ChangeSet publication boundary. [ADR 0002](docs/adr/0002-interactive-map-rendering-and-basemap-sources.md)
selects self-hosted MapLibre GL JS with initial USGS topo and aerial raster
basemaps, while keeping basemap context separate from Wayproof geometry
evidence. Its production amendment removes the contextless schematic while
retaining textual route facts, map-status messaging, and downloadable GeoJSON.
The same immutable-snapshot safeguards apply to managed-land polygons:
canonical claims select reviewed source features, while the read service
assembles display geometry without treating visual overlap as a relationship.

## Architectural principles

1. Storage is not the write API.
2. Canonical knowledge is never directly authored by an AI agent.
3. Observations are preserved separately from claims derived from them.
4. Rules, applicability, requirements, and fulfillment are separate concepts.
5. Time and geographic scope are first-class.
6. Absence, unknown, unavailable, closed, conflicting, and not applicable must
   not collapse into one state.
7. A route or access relationship requires evidence; proximity cannot establish
   feasibility.
8. Specialized destinations are expressed by general primitives plus context,
   not destination-specific schema forks.

## Canonical knowledge and evidence

The evidence lineage is:

```text
Source -> Observation -> Evidence -> Claim -> Rule / DerivedResult
```

- A `Source` identifies where information came from and carries retrieval and
  authority context. Authority is claim- and context-specific, not a universal
  ranking attached to a publisher.
- An `Observation` preserves what a source or reporter actually stated or
  recorded, including observation time, retrieval time, artifacts, attribution,
  and uncertainty. Observations are append-only history rather than mutable
  current truth.
- `Evidence` connects an observation or artifact to the proposition it supports
  or challenges and records the nature of that support.
- A `Claim` is an atomic proposition about a subject, predicate, value, scope,
  and applicable time. Composite prose is decomposed rather than copied into a
  timeless fact.
- A `Rule` expresses a normative or operational consequence under stated
  conditions. A source statement does not become a rule merely because it uses
  imperative language.
- A `DerivedResult` is a reproducible conclusion from claims, rules, trip
  context, and resolver behavior. It is not silently promoted into source fact.

Textual disagreement is not automatically an evidence conflict. Sources may be
describing different predicates, locations, times, or scopes. Genuine
unresolved conflicts remain visible; supersession does not erase history.

## Entities, relationships, and time

Entities have durable identity. Relationships are explicit, sourced, scoped,
and temporal when the world can change. Important relationships include
containment, management, operation, regulation, booking, route membership,
entry/exit, access, and traversal.

Time may qualify entities, relationships, observations, claims, rules,
credentials, fulfillments, and derived results. The model must support effective
intervals, observed/retrieved dates, recurring seasons and schedules, release
windows, deadlines, historical resolution, and partial supersession. A current
answer must not overwrite the answer that applied to an earlier trip.

## Trip and planning context

`Trip` represents the evaluated planning object. `TripIntent` is the user's
requested objective and constraints; `PlanningContext` is the resolved context
used for evaluation. `TripObjective` is not restricted to a peak.

The implemented resolver matches named objectives to canonical entities and
uses sourced `approached_via`, route-membership, and endpoint relationships to
resolve route and access choices. It returns explicit resolved, partial,
ambiguous, or unknown states. It does not choose between competing routes,
infer a return-to-start, or invent topology. Later expansion may add aliases,
constraint matching, and deeper traversal projection without moving this logic
into an adapter.

When a route publishes directed member segments, the traversal resolver finds
an evidenced path between the selected endpoints and emits one ordered stage
per atomic leg. Distance is accumulated only from published values; mapped
connectors without a printed distance keep the aggregate explicitly
incomplete. Official-mainline segments provide the default path. Parallel
alternates, spurs, and their accessible facilities remain visible choices and
are not silently substituted into the trip. A route without segment topology
keeps a coarse route stage and produces a partial result.

Planning-input projection uses an explicit predicate-to-category registry for
cost, deadline, inventory, and closure claims. It never assigns semantics from
predicate spelling or prose. Relevance follows resolved entities, one sourced
relationship hop, projected spatial scopes, trip date, and explicit activity
applicability. Canonical knowledge gaps identify supported conflict threads.
Every projected input retains evidence and answerability; volatile open-ended
claims require a current check. This layer identifies planning components but
does not infer quantities or choose among fee alternatives.

Operational evaluation sits on that projection. It totals only a set of
applicable inputs that each expose exactly one monetary amount. Structured
advance windows can be converted to trip-relative opening and closing dates;
their status requires an explicit caller-provided `as_of_date`, avoiding hidden
wall-clock behavior. Published inventory never becomes live availability.
Explicit effective closed status can block, while open-ended and seasonal
closure claims require rechecking. Conflict gaps keep the evaluation partial.

Ordered `TripStage` values locate relevant portions of a trip. Route primitives
represent routes and route variants; access primitives represent ways to reach
or leave them; traversal connects the trip to ordered segments, places, land
units, facilities, and jurisdiction changes. Entry and exit are distinct. A
known pair of endpoints does not imply that the path between them is known.

The planner carries only context relevant to a decision:

- `PartyContext` for count and rule-relevant participant characteristics;
- `ActivityContext` for activities such as hiking, camping, fishing, or
  boating; and
- `EquipmentContext` for rule-relevant equipment identity, properties,
  credentials, state, and bounded prior events.

Applicability may depend on current context or explicit prior history. For
example, a boat's recent use in an infested waterbody may trigger inspection,
quarantine, dry-out, or decontamination at the next lake.

## Geospatial scope projection

Claims and rules attach to explicit spatial scopes: an entity, point, facility,
zone, route, route segment, land unit, or other geometry. Planning projects
those scopes onto the resolved trip traversal. A rule applies only when its
spatial, temporal, route, activity, party, equipment, and other conditions fit.

Projection must preserve partial resolution. If only the endpoints are known,
Wayproof can answer endpoint questions but must not infer the intermediate route
or every crossed jurisdiction. Legal openness, observed physical condition, and
capability for a particular party or vehicle remain separate predicates.

## Rules, requirements, and fulfillment

The coverage chain is:

```text
Rule -> Requirement -> Fulfillment
```

A `Rule` can prohibit an action, impose a condition, or generate one or more
`Requirement` values for a particular trip context. A requirement identifies
what must be true and the population, dates, stages, places, activities,
vehicles, or equipment it covers.

A `Fulfillment` is evidence that some or all of a requirement has been
satisfied. It may be a permit, reservation, credential, completed action or
process, passed inspection, verified condition, or other accepted mechanism.
Inspection is not permission; a reservation confirmation is not necessarily a
permit; one booking can be a precondition for or emit another credential.

Coverage is many-to-many and explicit. A fulfillment may cover only part of a
party, one vehicle, a subset of nights, or selected trip stages. Conversely, one
requirement may need multiple fulfillments. Readiness cannot be complete while
required coverage remains partial.

## Answerability and freshness

Each planning question returns both a result and its answerability. Required
semantic states include answered, partial, conflicting, unknown, not applicable,
and needs-current-check; implementations may refine their exact representation.

`UNKNOWN` means Wayproof lacks enough evidence. `UNAVAILABLE` means the relevant
thing was checked and confirmed unavailable. `CLOSED` is an operational state,
not absence. Freshness is predicate- and trip-date-specific: a dated observation
can be valid history while being too old to establish a future condition.

The implemented Trip Readiness slice aggregates rule applicability,
requirements, fulfillment coverage, linked gaps, answerability, and provenance.
The composed plan now carries explicitly classified and boundedly evaluated
cost, deadline, inventory, closure, and conflict inputs alongside that
requirement slice; quantity selection and live operational integrations remain.
Pre-trip Recheck projects the canonical
recheck manifest onto trip date and spatial scope, distinguishes answered,
unknown, and needs-current-check results, and returns the sources to revisit.

The shared `plan` operation composes intent resolution, constraint evaluation,
readiness, and explicitly selected recheck manifests. It preserves separate
states for resolution and readiness: complete permit coverage cannot erase an
incomplete traversal, while ambiguous or unknown intent stops before rule
evaluation. Spatial projection accepts both directly linked scopes and
claim-backed scope attachments so older Schema v0 route fixtures participate
without a data rewrite or adapter-specific exception.

## Controlled write architecture

All writers use the same domain/service boundary, while Git and GitHub remain
the publication authority:

```text
evidence
  -> ChangeSet (DRAFT)
  -> validate (VALIDATED)
  -> prepare candidate snapshot
  -> Git commit / PR / CI
  -> maintainer approval
  -> merge to main (PROMOTED / PUBLISHED)
```

Validation enforces schema conformance, durable references, atomicity,
provenance, evidence lineage, temporal and geospatial semantics, controlled
predicates/attributes, rule applicability, coverage integrity, and change-state
transitions. Validation failure cannot be promoted. `VALIDATED` means that
uncertainty and gaps are represented legally, not that every claim is certain.

The domain service does not approve, publish, or mutate the canonical base. It
produces a detached candidate for Git review. Git supplies content identity,
exact diffs, concurrency, review, rollback, history, and reproducible published
versions. Maintainer merge authorization is approval for the current
single-maintainer project; merge to `main` is promotion and publication. CI
rejects canonical changes that are not fully accounted for by a validated typed
ChangeSet.

A permanent ChangeSet carries domain intent rather than duplicating Git audit
metadata: an ID, versions, summary, and ordered `ADD`, `REPLACE`, or
`REMOVE` operations naming affected record types, durable IDs, canonical
paths, reasons, and relevant evidence or knowledge-gap references. Git and
GitHub remain authoritative for authors, timestamps, reviews, commits, and PRs.

Promoted ChangeSets form public, wiki-like revision history. Consumers can walk
from a current record to the published edits that affected it, or from a
ChangeSet to its records and Git history. Real-world history remains in dated
Observations and temporally scoped Claims; publication history remains in Git
and ChangeSets.

Ordinary code, tests, documentation, and rendering PRs require no ChangeSet when
canonical knowledge is untouched. Schema migrations use a separately reviewed,
deterministic migration artifact. An administrative escape hatch may eventually
exist, but bypassing validation must never be the routine workflow.

## Storage and service boundaries

Git-backed structured files are sufficient canonical storage for M0/M1; no
database is required. The domain layer loads and indexes canonical knowledge in
memory and exposes query and write services. `CanonicalReadService` is the
shared read-only facade for entity search, typed lookup, provenance, published
ChangeSet history, requirements, readiness, and recheck. Storage adapters
implement those services but do not define domain semantics.

A generated SQLite index may later improve read performance, and a transactional
database may eventually serve a concurrent application, but neither decision is
part of Schema v0. Canonical storage uses versioned, deterministic,
one-record-per-file JSON named by durable record ID. The serializer owns
formatting; normal contributors and agents do not hand-author canonical files.
Schema v0 records live at `canonical/v0/<collection>/<record-id>.json`, and
permanent intent manifests live at `changesets/v0/<change-set-id>.json`. The
storage adapter applies only paths authorized by a validated ChangeSet. CI
loads and validates the resulting snapshot, then requires the Git action for
every canonical path to match exactly one typed operation in the new manifest.

CLI, website, importers, and MCP are adapters over the same domain/service layer.
MCP must not create a second mutation path.

The canonical `plan.py` mode is a thin terminal adapter: it constructs a typed
intent, calls `CanonicalReadService.plan`, renders the returned object, and can
serialize that same object as JSON. It has no route, rule, cost, deadline, or
readiness logic of its own. The CSV-backed mode remains available during
migration rather than being reinterpreted as canonical knowledge.

The deployed website is a static publication adapter over
`CanonicalReadService`, not an independent content model. Every canonical
entity receives an evidence/history detail page. Search and the Parks, Trails,
Camping, and Peaks directories are generated from canonical entity kinds;
published ChangeSet operations generate the Changes page. Their HTML, JSON
indexes, and sitemap entries are rebuilt after promotion to `main`. Focused
destination and corridor pages may compose more useful views from the same read
service, as Del Valle and the Ohlone Wilderness Trail do, but must not own
parallel facts or planning logic. Volatile conditions and rechecks remain
contextual to those entities and trips rather than forming a global status
surface.

Schema migrations change representation rather than outdoor knowledge. They
declare source and target versions, preserve provenance, produce explicit gaps
instead of invented values, and never rewrite historical promoted ChangeSets.
Artifact format, domain schema, and validator versions are tracked separately.

Initial MCP capability remains read-oriented, including entity search, typed
lookup, requirements, readiness, contextual recheck, history, knowledge gaps,
and evidence inspection. The implemented read-only MCP server exposes those
capabilities directly over `CanonicalReadService`, including bounded
intent-to-plan resolution, and has no write, approval, or promotion tools. The
resolver remains domain-owned rather than adapter-owned inference. The implemented
`ConstrainedProposalService` is the boundary for a later proposal adapter: an
identified actor may submit additive entities,
scopes, sources, observations, evidence, claims, relationships, and gaps, then
validate and explain the draft. It derives paths and operations and deliberately
excludes rules, derived results, runtime requirements/fulfillments,
`REPLACE`/`REMOVE`, candidate preparation, approval, and promotion. Raw
canonical CRUD, arbitrary SQL, and direct agent promotion are not part of the
authoring surface.

The current EBRPD coverage expansion validates this separation: dozens of new
park profiles passed through the ordinary Source-to-Claim and ChangeSet
lifecycle, then appeared automatically in the website's canonical directories.
No destination-specific schema or manually maintained web catalog was required.

## Legacy corpus audit and salvage policy

The completed audit chose selective salvage rather than bulk migration. Schema
v0 starts as a clean canonical corpus. Legacy CSVs remain research and migration
inputs; no dataset is mechanically reclassified as truth.

Every legacy field receives one treatment:

- `KEEP`: understood, sufficiently sourced candidate data, promoted only with
  retained provenance;
- `REVERIFY`: useful concept or value that must be checked before promotion;
- `RECONSTRUCT`: information worth retaining but split or remodeled as atomic
  entities, relationships, observations, claims, or rules; and
- `DISCARD`: inference, presentation artifact, obsolete field, unsupported
  guess, or other value that must not enter canonical knowledge.

Field-level outcome by legacy area:

| Legacy area | KEEP candidates | REVERIFY | RECONSTRUCT | DISCARD |
|---|---|---|---|---|
| Peaks | names, aliases, sourced coordinates/elevation | region | notes | proximity-derived nearest trailhead |
| Trailheads and passes | identity, sourced geometry/elevation | side, quad | agency/land/route relationships and notes | tiers, direct permit attributes, unsourced notes |
| Sources and source deferrals | source IDs, publishers, URLs, retrieval facts | identity matches | claim-specific authority/referral relationships | universal authority rankings, notes-as-facts |
| Water sources/log | identity, sourced geometry/type, dated checks and reported status | locations and source resolution | potable/availability prose into observations and claims | timeless availability inference |
| Approaches/routes | source URL and date | entity resolution | approach, traversal, access, and permit relationships | proximity as access; direct peak-to-trailhead assumptions |
| Permits/zones/releases | source/log identity and verified codes/names | all operational values | mechanics into atomic temporal claims and rules | assumed/self-issued/free values and unsupported guesses |
| Regulations/advisories | IDs, sources, observation dates | scope and citations | summaries/status into atomic scoped claims/rules | presentation severity as truth |
| Timed entry/access/hours/fees | historical source references | historical values | yearly/seasonal facts into temporal claims/rules | flattened schedules and default assumptions |
| Booking facilities/channels | external IDs, URLs, source references | names, operators, contacts | operator/agency/facility relationships and booking mechanics | inferred facility patterns and prose interpretation |
| Campgrounds/campsites | identity and sourced geometry | capacity/type/facility facts | operations, booking, fees, access, amenities, seasons | booking-system leakage and schema-derived assumptions |
| Collections/benchmarks | identity references | memberships and route facts | sourced relationships plus test fixtures | treating collections or measurements as intrinsic truth |
| Pending reports/freeform notes | source/history where attributable | candidate assertions | observations, evidence, conflicts, and research queue | bulk import as canonical fact |

The audit found valuable history in permit source logs, pending reports, water
logs, advisories, and timed-entry records. It also found composite rules,
inferences, known errors, flattened schedules, approximate geometry, and explicit
assumptions. Those findings validate the evidence, temporal, relationship, and
knowledge-gap primitives; none forced Schema v0 to reopen.

## Required regression suite

Implementation must preserve the Ohlone, Williamson/Tyndall, Whitney,
facility/concessioner, fishing, and boating/invasive-species fixtures described
in `PRODUCT.md`. It must also encode the eight
adversarial cases as durable tests:

1. legally open road versus physically impassable;
2. official water listing versus recent dry report;
3. partial route resolution;
4. requirement coverage mismatch;
5. source/rule supersession;
6. unknown versus unavailable;
7. compound spatial/activity/equipment scope; and
8. evidence disagreement.

Passing means the case resolves with general Schema v0 primitives, preserves
gaps and conflicts, and does not invent a destination-specific exception.

## Implementation boundary and unresolved decisions

The initial modules and enum spellings are now implemented in code and guarded
by the end-to-end lifecycle acceptance test. They are service contracts to
exercise through adapters, not justification for a database or a schema
redesign. Generated SQLite timing and an exceptional repair/redaction policy
for published artifacts remain unresolved until implementation evidence makes
them necessary.
