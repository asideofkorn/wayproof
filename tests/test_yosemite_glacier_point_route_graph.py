"""Glacier Point route topology is exact, reusable, and source bounded."""

import json
from datetime import date
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeAction, ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "route-mcgurk-meadow": ("trailhead-mcgurk-meadow", "place-mcgurk-meadow", 1),
    "route-sentinel-dome": ("trailhead-sentinel-dome-taft-point", "peak-sentinel-dome", 3),
    "route-taft-point": ("trailhead-sentinel-dome-taft-point", "viewpoint-taft-point", 4),
}


@pytest.mark.parametrize("route_id,start,end,count", [(route_id, *spec) for route_id, spec in ROUTES.items()])
def test_reviewed_routes_resolve_both_directions(route_id, start, end, count):
    reads = CanonicalReadService(ROOT)
    route = reads.entity(route_id)
    entry = reads.entity(start)
    exit_entity = reads.entity(end)
    forward = resolve_traversal(reads, route, entry, exit_entity, date(2026, 9, 30))
    reverse = resolve_traversal(reads, route, exit_entity, entry, date(2026, 9, 30))
    assert forward.state is TraversalState.COMPLETE
    assert reverse.state is TraversalState.COMPLETE
    assert len(forward.legs) == len(reverse.legs) == count
    assert [leg.segment_id for leg in reverse.legs] == [leg.segment_id for leg in reversed(forward.legs)]


def test_shared_sentinel_taft_connector_is_one_physical_segment():
    records = load_canonical(ROOT)
    segment_id = "route-segment-yosemite-glacier-point-nps-22472"
    memberships = {edge.object_id for edge in records.relationships if edge.subject_id == segment_id and edge.predicate == "part_of"}
    assert memberships == {"route-sentinel-dome", "route-taft-point"}


def test_snapshot_and_route_pages_publish(generated_site):
    snapshot = json.loads((ROOT / "geometry/v0/snapshots/nps-yose-glacier-point-route-features-20260926.geojson").read_text())
    assert {item["properties"]["nps_object_id"] for item in snapshot["features"]} == {17070, 22472, 21941, 21957, 19778, 15277, 20739}
    site_root, _ = generated_site
    for route_id in ROUTES:
        page = (site_root / "knowledge" / route_id / "index.html").read_text()
        assert "Interactive map" in page
        assert "Download generated GeoJSON" in page


def test_remaining_topology_is_explicit_and_not_proximity_inferred():
    records = load_canonical(ROOT)
    gap = next(item for item in records.gaps if item.gap_id == "gap-yosemite-glacier-point-route-topology")
    assert "nearby or unnamed lines are not joined" in gap.reason
    assert "route-ostrander-lake" in gap.related_ids
    assert "route-panorama-trail" in gap.related_ids


def test_batch_is_one_validated_changeset():
    change = load_changeset(ROOT / "changesets/v0/wp-20260926-yosemite-glacier-point-route-graph.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {operation.action for operation in change.operations} == {ChangeAction.ADD, ChangeAction.REPLACE}
    assert len(change.operations) == len({operation.path for operation in change.operations})
