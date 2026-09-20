# Wayproof Architecture

## Status and scope

This document records the target architecture for Canonical Schema v0. The
existing CSV-backed planner remains the current implementation during migration.
Schema v0 is frozen for initial implementation after reference-fixture review,
an 8/8 adversarial audit, and a complete legacy-corpus audit that found no case
requiring a redesign.

The architecture is domain-first and storage-independent. Names below identify
durable concepts, not final Python classes, files, tables, or enum spellings.

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

Trip Readiness aggregates applicable rules, requirements, fulfillment coverage,
conditions, costs, deadlines, gaps, and conflicts. Pre-trip Recheck reruns
volatile portions against the same context and explains changes.

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
memory and exposes query and write services. Storage adapters implement those
services but do not define domain semantics.

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

Schema migrations change representation rather than outdoor knowledge. They
declare source and target versions, preserve provenance, produce explicit gaps
instead of invented values, and never rewrite historical promoted ChangeSets.
Artifact format, domain schema, and validator versions are tracked separately.

Initial MCP capability is read-oriented, conceptually including objective
search, trip planning, requirements, advisories, and evidence inspection. Later
constrained proposal tools may inspect entities/evidence, propose sources,
observations, claims, rules, and relationships, then validate and explain a
ChangeSet. Raw canonical CRUD, arbitrary SQL, and direct agent promotion are not
part of the initial authoring surface.

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
facility/concessioner, fishing, boating/invasive-species, and California 14ers
social-water fixtures described in `PRODUCT.md`. It must also encode the eight
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

## Intentionally unresolved

Implementation will decide exact Python module/class layout, exact enum
spellings, and if or when to generate SQLite. These are not architectural gaps
until implementation evidence requires a choice.
