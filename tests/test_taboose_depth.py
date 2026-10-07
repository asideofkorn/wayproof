"""Consumer regressions for Taboose deep inventory and bounded western routes."""
from datetime import date
import hashlib
import json
import pytest
from scripts.ingest_taboose_depth import (ROOT,CHANGE_ID,MANIFEST,SNAPSHOT,ROUTES,SEGMENTS,
    TH,PASS,ROUTE,SEGMENT,CAMP,WEST,BENCH,PREFIX,segment,site_id,scope)
from wayproof.canonical_storage import load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ActivityContext,TripIntent,ChangeSetStatus
from wayproof.requirements import Applicability
from wayproof.recheck import RecheckAnswerability
from wayproof.traversal import TraversalState,resolve_traversal

DAY=date(2026,10,15)
@pytest.fixture(scope='module')
def reads():return CanonicalReadService(ROOT)
def cid(key):return 'claim-'+PREFIX+key
def intent(query,overnight=True,**kw):return TripIntent((query,),DAY,activities=ActivityContext(('hiking',),{'overnight':overnight}),**kw)
def inputs(reads,ctx):return {i.input_id:i for i in reads.pretrip_recheck(ctx,MANIFEST).items}

@pytest.mark.parametrize('key',ROUTES)
def test_western_routes_reuse_east_segment_and_traverse_in_both_directions(reads,key):
 rid,name,end,legs=ROUTES[key]
 expected=[SEGMENT,*map(segment,legs)]
 for start,finish,order in [(TH,end,expected),(end,TH,expected[::-1])]:
  path=resolve_traversal(reads,reads.entity(rid),reads.entity(start),reads.entity(finish),DAY)
  assert path.state is TraversalState.COMPLETE
  assert [l.segment_id for l in path.legs]==order
  assert not path.distance_complete and path.total_known_distance_miles==0
  assert not path.alternate_legs
 assert {r.subject_id for r in reads.relationships_for(rid) if r.predicate=='part_of'}==set(expected)
 assert any(r.subject_id==rid and r.predicate=='traverses' and r.object_id==WEST for r in reads.relationships_for(rid))
 geo=reads.route_geometry(rid,DAY)
 assert len(geo['features'])==len(expected)
 assert not geo['wayproof']['navigation_grade']
 assert not geo['wayproof']['distance_complete']

@pytest.mark.parametrize('key',ROUTES)
def test_full_itinerary_requires_both_entry_and_park_requirements(reads,key):
 rid,name,end,legs=ROUTES[key]
 resolved=reads.resolve_intent(intent(name))
 assert resolved.context is not None and resolved.traversal is None
 assert {x.code for x in resolved.issues}=={'exit_unknown'}
 evaluated=reads.requirements(resolved.context)
 applies={a.rule_id for a in evaluated.rule_assessments if a.applicability is Applicability.APPLIES}
 expected={'rule-taboose-overnight-permit',*('rule-'+PREFIX+k for k in ['west-permit','west-food','west-camping','west-fire'])}
 assert expected<=applies
 requirements={x.requirement.requirement_id:x for x in evaluated.requirements}
 for rule_id in expected:
  req_id=rule_id.replace('rule-','requirement-',1)
  assert requirements[req_id].requirement.rule_id==rule_id
  assert reads.get('requirement',req_id).rule_id==rule_id
 selected=inputs(reads,resolved.context)
 assert 'claim-taboose-west-pets' in selected
 assert cid('west-conditions') in selected
 assert 'gap-taboose-mileage' in selected
 assert cid('stock-opening') in selected
 assert selected[cid('west-conditions')].answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
 plan=reads.plan(intent(name),recheck_result_ids=(MANIFEST,))
 assert plan.rechecks and plan.readiness is not None


def test_original_east_only_trip_does_not_acquire_west_prohibition(reads):
 ctx=reads.resolve_intent(intent('Taboose Pass')).context
 selected=inputs(reads,ctx)
 assert 'claim-taboose-pets' in selected and 'claim-taboose-west-pets' not in selected
 assert cid('west-conditions') not in selected
 assert not any(a.rule_id.startswith('rule-'+PREFIX+'west-') and a.applicability is Applicability.APPLIES for a in reads.requirements(ctx).rule_assessments)
 for key in ROUTES:
  rid,name,end,_=ROUTES[key]
  ctx=reads.resolve_intent(intent(name,False)).context
  applies={a.rule_id for a in reads.requirements(ctx).rule_assessments if a.applicability is Applicability.APPLIES}
  assert 'rule-'+PREFIX+'west-permit' not in applies
  assert 'rule-'+PREFIX+'west-camping' not in applies
  assert 'rule-'+PREFIX+'west-food' in applies


def test_individual_inventory_is_complete_but_fit_and_availability_are_not_invented(reads):
 for number in range(1,37):
  key=f'{number:03d}';eid=site_id(key)
  assert reads.entity(eid).kind=='campsite'
  inventory=reads.explain_claim(cid('site-'+key+'-inventory'))
  assert inventory.claim.value['availability']=='unknown'
  assert inventory.sources[0].locator.endswith('/campsite-booking')
  fit=reads.get('claim',cid('site-'+key+'-fit')).value
  assert fit['maximum_vehicle_length']['unit']=='not stated'
  assert fit['fit_confirmed'] is False
  assert reads.get('claim',cid('site-'+key+'-accessibility')).value['provider_statement_only'] is True
  ctx=reads.resolve_intent(intent(eid)).context
  selected=inputs(reads,ctx)
  assert cid('site-'+key+'-fit') in selected
  assert cid('booking-window') in selected
  assert 'gap-taboose-camp-water-current' in selected
  assert 'claim-taboose-west-pets' not in selected
  evaluated=reads.requirements(ctx)
  assert any(x.requirement.requirement_id=='requirement-'+PREFIX+'camp-stay' for x in evaluated.requirements)
 assert reads.get('claim',cid('site-006-fit')).value['maximum_vehicle_length']['value']==25
 assert reads.get('claim',cid('site-016-fit')).value['maximum_vehicle_length']['value']==60
 assert reads.get('claim',cid('site-021-fit')).value['driveway_entry']=='Pull-Through'
 assert reads.get('claim',cid('site-033-fit')).value['site_width']['value']==20
 assert reads.get('claim','claim-taboose-camp-inventory').value['published_spaces']==35


def test_booking_and_road_limits_survive_consumer_projection(reads):
 camp=inputs(reads,reads.resolve_intent(intent(CAMP)).context)
 assert reads.get('claim',cid('booking-window')).value['maximum_months_in_advance']==9
 assert cid('cancellation-disclosure') in camp
 assert reads.get('claim',cid('camp-stay')).value['age_62_and_over'].startswith('30-day permit')
 assert 'gap-taboose-camp-count-conflict' in camp
 th=inputs(reads,reads.resolve_intent(intent(TH)).context)
 assert cid('parking') in th and cid('clearance') in th
 assert cid('road-report') in th
 assert reads.get('claim',cid('road-report')).value['absence_is_not_open_status'] is True
 assert reads.get('claim',cid('parking')).value['capacity']=='unknown'
 assert cid('site-001-fit') not in th


def test_geometry_preserves_feature_lineage_and_no_cross_agency_snapping(reads):
 raw=(ROOT/SNAPSHOT).read_bytes();geo=json.loads(raw)
 assert geo['wayproof']['classification']=='public_domain'
 assert len(geo['features'])==5
 expected={'pass-jmt':[188],'jmt-bench-junction':[186],'bench-lake':[187,509,508],'pinchot-pass':[185],'mather-pass':[189,722,190]}
 for key,indices in expected.items():
  f=next(f for f in geo['features'] if f['properties']['feature_id']=='nps-taboose-'+key)
  source=f['properties']['source_features']
  assert [x['shapefile_record_index_zero_based'] for x in source]==indices
  assert len(f['geometry']['coordinates'])==sum(x['source_vertex_range_inclusive'][1]+1 for x in source)-len(source)+1
  c=reads.get('claim',cid(key+'-geometry'))
  assert c.value['geometry_snapshot']['sha256']==hashlib.sha256(raw).hexdigest()
 east=reads.route_geometry(ROUTE,DAY)['features'][0]['geometry']['coordinates'][-1]
 west=geo['features'][0]['geometry']['coordinates'][0]
 assert east!=west
 assert geo['features'][1]['properties']['source_features'][0]['attributes']['TRLNAME']=='Pinchot Pass South'


def test_unknown_spurs_and_conflicts_are_explicit(reads):
 path=resolve_traversal(reads,reads.entity(ROUTES['bench'][0]),reads.entity(TH),reads.entity(BENCH),DAY)
 assert BENCH in path.accessible_entity_ids
 assert 'camp-bench-lake-stock' not in path.accessible_entity_ids
 assert reads.get('claim',cid('bench-stock-camp')).value['exact_spur']=='not surveyed or modeled'
 assert reads.get('claim',cid('signed-food-order')).value['internal_exhibit_mismatch_preserved'] is True
 assert reads.get('claim',cid('bench-annual-capacity')).value['annual_capacity_stock_nights']==28
 assert reads.get('claim',cid('bench-forage')).value['maximum_grazing_stock_per_party']==20
 assert reads.get('claim',cid('stock-opening')).value['current_status']=='must recheck'
 assert reads.get('gap','gap-taboose-vehicle-food-conflict')
 assert reads.get('gap','gap-taboose-day-equipment-permit')


def test_single_followup_changeset_preserves_original_history():
 change=load_changeset(ROOT/f'changesets/v0/{CHANGE_ID}.json')
 assert change.status is ChangeSetStatus.VALIDATED
 assert {op.action.value for op in change.operations}=={'ADD','REPLACE'}
 replaced={op.record_id for op in change.operations if op.action.value=='REPLACE'}
 assert replaced=={'gap-taboose-'+s for s in ['camp-depth','camp-count-conflict','camp-water-current','access-geometry','trailhead-facilities','food-order-metadata','western-scope']}
 assert not any(op.record_type=='observation' and op.action.value=='REPLACE' for op in change.operations)
 assert len({op.path for op in change.operations})==len(change.operations)
