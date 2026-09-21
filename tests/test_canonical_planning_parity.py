"""Executable checkpoints for the canonical/legacy parity decision."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.intent import IntentResolutionState
from wayproof.operational import OperationalState
from wayproof.planning import PlanningOutcomeState
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ActivityContext, PartyContext, TripIntent
from wayproof.traversal import TraversalState


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


def _ohlone(entry: str, exit_: str) -> TripIntent:
    return TripIntent(
        ("Ohlone Wilderness Trail",), date(2027, 9, 5),
        entry_query=entry, exit_query=exit_,
        party=PartyContext(("alice", "bob", "carol", "dave")),
        activities=ActivityContext(("hiking",), {"overnight": True}),
    )


def test_route_objective_and_distinct_endpoints_are_canonical(reads):
    plan = reads.plan(_ohlone(
        "Mission Peak Stanford Avenue Staging Area",
        "Lichen Bark Ohlone Trailhead",
    ))

    assert plan.resolution.state is IntentResolutionState.RESOLVED
    assert plan.resolution.context.objectives[0].entity_id == "trail-ohlone-wilderness"
    assert plan.resolution.entry.entity_id == "staging-mission-peak-stanford-avenue"
    assert plan.resolution.exit.entity_id == "trailhead-ohlone-lichen-bark"
    assert plan.resolution.traversal.state is TraversalState.COMPLETE
    assert plan.resolution.traversal.total_known_distance_miles == pytest.approx(26.90)
    assert plan.resolution.traversal.distance_complete is False


def test_completed_ohlone_trip_direction_remains_an_explicit_parity_gap(reads):
    plan = reads.plan(_ohlone(
        "Lichen Bark Ohlone Trailhead",
        "Mission Peak Stanford Avenue Staging Area",
    ))

    assert plan.state is PlanningOutcomeState.PARTIAL
    assert plan.resolution.traversal.state is TraversalState.DISCONNECTED
    assert {issue.code for issue in plan.resolution.issues} == {
        "traversal_disconnected",
    }


def test_cost_alternatives_do_not_become_a_false_ohlone_total(reads):
    plan = reads.plan(
        _ohlone(
            "Mission Peak Stanford Avenue Staging Area",
            "Lichen Bark Ohlone Trailhead",
        ),
        as_of_date=date(2027, 8, 1),
    )

    assert plan.operational.state is OperationalState.PARTIAL
    assert plan.operational.costs.total_usd is None
    assert plan.operational.costs.unresolved_input_ids == (
        "claim-del-valle-ebrpd-entry-fees:cost",
    )


def test_route_specific_whitney_requirement_is_preserved_without_fake_topology(reads):
    plan = reads.plan(TripIntent(
        ("Mount Whitney",), date(2027, 8, 12),
        route_query="Mount Whitney Trail",
        entry_query="Whitney Portal", exit_query="Whitney Portal",
        party=PartyContext(("alice", "bob")),
        activities=ActivityContext(("hiking",), {"overnight": True}),
    ))

    assert plan.state is PlanningOutcomeState.PARTIAL
    assert plan.resolution.traversal.state is TraversalState.UNAVAILABLE
    assert [item.requirement.requirement_id
            for item in plan.readiness.evaluation.requirements] == [
        "requirement-whitney-classic-overnight-permit",
    ]
