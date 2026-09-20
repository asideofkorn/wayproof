# Wayproof Roadmap

## Roadmap contract

This roadmap moves Wayproof from the current Sierra/SPS CSV-backed planner to
the architecture in `PRODUCT.md` and `ARCHITECTURE.md` without pretending the
target is already implemented. Milestones are capability gates, not dates.

Canonical Schema v0 is frozen for initial implementation. The legacy audit is
complete: existing data will be selectively salvaged under the field-level
`KEEP / REVERIFY / RECONSTRUCT / DISCARD` policy, never bulk-migrated as truth.

## M0 — Trusted foundation

**Outcome:** Wayproof can define, validate, review, and safely promote canonical
knowledge for the MVP fixtures.

- Materialize and review the product, architecture, and roadmap decisions.
- Implement Schema v0 domain concepts: identity and temporal relationships;
  evidence lineage; trip/context and route/access/traversal; claims and rules;
  requirements, fulfillments, coverage, answerability, derived results,
  knowledge gaps, and ChangeSets.
- Keep exact module layout, enum spellings, and SQLite timing open until
  implementation evidence supports a choice. Use the decided deterministic,
  versioned, one-record-per-file JSON storage model.
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
  fishing, boating/invasive-species, and California 14ers social-water fixtures.
- Encode the 8/8 adversarial schema audit as regression tests.
- Build the selective salvage importer/queue from the completed field-level
  manifest. Preserve research history and surface re-verification work; do not
  directly migrate ambiguous, inferred, composite, stale, or weakly sourced
  values.
- Run the California 14ers social-water evidence case end to end through
  proposal, validation, explanation, candidate preparation, Git review, and
  merge-based publication.

**Exit criteria:** all Schema v0 invariants and fixtures pass; canonical changes
are traceable to approved ChangeSets; the initial clean corpus can be built and
reproduced without direct table editing; no fixture requires a special-purpose
schema object.

## M1 — Planning MVP

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

**Outcome:** people and agents can inspect and plan through stable adapters over
the same service layer.

- Provide stable read services for objective search, trip planning,
  requirements, advisories, evidence, conflicts, and knowledge gaps.
- Adapt the CLI and website to those services rather than legacy storage shapes.
- Add an MCP read adapter for the same capabilities.
- Return structured answerability, provenance, and freshness information so an
  agent cannot mistake a missing field for confirmation.
- Consider a generated read index only if measured query or startup needs
  justify it; canonical Git-backed knowledge remains the source of truth.

**Exit criteria:** CLI, website, and MCP agree on fixture outputs because they
invoke the same domain behavior rather than reimplementing planning logic.

## M3 — Constrained contribution workflow

**Outcome:** community and agent-assisted evidence becomes reviewable proposals
without granting direct canonical write access.

- Ingest URLs, issues, artifacts, field reports, GPX, and supported structured
  sources into candidate observations/evidence.
- Add constrained proposal operations for sources, observations, claims, rules,
  and relationships plus ChangeSet validation and explanation.
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
  -> selective legacy salvage
  -> planning/readiness/recheck services
  -> CLI and website adapters
  -> MCP read adapter
  -> constrained proposal adapter
```

MCP is not the knowledge store and is not a separate write architecture. A
database is not an M0 prerequisite. Scaling mechanisms are introduced only in
response to demonstrated needs.

## Known design gaps to resolve with implementation evidence

These are intentionally deferred, not forgotten:

- exact Python module and class boundaries;
- exact enum names and wire spellings;
- generated SQLite timing, if any; and
- exceptional repair/redaction policy for published artifacts.

Any new gap that changes product semantics, evidence integrity, applicability,
or coverage should reopen the architecture explicitly. Mechanical choices
should be decided in the implementation PR that first needs them.
