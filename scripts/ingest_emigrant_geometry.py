#!/usr/bin/env python3
"""Prepare reviewed USFS display geometry for the existing Crabtree lake graph.

A reviewed raw query can produce the bounded snapshot with --reviewed-input.
Without it, reuse the committed snapshot. No live fetching or publication occurs.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wayproof.canonical_storage import RECORD_SPECS, load_canonical, write_candidate
from wayproof.schema import (CanonicalRecords, ChangeAction, ChangeOperation, ChangeSet,
    Claim, DerivedResult, Evidence, KnowledgeGap, Observation, Source)
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository

ROOT = Path(__file__).resolve().parents[1]
CHANGE_ID = 'wp-20261006-emigrant-crabtree-geometry'
SNAPSHOT = 'geometry/v0/snapshots/usfs-emigrant-crabtree-routes-20261006.geojson'
SOURCE_ID = 'source-usfs-emigrant-nfs-trail-geometry'
SERVICE = 'https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_TrailNFSPublish_01/MapServer/0'
RETRIEVED = datetime(2026, 10, 6, 0, 9, 34, tzinfo=timezone.utc)
MANIFEST = 'result-emigrant-crabtree-geometry-recheck'
# Indices are zero-based in the inspected EPSG:4326 source response. No snapping,
# interpolation, coordinate rounding, or distance computation is performed.
SLICES = (
    ('start-lake-valley', 9428086, 182, 172),
    ('lake-valley-pine-valley', 9428086, 172, 67),
    ('pine-valley-camp', 9428086, 67, 0),
    ('camp-bear-junction', 9430618, 836, 806),
    ('bear-spur', 9430557, 0, 164),
)
EXPECTED = {
    9428086: ('{DD41DD87-9AAE-4FE1-B078-0427EEE709F1}', 183, '20E16'),
    9430618: ('{1D2CDA88-08B4-4846-B5CD-A4ECF893054B}', 837, '20E16'),
    9430557: ('{8497BEEB-8635-4A89-8352-B24C998130DD}', 165, '19E09'),
}


def snapshot_from_reviewed(raw):
    features = {f['properties']['objectid']: f for f in raw['features']}
    for fid, (guid, count, trail) in EXPECTED.items():
        f = features[fid]
        assert f['properties']['globalid'] == guid
        assert f['properties']['trail_no'] == trail
        assert f['geometry']['type'] == 'LineString'
        assert len(f['geometry']['coordinates']) == count
    # Reviewed branch correspondence is independently established by the 2010
    # overview and lake detail maps already represented in the canonical graph.
    crab = features[9428086]['geometry']['coordinates']
    east = features[9430618]['geometry']['coordinates']
    bear = features[9430557]['geometry']['coordinates']
    assert crab[67] == features[9430585]['geometry']['coordinates'][0]
    assert crab[0] == east[836]
    assert east[806] == bear[0]
    assert crab[172] == [-119.90646170977695, 38.17758396939358]
    assert features[9430389]['geometry']['coordinates'][0] == [-119.90646084177686, 38.17758389639366]
    out = []
    for key, fid, start, end in SLICES:
        f = features[fid]
        step = 1 if end > start else -1
        coords = [f['geometry']['coordinates'][i] for i in range(start, end + step, step)]
        out.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': coords},
            'properties': {'feature_id': 'usfs-emigrant-' + key,
                'source_attributes': f['properties'],
                'source_vertex_range_inclusive': [start, end],
                'source_vertex_count': len(f['geometry']['coordinates']),
                'source_geometry_sha256': hashlib.sha256(json.dumps(f['geometry'], sort_keys=True).encode()).hexdigest(),
                'xy_accuracy': 'unknown; source coordinate digits are not an accuracy statement',
                'length_field_scope': 'original source feature; not the clipped Wayproof segment'}})
    for left, right in zip(out, out[1:]):
        assert left['geometry']['coordinates'][-1] == right['geometry']['coordinates'][0]
    return {'type': 'FeatureCollection', 'wayproof': {
        'source': SERVICE, 'publisher': 'USDA Forest Service',
        'retrieved_at': RETRIEVED.isoformat(), 'classification': 'public_domain', 'source_id': SOURCE_ID,
        'source_coordinate_reference_system': 'EPSG:4269',
        'normalized_coordinate_reference_system': 'EPSG:4326', 'navigation_grade': False,
        'processing': 'Reviewed contiguous source-vertex slices, oriented to existing canonical endpoints; no snapping, interpolation, simplification or mileage calculation.',
        'review_basis': 'Named 20E16 CRABTREE and 19E09 BEAR LAKE features matched to the 2010 Emigrant overview and Camp/Bear minimum camping maps. Existing relationships supply connectivity.',
        'lake_valley_junction_note': 'Crabtree vertex 172 is the reviewed display position. The unimported Lake Valley branch endpoint differs by approximately 0.08 m in the normalized response; neither line is snapped and no new branch relationship is created.',
        'camp_endpoint_note': 'The shared source-feature break supplies a reviewed western-approach display position, not an official lake centroid, surveyed junction or campsite.'}, 'features': out}


def build_records(snapshot, digest):
    r = CanonicalRecords()
    r.sources.append(Source(SOURCE_ID, SERVICE, 'USDA Forest Service'))
    selected = []
    route_scopes = tuple('scope-route-emigrant-crabtree-' + k + '-lake' for k in ('camp', 'bear'))
    for (key, fid, start, end), f in zip(SLICES, snapshot['features'], strict=True):
        assert f['properties']['feature_id'] == 'usfs-emigrant-' + key
        cid, oid, eid = ('claim-emigrant-geometry-' + key, 'observation-emigrant-geometry-' + key,
                         'evidence-emigrant-geometry-' + key)
        a, b = f['geometry']['coordinates'][0], f['geometry']['coordinates'][-1]
        attrs = f['properties']['source_attributes']
        r.observations.append(Observation(oid, SOURCE_ID,
            f'Public National Forest System Trails layer, feature {fid}, globalid {attrs["globalid"]}, trail {attrs["trail_no"]} {attrs["trail_name"]}: reviewed EPSG:4326 source vertices {start} through {end} are retained for display. Source segment_length {attrs["segment_length"]} and gis_miles {attrs["gis_miles"]} describe the original feature, not a computed length for this slice. Coordinate accuracy and current field condition are not established by retrieval.',
            retrieved_at=RETRIEVED, observer='Wayproof named-feature and official-map review'))
        r.evidence.append(Evidence(eid, oid, cid, notes='Wayproof display assignment to already evidenced endpoints; no new topology inferred from proximity.'))
        r.claims.append(Claim(cid, 'route-segment-emigrant-crabtree-' + key,
            'reviewed_route_display_geometry', {
                'geometry_snapshot': {'path': SNAPSHOT, 'sha256': digest, 'feature_id': f['properties']['feature_id']},
                'start_coordinate': {'longitude': a[0], 'latitude': a[1]},
                'end_coordinate': {'longitude': b[0], 'latitude': b[1]},
                'coordinate_reference_system': 'EPSG:4326', 'navigation_grade': False,
                'source_feature_id': fid, 'source_globalid': attrs['globalid'],
                'source_trail_number': attrs['trail_no'], 'source_vertex_range_inclusive': [start, end],
                'source_coordinate_accuracy': 'unknown', 'route_role': 'official_mainline',
                'distance_policy': 'Existing topology claims control mileage; no distance derived from these coordinates.',
                'current_route_status': 'unknown; pre-trip check required'}, (eid,),
            spatial_scope_ids=route_scopes if key in ('start-lake-valley', 'lake-valley-pine-valley', 'pine-valley-camp') else (route_scopes[1],)))
        selected.append(cid)
    gid = 'gap-emigrant-crabtree-geometry-limitations'
    r.gaps.append(KnowledgeGap(gid, 'What does the Crabtree route display geometry establish?',
        tuple(selected) + ('route-emigrant-crabtree-camp-lake', 'route-emigrant-crabtree-bear-lake'),
        'Reviewed USFS source vertices now draw the existing Camp/Bear approaches. Accuracy is unspecified and this is not navigation-grade or a current-condition survey. Camp western access is a descriptive display position at a source-feature break, not a lake centroid or campsite. The nearby Lake Valley source endpoint has a small coordinate mismatch; no branch is snapped or added. Other Emigrant routes, lake shores, facility positions and the wilderness boundary still lack reviewed display geometry.'))
    r.derived_results.append(DerivedResult(MANIFEST, 'pretrip_recheck',
        {'required': True, 'topics': ['display accuracy and endpoint interpretation', 'current trail conditions', 'unreviewed geometry coverage']},
        tuple(selected) + (gid,), 'Expose geometry limitations on the selected lake approach; retain the existing foundation and lake-route rechecks for permits, mileage conflicts and conditions.'))
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=ROOT)
    p.add_argument('--output', type=Path, default=ROOT)
    p.add_argument('--reviewed-input', type=Path)
    a = p.parse_args()
    path = a.output / SNAPSHOT
    if a.reviewed_input:
        payload = snapshot_from_reviewed(json.loads(a.reviewed_input.read_text()))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')
    content = path.read_bytes()
    records = build_records(json.loads(content), hashlib.sha256(content).hexdigest())
    ops = tuple(ChangeOperation(ChangeAction.ADD, kind, getattr(record, ident),
        f'canonical/v0/{collection}/{getattr(record, ident)}.json',
        'Attach reviewed federal display geometry without changing graph or mileage.',
        evidence_refs=getattr(record, 'evidence_ids', ()))
        for kind, (collection, ident, _) in RECORD_SPECS.items()
        for record in getattr(records, collection))
    change = ChangeSet(CHANGE_ID, records, summary='Make the existing Crabtree lake approaches geographically drawable with reviewed USFS vertices and explicit display limits.', operations=ops)
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(load_canonical(a.base)))
    writes.propose(change, 'emigrant-geometry-review')
    errors = writes.validate(CHANGE_ID, 'emigrant-validator')
    if errors:
        raise RuntimeError('\n'.join(errors))
    candidate = writes.prepare(CHANGE_ID, 'emigrant-candidate-builder')
    write_candidate(a.output, candidate, writes.get(CHANGE_ID))
    print(f'Prepared {len(ops)} records in {CHANGE_ID}; not published.')


if __name__ == '__main__':
    main()
