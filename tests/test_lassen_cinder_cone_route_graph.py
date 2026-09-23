"""Official NPS/USGS evidence supports the bounded Cinder Cone summit approach."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]


def test_cinder_cone_summit_approach_traverses_both_directions():
    reads = CanonicalReadService(ROOT)
    route = reads.entity("route-cinder-cone-trail")
    trailhead = reads.entity("trailhead-cinder-cone-butte-lake")
    summit = reads.entity("peak-cinder-cone")

    outbound = resolve_traversal(reads, route, trailhead, summit, date(2027, 8, 1))
    inbound = resolve_traversal(reads, route, summit, trailhead, date(2027, 8, 1))

    assert outbound.state is TraversalState.COMPLETE
    assert outbound.distance_complete is True
    assert outbound.total_known_distance_miles == 1.58296735
    assert [item.segment_id for item in outbound.legs] == [
        "route-segment-cinder-trailhead-nobles-junction",
        "route-segment-cinder-nobles-junction-base-fork",
        "route-segment-cinder-base-fork-summit",
    ]
    assert inbound.state is TraversalState.COMPLETE
    assert inbound.total_known_distance_miles == outbound.total_known_distance_miles
    assert [item.segment_id for item in inbound.legs] == [
        item.segment_id for item in reversed(outbound.legs)
    ]


def test_official_trailhead_coordinate_matches_dataset_endpoint_without_merging_parking():
    records = load_canonical(ROOT)
    claims = {item.claim_id: item for item in records.claims}
    mapped = claims["claim-cinder-cone-official-trailhead-coordinate"].value
    first = claims["claim-route-segment-cinder-trailhead-nobles-junction"].value

    assert mapped == {
        "alternate_name": "Butte Lake West Trailhead",
        "latitude": 40.563788,
        "longitude": -121.30221,
        "map_id": "40993263-b62b-4118-94c1-983fd352e367",
        "parking_is_separate_mapped_entity": True,
    }
    assert first["start_coordinate"] == {
        "latitude": 40.5638179,
        "longitude": -121.3022149,
    }


def test_source_profiles_remain_distinct_and_rim_crater_uncertainty_is_explicit():
    records = load_canonical(ROOT)
    claims = {item.claim_id: item for item in records.claims}
    gaps = {item.gap_id: item for item in records.gaps}
    variation = claims["claim-cinder-cone-source-profile-variation"].value

    assert variation["dataset_approach_to_base_miles"] == 1.24854719
    assert variation["dataset_trailhead_to_summit_approach_miles"] == 1.58296735
    assert variation["dataset_out_and_back_miles"] == 3.1659347
    assert variation["nps_published_summit_round_trip_miles"] == 4
    assert "22 additional Cinder Cone Trail features" in gaps[
        "gap-lassen-cinder-rim-crater-circulation"
    ].reason


def test_general_lassen_gap_is_narrowed_to_remaining_route_questions():
    records = load_canonical(ROOT)
    gap = next(
        item for item in records.gaps
        if item.gap_id == "gap-lassen-specific-route-topology"
    )

    assert "route-cinder-cone-trail" not in gap.related_ids
    assert "trailhead-to-summit approaches" in gap.reason
    assert "Cinder Cone rim/crater circulation" in gap.reason


def test_cinder_cone_graph_is_one_validated_changeset():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260923-lassen-cinder-cone-route-graph.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD", "REPLACE"}
