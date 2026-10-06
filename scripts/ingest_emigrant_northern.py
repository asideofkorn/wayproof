#!/usr/bin/env python3
"""Prepare northern Emigrant approaches and access evidence, without publication.

Regenerate against pre-batch main with --base. Only the reviewed USFS response
may be supplied to --reviewed-input; this builder performs no remote retrieval.
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
    Claim, DerivedResult, Entity, Evidence, KnowledgeGap, Observation, Relationship,
    Source, SpatialScope, TemporalScope)
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository
from scripts.ingest_emigrant_geometry import SERVICE, SOURCE_ID
from scripts.ingest_emigrant_western import th, node, scope

ROOT = Path(__file__).resolve().parents[1]
CHANGE_ID = 'wp-20261006-emigrant-northern-coverage'
SNAPSHOT = 'geometry/v0/snapshots/usfs-emigrant-northern-routes-20261006.geojson'
MANIFEST = 'result-emigrant-northern-pretrip-recheck'
ACCESS_MANIFEST = 'result-emigrant-northern-access-recheck'
LAND = 'wilderness-emigrant'
RETRIEVED = datetime(2026, 10, 6, 15, 34, 28, tzinfo=timezone.utc)
GEOMETRY_RETRIEVED = '2026-10-06T15:14:14+00:00'
QUERY = {'f':'geojson', 'where':'1=1', 'geometry':'-119.98,38.20,-119.52,38.37',
    'geometryType':'esriGeometryEnvelope', 'inSR':'4326', 'spatialRel':'esriSpatialRelIntersects',
    'outFields':'objectid,trail_name,trail_no,trail_cn,bmp,emp,segment_length,gis_miles,globalid,admin_org',
    'outSR':'4326', 'returnGeometry':'true'}
FS = 'https://www.fs.usda.gov/sites/nfs/files/r05/stanislaus/publication/'
SOURCES = {
 'brightman-2020': FS + 'Brightman%20Flat%20ROG.pdf',
 'horse-camping-2020': FS + 'Horse%20Camping%20ROG.pdf',
 'northern-road-order': FS + 'alerts/STF-16-2026-07%20Motor%20Vehicle%20Use%20Map%20Season%20Of%20Use%20Closure%20Extension%20%28Executed%20With%20Maps%29.pdf',
 'northern-road-alert': 'https://www.fs.usda.gov/r05/stanislaus/alerts/stanislaus-national-forest-extends-seasonal-mvum-closure-two-high-elevation',
 'kennedy-home': 'https://kennedymeadows.com/index.html',
 'kennedy-pct': 'https://kennedymeadows.com/sonoraPCThikers.html',
 'kennedy-destinations': 'https://kennedymeadows.com/packtripdestinations.html',
}

def source(key):
    return ('source-operator-emigrant-' if key.startswith('kennedy-') else 'source-usfs-emigrant-') + key

def route(key): return 'route-emigrant-' + key

def segment(key): return 'route-segment-emigrant-northern-' + key

RESOURCES = {
 'kennedy-lake': ('waterbody-emigrant-kennedy-lake', 'waterbody', 'Kennedy Lake (Emigrant Wilderness)'),
 'relief-reservoir': ('waterbody-emigrant-relief-reservoir', 'waterbody', 'Relief Reservoir (Emigrant Wilderness)'),
 'waterhouse-lake': ('waterbody-emigrant-waterhouse-lake', 'waterbody', 'Waterhouse Lake (Emigrant Wilderness)'),
 'cooper-meadow': ('place-emigrant-cooper-meadow', 'meadow', 'Cooper Meadow (Emigrant Wilderness)'),
 'eagle-pass': ('pass-emigrant-eagle', 'mountain_pass', 'Eagle Pass (Emigrant boundary)'),
}
def place(key): return RESOURCES[key][0]

NODES = {
 'kennedy-trail-start': 'Kennedy Meadows trail start at south end of main road',
 'kennedy-lake-junction': 'Kennedy Lake–Huckleberry trail junction',
 'kennedy-lake-west-approach': 'Kennedy Lake western trail approach',
 'relief-east-approach': 'Relief Reservoir eastern mainline approach',
 'waterhouse-trail-end': 'Waterhouse Lake mapped trail terminus',
 'cooper-meadow-junction': 'Cooper Meadow–Eagle Creek trail junction',
 'eagle-display-break': 'Eagle Creek Trail source-feature break',
 'eagle-pass-approach': 'Eagle Pass northern boundary approach',
 'pct-sonora-break-1': 'PCT source-feature break south of Sonora Pass 1',
 'pct-sonora-break-2': 'PCT source-feature break south of Sonora Pass 2',
 'pct-sonora-break-3': 'PCT source-feature break south of Sonora Pass 3',
 'pct-sonora-break-4': 'PCT source-feature break south of Sonora Pass 4',
 'pct-leavitt-lake-junction': 'PCT–Leavitt Lake Trail junction',
}
# key, feature id, inclusive source vertex range, graph endpoints, reviewed support.
# Interior vertices are descriptive display assignments, not surveyed point data.
LEGS = (
 ('waterhouse',9428140,0,147,th('waterhouse'),node('waterhouse-trail-end'),'19E31 from the mapped Waterhouse trailhead to its named lake trail terminus'),
 ('coyote-cooper',9430353,0,422,th('coyote-meadow'),node('cooper-meadow-junction'),'20E15 from the mapped Coyote trailhead through the wilderness to its explicit 20E08 junction in Cooper Meadow'),
 ('eagle-start',9430941,254,438,th('eagle-meadow'),node('eagle-display-break'),'20E08 south from its road crossing at the mapped Eagle Meadow trailhead; display start is not a parking centroid'),
 ('eagle-pass',9430469,0,77,node('eagle-display-break'),node('eagle-pass-approach'),'20E08 to the northern approach at the Eagle Pass boundary saddle; no southern descent included'),
 ('pct-south-1',9501224,0,60,th('sonora-pass'),node('pct-sonora-break-1'),'PCT south from Highway 108; display begins on the south side, not at northern parking'),
 ('pct-south-2',9510733,0,560,node('pct-sonora-break-1'),node('pct-sonora-break-2'),'PCT south, continuous named trail feature with exact shared endpoint'),
 ('pct-south-3',9513460,0,39,node('pct-sonora-break-2'),node('pct-sonora-break-3'),'PCT south, continuous named trail feature with exact shared endpoint'),
 ('pct-south-4',9511588,0,781,node('pct-sonora-break-3'),node('pct-sonora-break-4'),'PCT south past Leavitt Peak on the mapped mainline; no summit or Latopie Lake spur inferred'),
 ('pct-south-5',9502156,0,587,node('pct-sonora-break-4'),node('pct-leavitt-lake-junction'),'PCT south to the explicitly mapped Leavitt Lake Trail 22071 junction; named branch feature 9475574 ends at this exact vertex'),
)
TOPOLOGY_ONLY = (
 ('kennedy-parking-start', th('kennedy-meadows'), node('kennedy-trail-start'), 'traveler-2023', 'Traveler 2023 p10 Relief Reservoir entry explicitly places the trail start at the south end of the main road, half a mile from the Kennedy trailhead parking lot. The connecting walk is described but its geometry is not reviewed.'),
 ('kennedy-start-junction', node('kennedy-trail-start'), node('kennedy-lake-junction'), 'overview-map', '2010 overview northern panel shows the trail south from Kennedy Meadows over the footbridges on Huckleberry Trail 20E11 to the named Kennedy Lake Trail 21E03 branch.'),
 ('kennedy-lake-branch', node('kennedy-lake-junction'), node('kennedy-lake-west-approach'), 'overview-map', '2010 overview northern panel explicitly draws 21E03 east along Kennedy Creek to Kennedy Lake. The selected endpoint is the western trail approach, not the lake centroid or an asserted campsite.'),
 ('relief-approach', node('kennedy-lake-junction'), node('relief-east-approach'), 'overview-map', '2010 overview northern panel draws 20E11 south past the Kennedy Lake branch along the east side of Relief Reservoir. The selected endpoint is an eastern mainline approach; no shoreline spur is asserted.'),
)
# name, entry, resource or None, end, ordered physical segments, enters Emigrant.
ROUTES = {
 'kennedy-meadows-kennedy-lake': ('Kennedy Meadows to Kennedy Lake','kennedy-meadows','kennedy-lake','kennedy-lake-west-approach',['kennedy-parking-start','kennedy-start-junction','kennedy-lake-branch'],True),
 'kennedy-meadows-relief-reservoir': ('Kennedy Meadows to Relief Reservoir','kennedy-meadows','relief-reservoir','relief-east-approach',['kennedy-parking-start','kennedy-start-junction','relief-approach'],True),
 'waterhouse-waterhouse-lake': ('Waterhouse Trailhead to Waterhouse Lake','waterhouse','waterhouse-lake','waterhouse-trail-end',['waterhouse'],True),
 'coyote-cooper-meadow': ('Coyote Meadow to Cooper Meadow','coyote-meadow','cooper-meadow','cooper-meadow-junction',['coyote-cooper'],True),
 'eagle-meadow-eagle-pass': ('Eagle Meadow to Eagle Pass','eagle-meadow','eagle-pass','eagle-pass-approach',['eagle-start','eagle-pass'],False),
 'sonora-pass-leavitt-junction': ('Sonora Pass to Leavitt Lake Trail junction','sonora-pass',None,'pct-leavitt-lake-junction',['pct-south-1','pct-south-2','pct-south-3','pct-south-4','pct-south-5'],True),
}
REPLACEMENTS = {'gap-emigrant-route-topology', 'gap-emigrant-facility-inventory'}


def snapshot_from_reviewed(raw):
    features = {f['properties']['objectid']:f for f in raw['features']}
    assert len(features) == len(raw['features']) == 207
    assert features[9475574]['geometry']['coordinates'][-1] == features[9502156]['geometry']['coordinates'][587]
    out=[]
    for key,fid,start,end,*_ in LEGS:
        f=features[fid];guid,count,trail=EXPECTED[fid]
        assert f['properties']['globalid']==guid and f['properties']['trail_no']==trail
        assert f['geometry']['type']=='LineString' and len(f['geometry']['coordinates'])==count
        coords=f['geometry']['coordinates'][start:end+1]
        out.append({'type':'Feature','geometry':{'type':'LineString','coordinates':coords},'properties':{
            'feature_id':'usfs-emigrant-northern-'+key,'source_attributes':f['properties'],
            'source_vertex_range_inclusive':[start,end],'source_vertex_count':count,
            'source_geometry_sha256':hashlib.sha256(json.dumps(f['geometry'],sort_keys=True).encode()).hexdigest(),
            'xy_accuracy':'unknown; coordinate digits are not an accuracy statement',
            'length_field_scope':'whole original source feature, not the selected slice'}})
    branch=features[9475574]
    return {'type':'FeatureCollection','wayproof':{'source':SERVICE,'source_id':SOURCE_ID,
        'publisher':'USDA Forest Service','classification':'public_domain','retrieved_at':GEOMETRY_RETRIEVED,
        'reviewed_at':RETRIEVED.isoformat(),'query_endpoint':SERVICE+'/query','query_parameters':QUERY,
        'query_feature_count':207,'source_coordinate_reference_system':'EPSG:4269',
        'normalized_coordinate_reference_system':'EPSG:4326','navigation_grade':False,
        'processing':'Contiguous source vertices; no snapping, rounding, interpolation, simplification or mileage calculation.',
        'review_basis':'2010 Emigrant geospatial overview northern panel; 2012 trailhead guide; 2018 hiking guide; 2023 Traveler. Display endpoints are descriptive assignments, not official point features.',
        'junction_corroboration':{'source_attributes':branch['properties'],'source_geometry':branch['geometry'],
            'source_geometry_sha256':hashlib.sha256(json.dumps(branch['geometry'],sort_keys=True).encode()).hexdigest(),
            'use':'Leavitt Lake branch identity and exact endpoint join only; branch is not a route segment'},
        'excluded_geometry':'Kennedy routes: parking connector not reviewed; 21E03 and 20E11 branch coordinates disagree by about 45 metres. Overlapping multipart PCT jurisdiction fragments and motor/winter trails not selected. No routes to Leavitt Lake, Latopie Lake or Leavitt Peak are implied.'},'features':out}


def build_records(base, snapshot, digest):
    r=CanonicalRecords();inputs=[];access_inputs=[]
    for key,url in SOURCES.items():
        r.sources.append(Source(source(key),url,'Kennedy Meadows Resort & Pack Station' if key.startswith('kennedy-') else 'USDA Forest Service, Stanislaus National Forest'))
    def entity(eid,kind,name):
        r.entities.append(Entity(eid,kind,name));r.spatial_scopes.append(SpatialScope(scope(eid),kind,eid))
    def claim(key,src,text,subject,predicate,value,scopes=None,access=False,temporal=None):
        cid,oid,evid=('claim-emigrant-northern-'+key,'observation-emigrant-northern-'+key,'evidence-emigrant-northern-'+key)
        r.observations.append(Observation(oid,SOURCE_ID if src=='geometry' else source(src),text,
            retrieved_at=datetime.fromisoformat(GEOMETRY_RETRIEVED) if src=='geometry' else RETRIEVED,
            observer='Wayproof primary-source text, geospatial map and named-feature review'))
        r.evidence.append(Evidence(evid,oid,cid))
        r.claims.append(Claim(cid,subject,predicate,value,(evid,),temporal_scope=temporal,spatial_scope_ids=scopes or (scope(subject),)))
        (access_inputs if access else inputs).append(cid);return (evid,)
    def rel(key,a,p,b,ev): r.relationships.append(Relationship('relationship-emigrant-northern-'+key,a,p,b,ev))
    def gap(key,question,reason,related,access=False):
        gid='gap-emigrant-northern-'+key;r.gaps.append(KnowledgeGap(gid,question,tuple(related),reason));(access_inputs if access else inputs).append(gid)
    def cid(key): return 'claim-emigrant-northern-'+key
    for key,name in NODES.items():entity(node(key),'route_node',name)
    for key,(eid,kind,name) in RESOURCES.items():
        entity(eid,kind,name)
        ev=claim(key+'-identity','overview-map','2010 Emigrant overview northern panel names '+name+'. The resource remains distinct from its selected trail approach; no campsite or water availability is established.',eid,'mapped_place_identity',{'name':name,'resource_geometry':'not imported','campsite_inventory':'unknown','water_availability':'unknown','boundary_status':'boundary pass; no containment asserted' if key=='eagle-pass' else 'mapped in Emigrant Wilderness'})
        if key!='eagle-pass':rel(key+'-land',eid,'part_of',LAND,ev)
    for key,(name,entry,obj,end,legs,enters) in ROUTES.items():
        entity(route(key),'route',name)
        ev=claim(key+'-profile','overview-map','2010 Emigrant map northern panel explicitly draws the selected named trails. '+name+' is a Wayproof descriptive approach, not an official named itinerary. Kennedy parking connection is separately supported by Traveler 2023; the Eagle approach stops at the northern side of the boundary pass.',route(key),'route_description',{'entry_id':th(entry),'objective_id':place(obj) if obj else node(end),'end_node_id':node(end),'directionality':'bidirectional mapped trail','name_status':'Wayproof descriptive approach','source_edition':'2010','current_conditions':'unknown','display_geometry':'not reviewed' if entry=='kennedy-meadows' else 'reviewed, non-navigation-grade','endpoint_status':'trail approach; not campsite or resource centroid'})
        rel(key+'-start',route(key),'starts_at',th(entry),ev);rel(key+'-end',route(key),'ends_at',node(end),ev)
        if enters:
            rel(key+'-land',route(key),'traverses',LAND,ev)
            # TripIntent scope projection reads subject claims, not the generic
            # traverses relationship. Supply the evidenced wilderness context
            # for route-only intents as well as resource objectives. This is
            # not a whole-route containment or exclusive-jurisdiction claim.
            claim(key+'-wilderness-context','overview-map','2010 overview shows this selected approach entering or following Emigrant Wilderness. Sonora PCT follows a jurisdictional divide; Emigrant context does not resolve Hoover permission.',route(key),'mapped_wilderness_traversal_context',{'wilderness_id':LAND,'whole_route_containment':False,'other_jurisdiction_permission':'not established'},scopes=('scope-emigrant-wilderness',))
            inputs.pop()  # Static applicability context, not a cross-route recheck.

        if obj:rel(key+'-objective',place(obj),'approached_via',route(key),ev)
        for leg in legs:rel(key+'-'+leg,segment(leg),'part_of',route(key),ev)
        claim(key+'-conditions','alerts','Check current Forest Service orders and conditions against the selected access and intended itinerary. Historical map connections do not establish current crossings, snow, water, fire restrictions or trail clearance.',route(key),'pretrip_current_conditions_recheck',{'required':True,'current_status':'unknown','topics':['access roads','trail and crossings','water','fire restrictions','snow and closures']})
        reason='The selected approach has a sourced bidirectional graph; atomic mileage, return itinerary, shoreline paths, individual campsites and current conditions remain unknown. Source destination mileages may refer to a different precise endpoint.'
        if entry=='kennedy-meadows':reason+=' No display geometry is published: the parking-to-trail connection is unreviewed and the Kennedy Lake branch has an unsnapped roughly 45-metre source offset. The graph comes from explicit map/guide connections, not coordinate proximity.'
        if entry=='sonora-pass':reason+=' The PCT follows the Emigrant/Hoover divide; this is not a claim that every segment is in Emigrant or that Emigrant permission covers Hoover. Jurisdiction, PCT permit applicability and a continuation to Leavitt Lake, Leavitt Peak, Dorothy Lake or Yosemite need separate review. Parking-to-south-side highway crossing geometry is not included.'
        if entry=='eagle-meadow':reason+=' The route ends at the northern boundary approach to Eagle Pass. It does not assert entry south into Emigrant or establish an overnight wilderness permit requirement for this approach alone.'
        gap(key+'-planning','What remains unverified for '+name+'?',reason,[cid(key+'-profile'),cid(key+'-conditions')])
    features={f['properties']['feature_id'].removeprefix('usfs-emigrant-northern-'):f for f in snapshot['features']}
    legs=[(key,a,b,'overview-map',support,True) for key,fid,start,end,a,b,support in LEGS]+[(key,a,b,src,text,False) for key,a,b,src,text in TOPOLOGY_ONLY]
    for key,a,b,src,text,drawable in legs:
        entity(segment(key),'route_segment',key.replace('-',' ').title())
        scopes=tuple(scope(route(k)) for k,v in ROUTES.items() if key in v[4])
        ev=claim(key+'-topology',src,text+(' The reported half-mile connecting walk is retained; destination totals are not inferred.' if key=='kennedy-parking-start' else ' Atomic mileage remains unknown; cumulative reports and GIS lengths are not subtracted or measured.'),segment(key),'described_route_connector' if key=='kennedy-parking-start' else 'mapped_route_connector',{'start_node_id':a,'end_node_id':b,'distance_miles':0.5 if key=='kennedy-parking-start' else None,'distance_status':'reported' if key=='kennedy-parking-start' else 'not_printed','route_role':'official_mainline','support':text},scopes=scopes)
        if drawable:
            f=features[key];p=f['properties'];attrs=p['source_attributes'];cs=f['geometry']['coordinates'];start,end=p['source_vertex_range_inclusive']
            ev+=claim(key+'-geometry','geometry',f'USFS National Forest System Trails object {attrs["objectid"]}, globalid {attrs["globalid"]}, {attrs["trail_no"]} {attrs["trail_name"]}; reviewed inclusive normalized vertices {start}–{end}. Endpoint assignments are descriptive and source lengths apply to the original feature.',segment(key),'reviewed_route_display_geometry',{'geometry_snapshot':{'path':SNAPSHOT,'sha256':digest,'feature_id':p['feature_id']},'start_coordinate':{'longitude':cs[0][0],'latitude':cs[0][1]},'end_coordinate':{'longitude':cs[-1][0],'latitude':cs[-1][1]},'coordinate_reference_system':'EPSG:4326','source_coordinate_accuracy':'unknown','navigation_grade':False,'source_feature_id':attrs['objectid'],'source_globalid':attrs['globalid'],'source_vertex_range_inclusive':[start,end],'route_role':'official_mainline','current_route_status':'unknown; pre-trip check required'},scopes=scopes)
        rel(key+'-start',segment(key),'starts_at',a,ev);rel(key+'-end',segment(key),'ends_at',b,ev)
        for rt,v in ROUTES.items():
            if key==v[4][-1] and v[2]:rel(key+'-resource',segment(key),'provides_access_to',place(v[2]),ev)
    for key,src,miles,convention,edition in [
        ('kennedy-meadows-kennedy-lake','mileage-table',7.5,'one way','2012-06'),
        ('kennedy-meadows-kennedy-lake','kennedy-destinations',7.5,'not explicitly stated; riding destination','unknown'),
        ('kennedy-meadows-relief-reservoir','mileage-table',3,'one way','2012-06'),
        ('kennedy-meadows-relief-reservoir','favorite-hikes',3,'one way','2018-11'),
        ('kennedy-meadows-relief-reservoir','traveler-2023',6,'round trip','2023'),
        ('eagle-meadow-eagle-pass','favorite-hikes',3,'one way','2018-11')]:
        claim(key+'-mileage-'+src,src,f'{edition} {src}: {ROUTES[key][0]} is reported as {miles} miles ({convention}). Precise endpoint and parking inclusion are not resolved.',route(key),'published_approach_distance_report',{'reported_miles':miles,'distance_convention':convention,'source_edition':edition,'endpoint_precision':'unspecified','not_atomic_distance':True})
    claim('kennedy-parking-distance','traveler-2023','Traveler 2023 p10 states that the trail begins half a mile from the parking lot, at the south end of the main road. It does not state whether the six-mile round-trip destination total includes this connection.',route('kennedy-meadows-relief-reservoir'),'reported_access_walk_distance',{'reported_miles':0.5,'from':'trailhead parking lot','to':'trail start at south end of main road','inclusion_in_destination_total':'unknown','not_added_to_destination_reports':True})
    gap('kennedy-mileage-basis','Do Kennedy approach totals include the walk from parking?','The 2023 guide gives a six-mile round trip and a separate half-mile parking-to-trail walk; the 2012/2018 reports give three miles one way. Kennedy Lake is reported as 7.5 miles by the 2012 table and an undated riding operator. No arithmetic resolves parking inclusion or precise endpoint. Confirm intended start before using these reports.',[cid('kennedy-parking-distance'),cid('kennedy-meadows-relief-reservoir-mileage-traveler-2023'),cid('kennedy-meadows-kennedy-lake-mileage-mileage-table')])
    claim('relief-stock-use','favorite-hikes','ROG 16-41 November 2018 p2 Relief Reservoir description reports heavy stock use. This is a historical usage report, not current trail suitability.',route('kennedy-meadows-relief-reservoir'),'historical_trail_use',{'source_edition':'2018-11','reported_use':'heavy stock use','current_condition':'unknown'})
    claim('eagle-boundary','favorite-hikes','ROG 16-41 November 2018 p2 Eagle Creek to Eagle Pass: entry into Emigrant is south from the pass. The guide also reports the trailhead obscured by primitive campsites.',route('eagle-meadow-eagle-pass'),'boundary_approach_limit',{'wilderness_entry':'south from pass','selected_route':'stops at northern pass approach','wilderness_entry_asserted':False})

    add_access_records(entity,claim,rel,gap,cid)
    reasons={
      'gap-emigrant-route-topology':'Eight published western approaches from Crabtree, Gianelli, Bell Meadow, plus six northern approaches, now have sourced bounded graphs. Northern coverage includes Kennedy Lake, Relief Reservoir, Waterhouse Lake, Cooper Meadow, Eagle Pass and the southbound Sonora PCT to the Leavitt Lake trail junction. Kennedy display geometry remains unreviewed; southern entries, deeper lake/pass branches, cross-boundary itineraries, returns and individual facility spurs remain incomplete. No destination-wide route completeness is claimed.',
      'gap-emigrant-facility-inventory':'Historical western and northern trailhead facilities now include Crabtree, Kennedy and Sonora restrooms, Kennedy water faucets and separately identified Eagle/Coyote horse camps. Current operation, water safety, individual campsites, facility coordinates, approach campgrounds and operator booking inventory remain unresolved. Kennedy camping/fee conflicts and the distinction between Eagle trailhead and horse-camp facilities require recheck.'}
    for old in base.gaps:
        if old.gap_id in reasons:r.gaps.append(replace(old,reason=reasons[old.gap_id]))
    for mid,selected,topics in [(MANIFEST,inputs,['bounded northern routes and display limitations','mileage conventions','current trail conditions','return itinerary and jurisdiction']), (ACCESS_MANIFEST,access_inputs,['historical facilities and road directions','camping and fee conflicts','stock facilities','current roads and operator services'])]:
        r.derived_results.append(DerivedResult(mid,'pretrip_recheck',{'required':True,'topics':topics},tuple(selected),'Project only applicable northern route/access claims and linked gaps. Historical reports do not establish current availability or permission.'))
    return r


def add_access_records(entity,claim,rel,gap,cid):
    """Historical access evidence, distinct facilities and contextual rechecks."""
    for key in ('coyote-meadow','waterhouse','eagle-meadow','sonora-pass'):
        claim(key+'-camping-limit','trailheads','ROG 16-26 April 2012 introduction reports a one-night camping limit at all listed trailheads. This is historical guidance, not a current site-specific authorization.',th(key),'historical_trailhead_camping_limit',{'reported_nights':1,'source_edition':'2012-04','current_rule_status':'requires confirmation'},access=True)
        claim(key+'-parking','trailheads','ROG 16-26 April 2012 '+key.replace('-',' ').title()+' entry lists limited parking and '+('improved' if key=='sonora-pass' else 'native')+' surface.',th(key),'historical_parking_report',{'source_edition':'2012-04','reported_capacity':'limited; no stall count','surface':'improved' if key=='sonora-pass' else 'native','current_availability':'unknown'},access=True)
        claim(key+'-camping','trailheads','ROG 16-26 April 2012 '+key.replace('-',' ').title()+' entry describes '+('few' if key=='sonora-pass' else 'fair')+' overnight camping opportunities. No individual site inventory is supplied.',th(key),'historical_camping_opportunity',{'source_edition':'2012-04','reported_description':'few' if key=='sonora-pass' else 'fair','current_availability':'unknown'},access=True)
        if key!='sonora-pass':claim(key+'-facilities','trailheads','ROG 16-26 April 2012 '+key.replace('-',' ').title()+' trailhead entry says no facilities. This is not a present inventory and does not describe a separately named horse camp.',th(key),'historical_facility_report',{'source_edition':'2012-04','reported_facilities':'none','current_inventory':'unknown'},access=True)
    directions={
     'coyote-meadow':[('east Highway 108 from Summit Ranger Station',3),('right Herring Creek Road 4N12 to pavement end',5),('continue to Hammill Canyon Loop',2),('right, passing Pinecrest Peak 5N31 turnoff, to 5N67',4),('right 5N67 to trailhead',1)],
     'waterhouse':[('east Highway 108 from Summit Ranger Station',3),('right Herring Creek Road 4N12 to pavement end',5),('continue to Hammil Canyon Loop',2),('right',2),('right road labeled 4N31 in this guide toward Pinecrest Peak',{'minimum':0.5,'maximum':0.75})],
     'eagle-meadow':[('east Highway 108 from Summit Ranger Station',17),('right Eagle Meadow Road 5N01',0.25),('right, cross cattle guard, keep right',0.75),('paved road to bridge and Niagara OHV Campground',2),('uphill, turn right, to pavement end',2.25),('right at large intersection, rough road to Eagle Creek',1.75)],
     'sonora-pass':[('east Highway 108 from Summit Ranger Station to parking on left',38.5)],
    }
    for key,legs in directions.items():
        claim(key+'-directions','trailheads','ROG 16-26 April 2012 directions from Summit Ranger Station: '+ '; '.join(f'{x}: {v} miles' for x,v in legs)+'. The guide expressly qualifies all mileages as approximate.',th(key),'historical_driving_directions',{'source_edition':'2012-04','origin':'Summit Ranger Station (Pinecrest)','mileage_precision':'approximate','legs':[{'instruction':x,'approximate_miles':v} for x,v in legs],'current_road_status':'unknown; verify MVUM and current orders'},access=True)
    claim('waterhouse-last-approach','trailheads','ROG 16-26 April 2012 Waterhouse directions put the trailhead about 50 yards back from the four-way road intersection, diagonally left across the meadow.',th('waterhouse'),'historical_access_description',{'reported_setback_yards':50,'precision':'approximate','reference':'four-way intersection','direction':'diagonally left across meadow','current_access':'unknown'},access=True)
    claim('waterhouse-map-road','overview-map','2010 geospatial overview Waterhouse panel labels the Pinecrest Peak approach road 5N31, while the 2012 trailhead directions print 4N31.',th('waterhouse'),'mapped_approach_road_label',{'source_edition':'2010','road_label':'5N31','current_designation':'unverified'},access=True)
    gap('waterhouse-road-number','Which road designation applies to the Waterhouse approach?','The 2012 guide prints 4N31; the 2010 overview map labels 5N31 by Pinecrest Peak and Waterhouse. Preserve both; confirm on the current MVUM and road orders before driving.',[cid('waterhouse-directions'),cid('waterhouse-map-road')],access=True)
    claim('kennedy-directions','traveler-2023','Traveler 2023 p10: from Summit Ranger Station drive Highway 108 east 27 miles, right at Kennedy Meadows sign, half a mile to Trailhead Parking sign, left into the lot.',th('kennedy-meadows'),'historical_driving_directions',{'source_edition':'2023','origin':'Summit Ranger Station','reported_highway_miles':27,'reported_kennedy_road_miles':0.5,'current_road_status':'unknown'},access=True)
    claim('kennedy-parking','brightman-2020','ROG 16-53-01 March 2020 p2: Kennedy trailhead parking is paved, opposite Deadman Campground, with several pull-through stalls for horse trailers or RVs.',th('kennedy-meadows'),'historical_parking_report',{'source_edition':'2020-03','surface':'paved','location':'opposite Deadman Campground','reported_pull_through_stalls':'several','current_availability':'unknown'},access=True)
    claim('kennedy-picnic-tables','brightman-2020','ROG 16-53-01 March 2020 p2 reports three picnic tables at Kennedy trailhead.',th('kennedy-meadows'),'historical_facility_count',{'source_edition':'2020-03','facility':'picnic table','reported_count':3,'current_inventory':'unknown'},access=True)
    for src,nights,edition in [('brightman-2020',2,'2020-03'),('traveler-2023',1,'2023')]:
        claim('kennedy-limit-'+src,src,f'{edition} Forest Service guide reports a {nights}-night camping limit at Kennedy trailhead. '+('Traveler p10 specifies campers and stock entering Emigrant Wilderness.' if nights==1 else 'Brightman p2 describes the paved trailhead site opposite Deadman.'),th('kennedy-meadows'),'reported_trailhead_camping_limit',{'source_edition':edition,'reported_nights':nights,'current_rule_status':'conflicting reports; confirm with manager','scope':'trailhead stays for wilderness visitors'},access=True)
    for src,fee,edition in [('brightman-2020',5,'2020-03'),('kennedy-pct',10,'unknown')]:
        claim('kennedy-fee-'+src,src,f'{edition} '+('Brightman p2' if src=='brightman-2020' else 'operator PCT page')+f' reports ${fee} per night at the Forest Service trailhead site. Current fees are not independently verified.',th('kennedy-meadows'),'reported_trailhead_fee',{'source_edition':edition,'reported_usd_per_night':fee,'current_fee':'unknown'},access=True)
    gap('kennedy-camping-fees','What camping limit and fee currently apply at Kennedy trailhead?','The 2020 Brightman guide reports two nights and $5/night; Traveler 2023 reports one night for campers and stock entering Emigrant. The undated operator PCT page reports $10/night and also contains an obsolete Summer 2019 construction forecast. Confirm site-specific limits and fees with the Forest Service; general forest occupancy limits do not settle this conflict.',[cid('kennedy-limit-brightman-2020'),cid('kennedy-limit-traveler-2023'),cid('kennedy-fee-brightman-2020'),cid('kennedy-fee-kennedy-pct')],access=True)
    for key,src,edition,description in [('kennedy-meadows','brightman-2020','2020-03','accessible vault toilet'),('sonora-pass','trailheads','2012-04','accessible restrooms')]:
        eid='restroom-emigrant-'+key;entity(eid,'restroom',key.replace('-',' ').title()+' trailhead restrooms')
        ev=claim(key+'-restrooms',src,f'{edition} official guide reports {description} at {key.replace("-"," ")} trailhead. Present operation, count and precise location are unknown.',eid,'historical_facility_presence',{'source_edition':edition,'reported_type':description,'current_availability':'unknown','count':'unknown'},scopes=(scope(eid),scope(th(key))),access=True)
        rel(key+'-restroom-location',eid,'part_of',th(key),ev);rel(key+'-restroom-access',th(key),'provides_access_to',eid,ev)
    claim('kennedy-vault-2023','traveler-2023','Traveler 2023 p10 Horse Camping lists vault toilets at Kennedy Meadows trailhead.', 'restroom-emigrant-kennedy-meadows','reported_restroom_type',{'source_edition':'2023','type':'vault toilet','current_availability':'unknown'},scopes=(scope('restroom-emigrant-kennedy-meadows'),scope(th('kennedy-meadows'))),access=True)
    claim('sonora-toilet-project','traveler-2023','Traveler 2023 p8 lists new vault toilets at Sonora Pass day use area among improvements planned complete by 2026. A plan is not evidence of completion.', 'restroom-emigrant-sonora-pass','published_facility_project',{'source_edition':'2023','planned_completion_year':2026,'completion_status':'unknown','project':'new vault toilets at Sonora Pass day use area'},scopes=(scope('restroom-emigrant-sonora-pass'),scope(th('sonora-pass'))),access=True)
    water='water-source-emigrant-kennedy-faucets';entity(water,'water_source','Kennedy trailhead water faucets')
    ev=claim('kennedy-water','brightman-2020','ROG 16-53-01 March 2020 p2 reports faucets at the accessible vault toilet and at a horse unloading zone next to Kennedy Meadows Road. It does not establish current flow or potability.',water,'historical_water_facility',{'source_edition':'2020-03','reported_locations':['accessible vault toilet','horse unloading zone next to Kennedy Meadows Road'],'current_flow':'unknown','potability':'unknown','coordinates':'not reviewed'},scopes=(scope(water),scope(th('kennedy-meadows'))),access=True)
    rel('kennedy-water-location',water,'part_of',th('kennedy-meadows'),ev);rel('kennedy-water-access',th('kennedy-meadows'),'provides_access_to',water,ev)
    for key,improvements in [('eagle-meadow',['restrooms','fire rings']),('coyote-meadow',[])]:
        eid='campground-emigrant-'+key+'-horse';entity(eid,'campground',key.replace('-',' ').title()+' Horse Camp')
        ev=claim(key+'-horse-identity','horse-camping-2020','ROG 16-08 February 2020 pp1,4 names '+key.replace('-',' ').title()+' Horse Camp outside wilderness. The camp is distinct from the trailhead; no connecting path or shared facility is established.',eid,'historical_horse_camp_identity',{'source_edition':'2020-02','camp_type':'horse camp outside wilderness','individual_sites':'not inventoried','current_availability':'unknown'},access=True)
        claim(key+'-horse-facilities','horse-camping-2020','ROG 16-08 February 2020 p1 reports '+(', '.join(improvements) if improvements else 'no improvements')+' at '+key.replace('-',' ').title()+' Horse Camp.',eid,'historical_facility_report',{'source_edition':'2020-02','reported_improvements':improvements,'current_inventory':'unknown'},access=True)
        claim(key+'-horse-fee','horse-camping-2020','ROG 16-08 February 2020 p1 includes this horse camp among undeveloped camping areas requiring no camping fee. Current fees and operation require confirmation.',eid,'historical_camping_fee',{'source_edition':'2020-02','reported_fee_usd':0,'current_fee':'unknown'},access=True)
        claim(key+'-horse-stock-guidance','horse-camping-2020','ROG 16-08 February 2020 p1, Horse Camping outside Wilderness: keep animals at least 100 feet from lakes, streams and campsites. This outside-wilderness guidance does not replace the signed Emigrant stock rules or their existing interpretation gap.',eid,'historical_outside_wilderness_stock_guidance',{'source_edition':'2020-02','minimum_reported_feet':100,'from':['lakes','streams','campsites'],'scope':'outside wilderness horse-camping guidance','current_applicability':'confirm site rules; not a wilderness setback resolution'},access=True)
        claim(key+'-horse-referral','horse-camping-2020','ROG 16-08 February 2020 separately names '+key.replace('-',' ').title()+' Horse Camp. Same-area trailhead naming does not prove shared toilets or a connecting route.',th(key),'nearby_named_facility_recheck',{'reported_camp_id':eid,'trailhead_identity_distinct':True,'connection':'unreviewed','current_operation':'unknown'},access=True)
        gap(key+'-horse-access','How is '+key.replace('-',' ').title()+' Horse Camp reached and used today?','Historical outside-wilderness horse camp inventory does not establish a trailhead connector, shared facilities, individual campsites, current fees or operating status.',[cid(key+'-horse-identity'),cid(key+'-horse-referral'),cid(key+'-horse-facilities')],access=True)
    for key in ('kennedy-meadows','sonora-pass'):
        claim(key+'-highway-limits','traveler-2023','Traveler 2023 p10 Highway 108 information advises against large RVs or trailers from Kennedy Meadows on the west to Leavitt Meadow on the east; grades can be as steep as 26 percent, with narrow winding road and no shoulder.',th(key),'historical_vehicle_access_advisory',{'source_edition':'2023','reported_advisory':'large RVs or trailers not advised','maximum_reported_grade_percent':26,'extent':'Kennedy Meadows to Leavitt Meadow','current_road_status':'unknown'},access=True)
        claim(key+'-operator-service','kennedy-pct','Undated Kennedy operator PCT page advertises a resort–Sonora Pass shuttle. Its current schedule and availability need confirmation; the same page retains a Summer 2019 construction forecast.',th(key),'reported_operator_transport',{'operator':'Kennedy Meadows Resort & Pack Station','reported_link':['resort','Sonora Pass'],'current_availability':'unknown','walking_connection':'not asserted','source_date':'unknown'},access=True)
        claim(key+'-operator-season','kennedy-home','Undated Kennedy home page reports a season from the last Friday in April through Columbus Day in October.',th(key),'reported_operator_season',{'operator':'Kennedy Meadows Resort & Pack Station','reported_season':'last Friday in April through Columbus Day in October','current_availability':'unknown'},access=True)
        claim(key+'-operator-season-pct','kennedy-pct','Undated operator PCT page says package acceptance is May 1–October 1 and describes closure outside that interval. This does not align with the home-page resort season.',th(key),'reported_operator_season',{'reported_service':'package acceptance','reported_interval':'May 1 through October 1','outside_interval_statement':'closed','source_date':'unknown','current_availability':'unknown'},access=True)
        gap(key+'-operator','Which Kennedy operator services and dates can be relied on?','The home-page season and PCT-page closure wording differ; the PCT page also retains a 2019 construction forecast. Confirm shuttle operation, resupply dates and bookings directly. No bed, campsite, ride or service inventory is verified.',[cid(key+'-operator-service'),cid(key+'-operator-season'),cid(key+'-operator-season-pct')],access=True)
    # The expired order remains a dated historical claim. A separate timeless
    # recheck preserves consumer discoverability without implying a current closure.
    for key in ('coyote-meadow','waterhouse'):
        claim(key+'-road-order','northern-road-order','Signed STF-16-2026-07 p1, executed May 29, 2026: motor vehicles prohibited on 4N12 at 18EV463 junction June 1–15, 2026, subject to listed exemptions. This historical interval does not establish present closure or reopening.',th(key),'historical_road_closure',{'order':'STF-16-2026-07','road':'4N12 at 18EV463 junction','activity':'motor vehicle use','current_status':'unknown','supersedes':'STF-16-2026-04','exemptions':['FS-7700-48 specifically exempting holder','official-duty officers or organized rescue/fire forces'],'over_snow_exception':{'roads':['5N01','4N12','5N40Y','7N09','7N23','17EV485'],'minimum_snow_inches':12}},access=True,temporal=TemporalScope(date(2026,6,1),date(2026,6,15)))
        for suffix,src,number in [('summary','northern-road-alert','STF-16-2026-78'),('pdf','northern-road-order','STF-16-2026-07')]:
            claim(key+'-order-id-'+suffix,src,'June 2026 closure '+('alert opening summary names ' if suffix=='summary' else 'signed PDF and alert structured order number name ')+number+'. Retain the conflicting identifiers.',th(key),'reported_road_order_identifier',{'reported_order':number,'historical_effective_interval':'2026-06-01 through 2026-06-15','current_road_status':'unknown'},access=True)
        gap(key+'-order-id','Which order identifier describes the June 2026 4N12 restriction?','The alert summary says STF-16-2026-78; its structured number/link and signed PDF say STF-16-2026-07. The interval has expired; neither expiration nor an old alert listing proves current road opening. Recheck the current MVUM and orders.',[cid(key+'-order-id-summary'),cid(key+'-order-id-pdf')],access=True)
    for key in ('kennedy-meadows','sonora-pass','coyote-meadow','waterhouse','eagle-meadow'):
        claim(key+'-access-recheck','alerts','Check current Forest Service alerts and site-specific restrictions for '+key.replace('-',' ').title()+'. Old directions and facility descriptions are not road clearance, campsite availability, water safety or permission.',th(key),'pretrip_access_recheck',{'required':True,'current_status':'unknown','topics':['road and highway access','trailhead camping limits and fees','restroom operation','water availability','stock and vehicle restrictions']},access=True)
        gap(key+'-access','What access and facilities currently apply at '+key.replace('-',' ').title()+'?','Historical facility and camping descriptions require present confirmation. Verify current MVUM, road/fire orders, parking, toilets, water safety and site-specific overnight limits. Forest occupancy maxima do not override shorter site limits. Individual sites and facility footpaths are not inventoried.',[cid(key+'-access-recheck')],access=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,default=ROOT);p.add_argument('--output',type=Path,default=ROOT);p.add_argument('--reviewed-input',type=Path);a=p.parse_args();path=a.output/SNAPSHOT
    if a.reviewed_input:
        raw=a.reviewed_input.read_bytes();assert hashlib.sha256(raw).hexdigest()==REVIEWED_INPUT_SHA256
        payload=snapshot_from_reviewed(json.loads(raw));payload['wayproof']['reviewed_input_sha256']=REVIEWED_INPUT_SHA256
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    content=path.read_bytes();base=load_canonical(a.base);records=build_records(base,json.loads(content),hashlib.sha256(content).hexdigest())
    ops=tuple(ChangeOperation(ChangeAction.REPLACE if getattr(rec,ident) in REPLACEMENTS else ChangeAction.ADD,kind,getattr(rec,ident),f'canonical/v0/{collection}/{getattr(rec,ident)}.json','Add bounded northern approaches, geometry and historical access evidence; preserve unresolved planning limits.',evidence_refs=getattr(rec,'evidence_ids',()),knowledge_gap_refs=(getattr(rec,ident),) if kind=='gap' else ()) for kind,(collection,ident,_) in RECORD_SPECS.items() for rec in getattr(records,collection))
    change=ChangeSet(CHANGE_ID,records,summary='Add six northern Emigrant approaches, four with reviewed display geometry, plus distinct historical facilities and access conflicts.',operations=ops)
    writes=ChangeSetWriteService(InMemoryCanonicalRepository(base));writes.propose(change,'emigrant-northern-ingestion');errors=writes.validate(CHANGE_ID,'emigrant-validator')
    if errors:raise RuntimeError('\n'.join(errors))
    candidate=writes.prepare(CHANGE_ID,'emigrant-candidate-builder');write_candidate(a.output,candidate,writes.get(CHANGE_ID));print(f'Prepared {len(ops)} records in {CHANGE_ID}; not published.')

# Fixed identities/counts and input hash from the reviewed acquisition, not a
# discovery heuristic that could silently ingest a different live response.
EXPECTED = {9428140: ('{7D5C8931-FE33-4617-B426-1AB1394BD898}', 148, '19E31'), 9430353: ('{B94AF8F8-6909-420D-B63C-565E856CE3B3}', 575, '20E15'), 9430941: ('{E21E03C8-A491-47B2-B7D9-DFFB02C1F287}', 439, '20E08'), 9430469: ('{4462AC9E-FF7C-4BFB-A0EC-3155C06BBBB0}', 117, '20E08'), 9501224: ('{A727D99A-D0CF-45FC-A408-A94FA4611519}', 61, '2000'), 9510733: ('{1BDAB4FE-E8B1-43D0-8626-53069B960311}', 561, '2000'), 9513460: ('{1DCEF719-C6FD-4610-80C5-0CA02903061C}', 40, '2000'), 9511588: ('{6B0FA99D-C3DC-4A5C-83C8-CD1EF2FF0FED}', 782, '2000'), 9502156: ('{93AD03DF-A458-4275-8A64-89834337C317}', 634, '2000')}
REVIEWED_INPUT_SHA256 = '83fed12484880c7878c89e77a8bd6c56ea5a021afcb46a7641d5c642f513b744'

if __name__ == '__main__': main()
