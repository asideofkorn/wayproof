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
requirement coverage. A composed planner carries resolved party, activity, and
equipment context through readiness and named rechecks without collapsing their
answerability states. Explicitly registered cost, deadline, inventory, closure,
and conflict claims now project into that plan with provenance and contextual
answerability. Unambiguous costs and structured advance windows now receive
bounded operational evaluation; live inventory, current closures, and
quantity/option selection remain incomplete.

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
readiness, contextual recheck, and the composed planning operation through the
same facade. A canonical `plan.py` mode now calls that composed operation and
renders human or complete JSON output; CSV-backed planning remains the default
during transition.

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
- Deliver existing-record evidence explanations and navigation under accepted
  [ADR 0003](docs/adr/0003-evidence-explanations-and-navigation.md):
  - First, use existing canonical records to show observation content,
    attribution, evidence stance and limitations, distinct observation and
    retrieval dates, and readable gap comparisons. Preserve multiple
    observations from one source rather than collapsing them by source ID.
  - Add permanent observation/claim links, generated source pages and reviewed
    related-place backlinks, plus accessible section and next/previous
    navigation. Users should understand an observation's relevance before
    opening its original source.
  - Implemented for Schema v0: shared evidence detail projections and HTML/JSON/MCP
    consumers, observation-preserving comparisons, source/observation/evidence/claim/gap
    permalinks, related-place links, history, and section/previous/next navigation.
    This does not implement the media schema or processing stages under ADR 0004.
  **Gate:** users can understand a gap and compare its evidence in place;
  unknown dates and locations remain explicit, and links never imply current
  conditions or independent corroboration merely through repetition.
- Turn those evidence permalinks into a time-scoped distribution surface:
  - Generate a human-readable current claim page and an immutable share snapshot
    for each reviewed revision. A snapshot preserves the statement, evidence
    set, limitations, applicable scope and review date that a person originally
    shared; it never silently changes into a later conclusion.
  - On every historical snapshot, state whether the assessment is still
    supported, updated, superseded, corrected or now needs a current check, and
    link prominently to the latest reviewed answer with a concise explanation
    of what changed.
  - Distinguish observation/event time, claim-effective time, Wayproof review
    and publication time, and the viewer's current time. Prefer language such
    as "evidence reviewed through" over an unqualified claim of current truth.
  - Generate concise text that can stand alone in a comment plus accessible
    visual evidence cards and native share/copy actions. Evaluate the claim and
    its scope, not the person whose statement prompted the correction.
  - Append an allowlisted, non-unique campaign marker to links created by
    Wayproof's share/copy controls so aggregate analytics can distinguish an
    evidence-card visit from ordinary navigation. Use only coarse values such
    as share mechanism, card kind and current-versus-snapshot state; never add
    a sharer/recipient ID, session token, destination account, raw query, trip
    context or fingerprint. The destination path already identifies the public
    entity or claim and does not need to be duplicated into event properties.
  - On arrival, validate only the documented share parameters, emit one
    anonymous `shared_link_opened` event, then remove the campaign parameters
    from the visible URL where supported. Shared pages must work identically
    when a platform strips the parameters, JavaScript is unavailable or
    analytics is blocked. Canonical metadata, indexing and evidence identity
    always ignore campaign parameters.
  - Emit static Open Graph and other preview metadata in generated HTML, with
    content-addressed images and direct HTTPS URLs that remain useful in
    reduced in-app browsers. The answer, date, scope and source path must remain
    readable without JavaScript or the interactive map.
  - Keep the current claim URL self-canonical and indexed. Historical share
    snapshots remain resolvable but point search canonicalization to the current
    claim, stay out of the sitemap, and use `noindex` only when canonicalization
    cannot prevent stale operational answers from competing in search.
  - Give current claim pages descriptive question-oriented titles, contextual
    internal links and source citations so public forum or trip-report links can
    consolidate discovery and relevance around the current reviewed answer.
  **Gate:** an old public post continues to show what Wayproof knew when it was
  shared, visibly discloses its age, and leads to the current evidence without
  allowing an obsolete preview to masquerade as a current operational fact.
- Use the same evidence pages as the durable destination for agent distribution:
  - Return absolute, user-openable Wayproof claim, route, source and evidence
    URLs from every relevant MCP result rather than sending users to a generic
    home page.
  - Host the existing read-only MCP capabilities at a stable public endpoint
    and package the shared server for supported ChatGPT/Codex and Claude
    discovery surfaces without duplicating planning logic per platform.
  - Keep public reads anonymous initially. Treat agent tool arguments as
    untrusted and retain no raw conversation or complete personal itinerary by
    default.
  - Measure only minimized private operational signals needed to understand
    demand: requested canonical objective, broad question category,
    answerability, blocking knowledge gaps and evidence-link follow-through.
    Keep analytics outside the public canonical corpus and do not convert a
    planning request into evidence.
  - Offer an explicit, separately confirmed path to submit an unanswered
    planning gap, dated textual field observation, correction source or public
    trip-report URL through the constrained proposal workflow. No agent surface
    gains direct canonical write or publication authority.
  **Gate:** a person can ask an agent a planning question, inspect the exact
  supporting Wayproof page, and optionally contribute a bounded correction or
  observation while Wayproof learns aggregate coverage demand without silently
  collecting the surrounding conversation.
- Redesign generated pages around the planning questions in the reviewed
  personas rather than exposing every canonical record as a peer:
  - Make browse pages establish context before inventory. Group results by
    region, managed area, campground, trail corridor or other reviewed parent;
    preserve search and filters, but do not lead with thousands of numbered
    campsites or route segments in one undifferentiated list.
  - Treat a campground as the primary camping browse result. Put its individual
    sites in a nested, searchable inventory and map on the campground page,
    with meaningful summaries and comparison fields. Keep group camps,
    backcountry camps, cabins and other planning-level facilities discoverable
    without making site `001` appear globally meaningful by itself.
  - Give each park, campground, route, trailhead, peak and other objective a
    plain-language orientation layer: what it is, why someone might choose it,
    where it is, how it is reached, the decisions or restrictions most likely
    to change a trip, and what still needs checking. Follow that with maps and
    structured planning facts, then progressively disclose claims, provenance,
    raw identifiers and complete evidence.
  - Present connected information in task order—objective, access, route,
    permits and restrictions, camping and facilities, current-condition checks,
    unresolved questions—while preserving the canonical graph underneath.
    Repeated facts should link to one reviewed claim rather than become
    page-specific prose forks.
  - Keep research queues contextual. Show a small number of consequential gaps
    on a landing or entity page, with counts and links to explore the remainder;
    never let hundreds of open questions or inventory records dominate the
    primary reading path.
  - Design index cards and detail summaries for scanning on a phone: descriptive
    names, parent location, type, the few decision-relevant attributes available,
    clear status language and sufficiently large controls. Unknown information
    remains visible without overwhelming the known answer.
  - Treat search as a planning entry point rather than an exact-name record
    filter. Support the vocabulary people actually bring—place or objective,
    activity, access need, restriction, facility, camp type and known site
    number—and show how a recognized term maps to canonical entities. Do not
    imply that a text match answers a permit, safety or current-condition
    question.
  - Rank and group results by planning usefulness. Prefer a named park,
    campground, trailhead, route or objective over an otherwise ambiguous
    numbered campsite or atomic segment; label every child with its parent and
    location; and separately surface matching rules, evidence-backed answers
    and unresolved questions when they are relevant to the query.
  - Provide useful query refinement and recovery: visible applied filters,
    result counts by category, spelling and alias handling, a clear reset,
    shareable search state where practical, and an informative no-result state
    that distinguishes an unrecognized term from a known coverage gap. A person
    should be able to propose the missing question without treating it as fact.
  - Preserve orientation while navigating the graph. Use stable global entry
    points for Search, Map, Parks, Trails, Camping and Peaks; contextual
    breadcrumbs and parent links; and explicit next actions such as “see sites,”
    “compare approaches,” “check restrictions,” or “view supporting evidence.”
    Back navigation must restore the prior query, filters, map extent and
    selection rather than restarting discovery.
  - Offer complementary entry modes without creating separate catalogs: text
    search for a known name or need, the geographic explorer for spatial
    discovery, curated browse pages for orientation, and agent/MCP planning for
    multi-constraint questions. All resolve to the same canonical pages and
    claims.
  - Validate representative journeys against every persona in `PRODUCT.md`,
    including selecting a camp area before a numbered campsite, finding a route
    to an objective, identifying a rule that crosses jurisdictions, recognizing
    a volatile condition, and sharing an evidence-backed correction. Include
    both known-name and need-first search journeys, no-result recovery, and
    returning from evidence or a map without losing the planning context.
  - Add privacy-minimized product measurement for those journeys. Use a free,
    cookie-free aggregate traffic/performance service and Search Console for
    discovery and indexing, then add only explicit anonymous product events
    when the persona pilot needs funnel evidence. Prefer a narrowly configured
    hosted free tier over operating analytics infrastructure prematurely.
  - Define the initial event vocabulary before adding a tracker: search
    submitted by broad query category, result counts and zero-result state,
    result type/rank opened, filter name applied, map feature type opened, next
    action selected, evidence/source opened, share or latest-update action, and
    contribution flow started. Do not send raw search text or contribution
    content as event properties.
  - Do not collect trip or reservation dates, entered campsite details, precise
    GPS or map-center history, party composition, personal constraints, agent
    conversations, complete itineraries, session replay, input autocapture,
    persistent cross-device identity or person profiles. Analytics remain
    private operational data outside the canonical corpus and never become
    evidence.
  - Set and document a short retention period for raw anonymous product events,
    initially targeting 90 days, followed only by aggregate counts needed to
    compare releases and prioritize coverage. Publish a plain-language
    analytics disclosure and provide any consent or opt-out controls required
    by the selected configuration and applicable jurisdictions.
  - Measure successful planning progression rather than generic engagement:
    entry or search, useful result, relevant canonical entity, and discovery of
    a decision-critical restriction, recheck or evidence path. Use aggregate
    no-result and abandonment patterns to improve coverage and navigation,
    never to reconstruct an individual's trip.
  - Establish a small shared visual system for generated pages: typography,
    spacing, hierarchy, cards, status treatments, controls and responsive
    behavior. Add a content style guide for plain-language orientation,
    decision-critical restrictions, dated or uncertain information, and
    progressively disclosed provenance so every entity template communicates
    trust consistently without hand-authored page forks.
  - Define interface-level accessibility acceptance criteria covering semantic
    structure, keyboard order, focus visibility, touch targets, contrast,
    reduced motion, screen-reader labels, map alternatives and comprehension of
    status without color alone. Test the representative persona journeys, not
    only isolated controls.
  - Set measured mobile performance budgets for generated HTML, search data,
    JavaScript, maps, geometry and imagery. Preserve useful static content when
    scripts, analytics or map tiles fail, and prevent complete inventories from
    blocking the first planning answer.
  - Run bounded qualitative reviews of the vertical slice with representative
    people in addition to automated browser tests. Record whether they can
    explain the relevant choice, restriction, uncertainty and next action in
    their own words; treat confusion as a product gap even when every expected
    element rendered.
  - Offer a low-friction “Did this answer your planning question?” response with
    optional broad reason codes. Keep free text outside analytics; if someone
    elects to submit a correction, source or field observation, hand it to the
    separately confirmed M3 proposal workflow rather than storing it as product
    telemetry.
  - Assign ownership for analytics configuration, access, retention, deletion
    and periodic review. Document dashboards and event definitions in the repo,
    audit them against the allowlist, and remove events that no longer support a
    roadmap decision. M4 may later operationalize monitoring at scale without
    expanding M2's permitted collection by default.
  - After the Taboose Pass coverage batch is published, run an explicit persona
    acceptance audit modeled on the cited public Instagram example. Starting
    from the person's likely question rather than a known record ID, verify that
    search, map and navigation lead to the applicable pet restriction and its
    jurisdictional boundary; that the rule, currentness, limitations and source
    are understandable; and that the experience would help someone avoid
    reaching the pass with a prohibited pet. Preserve any failure as a concrete
    search, content, relationship, evidence or coverage gap instead of writing a
    favorable narrative after the fact.
  **Gate:** a first-time person can answer “is this relevant to my trip, what
  choice do I make next, and what must I verify?” from a representative page
  before needing to understand Wayproof's schema or inspect raw evidence; the
  team can evaluate that journey without retaining the person's query, trip or
  identity.
- Add generated interactive map views over the canonical read service for
  campsites, campgrounds, trailheads, facilities, peaks, and route GeoJSON.
  Selectable features should link to canonical detail pages and preserve the
  distinction between approximate points, official coordinates, reviewed
  reference geometry, and navigation-grade geometry. Use an
  OpenStreetMap-compatible basemap with the required attribution and licensing;
  do not create a parallel map catalog or infer route connections from spatial
  proximity. Choose the rendering library, production tile provider, satellite
  imagery policy, and hosting strategy only when implementation evidence
  requires those decisions.
- Expand those entity maps into a generated layered geographic explorer. It
  should expose authoritative park, wilderness, preserve, and other managed-land
  boundaries together with canonical routes, segments, peaks, trailheads,
  access points, campgrounds, campsites, parking, water, restrooms, and other
  facilities. Users can independently show or hide each layer; the explorer
  does not assign or display an internal coverage score.
- Make map features inspectable without losing spatial context: pointer hover
  may show a transient name and type, while click or tap opens a persistent
  card or mobile bottom sheet with canonical facts and a link to the generated
  entity page. Selecting empty map space, a close control, or Escape dismisses
  the selection. Overlapping features must produce an explicit chooser rather
  than an arbitrary inferred association.
- Add objective-to-route discovery to the geographic explorer. Selecting a
  peak, pass, lake, viewpoint, campsite, or other planning objective should
  highlight the published routes and route segments that canonically reach it,
  dim unrelated geometry, and expose the supported starting trailheads and
  access alternatives. The selection card should distinguish complete routes,
  partial approaches, unresolved connections, and directionality; summarize
  relevant distance, permit, restriction, and facility information; and link
  to each route's generated detail page. This must be graph-backed: geographic
  proximity, line intersection, or a basemap label alone never qualifies a
  route as reaching the objective. The interaction must work with pointer,
  keyboard, and mobile tap/bottom-sheet controls and preserve the ordinary
  feature-selection and dismissal behavior above.
- Support a responsive full-viewport map mode, including safe-area-aware mobile
  controls, exit back to the embedded page, a separate reset-view action, and
  preservation of center, zoom, visible layers, and selected feature across the
  transition. Prefer a dependable CSS viewport mode on iOS while treating the
  browser Fullscreen API as an optional enhancement.
- Generate explorer layers and feature links through canonical read services,
  use authoritative or appropriately licensed boundary geometry, and apply
  zoom-dependent visibility or clustering where necessary. Geographic overlap
  remains presentation only and never establishes access, containment, route
  membership, or traversal.
- Consider a generated read index only if measured query or startup needs
  justify it; canonical Git-backed knowledge remains the source of truth.

**Exit criteria:** CLI, website, and MCP agree on fixture outputs because they
invoke the same domain behavior rather than reimplementing planning logic.

**Canonical parity gate:** the first outcome-level audit is complete in
`docs/canonical-planning-parity.md`, with executable checkpoints. Canonical mode
is not yet the default: Ohlone directionality, booking dependencies, parking,
and party-to-site capacity are now connected; decide the supported Sierra
corpus and add thin canonical CLI adapters for retained inspection/discovery
behavior first.

## M3 — Constrained contribution workflow

**Status: started.** An identified-actor, additive-only proposal service can
derive a DRAFT ChangeSet, validate it, and explain failures. It cannot prepare,
approve, promote, or publish canonical knowledge.

**Outcome:** community and agent-assisted evidence becomes reviewable proposals
without granting direct canonical write access.

- Ingest URLs, issues, artifacts, field reports, GPX, and supported structured
  sources into candidate observations/evidence.
- Design and separately review the media-provenance and repeatable-analysis
  extension required by accepted [ADR 0004](docs/adr/0004-repeatable-media-analysis.md)
  before changing Schema v0. Keep original source material, attributed author
  statements, and Wayproof analysis distinct. Support attachment identity and
  order, explicit comment-to-media mappings, qualified dates and locations,
  and multiple analysis runs over identified media versions, subject to
  redaction/deletion policy. Findings must enter typed Evidence through an
  attributed Observation; Claims continue referencing Evidence IDs only.
  The [Step 4 schema and migration proposal](docs/proposals/media-provenance-v1/README.md)
  is **Accepted** (PR #196), with synthetic contracts/tests for exact version lineage,
  location provenance, separate public/private stores, and reviewed selection.
  Accepting it does not activate v1 or implement privacy controls.
  **Step 5a implemented:** public domain types, structural additive v1 draft
  validation through the ChangeSet service, and unsupported-schema rejection
  across canonical reads, exports and publication checks. V1 preparation and
  persistence stay disabled. [Implementation boundary](docs/media-contract-implementation.md).
  **Next:** [public-source, reference-only research](docs/public-source-research-plan.md),
  in these reviewable steps:

  1. **Draft-boundary enforcement implemented:** narrow public-source policy,
     reviewed-content binding, distinct excerpt/paraphrase/finding representations,
     withdrawal of owned research text/references, and dependent-support/output
     invalidation analysis. See [enforced scope and limits](docs/public-research-enforcement.md).
     Persisted removal and live consumer integration remain in the next gate.
  2. Complete v1 migration and HTML/JSON/MCP/read-service compatibility.
     The [staged migration implementation](docs/v1-migration-compatibility.md)
     provides deterministic rehearsal, workflow-verified review receipts, shared
     evidence projections and executed withdrawal/output regeneration for review.
     Production routing uses the same review, projection and removal contracts.
  3. **Reference-only activation implemented:** independently reviewed batches,
     continued v0 editing, shared production consumers and complete owned-output
     withdrawal. See [scope and acceptance criteria](docs/reference-only-activation.md).
     Event/capture, publication, retrieval and analysis times remain independent;
     locations preserve value, attribution, precision, sensitivity and uncertainty.
     Unknown values are never filled from other dates, proximity or a Claim subject.
  4. **Synthetic bounded-processing rehearsal implemented:** append-only identified
     attempts/runs, explicit failures, workflow-reviewed selection, and selective
     withdrawal through shared HTML/JSON/MCP outputs. See
     [scope and acceptance evidence](docs/synthetic-bounded-analysis.md).
     No live acquisition, processor plugins or external-model calls are enabled;
     the operational ledger is process-local. **Next:** separately review live
     activation, including execution, durable history/recovery and retention.
     Preserve the separate PR review gate for every canonical effect.
     Then create/test one evidence-ingestion skill with public-reference and textual
     field-observation modes, including an offline notes template. Personal photos
     and uploads require a later contributed-media scope decision.
  5. Defer private custody, accounts/uploads/consent workflows, private-media
     access controls, complex provider authorization, and retained raw-media/
     derivative cleanup until those inputs or artifacts are actually needed.
- The initial scope admits only publicly accessible sources, with official
  agency, park, campground, and institutional accounts preferred. Store safe
  links, bounded factual summaries, and distinct author statements/findings;
  no media copies or derivative files, profile harvesting, personal identities,
  EXIF extraction, or sensitive-location inference. No access-control bypass.
  Captions, OCR, imagery, and links are untrusted data, never instructions.
- No-retention does not mean no retained content: removal of links, statements,
  findings, and dependent support must work across owned consumer outputs before
  activation. Mark unavailable/materially changed posts without replacing the
  selected version silently. Preserve capture/publication time and location
  uncertainty, original attachment order, and immutable analysis history.
- Preserve the accepted Source → Observation → Evidence → Claim boundary and
  GitHub review. Reprocessing cannot publish, choose its own findings, resolve
  gaps, create relationships, or change plans. Rejected/deferred research stays
  batch-scoped; do not turn a skipped source into a global denylist.
  **Gate:** synthetic fixtures prove eligibility/content exclusions, inert
  malicious captions/OCR, source removal and consumer agreement, changed/missing
  inputs, unknown dates/locations, ambiguous mappings, partial video inspection,
  conflicting runs, reposts, and no canonical change without separate review.
  Private-custody/retained-media cases gate later expanded scope, not this launch.
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

## M5 — Offline Wayproof PWA

**Status: planned.** This milestone extends the generated website into an
installable, verifiably offline consumer of the same canonical read and
planning services. It does not create a second knowledge store or make browser
storage, volatile conditions, GPS accuracy, or navigation safety appear more
certain than they are.

**Outcome:** a person can install Wayproof, download the complete public
knowledge library, browse and search it without connectivity, build a bounded
trip plan locally, and later view foreground GPS position against downloaded
route geometry.

### PWA-1 — Installable application shell

- Add the web-app manifest, icons, standalone display, service worker, and
  offline fallback.
- Show installation and connectivity state without making connectivity a
  prerequisite for launching the downloaded application shell.

**Gate:** an installed Wayproof shell launches in airplane mode rather than
returning a browser network error.

### PWA-2 — Complete offline knowledge library

- Offer one explicit download for all public Wayproof pages, canonical read
  projections, claims, provenance, search data, and route GeoJSON.
- Generate a versioned, content-addressed offline manifest and show download
  size, progress, version, completion, and last-update time.
- Exclude external webpages, large source artifacts, photographs, satellite
  imagery, and third-party map tiles from the initial whole-library download.

**Gate:** after one verified download, every Wayproof page type, public claim,
source reference, search result, and included route geometry remains available
in airplane mode.

### PWA-3 — Updates, integrity, and recovery

- Update only changed assets, remove obsolete assets, and safely recover from
  interrupted downloads.
- Request persistent browser storage where supported, but do not equate PWA
  installation or a persistence request with guaranteed retention.
- Detect missing or reclaimed content and provide explicit `ready`,
  `downloading`, `update available`, `incomplete`, and `repair required`
  states plus update, repair, and removal controls.

**Gate:** Wayproof never reports offline readiness without verifying the
required manifest, and can repair an intentionally interrupted or damaged
offline library.

### PWA-4 — Offline structured trip planning

- Store trips and their dates, party, objectives, activities, equipment,
  stages, and limits locally on the device.
- Run route traversal, applicability, requirements, fulfillment coverage,
  conflicts, answerability, candidate-itinerary construction, and recheck-list
  generation against downloaded knowledge.
- Keep the deterministic planning core independent of MCP, the PWA interface,
  and any language model so every consumer applies the same domain semantics.
- Do not claim to perform a current recheck while offline.

**Gate:** the same bounded trip produces materially equivalent planning,
readiness, gap, and recheck results through the online service and the offline
planning core.

### PWA-5 — Offline route maps

- Render downloaded route and segment GeoJSON together with trailheads,
  campsites, water, toilets, parking, junctions, peaks, and other
  route-connected facilities.
- Reuse the online geographic explorer's layer controls, feature selection,
  entity links, full-viewport mode, reset behavior, and preserved map state for
  downloaded boundaries, routes, peaks, access points, camping, and facilities.
- Link selectable features to canonical records and preserve geometry source,
  review state, and fitness-for-use distinctions.
- Remain usable without a basemap. Evaluate separately licensed regional
  basemap packages rather than bulk-caching public OpenStreetMap tile servers.

**Gate:** a downloaded route and its evidenced planning features are
inspectable in airplane mode without inferring connections from proximity.

### PWA-6 — Foreground GPS positioning

- With explicit permission, show device position and accuracy against
  downloaded geometry and calculate nearest segment, distance off-route,
  along-route progress, and nearby facilities locally.
- Keep live location on the device and display stale-position, poor-accuracy,
  and off-route states explicitly.
- Initially exclude background track recording, turn-by-turn navigation,
  automatic rerouting, and emergency-navigation guarantees.

**Gate:** field tests demonstrate understandable foreground positioning and
uncertainty while the phone is offline.

### PWA-7 — Field validation

- Exercise installation, airplane-mode use, interrupted updates, storage
  reclamation, repair, battery consumption, GPS behavior, and map performance
  on supported iPhone and Android devices.
- Complete representative no-service trips and record failures or ambiguity as
  product gaps rather than silently weakening readiness guarantees.

**Exit criteria:** Wayproof can verify that its complete public planning
library is available offline, disclose when it is incomplete or outdated, run
the shared structured planner locally, and show foreground device position
against downloaded route geometry without transmitting that position.

## Later horizon — Native iOS application and local agent

**Status: considered, not committed.** A native iOS client may follow the PWA
only after the shared offline planning core and field contracts are proven.

- Reuse the canonical read projections, evidence semantics, geometry
  identifiers, and deterministic planning core rather than creating a native
  planning implementation with different answers.
- Use native storage, maps, background behavior, and device integration where
  they provide measured value beyond the PWA.
- Consider an Apple-supported on-device language model on compatible devices as
  a conversational layer that calls local Wayproof planning tools.
- Keep prompts, plans, and location local by default; do not allow the model to
  directly author or promote canonical knowledge.
- Treat background tracking, native navigation, notifications, and any health
  or emergency integration as separate safety and privacy decisions.

The intended sequence is:

```text
installable PWA
  -> complete and repairable offline library
  -> offline structured planning
  -> offline route maps
  -> foreground GPS
  -> field validation
  -> later native iOS client
  -> later fully local conversational agent
```

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
