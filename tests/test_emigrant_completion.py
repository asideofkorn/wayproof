"""Combined batch: source fidelity, route boundaries, booking and consumer output."""
from datetime import date
import hashlib
import json
import pytest
from scripts.ingest_emigrant_completion import (ROOT,BOUNDARY,CABINS,CHANGE_ID,CHERRY_SITES,
    MANIFEST,ACCESS_MANIFEST,SNAPSHOT,ROUTES,LEGS,REPLACEMENTS,cid,route,segment,th,node,place,campground)
from wayproof.canonical_storage import load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ActivityContext,ChangeSetStatus,EquipmentContext,TripIntent
from wayproof.requirements import Applicability
from wayproof.traversal import resolve_traversal,TraversalState
from wayproof.intent import IntentResolutionState
from wayproof.recheck import RecheckAnswerability

DAY=date(2027,7,12)
@pytest.fixture(scope='module')
def reads():return CanonicalReadService(ROOT)
def intent(reads,query,day=DAY,overnight=True,**kw):
 return reads.resolve_intent(TripIntent((query,),day,activities=ActivityContext(('hiking',),{'overnight':overnight}),**kw))
def items(reads,context,manifest=MANIFEST):return {i.input_id:i for i in reads.pretrip_recheck(context,manifest).items}
def applies(reads,context):return {a.rule_id for a in reads.requirements(context).rule_assessments if a.applicability is Applicability.APPLIES}

@pytest.mark.parametrize('key',ROUTES)
def test_selected_approaches_traverse_both_directions_without_fabricated_mileage(reads,key):
 name,entry,obj,end,legs,land=ROUTES[key]
 rt,start,finish=reads.entity(route(key)),reads.entity(th(entry)),reads.entity(node(end))
 forward=resolve_traversal(reads,rt,start,finish,DAY);reverse=resolve_traversal(reads,rt,finish,start,DAY)
 expected=[segment(k) for k in legs]
 assert forward.state is reverse.state is TraversalState.COMPLETE
 assert [l.segment_id for l in forward.legs]==expected
 assert [l.segment_id for l in reverse.legs]==expected[::-1]
 assert forward.total_known_distance_miles==reverse.total_known_distance_miles==0
 assert not forward.distance_complete and all(l.distance_miles is None for l in forward.legs)
 if obj:assert place(obj) in forward.legs[-1].accessible_entity_ids and node(end)!=place(obj)
 result=intent(reads,name)
 assert result.state is IntentResolutionState.PARTIAL and result.route.entity_id==route(key)
 assert result.entry.entity_id==th(entry) and result.exit is None and result.traversal is None
 selected=items(reads,result.context)
 assert 'gap-emigrant-completion-'+key+'-limits' in selected
 for other in ROUTES:
  assert (cid(other+'-profile') in selected) is (other==key)
 rule_ids=applies(reads,result.context)
 assert ('rule-emigrant-overnight-wilderness-permit' in rule_ids) is (land=='scope-emigrant-wilderness')
 assert ('rule-yosemite-overnight-wilderness-permit' in rule_ids) is (land=='scope-yosemite-wilderness')
 assert ('rule-emigrant-completion-leavitt-overnight-permit' in rule_ids) is (entry=='leavitt-lake')
 geo=reads.route_geometry(route(key),DAY)
 if key.startswith(('bourland','leavitt')):
  assert len(geo['features'])==len(legs) and not geo['wayproof']['navigation_grade']
 else:assert geo is None


def test_named_lakes_reject_unsupported_entries_and_share_shingle_approach(reads):
 for key,obj in [('box-springs-chain-lakes','chain-lakes'),('shingle-springs-kibbie-lake','kibbie-lake'),('shingle-springs-huckleberry-lake','huckleberry-lake')]:
  result=intent(reads,place(obj));assert result.route.entity_id==route(key)
  bad=intent(reads,place(obj),entry_query='Gianelli Cabin Trailhead')
  assert bad.state is IntentResolutionState.AMBIGUOUS and bad.traversal is None
 assert ROUTES['shingle-springs-kibbie-lake'][4][0]==ROUTES['shingle-springs-huckleberry-lake'][4][0]=='shingle-start'
 assert not any(r.predicate=='provides_access_to' and r.subject_id==node('bourland-mapped-terminus') for r in reads.relationships_for(node('bourland-mapped-terminus')))


def test_leavitt_rule_requirement_joins_and_entry_only_does_not_imply_entry(reads):
 for overnight in (True,False):
  c=intent(reads,ROUTES['leavitt-lake-pct-junction'][0],overnight=overnight).context
  evaluated=reads.requirements(c);ids={r.requirement.requirement_id for r in evaluated.requirements}
  assert ('requirement-emigrant-completion-leavitt-overnight-permit' in ids) is overnight
  assert 'requirement-emigrant-completion-leavitt-food-storage' in ids
  for rid in ids:
   if rid.startswith('requirement-emigrant-completion-'):assert reads.get('requirement',rid)
  selected=items(reads,c);assert selected[cid('leavitt-route-quota')].source_ids==('source-usfs-hoover-wilderness',)
  assert 'gap-emigrant-completion-leavitt-mileage' in selected
  assert 'gap-emigrant-completion-cross-boundary-continuation' in selected
  assert reads.get('claim',cid('leavitt-route-quota')).value['quota'] is False
 for entry in ['leavitt-lake','shingle-springs','bourland-meadow','box-springs']:
  c=intent(reads,th(entry)).context
  assert not any('overnight' in r for r in applies(reads,c))
  assert 'gap-emigrant-completion-'+entry+'-access' in items(reads,c,ACCESS_MANIFEST)
 c=intent(reads,'Emigrant Wilderness').context
 assert c.stages[0].spatial_scope_ids==('scope-emigrant-wilderness',)
 assert 'rule-emigrant-completion-leavitt-overnight-permit' not in applies(reads,c)


def test_yosemite_destination_rules_apply_despite_stanislaus_issuance(reads):
 c=intent(reads,place('kibbie-lake'),equipment=EquipmentContext(attributes={'equipment':('pet',)})).context
 assert {'rule-yosemite-wilderness-no-pets','rule-yosemite-wilderness-bear-canister','rule-yosemite-overnight-wilderness-permit'}<=applies(reads,c)
 selected=items(reads,c)
 assert cid('kibbie-issuer') in selected and cid('kibbie-fire') in selected
 assert 'gap-emigrant-completion-yose-continuity' in selected
 assert reads.get('claim',cid('kibbie-issuer')).value['agency']=='Stanislaus National Forest'
 assert reads.get('claim',cid('kibbie-fire')).value['campfires_allowed'] is False


def test_geometry_identity_hashes_and_exact_preexisting_pct_junction(reads):
 payload=json.loads((ROOT/SNAPSHOT).read_text());assert len(payload['features'])==6
 assert [q['feature_count'] for q in payload['wayproof']['queries']]==[71,207]
 assert payload['wayproof']['source_coordinate_reference_system']=='EPSG:4269'
 for (key,fid,a,z),f in zip(LEGS,payload['features'],strict=True):
  p=f['properties'];assert p['source_attributes']['objectid']==fid and p['source_vertex_range_inclusive']==[a,z]
  assert p['source_attributes']['globalid'] and len(p['source_geometry_sha256'])==64
  assert len(f['geometry']['coordinates'])==z-a+1
  c=reads.get('claim',cid(key+'-geometry'));assert c.value['geometry_snapshot']['sha256']==hashlib.sha256((ROOT/SNAPSHOT).read_bytes()).hexdigest()
 for a,z in zip(payload['features'][1:5],payload['features'][2:6]):assert a['geometry']['coordinates'][-1]==z['geometry']['coordinates'][0]
 existing=reads.route_geometry('route-emigrant-sonora-pass-leavitt-junction',DAY)
 assert existing['features'][-1]['geometry']['coordinates'][-1]==payload['features'][-1]['geometry']['coordinates'][-1]
 boundary=reads.managed_land_geometry('wilderness-emigrant')
 assert boundary['geometry']['type']=='Polygon' and not boundary['properties']['navigation_grade']
 p=boundary['properties']['source_features'][0]
 assert (p['OBJECTID'],p['Category'],p['Des_Tp'],p['Mang_Name'])==(237112,'Designation','WA','USFS')
 ref=reads.get('claim',cid('boundary')).value['boundary_geometry_snapshot']
 assert ref['sha256']==hashlib.sha256((ROOT/BOUNDARY).read_bytes()).hexdigest()
 assert 'overlap does not' in reads.get('gap','gap-emigrant-boundary-geometry').reason


def test_orders_remain_bounded_and_do_not_make_blanket_closures(reads):
 for day,expected in [(date(2026,10,6),RecheckAnswerability.ANSWERED),(DAY,RecheckAnswerability.NEEDS_CURRENT_CHECK)]:
  selected=items(reads,intent(reads,th('shingle-springs'),day=day).context,ACCESS_MANIFEST)
  assert selected[cid('cherry-shore-order')].answerability is expected
  assert selected[cid('cherry-road-order')].answerability is expected
  assert cid('cherry-order-recheck') in selected and 'gap-emigrant-completion-cherry-orders' in selected
 assert reads.get('claim',cid('cherry-road-order')).value['road']=='1N98'
 assert reads.get('claim',cid('cherry-shore-order')).value['not_general_campground_closure']
 assert cid('cherry-road-order') not in items(reads,intent(reads,th('leavitt-lake')).context,ACCESS_MANIFEST)


def test_campground_conflicts_are_contextual_and_keep_observation_dates_unknown(reads):
 c=intent(reads,campground('cherry-valley')).context;selected=items(reads,c,ACCESS_MANIFEST)
 assert 'gap-emigrant-completion-cherry-conflicts' in selected
 for key in ['cherry-fees-overview','cherry-valley-fees-table','cherry-water-notice','cherry-water-booking','cherry-valley-water-summary','cherry-valley-toilets-overview','cherry-valley-toilets-amenities']:
  assert cid(key) in selected
  explained=reads.explain_claim(cid(key));assert explained.observations[0].observed_at is None
 assert reads.get('claim',cid('cherry-fees-overview')).value['reported_usd_per_night']==41
 assert reads.get('claim',cid('cherry-valley-fees-table')).value['single_usd']==29
 assert reads.get('claim',cid('cherry-water-notice')).value['notice_date']=='2025-07-03'
 for key in ['baker','deadman']:
  c=intent(reads,campground(key)).context;selected=items(reads,c,ACCESS_MANIFEST)
  assert 'gap-emigrant-completion-'+key+'-facilities' in selected
  assert cid(key+'-surface-history') in selected and cid(key+'-surface-current') in selected
  assert reads.get('claim',cid(key+'-booking')).value['reservations'] is False


def test_individual_booking_inventory_inherits_parent_rechecks_without_live_availability(reads):
 assert len(CHERRY_SITES)==45 and {r[0] for r in CHERRY_SITES}=={f'{i:03}' for i in range(2,47)}
 for number,rid,kind,people,vehicles,*_ in CHERRY_SITES:
  key='cherry-site-'+number;eid='campsite-emigrant-cherry-valley-'+number
  c=reads.get('claim',cid(key+'-occupancy'));assert c.value['maximum_people']==people and c.value['maximum_vehicles']==vehicles
  explained=reads.explain_claim(cid(key+'-identity'));assert explained.sources[0].locator.endswith('/'+rid)
  assert explained.claim.value['availability']=='unknown'
  assert any(r.predicate=='part_of' and r.object_id==campground('cherry-valley') for r in reads.relationships_for(eid))
 selected=items(reads,intent(reads,'campsite-emigrant-cherry-valley-029').context,ACCESS_MANIFEST)
 assert 'gap-emigrant-completion-cherry-conflicts' in selected and 'gap-emigrant-completion-cherry-site-029-booking' in selected
 assert cid('cherry-site-030-identity') not in selected
 c=reads.get('claim',cid('cherry-site-029-vehicle')).value
 assert c['driveway_max_vehicle_length_report']==24 and c['driveway_length_report']=='32' and '50 ft.' in c['equipment_section']
 assert reads.get('claim',cid('cherry-site-011-timing')).value['checkout']=='1:00 PM'
 assert reads.get('claim',cid('cherry-site-002-vehicle')).value['driveway_max_vehicle_length_report'] is None
 assert len(CABINS)==21 and 13 not in {r[0] for r in CABINS}
 selected=items(reads,intent(reads,'cabin-emigrant-kennedy-3').context,ACCESS_MANIFEST)
 assert cid('kennedy-cabin-terms') in selected and 'gap-emigrant-completion-kennedy-bookings' in selected
 assert reads.get('claim',cid('kennedy-cabin-3-inventory')).value['kitchenette_exception']=='no kitchenette'
 assert cid('kennedy-cabin-4-inventory') not in selected


def test_one_validated_changeset_and_bounded_replacements():
 change=load_changeset(ROOT/'changesets/v0'/f'{CHANGE_ID}.json')
 assert change.status is ChangeSetStatus.VALIDATED
 from wayproof.schema import ChangeAction
 assert {op.record_id for op in change.operations if op.action is ChangeAction.REPLACE}==REPLACEMENTS
 assert sum(op.record_type=='rule' for op in change.operations)==2


def test_generated_routes_boundary_facilities_booking_and_evidence(generated_site):
 output,_=generated_site
 trail_ids={x['entity_id'] for x in json.loads((output/'trails/index.json').read_text())['entities']}
 assert {route(k) for k in ROUTES}<=trail_ids
 features=json.loads((output/'map/features.geojson').read_text())['features']
 assert any(f['properties'].get('entity_id')=='wilderness-emigrant' and f['geometry']['type']=='Polygon' for f in features)
 for key,(_,_,_,_,legs,_) in ROUTES.items():
  eid=route(key);data=json.loads((output/f'knowledge/{eid}.json').read_text());html=(output/f'knowledge/{eid}/index.html').read_text()
  assert 'gap-emigrant-completion-'+key+'-limits' in html
  if key.startswith(('bourland','leavitt')):
   assert len(data['route_geometry']['features'])==len(legs)
   assert (output/f'geometry/routes/{eid}.geojson').exists() and 'id="route-map"' in html
  else:assert not data['route_geometry'] and not (output/f'geometry/routes/{eid}.geojson').exists()
 camping_ids={x['entity_id'] for x in json.loads((output/'camping/index.json').read_text())['entities']}
 assert {campground(k) for k in ['baker','deadman','cherry-valley']}<=camping_ids
 assert {'campsite-emigrant-cherry-valley-'+r[0] for r in CHERRY_SITES}<=camping_ids
 assert {'cabin-emigrant-kennedy-'+str(r[0]) for r in CABINS}<=camping_ids
 html=(output/'knowledge/campsite-emigrant-cherry-valley-029/index.html').read_text()
 assert '92031' in html and 'unknown' in html
 conflict=(output/'evidence/gap/gap-emigrant-completion-cherry-conflicts/index.html').read_text()
 assert 'water' in conflict and '$41' in conflict and '$29' in conflict
 assert CHANGE_ID in (output/'changes/index.html').read_text()
