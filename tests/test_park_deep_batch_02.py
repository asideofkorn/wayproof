"""Group-camp evidence remains bounded and useful through planning."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_changeset
from wayproof.operational import OperationalState
from wayproof.planning_inputs import PlanningInputAnswerability
from wayproof.read_service import CanonicalReadService
from wayproof.schema import (ActivityContext, ChangeSetStatus, PartyContext,
                             TripIntent)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


def group_plan(reads, place, trip_date):
    return reads.plan(TripIntent(
        (place,), trip_date,
        party=PartyContext(tuple(f"person-{number}" for number in range(20))),
        activities=ActivityContext(("camping",), {"overnight": True}),
    ), as_of_date=date(2026, 9, 22))


def test_garin_projects_inventory_and_preserves_minimum_party_conflict(reads):
    plan = group_plan(reads, "Arroyo Flats Group Camp", date(2026, 10, 10))
    inputs = {item.input_id: item for item in plan.planning_inputs.inputs}

    assert inputs["claim-garin-arroyo-flats-profile:inventory"].evidence_ids
    assert inputs["claim-garin-arroyo-flats-reserveamerica-profile:inventory"].answerability is (
        PlanningInputAnswerability.ANSWERED
    )
    assert inputs["gap-garin-arroyo-flats-minimum-party"].answerability is (
        PlanningInputAnswerability.CONFLICTING
    )
    assert all(item.state is OperationalState.NEEDS_CURRENT_CHECK
               for item in plan.operational.inventory)


def test_las_trampas_winter_closure_blocks_and_water_rule_is_visible(reads):
    plan = group_plan(
        reads, "Las Trampas Corral Area Group Camp", date(2026, 12, 12),
    )
    closure = next(
        item for item in plan.operational.closures
        if item.input_id == "claim-las-trampas-seasonal-closure-2026-2027:closure"
    )
    rules = {
        item.requirement.rule_id for item in plan.readiness.evaluation.requirements
    }

    assert closure.state is OperationalState.BLOCKED
    assert plan.operational.state is OperationalState.BLOCKED
    assert "rule-las-trampas-corral-bring-water" in rules
    assert "rule-las-trampas-corral-fire-use" in rules


def test_batch_changeset_is_validated():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260922-parks-deep-batch-02-group-camps.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) >= 30

