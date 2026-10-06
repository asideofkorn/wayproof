"""Reviewed geometry makes existing approaches drawable without new route facts."""
from datetime import date
import hashlib
import json
from pathlib import Path
import pytest
from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.route_geometry import RouteGeometryError, RouteGeometryService
from wayproof.schema import ChangeSetStatus, TripIntent
from scripts.ingest_emigrant_geometry import CHANGE_ID, MANIFEST, SNAPSHOT, SLICES

ROOT = Path(__file__).resolve().parents[1]
DAY = date(2027, 7, 12)


@pytest.fixture(scope='module')
def reads():
    return CanonicalReadService(ROOT)


@pytest.mark.parametrize(('key', 'count', 'known'), [('camp', 3, 0), ('bear', 5, 1)])
def test_route_display_preserves_topology_order_and_unknown_mileage(reads, key, count, known):
    g = reads.route_geometry(f'route-emigrant-crabtree-{key}-lake', DAY)
    assert len(g['features']) == count
    assert g['wayproof']['distance_miles'] == known
    assert g['wayproof']['distance_complete'] is False
    assert g['wayproof']['navigation_grade'] is False
    assert [f['properties']['segment_id'] for f in g['features']] == [
        'route-segment-emigrant-crabtree-' + x[0] for x in SLICES[:count]]
    for left, right in zip(g['features'], g['features'][1:]):
        assert left['geometry']['coordinates'][-1] == right['geometry']['coordinates'][0]
    assert all(f['properties']['distance_miles'] is None for f in g['features'][:3])
    if key == 'bear':
        assert g['features'][-1]['properties']['distance_status'] == 'estimated'
    for f in g['features']:
        assert 'unknown' in f['properties']['source_geometry_accuracy']


def test_shared_geometry_is_identical_and_source_indices_are_bounded(reads):
    camp = reads.route_geometry('route-emigrant-crabtree-camp-lake', DAY)
    bear = reads.route_geometry('route-emigrant-crabtree-bear-lake', DAY)
    assert [f['geometry'] for f in camp['features']] == [f['geometry'] for f in bear['features'][:3]]
    content = (ROOT / SNAPSHOT).read_bytes()
    payload = json.loads(content)
    assert payload['wayproof']['classification'] == 'public_domain'
    assert payload['wayproof']['normalized_coordinate_reference_system'] == 'EPSG:4326'
    assert 'neither line is snapped' in payload['wayproof']['lake_valley_junction_note']
    assert len(payload['features']) == 5
    for (key, fid, start, end), feature in zip(SLICES, payload['features'], strict=True):
        props = feature['properties']
        assert props['source_attributes']['objectid'] == fid
        assert props['source_vertex_range_inclusive'] == [start, end]
        assert len(feature['geometry']['coordinates']) == abs(end-start) + 1
        claim = reads.explain_claim('claim-emigrant-geometry-' + key)
        assert claim.claim.value['geometry_snapshot']['sha256'] == hashlib.sha256(content).hexdigest()
        assert claim.observations[0].observed_at is None
        assert claim.observations[0].retrieved_at.date() == date(2026, 10, 6)
        assert claim.sources[0].publisher == 'USDA Forest Service'
        assert 'distance_miles' not in claim.claim.value
    # No unrelated continuation from the much longer source feature is displayed.
    assert payload['features'][3]['properties']['source_vertex_count'] == 837
    assert len(payload['features'][3]['geometry']['coordinates']) == 31


@pytest.mark.parametrize(('objective', 'expected'), [
    ('Camp Lake (Emigrant Wilderness)', 3), ('Bear Lake (Emigrant Wilderness)', 5),
    ('Crabtree Trailhead', 0), ('Emigrant Wilderness', 0),
])
def test_geometry_recheck_stays_on_selected_approach(reads, objective, expected):
    result = reads.resolve_intent(TripIntent((objective,), DAY))
    recheck = reads.pretrip_recheck(result.context, MANIFEST)
    claims = [i for i in recheck.items if i.claim_id]
    assert len(claims) == expected
    if expected:
        assert recheck.state is RecheckState.REQUIRED
        assert all(i.answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK for i in claims)
        assert any(i.input_id == 'gap-emigrant-crabtree-geometry-limitations' for i in recheck.items)
        assert result.exit is None and result.traversal is None
    else:
        assert recheck.state is RecheckState.NOT_APPLICABLE


def test_geometry_is_additive_and_one_validated_changeset():
    change = load_changeset(ROOT / f'changesets/v0/{CHANGE_ID}.json')
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 18
    assert {op.action.value for op in change.operations} == {'ADD'}
    assert {op.record_type for op in change.operations} == {'source', 'observation', 'evidence', 'claim', 'gap', 'derived_result'}
    # Foundation and route facts are unchanged; no new route/membership/length rule.
    records = load_canonical(ROOT)
    expected_segments = {'route-segment-emigrant-crabtree-' + item[0] for item in SLICES}
    assert expected_segments <= {e.entity_id for e in records.entities if e.kind == 'route_segment'}


def test_hash_mismatch_fails_closed(tmp_path):
    p = tmp_path / SNAPSHOT
    p.parent.mkdir(parents=True)
    p.write_text('{"type":"FeatureCollection","features":[]}')
    with pytest.raises(RouteGeometryError, match='hash mismatch'):
        RouteGeometryService(tmp_path, object())._snapshot({'path': SNAPSHOT, 'sha256': '0'*64})


def test_generated_interactive_map_and_route_geojson(generated_site):
    output, _ = generated_site
    map_data = json.loads((output / 'map/features.geojson').read_text())
    for key, count in [('camp', 3), ('bear', 5)]:
        eid = f'route-emigrant-crabtree-{key}-lake'
        features = [f for f in map_data['features'] if f['properties'].get('entity_id') == eid]
        assert len(features) == count
        assert all(f['properties']['layer'] == 'routes' for f in features)
        route_data = json.loads((output / f'geometry/routes/{eid}.geojson').read_text())
        assert len(route_data['features']) == count
        assert route_data['wayproof']['distance_complete'] is False
        html = (output / f'knowledge/{eid}/index.html').read_text()
        assert 'id="route-map"' in html
        assert f'/geometry/routes/{eid}.geojson' in html
        assert 'gap-emigrant-crabtree-geometry-limitations' in html
        data = json.loads((output / f'knowledge/{eid}.json').read_text())
        assert data['route_geometry']['wayproof']['navigation_grade'] is False
