# Taboose Pass corridor review, 2026-10-06

This is normal-depth **foundation coverage with connected access-to-pass topology**.
The named hiking route covers Taboose Pass Trailhead to Taboose Pass; the separate
road approach covers the US 395 junction to the trailhead. It does not claim
source-complete or deep individual-site coverage. The trail graph is connected
in both directions, but mileage remains unresolved and current travel conditions
require recheck. Western JMT branches are contextual evidence, not an asserted
onward itinerary. No social-media example drove source selection.

## Reproduction and publication boundary

`scripts/ingest_taboose_pass.py` builds typed records, proposes a DRAFT ChangeSet,
validates it and prepares a detached serializer-owned candidate. It never fetches,
approves or promotes knowledge. This PR has one new ChangeSet:
`wp-20261006-taboose-pass-corridor`. For a pre-merge correction, regenerate this
same ChangeSet against a clean checkout of the PR base:

```sh
python scripts/ingest_taboose_pass.py --base /path/to/clean/main
```

With the reviewed raw USFS query response, append
`--reviewed-input /path/to/trails.json` to reproduce the geometry snapshot.
The query parameters, raw-response hash, complete selected feature IDs/global IDs,
original attributes and geometry hashes are retained in the snapshot. Four exact
endpoint-connected source features form a single named, unbranched mainline.
Only duplicate shared vertices are omitted. No coordinates are snapped, rounded,
interpolated or simplified, and no canonical mileage is computed from geometry.

The tests cover both traversal directions, separate road mileage, a nearby but
unsupported campground entry, executable rules and persisted requirement joins,
recheck scope/date behavior, existing managed-land boundaries, official geometry,
source conflicts and generated HTML/JSON/map discovery. An unspecified exit stays
unknown. The current named-intent API accepts access kinds as exits; pass-node
traversal is exercised directly through the shared traversal service. No new
exit type or implied round trip is introduced by this data batch.

## Identity and jurisdiction audit

No Taboose canonical entities or prior Taboose PRs were present on base `149d608f`.
Existing `wilderness-john-muir`, `agency-inyo-national-forest`,
`park-sequoia-kings-canyon` and `permit-inyo-overnight-wilderness` are reused.
Existing reviewed PAD-US wilderness and NPS fee-manager boundary claims remain
unchanged. Kings Canyon is represented using the repository's existing combined
park identity; no duplicate park or new ownership polygon is invented.

The USFS map/description supports eastern wilderness traversal and the boundary
at the pass. A separate western-continuation zone holds park rules. A trip on the
eastern approach does not acquire every NPS restriction solely because it is
near the boundary. County campground facilities belong to that campground, not
the trailhead. County campground operation does not establish ownership of the
entire approach road.

## Source disposition ledger

All sources were retrieved/reviewed October 6, 2026. Source URLs also live in the
builder and canonical Source records; identical existing URLs reuse source IDs.
Only factual paraphrases and public-domain USFS geometry are redistributed.

| Source/layer | Disposition | Material coverage or limit |
| --- | --- | --- |
| [USFS Taboose trail](https://www.fs.usda.gov/r05/inyo/recreation/trails/taboose-pass-trail) | ingested; conflicts preserved | Road directions, route, >6,000 ft gain, permits/quota, no lockers, water treatment, fire and stock guidance. Old recreation URL redirects to index; current trail URL found through official site search. |
| [Independence Area Trails map](https://www.fs.usda.gov/sites/nfs/files/legacy-media/inyo/Trails-%20Independence%20area.pdf) | ingested | Visually inspected page 1; named continuous trail, trailhead, pass, wilderness and NPS transition. Edition unstated. No tracing or map-scale mileage. |
| [JMT Entry Points guide](https://www.fs.usda.gov/sites/nfs/files/legacy-media/inyo/JMT%20TripPlan%20Entry%20Points.pdf) | ingested; discrepancy preserved | Approximate 6.5 mi to pass, 8.75 mi to JMT, 5,400/11,350 ft trailhead/pass. Header qualifiers retained. |
| [USFS National Forest System Trails](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0) | ingested | Named 3304 chain, IDs 9575473, 9574682, 9575492, 9575315; official display line and reviewed endpoint points. Original length/milepost fields differ from guide. |
| Existing John Muir / Sequoia-Kings Canyon PAD-US geometry | already represented | Reused through read services; no new land unit requires unmatched boundary gap. |
| Official road polyline / precise road-jurisdiction divisions | deferred with gap | Directions establish access; official road geometry and current vehicle clearance are not matched. No synthetic line is drawn. |
| [USFS wilderness permits](https://www.fs.usda.gov/r05/inyo/permits/wilderness-permits) | ingested | Entry agency, continuous travel, quota season, release phases, winter process, fees/cancellations and cross-boundary obligations. Whitney exit condition retained as beyond-route caveat. |
| [Trail names and quotas](https://www.fs.usda.gov/sites/nfs/files/publication/trail%20quota%20sheet.pdf_0.pdf) | ingested | Pages 2-3: JM27 = 10/day, 6 six-month and 4 two-week spaces; shared commercial/public quota. Broken `https:/sites/...` link in permit page resolved to same official host. |
| [Permit printing](https://www.fs.usda.gov/r05/inyo/permits/printing-instructions) | ingested | Paper/signature/leader, seven-day printing, 10am overnight no-show, reissue after changes, park regulations printout referral. |
| [Recreation.gov Inyo permit](https://www.recreation.gov/permits/233262) | ingested; conflicts preserved | Permit product, released inventory vs live availability, PST/Pacific wording and vehicle-food guidance. No booking or availability transaction. |
| [USFS wilderness regulations](https://www.fs.usda.gov/r05/inyo/permits/wilderness-regulations) | ingested | Group, food, camping, sanitation, pets, stock and pack-goat rules. County and NPS rules kept distinct. |
| [Wilderness Use order](https://www.fs.usda.gov/r05/inyo/alerts/wilderness-use-restrictions) | ingested; scope conflict preserved | Current embedded order 05-04-50-25-02 and Exhibit A, effective 2025-06-18 to 2027-06-18. Equipment-permit provision vs day-use exemption is not resolved silently. Unrelated lake/Shepherd/Whitney exhibits excluded as irrelevant to bounded route. |
| [Signed standing fire order](https://www.fs.usda.gov/sites/nfs/files/r05/inyo/publication/alerts/05-04-50-25-04%20Ansel%20Adams%20%26%20John%20Muir%20Campfire%20Restrictions.pdf) and [Exhibit P](https://www.fs.usda.gov/sites/nfs/files/r05/inyo/publication/alerts/25-05-50-25-04%20Exhibits%20B-S%20-%20June%202025.pdf) | ingested | Signed order p1; maps PDF p15 inspected visually. Drainage/elevation ban, 2025-06-10 to 2027-06-10 interval, specified stove exception; no traced fire-zone polygon. |
| [Stage 1 order](https://www.fs.usda.gov/r05/inyo/alerts/stage-1-fire-restrictions-effect) | ingested | 2026-06-22 to 2026-12-31; narrower pressurized-fuel/shutoff-valve stove exception and California permit. Dynamic recheck survives expiry. |
| [Food/refuse order page](https://www.fs.usda.gov/r05/inyo/alerts/food-and-refuse-storage-restrictions) | conflicting and preserved | Page start 2023 vs embedded effective 2025; 23-03 page ID vs linked 25-03 filename. Eight mandatory-container zones are listed elsewhere; no unsupported blanket Taboose canister mandate. Detailed zone polygons deferred with order-version/current-storage recheck. |
| [NPS Minimum Impact Restrictions](https://www.nps.gov/seki/planyourvisit/minimum-impact-restrictions.htm) and [linked PDF](https://www.nps.gov/seki/planyourvisit/upload/NoYear-MIR-5-14-20.pdf) | ingested for bounded western context | Park food, pets, camping, group and fire rules. The page has a separate day-hiking group maximum; no flattening to overnight limit. Unrelated named lake exceptions excluded. |
| [NPS trail conditions](https://www.nps.gov/seki/planyourvisit/trailcond.htm) | ingested as dated report | Taboose entry 2026-08-26: brush, washed-out crossings, stock not recommended. Report date differs from retrieval; exact crossing positions unknown. |
| [NPS grazing restrictions](https://www.nps.gov/seki/planyourvisit/grazingrestrictions.htm) | ingested; operational layer deferred with gap | 12-acre wet meadow exclusion in Taboose area; annual grazing opening/current stock suitability requires checking. No permission inferred from stock geometry. |
| [NPS stock atlas part 2](https://parkplanning.nps.gov/showFile.cfm?projectID=33225&sfid=186534) | ingested as historical map context | Mt. Pinchot panel, printed p11/PDF p13, reviewed visually. West-side branches and park boundary contextualized; JMT/Bench Lake continuation graph and spurs deferred. |
| [County campground](https://www.inyocounty.us/services/parks-recreation/campgrounds/taboose-creek-campground) | ingested; conflicts preserved | Two-road-mile access, 35-space report, six people/site, toilets, well, amenities, no showers/hookups, fees, fire rings and booking referral. Fishing summary deferred pending CDFW water-specific review. |
| [County campground map](https://www.inyocounty.us/sites/default/files/2025-05/Taboose.pdf) | conflicting and preserved | Visual p1: sites 1-36 plus toilets, trash, pay station, well and day use. Not copied or georeferenced. |
| [County water notice](https://www.inyocounty.us/sites/default/files/2026-07/0267_001.pdf) | ingested; uncertainty preserved | Both scanned pages reviewed. July 30 notice concerns May monitoring; future-tense June follow-up wording does not prove completion. Not a positive contamination result or boil-water order. |
| [ReserveAmerica facility/listing](https://www.reserveamerica.com/explore/taboose-creek-campground/INYO/1100013/campsites) | ingested at aggregate depth | Ordinary fetch 403; browser rendered 36 standard non-electric sites and expanded $14 rate panel. Individual site profiles, complete booking/cancellation terms and live availability deferred with gap. No copyrighted captures committed. |
| [County roads index](https://www.inyocounty.us/services/public-works/news/inyo-county-road-openclosed-status) | ingested as recheck pointer | Index refers to separate closure reports. No Taboose open-status claim extracted; route-specific current report/map matching deferred. |
| Sierra Forever maps/guidebooks, PCTA and secondary driving descriptions | excluded as unnecessary / reference discovery only | Primary map, trail text and official line dataset support the promised mainline. No secondary geography or source artifact is imported. |
| Campground individual sites, wilderness camps/spurs, exact creek crossings, road shape and western branch geometry | deferred with explicit consumer gaps | Normal-depth boundaries; absence of modeled facilities or alternates never means they do not exist. |

## Material qualifications

- Route directionality is supported; mileage is not resolved. The approximate
  guide, original service mileposts and GIS lengths all remain available.
- Road distance is approximately six miles, separate from hiking mileage.
- The trailhead has no bear lockers; conflicting trunk-storage and generic
  no-food-in-car guidance is retained with a recheck.
- A day hike is not labeled unconditionally permit-free while carrying gear
  covered by the active order. No unsupported equipment context is invented.
- Forest orders retain effective intervals and exemptions. Missing successor
  orders after expiry never establish permission.
- The campground 35/36 inventory disagreement is visible; a listing count is
  not live inventory. The well notice is a monitoring failure, not a positive
  contamination test. Neither the well nor creek receives a timeless quality
  or flow guarantee.
- The permit fee schedule is visible in canonical details and rechecks. It is
  not registered as an unconditional cost input, which would charge day hiking
  or manufacture a per-party total without a permit/participant calculator.
