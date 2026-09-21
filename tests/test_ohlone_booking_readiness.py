"""Ohlone overnight logistics are connected to the composed planner."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_changeset
from wayproof.operational import DeadlineStatus
from wayproof.read_service import CanonicalReadService
from wayproof.schema import (ActivityContext, ChangeSetStatus, PartyContext,
                             PlanningContext, TripIntent, TripObjective, TripStage)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def plan():
    reads = CanonicalReadService(ROOT)
    return reads.plan(
        TripIntent(
            ("Ohlone Wilderness Trail",), date(2027, 9, 5),
            entry_query="Lichen Bark Ohlone Trailhead",
            exit_query="Mission Peak Stanford Avenue Staging Area",
            party=PartyContext(("alice", "bob", "carol", "dave")),
            activities=ActivityContext(("hiking",), {"overnight": True}),
        ),
        as_of_date=date(2027, 8, 1),
    )


def test_overnight_reservation_is_a_controlling_requirement(plan):
    requirements = {
        item.requirement.rule_id: item for item in plan.readiness.evaluation.requirements
    }

    assert "rule-ohlone-overnight-reservation" in requirements
    assert requirements["rule-ohlone-overnight-reservation"].status.value == "missing"
    deadline = next(
        item for item in plan.operational.deadlines
        if item.input_id == "claim-ohlone-overnight-reservation:deadline"
    )
    assert deadline.status is DeadlineStatus.ACTIONABLE
    assert deadline.closes_on == date(2027, 9, 3)


def test_stanford_overnight_parking_depends_on_the_camping_reservation(plan):
    requirements = {
        item.requirement.rule_id: item for item in plan.readiness.evaluation.requirements
    }

    parking = requirements["rule-mission-peak-stanford-overnight-parking"]
    assert parking.status.value == "missing"
    assert "through the Ohlone Wilderness camping reservation" in (
        parking.requirement.description
    )


def test_site_capacity_filters_candidates_without_claiming_live_availability(plan):
    sites = {
        item.input_id: item for item in plan.operational.inventory
        if item.input_id.startswith("claim-reserveamerica-sunol-site-")
    }

    sunol_site_ids = {
        f"claim-reserveamerica-sunol-site-{product_id}-profile:inventory"
        for product_id in (316, 357, 375, 389, 390, 391, 393)
    }
    assert sunol_site_ids <= sites.keys()
    assert sites["claim-reserveamerica-sunol-site-389-profile:inventory"].fits_party is False
    assert sites["claim-reserveamerica-sunol-site-389-profile:inventory"].capacity == 3
    assert sites["claim-reserveamerica-sunol-site-316-profile:inventory"].fits_party is True
    assert all(item.state.value == "needs_current_check" for item in sites.values())


def test_ohlone_college_is_not_an_overnight_parking_option():
    reads = CanonicalReadService(ROOT)
    readiness = reads.readiness(PlanningContext(
        date(2027, 9, 5),
        (TripObjective("objective-1", "trail-ohlone-wilderness", "trail"),),
        (TripStage(
            "exit", 1, "exit", ("scope-mission-peak-ohlone-college-entrance",),
        ),),
        activities=ActivityContext(("hiking",), {"overnight": True}),
    ))
    requirement = next(
        item for item in readiness.evaluation.requirements
        if item.requirement.rule_id
        == "rule-mission-peak-ohlone-college-no-overnight-parking"
    )

    assert requirement.status.value == "missing"
    assert "Do not use Ohlone College" in requirement.requirement.description


def test_connection_changeset_is_validated():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260921-ohlone-booking-readiness.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 3
