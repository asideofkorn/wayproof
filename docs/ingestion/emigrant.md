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

1. **Foundation (#203, merged):** wilderness identity, ten explicitly named access
   points, historical parking descriptions, overnight issuance/free/no-quota
   guidance, principal camping/stock/fire/food rules, source conflicts and
   scoped rechecks. Three executable requirements cover overnight permits,
   group limits and food storage. Other restrictions remain sourced claims;
   Wayproof does not automatically assess elevation, lake buffers, stock counts,
   special-order exemptions or permitted equipment from this foundation.
2. **Western approaches, geometry and facilities:** Crabtree–Camp/Bear topology
   (#204, merged) and its display geometry (#205, merged) established the model.
   The combined western batch (#206, merged) adds Gianelli/Powell/Chewing Gum,
   Bell Meadow/Grouse, Crabtree connections and the deeper Gem approach, plus
   trailhead facility/camping evidence in one PR.
3. **Northern approaches and facilities:** Kennedy Meadows, Sonora Pass, Coyote,
   Waterhouse and Eagle Meadow; associated lake/pass objectives, geometry,
   stock guidance, facilities, historical road orders and current-access rechecks.
4. **Southern and cross-boundary approaches:** Bourland, Box Springs,
   Shingle Springs/Cherry and Leavitt-side entries; reuse Yosemite/Hoover
   entities and review entry-agency permits and quota/food/dog differences.
5. **Completion and source audit:** authoritative wilderness boundary matching,
   remaining facility/booking/operator inventory, route gaps and source
   dispositions. Split a further PR only if material conflicts or cross-boundary
   rules need separate review. This sequence is a work plan, not a promise that
   every existing trail or campsite can be established from available evidence.

Each subsequent canonical PR starts from refreshed main after review and has
one ChangeSet. Foundation PR #203 was merged with explicit user authorization;
Crabtree lake approach PR #204 was also reviewed and merged with authorization.
Subsequent batches are prepared for review without assuming merge authorization. The foundation is not route-complete,
deep-inventory-complete or destination source-complete.

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


## Batch 2a: bounded Crabtree lake approaches

Inventory starts at main `b48af75f` (#203). Existing Emigrant coverage has one
wilderness, ten access points, three executable requirements and scoped
foundation rechecks, but no route, segment or lake resource. This batch reuses
Crabtree, wilderness identity, alert source and requirements. It introduces two
descriptive approaches, two lake resources, five descriptive mapped nodes and
five physical segments. The first three segments are shared. Nodes describe
map features, not official junction names or surveyed coordinates.

The bounded graph is Crabtree → Lake Valley Trail junction → Pine Valley Trail
junction → Camp Lake western approach → Bear Lake junction → Bear Lake trail
terminus. The Camp approach ends at its western access point; the Bear approach
continues along the south side of Camp Lake and branches north. Both graphs
traverse in reverse. Lake resources are connected explicitly to approach
segments and remain distinct from trail nodes. The branch routes toward Lake
Valley/Pine Valley and the continuation east of the Bear junction are deferred.

Only the Bear branch has atomic mileage (1.0, explicitly an estimate from the
schematic). The other four legs have unknown distances. Known-distance subtotals
are not complete trip lengths. No subtraction, scale measurement, summed
schematic labels, or inferred mileage reconciles the differing sources.
Named lake requests select Crabtree and their approach but retain `exit_unknown`;
this does not implement a complete return itinerary or campsite selection.

The historical ledger above describes the foundation. These updated
source dispositions apply to batch 2a:

| Source | Disposition in batch 2a |
| --- | --- |
| 2010 geospatial overview map, western panel | Ingested drawn connectivity and branch junctions. No boundary tracing, coordinates or scaled distance. Wider network deferred with retained topology gap. |
| June 2012 mileage table, Crabtree column | Conflicting and preserved: Camp 2.6 and Bear 3.9 miles; Lake Valley 0.1 and Pine Valley 1.4 are cumulative milepoints, not fabricated atomic legs. Other columns deferred. |
| 2021-filename mileage diagram, western panel | Ingested Bear branch 1.0 as estimate. Conflicting and preserved: Crabtree–south junction label 1.3 versus table Pine Valley 1.4. Intermediate Lake Valley branch is omitted. The link toward Camp has no printed mileage. Navigation/scale disclaimer retained. |
| Undated trail-distance GIF, western panel | Conflicting and preserved: Crabtree–south junction 1.3 and a separate 1.3 eastward link toward Camp; Camp/Bear branch 1.0. It omits/combines detail-map endpoints. These are source reports, not atomic assignments or a synthesized total. |
| [Favorite Hiking Trails, ROG 16-41, November 2018](https://www.fs.usda.gov/sites/nfs/files/r05/stanislaus/publication/Favorite%20Hiking%20Trails.pdf), page 2 | Ingested Crabtree entry and Camp/Bear progression. Conflicting and preserved: Camp 3 and Bear 4 one-way miles versus 2012 table. One-night language already represented by the foundation conflict; unrelated hikes and generalized water-treatment advice excluded from this batch. |
| Camp and Bear minimum camping maps, page 1, 2021 filenames | Visually reviewed and ingested system-trail connections, 100-foot minimum versus 200-foot LNT recommendation, Camp trail/lake exclusion, Bear cliff-edge restriction and horizontal measurement. Reference-only maps do not establish an available or legal individual campsite. |
| Chewing Gum and Grouse minimum camping maps | Visually reviewed, deferred with facility/topology gaps to the next western-route or inventory batch. No route or campsite access asserted here. |
| April 2012 trailhead guide | Already represented for Crabtree identity/parking. Crabtree restrooms and the historical one-night camping limit at trailheads are explicitly deferred to facility/deeper-access work, as requested in foundation review. Reconcile current orders and facility status there. |
| Foundation signed order, permits, regulations, alerts and conditions | Already represented. Lake intents inherit wilderness scope and executable permit requirements; use the foundation recheck alongside the new lake-route recheck for one-night, sanitation and other conflicts. Current trail/road/water/closure status remains unknown. |
| Gianelli and Bell Meadow map junctions, remaining western lakes | Deferred with narrowed route-topology gap; coarser schematics and overview connections need further reconciliation. No claim of destination route completeness. |

`scripts/ingest_emigrant_crabtree_lakes.py` produces one validated ChangeSet
from a clean pre-batch main using `--base`, with the serializer writing the
candidate. It replaces only the existing topology-gap explanation; historical
foundation observations and ChangeSet remain intact. A separate scoped recheck
manifest exposes lake mileage conflicts, endpoint alignment, camping placement
and approach unknowns without applying them to a Crabtree-only request.

Acceptance covers both graph directions, shared segments, resource access,
unknown/estimated atomic distance, differing printed totals and editions,
conservative named intents, rejection of unsupported Gianelli entry, wilderness
requirement joins, scoped rechecks and generated route/lake/evidence HTML/JSON.
The foundation regression still requires a wilderness-only request to have no
inferred route; its no-segment assertion now applies to foundation ChangeSet
entities so later explicitly evidenced graphs can coexist.


## Batch 2b: reviewed geographic display for Crabtree lake approaches

Inventory at main `b2c68ed2` (#204): two lake approaches, five shared/branching
segments, five descriptive nodes and two lake resources exist, but no Emigrant
coordinates or route GeoJSON. Review explicitly requested later geographic
coverage. This batch adds display geometry to those five existing segments;
it adds no entities, relationships, normative rules or route lengths. The
foundation and batch 2a claims, observations and ChangeSets remain unchanged.

### Source disposition and review

- **Ingested:** USDA Forest Service National Forest System Trails public layer,
  reviewed 2026-10-06 UTC (October 5 local). Named `20E16 CRABTREE` features
  9428086 and 9430618 and `19E09 BEAR LAKE` feature 9430557 match the already
  reviewed overview and lake-detail maps. Their original global IDs, length
  fields and source-geometry hashes remain in the bounded snapshot.
- **Already represented / corroborating:** 2010 Emigrant overview and Camp/Bear
  minimum camping maps. These establish the branch identities and approaches;
  proximity in the new dataset creates no relationship.
- **Reviewed but not imported:** `19E21 LAKE VALLEY` feature 9430389 and `19E10
  PINE VALLEY` feature 9430585 anchor the existing named junctions. Pine Valley
  shares an exact vertex. The normalized Lake Valley endpoint differs from the
  reviewed Crabtree vertex by about 0.08 m; no geometry is snapped or changed
  and the branch is not imported.
- **Deferred with explicit gap:** other Emigrant trail features, wilderness
  boundary, shoreline polygons and facility geometry. This is a bounded route
  display batch, not geographic completeness for Emigrant Wilderness.
- **Already represented / unchanged:** competing table/guide mileages, estimated
  Bear branch mileage, permit and camping restrictions, current-condition
  rechecks. Original dataset `segment_length` and `gis_miles` values describe
  whole source features and are not promoted into atomic traversal distance.

The source service was queried in EPSG:4326 for the western Emigrant envelope
(-119.91, 38.13, -119.70, 38.27), returning 45 features. Three supply display
geometry; the rest are excluded from the snapshot. A plotted review of named
lines and junctions was compared against the official overview and lake maps.
The committed snapshot contains only these contiguous source-vertex slices:

| Existing segment | Source object ID | Inclusive vertex indices (canonical direction) |
| --- | --- | --- |
| Crabtree–Lake Valley junction | 9428086 | 182 → 172 |
| Lake Valley–Pine Valley junction | 9428086 | 172 → 67 |
| Pine Valley–Camp western approach | 9428086 | 67 → 0 |
| Camp western approach–Bear junction | 9430618 | 836 → 806 |
| Bear branch | 9430557 | 0 → 164 |

All imported joins share exact source vertices. Camp's western display endpoint
is the shared Crabtree source-feature break, reviewed against the lake map;
it is a descriptive approach position, not a lake centroid, surveyed named
junction or campsite. Coordinate digits do not establish accuracy. The source
service does not establish current trail status. The new scoped geometry
recheck makes these limits visible to route/lake requests without applying
them to a trailhead-only or wilderness-only request.

`scripts/ingest_emigrant_geometry.py` prepares one validated ChangeSet through
the write service. With `--reviewed-input`, it creates the bounded snapshot
from the inspected service response after checking source identifiers, vertex
counts and reviewed joins. Without that option it reuses the committed
snapshot, enabling offline canonical regeneration against pre-batch main.
The snapshot is hashed and linked from five additive display claims; canonical
JSON remains serializer-owned. No geometry projection or website code changes.

Acceptance verifies both drawable routes in `/map/features.geojson`, route
GeoJSON and detail HTML/JSON; identical shared geometry; exact continuity;
source identifiers, vertex ranges and hash; fail-closed hash validation;
unknown/estimated mileage preservation; named-intent exit limits; and scoped
geometry rechecks. Existing bidirectional traversal and permit tests remain.
Crabtree restrooms, the historical trailhead one-night camping limit, Gianelli
and Bell Meadow route depth, and other planned coverage remain in later batches.


## Combined western batch: six approaches and access depth

### Starting inventory and delivered scope

Started from latest `origin/main` `6304e247` (merged #205), with no local changes.
Existing coverage: one wilderness, ten trailheads, two lake resources, two
Crabtree approaches, five physical segments with reviewed geometry, three
executable requirements, and foundation/route/geometry rechecks. Durable
identities, sources, requirements and the five existing segments are reused.

This batch adds **six approach routes, four lakes, twelve descriptive trail
nodes, fourteen physical segments and one collective restroom facility**.
Crabtree restrooms have no established unit count. Historical parking claims
already exist and are not duplicated into an invented parking-site inventory.
The six approaches have connected, bidirectional topology and drawable geometry:

| Approach | Physical legs | Reported mileage retained independently |
| --- | ---: | --- |
| Gianelli to Powell Lake | 3 | 2012: 2.3; 2018: 2; 2021 schematic: estimated 2.0; undated GIF: 1.8 |
| Gianelli to Chewing Gum Lake | 4 | 2012: 4.1 one way; operator: 4.1, convention unspecified |
| Crabtree to Chewing Gum Lake | 3 | 2012: 4.4 one way; operator calls this approach poorly marked, date/current condition unknown |
| Bell Meadow to Grouse Lake | 3 | 2012: 4.8 one way |
| Crabtree to Grouse Lake | 5 | Operator: 4 miles, convention unspecified |
| Crabtree to Gem Lake | 7 | 2012: 9.5 one way; operator: 10, convention unspecified |

All **new atomic distances remain unknown**. Cumulative destination totals,
coarse schematic labels and original GIS lengths are not subtracted, measured
or summed to manufacture missing leg distances. The earlier Bear branch keeps
its separate estimated 1.0-mile fact and is not part of the Gem route.

The two Gianelli routes share their first two physical segments. The two Grouse
routes share their final two. Crabtree–Chewing Gum reuses the first existing
Crabtree leg; Crabtree–Grouse reuses the first two; Crabtree–Gem reuses the first
four Camp/Bear mainline legs, then continues east through the Piute corridor
and turns onto 20E98. Named Chewing Gum and Grouse requests require an approach
choice; the resolver does not select one arbitrarily. Selected lake requests
retain an unknown exit rather than inventing a return itinerary.

This delivers bounded western approach topology/display and historical access
inventory depth. It is **not destination route-completeness or source-completeness**:
individual campsites, shoreline access, water availability, full mileage,
current operating conditions and remaining western branches are explicit gaps.
The twelve nodes are descriptive graph/display positions; no new official
junction names, surveyed lake points or facility coordinates are asserted.

### Source dispositions

| Source | Disposition in this batch |
| --- | --- |
| 2010 official geospatial overview, western panel | Ingested explicit 20E14, 19E21, 19E10, 20E17, 20E16 and 20E98 connections, plus lake identities. Map georeferencing was used to review dataset positions, never trace a boundary or compute distance. Other branches remain deferred with topology gap. |
| 2012 mileage table, Gianelli/Bell Meadow/Crabtree columns | Ingested the selected destination totals above as reports; precise endpoints remain unspecified. Deeper unselected destinations remain deferred. |
| 2018 Favorite Hiking Trails page 2; 2021 schematic; undated GIF | Conflicting and preserved Powell totals. Guide identifies Gianelli/Burst Rock/Powell progression. Burst Rock is not modeled as a summit objective; the source-feature break east of it is only a trail node. Existing Camp/Bear facts remain unchanged. |
| Chewing Gum and Grouse minimum camping maps, page 1, 2021 filenames | Visually reviewed and ingested trail/lake distinction; 100-foot minimum versus 200-foot LNT recommendation. Grouse trail/lake camping exclusion and Chewing Gum warning that existing sites may be illegal are explicit. No campsite is declared legal or available. |
| National Forest System Trails public layer | Ingested bounded slices below, matched to named trails and official map connections. All unrelated returned features excluded from committed snapshot. Source lengths/IDs/hashes retained; native EPSG:4269, service-normalized EPSG:4326. |
| April 2012 Trailheads guide | Ingested western trailhead camping opportunity reports, one-night trailhead limit, Crabtree restrooms, historical no-facilities statements at Gianelli/Bell Meadow, and approximate driving directions. Existing historical parking descriptions reused. Current inventory and road status remain unknown. |
| [Traveler 2023](https://www.fs.usda.gov/sites/nfs/files/legacy-media/stanislaus/Traveler%202023.pdf), pages 8 and 10 | Ingested Crabtree vault-toilet and one-night camper/stock stay reports. Planned toilet improvements described as complete-by-2026 are retained as a plan, not proof of completion. Kennedy and other forest facilities deferred to their regional batches. |
| [Aspen Chewing Gum](https://www.aspenmeadowpackstation.com/index.php/adventures-menu/destinations/gianellis-trail-head-menu/chewing-gum-lake-menu), [Grouse](https://www.aspenmeadowpackstation.com/index.php/adventures-menu/destinations/crabtree-trail-head-menu/grouse-lake-menu), [Gem](https://www.aspenmeadowpackstation.com/index.php/adventures-menu/destinations/crabtree-trail-head-menu/gem-menu) | Ingested attributed mileage reports, Chewing Gum route-finding qualification and Grouse one-night report. Publication date and riding-distance convention unknown. Fisheries, campsite/firewood availability and marketing descriptions are not promoted to current inventory. No copyrighted artifacts redistributed. |
| Aspen home, trail rides, booking/referral hierarchy | Inspected; booking, seasonal operation and remaining destination inventory deferred to completion/facility audit. No prices, capacity or availability imported. No inference that riding and hiking times are equivalent. |
| [Occupancy alert](https://www.fs.usda.gov/r05/stanislaus/alerts/forest-order-limiting-occupancy-and-use-remains-effect) and linked signed STF-16-2026-09 | Ingested dated forest occupancy context (14 consecutive days in 30 for developed sites; 21 total days/calendar year in undeveloped locations within one Ranger District), preserving exemptions. No developed/undeveloped classification assigned to these trailheads. Conflicting supersession preserved: signed PDF footer names STF-16-2024-10; webpage names STF-16-2022-06. These general limits do not resolve or override trailhead-specific one-night guidance. No new executable camping rule. |
| Current alert index and [seasonal-extension detail](https://www.fs.usda.gov/r05/stanislaus/alerts/extension-seasonal-road-closures) | Inspected. That alert lists 4N12/5N01 and Calaveras roads and carries April 16–June 1, 2026 dates. This is not proof that Crabtree/Gianelli/Bell roads are open. Current MVUM, fire orders and route-specific road status require recheck; other regional closures retained for later batches. |
| Foundation permits, signed Emigrant order, regulations and conditions | Already represented and reused. Selected routes inherit wilderness requirements and existing one-night/sanitation/stock/stove conflicts. Trailhead-only requests do not inherit an overnight wilderness permit obligation. |
| Bell Meadow Research Natural Area | Excluded as a distinct managed-land/ecology subject, not an alternative identity for Bell Meadow Trailhead. No new land entity or unsourced boundary introduced. |

Historical PDFs reviewed in preceding batches were reused; new Traveler,
operator and occupancy sources were retrieved October 6 UTC. Unknown event dates
remain null. Retrieval/review context never establishes present operation.

### Geometry acquisition and vertex review

Both #205 and this batch use the same reviewed 45-feature input, retrieved
2026-10-06 at 00:09:34 UTC. Exact acquisition parameters (including the previously
requested #205 follow-up) are now recorded here and in the new snapshot:

```text
GET https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0/query
f=geojson
where=1=1
geometry=-119.91,38.13,-119.70,38.27
geometryType=esriGeometryEnvelope
inSR=4326
spatialRel=esriSpatialRelIntersects
outFields=objectid,trail_name,trail_no,trail_cn,bmp,emp,segment_length,gis_miles,globalid,admin_org
outSR=4326
returnGeometry=true
```

No geometryPrecision, maxAllowableOffset, quantization or simplification was
requested. Intersecting features are returned whole; the Bell Meadow trailhead
can therefore lie west of the query envelope. Retrieval does not establish
survey date or coordinate accuracy. The bounded output retains original
attributes, global IDs, full source-geometry SHA-256, source vertex counts,
inclusive zero-based ranges and a hash checked by the consumer.

| Physical leg | Source object | Inclusive vertices |
| --- | ---: | --- |
| Gianelli–Burst display break | 9429323 | 0 → 67 |
| Burst break–Powell junction | 9505484 | 0 → 73 |
| Powell spur | 9430968 | 0 → 22 |
| Powell junction–Lake Valley junction | 9505484 | 73 → 290 |
| Lake Valley junction–Chewing Gum approach | 9429539 | 267 → 200 |
| Lower Lake Valley | 9430389 | 0 → 167 |
| Lake Valley break–Chewing Gum approach | 9429539 | 0 → 200 |
| Bell Meadow–Pine Valley junction | 9431555 | 0 → 343 |
| Pine Valley junction–Grouse source break | 9431555 | 343 → 436 |
| Grouse break–north approach | 9429412 | 0 → 120 |
| Pine Valley connector | 9430585 | 0 → 146 |
| Bear junction–Groundhog junction | 9430618 | 806 → 477 |
| Groundhog junction–Gem junction | 9430618 | 477 → 257 |
| Gem junction–east approach | 9429611 | 71 → 40 |

The official overview establishes the mapped network, the named Powell spur and
2018 guide corroborate Powell access, and lake detail maps refine Chewing Gum
and Grouse approaches. Dataset vertices were overlaid using PDF georeferencing
for visual review. Chewing Gum vertex 200 follows its west side; Grouse vertex
120 follows its north side; Gem vertex 40 follows its east side. These chosen
positions are trail display endpoints, not surveyed lake destinations or
campsites. Source-feature breaks do not become asserted physical junctions.

Three joins retain tiny source offsets: Lake Valley/Crabtree (as documented in
#205), Powell spur/Burst Rock, and Pine Valley/Bell Meadow. No point is snapped,
interpolated or rounded. Map/guide evidence supplies connectivity independently
of those offsets. The renderer accepts the original nearby endpoints under its
existing tolerance; the batch changes no geometry tolerance or topology code.

### Candidate and verification

`scripts/ingest_emigrant_western.py` creates one typed DRAFT ChangeSet, validates
it, prepares a detached candidate and writes through the canonical serializer.
Use a clean `6304e247` checkout as `--base`; `--reviewed-input` is optional when
reusing the committed snapshot. The builder never fetches or publishes.
Four existing coverage gaps are narrowed; earlier observations and ChangeSets
remain intact. Two manifests distinguish selected routes/lakes from western
trailhead facilities. Forest-wide occupancy context is scoped to wilderness
contexts, not used to infer that a trailhead-only stay enters wilderness.

Tests exercise both directions, exact shared physical/geometry reuse, distinct
lake versus trail endpoints, approach ambiguity, rejection of unrelated entry,
unknown atomic mileage, independent reports, current-condition and facility
scope isolation, permit requirement joins, historical availability, order
conflicts/effective intervals, generated directories/HTML/JSON and downloadable
GeoJSON/global map coverage. Existing Camp/Bear regressions remain unchanged.

## Combined northern batch: six approaches and access depth

Started from refreshed `origin/main` at `c3d5c621` after the authorized squash
merge of #206. Before this batch, Emigrant had ten named trailheads, eight
western routes, nineteen physical segments, seventeen trail nodes, six lakes
and the collective Crabtree restroom resource. No northern route graph or
northern display geometry existed. Existing wilderness rules and neighboring
Hoover/Yosemite identities are reused rather than duplicated.

### Delivered planning scope

| Approach | Physical graph | Display and endpoint boundary |
| --- | --- | --- |
| Kennedy Meadows → Kennedy Lake | Parking → described trail start → 20E11/21E03 junction → western lake approach | Topology only. The reviewed trail dataset does not reach parking, and the Kennedy Lake branch has an unsnapped roughly 45-metre endpoint offset. |
| Kennedy Meadows → Relief Reservoir | Shares the first two Kennedy segments, then follows 20E11 to the eastern reservoir approach | Topology only. No shoreline spur, dam crossing or campsite is invented. |
| Waterhouse → Waterhouse Lake | Named 19E31 trail to mapped terminus | Drawable; terminus is distinct from lake identity and any campsite. |
| Coyote Meadow → Cooper Meadow | Named 20E15 to its explicit 20E08 junction in Cooper Meadow | Drawable; no inference that the meadow is a campsite or that it has available water. |
| Eagle Meadow → Eagle Pass | 20E08 from the mapped trailhead road crossing to the northern boundary approach | Drawable. The guide says entry into Emigrant is south from the pass; this approach alone does not assert wilderness entry. |
| Sonora Pass → Leavitt Lake Trail junction | Southbound PCT across five contiguous source features | Drawable to the explicit 22071 junction only. No Leavitt Lake, Leavitt Peak, Latopie Lake, Dorothy Lake or Yosemite continuation is modeled. |

This adds six routes, thirteen physical segments, thirteen trail nodes, three
waterbodies, Cooper Meadow, Eagle Pass and five historical facility resources:
Kennedy and Sonora restrooms, Kennedy faucets, and distinct Eagle/Coyote horse
camps. Only the explicitly reported half-mile parking-to-trail walk has an atomic
distance; the other twelve segment distances remain unknown. The 2012 and 2018
three-mile Relief reports, 2023 six-mile round-trip report and separate half-mile
parking walk remain independent reports. Parking inclusion cannot be resolved
by adding, halving or subtracting those totals. Kennedy Lake's operator mileage
retains its unspecified riding-distance convention. The 2018 Cooper Meadow
three-mile one-way report is also retained at route level; its precise meadow
endpoint is unresolved and it supplies no atomic length for the displayed
Coyote–Cooper segment.

This is bounded approach coverage, not destination route completeness. It does
not establish return itineraries, campsite inventory, water safety, current
stock suitability, highway crossing geometry or exclusive jurisdiction. The
PCT follows the Emigrant/Hoover divide; Emigrant requirements do not establish
Hoover or PCT permit coverage. Those issues have a route-specific visible gap.

Route-only overnight intents receive the evidenced Emigrant applicability
context as well as named-resource intents. Eagle's northern boundary approach
and trailhead-only intents do not assert entry. The static wilderness-context
claims are deliberately outside the recheck manifest so that a route's
conditions and profile do not leak into another route's recheck.

### Northern source dispositions

Sources were reviewed on 2026-10-06. Government PDFs were downloaded directly;
operator pages were read through the web retrieval service after direct HTTP
returned 403. No copyrighted operator page, photo, third-party map or PDF is
redistributed. Publication editions stay in claim values; unknown real-world
observation dates remain null.

| Source/layer | Disposition and coverage limit |
| --- | --- |
| 2010 USFS Emigrant geospatial overview, northern panel | Ingested named connections, resources and explicit boundary context; reviewed rendered overlays against named NFS trails. A trail endpoint is not a lake coordinate or campsite. Boundary polygon still deferred. |
| 2012 USFS trailhead guide, ROG 16-26 | Ingested northern parking, facility/camping reports and approximate driving directions. Waterhouse's ½–¾-mile range and about-50-yard setback remain qualified. The printed 4N31 conflicts with the map's 5N31 and is preserved, not silently corrected. |
| 2012 mileage table, ROG 16-27 | Ingested Kennedy Lake 7.5 and Relief Reservoir 3.0 as destination reports. Other Kennedy objectives remain deferred with the route-topology gap. |
| 2018 Favorite Hiking Trails, ROG 16-41 | Ingested Relief and Eagle Pass mileage (p2), Cooper Meadow from Coyote Meadow Trailhead at three miles (p3; p2 specifies one-way mileage), Relief stock-use report and Eagle's boundary distinction. Historical difficulty or stock use is not current clearance. |
| Traveler 2023, pp8–10 | Ingested Kennedy parking/trail-start description, one-night limit and vault toilets, Sonora planned toilet project and highway vehicle advisory. Planned 2026 completion remains unknown. Broader campground and reservation inventory is deferred. |
| [Brightman Recreation Complex, ROG 16-53-01, March 2020](https://www.fs.usda.gov/sites/nfs/files/r05/stanislaus/publication/Brightman%20Flat%20ROG.pdf), pp1–2 | Ingested Kennedy paved/pull-through parking, tables, accessible vault toilet and faucets. Preserved two-night/$5 reports against 2023 one-night and operator $10 reports. Baker/Deadman and the other approach campgrounds were inspected but their individual inventory is deferred with the facility gap. No current faucet flow or potability inferred. |
| [Horse Camping outside Wilderness, ROG 16-08, February 2020](https://www.fs.usda.gov/sites/nfs/files/r05/stanislaus/publication/Horse%20Camping%20ROG.pdf), pp1–4 | Ingested distinct Eagle/Coyote horse-camp identities, historical improvements/fees and outside-wilderness stock setback guidance. Eagle camp restrooms do not become trailhead restrooms. No camp-to-trailhead connector is inferred. General developed-camp livestock restriction and other horse camps are deferred; signed wilderness stock context remains in the foundation. |
| [June 2026 road alert](https://www.fs.usda.gov/r05/stanislaus/alerts/stanislaus-national-forest-extends-seasonal-mvum-closure-two-high-elevation) and linked signed STF-16-2026-07 with Exhibits A/B | Ingested June 1–15 historical 4N12 restriction for Coyote/Waterhouse, exemptions and snow qualifier. Signed page and both map exhibits visually reviewed. Preserved the alert summary's STF-16-2026-78 versus structured/PDF STF-16-2026-07 disagreement. Expiration is not evidence of reopening. 8N13 is outside this batch; no unrelated road closure is applied by proximity. |
| April seasonal extension, current alert index and MVUM hierarchy | Already represented as current-order recheck sources; superseded April order is not substituted for June/current conditions. Exact present motor access requires current MVUM/order review. Current unrelated 4N90 closure is not projected onto these routes. |
| [Kennedy operator home](https://kennedymeadows.com/index.html), [PCT page](https://kennedymeadows.com/sonoraPCThikers.html), [destination list](https://kennedymeadows.com/packtripdestinations.html) | Ingested bounded mileage, trailhead fee, transport referral and conflicting season reports. Retained page-age warning (2019 construction forecast); no live prices, service schedule or reservable inventory asserted. Other destinations, rides, cabins and linked Triple Crown canister inventory deferred with operator/facility gaps. Operator campfire summaries do not override current Forest Service orders. |
| Operator-linked Deadman/Baker USFS legacy detail URLs (recid 15027/15011) | Retrieval returned 403; excluded for access in this pass. Historical Brightman descriptions were reviewed, but present campsite/booking inventory remains deferred rather than invented from the operator's first-come statement. |
| [Caltrans Highway 108 conditions](https://roads.dot.ca.gov/?roadnumber=108) | Inspected linked authority; live road status deliberately not snapshotted as permission or future clearance. Northern access rechecks require current highway/order review. Other highway, operator and booking depth remains in the final source audit. |
| NFS trails query below | Ingested nine reviewed contiguous slices and a branch-identity corroboration feature. Duplicate PCT jurisdiction fragments, multipart alternatives, motor/winter trails and unreviewed branches excluded from the selected graph. Their presence is not treated as a route connection. |

### Northern geometry acquisition and review

The direct query returned 207 features at 2026-10-06 15:14:14 UTC. Its exact
parameters and reviewed input SHA-256 are recorded in the committed snapshot.
The builder rejects a different supplied input hash instead of silently
accepting a changed live response.

```text
GET https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0/query
f=geojson
where=1=1
geometry=-119.98,38.20,-119.52,38.37
geometryType=esriGeometryEnvelope
inSR=4326
spatialRel=esriSpatialRelIntersects
outFields=objectid,trail_name,trail_no,trail_cn,bmp,emp,segment_length,gis_miles,globalid,admin_org
outSR=4326
returnGeometry=true
```

| Physical leg | Source object | Inclusive vertices |
| --- | ---: | --- |
| Waterhouse | 9428140 | 0 → 147 |
| Coyote–Cooper Meadow junction | 9430353 | 0 → 422 |
| Eagle road crossing–feature break | 9430941 | 254 → 438 |
| Eagle feature break–northern pass approach | 9430469 | 0 → 77 |
| PCT south 1 | 9501224 | 0 → 60 |
| PCT south 2 | 9510733 | 0 → 560 |
| PCT south 3 | 9513460 | 0 → 39 |
| PCT south 4 | 9511588 | 0 → 781 |
| PCT south 5 to Leavitt Lake branch | 9502156 | 0 → 587 |

All PCT feature joins are exact original endpoints. Leavitt Lake branch object
9475574 ends exactly at selected vertex 587; its source attributes, geometry and
hash are retained solely to corroborate the explicit junction. Its branch is
not part of the rendered route. No source point is snapped, rounded, simplified
or interpolated, and no source length becomes canonical mileage. Native
EPSG:4269 is normalized by the service to EPSG:4326. Accuracy remains unknown;
geometry is non-navigation-grade.

The 2010 map's georeferencing was used for review overlays, not tracing. Eagle's
start is the mapped trail/road crossing, not a surveyed parking location. Its
endpoint is the northern boundary approach. Coyote's endpoint is the explicit
20E15/20E08 junction in the named meadow; Waterhouse stops at the named feature
terminus. The PCT begins south of Highway 108 and does not draw the highway
crossing from parking. These assignments are descriptive review, not surveyed
point features or guaranteed modern on-ground alignments.

Kennedy source 9428128 (20E11) stops well south of the resort/parking approach.
Kennedy Lake source 9505483 (21E03) also starts roughly 45 metres from the
reviewed 20E11 branch position. Explicit map/guide connections support the
graph, but neither gap is bridged with fabricated geometry. Both Kennedy routes
therefore publish **no** GeoJSON, including their potentially usable subparts.
This preserves the renderer's full-route geometry invariant.

### Northern candidate and verification

`scripts/ingest_emigrant_northern.py` regenerates the one typed ChangeSet against
a clean `c3d5c621` base. It validates and prepares through the domain write
service and canonical serializer; it never fetches, approves or publishes.
Only the existing route-topology and facility-inventory gaps are narrowed;
previous observations, relationships and ChangeSets remain intact.

Focused tests exercise forward/reverse traversal, shared Kennedy paths, explicit
missing geometry, drawable source provenance, endpoint/resource distinction,
unsupported-entry rejection, direct-route and named-objective permit joins,
Eagle boundary exclusion, trailhead-only scope isolation, camping/fee and road
identifier conflicts, expired-order answerability, range precision and distinct
horse-camp facilities. Session-fixture site tests cover directories, HTML/JSON,
public history, downloadable GeoJSON and the global map. Full-suite and affected
site-group results are recorded in the PR after completion.

After northern review, the planned remaining combined phases are southern and
cross-boundary coverage, then boundary/facility/booking/source completion audit.
Kennedy display geometry remains an explicit follow-up, not silently complete.

## Combined southern coverage and completion audit — 2026-10-06

This single candidate combines the two remaining planned batches. It supplies
five bounded approaches, the designated wilderness display boundary, selected
cross-boundary permit behavior, three approach campgrounds, 45 individually
reviewed Cherry Valley campsite listings, 21 Kennedy cabin listings and two
operator service inventories. It does **not** claim that every Emigrant trail,
remote campsite, facility connector or neighboring wilderness is complete.

### Route review

| Approach | Graph and source | Geographic display | Remaining limit |
| --- | --- | --- | --- |
| Box Springs → Chain Lakes | 2010 official map 19E95/19E28; June 2012 table reports 2.5 miles | None | Primitive trail; full parking-to-lake geometry unreviewed; no atomic distance inferred |
| Bourland Meadow → mapped 19E13 terminus | Official map and named USFS feature 9431238 | Whole feature, 219 vertices | Terminus west of wilderness boundary; no invented continuation to Chain Lakes or assertion of wilderness entry |
| Shingle Springs → Kibbie Lake | 2010 southern panel: 20E11 to explicit east branch into Yosemite; 2012 report 4.3 miles | None | NPS branch/parking geometry not reviewed; Yosemite destination rules apply |
| Shingle Springs → Huckleberry Lake | Shared first segment; 20E11 via Styx Pass, Boundary Lake junction and Lord Meadow | None | No Boundary Lake spur; exact divide-side jurisdiction, complete geometry and current crossings unresolved; 2012 total 18.3 is a report |
| Leavitt Lake → PCT junction | Current USFS trail/TH detail and 2010 Leavitt panel, named 22071 chain | Five complete features; exact join to published PCT endpoint | Trailhead page coordinate differs from mapped trail start; not a parking-centroid substitution. Reports 1.65 vs 1.8 miles stay separate |

Named resources remain separate from trail endpoint nodes. Each graph traverses
in both directions. No return itinerary, atomic mileage, campsite, safe water or
current trail condition is manufactured. Shingle approaches reuse the same
physical entrance segment. Leavitt ends at the existing PCT junction node; the
Sonora Pass route remains unchanged. Neither Leavitt Peak nor a lake/pass
continuation is inferred.

The southern USFS query returned 71 features, including motor/winter features
that were excluded. Reviewed northern input is the previous 207-feature response.
Both exact query parameter sets, input hashes, source attributes, global IDs,
vertex ranges and original geometry hashes are recorded in the new snapshot.
Original GIS length fields are provenance, never computed hiking distances.

The complete Box Spring feature starts west of its trailhead marker and crosses
19E28 at an interior vertex; the selected parking connector is not established.
The Bourland feature terminates without a continuous dataset connection to that
chain. We preserve these source limitations instead of stitching nearby lines.
Kennedy review still lacks the parking connector and retains the roughly
45-metre 21E03/20E11 offset. Those two existing routes remain topology-only.

### Boundary review

USGS PAD-US Management Areas returned seven name matches for `Emigrant`.
Only OBJECTID **237112** matched Emigrant Wilderness, California, USFS,
`Category=Designation`, `Des_Tp=WA`; fishing access sites, an ACEC and unrelated
lakes/parks were excluded. Its outer ring has 9,263 vertices and bounds roughly
119.919–119.596° W / 38.026–38.322° N, consistent with the official overview.
The selected polygon is retained without local simplification or rounding.
The existing boundary gap is narrowed to precision/amendments/jurisdiction,
while its earlier unreviewed history remains in the published ChangeSet.
Geometry never creates access, ownership, containment or permission.

### Source-disposition ledger

All retrieval/review below occurred October 6, 2026. Undated source statements
remain undated observations; page update dates and notice dates are not replaced
by retrieval dates. Current pages were read through ordinary HTTPS, including
HTML text that the search tool could not fetch. Original downloads remain local
research artifacts and are not committed.

| Source / hierarchy layer | Disposition | Result or bounded limit |
| --- | --- | --- |
| Emigrant overview, Hwy108 access, permits, signed wilderness/occupancy orders, conditions and alerts | Already represented; permits/alerts reviewed again | Existing conflicts preserved. Source-specific directions and rules do not become region-wide permissions |
| 2010 Emigrant geospatial map, southern and Leavitt panels | Ingested | Explicit labeled connections for the five approaches, place identities and branch distinctions |
| April 2012 trailhead guide / June 2012 mileage table | Ingested / conflicting and preserved | Box/Bourland primitive access, historical one-night limit, approximate road directions, destination mileage reports. Bourland schematic 0.0 is not a zero-length edge |
| USFS NFS Trails service southern 71-feature / northern 207-feature inputs | Ingested / deferred with gap | Bourland and Leavitt complete selected chains only; no geographic Shingle/Box/Kennedy route published |
| USGS PAD-US Management Areas | Ingested | Exact designated-wilderness identity and display polygon, with query/selection/hash provenance |
| USFS Leavitt Lake trailhead and trail detail | Ingested / conflicting and preserved | Rough 32077 requires high-clearance 4WD; seasonal qualifier, no restrooms/site fee, separate permit fee; location/elevation and 1.65-mile report preserved separately from old table/geometry |
| USFS Hoover permit page, updated May 4, 2026 | Ingested | Leavitt **Lake** no-quota vs Leavitt **Meadows** quota; overnight permit and canister distinction; no transfer of Emigrant no-quota/free/hanging policies |
| Recreation.gov Hoover product 445856, all policy/fee sections | Ingested / conflicting and preserved | Print/signed-copy deadline, age-qualified fees, quota-entry release description, continuous-trip conditions and south-of-CA120 addendum/permit qualification |
| NPS wilderness permit FAQ, wilderness regulations, trailheads map Hetch Hetchy inset | Ingested; existing Yosemite identities/rules reused | Kibbie permit issued by Stanislaus, Yosemite pet/food rules still apply, Kibbie quarter-mile fire restriction. FAQ/regulations differ on White Wolf continuous-trip stop exception |
| Hoover general regulations / full adjacent-wilderness inventory | Deferred with gap | Selected Leavitt route policies reviewed; no exhaustive Hoover facility/route/stock-zone inventory, signed-order boundary import or PCTA permit eligibility claim |
| Cherry Lake page and current alerts | Ingested | Source of local facilities/road cautions; specific signed orders govern their bounded areas. Lake directions point to campground, not a verified Shingle driving route |
| STF-16-2025-01 signed four-page Cherry Lake order/map/decision memo | Ingested | January 27, 2025–December 31, 2026; restricted lake-shore/island acts and exemptions. No traced polygon or blanket campground closure |
| STF-16-2026-06 signed 1N98 road order + alert | Ingested | June 1, 2026–May 31, 2027; road from 1N14Y junction to terminus. Does not establish closure of all Cherry access or automatic reopening after expiration |
| Current Baker and Deadman USFS pages, all overview/amenity/fee sections | Ingested / conflicting and preserved | Campground identities, counts, operator/fees/season, occupancy; hydrants vs no-potable-water wording. Baker vault vs flush conflict; 2020 paved pads vs current dirt pads |
| Brightman 2020 / Traveler 2023 / Horse Camping 2020 | Already represented; Brightman comparisons ingested | Historical Kennedy/horse-camp records and previous conflicts retained; no present opening inferred |
| Cherry Valley USFS current conditions, overview, fee table and amenities | Ingested / conflicting and preserved | No water service plus retained July 3, 2025 E. coli boil notice; $41+fees/taxes vs $29/$58; vault vs flush toilets |
| Recreation.gov Cherry Valley 234756 overview and all 45 linked site pages | Deep inventory ingested / conflicting and preserved | Sites 002–046 with individual source URLs, type/capacity/vehicle fields/times; no site 001 inferred. Overview water conflicts with manager; 41+5 count differs from 45 exposed listings |
| Cherry Valley individual vehicle data | Conflicting and preserved | Equipment trailer length, maximum vehicle field and driveway lengths remain separate. Example site 029: trailer 50 ft, vehicle field 24, driveway 32. Site 028 short-site advisory retained; 002/003 missing max-vehicle field remains unknown |
| Baker/Deadman individual numbered sites | Deferred with gap | Current manager/operator provide aggregate inventory, not reviewed individual numbered booking pages; both are first-come, no reservations |
| Kennedy home, amenities, PCT page, destinations | Ingested / already represented | Current campground booking method; existing season, trailhead camping/fee and destination-mileage conflicts retained |
| Kennedy cabin page, full inventory and booking/cancellation notes | Deep inventory ingested | 21 listed cabins (1–22 except 13); capacity/base rate/category; cabin 3 has no kitchenette. Taxes, dog/extra-person charges, price changes after booking and cancellation cutoff ambiguity retained |
| Kennedy pack options, pack FAQ, ride options and ride FAQ | Ingested / conflicting and preserved | Service/booking/rider limits; ride page Kennedy Lake 8 mi vs prior 7.5 retained. Operator permit pickup advice is not authority to bypass Yosemite-bound issuance restrictions |
| Kennedy maps/photos, guest checklist/gear list, wedding/catering details | Excluded as irrelevant to this bounded planning inventory / reference-only | No copyrighted media redistributed; no new trail connection derived from advertisements |
| Aspen home/ride accordion, pack trips, all-inclusive and FAQ | Ingested | Season/weather qualifier, phone booking, pack options/deposit/one-way rate basis, inclusive minimums/gear limits. Larger-group invitation does not exempt wilderness limits |
| Aspen individual destination advertisements beyond prior Chewing/Grouse/Gem reviews | Deferred with gap | Names alone do not establish new routes; deeper lake branches outside the five selected approaches remain in the topology gap |
| Aspen referred Pinecrest campground / off-site hotels and resorts | Deferred with gap | Regional lodging alternatives and their individual inventories are outside the three approach campgrounds/two operators audited here |
| Secondary commercial trail sites and obsolete 2014 Rim Fire report | Excluded as non-current/non-primary for the promised routes | No current closure, route geometry or mileage imported from those pages |

### Consumer acceptance

The new rechecks are `result-emigrant-completion-pretrip-recheck` and
`result-emigrant-completion-access-recheck`. They expose route limits, source
conflicts, dated restrictions, individual inventory and parent booking terms in
applicable contexts. Access-only requests do not trigger a wilderness-entry
requirement. A Leavitt overnight route triggers its persisted permit requirement;
a day hike does not. Its Hoover food-storage requirement is distinct from
Emigrant's. Kibbie requests reuse Yosemite permit, food-storage and pet rules
while retaining Stanislaus issuance evidence.

Remaining gaps are evidence/itinerary-specific: unresolved geometry connectors,
divide-side jurisdiction, deeper branches and returns, actual live booking and
operating status, unresolved source conflicts, individual Baker/Deadman sites,
Cherry Valley site 001, remote campsite inventories and agency confirmation for
long cross-boundary itineraries. This finishes the **combined planned review
batch**, not an assertion of wilderness-wide source or route completeness.
