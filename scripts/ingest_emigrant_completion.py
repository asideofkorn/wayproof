#!/usr/bin/env python3
"""Prepare the combined Emigrant southern/access audit candidate; never publish.

Geometry inputs must be the reviewed responses identified by fixed SHA-256.
Rebuild against pre-batch main with --base; no live acquisition during generation.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
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
from scripts.ingest_emigrant_western import th, node, scope
from scripts.ingest_emigrant_geometry import SERVICE, SOURCE_ID
from scripts.backfill_managed_land_boundaries import PADUS_MANAGEMENT_URL

ROOT=Path(__file__).resolve().parents[1]
CHANGE_ID='wp-20261006-emigrant-completion'
PREFIX='emigrant-completion-'
RETRIEVED=datetime(2026,10,6,20,36,35,tzinfo=timezone.utc)
LAND='wilderness-emigrant'
LAND_SCOPE='scope-emigrant-wilderness'
YOSE='land-yosemite-wilderness'
HOOVER='wilderness-hoover'
MANIFEST='result-emigrant-completion-pretrip-recheck'
ACCESS_MANIFEST='result-emigrant-completion-access-recheck'
SNAPSHOT='geometry/v0/snapshots/usfs-emigrant-completion-routes-20261006.geojson'
BOUNDARY='geometry/v0/snapshots/usgs-padus-emigrant-boundary-20261006.geojson'
PADUS_SOURCE='source-usgs-padus-management-boundaries-20260924'
FS='https://www.fs.usda.gov'
SOURCES={
 'leavitt':(FS+'/r04/humboldt-toiyabe/recreation/leavitt-lake-trailhead','USDA Forest Service'),
 'leavitt-trail':(FS+'/r04/humboldt-toiyabe/recreation/trails/leavitt-lake-trail','USDA Forest Service'),
 'rec-hoover':('https://www.recreation.gov/permits/445856','Recreation.gov / Humboldt-Toiyabe National Forest'),
 'baker':(FS+'/r05/stanislaus/recreation/baker-campground','USDA Forest Service'),
 'deadman':(FS+'/r05/stanislaus/recreation/deadman-campground','USDA Forest Service'),
 'cherry-valley':(FS+'/r05/stanislaus/recreation/cherry-valley-campground','USDA Forest Service'),
 'cherry-lake':(FS+'/r05/stanislaus/recreation/cherry-lake','USDA Forest Service'),
 'cherry-road':(FS+'/r05/stanislaus/alerts/road-closure-forest-road-1n98-due-repairs-cherry-valley-dam-spillway-project','USDA Forest Service'),
 'cherry-road-signed':(FS+'/sites/nfs/files/r05/stanislaus/publication/alerts/STF-16-2026-06%20Chery%20Valley%20Short-Term%20Improvement%20Project%20Road%20Closure%201N98%20Order.pdf','USDA Forest Service'),
 'cherry-order':(FS+'/sites/nfs/files/r05/stanislaus/publication/alerts/STF-16-2025-01%20Signed.pdf','USDA Forest Service'),
 'rec-cherry':('https://www.recreation.gov/camping/campgrounds/234756','Recreation.gov / Stanislaus National Forest'),
 'kennedy-amenities':('https://kennedymeadows.com/amenities.html','Kennedy Meadows Resort & Pack Station'),
 'kennedy-cabins':('https://kennedymeadows.com/sonoracabins.html','Kennedy Meadows Resort & Pack Station'),
 'kennedy-pack':('https://kennedymeadows.com/packtripoptions.html','Kennedy Meadows Resort & Pack Station'),
 'kennedy-faq':('https://kennedymeadows.com/packtripFAQ.html','Kennedy Meadows Resort & Pack Station'),
 'kennedy-rides':('https://kennedymeadows.com/dayrideoptions.html','Kennedy Meadows Resort & Pack Station'),
 'kennedy-ride-faq':('https://kennedymeadows.com/dayrideFAQ.html','Kennedy Meadows Resort & Pack Station'),
 'aspen-home':('https://www.aspenmeadowpackstation.com/','Aspen Meadow Pack Station'),
 'aspen-pack':('https://www.aspenmeadowpackstation.com/index.php/adventures-menu/pack-trips-menu','Aspen Meadow Pack Station'),
 'aspen-inclusive':('https://www.aspenmeadowpackstation.com/index.php/adventures-menu/all-inclusive-trip-menu','Aspen Meadow Pack Station'),
 'aspen-faq':('https://www.aspenmeadowpackstation.com/index.php/faq-menu','Aspen Meadow Pack Station'),
}
EXISTING_SOURCES={
 'map':'source-usfs-emigrant-overview-map','trailheads':'source-usfs-emigrant-trailheads',
 'mileage':'source-usfs-emigrant-mileage-table','permits':'source-usfs-emigrant-permits',
 'alerts':'source-usfs-emigrant-alerts','hoover':'source-usfs-hoover-wilderness',
 'yose-faq':'source-nps-yosemite-wilderness-permit-faq-2026',
 'yose-regs':'source-nps-yosemite-wilderness-regulations',
 'yose-map':'source-nps-yosemite-wilderness-trailheads-map-2022',
 'kennedy-home':'source-operator-emigrant-kennedy-home','brightman':'source-usfs-emigrant-brightman-2020',
 'geometry':SOURCE_ID,'boundary':PADUS_SOURCE,
}
def sid(k):return EXISTING_SOURCES.get(k,'source-'+PREFIX+k)
def cid(k):return 'claim-'+PREFIX+k
def route(k):return 'route-emigrant-'+k
def segment(k):return 'route-segment-'+PREFIX+k
def campground(k):return 'campground-emigrant-'+k

NODES={
 'bourland-mapped-terminus':'Bourland Trail 19E13 mapped terminus',
 'box-chain-junction':'Box Spring–Chain Lakes trail junction',
 'chain-lakes-approach':'Chain Lakes mapped trail approach',
 'shingle-kibbie-junction':'Kibbie Ridge–Kibbie Lake trail junction',
 'kibbie-lake-approach':'Kibbie Lake southwestern trail approach',
 'styx-pass-approach':'Styx Pass mainline approach',
 'boundary-lake-junction':'Huckleberry–Boundary Lake trail junction',
 'lord-meadow-approach':'Lord Meadow mainline approach',
 'huckleberry-southwest-approach':'Huckleberry Lake southwestern mainline approach',
 **{f'leavitt-break-{i}':f'Leavitt Lake Trail source-feature break {i}' for i in range(1,5)},
}
PLACES={
 'chain-lakes':('waterbody-emigrant-chain-lakes','waterbody','Chain Lakes (Emigrant Wilderness)',LAND),
 'kibbie-lake':('waterbody-yosemite-kibbie-lake','waterbody','Kibbie Lake (Yosemite Wilderness)',YOSE),
 'huckleberry-lake':('waterbody-emigrant-huckleberry-lake','waterbody','Huckleberry Lake (Emigrant Wilderness)',LAND),
 'cherry-lake':('waterbody-stanislaus-cherry-lake','waterbody','Cherry Lake',None),
}
def place(k):return PLACES[k][0]
# All graph edges are supported by explicit labeled map connections, not proximity.
TOPOLOGY={
 'bourland':(th('bourland-meadow'),node('bourland-mapped-terminus'),'2010 southern map shows 19E13 from Bourland Meadow trailhead along Bourland Meadow. USFS object 9431238 ends west of the wilderness boundary; no continuation to Chain Lakes is asserted.'),
 'box-start':(th('box-springs'),node('box-chain-junction'),'2010 southern map explicitly connects Box Spring trailhead to the 19E95/19E28 fork; 2012 mileage table names the Chain Lakes Trail destination.'),
 'chain-branch':(node('box-chain-junction'),node('chain-lakes-approach'),'2010 southern map draws 19E28 east from 19E95 to Chain Lakes; the lake approach is distinct from the waterbody and any campsite.'),
 'shingle-start':(th('shingle-springs'),node('shingle-kibbie-junction'),'2010 southern map draws 20E11 north from Shingle Springs to the explicit Kibbie Lake branch; the 2012 table lists the Huckleberry/Kibbie Lake trail junction.'),
 'kibbie-branch':(node('shingle-kibbie-junction'),node('kibbie-lake-approach'),'2010 southern map draws the branch east across the Yosemite boundary to the southwestern Kibbie Lake approach.'),
 'kibbie-styx':(node('shingle-kibbie-junction'),node('styx-pass-approach'),'2010 southern map draws the main 20E11 north along Kibbie Ridge past Lookout Point and Sachse Spring to Styx Pass, distinct from the Kibbie Lake branch.'),
 'styx-boundary-junction':(node('styx-pass-approach'),node('boundary-lake-junction'),'2010 southern map draws the main 20E11 north/east from Styx Pass to the explicit 20E11A Boundary Lake fork.'),
 'boundary-lord':(node('boundary-lake-junction'),node('lord-meadow-approach'),'2010 southern map draws 20E11 northwest from the Boundary Lake branch to Lord Meadow; no Boundary Lake spur is included.'),
 'lord-huckleberry':(node('lord-meadow-approach'),node('huckleberry-southwest-approach'),'2010 southern map draws 20E11 from Lord Meadow north/east through Cherry Creek toward the southwest side of Huckleberry Lake. Shoreline camps and lake spurs are not included.'),
}
LEGS=[('bourland',9431238,0,218),('leavitt-1',9502910,0,133),('leavitt-2',9484495,0,3),('leavitt-3',9431483,0,14),('leavitt-4',9431503,0,3),('leavitt-5',9475574,0,8)]
for i in range(1,6):
 TOPOLOGY[f'leavitt-{i}']=(th('leavitt-lake') if i==1 else node(f'leavitt-break-{i-1}'),node('pct-leavitt-lake-junction') if i==5 else node(f'leavitt-break-{i}'),'USFS Leavitt Lake Trail detail explicitly connects Leavitt Lake Trailhead via trail 22071 to the PCT. Named, continuous source features establish the selected display chain; feature breaks are descriptive graph nodes.')
# name, entry, objective (optional), endpoint, segments, wilderness context.
ROUTES={
 'bourland-mapped-terminus':('Bourland Meadow to mapped trail terminus','bourland-meadow',None,'bourland-mapped-terminus',['bourland'],None),
 'box-springs-chain-lakes':('Box Springs to Chain Lakes','box-springs','chain-lakes','chain-lakes-approach',['box-start','chain-branch'],LAND_SCOPE),
 'shingle-springs-kibbie-lake':('Shingle Springs to Kibbie Lake','shingle-springs','kibbie-lake','kibbie-lake-approach',['shingle-start','kibbie-branch'],'scope-yosemite-wilderness'),
 'shingle-springs-huckleberry-lake':('Shingle Springs to Huckleberry Lake','shingle-springs','huckleberry-lake','huckleberry-southwest-approach',['shingle-start','kibbie-styx','styx-boundary-junction','boundary-lord','lord-huckleberry'],LAND_SCOPE),
 'leavitt-lake-pct-junction':('Leavitt Lake to Pacific Crest Trail junction','leavitt-lake',None,'pct-leavitt-lake-junction',[f'leavitt-{i}' for i in range(1,6)],'scope-wilderness-hoover'),
}
HASHES={'south':'d5fa68faecf9a86a9b51f6a2d446a0264df4c15d3e1591b2e7b4a2bed000377d','north':'83fed12484880c7878c89e77a8bd6c56ea5a021afcb46a7641d5c642f513b744','boundary':'599de56123aff9afed84ff0df7efd34005bb6f03ede10bb4b09c291994b98bb7'}
QUERY={'f':'geojson','where':'1=1','geometry':'-120.00,37.90,-119.65,38.16','geometryType':'esriGeometryEnvelope','inSR':'4326','spatialRel':'esriSpatialRelIntersects','outFields':'objectid,trail_name,trail_no,trail_cn,bmp,emp,segment_length,gis_miles,globalid,admin_org','outSR':'4326','returnGeometry':'true'}
REPLACEMENTS={'gap-emigrant-boundary-geometry','gap-emigrant-route-topology','gap-emigrant-facility-inventory','gap-emigrant-cross-boundary-permits','gap-emigrant-crabtree-geometry-limitations','gap-emigrant-northern-sonora-pass-leavitt-junction-planning'}


def prepare_snapshots(inputs,output):
 raw={}
 for k,p in inputs.items():
  b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==HASHES[k],k;raw[k]=json.loads(b)
 fs={f['properties']['objectid']:f for k in ('south','north') for f in raw[k]['features']}
 assert len(raw['south']['features'])==71 and len(raw['north']['features'])==207
 features=[]
 for key,fid,a,b in LEGS:
  f=fs[fid];cs=f['geometry']['coordinates'];assert f['geometry']['type']=='LineString' and len(cs)==b+1
  features.append({'type':'Feature','geometry':{'type':'LineString','coordinates':cs[a:b+1]},'properties':{'feature_id':PREFIX+key,'source_attributes':f['properties'],'source_vertex_range_inclusive':[a,b],'source_vertex_count':len(cs),'source_geometry_sha256':hashlib.sha256(json.dumps(f['geometry'],sort_keys=True).encode()).hexdigest(),'length_field_scope':'original source feature; not canonical trail mileage'}})
 for a,b in zip(features[1:5],features[2:6]):assert a['geometry']['coordinates'][-1]==b['geometry']['coordinates'][0]
 assert features[-1]['geometry']['coordinates'][-1]==fs[9502156]['geometry']['coordinates'][587]
 from scripts.ingest_emigrant_northern import QUERY as NORTH_QUERY
 payload={'type':'FeatureCollection','wayproof':{'source':SERVICE,'source_id':SOURCE_ID,'classification':'public_domain','publisher':'USDA Forest Service','retrieved_at':RETRIEVED.isoformat(),'normalized_coordinate_reference_system':'EPSG:4326','source_coordinate_reference_system':'EPSG:4269','navigation_grade':False,'query_endpoint':SERVICE+'/query','queries':[{'parameters':QUERY,'feature_count':71,'input_sha256':HASHES['south']},{'parameters':NORTH_QUERY,'feature_count':207,'input_sha256':HASHES['north']}],'processing':'Unaltered contiguous source vertices; no snapping, interpolation, simplification, or computed mileage. Endpoints are descriptive trail assignments, not surveyed parking points.','review_basis':'2010 Emigrant map southern and Leavitt panels; USFS Leavitt Lake trail and trailhead pages. Bourland stops at the dataset terminus, without invented continuation.','junction_match':'9475574 final vertex equals 9502156 vertex 587, the previously published PCT junction.'},'features':features}
 f=next(f for f in raw['boundary']['features'] if f['properties']['OBJECTID']==237112)
 assert (f['properties']['Unit_Nm'],f['properties']['Des_Tp'],f['properties']['Mang_Name'],f['properties']['Category'])==('Emigrant Wilderness','WA','USFS','Designation')
 boundary={'type':'FeatureCollection','wayproof':{'source_id':PADUS_SOURCE,'source_service':PADUS_MANAGEMENT_URL,'classification':'public_domain','retrieved_at':RETRIEVED.isoformat(),'normalized_coordinate_reference_system':'EPSG:4326','navigation_grade':False,'query_parameters':{'where':"Unit_Nm LIKE '%Emigrant%'",'outFields':'*','f':'geojson','outSR':'4326','returnGeometry':'true'},'query_feature_count':7,'reviewed_input_sha256':HASHES['boundary'],'selection_context':'Exact Emigrant Wilderness name, California, USFS, designated Wilderness Area; OBJECTID 237112. Not a fee-ownership boundary.','processing':'Source-normalized coordinates retained without rounding or simplification; accuracy unknown.'},'features':[dict(f,properties={**f['properties'],'feature_id':'padus-management:237112','source_object_id':237112})]}
 for path,data in [(SNAPSHOT,payload),(BOUNDARY,boundary)]:
  target=output/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')


class Builder:
 def __init__(self):self.r=CanonicalRecords();self.inputs=[];self.access=[]
 def entity(self,eid,kind,name):
  self.r.entities.append(Entity(eid,kind,name));self.r.spatial_scopes.append(SpatialScope(scope(eid),kind,eid))
 def claim(self,key,src,text,subject,predicate,value,scopes=None,access=False,time=None,static=False):
  c,o,e=cid(key),'observation-'+PREFIX+key,'evidence-'+PREFIX+key
  self.r.observations.append(Observation(o,sid(src),text,retrieved_at=RETRIEVED,observer='Wayproof primary-source, map and source-feature review'))
  self.r.evidence.append(Evidence(e,o,c));self.r.claims.append(Claim(c,subject,predicate,value,(e,),time,tuple(scopes) if scopes is not None else (scope(subject),)))
  if not static:(self.access if access else self.inputs).append(c)
  return (e,)
 def rel(self,key,a,p,b,ev):self.r.relationships.append(Relationship('relationship-'+PREFIX+key,a,p,b,ev))
 def gap(self,key,question,reason,related,access=False):
  g='gap-'+PREFIX+key;self.r.gaps.append(KnowledgeGap(g,question,tuple(related),reason));(self.access if access else self.inputs).append(g)
 def rule(self,key,claim_key,description,scopes,conditions=()):
  rid='rule-'+PREFIX+key;self.r.rules.append(Rule(rid,cid(claim_key),description,conditions,tuple(scopes)));self.r.requirements.append(Requirement('requirement-'+PREFIX+key,rid,description))


def build_records(base,output):
 b=Builder();r=b.r
 for key,(url,publisher) in SOURCES.items():r.sources.append(Source(sid(key),url,publisher))
 for key,name in [('shingle-springs','Shingle Springs Trailhead'),('leavitt-lake','Leavitt Lake Trailhead')]:
  b.entity(th(key),'trailhead',name)
  ev=b.claim(key+'-identity','map' if key=='shingle-springs' else 'leavitt','2010 map southern panel and 2012 mileage table name Shingle Springs; it is distinct from the lower Cherry Lake/Lake Eleanor access.' if key=='shingle-springs' else 'USFS identifies Leavitt Lake Trailhead and its connection via Leavitt Lake Trail to the PCT; it is distinct from quota entry Leavitt Meadows.',th(key),'trailhead_identity',{'name':name,'confusable_entry':'Lake Eleanor/Cherry Lake lower trailhead' if key=='shingle-springs' else 'Leavitt Meadows','current_access':'unknown'})
  b.rel(key+'-access',th(key),'accesses',LAND,ev if key=='shingle-springs' else b.claim('leavitt-entry-agency','permits','Stanislaus permit page explicitly assigns Leavitt Lake entry for Emigrant, Hoover or Yosemite to Humboldt-Toiyabe National Forest.',th(key),'permit_issuing_agency',{'agency':'Humboldt-Toiyabe National Forest','basis':'entry trailhead','destination_does_not_change_issuer':True},access=True))
 for key,name in NODES.items():b.entity(node(key),'route_node',name)
 for key,(eid,kind,name,land) in PLACES.items():
  b.entity(eid,kind,name)
  ev=b.claim(key+'-identity','map','2010 Emigrant overview labels '+name+'. Resource identity does not designate a campsite, water supply or shoreline access.',eid,'mapped_place_identity',{'name':name,'water_availability':'unknown','individual_campsites':'not established'})
  if land:b.rel(key+'-land',eid,'part_of',land,ev)
 drawable={key for key,*_ in LEGS}
 for key,(name,entry,obj,end,legs,landscope) in ROUTES.items():
  rt=route(key);b.entity(rt,'route',name);draw=all(k in drawable for k in legs)
  ev=b.claim(key+'-profile','leavitt-trail' if entry=='leavitt-lake' else 'map','Explicit named trail connections support '+name+'. This is a descriptive Wayproof approach; the endpoint is a trail node, not a campsite or lake centroid.',rt,'route_description',{'entry_id':th(entry),'end_node_id':node(end),'objective_id':place(obj) if obj else node(end),'name_status':'Wayproof descriptive approach','directionality':'bidirectional mapped trail','display_geometry':'reviewed; not navigation grade' if draw else 'not reviewed','current_conditions':'unknown'})
  b.rel(key+'-start',rt,'starts_at',th(entry),ev);b.rel(key+'-end',rt,'ends_at',node(end),ev)
  if obj:b.rel(key+'-objective',place(obj),'approached_via',rt,ev)
  if landscope:
   land={LAND_SCOPE:LAND,'scope-yosemite-wilderness':YOSE,'scope-wilderness-hoover':HOOVER}[landscope]
   b.rel(key+'-land',rt,'traverses',land,ev)
   b.claim(key+'-jurisdiction','leavitt-trail' if entry=='leavitt-lake' else 'map','The named mapped approach enters or follows this wilderness. This is route planning context, not whole-route containment or exclusive jurisdiction.',rt,'mapped_wilderness_traversal_context',{'wilderness_id':land,'whole_route_containment':False},scopes=(landscope,),static=True)
  for leg in legs:b.rel(key+'-'+leg,segment(leg),'part_of',rt,ev)
  b.claim(key+'-conditions','alerts','Recheck road access, signed orders, trail clearance, crossings and seasonal conditions for this selected approach.',rt,'pretrip_current_conditions_recheck',{'required':True,'current_status':'unknown'})
  limits='Atomic mileage, current trail condition, return itinerary, water and individual campsites are unresolved. '
  if key.startswith('bourland'):limits+='This bounds 19E13 at its reviewed terminus west of the boundary. The source has no continuous connection to Chain Lakes; entry into Emigrant is not asserted.'
  elif key.startswith('box'):limits+='The 2012 guide calls the trail primitive. Parking connection and the complete selected geometry have not been reviewed; no partial route GeoJSON is published.'
  elif key.startswith('shingle'):limits+='The graph follows explicit 2010 map connections; no complete parking-to-objective geometry is published. Boundary-following stretches do not establish exclusive jurisdiction. Confirm permits and rules for all actual crossings.'
  else:limits+='Display starts at the named trail feature near the lake, not the separate trailhead-page coordinate. That official point and map trail start differ; parking geometry is unreviewed. Continuations to Leavitt Peak, Latopie Lake, Emigrant Pass and Yosemite remain outside this bounded route.'
  b.gap(key+'-limits','What remains unresolved for '+name+'?',limits,[cid(key+'-profile'),cid(key+'-conditions')])
 features={f['properties']['feature_id'].removeprefix(PREFIX):f for f in json.loads((output/SNAPSHOT).read_text())['features']}
 digest=hashlib.sha256((output/SNAPSHOT).read_bytes()).hexdigest()
 for key,(start,end,support) in TOPOLOGY.items():
  b.entity(segment(key),'route_segment',key.replace('-',' ').title())
  scopes=tuple(scope(route(k)) for k,v in ROUTES.items() if key in v[4])
  ev=b.claim(key+'-topology','leavitt-trail' if key.startswith('leavitt') else 'map',support+' Atomic distance is unknown; published destination reports are not subtracted and GIS lengths are not promoted.',segment(key),'mapped_route_connector',{'start_node_id':start,'end_node_id':end,'distance_miles':None,'distance_status':'not_printed','route_role':'official_mainline','support':support},scopes=scopes)
  if key in features:
   f=features[key];p=f['properties'];cs=f['geometry']['coordinates'];a=p['source_attributes']
   ev+=b.claim(key+'-geometry','geometry',f'USFS {a["trail_name"]} {a["trail_no"]}, object {a["objectid"]}, globalid {a["globalid"]}; complete contiguous feature, reviewed against map/description. Coordinates are not a surveyed parking point.',segment(key),'reviewed_route_display_geometry',{'geometry_snapshot':{'path':SNAPSHOT,'sha256':digest,'feature_id':p['feature_id']},'start_coordinate':{'longitude':cs[0][0],'latitude':cs[0][1]},'end_coordinate':{'longitude':cs[-1][0],'latitude':cs[-1][1]},'source_feature_id':a['objectid'],'source_globalid':a['globalid'],'source_vertex_range_inclusive':p['source_vertex_range_inclusive'],'coordinate_reference_system':'EPSG:4326','source_coordinate_accuracy':'unknown','navigation_grade':False,'current_route_status':'unknown'},scopes=scopes)
  b.rel(key+'-start',segment(key),'starts_at',start,ev);b.rel(key+'-end',segment(key),'ends_at',end,ev)
  for rt,v in ROUTES.items():
   if v[2] and key==v[4][-1]:b.rel(key+'-resource',segment(key),'provides_access_to',place(v[2]),ev)
 for key,src,miles in [('box-springs-chain-lakes','mileage',2.5),('shingle-springs-kibbie-lake','mileage',4.3),('shingle-springs-huckleberry-lake','mileage',18.3),('leavitt-lake-pct-junction','mileage',1.8),('leavitt-lake-pct-junction','leavitt-trail',1.65)]:
  b.claim(key+'-distance-'+src,src,f'The {"June 2012 mileage table" if src=="mileage" else "USFS trail detail"} reports {miles} miles for {ROUTES[key][0]}; precise endpoint/parking inclusion is not established.',route(key),'published_approach_distance_report',{'reported_miles':miles,'distance_convention':'one way approach' if src=='mileage' else 'trail length','source_edition':'2012-06' if src=='mileage' else 'page updated 2025-07-15','not_atomic_distance':True,'endpoint_precision':'unspecified'})
 b.gap('leavitt-mileage','Why do Leavitt Lake reports differ?','The 2012 PCT/High Emigrant Trail report is 1.8 miles; the current trail detail reports 1.65 miles. Do not select a single precise total or convert either into atomic mileage.',[cid('leavitt-lake-pct-junction-distance-'+s) for s in ['mileage','leavitt-trail']])
 b.claim('boundary','boundary','USGS PAD-US Management Areas exact designated Emigrant Wilderness record 237112, USFS, California, WA, Category Designation. Reviewed bounds match the Emigrant map; geometry is display evidence, not inferred access or ownership.',LAND,'managed_land_boundary_geometry',{'boundary_geometry_snapshot':{'path':BOUNDARY,'sha256':hashlib.sha256((output/BOUNDARY).read_bytes()).hexdigest(),'feature_ids':['padus-management:237112']},'boundary_type':'designated_wilderness_management_area','coordinate_reference_system':'EPSG:4326','source_coordinate_accuracy':'unknown','navigation_grade':False},scopes=(),static=True)
 add_policies(b)
 add_facilities(b)
 add_inventory(b)
 add_operators(b)
 reasons={
 'gap-emigrant-boundary-geometry':'Reviewed PAD-US designated-wilderness display geometry now matches Emigrant Wilderness, OBJECTID 237112. Survey/legal precision, current amendments and exact route-side jurisdiction remain unverified. Polygon overlap does not create access, containment or permission.',
 'gap-emigrant-route-topology':'The eight western approaches from Crabtree, Gianelli, Bell Meadow and six northern approaches are joined by five bounded southern/eastern approaches: Box Springs–Chain Lakes, Bourland mapped terminus, Shingle Springs–Kibbie/Huckleberry and Leavitt Lake–PCT junction. Bourland continuation, Kennedy parking/branch geometry, southern display gaps, deeper lake/pass branches, returns and individual facility spurs remain unresolved; no wilderness-wide route completeness is claimed.',
 'gap-emigrant-facility-inventory':'Coverage includes historical trailhead facilities, Baker/Deadman/Cherry Valley campground reports, 45 individually reviewed Cherry Valley listing pages and Kennedy cabin inventory. Conflicting water/toilet/fee reports, omitted Cherry Valley site 001, individual Baker/Deadman sites, current availability, remote camps and facility connectors remain unresolved. Inventory is not a reservation or operating guarantee.',
 'gap-emigrant-cross-boundary-permits':'Stanislaus, Hoover/Bridgeport and Yosemite entry-agency rules and selected route contexts are represented. Leavitt Lake has no trailhead quota but overnight permits; Leavitt Meadows has quota. South-of-CA120 continuation/addendum wording differs between Hoover booking and NPS outside-origin guidance. Exact jurisdiction along divides, Yosemite-bound issuance logistics, PCT long-distance permits and unmodeled continuations still require agency confirmation.',
 'gap-emigrant-northern-sonora-pass-leavitt-junction-planning':'The Sonora route still ends at the PCT junction. The Leavitt Lake branch now has a separately reviewed route and display chain; no automatic combined return itinerary is asserted. Jurisdiction along the Emigrant/Hoover divide, PCT permit applicability, Leavitt Peak, Dorothy Lake and Yosemite continuations, parking/highway crossing, atomic mileage and current conditions remain unresolved.',
 'gap-emigrant-crabtree-geometry-limitations':'Camp western access remains a descriptive source-feature break, not a lake centroid or campsite. Reviewed Crabtree display geometry and Emigrant PAD-US boundary are published. Source accuracy, current trail alignment and conditions remain unknown; unsnapped Lake Valley mismatch, unreviewed branches, parking/facility connectors and navigation-grade survey remain unresolved.',
 }
 for old in base.gaps:
  if old.gap_id in reasons:r.gaps.append(replace(old,reason=reasons[old.gap_id],question='What boundary precision and exact jurisdiction remain unverified?' if old.gap_id=='gap-emigrant-boundary-geometry' else old.question))
 for mid,ids,topics in [(MANIFEST,b.inputs,['southern route limits','jurisdiction and permit distinctions','published distance reports']), (ACCESS_MANIFEST,b.access,['access roads and dated orders','facility inventory and source conflicts','booking and operator rechecks'])]:
  r.derived_results.append(DerivedResult(mid,'pretrip_recheck',{'required':True,'topics':topics},tuple(ids),'Scoped source reports and linked unknowns; historical inventory and published policies require pre-trip confirmation.'))
 return r


def add_policies(b):
 rt=route('leavitt-lake-pct-junction');rs=(scope(rt),)
 b.claim('leavitt-overnight','leavitt-trail','USFS Leavitt Lake Trail page requires permits for overnight Hoover travel year-round; day hikes do not require them. It refers Bridgeport permits to Recreation.gov.',rt,'overnight_wilderness_permit_required',{'overnight':True,'day_hike_permit_required':False,'season':'year-round','issuing_unit':'Humboldt-Toiyabe National Forest, Bridgeport Ranger District'},scopes=rs)
 b.rule('leavitt-overnight-permit','leavitt-overnight','Obtain and carry the wilderness permit issued for your Leavitt Lake entry; overnight Hoover travel requires it year-round. Confirm the complete itinerary with Bridgeport Ranger District.',rs,(Condition('activity.overnight','equals',True),))
 b.claim('leavitt-food','hoover','Hoover permit page requires approved bear-resistant food canisters and rejects hanging or guarding food. This route is the Bridgeport Leavitt Lake approach; Emigrant food-hanging options do not establish Hoover compliance.',rt,'required_food_storage',{'approved_bear_resistant_canister_required':True,'hanging_allowed':False,'guarding_allowed':False,'scope':'Leavitt Lake route in Bridgeport Hoover'},scopes=rs)
 b.rule('leavitt-food-storage','leavitt-food','Use an approved bear-resistant food canister on the Hoover portion of the Leavitt Lake approach. Hanging or guarding food does not comply.',rs)
 for subject,scopes in [(th('leavitt-lake'),(scope(th('leavitt-lake')),)),(rt,rs)]:
  key='leavitt-entry' if subject.startswith('trailhead') else 'leavitt-route'
  b.claim(key+'-quota','hoover','Hoover page separately lists Leavitt Lake among no-quota trailheads and Leavitt Meadows among quota trailheads. Its generic June 15–October 15 quota statement must be read with that entry list.',subject,'entry_quota_distinction',{'entry':'Leavitt Lake','quota':False,'different_entry_with_quota':'Leavitt Meadows','quota_season_for_quota_entries':'June 15 through October 15','overnight_permit_still_required':True},scopes=scopes,access=subject.startswith('trailhead'))
  b.claim(key+'-booking','rec-hoover','Recreation.gov Hoover permit product 445856 requires a signed printed permit by 10 a.m. Pacific on entry day. The fee section charges $6 reservation plus $8 for each person age 13 or older; all ages count for quota.',subject,'published_permit_booking_process',{'product_id':'445856','reservation_fee_usd':6,'reservation_fee_refundable':False,'per_person_fee_usd':8,'charged_minimum_age':13,'all_ages_count_for_quota':True,'print_deadline':'10:00 Pacific on entry date','signed_physical_copy_required':True,'current_terms':'recheck'},scopes=scopes,access=subject.startswith('trailhead'))
 b.claim('hoover-release','rec-hoover','Hoover quota product describes advance release six months ahead and the other half within three days at 7 a.m. PDT. This release split describes quota inventory, not a new quota on Leavitt Lake.',rt,'quota_entry_booking_schedule',{'applies_to':'quota trailheads, not Leavitt Lake quota-free designation','advance_release':'six months before entry','remaining_share':'one half','remaining_release':'within three days at 7 a.m. PDT','live_availability':'unknown'},scopes=rs)
 b.claim('outside-origin','yose-faq','NPS outside-origin FAQ assigns permits to the agency managing the entry trailhead even when every overnight is inside Yosemite. Cherry Lake and Lake Eleanor are explicit Stanislaus examples. Separate Donohue Pass and Half Dome eligibility still apply.',LAND,'cross_boundary_permit_issuance',{'issuer_basis':'entry trailhead manager','outside_origin_additional_yosemite_permit':'normally not required for continuous itinerary','examples_stanislaus':['Cherry Lake','Lake Eleanor'],'exceptions':['Donohue Pass requires eligible Yosemite permit','Half Dome eligibility is separate']},scopes=(LAND_SCOPE,))
 b.claim('kibbie-issuer','yose-map','NPS wilderness trailheads map Hetch Hetchy inset specifically directs Kibbie Lake and Lake Eleanor permit requests to Stanislaus National Forest.',route('shingle-springs-kibbie-lake'),'permit_issuing_agency',{'agency':'Stanislaus National Forest','destination':'Kibbie Lake','yosemite_quota_not_transferred_from_other_entries':True})
 b.claim('sonora-issuer','permits','Stanislaus permits page assigns Sonora Pass long-distance permits to Summit Ranger Station, contrasting Leavitt Lake on Humboldt-Toiyabe. This does not determine PCTA long-distance permit eligibility.',th('sonora-pass'),'permit_issuing_agency',{'agency':'Stanislaus National Forest','station':'Summit / Sugar Pine Ranger Station','pcta_permit_eligibility':'unresolved'},access=True)
 b.claim('hoover-continuation','rec-hoover','Hoover product allows continuation into neighboring wilderness, but says travel south of CA Highway 120 needs another relevant permit and/or a continuous-trip addendum from the issuing unit depending on itinerary.',rt,'cross_boundary_continuation_condition',{'trigger':'continuing south of CA Highway 120','published_condition':'additional relevant entry permit and/or issuing-unit long-distance continuous-trip addendum','specific_itinerary_decision':'confirm with issuing agency'},scopes=rs)
 b.gap('cross-boundary-continuation','Which permits/addenda cover the complete crossing itinerary?','NPS ordinarily accepts the outside-origin agency permit; Hoover booking adds a specific south-of-CA120 permit/addendum condition. Preserve both instead of promising blanket reciprocity. Confirm itinerary, Donohue/Half Dome eligibility, any PCT permit, and Yosemite-bound issuance/no-self-issue restrictions.',[cid('outside-origin'),cid('hoover-continuation'),cid('kibbie-issuer')])
 b.claim('kibbie-food-dogs','yose-regs','NPS wilderness regulations prohibit pets, require allowed bear-resistant storage and prohibit hanging. These are destination rules even with a Stanislaus-issued permit.',route('shingle-springs-kibbie-lake'),'cross_boundary_destination_rules',{'pets_allowed':False,'food_storage':'allowed bear-resistant canister/pannier/box; food being eaten or prepared may remain within reach of an awake person','hanging_allowed':False,'winter_exception':'consult NPS winter food-storage terms; no general Emigrant hanging permission transfers'})
 b.claim('kibbie-fire','yose-regs','NPS wilderness regulations prohibit campfires within one-quarter mile of Kibbie Lake shoreline; seasonal restrictions may further limit fire.',place('kibbie-lake'),'place_campfire_restriction',{'campfires_allowed':False,'extent':'within 0.25 mile of shoreline','seasonal_recheck_required':True},scopes=(scope(place('kibbie-lake')),scope(route('shingle-springs-kibbie-lake'))))
 for key,src,exceptions in [('faq','yose-faq',['crossing a road on foot or stock','one night at Tuolumne Meadows backpackers campground']),('regs','yose-regs',['crossing a road on foot or stock','one night at Tuolumne Meadows or White Wolf backpackers campground'])]:
  b.claim('yose-continuity-'+key,src,'NPS '+key+' lists continuous-travel exceptions: '+', '.join(exceptions)+'. Vehicle travel or wilderness exit otherwise invalidates the itinerary permit.',route('shingle-springs-kibbie-lake'),'published_continuous_travel_exceptions',{'exceptions':exceptions,'vehicle_travel_invalidates':True,'source_section':key})
 b.gap('yose-continuity','Which backpacker-camp stop preserves a through permit?','NPS FAQ mentions Tuolumne Meadows; regulations include White Wolf as well. Ask NPS about the actual continuous itinerary; neither list establishes campground operation.',[cid('yose-continuity-faq'),cid('yose-continuity-regs')])
 for key in ('bourland-meadow','box-springs'):
  b.claim(key+'-primitive','trailheads','ROG 16-26 April 2012 labels this a primitive trail, with native surface, limited parking, fair overnight camping opportunities and no facilities. These are historical reports.',th(key),'historical_access_inventory',{'source_edition':'2012-04','trail_qualifier':'primitive','surface':'native','parking':'limited','camping_opportunities':'fair','reported_facilities':'none','current_availability':'unknown'},access=True)
  b.claim(key+'-camp-limit','trailheads','ROG 16-26 April 2012 states a one-night limit at all trailheads; this is not current site-specific permission.',th(key),'historical_trailhead_camping_limit',{'source_edition':'2012-04','reported_nights':1,'current_limit':'recheck'},access=True)
  b.claim(key+'-road','trailheads','2012 directions from Summit Ranger District reach 3N01 via Long Barn then 3N16. Box Springs continues via 3N20Y; Bourland parking is the dead end beyond its junction. All road mileages in the guide are approximate.',th(key),'historical_road_access',{'source_edition':'2012-04','roads':['3N01','3N16']+(['3N20Y'] if key=='box-springs' else []),'mileages':'approximate; not modeled as driving route','current_access':'unknown'},access=True)
 b.claim('leavitt-road','leavitt','USFS trailhead page identifies 32077 as a rough road requiring high-clearance four-wheel drive, generally used June–October as weather permits.',th('leavitt-lake'),'reported_vehicle_access',{'road':'32077','required_vehicle':'high-clearance four-wheel drive','reported_season':'June through October, weather and conditions permitting','current_access':'unknown'},access=True)
 b.claim('leavitt-facilities','leavitt','USFS trailhead page reports no restrooms and no site fee; overnight Hoover permits have separate fees. The page permits horse/pack animals.',th('leavitt-lake'),'reported_trailhead_facilities',{'restrooms':False,'site_fee_usd':0,'wilderness_permit_fee_separate':True,'stock_allowed_at_site':True,'current_availability':'recheck'},access=True)
 b.claim('leavitt-location','leavitt','USFS trailhead page gives latitude 38.273405, longitude -119.612353 and elevation 9,670 feet. These are retained separately from the reviewed trail geometry start and the 2012 table elevation of 9,600 feet.',th('leavitt-lake'),'published_location_report',{'latitude':38.273405,'longitude':-119.612353,'reported_elevation_feet':9670,'location_role':'trailhead page point; not substituted for trail start','source_accuracy':'unknown'},access=True)
 for entry in ['bourland-meadow','box-springs','shingle-springs','leavitt-lake']:
  b.claim(entry+'-recheck','leavitt' if entry=='leavitt-lake' else 'alerts','Confirm current roads, closures, parking, facilities and permit pickup before travel. Historical directions and map lines do not establish present access.',th(entry),'pretrip_access_recheck',{'required':True,'current_status':'unknown','topics':['roads and seasonal access','signed orders','permit pickup','parking and facilities']},access=True)
  b.gap(entry+'-access','What access is usable at '+entry.replace('-',' ')+'?','Confirm current vehicle access, primitive trail conditions where applicable, facilities, water and overnight limits. No unreviewed road or parking connector is asserted.',[cid(entry+'-recheck')],access=True)
 cherry_scopes=(scope(place('cherry-lake')),scope(campground('cherry-valley')),scope(th('shingle-springs')))
 b.claim('cherry-shore-order','cherry-order','Signed STF-16-2025-01 p1 and map p2 prohibit camping, cooking, campfire building and fuel storage on National Forest lands at/below or within 100 feet above the 4,702-foot Cherry Lake high-water mark, and on its island. Effective January 27, 2025–December 31, 2026.',place('cherry-lake'),'dated_area_restriction',{'order':'STF-16-2025-01','activities':['camping','cooking','building campfire','storing fuel'],'extent':'National Forest lands at, below or within 100 feet above high-water mark; Cherry Lake island','high_water_elevation_feet':4702,'exemptions':['specifically exempting FS-7700-48 permit','official-duty officer or organized rescue/fire force'],'not_general_campground_closure':True},scopes=cherry_scopes,access=True,time=TemporalScope(date(2025,1,27),date(2026,12,31)))
 b.claim('cherry-road-order','cherry-road-signed','Signed STF-16-2026-06 prohibits being on 1N98 from its 1N14Y junction to its terminus June 1, 2026–May 31, 2027. This is not a blanket closure of 1N04, 1N14Y, Shingle Springs or all Cherry Lake access.',place('cherry-lake'),'dated_road_restriction',{'order':'STF-16-2026-06','road':'1N98','extent':'1N14Y junction to terminus','prohibition':'being on the specified road','exemptions':['specifically exempting FS-7700-48 permit','official-duty officer or organized rescue/fire force'],'effect_on_selected_trailhead_access':'recheck actual approach; not assumed'},scopes=cherry_scopes,access=True,time=TemporalScope(date(2026,6,1),date(2027,5,31)))
 b.claim('cherry-order-recheck','cherry-road','Recheck current Cherry-area signed orders and their maps, including 1N98 and lake-shore restrictions; expiration is not evidence of reopening or permission.',place('cherry-lake'),'pretrip_area_orders_recheck',{'required':True,'current_status':'unknown','do_not_generalize_to_all_access':True},scopes=cherry_scopes,access=True)
 b.gap('cherry-orders','Which Cherry-area restrictions affect this itinerary?','Match the actual roads and proposed camp against current signed maps. The 1N98 closure is bounded; the lake-shore order does not close every campground or the whole region. Expiration does not establish permission.',[cid('cherry-order-recheck')],access=True)


def add_facilities(b):
 for key,name,count in [('baker','Baker Campground',44),('deadman','Deadman Campground',17),('cherry-valley','Cherry Valley Campground',None)]:
  eid=campground(key);b.entity(eid,'campground',name)
  scopes=(scope(eid),scope(th('kennedy-meadows' if key!='cherry-valley' else 'shingle-springs')))
  b.claim(key+'-inventory',key,'USFS campground page identifies '+name+(' with '+str(count)+' sites including two walk-in sites.' if count else ' near Cherry Lake, with a hiking connection to the lake; no precise trailhead connector is established.'),eid,'published_campground_inventory',{'reported_site_count':count,'reported_walk_in_sites':2 if count else 'not specified','individual_sites':'see linked inventory' if not count else 'not individually identified','current_operation':'unknown'},scopes=scopes,access=True)
  b.claim(key+'-season',key,'USFS published season for '+name+' is '+{'baker':'April–early October','deadman':'April–October','cherry-valley':'May–September'}[key]+'. This is a seasonal report, not verified operation.',eid,'published_operating_season',{'reported_season':{'baker':'April–early October','deadman':'April–October','cherry-valley':'May–September'}[key],'current_operation':'recheck'},scopes=scopes,access=True)
  b.claim(key+'-occupancy',key,'USFS restrictions require designated sites, six people per single site and a maximum fourteen-day campground stay.',eid,'published_campground_occupancy',{'single_site_people':6,'stay_limit_days':14,'designated_sites_only':True,'individual_double_site_limits':'see individual inventory'},scopes=scopes,access=True)
  b.claim(key+'-water-summary',key,'USFS '+name+(' summary reports hydrants serving multiple sites.' if count else ' Current Conditions reports no water service and instructs visitors to bring potable water.'),eid,'published_water_service_report',{'section':'overview' if count else 'Current Conditions','reported':'hydrants serving multiple sites' if count else 'no water service; bring potable water','current_flow':'unknown','potability':'not established'},scopes=scopes,access=True)
  b.claim(key+'-water-amenities',key,'USFS '+name+' amenities panel says potable water is not available.',eid,'published_water_service_report',{'section':'amenities','reported':'potable water not available','current_confirmation':'required'},scopes=scopes,access=True)
  for section,reported in [('overview','vault toilets'),('amenities','vault toilets' if key=='deadman' else 'flush toilets')]:
   b.claim(key+'-toilets-'+section,key,'USFS '+name+' '+section+' reports '+reported+'.',eid,'reported_restroom_type',{'section':section,'type':reported,'current_availability':'unknown'},scopes=scopes,access=True)
  b.claim(key+'-fees-table',key,'USFS '+name+' fee panel reports '+('$25 single / $50 '+('group' if key=='baker' else 'double')+', cash only.' if count else '$29 single / $58 double.'),eid,'published_camping_fee',{'section':'fee panel','single_usd':25 if count else 29,'other_usd':50 if count else 58,'other_type':'group' if key=='baker' else 'double','payment':'cash only' if count else 'see booking terms','current_price':'recheck'},scopes=scopes,access=True)
  b.claim(key+'-operator',key,'USFS identifies '+('Kennedy Meadows Resort and Pack Station' if count else 'American Land & Leisure')+' as the permitted campground operator.',eid,'reported_campground_operator',{'operator':'Kennedy Meadows Resort and Pack Station' if count else 'American Land & Leisure','booking_url':SOURCES['rec-cherry'][0] if not count else SOURCES['kennedy-amenities'][0]},scopes=scopes,access=True)
  if count:
   b.claim(key+'-booking','kennedy-amenities','Kennedy operator home page lists Baker and Deadman as first-come, first-served without reservations.',eid,'published_booking_method',{'reservations':False,'method':'first-come, first-served','availability':'unknown'},scopes=scopes,access=True)
   b.claim(key+'-surface-current',key,'USFS current overview reports paved road and dirt-surfaced parking pads.',eid,'reported_parking_surface',{'source_context':'current page, updated 2026-09-15','road':'paved','parking_pads':'dirt'},scopes=scopes,access=True)
   b.claim(key+'-surface-history','brightman','Brightman Recreation Complex ROG 16-53-01 March 2020 p2 reports paved parking pads/spurs at this campground.',eid,'reported_parking_surface',{'source_edition':'2020-03','parking_pads':'paved','present_condition':'unknown'},scopes=scopes,access=True)
  reason='Published hydrant inventory does not establish current flow or potable supply; the amenities panel says no potable water. '
  if key!='deadman':reason+='Overview vault toilets and amenities flush toilets conflict. '
  if count:reason+='The 2020 guide and current page disagree on parking pad surface; individual sites are not enumerated. '
  else:reason+='The page and booking service disagree on water, fees and season; no live campsite availability has been checked. '
  b.gap(key+'-facilities','Which facilities and terms can be relied on at '+name+'?',reason+'Confirm with the operator.',[cid(key+'-'+s) for s in ['inventory','water-summary','water-amenities','toilets-overview','toilets-amenities','fees-table']],access=True)
  b.claim(key+'-referral',key,'Official campground directions place '+name+(' near Kennedy Meadows Trailhead.' if count else ' near Cherry Lake. It is a campground option for the southern access area, not the trailhead itself.'),th('kennedy-meadows' if count else 'shingle-springs'),'nearby_named_facility_recheck',{'campground_id':eid,'walking_connector':'not reviewed','campground_distinct_from_trailhead':True,'booking_availability':'unknown'},access=True)
 b.claim('cherry-lake-facilities','cherry-lake','Cherry Lake manager overview lists boat launch and vault restrooms but no cell, fuel, grocery or water services; its restroom amenities field says information is unavailable. Seasonal road access must be checked.',place('cherry-lake'),'published_lake_facility_report',{'overview_facilities':['boat launch','vault restrooms'],'amenities_restroom_field':'information unavailable','reported_absent_services':['cell','fuel','grocery','water'],'current_operation':'unknown','road_access':'subject to seasonal conditions'},access=True)
 cherry=campground('cherry-valley');cs=(scope(cherry),scope(th('shingle-springs')))
 b.claim('cherry-fees-overview','cherry-valley','The USFS Cherry Valley page overview separately says $41 per night plus fees and taxes, while its fee panel lists $29/$58.',cherry,'published_camping_fee',{'section':'overview','reported_usd_per_night':41,'additional_fees_and_taxes':True,'current_price':'unresolved'},scopes=cs,access=True)
 b.claim('cherry-water-notice','cherry-valley','The same USFS page retains a July 3, 2025 boil-water notice following a positive E. coli sample. No rescission is shown in the reviewed page; no present water-safety conclusion is made.',cherry,'dated_water_advisory_report',{'notice_date':'2025-07-03','reported_hazard':'positive E. coli sample','notice':'boil tap water or use bottled water','rescission_status':'not established','current_service_and_safety':'recheck; bring potable water'},scopes=cs,access=True)
 b.claim('cherry-water-booking','rec-cherry','Recreation.gov Cherry Valley overview says drinking water is available; this conflicts with the manager page no-water-service statement.',cherry,'published_water_service_report',{'section':'booking overview','reported':'drinking water available','current_availability':'unresolved'},scopes=cs,access=True)
 b.claim('cherry-site-count','rec-cherry','Recreation.gov overview reports 41 single and five double family sites. Its linked inventory exposes 45 individual pages numbered 002–046; absence of 001 does not establish closure or nonexistence.',cherry,'published_site_inventory_count',{'reported_single':41,'reported_double':5,'reviewed_individual_listings':45,'listed_site_numbers':'002–046','unmatched_number':'001','unmatched_status':'unknown'},scopes=cs,access=True)
 b.claim('cherry-booking','rec-cherry','Cherry Valley accepts reservations through Recreation.gov and also lists first-come single-family sites and walk-ins payable by cash/check. No electric hookups. The overview discourages trailers/fifth wheels and motorhomes over 24 feet.',cherry,'published_booking_conditions',{'product_id':'234756','reservation_url':SOURCES['rec-cherry'][0],'first_come_sites_reported':True,'first_come_payment':['cash','check'],'electric_hookups':False,'vehicle_advisory':'trailers/fifth wheels discouraged; motorhomes over 24 ft discouraged','availability':'unknown'},scopes=cs,access=True)
 b.gap('cherry-conflicts','What Cherry Valley water, price and inventory can be relied on?','Manager page: no water service plus retained 2025 boil notice; booking page: drinking water available. Manager overview: $41 plus fees/taxes; fee table: $29 single/$58 double. Overview inventory totals 46; only 45 numbered pages were exposed. Confirm water, rates, operation and site 001; do not infer a closed or missing site.',[cid('cherry-'+s) for s in ['fees-overview','water-notice','water-booking','site-count','booking']]+[cid('cherry-valley-fees-table')],access=True)


def add_inventory(b):
 parent=campground('cherry-valley')
 for row in CHERRY_SITES:
  number,rid,kind,people,vehicles,checkout,vehicle,driveway,equipment,note=row
  key='cherry-site-'+number;eid='campsite-emigrant-cherry-valley-'+number
  b.r.sources.append(Source(sid(key),'https://www.recreation.gov/camping/campsites/'+rid,'Recreation.gov / Stanislaus National Forest'))
  b.entity(eid,'family_campsite','Cherry Valley campsite '+number)
  ev=b.claim(key+'-identity',key,'Individual Recreation.gov listing identifies Cherry Valley site '+number+' in loop CHERRY VALLEY, '+kind+'. A listing is not available inventory for particular dates.',eid,'published_campsite_inventory',{'site_number':number,'booking_site_id':rid,'loop':'CHERRY VALLEY','site_type':kind,'availability':'unknown'},access=True)
  b.rel(key+'-parent',eid,'part_of',parent,ev)
  b.claim(key+'-occupancy',key,'Individual listing gives maximum occupancy '+str(people)+' people and '+str(vehicles)+' vehicles.',eid,'published_site_capacity',{'maximum_people':people,'maximum_vehicles':vehicles,'minimum_people':1,'source_scope':'individual site'},access=True)
  b.claim(key+'-timing',key,'Individual listing: check-in 2 p.m.; checkout '+checkout+'.',eid,'published_checkin_checkout',{'checkin':'14:00','checkout':checkout,'current_terms':'recheck'},access=True)
  b.claim(key+'-vehicle',key,'Individual site equipment section: '+equipment+'. Driveway section maximum vehicle length: '+str(vehicle)+', driveway length: '+driveway+'. Keep these separately; do not choose the more permissive limit.',eid,'published_vehicle_fit_reports',{'equipment_section':equipment,'driveway_max_vehicle_length_report':vehicle,'driveway_length_report':driveway,'driveway_length_units':'not explicit in field unless foot mark shown','resolved_vehicle_fit':'unknown','site_note':note},access=True)
  b.gap(key+'-booking','What can be booked and brought to Cherry Valley site '+number+'?','Confirm live availability, exact site terms, campground water/fees and vehicle fit. Equipment-specific trailer lengths can exceed both the driveway report and 24-foot vehicle field; longer listed equipment is not verified permission. Campfire/pet listing flags do not override current orders or Yosemite pet restrictions.',[cid(key+'-identity'),cid(key+'-vehicle')],access=True)

# Reviewed individual Recreation.gov pages; missing fields remain unknown.
CHERRY_SITES = [('002', '92988', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', None, '38', 'Tent', None),
 ('003', '92744', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', None, '42', 'Tent', None),
 ('004',
  '92008',
  'STANDARD NONELECTRIC',
  6,
  1,
  '11:00 AM',
  24,
  '32',
  'Tent RV/Motorhome (Max length: 25 ft.) Trailer (Max length: 24 ft.)',
  None),
 ('005', '92854', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '52', 'Tent RV/Motorhome Trailer (Max length: 60 ft.)', None),
 ('006', '92153', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '30', 'Tent RV/Motorhome Trailer (Max length: 30 ft.)', None),
 ('007', '92570', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '50', 'Tent Trailer (Max length: 50 ft.) RV/Motorhome', None),
 ('008', '92713', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '45', 'Tent RV/Motorhome Trailer (Max length: 45 ft.)', None),
 ('009', '92856', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '38', 'Tent RV/Motorhome Trailer (Max length: 38 ft.)', None),
 ('010', '92166', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '47', 'Tent RV/Motorhome Trailer (Max length: 47 ft.)', None),
 ('011', '92181', 'STANDARD NONELECTRIC', 6, 1, '1:00 PM', 24, '41', 'Tent RV/Motorhome Trailer (Max length: 41 ft.)', None),
 ('012', '92701', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '43', 'Tent RV/Motorhome Trailer (Max length: 43 ft.)', None),
 ('013', '92294', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '47', 'Tent RV/Motorhome Trailer (Max length: 47 ft.)', None),
 ('014', '92499', 'STANDARD NONELECTRIC', 12, 2, '11:00 AM', 24, '46', 'Tent RV/Motorhome Trailer (Max length: 55 ft.)', None),
 ('015', '92815', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '40', 'Tent RV/Motorhome Trailer (Max length: 40 ft.)', None),
 ('016', '92874', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '46', 'Tent RV/Motorhome Trailer (Max length: 70 ft.)', None),
 ('017', '92368', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '41', 'Tent', None),
 ('018', '92586', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '37', 'Tent', None),
 ('019', '92811', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '35', 'Tent', None),
 ('020', '92555', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '30', 'Tent', None),
 ('021', '92130', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '44', 'Tent', None),
 ('022', '92643', 'STANDARD NONELECTRIC', 12, 2, '11:00 AM', 24, "52'", 'Tent RV/Motorhome Trailer (Max length: 61 ft.)', None),
 ('023', '92096', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '50', 'Tent Trailer (Max length: 50 ft.) RV/Motorhome', None),
 ('024', '92591', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '52', 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('025', '92046', 'STANDARD NONELECTRIC', 12, 2, '11:00 AM', 24, "58'", 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('026', '92905', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '50', 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('027', '92931', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '28', 'Tent RV/Motorhome Trailer (Max length: 35 ft.)', None),
 ('028',
  '92057',
  'STANDARD NONELECTRIC',
  6,
  1,
  '11:00 AM',
  24,
  '37',
  'Tent RV/Motorhome Trailer',
  'Site 28 is best suited for pop-ups or tents due to the short site length.'),
 ('029', '92031', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '32', 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('030', '92561', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '37', 'Tent RV/Motorhome Trailer (Max length: 45 ft.)', None),
 ('031', '92187', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '40', 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('032', '92839', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '37', 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('033', '92018', 'STANDARD NONELECTRIC', 12, 2, '11:00 AM', 24, '50', 'Tent RV/Motorhome Trailer (Max length: 65 ft.)', None),
 ('034', '93045', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '28', 'Tent', None),
 ('035', '92987', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '38', 'Tent', None),
 ('036', '92426', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '28', 'Tent', None),
 ('037', '92728', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '30', 'Tent', None),
 ('038', '92842', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '38', 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('039', '92119', 'STANDARD NONELECTRIC', 12, 2, '11:00 AM', 24, '32', 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('040', '93000', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '50', 'Tent Trailer (Max length: 50 ft.) RV/Motorhome', None),
 ('041', '92105', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '38', 'Tent RV/Motorhome Trailer (Max length: 50 ft.)', None),
 ('042', '92484', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '32', 'Tent', None),
 ('043', '92159', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '30', 'Tent', None),
 ('044', '92851', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '48', 'Tent RV/Motorhome Trailer (Max length: 60 ft.)', None),
 ('045', '93731', 'TENT ONLY NONELECTRIC', 6, 1, '11:00 AM', 24, '30', 'Tent', None),
 ('046', '92251', 'STANDARD NONELECTRIC', 6, 1, '11:00 AM', 24, '30', 'Tent RV/Motorhome Trailer (Max length: 40 ft.)', None)]


def add_operators(b):
 kennedy='facility-emigrant-kennedy-resort';aspen='facility-emigrant-aspen-pack-station'
 for eid,name,src,entry in [(kennedy,'Kennedy Meadows Resort & Pack Station','kennedy-home','kennedy-meadows'),(aspen,'Aspen Meadow Pack Station','aspen-home','crabtree')]:
  b.entity(eid,'facility',name)
  b.claim(name.split()[0].lower()+'-operator-identity',src,'Operator website identifies '+name+' and advertises seasonal services. These are operator reports, not confirmed operation or a trail connection.',eid,'reported_operator_services',{'operator':name,'current_operation':'unknown','walking_connector':'not reviewed'},scopes=(scope(eid),scope(th(entry))),access=True)
 b.claim('kennedy-booking','kennedy-home','Kennedy accepts reservations and information requests by phone, 209-965-3911 or 209-965-3900, between 8 a.m. and 7 p.m.; seasonal service requires confirmation.',kennedy,'published_booking_contact',{'phone':['209-965-3911','209-965-3900'],'reported_call_hours':'08:00–19:00','availability':'unknown'},scopes=(scope(kennedy),scope(th('kennedy-meadows'))),access=True)
 b.claim('kennedy-pack-options','kennedy-pack','Kennedy lists all-inclusive trips, extended hire, drop trips and gear-only backpacker support; each has separate minimums and charges. Services require a booking, not inferred access permission.',kennedy,'published_service_options',{'options':['all-inclusive','extended hire','drop trip','backpacker gear support'],'prices':'confirm complete quote including published 10% government fee','availability':'unknown'},access=True)
 b.claim('kennedy-rider-conditions','kennedy-ride-faq','Kennedy day-ride FAQ requires riders at least seven years old and helmets for minors under eighteen; maximum published rider weight is 260 pounds, with special-consideration referral.',kennedy,'published_rider_conditions',{'minimum_age':7,'maximum_reported_weight_lb':260,'weight_exception':'call for special considerations','helmet_required_under_age':18,'current_booking_terms':'confirm'},access=True)
 b.claim('kennedy-lake-ride-mileage','kennedy-rides','Kennedy day-ride page reports Kennedy Lake eight miles one way. Previously ingested operator destination and USFS table reports are 7.5 miles; starts and exact endpoints are not reconciled.',route('kennedy-meadows-kennedy-lake'),'published_approach_distance_report',{'reported_miles':8,'distance_convention':'one way','activity':'guided riding','not_atomic_distance':True,'endpoint_precision':'unspecified'},access=True)
 b.gap('kennedy-ride-mileage','Which Kennedy Lake distance matches the intended start?','The operator ride page says eight miles one way; the operator destinations page and 2012 USFS table say 7.5. Preserve all reports, including the unresolved parking walk, without rewriting any physical segment.',[cid('kennedy-lake-ride-mileage'),'claim-emigrant-northern-kennedy-meadows-kennedy-lake-mileage-mileage-table','claim-emigrant-northern-kennedy-meadows-kennedy-lake-mileage-kennedy-destinations'],access=True)
 b.claim('kennedy-cabin-terms','kennedy-cabins','Cabin booking page requires a one-night deposit, lists 3 p.m. check-in/11 a.m. checkout, adds 12% occupancy tax, and warns prices can change after booking. Dogs must be controlled and cost $5 per dog/night.',kennedy,'published_cabin_booking_terms',{'method':'phone reservation','deposit':'one night','checkin':'15:00','checkout':'11:00','occupancy_tax_percent':12,'dog_fee_usd_per_night':5,'extra_person_fee_usd_per_day':5,'extra_person_qualification':'above reported cabin capacity; confirm allowed occupancy','prices_may_change_after_booking':True,'live_inventory':'unknown'},access=True)
 b.claim('kennedy-cabin-cancellation','kennedy-cabins','Cabin page refund schedule: four weeks prior 100%; two to four weeks 50%; zero to two weeks 0%. Exact cutoff overlap and current terms require confirmation.',kennedy,'published_cancellation_schedule',{'reported_bands':[{'weeks':'4 prior','deposit_refund_percent':100},{'weeks':'2–4','deposit_refund_percent':50},{'weeks':'0–2','deposit_refund_percent':0}],'boundary_interpretation':'confirm exact two/four-week cutoffs'},access=True)
 for number,capacity,price in CABINS:
  key='kennedy-cabin-'+str(number);eid='cabin-emigrant-kennedy-'+str(number)
  b.entity(eid,'cabin_campsite','Kennedy Meadows cabin '+str(number))
  ev=b.claim(key+'-inventory','kennedy-cabins','Operator cabin table row '+str(number)+': capacity '+str(capacity)+', nightly base rate $'+str(price)+'.',eid,'published_cabin_inventory',{'cabin_number':str(number),'reported_capacity':capacity,'base_rate_usd_per_night':price,'category':'sleeper' if number in (1,2,3,5,6,7) else 'furnished','kitchenette_exception':'no kitchenette' if number==3 else None,'rates_exclude_additions':True,'current_price_and_availability':'unknown'},access=True)
  b.rel(key+'-parent',eid,'part_of',kennedy,ev)
 b.gap('kennedy-bookings','Which Kennedy services, cabin prices and terms are current?','Confirm cabins, rides, stock support, actual season and complete charges directly. Existing home/PCT page season and trailhead-fee conflicts remain unresolved. Cabin numbering omits 13; no cabin 13 is inferred. Published capacity plus extra-person fees does not establish an approved larger occupancy.',[cid('kennedy-booking'),cid('kennedy-cabin-terms'),cid('kennedy-pack-options')],access=True)
 b.claim('aspen-season','aspen-home','Aspen advertises June–September operation depending on snowfall, seven days weekly; rides between 8 a.m. and 4 p.m. are reserved by phone 209-965-3402.',aspen,'published_operator_season_booking',{'season':'June–September depending on snowfall','reported_days':'seven days per week','reported_ride_hours':'08:00–16:00','phone':'209-965-3402','live_availability':'unknown'},scopes=(scope(aspen),scope(th('crabtree')),scope(th('gianelli'))),access=True)
 b.claim('aspen-pack-terms','aspen-pack','Aspen pack page advertises spot trips, retained packer trips and drop packs, with a nonrefundable packer-fee deposit and ten percent Forest Service/handling fee. Prices are one way; second packer thresholds are over six riders or over eight pack animals.',aspen,'published_pack_booking_terms',{'options':['spot trip','keep the packer','drop pack'],'deposit':'packer fee; nonrefundable','additional_fee_percent':10,'rates_basis':'one way','second_packer_threshold':{'riders_over':6,'pack_animals_over':8},'quote_and_availability':'confirm'},access=True)
 b.claim('aspen-inclusive','aspen-inclusive','Aspen all-inclusive page lists $300/person/day hiking or $350 riding, ordinarily four people/four days minimum, and 45 pounds personal gear unless arranged otherwise. Personal sleeping equipment remains the guest responsibility.',aspen,'published_all_inclusive_terms',{'usd_per_person_per_day':{'hiking':300,'riding':350},'minimum_people':4,'minimum_days':4,'minimum_exception':'unless arrangements made','gear_limit_lb':45,'gear_exception':'special arrangements at reservation','personal_gear_included':False,'current_quote':'confirm'},access=True)
 b.claim('aspen-group-referral','aspen-faq','Aspen FAQ states maximum group size fifteen and then invites larger groups to call for accommodation. Operator arrangements do not exempt wilderness group limits.',aspen,'operator_group_size_referral',{'stated_maximum':15,'larger_group_wording':'call for possible accommodation','legal_exception_established':False},access=True)
 for key,eid,src in [('kennedy',kennedy,'kennedy-faq'),('aspen',aspen,'aspen-faq')]:
  b.claim(key+'-permit-advice',src,'Operator FAQ says to obtain a Summit Ranger Station permit before arrival, count guides and stock, and confirm after-hours pickup. The manager, not the operator, determines issuing procedures.',eid,'operator_permit_pickup_advice',{'issuer_referral':'Summit / Sugar Pine Ranger Station','guide_and_stock_counts':'include in permit','after_hours':'operator advises calling to confirm box pickup','yosemite_bound_exception':'confirm with managing agency; advice is not self-issue permission'},access=True)
 b.gap('operator-permit-logistics','Do operator arrangements satisfy permits and group rules?','Aspen and Kennedy FAQs discuss after-hours pickup, while Stanislaus has a Yosemite-bound no-self-issue exception. Confirm issuance with the agency and count guides/stock. Aspen larger-group invitation is not legal permission beyond wilderness limits. Operators do not establish water safety or Yosemite dog permission.',[cid('aspen-group-referral'),cid('aspen-pack-terms'),cid('kennedy-pack-options'),cid('aspen-permit-advice'),cid('kennedy-permit-advice')],access=True)


CABINS=[(1,4,150),(2,4,150),(3,3,130),(4,6,230),(5,4,150),(6,4,150),(7,4,150),(8,7,230),(9,10,235),(10,11,250),(11,6,275),(12,4,150),(14,7,250),(15,10,285),(16,12,285),(17,8,265),(18,10,250),(19,9,285),(20,10,285),(21,6,230),(22,6,230)]


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,default=ROOT);p.add_argument('--output',type=Path,default=ROOT)
 for name in ('south','north','boundary'):p.add_argument('--reviewed-'+name,type=Path)
 a=p.parse_args();inputs={k:getattr(a,'reviewed_'+k) for k in HASHES}
 if any(inputs.values()):
  if not all(inputs.values()):p.error('all three reviewed geometry inputs are required together')
  prepare_snapshots(inputs,a.output)
 base=load_canonical(a.base);r=build_records(base,a.output)
 ops=tuple(ChangeOperation(ChangeAction.REPLACE if getattr(record,ident) in REPLACEMENTS else ChangeAction.ADD,kind,getattr(record,ident),f'canonical/v0/{collection}/{getattr(record,ident)}.json','Add combined southern approaches, boundary, entry-policy and facility audit; preserve uncertainty.',evidence_refs=getattr(record,'evidence_ids',()),knowledge_gap_refs=(getattr(record,ident),) if kind=='gap' else ()) for kind,(collection,ident,_) in RECORD_SPECS.items() for record in getattr(r,collection))
 change=ChangeSet(CHANGE_ID,r,summary='Combine five southern/eastern Emigrant approaches with reviewed boundary, jurisdiction-specific planning and campground/operator inventory audit.',operations=ops)
 writes=ChangeSetWriteService(InMemoryCanonicalRepository(base));writes.propose(change,'emigrant-completion-ingestion');errors=writes.validate(CHANGE_ID,'emigrant-validator')
 if errors:raise RuntimeError('\n'.join(errors))
 candidate=writes.prepare(CHANGE_ID,'emigrant-candidate-builder');write_candidate(a.output,candidate,writes.get(CHANGE_ID));print(f'Prepared {len(ops)} records in {CHANGE_ID}; not published.')

if __name__=='__main__':main()
