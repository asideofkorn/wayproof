"""Planning input projection is explicit, contextual, and provenance-backed."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.planning_inputs import (PlanningInputAnswerability,
                                      PlanningInputCategory)
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ActivityContext, TripIntent


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


def del_valle(reads, *activities):
    return reads.plan(TripIntent(
        ("Del Valle Regional Park",), date(2026, 9, 21),
        activities=ActivityContext(activities),
    ))


def by_id(plan):
    return {item.input_id: item for item in plan.planning_inputs.inputs}


def test_hiking_does_not_inherit_swimming_boating_or_camping_costs(reads):
    inputs = by_id(del_valle(reads, "hiking"))

    assert "claim-del-valle-ebrpd-entry-fees:cost" in inputs
    assert "claim-ebrpd-swimming-del-valle-parking-fee:cost" not in inputs
    assert "claim-del-valle-ebrpd-boating-fees:cost" not in inputs
    assert "claim-del-valle-campground-inventory:inventory" not in inputs


def test_missing_activity_keeps_conditional_inputs_unknown(reads):
    inputs = by_id(del_valle(reads))
    swimming = inputs["claim-ebrpd-swimming-del-valle-parking-fee:cost"]

    assert swimming.answerability is PlanningInputAnswerability.UNKNOWN
    assert "activity context" in swimming.explanation


def test_camping_projects_inventory_and_its_explicit_conflict(reads):
    inputs = by_id(del_valle(reads, "camping"))

    inventory = inputs["claim-del-valle-campground-inventory:inventory"]
    conflict = inputs["gap-del-valle-family-site-inventory-conflict"]
    assert inventory.answerability is PlanningInputAnswerability.ANSWERED
    assert inventory.evidence_ids
    assert conflict.category is PlanningInputCategory.CONFLICT
    assert conflict.answerability is PlanningInputAnswerability.CONFLICTING
    assert set(conflict.related_ids) == {
        "claim-del-valle-campground-inventory",
        "claim-reserveamerica-del-valle-campsites-inventory",
    }


def test_open_ended_operational_claims_require_a_current_check(reads):
    inputs = by_id(del_valle(reads, "hiking"))

    closure = inputs["claim-del-valle-seasonal-closures-2026:closure"]
    assert closure.category is PlanningInputCategory.CLOSURE
    assert closure.answerability is PlanningInputAnswerability.NEEDS_CURRENT_CHECK


def test_unregistered_predicates_are_not_heuristically_classified(reads):
    inputs = by_id(del_valle(reads, "hiking"))

    assert all(item.predicate != "seasonal_gate_hours" for item in inputs.values())
    assert all(item.predicate != "quiet_hours" for item in inputs.values())
