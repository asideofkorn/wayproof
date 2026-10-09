# Campground-first browsing

The approved M2 design direction puts the campground before its campsite
inventory. This slice introduces shared presentation and navigation; it does not
change outdoor knowledge, reservations, trip plans, map interaction, or sharing.

## Shared behavior

- Search, Explore and Map are the primary navigation. Explore links the existing
  automatically populated directories. How it works and published history remain
  in the footer.
- Camping browse lists campgrounds and standalone camps. An evidenced child site
  lives under every explicit parent, rather than becoming a peer directory card.
- A broad campground search groups its sites beneath the campground. A numbered
  query, distinctive site name or explicit site-type filter can reach the child.
  Other matching retains the existing text matcher; this is not natural-language
  trip evaluation.
- Campgrounds lead with orientation, dated opening information, current checks
  and the choice to inspect sites. Relevant access relationships remain linked.
- A separate inventory renders at most 20 summaries per static page. Filtering
  loads compact summaries only when used; it never fetches full site profiles.
- Conflicting source fields stay prominent on site pages. Comparing sources does
  not select a controlling limit or confirm that equipment fits. Complete facts
  and history remain on `/knowledge/<id>/facts/`; existing entity JSON is unchanged.
- Source-access dates remain visible. Disclosures and evidence links retain
  temporal scope, source locators and history. A source retrieval date is not an
  observation date or a current-condition check.

## Projection boundary

`CanonicalReadService.camping_hierarchy` accepts explicit, evidenced `part_of`,
`contained_by` and inverse `contains` relationships between allowed campsite and
campground/area kinds. Multiple parents and unparented sites remain representable.
Names, identifiers and geographic proximity do not establish containment.

`camping_claims` omits another individual campsite's claims from a place overview.
The existing `scoped_claims_for` API and full entity/evidence output retain their
semantics. Rules scoped to the campground stay in its overview. The renderer
formats supported predicates and fields; other values remain source-linked and
visible rather than guessed or silently discarded.

Site conflicts compare named fields for the same quantity within a source
statement. Vehicle count/length and checkout discrepancies link the complete
claim. Different equipment categories are not, by themselves, contradictory.

## Context, fallback and accessibility

Query, type and page live in URLs. An explicit return link accepts only local
planning paths, carries the previous query/filter and restores the selected
campsite anchor and focus. Browser history restores filters on `pageshow` as well
as ordinary navigation. Direct links do not invent a previous page. Context is
bounded to avoid indefinitely growing URLs; it uses no analytics or browser
storage. External source links receive no Wayproof return parameters.

Without JavaScript, directory links, campground facts, restrictions, sources,
parent links, all-details pages and paginated site lists remain available.
Search and local inventory filtering require JavaScript and identify their
browse fallback. No map or tile request is required for the camping flow.

The shared addition uses native disclosures, semantic headings and main
landmarks, labelled form controls, visible keyboard focus, text-labelled
uncertainty, wrapping navigation and 44px inventory actions. It introduces no
animation. Formal assistive-technology or participant usability acceptance is
not established by the author browser checks.

## Regression journeys and limits

East Fork: discover campground → review opening check → browse 133 sites → find
126 → inspect vehicle/checkout disagreement → source evidence → return with the
same filter and selected site. Taboose: search by pass/pet terms → scoped western
prohibition → evidence; no route-wide pet permission or alternative is implied.
Del Valle and other campgrounds use the same projection, with synthetic tests
covering missing evidence, multiple parents and proximity-only links.

Map overlays/full-screen behavior, amenity-map placement, share cards, general
question understanding and complete trip planning remain separate roadmap work.
The evidence-detail layout and unsupported structured predicates still need
further language/hierarchy work. No claim of live availability or completeness
is added by this slice.
