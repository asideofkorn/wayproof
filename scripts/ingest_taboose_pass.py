#!/usr/bin/env python3
"""Prepare reviewed Taboose coverage; no live fetching or publication.

Regenerate the same unmerged ChangeSet against a clean --base. Official source
geometry can be rebuilt using --reviewed-input; see docs/ingestion/taboose.md.
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

ROOT = Path(__file__).resolve().parents[1]
CHANGE_ID = 'wp-20261006-taboose-pass-corridor'
MANIFEST = 'result-taboose-pretrip-recheck'
TH = 'trailhead-taboose-pass'
PASS = 'place-taboose-pass'
ROUTE = 'route-taboose-pass'
SEGMENT = 'route-segment-taboose-trailhead-pass'
ROAD = 'road-taboose-creek'
ROAD_ROUTE = 'route-taboose-road-access'
ROAD_SEGMENT = 'route-segment-taboose-road-access'
HIGHWAY = 'entrance-taboose-us395'
CAMP = 'campground-taboose-creek'
WEST = 'zone-taboose-kings-canyon-continuation'
LAND = 'wilderness-john-muir'
PARK = 'park-sequoia-kings-canyon'
AGENCY = 'agency-inyo-national-forest'
PERMIT = 'permit-inyo-overnight-wilderness'
SNAPSHOT = 'geometry/v0/snapshots/usfs-taboose-pass-20261006.geojson'
SERVICE = 'https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0'
RETRIEVED = datetime(2026, 10, 6, 21, 40, tzinfo=timezone.utc)
REVIEW_RETRIEVED = datetime(2026, 10, 6, 23, 14, tzinfo=timezone.utc)
FIRE_TIME = TemporalScope(date(2025, 6, 10), date(2027, 6, 10))
USE_TIME = TemporalScope(date(2025, 6, 18), date(2027, 6, 18))
STAGE_TIME = TemporalScope(date(2026, 6, 22), date(2026, 12, 31))
FS = 'https://www.fs.usda.gov'
SOURCES = {
 'trail': (FS+'/r05/inyo/recreation/trails/taboose-pass-trail', 'USDA Forest Service, Inyo National Forest'),
 'map': (FS+'/sites/nfs/files/legacy-media/inyo/Trails-%20Independence%20area.pdf', 'USDA Forest Service, Inyo National Forest'),
 'entry-guide': (FS+'/sites/nfs/files/legacy-media/inyo/JMT%20TripPlan%20Entry%20Points.pdf', 'USDA Forest Service, Inyo National Forest'),
 'permits': (FS+'/r05/inyo/permits/wilderness-permits', 'USDA Forest Service, Inyo National Forest'),
 'quota': (FS+'/sites/nfs/files/publication/trail%20quota%20sheet.pdf_0.pdf', 'USDA Forest Service, Inyo National Forest'),
 'printing': (FS+'/r05/inyo/permits/printing-instructions', 'USDA Forest Service, Inyo National Forest'),
 'regulations': (FS+'/r05/inyo/permits/wilderness-regulations', 'USDA Forest Service, Inyo National Forest'),
 'use-order': (FS+'/r05/inyo/alerts/wilderness-use-restrictions', 'USDA Forest Service, Inyo National Forest'),
 'fire-order': (FS+'/sites/nfs/files/r05/inyo/publication/alerts/05-04-50-25-04%20Ansel%20Adams%20%26%20John%20Muir%20Campfire%20Restrictions.pdf', 'USDA Forest Service, Inyo National Forest'),
 'fire-map': (FS+'/sites/nfs/files/r05/inyo/publication/alerts/25-05-50-25-04%20Exhibits%20B-S%20-%20June%202025.pdf', 'USDA Forest Service, Inyo National Forest'),
 'stage1': (FS+'/r05/inyo/alerts/stage-1-fire-restrictions-effect', 'USDA Forest Service, Inyo National Forest'),
 'food': (FS+'/r05/inyo/alerts/food-and-refuse-storage-restrictions', 'USDA Forest Service, Inyo National Forest'),
 'recgov': ('https://www.recreation.gov/permits/233262', 'Recreation.gov / USDA Forest Service'),
 'nps-rules': ('https://www.nps.gov/seki/planyourvisit/minimum-impact-restrictions.htm', 'National Park Service'),
 'nps-conditions': ('https://www.nps.gov/seki/planyourvisit/trailcond.htm', 'National Park Service'),
 'nps-stock': ('https://www.nps.gov/seki/planyourvisit/grazingrestrictions.htm', 'National Park Service'),
 'nps-atlas': ('https://parkplanning.nps.gov/showFile.cfm?projectID=33225&sfid=186534', 'National Park Service'),
 'camp': ('https://www.inyocounty.us/services/parks-recreation/campgrounds/taboose-creek-campground', 'Inyo County Parks and Recreation'),
 'camp-map': ('https://www.inyocounty.us/sites/default/files/2025-05/Taboose.pdf', 'Inyo County Parks and Recreation'),
 'water-notice': ('https://www.inyocounty.us/sites/default/files/2026-07/0267_001.pdf', 'Inyo County / Taboose Creek Campground water system'),
 'booking': ('https://www.reserveamerica.com/explore/taboose-creek-campground/INYO/1100013/campsites', 'ReserveAmerica / Inyo County'),
 'roads': ('https://www.inyocounty.us/services/public-works/news/inyo-county-road-openclosed-status', 'Inyo County Public Works'),
 'geometry': (SERVICE, 'USDA Forest Service'),
}
FEATURES = [(9575473, 7, '{160C8A17-E103-49FB-98D7-D5574A353CB0}'),
            (9574682, 618, '{9E66CE68-D452-49EA-BEB7-260709E9E4C1}'),
            (9575492, 467, '{7ADB6735-DD74-4B82-B71B-62FD8DEB14CF}'),
            (9575315, 945, '{C7BB0F13-1364-48B6-8CED-751B7DA2C5A7}')]


def scope(eid):
    return 'scope-' + eid


def snapshot_from_reviewed(raw, raw_hash):
    source = {f['properties']['objectid']: f for f in raw['features']}
    assert set(source) == {x[0] for x in FEATURES}
    coords, lineage = [], []
    for fid, count, guid in FEATURES:
        f = source[fid]
        a, g = f['properties'], f['geometry']
        assert a['trail_name'] == 'TABOOSE PASS' and a['trail_no'] == '3304'
        assert a['globalid'] == guid and g['type'] == 'LineString'
        assert len(g['coordinates']) == count
        if coords:
            assert coords[-1] == g['coordinates'][0]
        coords.extend(g['coordinates'] if not coords else g['coordinates'][1:])
        lineage.append({'attributes': a, 'source_vertex_range_inclusive': [0, count-1],
            'source_geometry_sha256': hashlib.sha256(json.dumps(g, sort_keys=True).encode()).hexdigest()})
    return {'type': 'FeatureCollection', 'wayproof': {
        'source': SERVICE, 'publisher': 'USDA Forest Service', 'classification': 'public_domain',
        'retrieved_at': RETRIEVED.isoformat(), 'normalized_coordinate_reference_system': 'EPSG:4326',
        'source_coordinate_reference_system': 'EPSG:4269', 'navigation_grade': False,
        'query_parameters': {'where': "UPPER(TRAIL_NAME) LIKE '%TABOOSE%'", 'outFields': '*', 'outSR': 4326, 'f': 'geojson'},
        'reviewed_input_sha256': raw_hash,
        'processing': 'Four complete named features in source milepost order; exact shared endpoint duplicates omitted. No snapping, interpolation, simplification, rounding, or derived mileage.',
        'review_basis': 'USFS Independence Area Trails map, Taboose trail description, JMT Entry Points guide, and Exhibit P establish identity, trailhead, pass and eastern approach; source features supply display shape only.',
        'limitations': 'Does not depict the access road, individual crossings, campground, campsite spurs or western continuation. Coordinate accuracy is unspecified.'},
        'features': [{'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': coords},
         'properties': {'feature_id': 'usfs-taboose-trailhead-pass', 'source_features': lineage,
                        'xy_accuracy': 'unknown; coordinate digits do not establish positional accuracy'}}]}


class Builder:
    def __init__(self, base):
        self.r = CanonicalRecords()
        self.inputs = []
        self.sources = {}
        by_url = {s.locator: s.source_id for s in base.sources}
        for key, (url, publisher) in SOURCES.items():
            sid = by_url.get(url, 'source-taboose-' + key)
            self.sources[key] = sid
            if url not in by_url:
                self.r.sources.append(Source(sid, url, publisher))

    def entity(self, eid, kind, name):
        self.r.entities.append(Entity(eid, kind, name))
        self.r.spatial_scopes.append(SpatialScope(scope(eid), kind, eid))

    def claim(self, key, src, subject, predicate, value, content, *, scopes=None, time=None, observed=None, recheck=False, retrieved=None):
        cid, oid, evid = ('claim-taboose-'+key, 'observation-taboose-'+key, 'evidence-taboose-'+key)
        self.r.observations.append(Observation(oid, self.sources[src], content,
            observed_at=observed, retrieved_at=retrieved or RETRIEVED, observer='Wayproof primary-source text, table and visual map review'))
        self.r.evidence.append(Evidence(evid, oid, cid))
        self.r.claims.append(Claim(cid, subject, predicate, value, (evid,), time,
                                   (scope(subject),) if scopes is None else tuple(scopes)))
        if recheck:
            self.inputs.append(cid)
        return cid

    def rel(self, key, subject, predicate, obj, cid):
        self.r.relationships.append(Relationship('relationship-taboose-'+key, subject, predicate, obj,
                                                ('evidence-'+cid.removeprefix('claim-'),)))

    def gap(self, key, question, reason, *related):
        gid = 'gap-taboose-' + key
        self.r.gaps.append(KnowledgeGap(gid, question, tuple(related), reason))
        self.inputs.append(gid)

    def rule(self, key, cid, consequence, scopes, conditions=(), time=None):
        rid = 'rule-taboose-' + key
        self.r.rules.append(Rule(rid, cid, consequence, tuple(conditions), tuple(scopes), time))
        self.r.requirements.append(Requirement('requirement-taboose-'+key, rid, consequence))


def build_records(base, snapshot, digest):
    b = Builder(base)
    for eid, kind, name in [
        (TH, 'trailhead', 'Taboose Pass Trailhead'), (PASS, 'pass', 'Taboose Pass'),
        (ROUTE, 'route', 'Taboose Pass Trail'), (SEGMENT, 'route_segment', 'Taboose trailhead to Taboose Pass'),
        (ROAD, 'road', 'Taboose Creek Road'), (ROAD_ROUTE, 'route', 'US 395 to Taboose Pass Trailhead'),
        (ROAD_SEGMENT, 'route_segment', 'Taboose Creek Road approach from US 395'),
        (HIGHWAY, 'route_node', 'Taboose Creek Road junction at US 395'),
        (CAMP, 'campground', 'Taboose Creek Campground'),
        ('agency-inyo-county-parks', 'agency', 'Inyo County Parks and Recreation'),
        ('facility-taboose-camp-toilets', 'restroom', 'Taboose Creek Campground vault toilets'),
        ('facility-taboose-camp-well', 'water_source', 'Taboose Creek Campground water well'),
        ('waterway-taboose-creek', 'waterway', 'Taboose Creek'),
        (WEST, 'zone', 'Taboose Pass western continuation in Kings Canyon'),
    ]:
        b.entity(eid, kind, name)
    trail_scopes = (scope(ROUTE), scope(SEGMENT))
    access_scopes = (scope(ROAD), scope(ROAD_ROUTE), scope(HIGHWAY), scope(TH))
    profile = b.claim('trail-description', 'trail', ROUTE, 'route_description',
        {'directionality': 'bidirectional described and mapped trail', 'entry_id': TH, 'objective_id': PASS,
         'effort': 'strenuous', 'elevation_gain_feet': {'more_than': 6000},
         'west_continuation': 'John Muir Trail and Kings Canyon destinations south of Mather Pass',
         'current_conditions': 'unknown'},
        'USFS Taboose Pass Trail overview: the route ascends Taboose Creek canyon from the Owens Valley between Cardinal and Goodale mountains, gains more than 6,000 feet, crosses Taboose Pass and continues to the JMT in Kings Canyon. The pass is a common destination.')
    b.rel('route-start', ROUTE, 'starts_at', TH, profile)
    b.rel('route-end', ROUTE, 'ends_at', PASS, profile)
    b.rel('pass-approach', PASS, 'approached_via', ROUTE, profile)
    b.rel('trailhead-access', TH, 'accesses', ROUTE, profile)
    b.rel('route-managed', ROUTE, 'managed_by', AGENCY, profile)
    top = b.claim('trail-topology', 'map', SEGMENT, 'mapped_route_connector',
        {'start_node_id': TH, 'end_node_id': PASS, 'route_role': 'official_mainline',
         'distance_miles': None, 'distance_status': 'conflicting_source_reports',
         'directionality': 'bidirectional', 'mode': 'hiking', 'precision_note': 'Continuous named trail; no intermediate named junction or surveyed jurisdiction crossing asserted.'},
        'Independence Area Trails map, page 1, upper Taboose panel (edition unstated): highlighted trail connects the marked Taboose trailhead to Taboose Pass at the Forest Service / Kings Canyon boundary. It crosses John Muir Wilderness on the eastern approach. Map supports a continuous bidirectional trail, not exact mileage.', scopes=trail_scopes)
    for key, subj, pred, obj in [('segment-start',SEGMENT,'starts_at',TH),('segment-end',SEGMENT,'ends_at',PASS),
        ('segment-member',SEGMENT,'part_of',ROUTE),('route-wilderness',ROUTE,'traverses',LAND),
        ('segment-wilderness',SEGMENT,'traverses',LAND),('pass-west',PASS,'adjacent_to',WEST),
        ('west-park',WEST,'part_of',PARK)]:
        b.rel(key,subj,pred,obj,top)
    distance = b.claim('guide-distance', 'entry-guide', ROUTE, 'published_approach_distance_report',
        {'reported_one_way_miles': 6.5, 'qualifier': 'approximate', 'endpoint': 'trailhead to pass',
         'navigation_grade': False, 'edition': 'unstated'},
        'John Muir Trail Entry Points, page 1, Taboose Pass row: trailhead-to-pass 6.5 miles; the heading explicitly says all mileages/elevations are approximate and for planning, not navigation.', recheck=True)
    b.claim('guide-jmt-distance','entry-guide',ROUTE,'published_approach_distance_report',
        {'reported_one_way_miles':8.75,'qualifier':'approximate','endpoint':'trailhead to JMT junction','not_pass_distance':True},
        'JMT Entry Points page 1, Taboose row: 8.75 miles from trailhead to JMT junction. This longer endpoint is not the pass.')
    for key, subject, feet in [('trailhead',TH,5400),('pass',PASS,11350)]:
        b.claim(key+'-elevation','entry-guide',subject,'published_elevation',{'feet':feet,'qualifier':'approximate','navigation_grade':False},
            f'JMT Entry Points page 1, Taboose row: {key} elevation {feet:,} feet, under the approximate-for-planning heading.')
    f=snapshot['features'][0]; cs=f['geometry']['coordinates']
    geo=b.claim('trail-geometry','geometry',SEGMENT,'reviewed_route_display_geometry',
        {'geometry_snapshot':{'path':SNAPSHOT,'sha256':digest,'feature_id':f['properties']['feature_id']},
         'start_coordinate':{'longitude':cs[0][0],'latitude':cs[0][1]},
         'end_coordinate':{'longitude':cs[-1][0],'latitude':cs[-1][1]},
         'source_feature_ids':[x[0] for x in FEATURES], 'coordinate_reference_system':'EPSG:4326',
         'source_coordinate_accuracy':'unknown','navigation_grade':False,'route_role':'official_mainline',
         'distance_policy':'No canonical distance derived from coordinates or summed from service attributes.'},
        'USFS National Forest System Trails, four complete TABOOSE PASS 3304 features: exact shared endpoints form one trailhead-to-pass display chain. Source object/global IDs and original attributes are preserved in the snapshot; map and prose independently establish topology.', scopes=trail_scopes,recheck=True)
    for key, subject, point in [('trailhead', TH, cs[0]), ('pass', PASS, cs[-1])]:
        b.claim(key+'-display-point','geometry',subject,'reviewed_display_coordinate',
            {'longitude':point[0],'latitude':point[1],'coordinate_reference_system':'EPSG:4326',
             'role':'endpoint of reviewed official trail feature chain','source_coordinate_accuracy':'unknown',
             'not_surveyed_facility_coordinate':True,'navigation_grade':False},
            f'USFS named 3304 chain {key} endpoint matched against the Independence Area Trails map; retained unmodified as a display point, not a surveyed facility position.')
    dataset=b.claim('dataset-lengths','geometry',ROUTE,'published_dataset_length_report',
        {'source_segment_length_miles':[0.018,2.3639,1.7595,3.4732],
         'source_gis_miles':[0.019,2.243,1.704,3.316],'source_final_milepost':7.6146,
         'role':'separate source attributes; not adopted as a resolved hiking distance'},
        'USFS 3304 source attributes in connected order: segment_length 0.018, 2.3639, 1.7595, 3.4732; gis_miles 0.019, 2.243, 1.704, 3.316; terminal emp 7.6146. These differ from the approximate 6.5-mile guide and are not silently substituted.',recheck=True)
    b.gap('mileage','What distance should be planned from the trailhead to the pass?',
        'The approximate USFS guide gives 6.5 miles; the matching official trail dataset terminates at milepost 7.6146 and has different GIS length attributes. Different survey/measurement methods or editions may explain this, but the discrepancy is unresolved. Traversal is connected with unknown canonical distance; no arithmetic or map scaling resolves it.',ROUTE,distance,dataset,geo)
    road=b.claim('road-directions','trail',ROAD,'road_access_description',
        {'from':'US 395 about 12 miles south of Big Pine','turn':'west on Taboose Creek Road',
         'distance_miles':{'approximately':6},'surface':'rough, bumpy dirt road','endpoint':'road end at trailhead',
         'vehicle_clearance_requirement':'unknown','current_passability':'unknown'},
        'USFS Getting There directs visitors west from US 395 about 12 miles south of Big Pine, approximately six miles along rough, bumpy Taboose Creek Road to its end.',scopes=access_scopes,recheck=True)
    roadleg=b.claim('road-topology','trail',ROAD_SEGMENT,'described_route_connector',
        {'start_node_id':HIGHWAY,'end_node_id':TH,'distance_miles':6,'distance_status':'approximate',
         'route_role':'official_mainline','mode':'road access; separate from hiking mileage','directionality':'bidirectional access road'},
        'USFS directions explicitly connect the US 395 turnoff to the road-end trailhead along Taboose Creek Road, approximately six miles. No intermediate spur distance is derived.',scopes=access_scopes)
    for key, subj,pred,obj in [('road-start',ROAD_ROUTE,'starts_at',HIGHWAY),('road-end',ROAD_ROUTE,'ends_at',TH),
        ('roadleg-start',ROAD_SEGMENT,'starts_at',HIGHWAY),('roadleg-end',ROAD_SEGMENT,'ends_at',TH),
        ('roadleg-member',ROAD_SEGMENT,'part_of',ROAD_ROUTE),('road-route',ROAD_ROUTE,'traverses',ROAD),
        ('road-serves',ROAD,'provides_access_to',TH),('trailhead-approach',TH,'approached_via',ROAD_ROUTE)]:
        b.rel(key,subj,pred,obj,roadleg)
    b.claim('trailhead-lockers','trail',TH,'food_storage_facility',{'bear_lockers':False},
        'USFS General Information explicitly says there are no bear lockers at this trailhead.')
    parking=b.claim('vehicle-food','trail',TH,'vehicle_food_storage_guidance',
        {'recommendation':'secure food and scented items in vehicle trunk; cover ice chests','parking_capacity':'unknown','parking_fee':'unknown'},
        'USFS trailhead-specific recommendation is to secure food/scented items in a vehicle trunk and cover ice chests. It does not publish a parking capacity or fee.',recheck=True)
    generic=b.claim('generic-vehicle-food','recgov',TH,'vehicle_food_storage_guidance',
        {'general_instruction':'do not leave food/refuse in car or tent; use lockers where provided'},
        'Recreation.gov Inyo permit overview says not to leave food/refuse in cars or tents, and to use bear lockers at equipped parking. This differs from the trailhead-specific trunk recommendation at a trailhead without lockers.',recheck=True)
    b.gap('vehicle-food-conflict','How should food left at Taboose trailhead be secured?',
        'Conflict: trailhead page recommends trunk storage and says no lockers; general Inyo permit guidance says do not leave food in cars. Confirm trailhead-specific handling; do not invent lockers or choose one instruction silently.',TH,parking,generic)
    b.gap('trailhead-facilities','What parking, toilets and potable water are available at the trailhead?',
        'Road-end vehicle access and absent bear lockers are evidenced. Parking capacity, fees, designated spaces, toilet inventory and potable taps at the trailhead remain unknown. County campground toilets/well are separate facilities approximately two road miles from US 395, not trailhead amenities.',TH,road,parking)

    overnight=b.claim('overnight-permit','trail',ROUTE,'overnight_permit_required',{'required':True,'season':'year-round','permit_entity_id':PERMIT},
        'USFS Taboose Pass Permits requires a wilderness permit year-round for overnight visits.',recheck=True)
    b.rule('overnight-permit',overnight,'Obtain and carry a signed Inyo wilderness permit for the Taboose entry date and trail for an overnight trip.',trail_scopes,(Condition('activity.overnight','equals',True),))
    b.rel('permit-product',PERMIT,'applies_at',ROUTE,overnight)
    day=b.claim('day-permit','trail',ROUTE,'day_use_permit_policy',{'required':False,'qualification':'general trail-page statement; camping-equipment order may apply'},
        'Taboose trail page says day use does not require a permit. Preserve alongside the current order covering possession of listed camping/pack-outfitting equipment.',recheck=True)
    gear=b.claim('equipment-permit','use-order',ROUTE,'camping_equipment_permit_requirement',
        {'listed_items':['tent','sleeping bag','bear canister','camp stove'],'required':'valid Forest Service wilderness permit',
         'order':'05-04-50-25-02','exemptions':['specifically exempt FS-7700-48','official duty']},
        'Order 05-04-50-25-02 item 4 prohibits possession of camping/pack-outfitting equipment including tents, sleeping bags, bear canisters or camp stoves without a valid wilderness permit; effective June 18, 2025-June 18, 2027.',time=USE_TIME,recheck=True)
    b.gap('day-equipment-permit','Does a day trip carrying a stove or bear canister require a wilderness permit?',
        'Scope conflict: trail-page day-use exemption is unqualified, but the active order includes possession of listed equipment without an overnight condition. Day hiking is not represented as unconditional permit clearance; ask the Inyo permit office for interpretation. No new equipment vocabulary or exemption is invented.',ROUTE,day,gear,overnight)
    quota=b.claim('quota','quota',ROUTE,'wilderness_entry_quota',
        {'trail_code':'JM27','persons_per_entry_day':10,'six_month_spaces':6,'two_week_spaces':4,
         'season':'May 1-November 1','commercial_policy':'single quota shared with public','live_inventory':'unknown'},
        'Wilderness Trail Names and Quotas pages 2-3, Taboose Pass (JMT), JM27: total 10; six months 6; two weeks 4; single quota. JM quotas apply May 1-November 1. Commercial and public users share a single quota.',recheck=True)
    release=b.claim('release','permits',ROUTE,'reservation_release',
        {'required_year_round':True,'quota_period':'May 1-November 1','six_month_percent':60,'two_week_percent':40,
         'release_time':'07:00 America/Los_Angeles','nonquota_period':'November 2-April 30',
         'nonquota_release':'2 weeks before entry','live_availability':'unknown'},
        'USFS Wilderness Permits overview, How to Reserve and Winter Permits: 60% six calendar months ahead; 40% two weeks ahead at 7am Pacific; winter permits have no trailhead quota and appear two weeks ahead.',recheck=True)
    b.claim('release-time-wording','recgov',ROUTE,'published_release_time_wording',
        {'summary':'7AM PST','need_to_know':'7am Pacific Time','interpretation':'USFS uses Pacific time; verify booking clock rather than assume fixed UTC offset'},
        'Recreation.gov summary uses PST while its Need to Know uses Pacific Time. USFS gives Pacific time. Preserve the inconsistent timezone wording.',recheck=True)
    b.gap('release-clock','Which clock applies to online releases during daylight saving time?',
        'Recreation.gov alternates PST and Pacific Time. Canonical release uses the established America/Los_Angeles vocabulary, with this source wording retained for recheck; no fixed UTC offset is inferred.',release,'claim-taboose-release-time-wording')
    issuance=b.claim('issuance','printing',ROUTE,'wilderness_permit_process',
        {'channel':'Recreation.gov','print_at_home_days_before':7,'overnight_no_show_deadline':'10:00 on entry date',
         'required':['paper copy','signature','group leader possession'],'reservation_letter_is_permit':False,
         'changes_after_printing':'visitor center reissue','office':'Inyo wilderness permit office; verify open hours'},
        'Permit Printing Instructions: print at most seven days ahead; overnight no-show deadline 10am entry day; carry a signed paper permit. Reservation letter is not a permit; changes after printing require a visitor center.',recheck=True)
    b.claim('permit-fees','permits',ROUTE,'wilderness_permit_fee',
        {'reservation_usd':6,'per_person_usd':5,'currency':'USD','basis':'one non-Whitney wilderness permit; all ages count; no per-night charge',
         'applicability':{'activities':['hiking'],'overnight':True},'requires_current_check':True,'not_a_trip_total':True},
        'USFS Fees: $6 per permit plus $5/person outside Whitney Zone, all ages, no per-night charge; no pass, senior, military or child discount. Taboose-to-pass scope does not enter Whitney Zone.',recheck=True)
    b.claim('permit-cancellation','permits',ROUTE,'permit_cancellation_policy',
        {'per_person_refund':'cancel at least 12 days before entry','reservation_fee_refundable':False,
         'transferable':False,'leader_changes':False,'entry_change':'quota-dependent; date changes at least 12 days ahead'},
        'USFS cancellations and Recreation.gov: per-person fee refunded with cancellation at least 12 days before entry; $6 reservation fee nonrefundable; leader/alternate cannot be added/changed and reservations cannot be transferred.',recheck=True)
    b.claim('additional-documents','printing',ROUTE,'permit_supporting_documents',
        {'stove_use':'California Campfire Permit required by printing instructions',
         'park_entry':'print Sequoia and Kings Canyon Minimum Impact Wilderness Regulations',
         'jmt_pctravel':'JMT Minimum Impact Wilderness Regulations recommended'},
        'USFS Permit Printing Instructions lists a California Campfire Permit for stove operation, required SEKI regulations printout for entering the park, and recommended JMT regulations for JMT/PCT travel. Other orders may limit stove use despite a permit.',recheck=True)
    b.claim('continuous-travel','permits',ROUTE,'cross_jurisdiction_permit_policy',
        {'issuer':'entry agency: Inyo for Taboose start','continuous_trip':'one entry-agency permit accepted across adjacent park/forest',
         'break':'new permit from next entry agency, subject to stated long-distance resupply exceptions',
         'whitney_exit':'requires Trail Crest exit product/quota if added; outside this route scope'},
        'USFS What Permit Do I Need and JMT sections: agency at the trip start issues the permit, including when first night is in an adjacent park; continuous travel required. Separate Whitney exit provisions are not satisfied by merely choosing Taboose.',recheck=True)
    group=b.claim('group-limit','use-order',ROUTE,'wilderness_group_size_limit',{'maximum_persons':15,'includes_day_use':True,'order':'05-04-50-25-02','exemptions':['specifically exempt FS-7700-48','official duty']},
        'Wilderness Use order item 2 caps groups at 15; Taboose Restrictions explicitly includes day use. This is a group limit, distinct from the 10-person daily entry quota.',time=USE_TIME)
    b.rule('group-limit',group,'Keep a Taboose wilderness party to at most 15 people; separate permits cannot combine to evade the limit. Order exemptions require specific authorization or official duty.',trail_scopes,time=USE_TIME)
    food=b.claim('food-storage','regulations',ROUTE,'wilderness_food_storage',
        {'methods':['bear-resistant container','counterbalance at least 15 feet high and 10 feet from trunk'],
         'inadequate_trees':'bear container required','items':['food','trash','scented items','pet food'],
         'scope':'Inyo portion; park rules separately apply'},
        'Inyo Wilderness Regulations and Taboose Restrictions permit a bear container or specified counterbalance outside mandatory-container zones; the regulations require a container if trees cannot support a compliant hang.',recheck=True)
    b.rule('food-storage',food,'Store food, refuse and scented items in a bear-resistant container or an allowed counterbalance at least 15 feet high and 10 feet from the trunk; carry a container where suitable trees are absent. Recheck mapped storage zones and park continuation rules.',trail_scopes)
    meta=b.claim('food-order-metadata','food',ROUTE,'published_order_metadata_conflict',
        {'alert_start':'2023-06-18','embedded_order_effective_start':'2025-06-18','end':'2027-06-18',
         'page_order_number':'05-04-50-23-03','linked_filename':'05-04-50-25-03'},
        'Food and Refuse Storage page gives alert start 2023 and number 23-03, but embedded effective text starts June 18, 2025 and linked filename uses 25-03. These metadata disagree.',recheck=True)
    b.gap('food-order-metadata','Which food-storage order version is current?',
        'Official alert metadata, embedded text and linked filename disagree on start year/order number. General storage obligations are corroborated by current regulations/trail guidance; confirm current signed order and maps before travel.',food,meta,ROUTE)
    campfire=b.claim('campfire-restriction','fire-map',ROUTE,'campfire_restriction',
        {'area':'Taboose Creek drainage, Exhibit P','above_elevation_feet':10400,'order':'05-04-50-25-04',
         'precision':'mapped drainage zone; no screenshot-traced polygon'},
        'Order 05-04-50-25-04 maps PDF page 15, Exhibit P: black hatching prohibits fires in Taboose Creek drainage; purple hatching prohibits fires above 10,400 feet. Trail page also states no fires along Taboose Creek.',time=FIRE_TIME,recheck=True)
    b.rule('campfire-restriction',campfire,'Do not build or use campfires in the mapped Taboose Creek drainage or above 10,400 feet under 05-04-50-25-04. Consult Exhibit P; wilderness/campfire permits do not waive the ban. Specific authorization and official-duty exceptions apply.',trail_scopes,time=FIRE_TIME)
    b.claim('stove-exception','fire-order',ROUTE,'portable_stove_exception',
        {'allowed_by_this_order':'gas, jellied petroleum or pressurized liquid fuel portable stove/lantern',
         'permit':'valid wilderness permit or California Campfire Permit issued by Forest Service',
         'other_orders_still_apply':True},
        'Signed order 05-04-50-25-04 page 1 exception 3 permits specified portable stoves/lanterns for holders of a valid wilderness or California campfire permit; neither permit waives campfire prohibitions.',time=FIRE_TIME,recheck=True)
    stage=b.claim('stage1','stage1',ROUTE,'seasonal_fire_restrictions',
        {'order':'05-04-50-26-23','prohibited':'fire, campfire, stove fire and charcoal outside listed developed sites',
         'stove_exception':'California Campfire Permit plus pressurized liquid petroleum/LPG stove or lantern with shutoff valve',
         'scope':'Inyo National Forest; not county campground or NPS by inference'},
        'Stage 1 order 05-04-50-26-23 runs June 22-December 31, 2026. Its portable-stove exception is narrower than the standing wilderness order: California Campfire Permit, pressurized liquid petroleum/LPG fuel and shutoff valve.',time=STAGE_TIME,recheck=True)
    b.gap('fire-current','What current fire and stove restrictions apply on the trip date?',
        'Layered orders differ in stove exception wording. The standing order expires June 10, 2027 and Stage 1 December 31, 2026 unless changed. Recheck both and current alerts; expiry is not evidence of permission.',campfire,stage,ROUTE)
    camp_set=b.claim('camping-setback','use-order',ROUTE,'camping_setback',{'minimum_feet':100,'from':['lakeshore','stream','National Forest System trail'],'order':'05-04-50-25-02'},
        'Wilderness Use order Exhibit A prohibits camping within 100 feet of any lakeshore, stream or National Forest System trail; no Taboose numbered wilderness camps are assigned.',time=USE_TIME)
    b.rule('camping-setback',camp_set,'Camp at least 100 feet from lakeshores, streams and National Forest System trails in the Inyo wilderness portion; use durable previously impacted sites. The permit does not assign a campsite.',trail_scopes,(Condition('activity.overnight','equals',True),),USE_TIME)
    for key,predicate,value,text in [
        ('sanitation','sanitation_guidance',{'burial_depth_inches':[6,8],'setback_feet_at_least':100,'from':['water','camps'],'trash':'pack out'},'Inyo regulations: bury solid human waste 6-8 inches deep at least 100 feet from water or camps; dispose of wash water at least 100 feet away and pack out trash.'),
        ('pets','pet_policy',{'national_forest':'allowed under leash or responsive voice control; no wildlife harassment','waste_setback_feet':100},'Inyo Pets section permits controlled pets on National Forest trips and requires waste/food care. This claim covers only the eastern National Forest route; the western continuation has separately scoped NPS evidence.'),
        ('stock','stock_restrictions',{'maximum_head':25,'pack_goats':'prohibited west of US 395','loose_herding':'prohibited except unsafe-to-tie trail portions','route_suitability':'not recommended'},'Inyo regulations cap stock at 25 and prohibit pack goats west of US 395; Taboose trail is explicitly not recommended for stock. Legal stock rules do not establish physical passability.'),
        ('equipment-use','wilderness_use_restrictions',{'wheeled_vehicles':'prohibited under use order','scope':'Inyo wilderness, not the road approach'},'Inyo Wilderness Use order item 9 prohibits wagons, carts and other vehicles within wilderness. This is not a motor-vehicle ban on the access road.'),
    ]:
        b.claim(key,'regulations' if key!='equipment-use' else 'use-order',ROUTE,predicate,value,text,recheck=True)
    b.claim('drones','recgov',ROUTE,'wilderness_drone_restriction',{'prohibited':True,'scope':'wilderness'},
        'Recreation.gov Inyo wilderness permit Need to Know explicitly prohibits drones in wilderness.')
    water=b.claim('creek-water','trail','waterway-taboose-creek','water_treatment_guidance',
        {'treatment_required_before_drinking':True,'flow':'unknown','safe_crossings':'unknown'},
        'Taboose Water Available says creek, lake and spring water should be treated before drinking. It is not a dated flow or safe-crossing observation.',scopes=trail_scopes,recheck=True)
    b.rel('creek-corridor',SEGMENT,'follows','waterway-taboose-creek',profile)
    condition=b.claim('trail-condition-20260826','nps-conditions',ROUTE,'dated_trail_condition',
        {'report_date':'2026-08-26','brush':'overgrown and brushy','creek_crossings':'washed out','stock':'not recommended',
         'current_status':'unknown; recheck'},
        'NPS Trail Conditions, Taboose Pass entry dated August 26, 2026 reports heavy brush and washed-out creek crossings, and advises against stock. The entry does not identify individual crossing coordinates.',
        observed=datetime(2026,8,26,tzinfo=timezone.utc),time=TemporalScope(date(2026,8,26),date(2026,8,26)),recheck=True)
    b.gap('water-crossings','Where are usable water collection points and safe crossings on the trip date?',
        'The route follows Taboose Creek, but no current flow, exact crossing inventory, safe ford or facility spur is evidenced. The dated NPS report describes washouts. Do not manufacture crossing nodes or timeless drinking-water availability.',water,condition,ROUTE)
    roadcheck=b.claim('road-recheck','roads',ROAD,'pretrip_current_conditions_recheck',
        {'required':True,'topics':['road damage','closures','vehicle suitability','parking'],'current_status':'unknown'},
        'Inyo County road-status page and linked closure documents are the official road recheck destination. The retrieved index alone does not establish this road open or suitable for any vehicle.',scopes=access_scopes,recheck=True)
    b.gap('access-geometry','Is there reviewed official geometry and current clearance for the approach road?',
        'The named road approach is supported by USFS directions and map, but no reviewed official road polyline or highway-junction coordinates are imported. Trail geometry begins at the trailhead. Exact road jurisdiction divisions, clearance, turnarounds and parking capacity remain unverified.',road,roadcheck,geo)
    b.gap('route-limits','Which alternatives, camps and western continuations are modeled?',
        'The entire named eastern trailhead-to-pass route and separate US 395 road approach are connected. Intermediate campsite spurs, crossing positions, alternate trails and the western JMT network are not modeled. The NPS stock atlas shows west-side branching; this batch does not choose an onward branch or infer a Bench Lake facility visit.',ROUTE,profile,geo)

    west=b.claim('west-jurisdiction','map',WEST,'jurisdiction_transition',
        {'east':LAND,'west':PARK,'transition':'Taboose Pass','beyond_scope':'JMT and Upper Basin'},
        'Independence Area Trails page 1 shows the named pass on the Forest Service / Kings Canyon boundary; the trail continues west in Kings Canyon. This zone denotes only the western continuation, not the entire eastern trail.',recheck=True)
    b.claim('west-topology-context','nps-atlas',WEST,'mapped_continuation_context',
        {'map_panel':'Mt. Pinchot, printed page 11, PDF page 13','edition':'2014 planning atlas','western_branching':True,'not_imported_as_route':True},
        'SEKI Wilderness Stewardship Plan Stock Regulations Atlas part 2, Mt. Pinchot panel shows Taboose Pass on the park boundary, a branching trail toward the JMT and Bench Lake area, and a hatched stock restriction area. This historical map supports context, not current stock permission.',recheck=True)
    for key,predicate,value,text in [
        ('west-pets','pet_policy',{'pets_allowed':False},'NPS Minimum Impact Restrictions: pets are not allowed in park wilderness.'),
        ('west-fire','campfire_restriction',{'above_elevation_feet':10000,'park':'Kings Canyon','additional_current_orders':True},'NPS Minimum Impact Restrictions: Kings Canyon campfires prohibited above 10,000 feet; additional current fire restrictions may apply.'),
        ('west-food','wilderness_food_storage',{'methods':['approved portable container','permanent food box','compliant counterbalance'],'without_box_or_trees':'approved container required','mandatory_container_zones':'separate named areas; check onward itinerary'},'NPS Minimum Impact Restrictions permits approved containers, permanent boxes or counterbalance, but requires a container where boxes/adequate trees are absent; mandatory-container areas depend on itinerary.'),
        ('west-camping','camping_setback',{'never_within_feet_of_water':25,'between_25_and_100_feet':'only previously established sites','surface':'durable; no meadows/vegetation'},'NPS campsite selection differs from Inyo: no camping within 25 feet of water; 25-100 feet only at established sites; durable surfaces required.'),
        ('west-group','group_size_guidance',{'overnight_on_trail':15,'overnight_off_trail':12,'day_hiking':25,'exceptions':'other named areas and stock have separate limits','affiliated_separation_miles':0.5},'NPS Party Size Limits gives 15 on trail/12 off trail with named exceptions, affiliated separation, and a separate 25-person day-hiking maximum; the Inyo eastern approach still caps groups at 15.'),
    ]:
        b.claim(key,'nps-rules',WEST,predicate,value,text,recheck=True)
    for key,predicate,value,text in [
        ('west-wheeled-equipment','wilderness_wheeled_vehicle_restriction',{'prohibited':True,'scope':'park wilderness'},'NPS General Travel Requirements prohibits all wheeled vehicles in park wilderness.'),
        ('west-motorized-equipment','wilderness_motorized_equipment_restriction',{'prohibited':True,'scope':'park wilderness'},'NPS General Travel Requirements prohibits all motorized equipment in park wilderness.'),
        ('west-weapon-discharge','weapon_discharge_restriction',{'prohibited':True,'covers':['firearms','other weapons'],'distinct_from_possession':True},'NPS General Travel Requirements prohibits discharging a firearm or other weapon; this statement concerns discharge, not possession.'),
        ('west-weapon-possession','qualified_weapon_possession_policy',{'published_general_statement':'weapon possession prohibited, including bear spray','firearm_qualification':'firearm possession is subject to state regulations','not_a_blanket_firearm_possession_ban':True},'NPS General Travel Requirements states a weapon-possession prohibition including bear spray, while separately qualifying firearm possession by state regulations. These statements are retained together without extending the general prohibition to all firearm possession.'),
        ('west-overnight-permit','overnight_permit_carry_policy',{'overnight_permit_required':True,'signed_copy_in_permittee_possession':True,'present_on_authorized_request':True,'entry_agency_policy_claim':'claim-taboose-continuous-travel'},'NPS General Travel Requirements requires a signed permit for overnight travel, carried by the permittee and shown to authorized personnel on request. The separately sourced entry-agency policy governs a continuous Inyo-entry trip.'),
        ('west-trail-shortcuts','trail_shortcut_restriction',{'shortcuts_allowed':False},'NPS General Travel Requirements prohibits trail shortcuts to protect vegetation and reduce erosion.'),
        ('west-trail-markers','trail_marker_restriction',{'build_rock_cairns':False,'build_other_trail_markers':False},'NPS General Travel Requirements prohibits constructing rock cairns or other trail markers.'),
        ('west-trash','wilderness_waste_packout',{'pack_out_all_trash':True,'includes_toilet_paper':True},'NPS General Travel Requirements requires packing out all trash, including toilet paper.'),
        ('west-drift-gates','drift_fence_gate_policy',{'close_gates_after_passing':True,'route_gate_inventory':'unknown'},'NPS General Travel Requirements directs visitors to close drift-fence gates after passage. This does not establish that a particular gate exists on the Taboose continuation.'),
    ]:
        b.claim(key,'nps-rules',WEST,predicate,value,text,recheck=True,retrieved=REVIEW_RETRIEVED)
    b.gap('west-weapons-interpretation','How do the qualified NPS weapon-possession statements apply to the planned equipment?',
        'The NPS page states a weapon-possession prohibition including bear spray but separately says firearm possession is subject to state regulations. Discharge is independently prohibited. State-law eligibility, exceptions and equipment-specific interpretation have not been reviewed; confirm with the park before travel. Do not infer a blanket firearm possession ban or general permission.',WEST,'claim-taboose-west-weapon-possession','claim-taboose-west-weapon-discharge')
    b.claim('west-grazing','nps-stock',WEST,'stock_grazing_restriction',
        {'taboose_pass_area':'open to grazing except a 12-acre wet meadow at 11,000 feet','seasonal_opening':'requires current check','route_suitability':'not established by grazing permission'},
        'NPS permanent Stock Use and Grazing Restrictions, South Fork Kings/Woods Creek: Taboose Pass area excludes the 12-acre wet meadow at 11,000 feet from grazing. Annual opening and special restrictions still need recheck.',recheck=True)
    b.claim('cross-boundary-recheck','permits',ROUTE,'pretrip_current_conditions_recheck',
        {'required':True,'topics':['entry agency permit','park food, pet, stock, camping and fire rules'],'western_zone_id':WEST},
        'USFS requires travelers to obey the different rules in each jurisdiction crossed; the western continuation has separately linked NPS claims. Reaching the pass does not establish an onward itinerary.',recheck=True)
    b.gap('western-scope','What applies if continuing west of Taboose Pass?',
        'NPS restrictions and stock-area context are represented separately. Onward route, camps, daily stock opening, food-storage zones, and exact branch choices require itinerary-specific review. No NPS prohibition is projected onto the entire Inyo approach.',WEST,west,'claim-taboose-cross-boundary-recheck')

    campaccess=b.claim('camp-access','camp',CAMP,'campground_access',
        {'road':'Taboose Creek Road','from':'US 395, 14 miles north of Independence','distance_miles_from_highway':2,'not_trailhead':True},
        'County campground Location: turn west on Taboose Creek Road from US 395, 14 miles north of Independence, two miles to campground. This is distinct from USFS trailhead directions of approximately six road miles.')
    b.rel('camp-road',ROAD,'provides_access_to',CAMP,campaccess)
    b.rel('roadleg-camp',ROAD_SEGMENT,'provides_access_to',CAMP,campaccess)
    b.rel('camp-operator',CAMP,'operated_by','agency-inyo-county-parks',campaccess)
    inventory=b.claim('camp-inventory','camp',CAMP,'site_inventory',{'published_spaces':35,'live_availability':'unknown'},
        'County campground Amenities lists 35 camp spaces; this is an inventory statement, not availability.',recheck=True)
    mapinv=b.claim('camp-map-inventory','camp-map',CAMP,'mapped_site_inventory',
        {'numbered_sites':[1,36],'count':36,'edition':'unstated; URL uploaded 2025-05','facilities':['restrooms','trash','well house','pay station','day use'],'not_georeferenced':True},
        'County campground map, page 1: numbered sites 1-36, restroom and trash symbols, well house, pay station and day-use areas. Reviewed visually; no coordinates or campsite geometry traced.',recheck=True)
    booking=b.claim('camp-booking-inventory','booking',CAMP,'reserveamerica_campsite_inventory',
        {'listed_sites':36,'site_type':'Standard Non-Electric','availability':'unknown','provider_facility_id':'INYO/1100013'},
        'ReserveAmerica campground listing, browser review October 6, 2026: ALL 36 and Standard Non-Electric 36; first page shows sites 1-20 of 36. No date-specific availability search or booking was performed.',recheck=True)
    b.gap('camp-count-conflict','Does the campground currently have 35 or 36 sites?',
        'Conflict: county overview lists 35 spaces; county map labels 1-36 and ReserveAmerica lists 36 standard non-electric sites. Preserve all three and verify current inventory; no individual site catalog or availability is inferred.',CAMP,inventory,mapinv,booking)
    for key,kind,name in [('toilets','restroom','vault toilets'),('well','water_source','water well')]:
        eid='facility-taboose-camp-'+key
        c=b.claim('camp-'+key,'camp',eid,'facility_inventory',{'type':name,'current_operation':'unknown'},
            f'County campground Amenities explicitly lists {name}. Facility existence is separate from current operation and water quality.',scopes=(scope(CAMP),scope(eid)),recheck=True)
        b.rel('camp-'+key+'-contains',eid,'part_of',CAMP,c)
        b.rel('camp-'+key+'-access',CAMP,'provides_access_to',eid,c)
    b.claim('camp-amenities','camp',CAMP,'shared_facilities',
        {'tables':True,'grills':True,'fire_rings':True,'stream_fishing':True,'showers':False,'hookups':False,'larger_rv_accommodation':'published; site fit requires check'},
        'County Amenities lists tables, grills, fire rings, stream fishing and larger RV accommodation; no showers or hookups. These attributes belong to the county campground, not the pass trailhead.')
    b.claim('camp-fees','camp',CAMP,'fees',{'per_vehicle_per_night_usd':14,'additional_vehicle_per_night_usd':5,'payment':['cash','credit card'],'requires_current_check':True,'basis':'campground stay; not a trailhead fee'},
        'County Fee Information: $14/vehicle/night, $5/additional vehicle/night; automated pay stations accept credit cards or cash.',recheck=True)
    b.claim('camp-booking','camp',CAMP,'campground_booking_policy',{'channels':['ReserveAmerica','first come first served'],'availability':'unknown','url':SOURCES['booking'][0]},
        'County page links ReserveAmerica for reservations and also states first-come-first-served sites exist. This does not guarantee a site.',recheck=True)
    b.claim('camp-booking-rate','booking',CAMP,'published_booking_rate',{'nightly_usd':14,'season':'January 1-December 31, 2026','excludes':'discounts, attribute fees, taxes and incremental charges'},
        'ReserveAmerica expanded Fees & Cancellations panel lists standard non-electric nightly rate $14 for the 2026 peak season; the rate notice excludes additional charges.',recheck=True)
    b.claim('camp-occupancy','camp',CAMP,'people_per_campsite',{'maximum':6},'County campground page limits each site to six people.')
    b.claim('camp-fire','camp',CAMP,'campground_fire_rule',{'only_in':'fire rings','requires_current_check':True},'County campground page permits campfires only in fire rings; current restrictions still need confirmation.',recheck=True)
    notice=b.claim('camp-water-notice','water-notice','facility-taboose-camp-well','dated_water_monitoring_notice',
        {'distributed_on':'2026-07-30','affected_month':'2026-05','issue':'routine total-coliform sampling missed; water quality not assured for that period',
         'not_a_positive_contamination_test':True,'notice_advice':'no action needed at that time; not an emergency',
         'followup_wording':'sample will be taken in June','current_quality':'unknown','water_system_id':'CA1400516'},
        'County drinking-water notice, pages 1-2, visually read scan: missed May 2026 routine total-coliform sample; quality during that period uncertain. Notice says not an emergency/no action then; table says one sample and June follow-up; narrative says sample will be taken in June, yet distribution date is July 30, 2026.',
        scopes=(scope(CAMP),scope('facility-taboose-camp-well')),observed=datetime(2026,7,30,tzinfo=timezone.utc),
        time=TemporalScope(date(2026,5,1),date(2026,5,31)),recheck=True)
    b.gap('camp-water-current','Is campground well water available and suitable for drinking now?',
        'Well/map inventory does not prove current water quality. The July 30 notice concerns missed May monitoring and retains prospective June wording; follow-up results are not supplied. It is not evidence of a positive contamination test or a boil-water order. Ask the county for current results and operation.',CAMP,notice,'claim-taboose-camp-well')
    b.gap('camp-depth','What campsite-specific fit, booking terms and fishing restrictions apply?',
        'Normal-depth aggregate inventory, mapped facilities, fees and reservation channel are covered. Individual 36-site profiles, advance booking window/cancellation detail, current site availability and CDFW water-specific fishing regulations remain deferred. County fishing season summary is not promoted as the complete fishing law.',CAMP,booking,'claim-taboose-camp-booking')
    b.r.derived_results.append(DerivedResult(MANIFEST,'pretrip_recheck',
        {'required':True,'topics':['road and trail conditions','permit/quota/issuance','source conflicts','fire and food rules',
         'cross-boundary rules','water and campground operation','geometry and mileage limitations']},
        tuple(b.inputs),'Project Taboose source evidence, dated conditions and gaps onto the selected trail, road, campground or western-continuation context. No live availability or permission inferred.'))
    return b.r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=ROOT)
    p.add_argument('--output',type=Path,default=ROOT)
    p.add_argument('--reviewed-input',type=Path)
    a=p.parse_args(); path=a.output/SNAPSHOT
    if a.reviewed_input:
        raw=a.reviewed_input.read_bytes()
        payload=snapshot_from_reviewed(json.loads(raw),hashlib.sha256(raw).hexdigest())
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    raw=path.read_bytes(); base=load_canonical(a.base)
    records=build_records(base,json.loads(raw),hashlib.sha256(raw).hexdigest())
    ops=[]
    for kind,(collection,ident,_) in RECORD_SPECS.items():
        for record in getattr(records,collection):
            rid=getattr(record,ident)
            ops.append(ChangeOperation(ChangeAction.ADD,kind,rid,f'canonical/v0/{collection}/{rid}.json',
                'Add authoritative Taboose access-to-pass planning coverage with preserved uncertainty.',
                evidence_refs=getattr(record,'evidence_ids',()),knowledge_gap_refs=(rid,) if kind=='gap' else ()))
    change=ChangeSet(CHANGE_ID,records,summary='Add Taboose Pass road/trail topology, official display geometry, jurisdiction-specific planning evidence, permits, facilities, restrictions and rechecks.',operations=tuple(ops))
    service=ChangeSetWriteService(InMemoryCanonicalRepository(base))
    service.propose(change,'taboose-source-ingestion')
    errors=service.validate(CHANGE_ID,'taboose-validator')
    if errors:raise RuntimeError('\n'.join(errors))
    candidate=service.prepare(CHANGE_ID,'taboose-candidate-builder')
    write_candidate(a.output,candidate,service.get(CHANGE_ID))
    print(f'Prepared {len(ops)} records in one validated ChangeSet; not published.')


if __name__=='__main__':main()
