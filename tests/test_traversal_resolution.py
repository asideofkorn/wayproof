"""Traversal projection from canonical route-segment topology."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.read_service import CanonicalReadService
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


def test_ohlone_mainline_resolves_as_ordered_atomic_legs(reads):
    plan = resolve_traversal(
        reads,
        reads.entity("trail-ohlone-wilderness"),
        reads.entity("staging-mission-peak-stanford-avenue"),
        reads.entity("trailhead-ohlone-lichen-bark"),
        date(2027, 9, 5),
    )

    assert plan.state is TraversalState.COMPLETE
    assert len(plan.legs) == 52
    assert plan.legs[0].segment_id == "route-leg-ohlone-mainline-001"
    assert plan.legs[-1].segment_id == "route-leg-ohlone-mainline-050"
    assert [item.sequence for item in plan.legs] == list(range(1, 53))
    assert plan.total_known_distance_miles == pytest.approx(26.90)
    assert plan.distance_complete is False
    assert [item.distance_status for item in plan.legs].count("not_printed") == 2


def test_mainline_access_and_alternates_remain_distinct(reads):
    plan = resolve_traversal(
        reads,
        reads.entity("trail-ohlone-wilderness"),
        reads.entity("staging-mission-peak-stanford-avenue"),
        reads.entity("trailhead-ohlone-lichen-bark"),
        date(2027, 9, 5),
    )

    assert plan.accessible_entity_ids == ("peak-rose",)
    assert set(plan.alternate_segment_ids) == {
        "route-segment-ohlone-ot26-doe-canyon",
        "route-segment-ohlone-ot27-ot29-maggies",
        "route-segment-ohlone-ot33-ot35-stewarts",
    }
    alternate_access = {
        entity_id
        for leg in plan.alternate_legs
        for entity_id in leg.accessible_entity_ids
    }
    assert {
        "water-ohlone-doe-camp", "water-ohlone-maggies-half-acre",
        "facility-ohlone-stewarts-restroom", "water-ohlone-stewarts-camp",
    }.issubset(alternate_access)


def test_resolved_leg_scopes_feed_requirement_coverage(reads):
    from wayproof.schema import TripIntent

    result = reads.resolve_intent(TripIntent(
        ("Ohlone Wilderness Trail",), date(2027, 9, 5),
        entry_query="Mission Peak Stanford Avenue Staging Area",
        exit_query="Lichen Bark Ohlone Trailhead",
    ))
    evaluation = reads.requirements(result.context)
    restriction = next(
        item.requirement for item in evaluation.requirements
        if item.requirement.rule_id == "rule-ohlone-map-no-restricted-access"
    )

    assert "route-leg-ohlone-mainline-001" in restriction.coverage.stage_ids
    assert "route-leg-ohlone-mainline-050" in restriction.coverage.stage_ids
    assert "route" not in restriction.coverage.stage_ids


def test_route_without_segment_topology_fails_closed(reads):
    plan = resolve_traversal(
        reads,
        reads.entity("route-mount-whitney-classic"),
        reads.entity("trailhead-whitney-portal"),
        reads.entity("trailhead-whitney-portal"),
        date(2027, 8, 12),
    )

    assert plan.state is TraversalState.UNAVAILABLE
    assert plan.legs == ()
    assert plan.total_known_distance_miles == 0.0


def test_reversed_ohlone_endpoints_are_not_assumed_bidirectional(reads):
    plan = resolve_traversal(
        reads,
        reads.entity("trail-ohlone-wilderness"),
        reads.entity("trailhead-ohlone-lichen-bark"),
        reads.entity("staging-mission-peak-stanford-avenue"),
        date(2027, 9, 5),
    )

    assert plan.state is TraversalState.DISCONNECTED
    assert plan.legs == ()
