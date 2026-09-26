from datetime import date
import json
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeAction, ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]
ROUTES = (
    (
        "route-may-lake-day-hike",
        "trailhead-may-lake",
        "waterbody-may-lake",
        19452,
    ),
    (
        "route-lukens-lake-tioga",
        "trailhead-lukens-lake-tioga",
        "waterbody-lukens-lake",
        18552,
    ),
)


@pytest.mark.parametrize("route,start,end,object_id", ROUTES)
def test_reviewed_routes_traverse_both_directions(route, start, end, object_id):
    read = CanonicalReadService(ROOT)
    forward = resolve_traversal(
        read, read.entity(route), read.entity(start), read.entity(end), date(2026, 9, 30)
    )
    backward = resolve_traversal(
        read, read.entity(route), read.entity(end), read.entity(start), date(2026, 9, 30)
    )
    assert forward.state is backward.state is TraversalState.COMPLETE
    assert len(forward.legs) == len(backward.legs) == 1
    assert forward.legs[0].segment_id == backward.legs[0].segment_id
    assert forward.total_known_distance_miles == backward.total_known_distance_miles == 0
    assert forward.distance_complete is backward.distance_complete is False
    assert str(object_id) in forward.legs[0].segment_id


def test_snapshot_and_route_pages_publish(generated_site):
    snapshot = json.loads(
        (
            ROOT
            / "geometry/v0/snapshots/nps-yose-west-tioga-route-features-20260926.geojson"
        ).read_text()
    )
    assert {feature["properties"]["nps_object_id"] for feature in snapshot["features"]} == {
        18552,
        19452,
    }
    site, _ = generated_site
    for route, *_ in ROUTES:
        page = (site / "knowledge" / route / "index.html").read_text()
        assert "Interactive map" in page
        assert "Download generated GeoJSON" in page


def test_remaining_topology_gap_names_unsupported_joins():
    records = load_canonical(ROOT)
    gap = next(
        item
        for item in records.gaps
        if item.gap_id == "gap-yosemite-west-tioga-route-topology"
    )
    assert "no nearby geometry is snapped" in gap.reason
    assert "route-merced-grove" in gap.related_ids
    assert "route-north-dome-porcupine-creek" in gap.related_ids


def test_batch_is_one_validated_changeset():
    changeset = load_changeset(
        ROOT / "changesets/v0/wp-20260926-yosemite-west-tioga-route-graph.json"
    )
    assert changeset.status is ChangeSetStatus.VALIDATED
    assert {operation.action for operation in changeset.operations} == {
        ChangeAction.ADD,
        ChangeAction.REPLACE,
    }
