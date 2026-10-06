"""Western approaches share physical paths and retain source/itinerary limits."""
from datetime import date
import hashlib
import json
from pathlib import Path
import pytest
from scripts.ingest_emigrant_western import (ACCESS_MANIFEST, CHANGE_ID, LEGS, MANIFEST,
    REPLACEMENTS, ROOT, ROUTES, SNAPSHOT, lake, node, old_segment, route, segment, th)
from wayproof.canonical_storage import load_changeset
from wayproof.intent import IntentResolutionState
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckState
from wayproof.requirements import Applicability
from wayproof.schema import ActivityContext, ChangeSetStatus, TripIntent
from wayproof.traversal import TraversalState, resolve_traversal

DAY = date(2027, 7, 12)

@pytest.fixture(scope='module')
def reads(): return CanonicalReadService(ROOT)

@pytest.mark.parametrize('key', ROUTES)
def test_selected_approach_traverses_both_directions_and_draws(reads, key):
    name, entry, objective, end, legs, _ = ROUTES[key]
    expected = [x if x.startswith('route-segment-') else segment(x) for x in legs]
    rt, start, finish = reads.entity(route(key)), reads.entity(th(entry)), reads.entity(node(end))
    out = resolve_traversal(reads, rt, start, finish, DAY)
    back = resolve_traversal(reads, rt, finish, start, DAY)
    assert out.state is back.state is TraversalState.COMPLETE
    assert [x.segment_id for x in out.legs] == expected
    assert [x.segment_id for x in back.legs] == expected[::-1]
    assert out.total_known_distance_miles == back.total_known_distance_miles == 0
    assert not out.distance_complete and not back.distance_complete
    assert all(x.distance_miles is None for x in out.legs)
    assert lake(objective) in out.legs[-1].accessible_entity_ids
    assert finish.entity_id != lake(objective)
    geo = reads.route_geometry(route(key), DAY)
    assert [f['properties']['segment_id'] for f in geo['features']] == expected
    assert not geo['wayproof']['navigation_grade'] and not geo['wayproof']['distance_complete']
    resolved = reads.resolve_intent(TripIntent((reads.entity(lake(objective)).name,), DAY,
        route_query=name, activities=ActivityContext(('hiking',), {'overnight':True})))
    assert resolved.state is IntentResolutionState.PARTIAL
    assert resolved.route.entity_id == route(key) and resolved.entry.entity_id == th(entry)
    assert resolved.exit is None and resolved.traversal is None
    assert {i.code for i in resolved.issues} == {'exit_unknown'}
    ev = reads.requirements(resolved.context)
    assert next(i for i in ev.rule_assessments if i.rule_id == 'rule-emigrant-overnight-wilderness-permit').applicability is Applicability.APPLIES
    assert 'requirement-emigrant-overnight-wilderness-permit' in {i.requirement.requirement_id for i in ev.requirements}
    check = reads.pretrip_recheck(resolved.context, MANIFEST)
    ids = {i.input_id for i in check.items}
    assert check.state is RecheckState.REQUIRED
    assert f'gap-emigrant-western-{key}-planning' in ids
    assert f'claim-emigrant-western-{key}-conditions' in ids
    # A selected route does not acquire a different route's claims or conditions.
    assert all(f'claim-emigrant-western-{other}-conditions' not in ids for other in ROUTES if other != key)
    access = reads.pretrip_recheck(resolved.context, ACCESS_MANIFEST)
    assert f'gap-emigrant-western-{entry}-access' in {i.input_id for i in access.items}
    assert 'gap-emigrant-western-occupancy-supersession' in {i.input_id for i in access.items}
    foundation = reads.pretrip_recheck(resolved.context, 'result-emigrant-pretrip-recheck')
    assert 'gap-emigrant-lake-night-limit-conflict' in {i.input_id for i in foundation.items}

@pytest.mark.parametrize('objective', ['chewing-gum','grouse'])
def test_two_supported_approaches_require_route_selection(reads, objective):
    result = reads.resolve_intent(TripIntent((reads.entity(lake(objective)).name,), DAY))
    assert result.state is IntentResolutionState.AMBIGUOUS
    assert result.route is None and result.traversal is None


def test_unrelated_entry_is_not_accepted(reads):
    result = reads.resolve_intent(TripIntent(('Gem Lake (Emigrant Wilderness)',), DAY,
        route_query='Crabtree to Gem Lake', entry_query='Gianelli Cabin Trailhead'))
    assert result.state is IntentResolutionState.AMBIGUOUS
    assert result.traversal is None and any('not_supported' in i.code for i in result.issues)


def test_shared_paths_reuse_identical_physical_geometry(reads):
    def geos(key): return {f['properties']['segment_id']:f['geometry'] for f in reads.route_geometry(route(key),DAY)['features']}
    gp, gc = geos('gianelli-powell'), geos('gianelli-chewing-gum')
    assert set(gp) & set(gc) == {segment('gianelli-burst'),segment('burst-powell-junction')}
    assert all(gp[k] == gc[k] for k in set(gp)&set(gc))
    bg, cg = geos('bell-meadow-grouse'), geos('crabtree-grouse')
    assert set(bg)&set(cg) == {segment('pine-grouse-break'),segment('grouse-approach')}
    assert all(bg[k] == cg[k] for k in set(bg)&set(cg))
    gem = geos('crabtree-gem')
    bear = {f['properties']['segment_id']:f['geometry'] for f in reads.route_geometry('route-emigrant-crabtree-bear-lake',DAY)['features']}
    assert len(set(gem)&set(bear)) == 4
    assert all(gem[k] == bear[k] for k in set(gem)&set(bear))
    assert old_segment('bear-spur') not in gem


def test_snapshot_preserves_source_ranges_and_unsnapped_offsets(reads):
    content=(ROOT/SNAPSHOT).read_bytes();data=json.loads(content)
    assert len(data['features']) == len(LEGS) == 14
    assert data['wayproof']['query_feature_count'] == 45
    assert data['wayproof']['query_parameters']['outSR'] == '4326'
    assert data['wayproof']['source_coordinate_reference_system'] == 'EPSG:4269'
    assert not data['wayproof']['navigation_grade']
    for leg,f in zip(LEGS,data['features'],strict=True):
        key,fid,a,b,*_=leg;props=f['properties']
        assert props['source_attributes']['objectid'] == fid
        assert props['source_vertex_range_inclusive'] == [a,b]
        assert len(f['geometry']['coordinates']) == abs(a-b)+1
        assert len(props['source_geometry_sha256']) == 64
        c=reads.explain_claim('claim-emigrant-western-'+key+'-geometry')
        assert c.claim.value['geometry_snapshot']['sha256'] == hashlib.sha256(content).hexdigest()
        assert c.sources[0].source_id == 'source-usfs-emigrant-nfs-trail-geometry'
        assert c.observations[0].observed_at is None
    # Deliberately preserve source offsets, while mapped topology joins the nodes.
    fs={f['properties']['feature_id'].removeprefix('usfs-emigrant-western-'):f['geometry']['coordinates'] for f in data['features']}
    assert fs['burst-powell-junction'][-1] != fs['powell-spur'][0]
    assert fs['pine-connector'][-1] != fs['bell-pine'][-1]
    assert fs['north-chewing'][-1] == fs['south-chewing'][-1]


def test_distance_conflicts_remain_reports_and_camping_precision_survives(reads):
    for suffix,value in [('gianelli-powell-table',2.3),('powell-favorite-hikes',2),('powell-mileage-diagram',2.0),('powell-trail-map',1.8)]:
        c=reads.get('claim','claim-emigrant-western-'+suffix)
        assert c.value['reported_one_way_miles'] == value and c.value['not_atomic_distance']
        assert c.predicate == 'published_approach_distance_report'
    assert reads.get('claim','claim-emigrant-western-crabtree-gem-table').value['reported_one_way_miles'] == 9.5
    operator=reads.explain_claim('claim-emigrant-western-gem-operator-mileage')
    assert operator.claim.value['reported_miles'] == 10
    assert operator.claim.value['distance_convention'] == 'not explicitly stated'
    assert operator.observations[0].observed_at is None
    assert operator.sources[0].publisher == 'Aspen Meadow Pack Station'
    for key in ('chewing-gum','grouse'):
        assert reads.get('claim',f'claim-emigrant-western-{key}-minimum').value['minimum_feet'] == 100
        assert reads.get('claim',f'claim-emigrant-western-{key}-recommendation').value['recommended_feet'] == 200
    assert reads.get('claim','claim-emigrant-western-chewing-existing-sites').value['existing_site_is_not_permission']
    assert reads.get('claim','claim-emigrant-western-grouse-exclusion').value['location'] == 'between trail and Grouse Lake'

@pytest.mark.parametrize('entry',['crabtree','gianelli','bell-meadow'])
def test_access_only_does_not_imply_a_lake_or_wilderness_permit(reads,entry):
    context=reads.resolve_intent(TripIntent((reads.entity(th(entry)).name,),DAY,
        activities=ActivityContext(('hiking',),{'overnight':True}))).context
    assert reads.pretrip_recheck(context,MANIFEST).state is RecheckState.NOT_APPLICABLE
    items={i.input_id for i in reads.pretrip_recheck(context,ACCESS_MANIFEST).items}
    assert f'claim-emigrant-western-{entry}-trailhead-night-limit' in items
    assert f'claim-emigrant-western-{entry}-driving' in items
    assert all(f'claim-emigrant-western-{other}-driving' not in items for other in ('crabtree','gianelli','bell-meadow') if other!=entry)
    evaluation=reads.requirements(context)
    assert not any(i.rule_id=='rule-emigrant-overnight-wilderness-permit' and i.applicability is Applicability.APPLIES for i in evaluation.rule_assessments)
    driving=reads.get('claim',f'claim-emigrant-western-{entry}-driving').value
    assert driving['mileage_precision'] == 'approximate' and driving['source_edition'] == '2012-04'
    night=reads.get('claim',f'claim-emigrant-western-{entry}-trailhead-night-limit').value
    assert night['reported_nights']==1 and night['current_rule_status']=='unverified'
    assert ('claim-emigrant-western-crabtree-restrooms-2023' in items) is (entry=='crabtree')


def test_facility_reports_do_not_claim_operation_or_completed_construction(reads):
    for suffix in ('crabtree-restrooms-2012','crabtree-restrooms-2023'):
        e=reads.explain_claim('claim-emigrant-western-'+suffix)
        assert e.claim.value['current_availability']=='unknown'
        assert e.observations[0].observed_at is None
    assert reads.get('claim','claim-emigrant-western-crabtree-toilet-project').value['completion_status']=='unknown'
    for entry in ('gianelli','bell-meadow'):
        assert reads.get('claim',f'claim-emigrant-western-{entry}-no-facilities-report').value['current_inventory']=='unknown'
    c=reads.get('claim','claim-emigrant-western-occupancy-developed')
    assert c.temporal_scope.starts_on == date(2026,7,31) and c.temporal_scope.ends_on == date(2029,7,30)
    assert c.value['site_classification']=='not assigned to these trailheads'
    assert len(c.value['exemptions'])==2
    assert reads.get('claim','claim-emigrant-western-supersession-occupancy-order').value['reported_superseded_order']=='STF-16-2024-10'
    assert reads.get('claim','claim-emigrant-western-supersession-occupancy-page').value['reported_superseded_order']=='STF-16-2022-06'


def test_one_validated_candidate_narrows_existing_gaps():
    change=load_changeset(ROOT/f'changesets/v0/{CHANGE_ID}.json')
    assert change.status is ChangeSetStatus.VALIDATED
    assert {o.record_id for o in change.operations if o.action.value=='REPLACE'} == REPLACEMENTS
    assert not any(o.record_type=='rule' for o in change.operations)
    assert sum(o.record_type == 'entity' for o in change.operations) == 37


def test_generated_routes_map_lakes_and_historical_facilities(generated_site):
    output,_=generated_site
    directory=json.loads((output/'trails/index.json').read_text())
    assert {route(k) for k in ROUTES} <= {e['entity_id'] for e in directory['entities']}
    features=json.loads((output/'map/features.geojson').read_text())['features']
    for key,v in ROUTES.items():
        eid=route(key)
        assert len([f for f in features if f['properties'].get('entity_id')==eid])==len(v[4])
        geo=json.loads((output/f'geometry/routes/{eid}.geojson').read_text())
        assert len(geo['features'])==len(v[4]) and not geo['wayproof']['navigation_grade']
        html=(output/f'knowledge/{eid}/index.html').read_text()
        assert 'id="route-map"' in html
        assert f'gap-emigrant-western-{key}-planning' in html
        assert json.loads((output/f'knowledge/{eid}.json').read_text())['route_geometry']
    facilities=json.loads((output/'facilities/index.json').read_text())
    assert 'restroom-emigrant-crabtree' in {e['entity_id'] for e in facilities['entities']}
    restroom=(output/'knowledge/restroom-emigrant-crabtree/index.html').read_text()
    assert 'unknown' in restroom and '2023' in restroom and '2012' in restroom
    for key in ('chewing-gum','grouse'):
        html=(output/f'knowledge/{lake(key)}/index.html').read_text()
        assert '100' in html and '200' in html and 'Leave No Trace' in html
    conflict=(output/'evidence/gap/gap-emigrant-western-powell-mileage/index.html').read_text()
    assert '2.3' in conflict and '1.8' in conflict
