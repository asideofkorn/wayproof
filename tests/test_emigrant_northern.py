"""Northern planning preserves boundaries, historical conflicts and missing geometry."""
from datetime import date
import hashlib
import json
import pytest
from scripts.ingest_emigrant_northern import (ACCESS_MANIFEST,CHANGE_ID,LEGS,MANIFEST,
    REPLACEMENTS,ROOT,ROUTES,SNAPSHOT,place,node,route,segment,th)
from wayproof.canonical_storage import load_changeset
from wayproof.intent import IntentResolutionState
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability,RecheckState
from wayproof.requirements import Applicability
from wayproof.schema import ActivityContext,ChangeSetStatus,TripIntent
from wayproof.traversal import TraversalState,resolve_traversal

DAY=date(2027,7,12)
PREFIX='claim-emigrant-northern-'

@pytest.fixture(scope='module')
def reads():return CanonicalReadService(ROOT)

def intent(reads,query,day=DAY,**kw):
    return reads.resolve_intent(TripIntent((query,),day,activities=ActivityContext(('hiking',),{'overnight':True}),**kw))

def ids(reads,context,manifest):return {i.input_id for i in reads.pretrip_recheck(context,manifest).items}

@pytest.mark.parametrize('key',ROUTES)
def test_northern_routes_traverse_both_directions_with_explicit_geometry_limits(reads,key):
    name,entry,obj,end,legs,enters=ROUTES[key]
    rt,start,finish=reads.entity(route(key)),reads.entity(th(entry)),reads.entity(node(end))
    out=resolve_traversal(reads,rt,start,finish,DAY);back=resolve_traversal(reads,rt,finish,start,DAY)
    expected=[segment(x) for x in legs]
    assert out.state is back.state is TraversalState.COMPLETE
    assert [x.segment_id for x in out.legs]==expected
    assert [x.segment_id for x in back.legs]==expected[::-1]
    assert out.total_known_distance_miles==back.total_known_distance_miles==(0.5 if entry=='kennedy-meadows' else 0)
    assert not out.distance_complete and not back.distance_complete
    assert [x.distance_miles for x in out.legs]==([0.5,None,None] if entry=='kennedy-meadows' else [None]*len(legs))
    if entry=='kennedy-meadows':assert out.legs[0].distance_status=='reported'
    if obj:
        assert place(obj) in out.legs[-1].accessible_entity_ids
        assert node(end)!=place(obj)
    geo=reads.route_geometry(route(key),DAY)
    if entry=='kennedy-meadows':assert geo is None
    else:
        assert [f['properties']['segment_id'] for f in geo['features']]==expected
        assert not geo['wayproof']['navigation_grade'] and not geo['wayproof']['distance_complete']
    result=intent(reads,place(obj) if obj else name)
    assert result.state is IntentResolutionState.PARTIAL
    assert result.route.entity_id==route(key) and result.entry.entity_id==th(entry)
    assert result.exit is None and result.traversal is None
    assert {i.code for i in result.issues}=={'exit_unknown'}
    selected=ids(reads,result.context,MANIFEST)
    assert f'gap-emigrant-northern-{key}-planning' in selected
    assert PREFIX+key+'-conditions' in selected
    assert all(PREFIX+other+'-conditions' not in selected for other in ROUTES if other!=key)
    assert all(PREFIX+other+'-profile' not in selected for other in ROUTES if other!=key)
    assert f'gap-emigrant-northern-{entry}-access' in ids(reads,result.context,ACCESS_MANIFEST)
    # Direct route requests must receive the same wilderness applicability as
    # resource requests; Eagle's northern boundary approach must not assert entry.
    for context in (result.context,intent(reads,name).context):
        rules=reads.requirements(context)
        assessment=next(x for x in rules.rule_assessments if x.rule_id=='rule-emigrant-overnight-wilderness-permit')
        assert assessment.applicability is (Applicability.APPLIES if enters else Applicability.DOES_NOT_APPLY)
        assert ('requirement-emigrant-overnight-wilderness-permit' in {x.requirement.requirement_id for x in rules.requirements}) is enters


def test_kennedy_shared_walks_are_one_physical_graph_without_partial_geojson(reads):
    a,b=[ROUTES[k][4] for k in ('kennedy-meadows-kennedy-lake','kennedy-meadows-relief-reservoir')]
    assert a[:2]==b[:2]==['kennedy-parking-start','kennedy-start-junction']
    assert a[-1]!=b[-1]
    for key in set(a+b):
        assert not any(c.predicate=='reviewed_route_display_geometry' for c in reads.claims_for(segment(key)))
    result=intent(reads,place('kennedy-lake'),entry_query=reads.entity(th('sonora-pass')).name)
    assert result.state is IntentResolutionState.AMBIGUOUS and result.traversal is None
    assert any('not_supported' in x.code for x in result.issues)


def test_pct_junction_does_not_invent_lake_or_summit_access(reads):
    endpoint=node('pct-leavitt-lake-junction')
    assert reads.entity(endpoint).kind=='route_node'
    relationships=reads.relationships_for(endpoint)
    assert not any(x.predicate=='provides_access_to' and x.subject_id==endpoint for x in relationships)
    gap=reads.get('gap','gap-emigrant-northern-sonora-pass-leavitt-junction-planning')
    assert all(x in gap.reason for x in ('Hoover','Leavitt Peak','Leavitt Lake','Jurisdiction'))
    snapshot=json.loads((ROOT/SNAPSHOT).read_text())
    branch=snapshot['wayproof']['junction_corroboration']
    assert branch['source_attributes']['objectid']==9475574
    assert branch['source_geometry']['coordinates'][-1]==snapshot['features'][-1]['geometry']['coordinates'][-1]
    assert all(f['properties']['source_attributes']['objectid']!=9475574 for f in snapshot['features'])


def test_display_snapshot_retains_reviewed_ranges_hashes_and_exact_pct_joins(reads):
    content=(ROOT/SNAPSHOT).read_bytes();data=json.loads(content);meta=data['wayproof']
    assert len(data['features'])==len(LEGS)==9
    assert meta['query_feature_count']==207 and meta['query_parameters']['geometry']=='-119.98,38.20,-119.52,38.37'
    assert meta['query_parameters']['outSR']=='4326' and meta['source_coordinate_reference_system']=='EPSG:4269'
    assert len(meta['reviewed_input_sha256'])==64 and not meta['navigation_grade']
    for (key,fid,a,b,*_),f in zip(LEGS,data['features'],strict=True):
        p=f['properties'];assert p['source_attributes']['objectid']==fid
        assert p['source_vertex_range_inclusive']==[a,b]
        assert len(f['geometry']['coordinates'])==b-a+1
        assert len(p['source_geometry_sha256'])==64
        e=reads.explain_claim(PREFIX+key+'-geometry')
        assert e.claim.value['geometry_snapshot']['sha256']==hashlib.sha256(content).hexdigest()
        assert e.sources[0].source_id=='source-usfs-emigrant-nfs-trail-geometry'
        assert e.observations[0].observed_at is None
        assert e.claim.value['source_coordinate_accuracy']=='unknown'
    for a,b in zip(data['features'][4:8],data['features'][5:9]):
        assert a['geometry']['coordinates'][-1]==b['geometry']['coordinates'][0]

@pytest.mark.parametrize('entry',['kennedy-meadows','sonora-pass','coyote-meadow','waterhouse','eagle-meadow'])
def test_access_only_rechecks_are_scoped_and_do_not_imply_wilderness_entry(reads,entry):
    result=intent(reads,reads.entity(th(entry)).name)
    assert reads.pretrip_recheck(result.context,MANIFEST).state is RecheckState.NOT_APPLICABLE
    selected=ids(reads,result.context,ACCESS_MANIFEST)
    assert f'gap-emigrant-northern-{entry}-access' in selected
    assert PREFIX+entry+'-access-recheck' in selected
    for other in ('kennedy-meadows','sonora-pass','coyote-meadow','waterhouse','eagle-meadow'):
        assert (PREFIX+other+'-access-recheck' in selected) is (other==entry)
    assert not any(x.rule_id=='rule-emigrant-overnight-wilderness-permit' and x.applicability is Applicability.APPLIES for x in reads.requirements(result.context).rule_assessments)


def test_kennedy_conflicts_and_water_uncertainty_reach_consumers(reads):
    context=intent(reads,place('kennedy-lake')).context
    selected=ids(reads,context,ACCESS_MANIFEST)
    assert 'gap-emigrant-northern-kennedy-camping-fees' in selected
    for suffix,nights in [('brightman-2020',2),('traveler-2023',1)]:
        c=reads.get('claim',PREFIX+'kennedy-limit-'+suffix)
        assert c.value['reported_nights']==nights and c.claim_id in selected
    for suffix,fee in [('brightman-2020',5),('kennedy-pct',10)]:
        c=reads.get('claim',PREFIX+'kennedy-fee-'+suffix)
        assert c.value['reported_usd_per_night']==fee and c.value['current_fee']=='unknown' and c.claim_id in selected
    water=reads.explain_claim(PREFIX+'kennedy-water')
    assert water.claim.value['current_flow']==water.claim.value['potability']=='unknown'
    assert water.claim.claim_id in selected and water.observations[0].observed_at is None
    assert 'gap-emigrant-northern-kennedy-meadows-operator' in selected
    assert 'gap-emigrant-northern-kennedy-mileage-basis' in ids(reads,context,MANIFEST)
    relief=reads.get('claim',PREFIX+'kennedy-meadows-relief-reservoir-mileage-traveler-2023')
    assert relief.value['reported_miles']==6 and relief.value['distance_convention']=='round trip'
    parking=reads.get('claim',PREFIX+'kennedy-parking-distance')
    assert parking.value['reported_miles']==0.5 and parking.value['not_added_to_destination_reports']


def test_road_reports_retain_range_conflict_and_expired_interval(reads):
    context=intent(reads,th('waterhouse')).context
    selected=ids(reads,context,ACCESS_MANIFEST)
    assert 'gap-emigrant-northern-waterhouse-road-number' in selected
    assert 'gap-emigrant-northern-waterhouse-order-id' in selected
    c=reads.get('claim',PREFIX+'waterhouse-directions')
    assert c.value['mileage_precision']=='approximate'
    assert c.value['legs'][-1]['approximate_miles']=={'minimum':0.5,'maximum':0.75}
    assert '4N31' in c.value['legs'][-1]['instruction']
    assert reads.get('claim',PREFIX+'waterhouse-map-road').value['road_label']=='5N31'
    c=reads.get('claim',PREFIX+'waterhouse-road-order')
    assert c.temporal_scope.starts_on==date(2026,6,1) and c.temporal_scope.ends_on==date(2026,6,15)
    assert c.value['over_snow_exception']['minimum_snow_inches']==12
    check=reads.pretrip_recheck(context,ACCESS_MANIFEST)
    assert next(x for x in check.items if x.input_id==c.claim_id).answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    historical=reads.pretrip_recheck(intent(reads,th('waterhouse'),date(2026,6,10)).context,ACCESS_MANIFEST)
    assert next(x for x in historical.items if x.input_id==c.claim_id).answerability is RecheckAnswerability.ANSWERED


def test_horse_camps_are_not_trailhead_toilets_and_sonora_project_is_not_completion(reads):
    c=reads.get('claim',PREFIX+'eagle-meadow-facilities')
    assert c.value['reported_facilities']=='none' and c.value['current_inventory']=='unknown'
    camp='campground-emigrant-eagle-meadow-horse'
    c=reads.get('claim',PREFIX+'eagle-meadow-horse-facilities')
    assert c.subject_id==camp and c.value['reported_improvements']==['restrooms','fire rings']
    assert not any(x.predicate=='provides_access_to' and x.object_id==camp for x in reads.relationships_for(th('eagle-meadow')))
    context=intent(reads,camp).context
    assert 'gap-emigrant-northern-eagle-meadow-horse-access' in ids(reads,context,ACCESS_MANIFEST)
    assert reads.get('claim',PREFIX+'sonora-toilet-project').value['completion_status']=='unknown'


def test_one_validated_changeset_preserves_published_history():
    change=load_changeset(ROOT/f'changesets/v0/{CHANGE_ID}.json')
    assert change.status is ChangeSetStatus.VALIDATED
    assert {o.record_id for o in change.operations if o.action.value=='REPLACE'}==REPLACEMENTS
    assert not any(o.record_type=='rule' for o in change.operations)
    assert sum(o.record_type=='entity' for o in change.operations)==42


def test_generated_northern_routes_conflicts_and_distinct_facilities(generated_site):
    output,_=generated_site
    trails=json.loads((output/'trails/index.json').read_text())
    assert {route(k) for k in ROUTES}<={e['entity_id'] for e in trails['entities']}
    map_features=json.loads((output/'map/features.geojson').read_text())['features']
    for key,(name,entry,obj,end,legs,enters) in ROUTES.items():
        eid=route(key);html=(output/f'knowledge/{eid}/index.html').read_text();data=json.loads((output/f'knowledge/{eid}.json').read_text())
        assert f'gap-emigrant-northern-{key}-planning' in html
        count=sum(f['properties'].get('entity_id')==eid for f in map_features)
        if entry=='kennedy-meadows':
            assert not data['route_geometry'] and count==0 and 'id="route-map"' not in html
            assert not (output/f'geometry/routes/{eid}.geojson').exists()
        else:
            assert data['route_geometry'] and count==len(legs) and 'id="route-map"' in html
            assert len(json.loads((output/f'geometry/routes/{eid}.geojson').read_text())['features'])==len(legs)
    camping=json.loads((output/'camping/index.json').read_text())
    assert {'campground-emigrant-eagle-meadow-horse','campground-emigrant-coyote-meadow-horse'}<={e['entity_id'] for e in camping['entities']}
    search=json.loads((output/'search/index.json').read_text())
    assert {'restroom-emigrant-kennedy-meadows','restroom-emigrant-sonora-pass','water-source-emigrant-kennedy-faucets'}<={e['entity_id'] for e in search['entities']}
    conflict=(output/'evidence/gap/gap-emigrant-northern-kennedy-camping-fees/index.html').read_text()
    assert all(x in conflict for x in ('two nights','one night','$5/night','$10/night'))
    assert 'unknown' in (output/'knowledge/water-source-emigrant-kennedy-faucets/index.html').read_text()
    assert CHANGE_ID in (output/'changes/index.html').read_text()
