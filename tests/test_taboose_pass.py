"""Taboose consumer coverage: connected geography is not current clearance."""
from datetime import date
import hashlib
import json
from pathlib import Path
import pytest
from scripts.ingest_taboose_pass import (CHANGE_ID, MANIFEST, TH, PASS, ROUTE, SEGMENT,
    ROAD, ROAD_ROUTE, HIGHWAY, CAMP, WEST, SNAPSHOT, FEATURES, build_records, scope)
from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.requirements import Applicability, CoverageStatus
from wayproof.schema import ActivityContext, ChangeSetStatus, PartyContext, TripIntent
from wayproof.traversal import TraversalState, resolve_traversal

ROOT=Path(__file__).resolve().parents[1]
DAY=date(2026,10,15)

@pytest.fixture(scope='module')
def reads():
    return CanonicalReadService(ROOT)


def intent(objective='Taboose Pass', overnight=True, day=DAY, **kwargs):
    return TripIntent((objective,),day,party=PartyContext(('alice','bob')),
        activities=ActivityContext(('hiking',),{'overnight':overnight}),**kwargs)


def test_identity_and_bidirectional_entire_access_to_pass(reads):
    assert [e.entity_id for e in reads.search_entities('Taboose Pass') if e.name=='Taboose Pass']==[PASS]
    for rt,start,end,count in [(ROUTE,TH,PASS,1),(ROAD_ROUTE,HIGHWAY,TH,1)]:
        outward=resolve_traversal(reads,reads.entity(rt),reads.entity(start),reads.entity(end),DAY)
        inward=resolve_traversal(reads,reads.entity(rt),reads.entity(end),reads.entity(start),DAY)
        assert outward.state is inward.state is TraversalState.COMPLETE
        assert len(outward.legs)==len(inward.legs)==count
        assert inward.legs[0].end_node_id==start
        assert outward.legs[0].end_node_id==end
        if rt==ROUTE:
            assert not outward.distance_complete
            assert outward.legs[0].distance_miles is None
            assert outward.legs[0].distance_status=='conflicting_source_reports'
            assert not outward.alternate_segment_ids
            assert CAMP not in outward.accessible_entity_ids
        else:
            assert outward.distance_complete
            assert outward.total_known_distance_miles==6
            assert outward.legs[0].distance_status=='approximate'
            assert CAMP in outward.accessible_entity_ids


def test_named_plan_keeps_exit_unknown_and_rules_executable(reads):
    resolved=reads.resolve_intent(intent())
    assert resolved.route.entity_id==ROUTE and resolved.entry.entity_id==TH
    assert resolved.exit is None and resolved.traversal is None
    assert {i.code for i in resolved.issues}=={'exit_unknown'}
    evaluation=reads.requirements(resolved.context)
    expected={'rule-taboose-'+k for k in ['overnight-permit','food-storage','group-limit','campfire-restriction','camping-setback']}
    assert expected <= {a.rule_id for a in evaluation.rule_assessments if a.applicability is Applicability.APPLIES}
    items={i.requirement.requirement_id:i for i in evaluation.requirements}
    for rid in expected:
        persisted=reads.get('requirement',rid.replace('rule-','requirement-',1))
        generated=items[persisted.requirement_id]
        assert generated.requirement.rule_id==rid
        assert generated.status is CoverageStatus.MISSING
        assert reads.get('rule',rid).claim_id
    plan=reads.plan(intent(),recheck_result_ids=(MANIFEST,))
    assert plan.rechecks[0].state is RecheckState.REQUIRED
    assert plan.readiness is not None


def test_day_hike_does_not_get_unconditional_permit_clearance(reads):
    ctx=reads.resolve_intent(intent(overnight=False)).context
    assessments={a.rule_id:a for a in reads.requirements(ctx).rule_assessments}
    assert assessments['rule-taboose-overnight-permit'].applicability is Applicability.DOES_NOT_APPLY
    assert assessments['rule-taboose-camping-setback'].applicability is Applicability.DOES_NOT_APPLY
    check=reads.pretrip_recheck(ctx,MANIFEST)
    assert 'gap-taboose-day-equipment-permit' in {i.input_id for i in check.items}
    assert reads.get('claim','claim-taboose-day-permit').value['required'] is False
    assert reads.get('claim','claim-taboose-equipment-permit').value['listed_items']==['tent','sleeping bag','bear canister','camp stove']
    # Fee source remains a scoped schedule/recheck, not an unconditional day fee.
    dayplan=reads.plan(intent(overnight=False),recheck_result_ids=(MANIFEST,))
    assert not any(i.input_id.startswith('claim-taboose-permit-fees') for i in dayplan.planning_inputs.inputs)


def test_rule_expiry_does_not_remove_current_check(reads):
    ctx=reads.resolve_intent(intent(day=date(2027,7,12))).context
    applies={a.rule_id:a.applicability for a in reads.requirements(ctx).rule_assessments}
    assert applies['rule-taboose-overnight-permit'] is Applicability.APPLIES
    assert applies['rule-taboose-campfire-restriction'] is Applicability.DOES_NOT_APPLY
    items={i.input_id:i for i in reads.pretrip_recheck(ctx,MANIFEST).items}
    assert items['claim-taboose-campfire-restriction'].answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    assert 'gap-taboose-fire-current' in items


def test_rechecks_are_scoped_and_dated(reads):
    trail={i.input_id:i for i in reads.pretrip_recheck(reads.resolve_intent(intent()).context,MANIFEST).items}
    assert 'gap-taboose-mileage' in trail and 'gap-taboose-water-crossings' in trail
    assert 'gap-taboose-day-equipment-permit' in trail
    assert trail['claim-taboose-trail-condition-20260826'].answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    assert trail['claim-taboose-trail-condition-20260826'].source_ids==('source-nps-seki-trail-conditions',)
    assert 'claim-taboose-west-pets' not in trail
    assert 'claim-taboose-camp-fees' not in trail
    assert 'claim-taboose-road-recheck' in trail
    campground={i.input_id:i for i in reads.pretrip_recheck(reads.resolve_intent(intent('Taboose Creek Campground')).context,MANIFEST).items}
    assert 'gap-taboose-camp-water-current' in campground
    assert 'gap-taboose-camp-count-conflict' in campground
    assert 'claim-taboose-overnight-permit' not in campground
    west={i.input_id:i for i in reads.pretrip_recheck(reads.resolve_intent(intent('Taboose Pass western continuation in Kings Canyon')).context,MANIFEST).items}
    assert 'claim-taboose-west-pets' in west and 'claim-taboose-west-fire' in west
    assert 'claim-taboose-day-permit' not in west
    assert reads.pretrip_recheck(reads.resolve_intent(intent('Emigrant Wilderness')).context,MANIFEST).state is RecheckState.NOT_APPLICABLE
    condition=reads.explain_claim('claim-taboose-trail-condition-20260826')
    assert condition.observations[0].observed_at.date()==date(2026,8,26)
    assert condition.observations[0].retrieved_at.date()==date(2026,10,6)
    notice=reads.explain_claim('claim-taboose-camp-water-notice')
    assert notice.claim.temporal_scope.starts_on==date(2026,5,1)
    assert notice.observations[0].observed_at.date()==date(2026,7,30)
    assert notice.claim.value['not_a_positive_contamination_test'] is True


def test_east_and_west_general_travel_rechecks_preserve_jurisdiction(reads):
    east = {i.input_id: i for i in reads.pretrip_recheck(
        reads.resolve_intent(intent()).context, MANIFEST).items}
    west = {i.input_id: i for i in reads.pretrip_recheck(
        reads.resolve_intent(intent('Taboose Pass western continuation in Kings Canyon')).context,
        MANIFEST).items}
    pet = reads.explain_claim('claim-taboose-pets')
    assert pet.claim.spatial_scope_ids == (scope(ROUTE),)
    assert pet.claim.value == {
        'national_forest': 'allowed under leash or responsive voice control; no wildlife harassment',
        'waste_setback_feet': 100,
    }
    assert 'pets prohibited' not in pet.observations[0].content
    assert 'claim-taboose-pets' in east and 'claim-taboose-pets' not in west
    keys = ('pets', 'wheeled-equipment', 'motorized-equipment', 'weapon-discharge',
            'weapon-possession', 'overnight-permit', 'trail-shortcuts', 'trail-markers',
            'trash', 'drift-gates')
    for key in keys:
        cid = 'claim-taboose-west-' + key
        assert cid in west and cid not in east
        assert reads.get('claim', cid).spatial_scope_ids == (scope(WEST),)
        assert west[cid].source_ids == ('source-taboose-nps-rules',)
        assert west[cid].answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    gap = 'gap-taboose-west-weapons-interpretation'
    assert gap in west and gap not in east
    value = reads.get('claim', 'claim-taboose-west-weapon-possession').value
    assert value['not_a_blanket_firearm_possession_ban'] is True
    assert value['firearm_qualification'] == 'firearm possession is subject to state regulations'
    assert 'bear spray' in value['published_general_statement']
    assert reads.get('claim', 'claim-taboose-west-weapon-discharge').value['distinct_from_possession'] is True


def test_source_precision_conflicts_and_facilities(reads):
    assert reads.get('claim','claim-taboose-guide-distance').value['qualifier']=='approximate'
    assert reads.get('claim','claim-taboose-guide-distance').value['reported_one_way_miles']==6.5
    assert reads.get('claim','claim-taboose-guide-jmt-distance').value['reported_one_way_miles']==8.75
    quota=reads.get('claim','claim-taboose-quota').value
    assert (quota['persons_per_entry_day'],quota['six_month_spaces'],quota['two_week_spaces'])==(10,6,4)
    assert reads.get('claim','claim-taboose-camp-inventory').value['published_spaces']==35
    assert reads.get('claim','claim-taboose-camp-booking-inventory').value['listed_sites']==36
    assert reads.get('claim','claim-taboose-trailhead-lockers').value['bear_lockers'] is False
    relations=reads.relationships_for(CAMP)
    assert any(r.predicate=='provides_access_to' and r.object_id=='facility-taboose-camp-toilets' for r in relations)
    assert not any(r.subject_id==TH and r.object_id==CAMP and r.predicate=='part_of' for r in relations)
    assert reads.managed_land_geometry('wilderness-john-muir')
    assert reads.managed_land_geometry('park-sequoia-kings-canyon')


def test_unconnected_campground_cannot_be_hiking_entry(reads):
    resolved=reads.resolve_intent(intent(entry_query='Taboose Creek Campground'))
    assert resolved.context is None and resolved.traversal is None
    assert 'entry_not_supported' in {i.code for i in resolved.issues}


def test_geometry_keeps_official_vertices_and_lineage(reads):
    payload=json.loads((ROOT/SNAPSHOT).read_text())
    props=payload['features'][0]['properties']
    assert len(payload['features'][0]['geometry']['coordinates'])==sum(x[1] for x in FEATURES)-3
    assert [f['attributes']['objectid'] for f in props['source_features']]==[x[0] for x in FEATURES]
    assert payload['wayproof']['classification']=='public_domain'
    claim=reads.get('claim','claim-taboose-trail-geometry')
    assert claim.value['geometry_snapshot']['sha256']==hashlib.sha256((ROOT/SNAPSHOT).read_bytes()).hexdigest()
    output=reads.route_geometry(ROUTE,DAY)
    assert output['wayproof']['navigation_grade'] is False
    assert output['wayproof']['distance_complete'] is False
    assert len(output['features'])==1
    assert output['features'][0]['geometry']==payload['features'][0]['geometry']
    assert reads.route_geometry(ROAD_ROUTE,DAY) is None
    assert reads.get('claim','claim-taboose-pass-display-point').value['longitude']==payload['features'][0]['geometry']['coordinates'][-1][0]


def test_one_validated_changeset_and_reproducible_builder():
    change=load_changeset(ROOT/f'changesets/v0/{CHANGE_ID}.json')
    assert change.status is ChangeSetStatus.VALIDATED
    assert {op.action.value for op in change.operations}=={'ADD'}
    assert len({(op.record_type,op.record_id) for op in change.operations})==len(change.operations)
    base=load_canonical(ROOT)
    introduced={(op.record_type,op.record_id) for op in change.operations}
    from wayproof.canonical_storage import RECORD_SPECS
    for kind,(collection,identifier,_) in RECORD_SPECS.items():
        setattr(base,collection,[r for r in getattr(base,collection) if (kind,getattr(r,identifier)) not in introduced])
    data=(ROOT/SNAPSHOT).read_bytes()
    rebuilt=build_records(base,json.loads(data),hashlib.sha256(data).hexdigest())
    from wayproof.validation import validate_records
    assert validate_records(rebuilt,existing=base)==[]
    assert len(rebuilt.claims)==sum(op.record_type=='claim' for op in change.operations)


def test_generated_directories_map_and_evidence(generated_site):
    output,_=generated_site
    trails=json.loads((output/'trails/index.json').read_text())
    assert {ROUTE,ROAD_ROUTE}<={e['entity_id'] for e in trails['entities']}
    camping=json.loads((output/'camping/index.json').read_text())
    assert CAMP in {e['entity_id'] for e in camping['entities']}
    for eid in (PASS,TH,ROUTE,ROAD_ROUTE,CAMP,WEST):
        assert (output/f'knowledge/{eid}/index.html').exists()
        assert (output/f'knowledge/{eid}.json').exists()
    geo=json.loads((output/f'geometry/routes/{ROUTE}.geojson').read_text())
    assert len(geo['features'])==1 and geo['wayproof']['distance_complete'] is False
    html=(output/f'knowledge/{ROUTE}/index.html').read_text()
    assert 'id="route-map"' in html and 'gap-taboose-mileage' in html
    payload=(output/f'knowledge/{CAMP}.json').read_text()
    assert 'gap-taboose-camp-count-conflict' in payload
    for key in ('day-equipment-permit','camp-water-current','vehicle-food-conflict','food-order-metadata'):
        for filename in ('index.html','index.json'):
            assert (output/f'evidence/gap/gap-taboose-{key}/{filename}').exists()
    explorer=json.loads((output/'map/features.geojson').read_text())
    points={f['properties'].get('entity_id') for f in explorer['features'] if f['geometry']['type']=='Point'}
    assert {TH,PASS}<=points


def test_generated_west_restrictions_preserve_qualifications(generated_site):
    output, _ = generated_site
    detail = json.loads((output/f'knowledge/{WEST}.json').read_text())
    for key in ('pets', 'wheeled-equipment', 'motorized-equipment', 'weapon-discharge',
                'weapon-possession', 'overnight-permit', 'trail-shortcuts', 'trail-markers',
                'trash', 'drift-gates'):
        cid = 'claim-taboose-west-' + key
        assert cid in json.dumps(detail)
        assert cid in (output/f'knowledge/{WEST}/index.html').read_text()
        for suffix in ('index.html', 'index.json'):
            evidence = (output/f'evidence/claim/{cid}/{suffix}').read_text()
            assert cid in evidence
            if key == 'weapon-possession':
                assert 'bear spray' in evidence
                assert 'firearm possession is subject to state regulations' in evidence
    for suffix in ('index.html', 'index.json'):
        assert (output/f'evidence/gap/gap-taboose-west-weapons-interpretation/{suffix}').exists()
    east = (output/f'evidence/claim/claim-taboose-pets/index.json').read_text()
    assert 'park_wilderness' not in east and 'pets prohibited' not in east
