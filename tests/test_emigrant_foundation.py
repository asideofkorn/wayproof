"""USFS foundation answers bounded requests without manufacturing route certainty."""
from datetime import date
import json
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.requirements import Applicability, CoverageStatus
from wayproof.schema import ActivityContext, ChangeSetStatus, PartyContext, TripIntent

ROOT = Path(__file__).resolve().parents[1]
LAND = 'wilderness-emigrant'
MANIFEST = 'result-emigrant-pretrip-recheck'


@pytest.fixture(scope='module')
def reads():
    return CanonicalReadService(ROOT)


def intent(day=date(2027, 7, 12), overnight=True, objective='Emigrant Wilderness'):
    return TripIntent((objective,), day, party=PartyContext(('alice', 'bob')),
                      activities=ActivityContext(('hiking',), {'overnight': overnight}))


def test_identity_access_and_no_fabricated_route(reads):
    records = load_canonical(ROOT)
    assert [e.entity_id for e in reads.search_entities('Emigrant Wilderness')
            if e.name == 'Emigrant Wilderness'] == [LAND]
    access = [r for r in records.relationships if r.object_id == LAND and r.predicate == 'accesses']
    assert len(access) == 10
    assert all(r.evidence_ids for r in access)
    assert {r.subject_id for r in access} >= {
        'trailhead-emigrant-crabtree', 'trailhead-emigrant-gianelli',
        'trailhead-emigrant-kennedy-meadows', 'trailhead-emigrant-sonora-pass',
    }
    resolution = reads.resolve_intent(intent())
    assert resolution.context is not None
    assert resolution.route is None and resolution.traversal is None
    assert resolution.context.stages[0].spatial_scope_ids == ('scope-emigrant-wilderness',)
    foundation = load_changeset(ROOT / 'changesets/v0/wp-20261005-emigrant-foundation.json')
    foundation_entities = {op.record_id for op in foundation.operations if op.record_type == 'entity'}
    assert not [e for e in records.entities if e.entity_id in foundation_entities and e.kind == 'route_segment']
    # Later explicit graphs must not fabricate a route for a wilderness-only request.


@pytest.mark.parametrize('day', [date(2027, 1, 12), date(2027, 7, 12)])
def test_overnight_rule_and_persisted_requirement_join(reads, day):
    context = reads.resolve_intent(intent(day)).context
    evaluation = reads.requirements(context)
    applicable = {x.rule_id for x in evaluation.rule_assessments if x.applicability is Applicability.APPLIES}
    expected = {'rule-emigrant-overnight-wilderness-permit', 'rule-emigrant-group-limit',
                'rule-emigrant-food-storage'}
    assert expected <= applicable
    assessments = {x.requirement.requirement_id: x for x in evaluation.requirements}
    for rule in expected:
        rid = rule.replace('rule-', 'requirement-', 1)
        item = assessments[rid]
        assert item.status is CoverageStatus.MISSING
        assert reads.get('requirement', rid).rule_id == rule
        assert item.requirement.coverage.participant_ids == ('alice', 'bob')
        source_claim = reads.get('rule', rule).claim_id
        assert reads.explain_claim(source_claim).sources


@pytest.mark.parametrize(('day', 'overnight', 'expected'), [
    (date(2027, 7, 12), False, Applicability.DOES_NOT_APPLY),
    (date(2026, 7, 7), True, Applicability.DOES_NOT_APPLY),
    (date(2026, 7, 8), True, Applicability.APPLIES),
    (date(2029, 6, 30), True, Applicability.APPLIES),
    (date(2029, 7, 1), True, Applicability.DOES_NOT_APPLY),
])
def test_permit_day_use_and_order_interval(reads, day, overnight, expected):
    context = reads.resolve_intent(intent(day, overnight)).context
    assessments = {x.rule_id: x for x in reads.requirements(context).rule_assessments}
    assert assessments['rule-emigrant-overnight-wilderness-permit'].applicability is expected
    # An expired order is not proof that the future trip is permit-free.
    if day > date(2029, 6, 30):
        recheck = reads.pretrip_recheck(context, MANIFEST)
        item = next(i for i in recheck.items if i.input_id == 'claim-emigrant-overnight-permit-order')
        assert item.answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK


def test_conflicts_and_dynamic_sources_reach_consumer(reads):
    context = reads.resolve_intent(intent()).context
    result = reads.pretrip_recheck(context, MANIFEST)
    assert result.state is RecheckState.REQUIRED
    items = {i.input_id: i for i in result.items}
    for suffix in ['permit-season', 'lake-night-limit', 'sanitation', 'stock-setback', 'stove-scope', 'order-date']:
        assert items[f'gap-emigrant-{suffix}-conflict'].answerability is RecheckAnswerability.UNKNOWN
    for suffix, source in [('conditions', 'conditions'), ('alerts', 'alerts'), ('access', 'access')]:
        item = items[f'claim-emigrant-{suffix}-recheck']
        assert item.answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
        assert item.source_ids == (f'source-usfs-emigrant-{source}',)
    for suffix in ['boundary-geometry', 'route-topology', 'facility-inventory', 'cross-boundary-permits']:
        assert f'gap-emigrant-{suffix}' in items
    permit = reads.get('claim', 'claim-emigrant-overnight-permit-order')
    assert permit.value['season'] == 'year-round'
    assert permit.value['exemptions']
    assert reads.get('claim', 'claim-emigrant-permit-season-access-page').value['current_conditions_season'] == 'April 15-November 15'
    assert reads.get('claim', 'claim-emigrant-lake-night-limit-order').value['basis'] == 'consecutive'
    assert reads.get('claim', 'claim-emigrant-lake-night-limit-guidance').value['basis'] == 'per trip'


def test_access_only_does_not_imply_wilderness_entry(reads):
    context = reads.resolve_intent(intent(objective='Crabtree Trailhead')).context
    assert context is not None
    assert 'scope-emigrant-wilderness' not in context.stages[0].spatial_scope_ids
    evaluation = reads.requirements(context)
    permit = next(x for x in evaluation.rule_assessments if x.rule_id == 'rule-emigrant-overnight-wilderness-permit')
    assert permit.applicability is Applicability.DOES_NOT_APPLY
    recheck = reads.pretrip_recheck(context, MANIFEST)
    items = {i.input_id: i for i in recheck.items}
    assert items['claim-emigrant-approach-recheck-crabtree'].source_ids == ('source-usfs-emigrant-alerts',)
    assert 'gap-emigrant-current-conditions' in items
    assert 'claim-emigrant-approach-recheck-gianelli' not in items
    assert 'claim-emigrant-overnight-permit-order' not in items


def test_source_precision_and_issuance_exceptions(reads):
    claim = reads.explain_claim('claim-emigrant-parking-crabtree')
    assert claim.claim.value['source_edition'] == '2012-04'
    assert claim.claim.value['current_availability'] == 'unknown'
    assert claim.observations[0].observed_at is None
    assert claim.observations[0].retrieved_at.date() == date(2026, 10, 5)
    acquisition = reads.get('claim', 'claim-emigrant-permit-acquisition').value
    assert acquisition['outside_stanislaus_self_issue_allowed'] is False
    assert 'when closed' in acquisition['sugar_pine']
    assert reads.get('claim', 'claim-emigrant-permit-fee').value['scope'] == 'Stanislaus-issued wilderness permit'
    assert reads.get('claim', 'claim-emigrant-mechanized-use').value['exception'] == 'non-motorized mobility devices may be utilized'


def test_generated_destination_and_evidence_surfaces(generated_site):
    output, _ = generated_site
    parks = json.loads((output / 'parks/index.json').read_text())
    assert LAND in {item['entity_id'] for item in parks['entities']}
    html = (output / f'knowledge/{LAND}/index.html').read_text()
    payload = (output / f'knowledge/{LAND}.json').read_text()
    for text in ['Emigrant Wilderness', 'gap-emigrant-permit-season-conflict', 'gap-emigrant-boundary-geometry']:
        assert text in html
        assert text in payload
    parking = (output / 'knowledge/trailhead-emigrant-crabtree/index.html').read_text()
    assert '2012-04' in parking and 'unknown' in parking
    conflict = output / 'evidence/gap/gap-emigrant-permit-season-conflict'
    for filename in ['index.html', 'index.json']:
        rendered = (conflict / filename).read_text()
        assert 'claim-emigrant-overnight-permit-order' in rendered
        assert 'claim-emigrant-permit-season-access-page' in rendered


def test_single_validated_changeset_and_provenance():
    change = load_changeset(ROOT / 'changesets/v0/wp-20261005-emigrant-foundation.json')
    assert change.status is ChangeSetStatus.VALIDATED
    targets = {(op.record_type, op.record_id) for op in change.operations}
    assert ('entity', LAND) in targets
    assert sum(kind == 'rule' for kind, _ in targets) == 3
    from scripts.ingest_emigrant_foundation import build_records
    from wayproof.validation import validate_records
    assert validate_records(build_records()) == []


def test_composed_plan_keeps_missing_permit_and_rechecks_visible(reads):
    from wayproof.planning import PlanningOutcomeState
    plan = reads.plan(intent(date(2027, 1, 12)), recheck_result_ids=(MANIFEST,))
    assert plan.state is PlanningOutcomeState.BLOCKED
    assert plan.resolution.traversal is None
    assert len(plan.rechecks) == 1
    assert plan.rechecks[0].state is RecheckState.REQUIRED
    assert 'gap-emigrant-permit-season-conflict' in {
        item.input_id for item in plan.rechecks[0].items
    }
