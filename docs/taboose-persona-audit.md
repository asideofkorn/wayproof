# Taboose first-time traveler acceptance audit

Audit date: October 6, 2026. Persona: a first-time traveler planning Taboose
Pass with a dog and a low-clearance vehicle. Acceptance comes from PRODUCT.md's
cross-jurisdiction adventurer and ROADMAP.md's explicit Taboose website audit.
Baseline implementation: `e8353a07`; observations began on the live website.

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
The PR remains unmerged; production retains baseline behavior until reviewed.
