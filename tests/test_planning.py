"""Integrated planning keeps resolution and readiness answerability distinct."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.planning import PlanningOutcomeState
from wayproof.readiness import ReadinessState
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckState
from wayproof.schema import (ActivityContext, Coverage, Fulfillment,
                             PartyContext, TripIntent)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


def whitney_intent():
    return TripIntent(
        ("Mount Whitney",), date(2027, 8, 12),
        route_query="Mount Whitney Trail",
        entry_query="Whitney Portal", exit_query="Whitney Portal",
        party=PartyContext(("alice", "bob")),
        activities=ActivityContext(("hiking",), {"overnight": True}),
    )


def test_ambiguous_intent_stops_before_readiness(reads):
    plan = reads.plan(TripIntent(("Mount Whitney",), date(2027, 8, 12)))

    assert plan.state is PlanningOutcomeState.AMBIGUOUS
    assert plan.readiness is None
    assert plan.rechecks == ()


def test_claim_backed_route_scope_drives_constraint_evaluation(reads):
    plan = reads.plan(whitney_intent())

    assert plan.state is PlanningOutcomeState.PARTIAL
    assert plan.resolution.context.stages[1].spatial_scope_ids == (
        "scope-route-whitney-classic",
    )
    assert plan.readiness.state is ReadinessState.BLOCKED
    assert [item.requirement.requirement_id
            for item in plan.readiness.evaluation.requirements] == [
        "requirement-whitney-classic-overnight-permit",
    ]


def test_fulfillment_changes_readiness_but_not_missing_topology(reads):
    fulfillment = Fulfillment(
        "whitney-party-permit",
        "requirement-whitney-classic-overnight-permit",
        "permit", ("evidence-whitney-overnight-scope",),
        Coverage(
            participant_ids=("alice", "bob"), stage_ids=("route",),
            starts_on=date(2027, 8, 12), ends_on=date(2027, 8, 12),
        ),
    )
    plan = reads.plan(whitney_intent(), (fulfillment,))

    assert plan.readiness.state is ReadinessState.READY
    assert plan.state is PlanningOutcomeState.PARTIAL
    assert {item.code for item in plan.resolution.issues} == {
        "traversal_unavailable",
    }


def test_named_rechecks_are_evaluated_in_the_same_context(reads):
    plan = reads.plan(
        TripIntent(("Del Valle Regional Park",), date(2026, 9, 21)),
        recheck_result_ids=("result-del-valle-pretrip-recheck",),
    )

    assert len(plan.rechecks) == 1
    assert plan.rechecks[0].state is RecheckState.REQUIRED
    assert any(item.source_ids for item in plan.rechecks[0].items)
