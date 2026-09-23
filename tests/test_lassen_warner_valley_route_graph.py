"""Warner Valley publishes useful topology without invented atomic mileage."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]


def by_id(records, collection, field):
    return {getattr(item, field): item for item in getattr(records, collection)}


def test_warner_valley_preserves_printed_milepoints_without_derived_legs():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")

    assert claims[
        "claim-lassen-devils-first-intersection-milepoint"
    ].value == {"cumulative_miles_from_trailhead": 0.4}
    assert claims[
        "claim-lassen-devils-dream-junction-milepoint"
    ].value == {"cumulative_miles_from_trailhead": 0.6}
    assert claims[
        "claim-lassen-terminal-pct-rejoin-milepoint"
    ].value == {"cumulative_miles_from_trailhead": 2.5}
    assert claims[
        "claim-lassen-terminal-pct-divergence-milepoint"
    ].value == {
        "distance_feet_from_previous_junction": 25,
        "qualifier": "about",
    }
    connector = claims[
        "claim-route-segment-lassen-warner-start-first-y"
    ]
    assert connector.predicate == "described_route_connector"
    connector = connector.value
    assert connector["distance_miles"] is None
    assert connector["distance_status"] == "not_printed"


def test_devils_kitchen_traverses_shared_warner_network_both_directions():
    reads = CanonicalReadService(ROOT)
    route = reads.entity("route-devils-kitchen-trail")
    trailhead = reads.entity("trailhead-warner-valley")
    destination = reads.entity("hydrothermal-area-devils-kitchen")

    outbound = resolve_traversal(reads, route, trailhead, destination, date(2027, 8, 1))
    inbound = resolve_traversal(reads, route, destination, trailhead, date(2027, 8, 1))

    assert outbound.state is TraversalState.COMPLETE
    assert inbound.state is TraversalState.COMPLETE
    assert len(outbound.legs) == 4
    assert [item.segment_id for item in inbound.legs] == [
        item.segment_id for item in reversed(outbound.legs)
    ]
    assert outbound.distance_complete is False
    assert all(item.distance_status == "not_printed" for item in outbound.legs)


def test_terminal_geyser_traverses_shared_then_distinct_junctions():
    reads = CanonicalReadService(ROOT)
    route = reads.entity("route-terminal-geyser-trail")
    trailhead = reads.entity("trailhead-warner-valley")
    destination = reads.entity("hydrothermal-feature-terminal-geyser")

    plan = resolve_traversal(reads, route, trailhead, destination, date(2027, 8, 1))

    assert plan.state is TraversalState.COMPLETE
    assert len(plan.legs) == 6
    assert plan.legs[0].segment_id == "route-segment-lassen-warner-start-first-y"
    assert plan.legs[-1].segment_id == (
        "route-segment-lassen-terminal-divergence-destination"
    )
    assert plan.legs[-2].start_node_id == "route-node-lassen-terminal-pct-rejoin"
    assert plan.distance_complete is False


def test_remaining_lassen_topology_gap_is_narrowed_not_erased():
    records = load_canonical(ROOT)
    gaps = by_id(records, "gaps", "gap_id")
    gap = gaps["gap-lassen-specific-route-topology"]

    assert "ordered, bidirectional Warner Valley topology" in gap.reason
    assert "atomic leg distances remain unknown" in gap.reason
    assert "route-cinder-cone-trail" in gap.related_ids


def test_warner_valley_graph_is_one_validated_changeset():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260923-lassen-warner-valley-route-graph.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD", "REPLACE"}
