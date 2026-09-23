"""Bumpass Hell preserves the visitor approach without flattening basin branches."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]


def by_id(records, collection, field):
    return {getattr(item, field): item for item in getattr(records, collection)}


def test_bumpass_parking_to_basin_entry_traverses_both_directions():
    reads = CanonicalReadService(ROOT)
    route = reads.entity("route-bumpass-hell-trail")
    trailhead = reads.entity("trailhead-bumpass-hell")
    basin = reads.entity("hydrothermal-area-bumpass-hell")

    outbound = resolve_traversal(reads, route, trailhead, basin, date(2027, 8, 1))
    inbound = resolve_traversal(reads, route, basin, trailhead, date(2027, 8, 1))

    assert outbound.state is TraversalState.COMPLETE
    assert outbound.distance_complete is True
    assert outbound.total_known_distance_miles == 1.29564925
    assert [item.segment_id for item in outbound.legs] == [
        "route-segment-bumpass-trailhead-basin-approach",
        "route-segment-bumpass-basin-approach-entry",
    ]
    assert [item.segment_id for item in inbound.legs] == [
        item.segment_id for item in reversed(outbound.legs)
    ]


def test_bumpass_source_features_preserve_ids_endpoints_and_precision():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")

    first = claims["claim-route-segment-bumpass-trailhead-basin-approach"]
    second = claims["claim-route-segment-bumpass-basin-approach-entry"]
    assert first.value["dataset_feature_id"] == (
        "d0d63ec3-c99c-41e0-a353-50ac64f4fff8"
    )
    assert first.value["distance_miles"] == 1.26580720
    assert first.value["end_coordinate"] == second.value["start_coordinate"]
    assert second.value["distance_miles"] == 0.02984205
    assert second.value["operational_status_requires_current_check"] is True


def test_boardwalk_alternate_and_profile_variations_remain_visible_gaps():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")
    gaps = by_id(records, "gaps", "gap_id")

    variations = claims["claim-bumpass-hell-source-profile-variations"].value
    assert variations["southwest_entrance_distance_miles"] == [7, 8]
    assert variations["duration_minutes"] == [90, 120]
    assert variations["descent_feet"] == [200, 300]
    circulation = gaps["gap-lassen-bumpass-full-basin-circulation"]
    assert "1.29564925-mile approach" in circulation.reason
    assert "Kings Creek alternative" in circulation.reason
    conflicts = gaps["gap-lassen-bumpass-source-profile-conflicts"]
    assert "internally different values" in conflicts.reason


def test_global_gap_moves_bumpass_to_its_narrower_route_specific_gaps():
    records = load_canonical(ROOT)
    gap = by_id(records, "gaps", "gap_id")["gap-lassen-specific-route-topology"]

    assert "route-bumpass-hell-trail" not in gap.related_ids
    assert "connected distance-bearing" in gap.reason
    assert "full Bumpass basin circulation" in gap.reason


def test_bumpass_route_graph_is_one_validated_changeset():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260923-lassen-bumpass-route-graph.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD", "REPLACE"}
