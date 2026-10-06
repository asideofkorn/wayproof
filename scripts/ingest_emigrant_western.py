#!/usr/bin/env python3
"""Prepare six western Emigrant approaches, display geometry and access evidence.

Use --base at pre-batch main. --reviewed-input accepts only the reviewed USFS
query artifact; no remote acquisition or publication occurs in this builder.
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

ROOT = Path(__file__).resolve().parents[1]
CHANGE_ID = 'wp-20261006-emigrant-western-coverage'
SNAPSHOT = 'geometry/v0/snapshots/usfs-emigrant-western-routes-20261006.geojson'
MANIFEST = 'result-emigrant-western-pretrip-recheck'
ACCESS_MANIFEST = 'result-emigrant-western-access-recheck'
LAND = 'wilderness-emigrant'
RETRIEVED = datetime(2026, 10, 6, 7, 44, 34, tzinfo=timezone.utc)
GEOMETRY_RETRIEVED = '2026-10-06T00:09:34+00:00'
QUERY = {'f': 'geojson', 'where': '1=1', 'geometry': '-119.91,38.13,-119.70,38.27',
    'geometryType': 'esriGeometryEnvelope', 'inSR': '4326',
    'spatialRel': 'esriSpatialRelIntersects',
    'outFields': 'objectid,trail_name,trail_no,trail_cn,bmp,emp,segment_length,gis_miles,globalid,admin_org',
    'outSR': '4326', 'returnGeometry': 'true'}
FS = 'https://www.fs.usda.gov/sites/nfs/files/'
SOURCES = {
    'chewing-camping-map': FS + 'legacy-media/stanislaus/Chewing%20Gum%20Lake%20-%20Minimum%20Camping%20Distances%202021.pdf',
    'grouse-camping-map': FS + 'legacy-media/stanislaus/Grouse%20Lake%20-%20Minimum%20Camping%20Distances%202021.pdf',
    'traveler-2023': FS + 'legacy-media/stanislaus/Traveler%202023.pdf',
    'occupancy-order': FS + 'r05/stanislaus/publication/alerts/STF-16-2026-09%20Occupancy%20and%20Use-Camping%20Limits%20Order%20%28final%29.pdf',
    'occupancy-page': 'https://www.fs.usda.gov/r05/stanislaus/alerts/forest-order-limiting-occupancy-and-use-remains-effect',
}
OPERATOR = 'https://www.aspenmeadowpackstation.com/index.php/adventures-menu/destinations/'
for key, path in [('chewing', 'gianellis-trail-head-menu/chewing-gum-lake-menu'),
                  ('grouse', 'crabtree-trail-head-menu/grouse-lake-menu'),
                  ('gem', 'crabtree-trail-head-menu/gem-menu')]:
    SOURCES['aspen-' + key] = OPERATOR + path


def source(key): return 'source-' + ('aspen-emigrant-' + key[6:] if key.startswith('aspen-') else 'usfs-emigrant-' + key)
def th(key): return 'trailhead-emigrant-' + key
def route(key): return 'route-emigrant-' + key + '-lake'
def lake(key): return 'waterbody-emigrant-' + key + '-lake'
def node(key): return 'route-node-emigrant-' + key
def segment(key): return 'route-segment-emigrant-western-' + key
def scope(eid):
    return 'scope-emigrant-' + eid.removeprefix('trailhead-emigrant-') if eid.startswith('trailhead-emigrant-') else 'scope-' + eid

def old_segment(key): return 'route-segment-emigrant-crabtree-' + key

# Review assignments are source-vertex positions, not official point features.
# A feature break or lake approach is deliberately a separate descriptive node.
# key, source feature, inclusive start/end vertex, graph endpoints, map support
LEGS = (
 ('gianelli-burst', 9429323, 0, 67, th('gianelli'), node('burst-display-break'), '20E14 from Gianelli over Burst Rock; source-feature break east of Burst Rock'),
 ('burst-powell-junction', 9505484, 0, 73, node('burst-display-break'), node('powell-junction'), '20E14 continues east toward the Powell Lake branch'),
 ('powell-spur', 9430968, 0, 22, node('powell-junction'), node('powell-trail-end'), 'named USFS 20E14A POWELL LAKE SPUR; Powell access corroborated by 2018 hiking guide'),
 ('powell-lake-valley', 9505484, 73, 290, node('powell-junction'), node('burst-lake-valley-junction'), '20E14 continues to the explicitly drawn 19E21 Lake Valley junction'),
 ('north-chewing', 9429539, 267, 200, node('burst-lake-valley-junction'), node('chewing-west-approach'), '19E21 south from 20E14 to the west-side system trail at Chewing Gum Lake; lake detail map labels To Gianelli Trailhead'),
 ('lake-valley-lower', 9430389, 0, 167, node('lake-valley-junction'), node('lake-valley-display-break'), '19E21 branches northeast from Crabtree mainline toward Lake Valley'),
 ('south-chewing', 9429539, 0, 200, node('lake-valley-display-break'), node('chewing-west-approach'), '19E21 continues northeast to the west-side system trail at Chewing Gum Lake'),
 ('bell-pine', 9431555, 0, 343, th('bell-meadow'), node('bell-pine-junction'), '20E17 from Bell Meadow to the drawn 19E10 Pine Valley junction'),
 ('pine-grouse-break', 9431555, 343, 436, node('bell-pine-junction'), node('grouse-display-break'), '20E17 east from the Pine Valley junction toward Grouse Lake'),
 ('grouse-approach', 9429412, 0, 120, node('grouse-display-break'), node('grouse-north-approach'), '20E17 continues along the north side of Grouse; lake detail map labels To Crabtree Trailhead'),
 ('pine-connector', 9430585, 0, 146, node('pine-valley-junction'), node('bell-pine-junction'), '19E10 connects Crabtree 20E16 to Bell Meadow 20E17 in Pine Valley'),
 ('bear-groundhog', 9430618, 806, 477, node('bear-junction'), node('crabtree-groundhog-junction'), '20E16 continues east past Piute Meadow to the drawn 19E90 Groundhog Meadow branch'),
 ('groundhog-gem', 9430618, 477, 257, node('crabtree-groundhog-junction'), node('crabtree-gem-junction'), '20E16 continues east past Piute Lake to its 20E98 Gem Lake branch'),
 ('gem-approach', 9429611, 71, 40, node('crabtree-gem-junction'), node('gem-east-approach'), '20E98 branches south from 20E16 and passes the east side of Gem Lake'),
)
ROUTES = {
 'gianelli-powell': ('Gianelli to Powell Lake', 'gianelli', 'powell', 'powell-trail-end', ['gianelli-burst','burst-powell-junction','powell-spur'], 2.3),
 'gianelli-chewing-gum': ('Gianelli to Chewing Gum Lake', 'gianelli', 'chewing-gum', 'chewing-west-approach', ['gianelli-burst','burst-powell-junction','powell-lake-valley','north-chewing'], 4.1),
 'crabtree-chewing-gum': ('Crabtree to Chewing Gum Lake', 'crabtree', 'chewing-gum', 'chewing-west-approach', [old_segment('start-lake-valley'),'lake-valley-lower','south-chewing'], 4.4),
 'bell-meadow-grouse': ('Bell Meadow to Grouse Lake', 'bell-meadow', 'grouse', 'grouse-north-approach', ['bell-pine','pine-grouse-break','grouse-approach'], 4.8),
 'crabtree-grouse': ('Crabtree to Grouse Lake', 'crabtree', 'grouse', 'grouse-north-approach', [old_segment('start-lake-valley'),old_segment('lake-valley-pine-valley'),'pine-connector','pine-grouse-break','grouse-approach'], None),
 'crabtree-gem': ('Crabtree to Gem Lake', 'crabtree', 'gem', 'gem-east-approach', [old_segment(k) for k in ('start-lake-valley','lake-valley-pine-valley','pine-valley-camp','camp-bear-junction')] + ['bear-groundhog','groundhog-gem','gem-approach'], 9.5),
}
NODES = {
 'burst-display-break': 'Burst Rock eastern trail display break', 'powell-junction': 'Powell Lake spur junction',
 'powell-trail-end': 'Powell Lake mapped trail terminus', 'burst-lake-valley-junction': 'Burst Rock–Lake Valley trail junction',
 'chewing-west-approach': 'Chewing Gum Lake western trail approach', 'lake-valley-display-break': 'Lake Valley Trail source-feature break',
 'bell-pine-junction': 'Bell Meadow–Pine Valley trail junction', 'grouse-display-break': 'Western Grouse approach source-feature break',
 'grouse-north-approach': 'Grouse Lake northern trail approach', 'crabtree-groundhog-junction': 'Crabtree–Groundhog Meadow trail junction',
 'crabtree-gem-junction': 'Crabtree–Gem Lake trail junction', 'gem-east-approach': 'Gem Lake eastern trail approach',
}
RESOURCE_LEGS = {'powell-spur': 'powell', 'north-chewing': 'chewing-gum', 'south-chewing': 'chewing-gum', 'grouse-approach': 'grouse', 'gem-approach': 'gem'}
REPLACEMENTS = {'gap-emigrant-route-topology', 'gap-emigrant-facility-inventory', 'gap-emigrant-crabtree-planning-limits', 'gap-emigrant-crabtree-geometry-limitations'}


def snapshot_from_reviewed(raw):
    features = {f['properties']['objectid']: f for f in raw['features']}
    assert len(features) == 45
    out = []
    for key, fid, start, end, *_ in LEGS:
        f = features[fid]
        guid, count, trail = EXPECTED[fid]
        assert f['properties']['globalid'] == guid
        assert f['properties']['trail_no'] == trail
        assert f['geometry']['type'] == 'LineString'
        assert len(f['geometry']['coordinates']) == count
        step = 1 if end > start else -1
        coords = [f['geometry']['coordinates'][i] for i in range(start, end + step, step)]
        out.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': coords},
            'properties': {'feature_id': 'usfs-emigrant-western-' + key,
                'source_attributes': f['properties'], 'source_vertex_range_inclusive': [start, end],
                'source_vertex_count': count,
                'source_geometry_sha256': hashlib.sha256(json.dumps(f['geometry'], sort_keys=True).encode()).hexdigest(),
                'xy_accuracy': 'unknown; coordinate digits are not an accuracy statement',
                'length_field_scope': 'whole original source feature, not the selected slice'}})
    return {'type': 'FeatureCollection', 'wayproof': {'source': SERVICE, 'source_id': SOURCE_ID,
        'publisher': 'USDA Forest Service', 'classification': 'public_domain',
        'retrieved_at': GEOMETRY_RETRIEVED, 'reviewed_at': RETRIEVED.isoformat(),
        'query_endpoint': SERVICE + '/query', 'query_parameters': QUERY, 'query_feature_count': 45,
        'source_coordinate_reference_system': 'EPSG:4269', 'normalized_coordinate_reference_system': 'EPSG:4326',
        'navigation_grade': False,
        'processing': 'Reviewed contiguous source-vertex slices; no snapping, interpolation, simplification, rounding or mileage calculation.',
        'review_basis': '2010 Emigrant geospatial overview; Chewing Gum and Grouse minimum camping maps; 2012 mileage table; 2018 hiking guide; named USFS trails. Lake approach positions are descriptive display endpoints, not surveyed official lake points or campsites.',
        'endpoint_mismatches': 'Lake Valley/Crabtree, Powell spur/Burst Rock and Pine Valley/Bell Meadow have small unsnapped coordinate offsets. Explicit mapped or described connectivity supplies the graph, not coordinate proximity.'}, 'features': out}


def build_records(base, snapshot, digest):
    r = CanonicalRecords()
    inputs, access_inputs = [], []
    for key, url in SOURCES.items():
        r.sources.append(Source(source(key), url, 'Aspen Meadow Pack Station' if key.startswith('aspen-') else 'USDA Forest Service, Stanislaus National Forest'))

    def entity(eid, kind, name):
        r.entities.append(Entity(eid, kind, name)); r.spatial_scopes.append(SpatialScope(scope(eid), kind, eid))

    def claim(key, src, text, subject, predicate, value, scopes=None, access=False, temporal=None):
        cid, oid, evid = ('claim-emigrant-western-' + key, 'observation-emigrant-western-' + key, 'evidence-emigrant-western-' + key)
        sid = SOURCE_ID if src == 'geometry' else source(src)
        r.observations.append(Observation(oid, sid, text, retrieved_at=datetime.fromisoformat(GEOMETRY_RETRIEVED) if src == 'geometry' else RETRIEVED,
            observer='Wayproof primary-source text, georeferenced map and named-feature review'))
        r.evidence.append(Evidence(evid, oid, cid))
        r.claims.append(Claim(cid, subject, predicate, value, (evid,), temporal_scope=temporal,
            spatial_scope_ids=scopes or (scope(subject),)))
        (access_inputs if access else inputs).append(cid)
        return (evid,)

    def rel(key, subject, predicate, obj, ev):
        r.relationships.append(Relationship('relationship-emigrant-western-' + key, subject, predicate, obj, ev))

    def gap(key, question, reason, related, access=False):
        gid = 'gap-emigrant-western-' + key
        r.gaps.append(KnowledgeGap(gid, question, tuple(related), reason)); (access_inputs if access else inputs).append(gid)

    for key, name in NODES.items(): entity(node(key), 'route_node', name)
    for key, name in [('powell','Powell'),('chewing-gum','Chewing Gum'),('grouse','Grouse'),('gem','Gem')]:
        entity(lake(key), 'waterbody', name + ' Lake (Emigrant Wilderness)')
        src = {'chewing-gum':'chewing-camping-map', 'grouse':'grouse-camping-map'}.get(key, 'overview-map')
        ev = claim(key + '-identity', src, f'Official Emigrant map names {name} Lake within the wilderness and depicts its trail approach. The lake is distinct from the trail display endpoint.',
            lake(key), 'mapped_lake_identity', {'name': name + ' Lake', 'wilderness': LAND,
            'shoreline_geometry': 'not imported', 'water_availability': 'unknown', 'campsites': 'not inventoried'})
        rel(key + '-land', lake(key), 'part_of', LAND, ev)

    route_evidence = {}
    for key, (name, entry, objective, end, legs, mileage) in ROUTES.items():
        entity(route(key), 'route', name)
        ev = claim(key + '-profile', 'overview-map', f'2010 Emigrant Wilderness map, western panel: {name} follows the explicitly drawn trail network. Detailed segment claims retain the reviewed trail numbers and junctions. This is a Wayproof descriptive approach, not an asserted official route name.',
            route(key), 'route_description', {'entry_id': th(entry), 'objective_id': lake(objective),
            'end_node_id': node(end), 'name_status': 'Wayproof descriptive approach', 'directionality': 'bidirectional mapped trail',
            'source_edition': '2010', 'current_conditions': 'unknown', 'endpoint_status': 'reviewed trail approach; not lake centroid or campsite'})
        route_evidence[key] = ev
        rel(key + '-start', route(key), 'starts_at', th(entry), ev)
        rel(key + '-end', route(key), 'ends_at', node(end), ev)
        rel(key + '-land', route(key), 'traverses', LAND, ev)
        rel(key + '-objective', lake(objective), 'approached_via', route(key), ev)
        for leg in legs:
            sid = leg if leg.startswith('route-segment-') else segment(leg)
            rel(key + '-' + leg, sid, 'part_of', route(key), ev)
        if mileage is not None:
            claim(key + '-table', 'mileage-table', f'ROG 16-27 June 2012, page 1: {entry.replace("-"," ").title()} column reports {objective.replace("-"," ").title()} Lake at {mileage} miles. Printed destination total; exact lake endpoint is unspecified.',
                route(key), 'published_approach_distance_report', {'reported_one_way_miles': mileage, 'source_edition': '2012-06',
                'endpoint_precision': 'destination unspecified', 'not_atomic_distance': True})
        claim(key + '-conditions', 'alerts', 'Forest alert index requires current order and map review. Historical maps do not establish present road, snow, crossing, water, fire or trail status.',
            route(key), 'pretrip_current_conditions_recheck', {'required': True, 'current_status': 'unknown',
            'topics': ['access roads','trail and crossings','water','fire restrictions','snow and closures']})
        gap(key + '-planning', f'What remains unverified for {name}?',
            'Approach topology and display geometry are represented; no complete mileage, return itinerary, shoreline circulation, legal individual campsite, drinkable water or current trail clearance is established. Printed destination totals may end at a different point from the descriptive display endpoint. Recheck the route and intended endpoint with the Forest Service.',
            ['claim-emigrant-western-' + key + '-profile', 'claim-emigrant-western-' + key + '-conditions'])

    for leg, feature in zip(LEGS, snapshot['features'], strict=True):
        key, fid, start, end, a, b, support = leg
        entity(segment(key), 'route_segment', key.replace('-', ' ').title())
        route_scopes = tuple(scope(route(k)) for k, v in ROUTES.items() if key in v[4])
        src = 'chewing-camping-map' if key == 'north-chewing' else 'grouse-camping-map' if key == 'grouse-approach' else 'overview-map'
        ev = claim(key + '-topology', src, '2010 overview western panel, corroborated by lake detail maps and named USFS trail features: ' + support + '. Segmentation at source breaks and chosen trail approach vertices is descriptive, not a claim of an official named junction. No atomic mileage assigned from cumulative reports or GIS lengths.',
            segment(key), 'mapped_route_connector', {'start_node_id': a, 'end_node_id': b,
            'distance_miles': None, 'distance_status': 'not_printed', 'route_role': 'official_mainline', 'support': support}, scopes=route_scopes)
        attrs = feature['properties']['source_attributes']; coords = feature['geometry']['coordinates']
        gev = claim(key + '-geometry', 'geometry', f'USFS National Forest System Trails feature {fid}, globalid {attrs["globalid"]}, {attrs["trail_no"]} {attrs["trail_name"]}: reviewed inclusive normalized source vertices {start} through {end}. Matched against official trail maps; source lengths describe the entire original feature. No coordinate is snapped and no mileage is computed.',
            segment(key), 'reviewed_route_display_geometry', {'geometry_snapshot': {'path': SNAPSHOT, 'sha256': digest, 'feature_id': feature['properties']['feature_id']},
            'start_coordinate': {'longitude': coords[0][0], 'latitude': coords[0][1]},
            'end_coordinate': {'longitude': coords[-1][0], 'latitude': coords[-1][1]},
            'coordinate_reference_system': 'EPSG:4326', 'source_coordinate_accuracy': 'unknown',
            'navigation_grade': False, 'source_feature_id': fid, 'source_globalid': attrs['globalid'],
            'source_vertex_range_inclusive': [start,end], 'route_role': 'official_mainline',
            'current_route_status': 'unknown; pre-trip check required'}, scopes=route_scopes)
        rel(key + '-start', segment(key), 'starts_at', a, ev + gev)
        rel(key + '-end', segment(key), 'ends_at', b, ev + gev)
        if key in RESOURCE_LEGS:
            rel(key + '-resource', segment(key), 'provides_access_to', lake(RESOURCE_LEGS[key]), ev + gev)

    for src, value, edition in [('favorite-hikes',2,'2018-11'), ('mileage-diagram',2.0,'2021 filename'), ('trail-map',1.8,'unknown')]:
        claim('powell-' + src, src, f'Official {src} gives Gianelli–Powell Lake as {value} miles; edition {edition}. The 2018 guide describes Powell as one mile beyond Burst Rock; schematic estimates do not identify every graph vertex.',
            route('gianelli-powell'), 'published_approach_distance_report', {'reported_one_way_miles': value,
            'source_edition': edition, 'qualifier': 'estimate' if src == 'mileage-diagram' else 'printed report', 'not_atomic_distance': True})
    gap('powell-mileage', 'Which Powell Lake approach mileage applies?',
        'The 2012 table reports 2.3 miles, the 2018 guide and 2021 schematic 2/2.0, and the undated GIF 1.8. Retain the reports independently; endpoint and edition alignment is unresolved. Do not subtract destination totals into atomic lengths.',
        ['claim-emigrant-western-gianelli-powell-table'] + ['claim-emigrant-western-powell-' + s for s in ('favorite-hikes','mileage-diagram','trail-map')])
    for objective, rt, miles in [('chewing','gianelli-chewing-gum',4.1), ('grouse','crabtree-grouse',4), ('gem','crabtree-gem',10)]:
        claim(objective + '-operator-mileage', 'aspen-' + objective,
            f'Aspen Meadow Pack Station destination page reports {miles} miles under its {"Gianelli" if objective == "chewing" else "Crabtree"} destination hierarchy. Publication date, precise endpoint and one-way/round-trip convention are not stated; the operator describes riding destinations.',
            route(rt), 'published_approach_distance_report', {'reported_miles': miles, 'source_edition': 'unknown',
            'travel_context': 'operator riding destination', 'distance_convention': 'not explicitly stated', 'not_atomic_distance': True})
    gap('gem-mileage', 'How does the operator Gem mileage compare with the Forest Service table?',
        'The 2012 Forest Service table reports 9.5 one-way miles from Crabtree; the undated operator page reports 10 miles without explicitly stating its distance convention or precise endpoint. They remain separate reports, not a resolved route total.',
        ['claim-emigrant-western-crabtree-gem-table','claim-emigrant-western-gem-operator-mileage'])
    claim('chewing-operator-marking', 'aspen-chewing', 'Undated Aspen Meadow Chewing Gum page distinguishes a good trail from Gianelli from a poorly marked trail from Crabtree. This describes the operator report, not a current field inspection.',
        route('crabtree-chewing-gum'), 'reported_route_finding_condition', {'reported_marking': 'poorly marked', 'source_date': 'unknown', 'current_condition': 'unknown'})
    for key, src in [('chewing-gum','chewing-camping-map'),('grouse','grouse-camping-map')]:
        claim(key + '-minimum', src, 'Minimum Camping Distance Map, page 1 (2021 filename): camping less than 100 feet from water, trails or posted signs is prohibited; map is reference only.', lake(key), 'camping_setback', {'minimum_feet':100, 'from':['water','trails','posted signs'], 'map_is_reference_only':True})
        claim(key + '-recommendation', src, 'Minimum Camping Distance Map, page 1 (2021 filename): 200 feet is the Leave No Trace recommendation, distinct from the 100-foot minimum.', lake(key), 'camping_setback_recommendation', {'recommended_feet':200, 'basis':'Leave No Trace; not asserted regulatory minimum'})
    claim('grouse-exclusion', 'grouse-camping-map', 'Grouse Lake minimum camping map states no legal place to camp between the trail and lake because of their proximity.', lake('grouse'), 'camping_exclusion', {'location':'between trail and Grouse Lake', 'camping':'prohibited by mapped minimum distances', 'individual_sites':'not inventoried'})
    claim('chewing-existing-sites', 'chewing-camping-map', 'Chewing Gum Lake minimum camping map warns of illegal fire rings and campsites and says existing sites can be used only if minimum distances are met.', lake('chewing-gum'), 'existing_campsite_qualification', {'existing_site_is_not_permission':True, 'must_meet_minimum_distances':True, 'current_site_inventory':'unknown'})
    claim('powell-guide-night-limit', 'favorite-hikes', 'ROG 16-41 November 2018 page 2 reports a one-night camping limit for Powell Lake. It does not reconcile the newer one-consecutive-night versus per-trip wilderness wording.', lake('powell'), 'historical_lake_camping_limit', {'reported_nights':1, 'source_edition':'2018-11', 'current_interpretation':'requires foundation wilderness recheck'})
    claim('grouse-operator-night-limit', 'aspen-grouse', 'Undated Aspen Meadow Grouse destination page reports a one-night camping limit. Operator description does not establish current legal wording.', lake('grouse'), 'reported_lake_camping_limit', {'reported_nights':1, 'source_date':'unknown', 'current_interpretation':'requires foundation wilderness recheck'})

    # Historical facility/road reports remain scoped to the access actually used.
    restroom = 'restroom-emigrant-crabtree'
    entity(restroom, 'restroom', 'Crabtree Trailhead restrooms')
    ev = claim('crabtree-restrooms-2012', 'trailheads', 'ROG 16-26 April 2012, Crabtree Camp Trailhead: restrooms are listed. Count, exact position and current operation are unspecified.', restroom, 'historical_facility_presence', {'reported_present':True, 'source_edition':'2012-04', 'count':'unknown', 'current_availability':'unknown'}, scopes=(scope(restroom),scope(th('crabtree'))), access=True)
    rel('crabtree-restrooms-location', restroom, 'part_of', th('crabtree'), ev)
    rel('crabtree-restrooms-access', th('crabtree'), 'provides_access_to', restroom, ev)
    claim('crabtree-restrooms-2023', 'traveler-2023', 'Traveler 2023, Highway 108 recreation opportunities page 10, Horse Camping: Crabtree and Kennedy Meadows trailheads have vault toilets. This is a published facility report, not an operating-status check.', restroom, 'reported_restroom_type', {'type':'vault toilet', 'source_edition':'2023', 'current_availability':'unknown'}, scopes=(scope(restroom),scope(th('crabtree'))), access=True)
    claim('crabtree-toilet-project', 'traveler-2023', 'Traveler 2023 page 8, improvements planned complete by 2026: new vault toilets include Crabtree day use area. A planned completion date does not establish installation or opening.', restroom, 'published_facility_project', {'project':'new vault toilets', 'source_edition':'2023', 'planned_completion_year':2026, 'completion_status':'unknown'}, scopes=(scope(restroom),scope(th('crabtree'))), access=True)
    for key in ('crabtree','gianelli','bell-meadow'):
        claim(key + '-trailhead-night-limit', 'trailheads', 'ROG 16-26 April 2012 introduction states a one-night camping limit at all trailheads. This is a historical report; confirm present trailhead-specific restrictions before relying on it.', th(key), 'historical_trailhead_camping_limit', {'reported_nights':1, 'source_edition':'2012-04', 'scope':'trailhead camping; distinct from wilderness lake limit', 'current_rule_status':'unverified'}, access=True)
        claim(key + '-camping-opportunity', 'trailheads', f'ROG 16-26 April 2012 {key.replace("-"," ").title()} entry describes {"good" if key == "bell-meadow" else "fair"} overnight camping opportunities. It provides no reservable individual site inventory or current availability.', th(key), 'historical_camping_opportunity', {'source_edition':'2012-04','reported_description':'good' if key == 'bell-meadow' else 'fair', 'current_availability':'unknown'}, access=True)
        if key != 'crabtree':
            claim(key + '-no-facilities-report', 'trailheads', f'ROG 16-26 April 2012 {key.replace("-"," ").title()} entry says no facilities. Do not interpret this historical statement as present absence.', th(key), 'historical_facility_report', {'source_edition':'2012-04', 'reported_facilities':'none', 'current_inventory':'unknown'}, access=True)
        tail = {'crabtree':[('continue straight 4N26',4),('right Crabtree Camp Road',1)], 'gianelli':[('continue straight 4N26',5),('left 4N47 fork',4)], 'bell-meadow':[('right 4N26',1),('left 4N02Y',1.5)]}[key]
        claim(key + '-driving', 'trailheads', 'ROG 16-26 April 2012 directions from Summit Ranger Station (Pinecrest): west on Hwy 108 two miles, left on Crabtree Road seven miles to Aspen Meadow, then ' + ', '.join(f'{turn} {miles} miles' for turn,miles in tail) + '. The guide explicitly says all mileages are approximate.', th(key), 'historical_driving_directions', {'source_edition':'2012-04', 'origin':'Summit Ranger Station (Pinecrest)', 'mileage_precision':'approximate', 'legs':[{'instruction':turn,'approximate_miles':miles} for turn,miles in [('west Highway 108',2),('left Crabtree Road to Aspen Meadow',7)] + tail], 'current_road_status':'unknown; verify current MVUM and orders'}, access=True)
        claim(key + '-access-recheck', 'alerts', 'Forest alert index and individual road/fire orders must be checked against the selected access. Historical directions, parking descriptions and facility reports are not current clearance.', th(key), 'pretrip_access_recheck', {'required':True, 'current_status':'unknown', 'topics':['parking and road access','restroom operation','trailhead camping limits','fire orders']}, access=True)
        gap(key + '-access', 'What facilities and camping restrictions currently apply at ' + key.replace('-',' ').title() + '?', 'Published facility and camping reports are historical or undated. Verify operating toilets, road access and parking, the trailhead-specific one-night limit, and interaction with current forest occupancy/fire orders. Do not substitute the general forest maximum for a more restrictive site limit. Individual sites, facility coordinates and connecting footpaths are not inventoried.', ['claim-emigrant-western-' + key + '-access-recheck','claim-emigrant-western-' + key + '-trailhead-night-limit'], access=True)
    claim('crabtree-night-limit-2023', 'traveler-2023', 'Traveler 2023 page 10 Horse Camping: Crabtree and Kennedy Meadows trailheads allow one-night stays for campers and stock entering Emigrant Wilderness. This report concerns trailhead stays, not a lake camping interpretation.', th('crabtree'), 'reported_trailhead_camping_limit', {'reported_nights':1, 'source_edition':'2023', 'applies_to':'campers and stock entering Emigrant Wilderness', 'current_rule_status':'requires confirmation'}, access=True)
    temporal = TemporalScope(date(2026,7,31), date(2029,7,30))
    for key, value, text in [('developed', {'maximum_consecutive_days':14,'window_days':30,'location':'developed recreation site within one Ranger District'}, 'Developed recreation site camping within one Ranger District is limited to 14 consecutive days within any 30-day period.'), ('undeveloped', {'maximum_total_days':21,'window':'calendar year','location':'undeveloped locations within one Ranger District'}, 'Undeveloped-location camping within one Ranger District is limited to 21 total days during a calendar year.')]:
        claim('occupancy-' + key, 'occupancy-order', 'Signed STF-16-2026-09 page 1, effective July 31, 2026–July 30, 2029: ' + text + ' Exemptions: FS-7700-48 permits specifically exempting the holder, and official-duty officers or organized rescue/fire personnel.', LAND, 'forest_occupancy_limit_context', value | {'site_classification':'not assigned to these trailheads', 'does_not_resolve_site_specific_limit':True, 'exemptions':['FS-7700-48 specifically exempting holder','official-duty federal/state/local officer or organized rescue/fire force']}, scopes=('scope-emigrant-wilderness',), access=True, temporal=temporal)
    for src, previous in [('occupancy-order','STF-16-2024-10'),('occupancy-page','STF-16-2022-06')]:
        claim('supersession-' + src, src, f'STF-16-2026-09 {"signed PDF footer" if src == "occupancy-order" else "alert summary"} identifies {previous} as the superseded order. The two sources disagree.', LAND, 'reported_order_supersession', {'order':'STF-16-2026-09','reported_superseded_order':previous}, scopes=('scope-emigrant-wilderness',), access=True)
    gap('occupancy-supersession', 'Which prior occupancy order does STF-16-2026-09 supersede?', 'Signed PDF footer names STF-16-2024-10 (July 29, 2024); alert summary names STF-16-2022-06 (July 28, 2022). Preserve both statements. This does not resolve trailhead-specific one-night guidance or classify a camping site as developed/undeveloped.', ['claim-emigrant-western-supersession-occupancy-order','claim-emigrant-western-supersession-occupancy-page'], access=True)

    reasons = {
      'gap-emigrant-route-topology': 'Crabtree Camp/Bear and six further western approaches are represented: Gianelli, Bell Meadow and Crabtree now reach Powell, Chewing Gum, Grouse or Gem via the selected sourced paths. Other alternatives, northern/southern entries, deeper lake/pass branches and individual facility spurs remain unmodeled. These bounded bidirectional graphs do not establish destination-wide route completeness.',
      'gap-emigrant-facility-inventory': 'Historical western trailhead camping, driving and facility reports now include Crabtree restrooms and 2023 corroboration. Current operation, individual campsites, water supplies, facility coordinates, Kennedy/Aspen booking inventory and developed approach campgrounds remain unresolved. Historical parking is not live inventory.',
      'gap-emigrant-crabtree-planning-limits': 'Camp/Bear remain bounded Crabtree approaches requiring an exit itinerary. Separate western routes now represent Lake Valley, Pine Valley and the eastward Gem continuation; their existence does not add those segments to the Camp/Bear routes. Shoreline circulation, individual campsites, current water and restroom availability remain unresolved. Historical maps are not current clearance.',
      'gap-emigrant-crabtree-geometry-limitations': 'Reviewed USFS vertices draw the Camp/Bear approaches and separately reviewed western routes. Accuracy is unknown and geometry is not navigation-grade or current-condition evidence. Camp western access is a descriptive source-feature break, not a lake centroid or campsite. Lake Valley has a small unsnapped endpoint mismatch, explicitly retained in its separately sourced branch. Other Emigrant routes, shorelines, facility positions and wilderness boundary remain without reviewed geometry.'}
    for old in base.gaps:
        if old.gap_id in reasons: r.gaps.append(replace(old, reason=reasons[old.gap_id]))
    for manifest, selected, topics in [(MANIFEST,inputs,['approach mileage reports','display endpoints and accuracy','lake camping placement','route finding and current conditions','return itinerary']), (ACCESS_MANIFEST,access_inputs,['historical facilities and driving directions','current trailhead camping restrictions','forest occupancy context and source conflict'])]:
        r.derived_results.append(DerivedResult(manifest, 'pretrip_recheck', {'required':True,'topics':topics}, tuple(selected), 'Project only selected western approach/access evidence and linked gaps. Wilderness requirements and lake-night conflicts remain in the foundation manifest.'))
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,default=ROOT);p.add_argument('--output',type=Path,default=ROOT);p.add_argument('--reviewed-input',type=Path)
    a=p.parse_args();path=a.output/SNAPSHOT
    if a.reviewed_input:
        payload=snapshot_from_reviewed(json.loads(a.reviewed_input.read_text()));path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    content=path.read_bytes();base=load_canonical(a.base)
    records=build_records(base,json.loads(content),hashlib.sha256(content).hexdigest())
    ops=tuple(ChangeOperation(ChangeAction.REPLACE if getattr(rec,ident) in REPLACEMENTS else ChangeAction.ADD,kind,getattr(rec,ident),f'canonical/v0/{collection}/{getattr(rec,ident)}.json','Add bounded western approach, geometry and facility evidence; retain unresolved planning limits.', evidence_refs=getattr(rec,'evidence_ids',()),knowledge_gap_refs=(getattr(rec,ident),) if kind=='gap' else ()) for kind,(collection,ident,_) in RECORD_SPECS.items() for rec in getattr(records,collection))
    change=ChangeSet(CHANGE_ID,records,summary='Add six drawable western Emigrant approaches with shared physical segments, lake camping evidence and historical trailhead facilities.',operations=ops)
    writes=ChangeSetWriteService(InMemoryCanonicalRepository(base));writes.propose(change,'emigrant-western-ingestion');errors=writes.validate(CHANGE_ID,'emigrant-validator')
    if errors: raise RuntimeError('\n'.join(errors))
    candidate=writes.prepare(CHANGE_ID,'emigrant-candidate-builder');write_candidate(a.output,candidate,writes.get(CHANGE_ID));print(f'Prepared {len(ops)} records in {CHANGE_ID}; not published.')


# Fixed identities/counts from the reviewed response, not a discovery heuristic.
EXPECTED = {9429323: ('{C2BC6336-47AF-4373-BBF9-B3E9BD88D532}', 68, '20E14'),
 9429412: ('{C7292D7C-0FDE-4FAA-8861-BBB2C417C09A}', 1668, '20E17'),
 9429539: ('{462C358A-F41E-4870-8D43-46F953769424}', 268, '19E21'),
 9429611: ('{0FCAEB78-86BA-4488-8695-1E024CD7147E}', 72, '20E98'),
 9430389: ('{DF0AD790-4CE3-4F4D-8658-BD614F3D7FF7}', 168, '19E21'),
 9430585: ('{EDD61318-4DB8-4553-B8EC-17DF0A3BD987}', 147, '19E10'),
 9430618: ('{1D2CDA88-08B4-4846-B5CD-A4ECF893054B}', 837, '20E16'),
 9430968: ('{C539E29C-748A-4018-821E-D53108F78B61}', 23, '20E14A'),
 9431555: ('{EF38ACD6-5434-4D6D-951B-0409DCE1EC92}', 437, '20E17'),
 9505484: ('{A67C6A39-1A55-4D55-B9C7-AFD31CBE40F7}', 748, '20E14')}

if __name__ == '__main__': main()
