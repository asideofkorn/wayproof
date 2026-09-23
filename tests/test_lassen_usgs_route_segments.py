"""Official USGS/NPS segments make two Lassen summit routes distance-complete."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus, TripIntent
from wayproof.intent import IntentResolutionState
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("route_id", "entry_id", "exit_id", "segment_id", "distance"),
    (
        (
            "route-lassen-peak-trail",
            "trailhead-lassen-peak",
            "peak-lassen-peak",
            "route-segment-lassen-peak-trailhead-summit",
            2.51712045,
        ),
        (
            "route-brokeoff-mountain-trail",
            "trailhead-brokeoff-mountain",
            "peak-brokeoff-mountain",
            "route-segment-brokeoff-trailhead-summit",
            3.60834485,
        ),
    ),
)
def test_unbranched_summit_routes_traverse_both_directions_with_source_distance(
    route_id, entry_id, exit_id, segment_id, distance
):
    reads = CanonicalReadService(ROOT)
    route = reads.entity(route_id)
    entry = reads.entity(entry_id)
    exit_entity = reads.entity(exit_id)

    outbound = resolve_traversal(reads, route, entry, exit_entity, date(2027, 8, 1))
    inbound = resolve_traversal(reads, route, exit_entity, entry, date(2027, 8, 1))

    assert outbound.state is TraversalState.COMPLETE
    assert outbound.distance_complete is True
    assert outbound.total_known_distance_miles == distance
    assert [(leg.segment_id, leg.distance_status) for leg in outbound.legs] == [
        (segment_id, "known")
    ]
    assert inbound.state is TraversalState.COMPLETE
    assert inbound.total_known_distance_miles == distance
    assert inbound.legs[0].start_node_id == exit_id
    assert inbound.legs[0].end_node_id == entry_id


def test_dataset_provenance_and_precision_are_preserved():
    records = load_canonical(ROOT)
    claims = {item.claim_id: item for item in records.claims}
    observations = {item.observation_id: item for item in records.observations}

    claim = claims["claim-route-segment-lassen-peak-trailhead-summit"]
    assert claim.predicate == "official_dataset_route_segment"
    assert claim.value["dataset_field"] == "lengthmiles"
    assert claim.value["dataset_feature_id"] == (
        "156823fe-597b-42f7-85ad-d3d73e6754a7"
    )
    assert claim.value["distance_miles"] == 2.51712045
    assert claim.value["operational_status_requires_current_check"] is True
    observation = observations[
        "observation-usgs-topo-vector-lassen-trails-20250729-20260923"
    ]
    assert "temporal changes may have occurred" in observation.content


def test_lassen_peak_intent_keeps_trip_exit_unknown_without_inventing_return():
    result = CanonicalReadService(ROOT).resolve_intent(
        TripIntent(("Lassen Peak",), date(2027, 8, 12))
    )

    assert result.state is IntentResolutionState.PARTIAL
    assert result.entry.entity_id == "trailhead-lassen-peak"
    assert result.exit is None
    assert {item.code for item in result.issues} == {"exit_unknown"}


def test_remaining_gap_excludes_completed_summit_routes():
    records = load_canonical(ROOT)
    gap = next(
        item for item in records.gaps
        if item.gap_id == "gap-lassen-specific-route-topology"
    )

    assert "route-lassen-peak-trail" not in gap.related_ids
    assert "route-brokeoff-mountain-trail" not in gap.related_ids
    assert "route-cinder-cone-trail" not in gap.related_ids
    cinder_gap = next(
        item for item in records.gaps
        if item.gap_id == "gap-lassen-cinder-rim-crater-circulation"
    )
    assert "route-cinder-cone-trail" in cinder_gap.related_ids
    assert "complete, bidirectional, distance-bearing" in gap.reason


def test_usgs_route_segments_are_one_validated_changeset():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260923-lassen-usgs-route-segments.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD", "REPLACE"}
