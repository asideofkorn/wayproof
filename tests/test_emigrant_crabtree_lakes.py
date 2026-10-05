"""Bounded mapped approaches retain source disagreement and itinerary limits."""
from datetime import date
import json
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.intent import IntentResolutionState
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.requirements import Applicability
from wayproof.schema import ActivityContext, ChangeSetStatus, TripIntent
from wayproof.traversal import TraversalState, resolve_traversal
from scripts.ingest_emigrant_crabtree_lakes import CHANGE_ID, MANIFEST, TH, lake, node, route

ROOT = Path(__file__).resolve().parents[1]
DAY = date(2027, 7, 12)


@pytest.fixture(scope='module')
def reads():
    return CanonicalReadService(ROOT)


@pytest.mark.parametrize(('key', 'end', 'count', 'subtotal'), [
    ('camp', 'camp-west-approach', 3, 0), ('bear', 'bear-trail-end', 5, 1),
])
def test_bidirectional_shared_approach_has_partial_distance(reads, key, end, count, subtotal):
    rt, start, finish = reads.entity(route(key)), reads.entity(TH), reads.entity(node(end))
    outward = resolve_traversal(reads, rt, start, finish, DAY)
    inward = resolve_traversal(reads, rt, finish, start, DAY)
    assert outward.state is inward.state is TraversalState.COMPLETE
    assert len(outward.legs) == count
    assert [l.segment_id for l in inward.legs] == [l.segment_id for l in reversed(outward.legs)]
    assert outward.total_known_distance_miles == inward.total_known_distance_miles == subtotal
    assert outward.distance_complete is inward.distance_complete is False
    assert all(l.distance_miles is None and l.distance_status == 'not_printed' for l in outward.legs[:3])
    assert lake('camp') in outward.legs[2].accessible_entity_ids
    if key == 'bear':
        assert outward.legs[-1].distance_status == 'estimated'
        assert lake('bear') in outward.legs[-1].accessible_entity_ids
    else:
        assert not any(lake('bear') in l.accessible_entity_ids for l in outward.legs)


def test_competing_totals_are_not_turned_into_atomic_legs(reads):
    for key, table, guide in [('camp', 2.6, 3), ('bear', 3.9, 4)]:
        for source, expected in [('mileage-table', table), ('favorite-hikes', guide)]:
            explanation = reads.explain_claim(f'claim-emigrant-crabtree-{key}-{source}')
            assert explanation.claim.value['reported_one_way_miles'] == expected
            assert explanation.claim.predicate == 'published_approach_distance_report'
            assert explanation.sources[0].source_id == 'source-usfs-emigrant-' + source
            assert explanation.observations[0].observed_at is None
            assert explanation.observations[0].retrieved_at.date() == date(2026, 10, 5)
    milepoint = reads.get('claim', 'claim-emigrant-crabtree-pine-valley-junction-milepoint')
    assert milepoint.value['cumulative_miles_from_crabtree'] == 1.4
    schematic = reads.get('claim', 'claim-emigrant-crabtree-schematic-crabtree-junction')
    assert schematic.value['reported_miles'] == 1.3
    assert schematic.value['qualifier'] == 'estimate'
    legacy = reads.get('claim', 'claim-emigrant-crabtree-legacy-schematic')
    assert legacy.value['source_edition'] == 'unknown'
    assert legacy.value['not_atomic_distance'] is True


@pytest.mark.parametrize('key', ['camp', 'bear'])
def test_named_lake_retains_missing_exit_and_overnight_requirement(reads, key):
    intent = TripIntent((reads.entity(lake(key)).name,), DAY,
                        activities=ActivityContext(('hiking',), {'overnight': True}))
    resolved = reads.resolve_intent(intent)
    assert resolved.state is IntentResolutionState.PARTIAL
    assert resolved.route.entity_id == route(key)
    assert resolved.entry.entity_id == TH
    assert resolved.exit is None and resolved.traversal is None
    assert {i.code for i in resolved.issues} == {'exit_unknown'}
    evaluation = reads.requirements(resolved.context)
    permit = next(i for i in evaluation.rule_assessments if i.rule_id == 'rule-emigrant-overnight-wilderness-permit')
    assert permit.applicability is Applicability.APPLIES
    assert 'requirement-emigrant-overnight-wilderness-permit' in {i.requirement.requirement_id for i in evaluation.requirements}
    check = reads.pretrip_recheck(resolved.context, MANIFEST)
    assert check.state is RecheckState.REQUIRED
    items = {i.input_id: i for i in check.items}
    assert items[f'gap-emigrant-crabtree-{key}-mileage'].answerability is RecheckAnswerability.UNKNOWN
    assert items['gap-emigrant-crabtree-junction-mileage'].answerability is RecheckAnswerability.UNKNOWN
    assert 'gap-emigrant-crabtree-planning-limits' in items
    assert items[f'claim-emigrant-crabtree-{key}-conditions'].source_ids == ('source-usfs-emigrant-alerts',)
    assert f'claim-emigrant-crabtree-{key}-camping-exclusion' in items
    other = 'bear' if key == 'camp' else 'camp'
    assert f'claim-emigrant-crabtree-{other}-camping-exclusion' not in items
    assert f'claim-emigrant-crabtree-{other}-conditions' not in items
    assert f'gap-emigrant-crabtree-{other}-mileage' not in items
    foundation = reads.pretrip_recheck(resolved.context, 'result-emigrant-pretrip-recheck')
    assert 'gap-emigrant-lake-night-limit-conflict' in {i.input_id for i in foundation.items}


def test_nearby_unconnected_entry_does_not_get_selected(reads):
    resolved = reads.resolve_intent(TripIntent((reads.entity(lake('bear')).name,), DAY,
                                              entry_query='Gianelli Cabin Trailhead'))
    assert resolved.state is IntentResolutionState.AMBIGUOUS
    assert resolved.traversal is None
    assert any('not_supported' in i.code for i in resolved.issues)


def test_access_only_recheck_does_not_claim_lake_visit(reads):
    context = reads.resolve_intent(TripIntent(('Crabtree Trailhead',), DAY)).context
    assert reads.pretrip_recheck(context, MANIFEST).state is RecheckState.NOT_APPLICABLE


def test_camping_precision_and_no_invented_facilities(reads):
    for key in ('camp', 'bear'):
        assert reads.get('claim', f'claim-emigrant-crabtree-{key}-setback').value['minimum_feet'] == 100
        rec = reads.get('claim', f'claim-emigrant-crabtree-{key}-recommendation').value
        assert rec['recommended_feet'] == 200
        assert 'not asserted regulatory minimum' in rec['basis']
    assert reads.get('claim', 'claim-emigrant-crabtree-bear-horizontal-distance').value['basis'] == 'horizontal; not slope line'
    change = load_changeset(ROOT / f'changesets/v0/{CHANGE_ID}.json')
    assert change.status is ChangeSetStatus.VALIDATED
    added_ids = {op.record_id for op in change.operations if op.record_type == 'entity'}
    added_entities = [e for e in load_canonical(ROOT).entities if e.entity_id in added_ids]
    assert {e.kind for e in added_entities} == {'route', 'route_node', 'route_segment', 'waterbody'}
    assert len(added_entities) == 14
    assert not [op for op in change.operations if op.record_type == 'rule']
    assert {(op.record_type, op.record_id) for op in change.operations if op.action.value == 'REPLACE'} == {('gap', 'gap-emigrant-route-topology')}
    assert 'Gianelli, Bell Meadow' in reads.get('gap', 'gap-emigrant-route-topology').reason


def test_generated_routes_lakes_and_conflicts(generated_site):
    output, _ = generated_site
    routes = json.loads((output / 'trails/index.json').read_text())
    assert {route('camp'), route('bear')} <= {e['entity_id'] for e in routes['entities']}
    for key in ('camp', 'bear'):
        for suffix in ['index.html', 'index.json']:
            conflict = (output / f'evidence/gap/gap-emigrant-crabtree-{key}-mileage/{suffix}').read_text()
            assert f'claim-emigrant-crabtree-{key}-mileage-table' in conflict
            assert f'claim-emigrant-crabtree-{key}-favorite-hikes' in conflict
        for eid in (route(key), lake(key)):
            assert (output / f'knowledge/{eid}/index.html').exists()
            assert (output / f'knowledge/{eid}.json').exists()
        html = (output / f'knowledge/{lake(key)}/index.html').read_text()
        assert '100' in html and '200' in html and 'Leave No Trace' in html
    segment = output / 'knowledge/route-segment-emigrant-crabtree-bear-spur'
    assert 'estimated' in (segment / 'index.html').read_text()
    assert 'estimated' in segment.with_suffix('.json').read_text()
