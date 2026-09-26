# ADR 0003: Separate media analysis and navigable evidence

- Status: Proposed — schema and implementation details require review
- Date: 2026-09-26
- Decision owners: Wayproof maintainers
- Related: [Architecture](../../ARCHITECTURE.md), [Roadmap](../../ROADMAP.md),
  [Product](../../PRODUCT.md), [Source policy](../../DATA_LICENSE.md),
  [ADR 0001](0001-versioned-source-geometry-for-route-maps.md)

## Context

Social posts can contribute bounded observations about terrain, facilities,
signs, and conditions. Relevant information may span a caption, individual
attachments, and later author comments. A comment can establish a reported
capture date while leaving the photographed location unresolved. An ordered
caption can identify individual photos only when its correspondence to the
attachment order is explicit and preserved.

Wayproof's existing Source -> Observation -> Evidence -> Claim lineage supports
attributed statements, evidence stance, uncertainty, and scoped claims. It does
not provide dedicated media identity/version, publication-time, clarification,
or analysis-run records. Observation artifact references alone do not establish
which version or frames an analyst inspected. Our visual interpretation must
not appear to be a statement made by the uploader.

The existing fact renderer emphasizes source links, combines observation and
retrieval dates, and groups observations by source ID. That presentation can
hide multiple observations and makes users open external links to understand
the supporting evidence or unresolved disagreement.

The research discussion of [Swarmtraces](https://swarmtraces.org/) and the
[Collusion explorer](https://collusion.wiki/explorer/sites/) motivates readable
evidence excerpts, permanent detail links, source-to-record navigation, and
history. Wayproof should adapt those patterns to outdoor planning while
preserving its own evidence and publication semantics.

## Proposed decision

### Separate source material, statements, and analysis

Model these as distinct concepts, with final record names and serialization
deferred to schema review:

1. Source and media identity: the original post/comment locator, publisher or
   author, individual attachment identity, original attachment order, and the
   identifiable media version inspected. Preserve repost/origin relationships
   when supported; repeated copies are not independent corroboration.
2. Attributed observations and clarifications: what an author actually says,
   including explicit mappings between list items/comments and media items.
   Preserve the wording and uncertainty of the mapping. A commenter must not
   inherit the parent post's authorship or be labeled the author without
   evidence of that relationship.
3. Media analysis: a separately stored run over identified source media, with
   analyst/model identity, analysis time, method/version, inspected images or
   video time ranges, findings, limitations, and corroborating references.
   Distinguish visual inspection, text recognition, transcription, and location
   inference. Model identity alone is not a reproducible method description.

An author statement about a photo and an analysis of that photo may both
support a claim, but their origins must remain inspectable. Analysis is not
automatically canonical truth, and useful observations need not become rules.

### Preserve independent time and location uncertainty

Keep reported capture/event time, source publication time, retrieval time, and
analysis time separate, including their basis and precision. Unknown capture
time remains unknown even when the publication date is known. A later author's
comment supplies an attributed date assertion, not an independently verified
capture timestamp. Preserve conflicting assertions.

Track location attribution separately: author-labeled, visible sign,
corroborated identification, or unresolved inference. Resolving a date does not
resolve the location. A narrow view of a trail cannot establish conditions for
the entire route, present passability, or legal access.

For ordered photo lists, retain each supported list-item-to-attachment mapping.
Do not reconstruct correspondence from a changed display order or assign
locations from nearby scenery. Ambiguous mappings remain unresolved.

### Allow repeated processing without silent promotion

Each analysis run is immutable and references the input version it actually
inspected. New runs preserve earlier findings and may agree, disagree, or use
different methods. A reviewed claim references specific findings/runs rather
than a moving pointer to the latest analysis. Comparing runs does not treat
multiple analyses of the same media as independent field observations.

If the input version cannot be reliably identified or retained, record that
limitation; do not promise exact reproducibility. Source deletion or changed
media must not silently substitute new content for reviewed evidence.

Reprocessing alone must not publish a claim, resolve a gap, create a rule,
change a planning result, or add a related-place link. Canonical changes still
use the domain write boundary, validated ChangeSets, and GitHub review/merge.

### Make evidence understandable before following links

Generated evidence cards should expose the relevant observation, attribution,
evidence stance, dates, scope, and limitations. Distinguish author reports,
visual findings, and Wayproof interpretations, including their analytical
origin even when a finding seems directly visible. Preserve all relevant
observations from a source.

Gap cards should explain the unresolved question, compare relevant statements
in place, distinguish conflicts from missing information or current checks,
and say what additional evidence would resolve the question. Different times
or locations are not automatically contradictions.

Provide permanent claim and observation links, generated source pages with
backlinks, and relevant destination previews derived from reviewed connections.
Discovery attribution is distinct from evidence supporting a claim. Keyword
matches or geographic proximity cannot create a published association.

Use accessible section links and labeled next/previous controls with visible
position and keyboard support; do not depend on tiny unlabeled timeline dots.
Link media timestamps where supported and otherwise display the inspected
range without claiming that the external platform supports seeking to it.

## Scope and source policy

Public accessibility does not grant redistribution rights. Apply DATA_LICENSE
to media, screenshots, excerpts, and thumbnails. Prefer source links and bounded
summaries; storing analysis does not require mirroring the original media.
Hash retained artifacts when lawful and available, without treating a hash as
proof of authorship, location, or capture date. No bulk social scraping, new
binary-media store, or automatic embedding is selected by this ADR.

The Facebook example excluded by the user remains excluded from canonical
sources and public evidence pages. Its behavior may inform synthetic tests;
documenting this pattern does not authorize ingesting that post or other
examples discussed during research.

## Alternatives considered

- Put all analysis in Observation.content: convenient under v0, but conflates
  author statements with analyst output and makes repeated runs hard to audit.
- Replace the previous analysis with the latest: simpler display, but loses
  history and silently changes evidence supporting existing claims.
- Display only outbound links: minimal implementation, but forces users to
  reconstruct comparisons and fails when the original becomes inaccessible.
- Mirror all source media: improves access but introduces rights, retention,
  and storage obligations not justified by the current scope.

## Delivery and acceptance

1. Improve evidence/gap rendering and navigation using existing records and
   shared read services. Do not infer missing metadata from prose merely to
   fill a UI field. This phase does not require a schema migration.
2. Review exact record contracts, validators, version identity, retention,
   migration/backward compatibility, and evidence-to-analysis references.
   Schema v0 remains the contract until this migration is separately approved.
3. Implement bounded ingestion/reprocessing, reviewed analysis selection, and
   history projections through existing domain boundaries. Expand planning
   applicability only with explicit semantics and focused tests.

Use synthetic or appropriately licensed fixtures for unknown dates/locations,
author clarification in comments, partial video inspection, ordered and
ambiguous photo mappings, repeated/conflicting analyses, reposts, source edits,
and unavailable originals. Verify provenance joins, unchanged historical
references, exclusion behavior, readable comparisons, mobile/keyboard
navigation, and parity across generated HTML/JSON and shared read consumers.

## Consequences and open decisions

This design makes evidence reusable and auditable while reducing the effort
needed to understand a planning gap. It adds record relationships, validation,
history, and presentation work. Links may still become unavailable, and
undated media may remain useful only as terrain or facility context.

Exact schema names, analysis storage and retention, input-version fallback,
structured author identity, migration format, and selection/supersession
mechanics remain review decisions. This ADR proposes those capabilities; it
does not freeze their implementation or authorize a new publication path.
