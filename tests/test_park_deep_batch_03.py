"""Coyote Hills and Reinhardt Redwood group camps compose into planning."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_changeset
from wayproof.operational import OperationalState
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


def test_dairy_glen_access_and_capacity_are_planning_visible(reads):
    plan = group_plan(reads, "Dairy Glen Group Camp", date(2026, 10, 10))
    rules = {
        item.requirement.rule_id for item in plan.readiness.evaluation.requirements
    }
    inventory = {
        item.input_id: item for item in plan.operational.inventory
    }

    assert "rule-coyote-hills-dairy-glen-capacity" in rules
    assert "rule-coyote-hills-dairy-glen-hike-in" in rules
    assert inventory["claim-coyote-hills-dairy-glen-profile:inventory"].state is (
        OperationalState.NEEDS_CURRENT_CHECK
    )


def test_reinhardt_winter_closure_and_site_parking_are_bounded(reads):
    plan = group_plan(reads, "Trails End Group Camp", date(2026, 12, 12))
    rules = {
        item.requirement.rule_id for item in plan.readiness.evaluation.requirements
    }
    closure = next(
        item for item in plan.operational.closures
        if item.input_id == "claim-reinhardt-redwood-seasonal-closure-2026-2027:closure"
    )

    assert closure.state is OperationalState.BLOCKED
    assert plan.operational.state is OperationalState.BLOCKED
    assert "rule-reinhardt-redwood-trails-end-parking" in rules
    assert "rule-reinhardt-redwood-no-site-driving" in rules
    assert "rule-reinhardt-redwood-fern-dell-parking" not in rules


def test_batch_changeset_is_validated():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260922-parks-deep-batch-03-group-camps.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) >= 40

