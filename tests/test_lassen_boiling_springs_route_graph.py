"""Official USGS/NPS features preserve the Boiling Springs Lake route graph."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]


def test_boiling_springs_access_is_distance_complete_both_directions():
    reads = CanonicalReadService(ROOT)
    route = reads.entity("route-boiling-springs-lake-trail")
    trailhead = reads.entity("trailhead-warner-valley")
    lake = reads.entity("waterbody-boiling-springs-lake")

    outbound = resolve_traversal(reads, route, trailhead, lake, date(2027, 8, 1))
    inbound = resolve_traversal(reads, route, lake, trailhead, date(2027, 8, 1))

    assert outbound.state is TraversalState.COMPLETE
    assert outbound.distance_complete is True
    assert outbound.total_known_distance_miles == 1.40383803
    assert len(outbound.legs) == 6
    assert inbound.state is TraversalState.COMPLETE
    assert inbound.total_known_distance_miles == outbound.total_known_distance_miles
    assert [item.segment_id for item in inbound.legs] == [
        item.segment_id for item in reversed(outbound.legs)
    ]


def test_parallel_approach_and_around_lake_features_are_not_flattened():
    records = load_canonical(ROOT)
    relationships = records.relationships
    members = {
        item.subject_id
        for item in relationships
        if item.predicate == "part_of"
        and item.object_id == "route-boiling-springs-lake-trail"
    }

    assert len(members) == 12
    assert {
        "route-segment-lassen-boiling-west-approach",
        "route-segment-lassen-boiling-pct-north",
        "route-segment-lassen-boiling-north-connector",
        "route-segment-lassen-boiling-lake-southeast",
        "route-segment-lassen-boiling-southeast-northeast",
        "route-segment-lassen-boiling-northeast-north",
        "route-segment-lassen-boiling-north-lake",
    } <= members
    southeast = next(
        item for item in relationships
        if item.relationship_id
        == "relationship-route-segment-lassen-boiling-lake-southeast-ends-at"
    )
    assert southeast.object_id == "route-node-lassen-boiling-springs-southeast"


def test_dataset_feature_identity_precision_and_current_check_are_preserved():
    records = load_canonical(ROOT)
    claims = {item.claim_id: item for item in records.claims}
    claim = claims["claim-route-segment-lassen-boiling-west-approach"]

    assert claim.predicate == "official_dataset_route_segment"
    assert claim.value["dataset_feature_id"] == (
        "d0ca7a44-9773-4286-9921-cc664f3a72a5"
    )
    assert claim.value["distance_miles"] == 0.23998938
    assert claim.value["operational_status_requires_current_check"] is True


def test_remaining_lassen_gap_excludes_boiling_springs_route():
    records = load_canonical(ROOT)
    gap = next(
        item for item in records.gaps
        if item.gap_id == "gap-lassen-specific-route-topology"
    )

    assert "route-boiling-springs-lake-trail" not in gap.related_ids
    assert "atomic shared approach plus around-lake network" in gap.reason
    assert "route-cinder-cone-trail" not in gap.related_ids
    assert any(
        item.gap_id == "gap-lassen-cinder-rim-crater-circulation"
        for item in records.gaps
    )


def test_boiling_springs_graph_is_one_validated_changeset():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260923-lassen-boiling-springs-route-graph.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD", "REPLACE"}
