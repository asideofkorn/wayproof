# Emigrant Wilderness coverage ledger

## Inventory before batch 1

Audited `origin/main` at `fabeb109` on 2026-10-05, before preparing any records.
There was no canonical Emigrant identity, access graph, source, claim, rule,
requirement, recheck or ChangeSet. The two canonical occurrences of “Emigrant”
were the unrelated Nobles Emigrant Trail at Cinder Cone. Existing Kennedy Grove
and neighboring Hoover/Yosemite identities are distinct and remain untouched.
The GitHub PR search found no prior Emigrant coverage PR (only Cinder Cone #136).

Relevant legacy material was recovered before researching:

| Material | Disposition |
| --- | --- |
| `data/trailheads.csv`, Gianelli Cabin | REVERIFY identity/access; RECONSTRUCT aliases and evidence. Approximate, unverified coordinates are not promoted. |
| `data/permits.csv`, `stanislaus_free` | REVERIFY free/no-quota and acquisition; RECONSTRUCT atomic claims and executable requirement. Composite legacy text is not canonical authority. |
| `data/permit_source_log.csv`, July 23 verification | Provenance context for prior user-pasted USFS text, confirmed by direct retrieval; do not reuse retrieval dates as effective dates. |
| `data/regulations.csv`, Stanislaus fire/group rows | REVERIFY against current signed order and preserve conflicting page wording. |
| `data/collections/sps.csv`, Black Hawk; GNIS peak/pass rows | Deferred to source-backed objectives and route batches; no inferred access or bulk migration. |
| Git commits `623d2270`, `fc2332af` | Earlier permit/entry context located; fresh primary sources control this candidate. |

## Reviewable batch sequence

1. **Foundation (this PR):** wilderness identity, ten explicitly named access
   points, historical parking descriptions, overnight issuance/free/no-quota
   guidance, principal camping/stock/fire/food rules, source conflicts and
   scoped rechecks. Three executable requirements cover overnight permits,
   group limits and food storage. Other restrictions remain sourced claims;
   Wayproof does not automatically assess elevation, lake buffers, stock counts,
   special-order exemptions or permitted equipment from this foundation.
2. **Western approaches and lake routes:** reconcile the 2012 mileage table,
   2021 schematic, overview map and detail map; model Crabtree, Gianelli and
   Bell Meadow corridors with explicit junctions, alternatives and lake spurs.
   Test both directions and preserve approximate/conflicting mileage.
3. **Northern approaches and passes:** Kennedy Meadows, Sonora Pass, Coyote,
   Waterhouse and Eagle Meadow; lake/pass objectives, stock limitations,
   separately supported route-connected facilities and current road orders.
4. **Southern and cross-boundary approaches:** Bourland, Box Springs,
   Shingle Springs/Cherry and Leavitt-side entries; reuse Yosemite/Hoover
   entities, review entry-agency permits and quota/food/dog differences.
5. **Deep inventory and coverage audit:** individual approach campgrounds and
   reservation inventory, operators, sanitation/water evidence, authoritative
   boundary matching, lake camping maps and remaining discovered sources.

Each subsequent canonical PR starts from refreshed main after review and has
one ChangeSet. This task stops at the first PR, without merge. The foundation
is not route-complete, deep-inventory-complete or destination source-complete.

## Primary-source disposition ledger

Direct HTTPS retrieval succeeded on 2026-10-05. Search-engine text was older
than direct retrieval and was not used as current evidence. PDF text was read;
the signed order page 1, trailhead guide page 1 and mileage schematic were also
rendered and visually inspected. No source PDFs, map images, captures or
third-party text are redistributed. Observation timestamps are retrieval
context; unknown observation/event dates remain null. The signed order's
explicit effective interval is 2026-07-08 through 2029-06-30.

| Source/layer | Disposition and coverage limit |
| --- | --- |
| [Emigrant overview](https://www.fs.usda.gov/r05/stanislaus/wilderness/emigrant-wilderness) (updated September 15, 2026) | Ingested identity and approximate dimensions; linked source hierarchy inventoried below. |
| [Highway 108 access](https://www.fs.usda.gov/r05/stanislaus/recreation/emigrant-wilderness-highway-108-access) (September 16, 2026) | Ingested all ten named access points, fees and principal restrictions. Conflicting permit season, sanitation and camping wording preserved. Site Open banner not promoted to route clearance. |
| [Wilderness permits](https://www.fs.usda.gov/r05/stanislaus/permits/wilderness-permits) (July 12, 2026) | Ingested acquisition, no-quota scope, other-agency entry and no-self-issue exception. Conflicting order year, stock setbacks and stove scope preserved. Yosemite quota details deferred with cross-boundary gap. |
| [Order alert](https://www.fs.usda.gov/r05/stanislaus/alerts/renewal-emigrant-wilderness-use-rules) and [signed STF-16-2026-08](https://www.fs.usda.gov/sites/nfs/files/r05/stanislaus/publication/alerts/STF-16-2026-08%20Emigrant%20Wilderness%20Restrictions%20%28Order%29%20.pdf) | Alert checked against signed PDF; signed page 1 supplies claims, all numbered restrictions and exemptions. Geometry exhibit deferred with boundary gap. |
| [Regulations ROG, June 2024](https://www.fs.usda.gov/media/237204) | Ingested food storage, dispersed-camping character, equipment/mobility exception, pack-out and fire-permit requirements. Sanitation, one-night and stove differences preserved against current pages/order. Other etiquette deferred. Water-treatment advice excluded from this planning batch; not independently reviewed medical guidance. |
| [Trailheads ROG 16-26, April 2012](https://www.fs.usda.gov/media/226285) | Ingested aliases and nine parking descriptions as historical, with availability unknown. Kennedy parking not supplied by this guide; facilities, driving directions and road-code reconciliation deferred with facility/access gaps. |
| [Mileage table ROG 16-27, June 2012](https://www.fs.usda.gov/media/139022) | Inspected, deferred with route-topology gap. Gianelli-Powell is 2.3 miles in table versus 2.0 on schematic. Box Springs elevation also differs from trailhead guide (7,440 vs 7,600 ft); neither elevation promoted. |
| [Mileage schematic, 2021 filename](https://www.fs.usda.gov/media/138934) | Visually inspected, deferred with topology gap. Source calls distances estimates and explicitly disclaims scale/navigation. Bourland connector labeled 0.0 is not proof of a zero-cost traversable edge. |
| [Overview geospatial PDF](https://www.fs.usda.gov/media/138049), [trail-map GIF](https://www.fs.usda.gov/media/226287) | Retrieved, full map reconciliation deferred with boundary/topology gaps. No boundaries traced or connectivity inferred from proximity. |
| Minimum camping maps: [Bear](https://www.fs.usda.gov/media/138548), [Camp](https://www.fs.usda.gov/media/138625), [Chewing Gum](https://www.fs.usda.gov/media/138610), [Grouse](https://www.fs.usda.gov/media/138666) | Retrieved, detailed visual review and lake inventory deferred with facility gap. No individual campsite/route connections asserted. |
| [Current conditions](https://www.fs.usda.gov/r05/stanislaus/conditions) | Ingested checking sources for fire/smoke/snow/avalanche topics; no live environmental status asserted. Linked AirNow, avalanche and snow-map values deferred with current-conditions gap. |
| [Alerts](https://www.fs.usda.gov/r05/stanislaus/alerts) | Ingested recheck pointer. Listed moderate/high fire orders, occupancy order, 4N12/8N13 seasonal closures, 1N98 Cherry Dam closure and Cherry Lake camping restrictions need individual orders/maps matched to selected approaches. Deferred with current-condition gap, not deemed irrelevant or open. Woodcut PAL, Mokelumne and Rainbow Pool topics excluded from this bounded Emigrant foundation. |
| [Maps and guides](https://www.fs.usda.gov/r05/stanislaus/maps-guides) | Inspected hierarchy; MVUM, fire-restrictions map, Highway 108 facility guide, Brightman complex, horse camping and dispersed-camping guides deferred to access/facility depth. Winter ski/OSV layers deferred as a distinct mode; no summer/winter equivalence. |
| [Kennedy Meadows Resort](https://www.kennedymeadows.com/), [Aspen Meadow Pack Station](http://www.aspenmeadowpackstation.com/) | Official referrals discovered; operator inventory, booking and prices deferred with facility gap. |
| [USGS map product](https://store.usgs.gov/product/116312), 3FIA/Avenza map sales | Deferred; no purchased map or licensed artifact imported. |
| [Hoover permits](https://www.fs.usda.gov/r04/humboldt-toiyabe/permits/hoover-wilderness-permits), [Yosemite permits](https://www.nps.gov/yose/planyourvisit/wildpermits.htm), [Yosemite rules](https://www.nps.gov/yose/planyourvisit/wildregs.htm) | Referrals discovered, deferred with cross-boundary gap; reuse canonical neighboring entities in later route-specific batches. No outside-agency fees or quotas generalized. |
| [CAL FIRE](https://permit.preventwildfiresca.org/), [bear-container guidance](https://www.fs.usda.gov/visit/know-before-you-go/bears/bear-resistant-food-canister), Be Bear Aware, Leave No Trace, linked safety PDF and NWS weather | Referrals discovered; USFS requirement captured, detailed referred-authority content deferred to operational/source-depth audit. No permit issued, product endorsement or forecast claim. |

Other source discrepancies are deferred explicitly: the access page and 2024
ROG give different Leavitt Peak elevations (11,570 and 11,750 feet); neither is
promoted. The 2012 guide's Waterhouse road number and newer guide/map references
need reconciliation before publishing driving directions. These are research
questions, not facts to repair by guessing.

## Candidate production and acceptance

`scripts/ingest_emigrant_foundation.py` constructs typed records, proposes one
DRAFT ChangeSet, validates it, prepares a detached candidate, and invokes the
canonical serializer. To regenerate before merge, use `--base` pointing to a
clean main checkout that does not contain this batch; write to the working
candidate with `--output`. The builder performs no remote acquisition and
cannot approve or publish. Corrections belong to this same ChangeSet.

Tests exercise ordinary named hiking/overnight requests in summer and winter,
day-use exclusion, effective-date boundaries, exact persisted/runtime
requirement IDs, evidence lineage, all six conflict rechecks, and access-only
scope isolation. Generated directory, detail HTML/JSON and evidence pages must
show the destination, qualifiers, conflicts and gaps. No destination-specific
website or schema logic is added. Run the site CI group, exhaustive group check,
full Python 3.14 suite, and committed canonical diff verifier before PR review.
