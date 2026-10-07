#!/usr/bin/env python3
"""Prepare one follow-up Taboose facilities and western-route candidate.

Reads only reviewed local evidence; no fetching, approval or publication.
See docs/ingestion/taboose-depth.md for source dispositions and geometry rebuild.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wayproof.canonical_storage import RECORD_SPECS, load_canonical, write_candidate
from wayproof.schema import (CanonicalRecords, ChangeAction, ChangeOperation, ChangeSet,
    Claim, Condition, DerivedResult, Entity, Evidence, KnowledgeGap, Observation,
    Relationship, Requirement, Rule, Source, SpatialScope, TemporalScope)
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository
from scripts.ingest_taboose_pass import TH, PASS, ROUTE, SEGMENT, ROAD, ROAD_ROUTE, ROAD_SEGMENT, CAMP, WEST, PARK, MANIFEST as BASE_MANIFEST, scope

ROOT=Path(__file__).resolve().parents[1]
CHANGE_ID='wp-20261007-taboose-facilities-west'
MANIFEST='result-taboose-depth-pretrip-recheck'
SNAPSHOT='geometry/v0/snapshots/nps-taboose-west-20261007.geojson'
RETRIEVED=datetime(2026,10,7,1,21,tzinfo=timezone.utc)
PREFIX='taboose-depth-'
JMT='junction-taboose-jmt'
BENCH_JCT='junction-bench-lake-jmt'
BENCH='lake-bench-kings-canyon'
MATHER='place-mather-pass'
PINCHOT='place-pinchot-pass'
ROUTES={'bench':('route-taboose-bench-lake','Taboose trailhead to Bench Lake',BENCH,('pass-jmt','jmt-bench-junction','bench-lake')),
        'mather':('route-taboose-mather-pass','Taboose trailhead to Mather Pass',MATHER,('pass-jmt','mather-pass')),
        'pinchot':('route-taboose-pinchot-pass','Taboose trailhead to Pinchot Pass',PINCHOT,('pass-jmt','jmt-bench-junction','pinchot-pass'))}
SEGMENTS={'pass-jmt':(PASS,JMT,'Taboose Pass to John Muir Trail'),
 'jmt-bench-junction':(JMT,BENCH_JCT,'JMT between Taboose and Bench Lake junctions'),
 'bench-lake':(BENCH_JCT,BENCH,'Bench Lake spur from JMT'),
 'mather-pass':(JMT,MATHER,'JMT north from Taboose junction to Mather Pass'),
 'pinchot-pass':(BENCH_JCT,PINCHOT,'JMT south from Bench Lake junction to Pinchot Pass')}
NPS='https://www.nps.gov/seki/planyourvisit/'
COUNTY='https://www.inyocounty.us/services/parks-recreation/'
GIS='https://services.arcgis.com/0jRlQ17Qmni5zEMr/arcgis/rest/services/'
SOURCES={
 'nps-geometry':('https://irma.nps.gov/DataStore/DownloadFile/601800?Reference=2253434','National Park Service'),
 'nps-map':(NPS+'upload/2026_KingsCanyonNp-Stock-Use-and-Grazing-Regulations-Map_508_Compressed.pdf','National Park Service'),
 'stock-guide':(NPS+'upload/2026_SEKI_Stock_Users_Guide_508.pdf','National Park Service'),
 'grazing':(NPS+'grazing.htm','National Park Service'),
 'food':(NPS+'bear_bc.htm','National Park Service'),
 'boxes':(NPS+'bear_box.htm','National Park Service'),
 'canister-areas':(NPS+'canister-areas.htm','National Park Service'),
 'conditions':(NPS+'trailcond.htm','National Park Service'),
 'county-rules':(COUNTY+'camping-information','Inyo County Parks and Recreation'),
 'county-fees':(COUNTY+'fees-rates','Inyo County Parks and Recreation'),
 'county-camp':(COUNTY+'campgrounds/taboose-creek-campground','Inyo County Parks and Recreation'),
 'booking':('https://www.reserveamerica.com/explore/taboose-creek-campground/INYO/1100013/campsites','ReserveAmerica / Inyo County'),
 'pcta':('https://explore.pcta.org/trailheads/taboose-pass-trailhead','Pacific Crest Trail Association'),
 'county-roads':(GIS+'Maintained_Mileage_System/FeatureServer/0','Inyo County GIS'),
 'county-road-use':('https://gisdata.inyo.gov/pages/conditions-of-use','Inyo County GIS'),
 'road-report':('https://www.inyocounty.us/sites/default/files/2026-08/CURRENT%20ROAD%20UPDATE%20%20%2008.11.26.pdf','Inyo County Public Works'),
 'road-extra':('https://www.inyocounty.us/sites/default/files/2026-08/Additional%20Road%20status%20information%2008.11.26.pdf','Inyo County Public Works'),
 'food-signed':('https://www.fs.usda.gov/sites/nfs/files/r05/inyo/publication/alerts/05-04-50-25-03%20Food%20and%20Refuse%20Storage%20Order.pdf','USDA Forest Service, Inyo National Forest'),
}
# Factual transcription of all 36 separately opened site-detail pages. Measurements
# intentionally retain unspecified units, as displayed; no conversions or fit guarantees.
# site, provider id, driveway entry, max vehicle/equipment/site length, width, waterfront, restroom proximity
SITE_ROWS='''001 1051 Parallel 40 25 300 150
002 1052 Parallel 40 25 300 150
003 1053 Parallel 40 25 360 90
004 1054 Parallel 30 25 375 75
005 1055 Back-In 40 25 390 45
006 1060 Back-In 25 15 420 75
007 1063 Parallel 35 25 450 90
008 1066 Parallel 40 25 480 90
009 1069 Parallel 30 25 510 60
010 1072 Parallel 30 25 540 75
011 1081 Parallel 40 25 570 90
012 1082 Parallel 30 25 600 120
013 1083 Parallel 30 25 630 150
014 1084 Parallel 35 25 660 165
015 1085 Parallel 35 25 1200 180
016 1086 Back-In 60 25 1050 150
017 1087 Back-In 40 25 600 120
018 1088 Parallel 40 25 540 150
019 1089 Parallel 40 25 525 120
020 1090 Back-In 30 15 480 105
021 1091 Pull-Through 35 15 450 60
022 1092 Back-In 30 15 360 75
023 1093 Pull-Through 30 15 300 60
024 1094 Back-In 30 15 120 75
025 1095 Parallel 30 25 120 120
026 1096 Parallel 35 25 90 150
027 1097 Parallel 35 20 90 150
028 1098 Parallel 35 20 120 180
029 1099 Parallel 35 20 135 210
030 1100 Parallel 40 25 150 270
031 1101 Parallel 40 25 135 255
032 1102 Parallel 40 25 120 240
033 1103 Parallel 40 20 105 225
034 1104 Back-In 30 20 90 210
035 1105 Back-In 30 20 135 195
036 1106 Parallel 40 25 150 180'''

def segment(key): return 'route-segment-taboose-west-'+key

def site_id(number): return 'campsite-taboose-creek-'+number

class Builder:
 def __init__(self,base):
  self.base=base; self.r=CanonicalRecords();self.inputs=[];self.sources={};self.replacements=set()
  self.by_url={s.locator:s.source_id for s in base.sources}
  for key,(url,publisher) in SOURCES.items(): self.source(key,url,publisher)
 def source(self,key,url,publisher):
  sid=self.by_url.get(url,'source-'+PREFIX+key);self.sources[key]=sid
  if url not in self.by_url:self.r.sources.append(Source(sid,url,publisher));self.by_url[url]=sid
 def entity(self,eid,kind,name):
  assert not any(e.entity_id==eid for e in self.base.entities),eid
  self.r.entities.append(Entity(eid,kind,name));self.r.spatial_scopes.append(SpatialScope(scope(eid),kind,eid))
 def claim(self,key,src,subject,predicate,value,text,*,scopes=None,time=None,observed=None,recheck=True):
  cid='claim-'+PREFIX+key;oid='observation-'+PREFIX+key;eid='evidence-'+PREFIX+key
  self.r.observations.append(Observation(oid,self.sources[src],text,observed_at=observed,retrieved_at=RETRIEVED,observer='Wayproof primary source, table and visual map review'))
  self.r.evidence.append(Evidence(eid,oid,cid));self.r.claims.append(Claim(cid,subject,predicate,value,(eid,),time,tuple(scopes) if scopes is not None else (scope(subject),)))
  if recheck:self.inputs.append(cid)
  return cid
 def rel(self,key,sub,pred,obj,cid):
  self.r.relationships.append(Relationship('relationship-'+PREFIX+key,sub,pred,obj,('evidence-'+cid.removeprefix('claim-'),)))
 def gap(self,key,question,reason,*related,replace=False):
  gid=('gap-taboose-' if replace else 'gap-'+PREFIX)+key
  self.r.gaps.append(KnowledgeGap(gid,question,tuple(related),reason));self.inputs.append(gid)
  if replace:self.replacements.add(gid)
 def rule(self,key,cid,text,scopes,conditions=()):
  rid='rule-'+PREFIX+key
  self.r.rules.append(Rule(rid,cid,text,tuple(conditions),tuple(scopes)))
  self.r.requirements.append(Requirement('requirement-'+PREFIX+key,rid,text))


def build_records(base,output=ROOT):
 b=Builder(base)
 # Deep inventory is independent of availability and of the distant wilderness trailhead.
 for row in SITE_ROWS.splitlines():
  number,provider,entry,length,width,water,rest=row.split();eid=site_id(number);src='site-'+number
  b.source(src,f'https://www.reserveamerica.com/explore/taboose-creek-campground/INYO/1100013/{provider}/campsite-booking','ReserveAmerica / Inyo County')
  b.entity(eid,'campsite','Taboose Creek campsite '+number)
  inventory=b.claim(src+'-inventory',src,eid,'campsite_inventory',{'number':number,'provider_site_id':provider,'site_type':'Standard Non-Electric','access':'Drive-In','use':'Overnight','reservation_type':'Site-Specific','availability':'unknown'},f'ReserveAmerica individual site {number}, Site Details and heading: numbered standard non-electric drive-in overnight site, site-specific reservations. Calendar availability excluded.')
  b.rel(src+'-part',eid,'part_of',CAMP,inventory);b.rel(src+'-access',CAMP,'provides_access_to',eid,inventory)
  b.claim(src+'-fit',src,eid,'campsite_vehicle_fit',{'driveway_entry':entry,'surface':'Gravel','maximum_vehicle_length':{'value':int(length),'unit':'not stated'},'equipment_length':{'value':int(length),'unit':'not stated'},'site_length':{'value':int(length),'unit':'not stated'},'site_width':{'value':int(width),'unit':'not stated'},'equipment_categories':['RV Site','Tent Site','Trailer Site'],'fit_confirmed':False},f'Site {number} detail table: {entry} gravel driveway; maximum vehicle length, equipment length and site length each {length}; width {width}. Page does not label measurement units. Listed categories RV, tent and trailer; confirm actual fit with operator.')
  b.claim(src+'-capacity',src,eid,'campsite_occupancy_limits',{'minimum_people':1,'maximum_people':6,'maximum_vehicles':2},f'Site {number} detail table lists 1–6 people and maximum two vehicles.')
  b.claim(src+'-accessibility',src,eid,'provider_accessibility_statement',{'ADA_accessible':'Y','provider_statement_only':True,'specific_accessibility_features':'unknown'},f'Site {number} detail table labels ADA Accessible Y; this is the provider label, not an independently surveyed accessible route or facility specification.')
  b.claim(src+'-amenities',src,eid,'campsite_amenities',{'picnic_table':True,'grill':True,'fire_ring':True,'shade':'Partial','waterfront_setting':'Stream','waterfront_report':{'value':int(water),'unit':'not stated','meaning':'provider Waterfront field; no surveyed shoreline access inferred'},'restroom_proximity_report':{'value':int(rest),'unit':'not stated'},'potable_water_at_site':'unknown'},f'Site {number} table lists picnic table, grill, fire ring, partial shade, stream setting; Waterfront {water} and Proximity to Restrooms {rest}, with no displayed units. These numbers do not establish a measured walking route or drinking-water service.')
  b.claim(src+'-times',src,eid,'campsite_checkin_checkout',{'checkin_local':'13:00','checkout_local':'10:00'},f'Site {number} table: check-in 1 PM and checkout 10 AM.')
  b.claim(src+'-pets',src,eid,'campsite_pet_policy',{'pets_allowed':True,'subject_to':'county leash, posted exceptions and vaccination rules'},f'Site {number} detail table labels Pets Allowed Y; county general rules remain applicable.')
 b.claim('booking-window','booking',CAMP,'advance_reservation_window',{'minimum_days_before_arrival':1,'maximum_months_in_advance':9,'availability':'unknown'},'ReserveAmerica expanded Booking Window on October 6 local time: reservations at least one day ahead and up to nine months ahead. Rolling example dates are not a permanent season.')
 b.claim('cancellation-disclosure','booking',CAMP,'reviewed_booking_terms_coverage',{'rates_panel_reviewed':True,'cancellation_deadline':'not stated in reviewed panel','refund_schedule':'not stated in reviewed panel','cancellation_fee':'not stated in reviewed panel'},'Expanded Fees & Cancellations panel supplies the $14 2026 standard non-electric rate and charge exclusions, but no cancellation deadline, refund schedule or cancellation fee. No checkout or transaction performed.')
 stay=b.claim('camp-stay','county-rules',CAMP,'campground_stay_limit',{'maximum_days':15,'within_weeks':6,'per_campground':True,'age_62_and_over':'30-day permit available from park employee or county; not automatic'},'County Camping Information: stay limited to 15 days at one campground in six weeks; a 30-day permit is available to people 62 and older through park staff or the county.')
 pets=b.claim('camp-pets','county-rules',CAMP,'county_campground_pet_restrictions',{'permitted_unless_posted_otherwise':True,'dogs_leashed':True,'rabies_shot_within_years':2,'vaccination_evidence_on_request':True},'County Camping Information: pets permitted unless posted otherwise; dogs leashed, rabies shot within last two years, evidence on request.')
 b.claim('camp-firearms','county-rules',CAMP,'firearm_use_restriction',{'use_prohibited':True,'possession_policy':'not supplied here'},'County Camping Information prohibits use of firearms within campgrounds; does not state a possession prohibition.')
 b.claim('camp-ohv','county-rules',CAMP,'campground_ohv_restriction',{'published_speed_mph':{'less_than':5},'county_rule':'OHV operation allowed in county campgrounds other than Diaz Lake','not_wilderness_permission':True},'County Camping Information permits OHV operation in county campgrounds except Diaz Lake and requires speed under 5 mph. It supplies no permission for adjacent wilderness or other roads.')
 b.claim('camp-waste-service','county-fees',CAMP,'seasonal_waste_service_guidance',{'black_gray_removal':'ask park attendant','season':'spring and summer only','site_hookups':False,'current_service':'unknown'},'County Fees & Rates says black/gray removal service is available in spring/summer through the park attendant; it does not identify an onsite dump station or service schedule at Taboose.')
 b.claim('camp-rv-general','county-rules',CAMP,'general_campground_rv_size_statement',{'all_county_campgrounds_accommodate_feet':30,'most_spaces':'larger units'},'County Camping Information says all campgrounds accommodate 30-foot RVs and most spaces larger units; this does not establish any specific site fit.')
 b.claim('camp-rv-fees','county-fees',CAMP,'general_campground_rv_size_statement',{'all_county_campgrounds_accommodate_feet':45,'most_spaces':'larger units'},'County Fees & Rates says all county campgrounds accommodate 45-foot RVs and most sites even larger units. This differs from 30-foot wording on Camping Information and does not supply units for the individual provider fields.')
 b.gap('camp-rv-claims','Which vehicle dimensions can be used for booking?','County aggregate pages use 30-foot and 45-foot accommodation statements. Individual site provider length values vary 25–60 but omit units. Preserve each statement and confirm the chosen site and maneuvering clearance; do not project aggregate accommodation onto every site.',CAMP,'claim-'+PREFIX+'camp-rv-general','claim-'+PREFIX+'camp-rv-fees')
 b.rule('camp-stay',stay,'Observe county stay limit; obtain applicable extended-stay permit if eligible.',(scope(CAMP),),(Condition('activity.overnight','equals',True),))
 b.gap('camp-depth','What campsite-specific details remain unverified?','All 36 provider site-detail pages are represented. Confirm units and actual vehicle fit, specific ADA features, current availability, cancellation/refund terms and any water-specific fishing restrictions. County overview 35-space count remains in conflict with map and complete 36-site provider inventory.',CAMP,'claim-'+PREFIX+'booking-window','claim-'+PREFIX+'cancellation-disclosure',*[site_id(f'{i:03d}') for i in range(1,37)],replace=True)
 b.gap('camp-count-conflict','Does the campground currently have 35 or 36 sites?','County overview still lists 35 spaces; map labels 1–36 and all 36 individual ReserveAmerica profiles were reviewed, including 036. None is labeled a separate group-site type. This narrows the inventory evidence but does not establish why the county reports 35. No live availability or closure conclusion follows.',CAMP,'claim-taboose-camp-inventory','claim-taboose-camp-map-inventory','claim-'+PREFIX+'site-036-inventory',replace=True)
 b.gap('camp-water-current','Is campground well water available and suitable for drinking now?','County campground page still links the July 30 missed-May-monitoring notice, without a follow-up result. County parks overview did not supply a Taboose follow-up; California Drinking Water Watch retrieval timed out. Current quality and operation remain unknown. Original notice and observation are retained; it is neither a positive contamination result nor a boil-water order.',CAMP,'claim-taboose-camp-water-notice','claim-taboose-camp-well',replace=True)
 # Trailhead and road audit.
 access=(scope(TH),scope(ROAD),scope(ROAD_ROUTE))
 b.claim('parking','pcta',TH,'partner_trailhead_parking',{'location':'roadside where Taboose Creek Road ends at trailhead','overnight':True,'fee':'Free (PCTA listing)','capacity':'unknown','requires_manager_recheck':True},'PCTA trailhead page Parking and description identify free overnight roadside parking at the road end; no capacity or designated-stall inventory supplied.',scopes=access)
 b.claim('clearance','pcta',ROAD,'partner_vehicle_access_guidance',{'surface':'paved at US 395, then gravel','vehicle_guidance':'generally passenger vehicle accessible','current_clearance':'unknown','not_current_passability_assurance':True},'PCTA Access section labels dirt/gravel and generally passenger vehicle accessible; description says paving at US395 quickly becomes gravel. Preserve generally and reconcile with USFS rough/bumpy description before travel.',scopes=access)
 b.claim('trailhead-amenities','pcta',TH,'partner_trailhead_amenities',{'published_amenities':'None available','toilet_or_potable_tap_verified_by_manager':False,'not_campground_inventory':True},'PCTA Amenities says none available at Taboose Pass Trailhead. This partner listing is separate from county campground vault toilets/well and is not a manager facility survey.',scopes=(scope(TH),))
 b.entity('agency-inyo-county-public-works','agency','Inyo County Public Works')
 road=b.claim('road-maintenance','county-roads',ROAD,'published_road_maintenance_inventory',{'road_number':'3022','inyo_name':'TABOOSE CREEK RD','inyo_mms':'Yes','published_from':'3018 Tinnemaha','published_to':"Nat’l Forest Bo (source abbreviation)",'surface':'UNPAVED','ownership_or_easement_determined':False,'exact_jurisdiction_breaks':'unknown'},'County-owned ArcGIS Maintained Mileage System layer 0, query UPPER(inyo_name) LIKE TABOOSE: eight features 9098, 9100, 9121, 9130, 9141, 9143, 9149, 9154 consistently identify MMS 3022, unpaved, Tinnemaha to abbreviated national-forest-boundary endpoint. Maintenance listing does not prove ownership, easement or full-route jurisdiction.',scopes=access)
 b.rel('road-maintainer',ROAD,'maintenance_authority','agency-inyo-county-public-works',road)
 for key,src in [('road-report','road-report'),('road-extra','road-extra')]:
  b.claim(key,src,ROAD,'dated_road_report_review',{'report_date':'2026-08-11','taboose_entry_present':False,'current_taboose_status':'unknown','absence_is_not_open_status':True},'Inyo County August 11, 2026 road status PDF, page 1, reviewed: no Taboose entry. A selective closure report omitting the road does not establish that it is open or passable.',scopes=access,observed=datetime(2026,8,11,tzinfo=timezone.utc),time=TemporalScope(date(2026,8,11),date(2026,8,11)))
 b.gap('access-geometry','What official road geometry and jurisdiction divisions are established?','Official county Centerlines and Maintained Mileage System geometry was matched to named Taboose Creek Road 3022. County GIS terms supply as-is illustrative use but no explicit redistribution license required by repository policy, so no county polyline is shipped. Federal NFS Roads named-TABOOSE query returned no features, not proof of absence. Full US395-to-trailhead line, jurisdiction/easement breaks and precise trailhead turning/parking dimensions remain unverified.',ROAD,TH,road,'claim-taboose-road-directions',replace=True)
 b.gap('trailhead-facilities','What parking, toilets and potable water are available at the trailhead?','PCTA now supplies free overnight roadside parking and an amenities-none statement; USFS confirms absent bear lockers. Parking capacity, designated spaces, current road clearance and manager-verified toilet/tap inventory remain unverified. Campground amenities are two road miles from US395, not trailhead services.',TH,'claim-'+PREFIX+'parking','claim-'+PREFIX+'trailhead-amenities','claim-taboose-trailhead-lockers',replace=True)
 signed=b.claim('signed-food-order','food-signed',ROUTE,'signed_order_metadata',{'order':'05-04-50-25-03','executed_on':'2025-06-17','effective_from':'2025-06-18','effective_through':'2027-06-18','exhibit_A_header':'05-04-50-23-04','internal_exhibit_mismatch_preserved':True},'Signed PDF page 1, visually reviewed: Lesley Yen signed June 17, 2025; effective June 18, 2025–June 18, 2027. Attached Exhibit A pages retain 2023 order headers. This resolves signed-cover dates, not inconsistent attachment labeling.',time=TemporalScope(date(2025,6,18),date(2027,6,18)))
 b.gap('food-order-metadata','Which food-order metadata still needs clarification?','Signed order 05-04-50-25-03 confirms June 18, 2025–June 18, 2027 applicability; attached Exhibit A and alert prose retain older 2023 identifiers/dates. Signed-cover dates are now evidenced, while attachment and webpage discrepancies remain explicit. This does not resolve separate trailhead vehicle-storage guidance.',ROUTE,signed,'claim-taboose-food-storage',replace=True)
 # Western topology: existing east-side physical segment is reused, never duplicated.
 for eid,kind,name in [(JMT,'junction','Taboose Pass / John Muir Trail junction'),(BENCH_JCT,'junction','Bench Lake / John Muir Trail junction'),(BENCH,'lake','Bench Lake (Kings Canyon)'),(MATHER,'pass','Mather Pass'),(PINCHOT,'pass','Pinchot Pass')]:b.entity(eid,kind,name)
 snapshot_bytes=(output/SNAPSHOT).read_bytes();snapshot=json.loads(snapshot_bytes);digest=hashlib.sha256(snapshot_bytes).hexdigest()
 for key,(start,end,name) in SEGMENTS.items():
  eid=segment(key);b.entity(eid,'route_segment',name)
  top=b.claim(key+'-topology','nps-map',eid,'mapped_route_connector',{'start_node_id':start,'end_node_id':end,'distance_miles':None,'distance_status':'not_published_on_reviewed_map','directionality':'bidirectional','route_role':'official_mainline','mode':'hiking on mapped maintained trails'},f'2026 Kings Canyon Stock Use and Grazing Regulations map, Taboose/Bench Lake/Upper Basin panel, visually reviewed with NPS maintained-trails From_Junc/To_Junc records: {name}. Mapped trail connections support both directions; no route mileage calculated from coordinates.',scopes=(scope(eid),scope(WEST)),recheck=False)
  b.rel(key+'-start',eid,'starts_at',start,top);b.rel(key+'-end',eid,'ends_at',end,top);b.rel(key+'-park',eid,'traverses',PARK,top)
  f=next(x for x in snapshot['features'] if x['properties']['feature_id']=='nps-taboose-'+key);cs=f['geometry']['coordinates']
  b.claim(key+'-geometry','nps-geometry',eid,'reviewed_route_display_geometry',{'geometry_snapshot':{'path':SNAPSHOT,'sha256':digest,'feature_id':f['properties']['feature_id']},'start_coordinate':{'longitude':cs[0][0],'latitude':cs[0][1]},'end_coordinate':{'longitude':cs[-1][0],'latitude':cs[-1][1]},'coordinate_reference_system':'EPSG:4326','source_coordinate_reference_system':'EPSG:26911','source_coordinate_accuracy':'retained per feature: >=5m and <14m or Unknown','navigation_grade':False,'source_LengthMile_attributes':[x['attributes']['LengthMile'] for x in f['properties']['source_features']],'distance_policy':'Source GIS length fields preserved as reports; no canonical hiking mileage inferred.'},f'NPS 2018 published maintained-trails shapefile complete features for {name}; exact source joins, reorientation and CRS transformation only. Original attributes and hashes retained; topology separately supported by 2026 map.',scopes=(scope(eid),scope(WEST)))
 for key,(rid,name,end,legs) in ROUTES.items():
  b.entity(rid,'route',name)
  c=b.claim(key+'-route','nps-map',rid,'route_description',{'entry_id':TH,'objective_id':end,'directionality':'bidirectional','east_approach_route_id':ROUTE,'western_segment_ids':[segment(x) for x in legs],'current_conditions':'unknown','distance_complete':False},f'Combined reviewed USFS Taboose entry map/description and NPS 2026 map connect the existing trailhead-to-pass approach onward to {name.removeprefix("Taboose trailhead to ")}. This itinerary reuses the published east segment and adds only mapped western trails.',scopes=(scope(rid),scope(ROUTE),scope(WEST)),recheck=False)
  for suffix,sub,pred,obj in [('start',rid,'starts_at',TH),('end',rid,'ends_at',end),('access',TH,'accesses',rid),('approach',end,'approached_via',rid),('east',SEGMENT,'part_of',rid),('west',rid,'traverses',WEST)]:b.rel(key+'-'+suffix,sub,pred,obj,c)
  for leg in legs:b.rel(key+'-'+leg,segment(leg),'part_of',rid,c)
 # Endpoint context does not spread NPS rules onto the original eastern route.
 for eid in [JMT,BENCH_JCT,BENCH,MATHER,PINCHOT]:
  c=b.claim(eid+'-jurisdiction','nps-map',eid,'mapped_jurisdiction',{'park':'Kings Canyon National Park','zone_id':WEST},'2026 NPS map locates this western-route feature within Kings Canyon National Park.',recheck=False)
  b.rel(eid+'-west',eid,'part_of',WEST,c)
 b.rel('bench-spur-lake-access',segment('bench-lake'),'provides_access_to',BENCH,'claim-'+PREFIX+'bench-lake-topology')
 # Route-connected water and camps retain the distinction between geographic access and usable supply.
 b.claim('bench-water','stock-guide',BENCH,'natural_water_planning',{'type':'lake','route_access':'Bench Lake spur','drinking_quality':'unknown','treatment_needed':'check NPS guidance','flow_or_collection_point':'not inventoried'},'2026 NPS stock guide page 14 and map identify Bench Lake at the Bench Lake trail destination. Lake presence does not establish a potable collection point or present water quality.')
 b.entity('camp-bench-lake-stock','backcountry_camp','Bench Lake southwest stock camp')
 c=b.claim('bench-stock-camp','stock-guide','camp-bench-lake-stock','described_backcountry_camp',{'location':'southwest end of Bench Lake','use':'site used by stock parties','availability':'unknown','exact_spur':'not surveyed or modeled'},'2026 NPS Stock Users Guide page 14, 46-4: a campsite used by stock parties at the southwest end of Bench Lake. No precise spur or coordinates supplied.',scopes=(scope(BENCH),scope(WEST),scope('camp-bench-lake-stock')))
 b.rel('bench-stock-part','camp-bench-lake-stock','part_of',BENCH,c)
 b.claim('south-fork-crossing','stock-guide',segment('mather-pass'),'described_route_water_crossing',{'waterway':'South Fork Kings River','trail':'John Muir Trail','elevation_feet':{'just_above':10000},'stock_camps':'one just above 10000 feet at crossing, second on south side','ford_or_bridge':'not established','crossing_safety':'unknown','water_collection':'not inventoried'},'2026 stock guide p14, 46-2 describes JMT crossing of South Fork Kings River and stock camps on both sides; map places the crossing on the northward JMT approach. Exact crossing coordinates, bridge/ford configuration and current conditions are not supplied.',scopes=(scope(segment('mather-pass')),scope(ROUTES['mather'][0])))
 for key,eid,value,text in [
  ('taboose-meadow',WEST,{'forage_area':'46-5','grazing_exclusion_acres':12,'exclusion_elevation_feet_in_guide':10920,'stock_camps_in_described_area':False,'drift_fences_in_described_area':False},'46-5: large wet alpine meadow between JMT and Taboose Pass; 12-acre wet meadow at 10,920 feet closed to grazing; no stock camps or drift fences. Existing general webpage rounds elevation to 11,000 feet; do not use either as a surveyed boundary.'),
  ('bench-forage',BENCH,{'forage_area':'46-4','quality':'Poor','suitable_overnight_feed':'less than five head (guide quality definition)','maximum_grazing_stock_per_party':20,'maximum_grazing_nights_per_party':14},'46-4: poor and very limited forage; 20 stock/14 nights per-party table limits. Guide p3 defines Poor as overnight feed for parties under five head.'),
  ('bench-southwest-stock',BENCH,{'forage_area':'47-5','all_stock_access':'closed','reason':'no maintained trails'},'47-5 meadows southwest of Bench Lake closed to all stock access; no maintained trails.'),
  ('marjorie-water',segment('pinchot-pass'),{'forage_area':'46-6','lake':'Lake Marjorie','forage':'Poor','stock_camps_in_described_area':False,'drift_fences_in_described_area':False,'water_collection_spur':'unknown'},'46-6 Lake Marjorie, along southward JMT corridor on map: very limited meadow; no stock camps or drift fences. Lake proximity does not establish a collection spur.')]:
  b.claim(key,'stock-guide',eid,'stock_area_planning',value,'2026 NPS Stock Users Guide p14, with p3 definitions and 2026 grazing map: '+text)
 b.claim('bench-annual-capacity','nps-map',BENCH,'annual_stock_grazing_capacity',{'forage_area':'46-4','annual_capacity_stock_nights':28,'not_per_party_limit':True,'remaining_capacity':'unknown'},'2026 Kings Canyon stock map labels 46-4 Bench Lake 28sn; legend defines total grazing rights in a season. This is separate from the guide per-party limit and does not establish remaining capacity.')
 b.claim('food-season-main','food',WEST,'published_canister_zone_season',{'named_zone_season':'May 1 through October 31','taboose_zone_membership':'not determined'},'NPS Wilderness Food Storage page names May 1 through October 31 for required-container areas; this observation does not classify this corridor into one of them.')
 b.claim('food-season-boundary','canister-areas',WEST,'published_canister_zone_season',{'rae_lakes_zone_season':'Friday before Memorial Day through October 31','taboose_zone_membership':'not determined'},'NPS linked boundary page retains Friday before Memorial Day through October 31 for Rae Lakes Loop, differing from the main food page; old Kearsarge notice also retained.')
 b.claim('stock-opening','grazing',WEST,'seasonal_grazing_recheck',{'year':2026,'travel_zone':46,'forage_areas':'1–6','published_tentative_opening':'2026-07-15','current_status':'must recheck','permanent_exclusions_still_apply':True},'NPS meadow opening table, updated September 22, 2026: zone 46, forage 1–6 Upper South Fork Kings/Above JMT Junction, July 15 tentative opening; all dates subject to change. Not blanket grazing permission.',time=TemporalScope(date(2026,1,1),date(2026,12,31)))
 b.claim('west-food-detail','food',WEST,'wilderness_food_storage_options',{'containers':'highly recommended throughout park','boxes':'if available outside mandatory-container areas; share, no locks or caching','counterbalance':'last resort outside mandatory-container areas when other methods unavailable; suitable trees rare','current_zone_and_equipment_check':True},'NPS Wilderness Food Storage: portable containers highly recommended; boxes conditional on availability outside required-container areas, shared and uncached; counterbalance only outside required areas when other methods unavailable.')
 b.claim('west-box-inventory','boxes',WEST,'food_box_inventory_review',{'taboose_or_bench_named_in_list':False,'actual_box_presence':'unknown','do_not_rely_on_boxes':True},'NPS Locations of Food Storage Boxes reviewed: no Taboose or Bench Lake listing. Page warns boxes may be full or removed. Absence from listing is not a verified no-box inventory.')
 b.gap('west-food-zone','What exact container rules apply to the western itinerary?','Food page names May 1–October 31 for mandatory-container zones; linked boundary page retains Friday-before-Memorial-Day wording and older notice text. No blanket zone classification is inferred for Taboose/Bench/Mather/Pinchot. Carry an approved container where no compliant box/tree alternative exists; confirm current zone boundaries, dates and equipment approval with NPS.',WEST,'claim-'+PREFIX+'west-food-detail','claim-taboose-west-food')
 for key,cid,text,conditions in [
  ('west-permit','claim-taboose-west-overnight-permit','Carry the signed overnight wilderness permit; continuous Inyo-entry trips follow the entry-agency permit policy.',(Condition('activity.overnight','equals',True),)),
  ('west-food','claim-taboose-west-food','Use NPS-compliant food storage; approved container required without a compliant box or trees. Recheck mandatory zones.',()),
  ('west-camping','claim-taboose-west-camping','Use durable campsites and comply with NPS water setbacks; do not camp in meadows.',(Condition('activity.overnight','equals',True),)),
  ('west-fire','claim-taboose-west-fire','No campfires above 10000 feet in Kings Canyon; check additional current restrictions.',()),
 ]:b.rule(key,cid,text,(scope(WEST),),conditions)
 b.claim('west-conditions','conditions',WEST,'pretrip_current_conditions_recheck',{'topics':['Taboose Pass','JMT Mather and Pinchot passes','South Fork Kings crossing','Bench Lake spur','snow','trail damage','water'],'current_status':'unknown'},'NPS trail conditions page is the official recheck source for the newly modeled western itineraries. Historical mapped trails and a previous Taboose report do not establish present conditions.')
 b.gap('western-scope','What western route coverage and limits are now available?','Mapped hiking topology now reaches Bench Lake, Mather Pass and Pinchot Pass from the existing Taboose trailhead via JMT junctions, with unmodified-source NPS display geometry and scoped park rules. Distances remain unknown where only GIS lengths exist. Exact camp/water spurs, ranger-station access, any historical map alternate not corroborated by 2026 map, full stock suitability and routes beyond these endpoints remain unmodeled.',WEST,*[x[0] for x in ROUTES.values()],*['claim-'+PREFIX+k+'-route' for k in ROUTES],replace=True)
 b.gap('western-facility-spurs','How are individual camps, water and ranger services reached?','Bench Lake trail reaches the lake; southwest stock camp is described but no exact access spur is evidenced. South Fork crossing camps and Lake Marjorie water are described, not mapped as precise facilities. Bench Lake ranger station is mapped but service season, occupancy, toilet/water access and spur remain unknown. Do not assume a staffed station, developed toilet, food box or safe crossing.',WEST,BENCH,'camp-bench-lake-stock',segment('mather-pass'),segment('pinchot-pass'))
 b.gap('western-geometry','How precise are western route geometry and mileage?','NPS 2018 dataset has feature edits from 2006–2014, 5–14m or unknown accuracy, and an inconsistent Pinchot Pass South label for the seven-vertex connector between the two JMT junctions. Its endpoints and 2026 map support the connection; original attributes retained. Source LengthMile values are not promoted to hiking distances. NPS and USFS Taboose endpoints differ and are not snapped. Use current navigation sources.',WEST,*[segment(k) for k in SEGMENTS])
 base_manifest=next(x for x in base.derived_results if x.result_id==BASE_MANIFEST)
 b.r.derived_results.append(DerivedResult(MANIFEST,'pretrip_recheck',{'required':True,'topics':['individual campsite fit and booking','water monitoring','road clearance and jurisdiction','source conflicts','western route conditions','park restrictions and stock conditions']},tuple(dict.fromkeys((*base_manifest.input_ids,*b.inputs))),'Project original and follow-up evidence onto actual campground, access, east or west scopes; missing current information is not clearance.'))
 return b.r,b.replacements


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT);a=p.parse_args()
 base=load_canonical(a.base);records,replacements=build_records(base,a.output)
 ops=tuple(ChangeOperation(ChangeAction.REPLACE if getattr(rec,ident) in replacements else ChangeAction.ADD,kind,getattr(rec,ident),f'canonical/v0/{collection}/{getattr(rec,ident)}.json','Deepen Taboose campsite inventory, access evidence and western routes while retaining uncertainty.',evidence_refs=getattr(rec,'evidence_ids',()),knowledge_gap_refs=(getattr(rec,ident),) if kind=='gap' else ()) for kind,(collection,ident,_) in RECORD_SPECS.items() for rec in getattr(records,collection))
 change=ChangeSet(CHANGE_ID,records,summary='Deepen Taboose facilities and connect west to Bench Lake, Mather Pass and Pinchot Pass with scoped planning evidence.',operations=ops)
 svc=ChangeSetWriteService(InMemoryCanonicalRepository(base));svc.propose(change,'taboose-depth-ingestion');errors=svc.validate(CHANGE_ID,'taboose-depth-validator')
 if errors:raise RuntimeError('\n'.join(errors))
 candidate=svc.prepare(CHANGE_ID,'taboose-depth-builder');write_candidate(a.output,candidate,svc.get(CHANGE_ID));print(f'Prepared {len(ops)} operations; not published.')

if __name__=='__main__':main()
