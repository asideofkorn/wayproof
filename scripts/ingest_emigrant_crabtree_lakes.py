#!/usr/bin/env python3
"""Build reviewed Crabtree lake approaches through the validated write boundary.

Regenerate against main before this batch using --base; never fetch or publish.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wayproof.canonical_storage import RECORD_SPECS, load_canonical, write_candidate
from wayproof.schema import (CanonicalRecords, ChangeAction, ChangeOperation, ChangeSet,
    Claim, DerivedResult, Entity, Evidence, KnowledgeGap, Observation, Relationship,
    Source, SpatialScope)
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]
CHANGE_ID = 'wp-20261005-emigrant-crabtree-lakes'
LAND = 'wilderness-emigrant'
TH = 'trailhead-emigrant-crabtree'
MANIFEST = 'result-emigrant-crabtree-lakes-pretrip-recheck'
RETRIEVED = datetime(2026, 10, 5, 22, 52, 54, tzinfo=timezone.utc)
FS = 'https://www.fs.usda.gov/sites/nfs/files/'
SOURCES = {
    'overview-map': 'legacy-media/stanislaus/Emigrant%20Wilderness%20GEOSPATIAL.pdf',
    'mileage-table': 'legacy-media/stanislaus/Trail%20Mileages%20-%20Emigrant%202012.pdf',
    'mileage-diagram': 'legacy-media/stanislaus/Emigrant%20Trail%20Mileage%20Diagram%202021.pdf',
    'trail-map': 'r05/stanislaus/image/emigrant-wilderness-trail-map.gif',
    'favorite-hikes': 'r05/stanislaus/publication/Favorite%20Hiking%20Trails.pdf',
    'camp-camping-map': 'legacy-media/stanislaus/Camp%20Lake%20-%20Minimum%20Camping%20Distances%202021.pdf',
    'bear-camping-map': 'legacy-media/stanislaus/Bear%20Lake%20-%20Minimum%20Camping%20Distances%202021.pdf',
}
REPLACEMENTS = {'gap-emigrant-route-topology'}


def route(key):
    return f'route-emigrant-crabtree-{key}-lake'


def lake(key):
    return f'waterbody-emigrant-{key}-lake'


def node(key):
    return f'route-node-emigrant-{key}'


def scope(entity):
    return 'scope-' + entity


def build_records(base):
    r = CanonicalRecords()
    inputs = []
    lake_evidence = {}
    for key, path in SOURCES.items():
        r.sources.append(Source('source-usfs-emigrant-' + key, FS + path,
                                'USDA Forest Service, Stanislaus National Forest'))

    def entity(eid, kind, name):
        r.entities.append(Entity(eid, kind, name))
        r.spatial_scopes.append(SpatialScope(scope(eid), kind, eid))

    def claim(key, source, content, subject, predicate, value, scopes=None, recheck=False):
        cid, oid, evid = ('claim-emigrant-crabtree-' + key,
                         'observation-emigrant-crabtree-' + key,
                         'evidence-emigrant-crabtree-' + key)
        r.observations.append(Observation(oid, 'source-usfs-emigrant-' + source,
            content, retrieved_at=RETRIEVED, observer='Wayproof primary-source text and visual map review'))
        r.evidence.append(Evidence(evid, oid, cid))
        r.claims.append(Claim(cid, subject, predicate, value, (evid,),
                              spatial_scope_ids=scopes or (scope(subject),)))
        if recheck:
            inputs.append(cid)
        return (evid,)

    def rel(key, subject, predicate, obj, evidence):
        r.relationships.append(Relationship('relationship-emigrant-crabtree-' + key,
                                            subject, predicate, obj, evidence))

    def gap(key, question, reason, related):
        gid = 'gap-emigrant-crabtree-' + key
        r.gaps.append(KnowledgeGap(gid, question, tuple(related), reason))
        inputs.append(gid)

    nodes = [('lake-valley-junction', 'Lake Valley Trail junction near Crabtree'),
             ('pine-valley-junction', 'Pine Valley Trail junction on Camp Lake approach'),
             ('camp-west-approach', 'Camp Lake western trail approach'),
             ('bear-junction', 'Bear Lake trail junction east of Camp Lake'),
             ('bear-trail-end', 'Bear Lake mapped trail terminus')]
    for key, name in nodes:
        entity(node(key), 'route_node', name)
    for key in ('camp', 'bear'):
        entity(route(key), 'route', f'Crabtree to {key.title()} Lake')
        entity(lake(key), 'waterbody', f'{key.title()} Lake (Emigrant Wilderness)')
        ev = claim(key + '-profile', 'favorite-hikes',
            f'Favorite Hiking Trails, ROG 16-41, November 2018, page 2 Day Hikes (mileages one way): {key.title()} Lake starts from Crabtree; Bear Lake continues past Camp Lake. Route names used here are descriptive, not asserted official trail names.',
            route(key), 'route_description', {'entry_id': TH, 'objective_id': lake(key),
            'source_edition': '2018-11', 'name_status': 'Wayproof descriptive approach',
            'directionality': 'bidirectional mapped trail', 'current_conditions': 'unknown'},
            scopes=(scope(route(key)),), recheck=True)
        rel(key + '-start', route(key), 'starts_at', TH, ev)
        end = node('camp-west-approach' if key == 'camp' else 'bear-trail-end')
        rel(key + '-approach', lake(key), 'approached_via', route(key), ev)
        map_detail = ('The system trail approaches from the west and follows south of Camp Lake.'
                      if key == 'camp' else 'The system trail ends on the southwest approach to Bear Lake.')
        map_ev = claim(key + '-identity', key + '-camping-map',
            f'Minimum Camping Distance Map for {key.title()} Lake, page 1 (2021 filename): named lake in Emigrant Wilderness and system trail marked To Crabtree Trailhead. {map_detail} No shoreline polygon, campsite inventory or live water availability is inferred.',
            lake(key), 'mapped_lake_identity', {'name': key.title() + ' Lake',
            'wilderness': LAND, 'geometry': 'not imported', 'edition_basis': '2021 filename'}, recheck=True)
        lake_evidence[key] = map_ev
        rel(key + '-end', route(key), 'ends_at', end, map_ev)
        rel(key + '-land', lake(key), 'part_of', LAND, map_ev)
        rel(key + '-traverses', route(key), 'traverses', LAND, map_ev)
        # Preserve each printed total as a report, never as an atomic traversal leg.
        for source, miles, edition in [('mileage-table', 2.6 if key == 'camp' else 3.9, '2012-06'),
                                       ('favorite-hikes', 3 if key == 'camp' else 4, '2018-11')]:
            claim(key + '-' + source, source,
                f'{edition}, {"ROG 16-27 Crabtree column, page 1" if source == "mileage-table" else "ROG 16-41 Day Hikes, page 2"}: {key.title()} Lake {miles} miles from Crabtree. Endpoint precision is not specified; editions disagree.',
                route(key), 'published_approach_distance_report',
                {'reported_one_way_miles': miles, 'source_edition': edition,
                 'endpoint_precision': 'lake destination; exact point unspecified',
                 'status': 'conflicting reports; not a resolved route total'}, recheck=True)
        gap(key + '-mileage', f'What one-way distance should be planned from Crabtree to {key.title()} Lake?',
            'Official editions give different destination mileages. Preserve each report; neither supplies all atomic leg distances. No subtraction or schematic measurement supplies missing legs. Confirm the intended lake endpoint and current route with the Forest Service.',
            [route(key), 'claim-emigrant-crabtree-' + key + '-mileage-table',
             'claim-emigrant-crabtree-' + key + '-favorite-hikes'])

    # Explicit branches visible on the 2010 overview, refined by the Camp/Bear detail maps.
    path = [TH] + [node(k) for k, _ in nodes]
    leg_keys = ['start-lake-valley', 'lake-valley-pine-valley', 'pine-valley-camp',
                'camp-bear-junction', 'bear-spur']
    for i, key in enumerate(leg_keys):
        eid = 'route-segment-emigrant-crabtree-' + key
        entity(eid, 'route_segment', key.replace('-', ' ').title())
        source = 'overview-map' if i < 3 else 'camp-camping-map' if i == 3 else 'mileage-diagram'
        excerpt = [
            '2010 Emigrant Wilderness map, western Crabtree panel: trail from Crabtree joins the Lake Valley branch (19E21) while the Camp Lake route continues south on 20E16.',
            '2010 Emigrant Wilderness map, western Crabtree panel: 20E16 continues from the Lake Valley branch to its junction with the Pine Valley connection (19E10).',
            '2010 Emigrant Wilderness map, Camp Lake panel: 20E16 continues east from the Pine Valley connection to Camp Lake; the Camp Lake detail map confirms the western trail approach.',
            'Minimum Camping Distance Map for Camp Lake, page 1 (2021 filename): system trail from To Crabtree Trailhead follows south of Camp Lake to an east-side fork explicitly labeled To Bear Lake.',
            'Emigrant Trail Mileage Diagram (2021 filename), western panel: branch from the junction by Camp Lake to Bear Lake is labeled 1.0. Source explicitly calls distances estimates. The schematic endpoint is Bear Lake; detailed endpoint support is retained separately in the Bear map identity evidence.'
        ][i]
        ev = claim(key, source, excerpt, eid, 'mapped_route_connector',
            {'start_node_id': path[i], 'end_node_id': path[i + 1],
             'distance_miles': 1.0 if i == 4 else None,
             'distance_status': 'estimated' if i == 4 else 'not_printed',
             'route_role': 'official_mainline',
             'precision_note': 'Mapped connectivity; no surveyed coordinates. Schematic distance is an estimate, not navigation.'})
        if i == 2:
            ev += lake_evidence['camp']
        elif i == 4:
            ev += lake_evidence['bear']
        rel(key + '-start', eid, 'starts_at', path[i], ev)
        rel(key + '-end', eid, 'ends_at', path[i + 1], ev)
        for dest in (('camp', 'bear') if i < 3 else ('bear',)):
            rel(key + '-' + dest, eid, 'part_of', route(dest), ev)
        if i == 2:
            rel(key + '-resource', eid, 'provides_access_to', lake('camp'), ev)
        if i == 4:
            rel(key + '-resource', eid, 'provides_access_to', lake('bear'), ev)

    for key, miles in [('lake-valley-junction', 0.1), ('pine-valley-junction', 1.4)]:
        claim(key + '-milepoint', 'mileage-table',
            f'ROG 16-27 June 2012 page 1, Crabtree column: {key.replace("-junction", "").replace("-", " ").title()} Trail {miles} miles. This is a destination milepoint, not an atomic segment distance.',
            node(key), 'published_milepoint', {'cumulative_miles_from_crabtree': miles,
            'source_edition': '2012-06'}, scopes=(scope(route('camp')), scope(route('bear'))), recheck=True)
    claim('schematic-crabtree-junction', 'mileage-diagram',
        'Emigrant Trail Mileage Diagram (2021 filename), western panel: Crabtree to the first drawn south-side junction is labeled 1.3. Lake Valley branch is omitted. Diagram calls mileages estimates, straightens trail segments and disclaims navigation/scale.',
        node('pine-valley-junction'), 'published_schematic_distance_report',
        {'reported_miles': 1.3, 'qualifier': 'estimate',
         'endpoint': 'first drawn south-side junction; Pine Valley connection on overview',
         'omitted_branch': 'Lake Valley', 'not_atomic_distance': True},
        scopes=(scope(route('camp')), scope(route('bear'))), recheck=True)
    claim('legacy-schematic', 'trail-map',
        'Undated Emigrant Wilderness Trail Distances GIF, western panel: Crabtree to an unlabeled south junction is labeled 1.3; the eastward link from that junction toward Camp Lake is also labeled 1.3; Camp/Bear branch 1.0. This coarse schematic omits the Lake Valley junction near Crabtree and does not distinguish the Camp Lake approach from the east-side Bear junction.',
        node('pine-valley-junction'), 'published_schematic_distance_report',
        {'source_edition': 'unknown', 'crabtree_to_south_junction_miles': 1.3,
         'south_junction_toward_camp_miles': 1.3, 'camp_bear_branch_miles': 1.0,
         'endpoint_alignment': 'coarse; unresolved', 'not_atomic_distance': True},
        scopes=(scope(route('camp')), scope(route('bear'))), recheck=True)
    gap('junction-mileage', 'Which schematic endpoints match the detailed mapped junctions?',
        'The 2012 Pine Valley milepoint is 1.4; schematics print 1.3 to the south junction and omit the near-trailhead Lake Valley branch. The undated GIF prints another 1.3 toward Camp where the 2021 diagram leaves the link unlabeled. Endpoint alignment and edition differences remain unresolved; these labels are not assigned to atomic legs.',
        ['claim-emigrant-crabtree-pine-valley-junction-milepoint',
         'claim-emigrant-crabtree-schematic-crabtree-junction', 'claim-emigrant-crabtree-legacy-schematic'])

    for key in ('camp', 'bear'):
        common = f'Minimum Camping Distance Map for {key.title()} Lake, page 1 (2021 filename)'
        claim(key + '-setback', key + '-camping-map', common + ': camping less than 100 feet from water, trails or posted signs is prohibited.',
            lake(key), 'camping_setback', {'minimum_feet': 100,
            'from': ['water', 'trails', 'posted signs'], 'map_is_reference_only': True}, recheck=True)
        claim(key + '-recommendation', key + '-camping-map', common + ': 200 feet is the Leave No Trace recommended minimum distance, distinct from the 100-foot regulatory minimum.',
            lake(key), 'camping_setback_recommendation', {'recommended_feet': 200,
            'basis': 'Leave No Trace ethic; not asserted regulatory minimum'}, recheck=True)
        text = ('Camping is prohibited between the trail and Camp Lake.' if key == 'camp' else
                'Camping near cliff edges directly above Bear Lake is prohibited.')
        claim(key + '-camping-exclusion', key + '-camping-map', common + ': ' + text,
            lake(key), 'camping_area_restriction', {'restriction': text,
            'site_availability': 'unknown', 'no_campsites_inferred': True}, recheck=True)
    claim('bear-horizontal-distance', 'bear-camping-map',
        'Minimum Camping Distance Map for Bear Lake, page 1 (2021 filename): distance from water to camp is measured horizontally, not on the slope line.',
        lake('bear'), 'camping_distance_measurement', {'basis': 'horizontal; not slope line'}, recheck=True)
    for key in ('camp', 'bear'):
        claim(key + '-conditions', 'alerts',
            'Forest alert index requires current order/map review. Historical mapped connections and hiking descriptions do not establish present road, trail, snow, crossing or water conditions.',
            route(key), 'pretrip_current_conditions_recheck', {'required': True,
            'current_status': 'unknown', 'topics': ['access road', 'trail and crossings', 'snow', 'water', 'fire and closures']}, recheck=True)
    gap('planning-limits', 'Does this graph establish a complete lake camping itinerary?',
        'Only the Crabtree approach to two mapped lake-access points is represented. Named lake planning selects the route and trailhead but needs an exit itinerary; this is not a complete out-and-back camping plan. Lake Valley, Pine Valley and eastward continuations, shoreline circulation, campsites, toilets and water availability remain unresolved. Recheck road, trail and closure conditions; the maps are not current clearance.',
        ['claim-emigrant-crabtree-camp-profile', 'claim-emigrant-crabtree-bear-profile',
         'claim-emigrant-crabtree-camp-conditions', 'claim-emigrant-crabtree-bear-conditions'])
    old = next(g for g in base.gaps if g.gap_id == 'gap-emigrant-route-topology')
    r.gaps.append(replace(old, reason='Bidirectional mapped Crabtree approaches to Camp Lake and Bear Lake are represented with shared segments, separate lake resources and unknown or estimated atomic distances. Gianelli, Bell Meadow, other trailheads, alternative branches, deeper lake/pass networks and facility spurs remain deferred. This bounded approach graph does not establish destination-wide route completeness.'))
    r.derived_results.append(DerivedResult(MANIFEST, 'pretrip_recheck',
        {'required': True, 'topics': ['conflicting lake mileages', 'map endpoint alignment',
         'lake camping placement', 'current approach conditions', 'partial itinerary']},
        tuple(inputs), 'Project Crabtree lake source reports and unresolved planning questions onto the selected route/lake; use the Emigrant foundation manifest for wilderness-wide requirements and conflicts.'))
    return r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=ROOT)
    args = parser.parse_args()
    base = load_canonical(args.base)
    records = build_records(base)
    operations = []
    for kind, (collection, identifier, _) in RECORD_SPECS.items():
        for record in getattr(records, collection):
            rid = getattr(record, identifier)
            operations.append(ChangeOperation(
                ChangeAction.REPLACE if rid in REPLACEMENTS else ChangeAction.ADD,
                kind, rid, f'canonical/v0/{collection}/{rid}.json',
                'Add bounded Crabtree lake approaches while preserving map precision and unresolved coverage.',
                evidence_refs=getattr(record, 'evidence_ids', ()),
                knowledge_gap_refs=(rid,) if kind == 'gap' else ()))
    change = ChangeSet(CHANGE_ID, records, summary='Model shared Crabtree approaches to Camp and Bear lakes with conflicting mileage reports and lake camping rechecks.', operations=tuple(operations))
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(base))
    writes.propose(change, 'emigrant-source-ingestion')
    errors = writes.validate(CHANGE_ID, 'emigrant-validator')
    if errors:
        raise RuntimeError('\n'.join(errors))
    candidate = writes.prepare(CHANGE_ID, 'emigrant-candidate-builder')
    write_candidate(args.output, candidate, writes.get(CHANGE_ID))
    print(f'Prepared {len(operations)} records in {CHANGE_ID}; not published.')


if __name__ == '__main__':
    main()
