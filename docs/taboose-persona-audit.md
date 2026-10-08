# Taboose first-time traveler acceptance audit

Baseline audit date: October 6, 2026. Production acceptance date: October 7,
2026. Persona: a first-time traveler planning Taboose Pass with a dog and a
low-clearance vehicle. Acceptance comes from PRODUCT.md's cross-jurisdiction
adventurer and ROADMAP.md's explicit Taboose website audit. Baseline
implementation: `e8353a07`; observations began on the live website.

## Baseline journey and failure classification

Started at the homepage, selected **Search Wayproof**, and submitted **Taboose
Pass dog**. No record IDs, detail URLs, or implementation knowledge were used
to start the journey. Recovered with **Taboose**, selected **Taboose Pass**,
followed **Taboose Pass Trail**, **Taboose Pass Trailhead**, then **US 395 to
Taboose Pass Trailhead**. Opened **Map** through global navigation. Returned to
Search and selected **Taboose Pass western continuation in Kings Canyon**.

| Failure | Classification | Observed evidence |
| --- | --- | --- |
| Adding “dog” hides the destination | Search | “Taboose Pass dog” returned 0 results; “Taboose” returned 13. |
| Pass page omits the west-side restriction | Relationship projection | Two elevation/location facts, an adjacent-continuation link, and “No explicit knowledge gap” gave no pet warning. |
| East-side allowance dominates the route reading path | Content hierarchy | “Pet policy” allows forest pets; jurisdiction transition appears far below in the western-scope gap evidence. No visible west-side prohibition accompanies the allowance. |
| Prohibition requires discovering a separate zone page | Content hierarchy | Western continuation has “Pets allowed: No,” amid 17 facts; transition is in “More planning facts.” |
| Road-route reports zero planning facts | Relationship projection | Road evidence is already explicitly scoped to the road route, but appears on the trailhead only inside a facility gap's evidence. |
| Map requires visual hunting and offers no decision context | Map presentation | No name lookup; layer says “Peaks”; selection offers identity/evidence status, not restrictions. The pass **does exist** in the geometry feed, alongside route and trailhead. It is not missing geometry. |
| No established low-clearance fallback, extra approach distance, or compliant dog alternative | Missing data | Access geometry/clearance and onward-topology gaps remain; no supported fallback or alternative is available. A county campground is not a substitute trailhead by proximity. |

## Bounded repair

- Tokenized name/need search includes existing decision predicates, scoped
  claims, connected-place context, and explicit gaps. Dog/pet synonyms are
  generic. Named planning entities precede atomic inventory. A text match is
  explicitly not permission or clearance.
- A shared decision section precedes maps and ordinary facts. It presents
  separately labeled places, jurisdiction transition, pet prohibition,
  road uncertainty, original sources, retrieval dates, and recheck actions.
- Discovery follows explicit approach, entry, destination, traversed-place and
  adjacent-jurisdiction edges. Adjacency never creates a traversable segment,
  extends legal applicability, or resolves a trip. JSON preserves the supporting
  relationship path. Direct claims remain separate from connected warnings.
- Explicit spatial scopes supply road facts to the road-route and trailhead
  pages. Claim subjects, provenance, dates, gaps and source precision survive.
- Map lookup uses the published geometry inventory, has a text/detail-page
  path, labels peaks and passes, and shows scoped warning previews. It creates
  no road polyline, western continuation geometry, or exact boundary line.

## Limits and acceptance

The traveler should discover the west-side prohibition **before** committing to
the climb: do not continue into the prohibited area with a dog; confirm the
boundary and entire itinerary with the land manager. Road descriptions do not
establish present suitability for a low-clearance car. Confirm current access
before departure; fallback parking and added walking distance/elevation are
unresolved. No dog-compliant alternative or precise turnaround is invented.

The complete product persona remains **partial** because supported alternatives
and current vehicle-access evidence are missing. Improving discoverability is
not evidence that the trip is feasible. No canonical knowledge changes or
ChangeSet are required for these read/projection/rendering changes.

## Regression and validation

`tests/test_persona_journey.py` starts with the homepage search link, exercises
the shipped JavaScript matcher, selects visible names, and follows generated
links through pass, route, western continuation, trailhead and road. It checks
warning priority, sources, currentness, uncertainty, map previews, no-result
recovery and actual evidence-page targets. Synthetic non-Taboose consumer tests
guard against proximity inference and applying an adjacent prohibition to the
whole route. Existing Taboose rule/recheck tests preserve east/west separation.

Use the affected-output production renderer with the changed journey module,
then reuse its artifact through `WAYPROOF_PREBUILT_SITE`. Because shared read
services/rendering change, the normal selector must retain its full-suite/site
fallback. No canonical records change, so the diff-based canonical dependency
closure has no seeds; the journey tests explicitly verify the affected pages.
Browser verification also starts at local homepage search and follows names.
The repair shipped in [PR #215](https://github.com/asideofkorn/wayproof/pull/215)
at merge commit `2d4a2a246ccc54ce928d191373498517721fa778`.

## PR review follow-up: map loading and inventory budget

The review confirmed a map-presentation failure: search buttons were usable
before their handlers existed, and layer controls could address unloaded layers.
Map focus, layers, basemaps and expansion now start disabled in the generated
HTML and become enabled only after the map's layers and handlers are ready.
A visible, accessible loading status explains this. Search results keep working
place links while the map loads or fails; newly rendered focus buttons use the
same readiness state. Empty layers remain disabled.

The complete map inventory no longer appears as hidden initial HTML. A compact
canonical-derived search index is fetched only for a nonempty query, independently
of geometry loading. At most 20 matching rows render, with a count and refinement
prompt. The all-place search link remains available without JavaScript.

Measured on the review fixture (bytes, gzip from Python's default compressor):

| Asset | Before | After | Regression budget |
| --- | ---: | ---: | ---: |
| Map HTML | 644,076 / 47,580 gzip | 4,631 / 1,610 gzip | <12,000 / <4,000 gzip |
| Lazy search index | Included in HTML | 147,613 / 16,479 gzip | <350,000 / <50,000 gzip |
| Geometry | 10,235,879 / 1,117,372 gzip | Unchanged | No increase in this repair |

These are transfer/DOM budgets for this discovery path, not measured mobile
latency guarantees or a complete site performance budget. Geometry remains large,
but does not gate search results or their planning-page links.

The executable JavaScript regression delays module resolution, geometry retrieval
and the map load event separately. It tries unavailable controls, then verifies
selection focusing and layer/basemap changes after readiness. It also checks
results created after readiness, map/search failure fallbacks, a lazy single
index fetch and the 20-row cap. The existing persona/consumer assertions still
check restrictions, provenance and missing-data boundaries.

## Production acceptance — October 7, 2026

The deployed journey was repeated from the likely question rather than a known
record ID. The entry point was
[`/search/?q=Taboose%20Pass%20dog`](https://wayproof.dev/search/?q=Taboose%20Pass%20dog),
followed by the visible Taboose Pass result, its evidence links, and the same
query in the geographic explorer.

| Acceptance question | Live result | Assessment |
| --- | --- | --- |
| Can the traveler find a relevant place without knowing Wayproof's identifiers? | The query returned four bounded results: the pass, trail, western continuation, and approach route. | Pass. |
| Is the consequential restriction visible before committing to the climb? | The [Taboose Pass page](https://wayproof.dev/knowledge/place-taboose-pass/) leads with the prohibition on the western continuation and says not to continue there with a dog. | Pass. |
| Is the jurisdictional scope understandable? | The page distinguishes the east-side approach from the adjacent Kings Canyon continuation and describes the transition at the pass. | Pass, with the exact on-the-ground boundary still requiring confirmation. |
| Can the traveler inspect provenance and currentness? | The [claim page](https://wayproof.dev/evidence/claim/claim-taboose-west-pets/) identifies the NPS source, western scope, retrieval date, unknown observation time, and missing effective interval. | Pass. The interface exposes rather than fills temporal uncertainty. |
| Does the experience avoid inventing vehicle suitability or an alternative? | The pass page says current suitability, clearance, fallback parking, added walking, and a supported dog-compliant alternative are unknown. | Pass for honest answerability; coverage remains partial. |
| Does the map preserve the decision context? | [`/map/?q=Taboose%20Pass%20dog`](https://wayproof.dev/map/?q=Taboose%20Pass%20dog) returned the pass and trail, delayed controls until ready, and showed the pet warning and access uncertainty in the selected-pass summary. | Pass. |

This is an **internal production acceptance pass** for discovery, scope,
provenance, uncertainty, and safe non-inference. It is not evidence that the
complete trip is feasible, not a current road-condition check, and not an
external usability study. The page remains long and evidence-heavy, and search
still exposes some technical entity labels. Those are inputs to the broader M2
persona-centered page, browse, and search redesign rather than blockers for
this bounded journey.
