"""Deep campground records remain useful from planning through publication."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.operational import DeadlineStatus, OperationalState
from wayproof.read_service import CanonicalReadService
from wayproof.schema import (ActivityContext, ChangeSetStatus, PartyContext,
                             TripIntent)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


def camping_plan(reads, place, trip_date, *, as_of_date=None):
    return reads.plan(
        TripIntent(
            (place,), trip_date,
            party=PartyContext(("alice", "bob", "carol", "dave")),
            activities=ActivityContext(("camping",), {"overnight": True}),
        ),
        as_of_date=as_of_date,
    )


def test_canonical_records_and_booking_links_load():
    records = load_canonical(ROOT)

    entities = {item.entity_id: item for item in records.entities}
    assert "campground-anthony-chabot-family" in entities
    assert "campground-dumbarton-quarry" in entities
    links = {item.relationship_id: item for item in records.relationships}
    assert links["relationship-reserveamerica-110004-books-anthony-chabot"].object_id == (
        "campground-anthony-chabot-family"
    )
    assert links["relationship-reserveamerica-110750-books-dumbarton-quarry"].object_id == (
        "campground-dumbarton-quarry"
    )


def test_anthony_chabot_known_2026_closure_blocks_a_trip(reads):
    plan = camping_plan(
        reads, "Anthony Chabot Family Campground", date(2026, 10, 20),
        as_of_date=date(2026, 9, 21),
    )

    closure = next(
        item for item in plan.operational.closures
        if item.input_id == "claim-anthony-chabot-family-closure-2026:closure"
    )
    assert closure.state is OperationalState.BLOCKED
    assert plan.operational.state is OperationalState.BLOCKED


def test_dumbarton_booking_window_and_inventory_are_bounded(reads):
    plan = camping_plan(
        reads, "Dumbarton Quarry Campground", date(2027, 8, 12),
        as_of_date=date(2027, 6, 1),
    )

    deadline = next(
        item for item in plan.operational.deadlines
        if item.input_id == "claim-dumbarton-quarry-reservation-window:deadline"
    )
    assert deadline.status is DeadlineStatus.ACTIONABLE
    assert deadline.opens_on == date(2027, 5, 20)
    assert deadline.closes_on == date(2027, 8, 10)

    inventory = next(
        item for item in plan.operational.inventory
        if item.input_id == "claim-dumbarton-quarry-campground-profile:inventory"
    )
    assert inventory.state is OperationalState.NEEDS_CURRENT_CHECK


def test_alternative_campground_fees_do_not_become_a_false_total(reads):
    plan = camping_plan(
        reads, "Dumbarton Quarry Campground", date(2027, 8, 12),
        as_of_date=date(2027, 6, 1),
    )

    assert plan.operational.costs.state is OperationalState.PARTIAL
    assert plan.operational.costs.total_usd is None


def test_batch_changeset_is_validated():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260921-parks-deep-batch-01-campgrounds.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) >= 40
