# ADR 0003: Evidence explanations and navigation using existing records

- Status: Accepted
- Date: 2026-09-26
- Decision owners: Wayproof maintainers
- Related: [Architecture](../../ARCHITECTURE.md), [Roadmap](../../ROADMAP.md),
  [Product](../../PRODUCT.md), [Source policy](../../DATA_LICENSE.md)

## Context

The current fact renderer emphasizes source links, combines observation and
retrieval dates, and groups observations by source ID. Multiple observations
from one source can disappear from the presentation. Users must follow external
links to reconstruct the evidence behind a claim or unresolved gap.

The evidence explorers discussed during design motivate readable excerpts,
permanent links, source backlinks, and history. These are UI patterns, not an
endorsement of those reports' claims or a new Wayproof ingestion policy.

## Decision

Render existing canonical knowledge through the shared read services, preserving
Source -> Observation -> Evidence -> Claim. No schema migration or media-analysis
pipeline is required by this decision. Implementation is independent of
[ADR 0004](0004-repeatable-media-analysis.md), whose accepted media requirements
retain a separate schema-design and migration review.

1. Evidence cards show the observation content, attribution, evidence stance,
   notes/limitations, scope, and separate observation and retrieval dates.
   Preserve every relevant observation instead of collapsing by source ID.
   Do not invent publication/capture metadata or parse prose to fill absent
   structured fields. Do not relabel analyst interpretations as author reports.
2. Gap cards explain the unresolved question and compare relevant statements in
   place, distinguishing conflicts, missing information, and current checks.
   Different dates or locations are not automatically contradictions. Explain
   what evidence is needed without implying that a gap has been resolved.
3. Generate permanent observation/claim links, source detail pages with
   backlinks, and relevant destination previews from canonical read services.
   Reviewed relationships supply relevance; proximity and keyword matches do
   not create it. Discovery attribution is separate from supporting evidence.
4. Provide labeled section and next/previous links, visible position, keyboard
   navigation, and usable mobile targets. Do not rely on unlabeled timeline
   dots. Expose the original-source link alongside a useful bounded summary.
5. Show published history without treating repeated source copies or multiple
   analyses as independent corroboration. Missing external originals should
   have explicit availability context, not substituted content.

Whenever information is used, its source and provenance must be visible and
traceable. Existing licensing and privacy safeguards apply to every preview.
Do not mirror media, add embeds, or introduce new analysis fields in this phase.
Future media displays depend on the separately approved provenance contract.

## Alternatives considered

- Outbound links alone leave comparison work to users and depend on external
  availability.
- Collapse by source reduces clutter but loses distinct observations.
- Wait for a media schema unnecessarily blocks existing-record improvements.
- Build a separate website evidence catalog duplicates the canonical read model.

## Acceptance

Verify source-level multi-observation preservation, dates, evidence stance,
conflict/missing/current-check distinctions, permanent links and backlinks,
keyboard/mobile navigation, and HTML/JSON parity through shared read services.
Unknowns stay unknown; historical observations cannot silently become present
access, prices, passability, or resolved planning answers. No canonical-data
changes are required for rendering-only work.

## Consequences

Users can understand evidence and gaps before leaving Wayproof. Read projections
and UI tests become richer, but the existing data contract remains stable.

## Design references

- Sydney Von Arx, Cormac Slade Byrd, Spencer Kitts, and Thomas Larsen,
  [Discovery of a new OpenAI agent message board](https://collusion.wiki/),
  September 4, 2026 — the research report itself;
  [its evidence explorer](https://collusion.wiki/explorer/sites/) is a separate
  navigation example.
- Alex Forman et al.,
  [Revealing the details of how OpenAI agents hacked Hugging Face](https://swarmtraces.org/),
  September 25, 2026 — Swarm Traces web report;
  [its evidence viewer](https://swarmtraces.org/viewer/) is the UI reference.
