# Wayproof Roadmap

## Roadmap contract

This roadmap moves Wayproof from the legacy Sierra/SPS CSV-backed planner to the
architecture in `PRODUCT.md` and `ARCHITECTURE.md`. Canonical foundations and
several planning services are now implemented alongside the legacy planner;
milestones remain capability gates, not dates.

Canonical Schema v0 is frozen for initial implementation. The legacy audit is
complete: existing data will be selectively salvaged under the field-level
`KEEP / REVERIFY / RECONSTRUCT / DISCARD` policy, never bulk-migrated as truth.

## M0 — Trusted foundation

**Status: complete.** The accepted M0 scope excludes bulk legacy migration and
the California 14ers social-water example. Existing data is added only when it
exercises a product capability or can pass the selective salvage policy.

**Outcome:** Wayproof can define, validate, review, and safely promote canonical
knowledge for the MVP fixtures.

- Materialize and review the product, architecture, and roadmap decisions.
- Implement Schema v0 domain concepts: identity and temporal relationships;
  evidence lineage; trip/context and route/access/traversal; claims and rules;
  requirements, fulfillments, coverage, answerability, derived results,
  knowledge gaps, and ChangeSets.
- Use the implemented Python service boundaries and enum spellings as the
  initial adapter contracts. Keep SQLite timing open until measured evidence
  supports it. Use deterministic, versioned, one-record-per-file JSON storage.
- Implement deterministic validation before scaled ingestion: references,
  provenance, atomicity, evidence integrity, temporal and geospatial scope,
  applicability, coverage, and lifecycle transitions.
- Implement one domain write boundary that produces validated, detached
  candidate snapshots. GitHub review supplies approval and merge to `main`
  supplies promotion/publication.
- Keep permanent ChangeSets focused on typed domain intent; use Git for content
  identity, diffs, concurrency, audit history, rollback, and publication.
- Add CI enforcement proving every canonical diff is exactly accounted for by
  a validated ChangeSet or explicit schema-migration artifact.
- Encode the Ohlone, Williamson/Tyndall, Whitney, facility/concessioner,
  fishing, and boating/invasive-species fixtures.
- Encode the 8/8 adversarial schema audit as regression tests.
- Apply the completed field-level salvage manifest selectively as fixture or
  product needs arise. Preserve research history and surface re-verification
  work; do not directly migrate ambiguous, inferred, composite, stale, or weakly
  sourced values.
- Run the controlled lifecycle end to end through proposal, validation,
  explanation, separate candidate preparation, publication verification,
  Git-backed persistence, read history, requirements, readiness, and recheck.

**Exit criteria:** all Schema v0 invariants and fixtures pass; canonical changes
are traceable to approved ChangeSets; the initial clean corpus can be built and
reproduced without direct table editing; no fixture requires a special-purpose
schema object.

## M1 — Planning MVP

**Status: in progress.** Rule applicability, runtime requirements, explicit
fulfillment coverage, bounded Trip Readiness, Pre-trip Recheck, provenance, and
the complete lifecycle acceptance test are implemented. Named objective,
route, and access intent resolution is implemented conservatively; richer
published segment topology now expands into ordered planning stages and
requirement coverage. Richer constraint resolution and several readiness
inputs remain.

**Outcome:** a bounded trip produces explainable Trip Readiness and Pre-trip
Recheck results from canonical Schema v0 knowledge.

- Resolve `TripIntent` into objectives, ordered stages, route/access/traversal,
  and planning context.
- Project temporal and geospatial scope onto the trip.
- Evaluate rules and produce requirements with explicit fulfillment coverage.
- Represent route-dependent partial answers, costs, deadlines, inventory state,
  closures, and knowledge gaps without treating silence as permission.
- Deliver answerability and evidence explanations for every material result.
- Support PartyContext, ActivityContext, and rule-relevant EquipmentContext,
  including bounded prior events.
- Preserve useful current CLI behavior while shifting resolution behind the
  domain/service layer.

**Exit criteria:** the MVP contract in `PRODUCT.md` passes for all reference
fixtures, including distinct entry/exit, route-specific Whitney permits,
coverage mismatches, historical rules, and volatile water/access rechecks.

## M2 — Read interfaces and MCP

**Status: in progress.** The shared read-only service facade now supports entity
search, typed lookup, evidence provenance, published ChangeSet history,
requirements, readiness, and recheck. The deployed website now uses that facade
for canonical search, every entity detail, automatic Parks/Trails/Camping/Peaks
directories, public ChangeSet history, and the focused Del Valle destination
and Ohlone trail guides. It also generates corresponding JSON indexes and
sitemap discovery. A read-only MCP server now exposes search, typed lookup,
provenance, history, knowledge gaps, bounded intent resolution, requirements,
readiness, and contextual recheck through the same facade. CLI migration
remains.

**Outcome:** people and agents can inspect and plan through stable adapters over
the same service layer.

- Provide stable read services for objective search, trip planning,
  requirements, advisories, evidence, conflicts, and knowledge gaps.
- Keep the website on those services and migrate the remaining CLI behavior
  away from legacy storage shapes.
- Keep the MCP read adapter on the same capabilities and expand its planning
  output only as the underlying M1 services expand.
- Return structured answerability, provenance, and freshness information so an
  agent cannot mistake a missing field for confirmation.
- Consider a generated read index only if measured query or startup needs
  justify it; canonical Git-backed knowledge remains the source of truth.

**Exit criteria:** CLI, website, and MCP agree on fixture outputs because they
invoke the same domain behavior rather than reimplementing planning logic.

**Next capability gate:** add constraint-aware planning and remaining readiness
inputs, then migrate the useful legacy CLI behavior without duplicating domain
resolution in an adapter.

## M3 — Constrained contribution workflow

**Status: started.** An identified-actor, additive-only proposal service can
derive a DRAFT ChangeSet, validate it, and explain failures. It cannot prepare,
approve, promote, or publish canonical knowledge.

**Outcome:** community and agent-assisted evidence becomes reviewable proposals
without granting direct canonical write access.

- Ingest URLs, issues, artifacts, field reports, GPX, and supported structured
  sources into candidate observations/evidence.
- Add constrained proposal operations for evidence-bearing records and
  relationships plus ChangeSet validation and explanation. Keep normative rule
  and derived-result authoring outside the initial consumer proposal surface.
- Keep approval and publication in GitHub review and merge; MCP proposal tools
  do not gain a separate promotion path.
- Improve entity resolution, duplicate detection, supersession/conflict review,
  and research queues for `REVERIFY` and `RECONSTRUCT` legacy material.
- Preserve licensing and source-policy constraints from `DATA_LICENSE.md` and
  the established contribution workflow.

**Exit criteria:** a contributor report can move from evidence to an explainable
PR through the controlled lifecycle, and neither an AI agent nor an MCP client
can perform raw canonical CRUD.

## M4 — Coverage and operational scale

**Status: started for coverage; operational-scale work is not started.** The
canonical corpus now includes every current top-level parkland page found in the
official EBRPD directory, promoted in reviewable source-backed batches. This
proved that a new regional corpus can reuse Schema v0, the controlled write
lifecycle, and automatic publication without destination-specific branches.

**Outcome:** expand geography, activities, and collaboration only after the
MVP's trust model is durable.

- Grow beyond the initial Sierra/public-lands coverage through fixture-backed,
  source-backed additions rather than destination-specific schema branches.
- Add more activities and rule domains when they fit the general context,
  applicability, requirement, and fulfillment model.
- Improve monitoring, freshness policies, recheck scheduling, moderation, and
  multi-contributor review.
- Generate SQLite or adopt transactional infrastructure only when measured
  scale, concurrency, or service requirements justify it; keep canonical and
  published-state semantics explicit.
- Revisit approval policy only with auditable authorization and rollback.

**Exit criteria:** new regions and activities can be added without bypassing the
domain write boundary, weakening provenance, or changing the meaning of
answerability and coverage.

## MVP sequencing

The implementation order is deliberately:

```text
Schema v0 domain model
  -> validators and regression fixtures
  -> ChangeSet validation and candidate preparation
  -> clean canonical storage
  -> selective legacy salvage as needed
  -> planning/readiness/recheck services
  -> shared read facade and constrained proposal service
  -> CLI and website adapters
  -> MCP read adapter
  -> MCP proposal adapter
```

MCP is not the knowledge store and is not a separate write architecture. A
database is not an M0 prerequisite. Scaling mechanisms are introduced only in
response to demonstrated needs.

## Known design gaps to resolve with implementation evidence

These are intentionally deferred, not forgotten:

- generated SQLite timing, if any;
- exceptional repair/redaction policy for published artifacts; and
- authorization policy beyond the current maintainer-reviewed GitHub workflow.

Any new gap that changes product semantics, evidence integrity, applicability,
or coverage should reopen the architecture explicitly. Mechanical choices
should be decided in the implementation PR that first needs them.
