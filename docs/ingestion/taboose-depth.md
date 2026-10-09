# Taboose facilities and western routes: follow-up batch

Outcome: one follow-up ChangeSet, `wp-20261007-taboose-facilities-west`, over the
published Taboose foundation. Reviewed October 6–7, 2026 (UTC retrieval context
October 7 01:21). No merge or publication is performed by the importer.

## Delivered scope and honest limits

- **Deep inventory:** all 36 individually opened ReserveAmerica site profiles,
  including vehicle layout/size reports, capacity, provider accessibility label,
  facilities, check-in/out and pets. Each site has its own source and claims.
  Dimensions retain `unit: not stated`; no invented feet, accessible-feature
  survey, availability or guaranteed RV fit. County pages' 30-foot and 45-foot
  general accommodation statements remain separate from site-specific values.
- **Route graph:** existing Taboose trailhead→pass segment reused in three
  bidirectional itineraries, onward to Bench Lake, Mather Pass and Pinchot Pass.
  Five new physical segments distinguish the two JMT junctions and Bench Lake
  spur. NPS geometry is display evidence, not inferred access or calculated
  hiking mileage. This is a connected mainline graph, **not full route-complete
  planning depth**: precise camps/water spurs, distances and some facilities are
  unresolved.
- **Planning:** original Inyo entry-permit requirements plus separately scoped
  NPS permit-carry, food, camping and fire requirements, plus an executable
  `equipment contains pet` prohibition on the western routes, grounded in the
  existing NPS pet claim. Following the Yosemite prohibition pattern, it adds
  no persisted fulfillment requirement; the composed planner surfaces its
  do-not-bring-pets consequence when applicable. The original east-only
  route never acquires west-only pet or weapon restrictions. The new recheck
  composes the existing manifest and the follow-up evidence. County stay-limit
  requirements join the campground and its individual sites.
- **Access audit:** PCTA parking/amenity/general vehicle guidance, county road
  maintenance identity and August 11 status-report review. County GIS geometry
  was inspected but is not redistributed without an explicit compatible license.
- **Conflicts:** signed food-order cover resolves its effective dates while old
  exhibit headers remain visible. Camp count (35 versus 36), trail mileage,
  vehicle-food guidance and day-equipment permit wording remain unresolved.
  More research did not turn disagreement into permission.

The intent resolver currently admits only access-kind exits (trailheads,
entrances and staging areas). Named destination/route plans therefore retain
`exit_unknown`; direct traversal proves connected routes to the lake/passes in
both directions. No fake trailhead identities or general planner-semantic change
is introduced to hide that existing limitation.

## Source dispositions

| Source / inspected layer | Disposition and result |
|---|---|
| [County campground](https://www.inyocounty.us/services/parks-recreation/campgrounds/taboose-creek-campground), [county parks overview](https://www.inyocounty.us/services/parks-recreation/) | Already represented, reviewed again; 35-space statement and original missed-May water-monitoring notice remain. No follow-up water result found in these pages. |
| [ReserveAmerica inventory](https://www.reserveamerica.com/explore/taboose-creek-campground/INYO/1100013/campsites), both pages and every site 001–036 detail link | Ingested; all 36 are standard non-electric sites, 1–6 people, maximum two vehicles, drive-in, gravel, partial shade, provider ADA label Y. Different site sizes/layouts retained. Provider IDs and exact detail URLs in importer and canonical sources. No booking or date-specific availability promotion. |
| ReserveAmerica Booking Window and Fees & Cancellations expanded panels | Ingested: one-day minimum advance and nine-month maximum. Rates already represented; panel gives no refund, cancellation deadline or cancellation-fee terms. Deferred with campground-depth gap; no transaction entered to discover terms. |
| [County Camping Information](https://www.inyocounty.us/services/parks-recreation/camping-information) | Ingested applicable stay limit, senior permit qualification, leashes/vaccination, firearm-use restriction, OHV speed and aggregate 30-foot RV statement. General fishing summary deferred pending water-specific CDFW review; general cell coverage is not a Taboose-specific coverage guarantee. |
| [County Fees & Rates](https://www.inyocounty.us/services/parks-recreation/fees-rates) | Ingested 45-foot aggregate RV statement and attendant-arranged spring/summer waste service guidance; fee/payment/no-hookups facts already represented. No invented dump-station point. |
| County linked group-picnic fee PDF / other county campgrounds | Excluded as irrelevant to individual Taboose campsite cancellation terms and this corridor. |
| [PCTA trailhead](https://explore.pcta.org/trailheads/taboose-pass-trailhead) | Ingested factual partner guidance: free overnight roadside parking at road end; no amenities listed; generally passenger-vehicle accessible dirt/gravel after initial pavement. No capacity, current passability or land-manager facility survey inferred. Recheck required. |
| [Official county GIS landing page](https://www.inyocounty.us/services/gis-data-maps), [county open-data hub](https://gisdata.inyo.gov) | Reviewed provenance: hub identifies county organization `0jRlQ17Qmni5zEMr`; matched county-owned ArcGIS items. |
| [Maintained Mileage System layer 0](https://services.arcgis.com/0jRlQ17Qmni5zEMr/arcgis/rest/services/Maintained_Mileage_System/FeatureServer/0), [Centerlines layer 1](https://services.arcgis.com/0jRlQ17Qmni5zEMr/arcgis/rest/services/Centerlines/FeatureServer/1) | Ingested factual road 3022, unpaved, maintenance list From/To wording. Eight named features returned. Geometry matched but deferred for licensing, not described as unlocated. No ownership/easement claim. |
| [County Conditions of Use](https://gisdata.inyo.gov/pages/conditions-of-use) | Reviewed: illustrative/as-is data, accuracy/currency/completeness cautions, no explicit redistribution license in item metadata or terms. Repository `DATA_LICENSE.md` requires explicit local-data license. No county geometry shipped. |
| County `COI_INF_Roads` and `Bishop_Streets` layers | Reviewed as corroborating discovery; not imported. Full county road 3022 total and repeated feature attributes are not independent segment lengths. Recorded-survey and assessor links deferred with exact-jurisdiction/easement gap; not needed to assert ownership because no ownership is asserted. |
| [Federal NFS Roads service](https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_RoadBasic_01/MapServer/0) | Named-TABOOSE query returned zero features; recorded as a search limit, not proof no federal road exists. Full road geometry remains deferred. |
| [August 11 county road report](https://www.inyocounty.us/sites/default/files/2026-08/CURRENT%20ROAD%20UPDATE%20%20%2008.11.26.pdf) and [additional report](https://www.inyocounty.us/sites/default/files/2026-08/Additional%20Road%20status%20information%2008.11.26.pdf) | Ingested dated review: neither lists Taboose. Omission is not evidence of open/passable status. |
| [California Drinking Water Watch](https://sdwis.waterboards.ca.gov/PDWW/JSP/WaterSystems.jsp) | Deferred for access: retrieval timed out; no result attributed to the water system. County CA1400516 notice retained, current operation/quality unknown. |
| [Signed food order 05-04-50-25-03](https://www.fs.usda.gov/sites/nfs/files/r05/inyo/publication/alerts/05-04-50-25-03%20Food%20and%20Refuse%20Storage%20Order.pdf) | Ingested visually reviewed signed cover, June 17 execution and June 18 2025–June 18 2027 effective dates. Exhibit A still says 05-04-50-23-04; preserve inconsistency. The order does not resolve vehicle storage at this trailhead. |
| Existing USFS entry guide, trail page, wilderness-use order and Recreation.gov Inyo permit overview | Already represented. Approximate 6.5/8.75-mile endpoints remain distinct; official trail dataset mileage disagreement, vehicle-storage conflict and equipment-carry/day-permit ambiguity stay open. No manager clarification invented. |
| [NPS maintained-trails catalog](https://catalog.data.gov/dataset/trails-of-sequoia-and-kings-canyon-national-parks), [IRMA profile](https://irma.nps.gov/DataStore/Reference/Profile/2253434), [download](https://irma.nps.gov/DataStore/DownloadFile/601800?Reference=2253434) | Ingested selected complete public-display/unrestricted trail features. Published 2018 dataset includes older edits; original feature accuracy/method/From/To and length attributes retained. |
| [2026 Kings Canyon stock map](https://www.nps.gov/seki/planyourvisit/upload/2026_KingsCanyonNp-Stock-Use-and-Grazing-Regulations-Map_508_Compressed.pdf) | Ingested visually reviewed Taboose–Bench–Mather–Pinchot panel and legend for current mapped topology, park context and Bench annual stock-night capacity. No geometry traced from map. |
| [Historical stock atlas](https://parkplanning.nps.gov/showFile.cfm?projectID=33225&sfid=186534), printed panels 7 and 11 | Already represented, further visual review for north/south continuity. Historical branch depiction not promoted into an additional modern alternate; exact alternative remains a gap. |
| [2026 Stock Users Guide](https://www.nps.gov/seki/planyourvisit/upload/2026_SEKI_Stock_Users_Guide_508.pdf), pp3,14, and [stock overview](https://www.nps.gov/seki/planyourvisit/stockuse.htm) | Ingested bounded forage/camp/crossing facts for 46-1–6 and 47-5 as applicable. Southwest Bench camp is separate from trail endpoint; no synthetic spur. Guide per-party stock/night limits and map annual grazing capacity are distinct. Older 2024 PDF discovery returned 404; replaced by current linked 2026 guide. |
| [Meadow dates](https://www.nps.gov/seki/planyourvisit/grazing.htm) | Ingested tentative 2026 zone46 opening and dynamic recheck; permanent meadow exclusions remain applicable. |
| [NPS general travel restrictions](https://www.nps.gov/seki/planyourvisit/minimum-impact-restrictions.htm) | Already represented after previous PR review, reused for western rules. Pet, wheeled/motorized equipment, weapons qualifications, waste, shortcuts, markers, gates, permit, food/camp/fire all remain separate jurisdictional claims. |
| [Wilderness food](https://www.nps.gov/seki/planyourvisit/bear_bc.htm), [boxes](https://www.nps.gov/seki/planyourvisit/bear_box.htm), [canister area descriptions](https://www.nps.gov/seki/planyourvisit/canister-areas.htm) | Ingested methods, non-guaranteed box availability, absence of a named Bench/Taboose listing without claiming actual absence, and competing required-zone seasonal wording. Exact itinerary zone classification still requires recheck. Approved-device list/rental prices deferred with equipment check, not a promised equipment catalog. |
| [NPS trail conditions](https://www.nps.gov/seki/planyourvisit/trailcond.htm) | Existing dated Taboose observation preserved; added western trail/crossing/snow/water recheck. No timeless open/safe assertion. |
| Mount Rainier Bench/Snow Lake search results; surrounding peaks/off-trail routes; historical Cinder fire discovery | Excluded as wrong destination or beyond bounded route scope/current status evidence. No Rainier amenities imported into Kings Canyon. |

## Geometry provenance and rebuild

Snapshot: `geometry/v0/snapshots/nps-taboose-west-20261007.geojson`.
Source archive hash, original complete feature attributes, local record indices,
vertex ranges, reversals and per-feature geometry hashes are retained. The source
has no populated stable feature/global identifier; indices identify rows only in
the hashed artifact. Reprojection uses EPSG:26911→4326. Only identical shared
endpoints are deduplicated. No rounding, simplification, interpolation, snapping
or calculated canonical hiking distance. NPS and USFS pass endpoints differ and
remain unmodified. Record186 is mislabeled `Pinchot Pass South`; the current map
and exact shared junction endpoints support its short connector role, with the
original label explicitly retained.

Optional geometry rebuild requires `pyshp` and `pyproj` in a temporary environment:

```sh
python scripts/ingest_taboose_west_geometry.py \
  --shapefile /path/to/seki_maintained_trails \
  --archive /path/to/downloaded-nps-trails.zip \
  --output geometry/v0/snapshots/nps-taboose-west-20261007.geojson
python scripts/ingest_taboose_depth.py --base /path/to/clean-main --output .
```

Always regenerate against the clean base, not against this unmerged candidate.
Typed DRAFT→validate→prepare owns all canonical JSON. Seven existing knowledge
gaps are replaced with narrower limits; original observations, claims and the
previous ChangeSet are not rewritten. Exactly one new ChangeSet is introduced.

## Verification contract

Focused tests cover bidirectional ordered traversal, original physical-segment
reuse, unknown distances, geometry lineage/hashes, original east-only scope,
western and county rule/requirement joins, pet prohibition consequences on all
three western routes for day and overnight trips (and no application without
pets or on the east-only route), every site's source/fit/recheck,
booking limits, unresolved conflicts and absent synthetic facility spurs.
A separate test module uses the shared `generated_site` fixture to check generic
camping/trails/pass discovery, new detail pages, geometry and published evidence.
The existing `test_taboose_pass.py` assertions remain unchanged.
