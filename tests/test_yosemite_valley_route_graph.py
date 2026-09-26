"""Reviewed Yosemite Valley route topology remains connected and source bounded."""

import json
from datetime import date
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeAction, ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]
ROUTES = (
    ("route-four-mile-trail", "trailhead-four-mile-yosemite-valley", "place-glacier-point", 2),
    ("route-upper-yosemite-fall", "trailhead-yosemite-falls", "waterfall-upper-yosemite-fall", 1),
    ("route-vernal-nevada-falls", "trailhead-happy-isles", "waterfall-nevada-fall", 10),
)


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


@pytest.mark.parametrize("route_id,entry_id,exit_id,leg_count", ROUTES)
def test_reviewed_valley_routes_resolve_both_directions(reads, route_id, entry_id, exit_id, leg_count):
    route = reads.entity(route_id)
    entry = reads.entity(entry_id)
    exit_entity = reads.entity(exit_id)
    forward = resolve_traversal(reads, route, entry, exit_entity, date(2026, 9, 30))
    reverse = resolve_traversal(reads, route, exit_entity, entry, date(2026, 9, 30))

    assert forward.state is TraversalState.COMPLETE
    assert reverse.state is TraversalState.COMPLETE
    assert len(forward.legs) == leg_count
    assert [leg.segment_id for leg in reverse.legs] == [
        leg.segment_id for leg in reversed(forward.legs)
    ]
    assert forward.distance_complete is False


def test_jmt_detour_is_preserved_as_an_alternate(reads):
    plan = resolve_traversal(
        reads,
        reads.entity("route-vernal-nevada-falls"),
        reads.entity("trailhead-happy-isles"),
        reads.entity("waterfall-nevada-fall"),
        date(2026, 9, 30),
    )
    assert plan.state is TraversalState.COMPLETE
    assert "route-segment-yosemite-valley-nps-16432" in plan.alternate_segment_ids
    assert plan.alternate_legs


def test_remaining_valley_topology_is_explicitly_bounded():
    records = load_canonical(ROOT)
    gap = next(item for item in records.gaps if item.gap_id == "gap-yosemite-valley-remaining-route-topology")
    assert "route-mirror-lake" in gap.related_ids
    assert "route-yosemite-valley-loop" in gap.related_ids
    assert "does not snap nearby endpoints" in gap.reason


def test_reviewed_snapshot_and_route_pages_publish(generated_site):
    snapshot = json.loads(
        (ROOT / "geometry/v0/snapshots/nps-yose-valley-route-features-20260926.geojson").read_text()
    )
    assert len(snapshot["features"]) == 19
    assert {item["properties"]["trail_name"] for item in snapshot["features"]} == {
        "Four Mile Trail",
        "John Muir Trail",
        "Mist Trail",
        "Yosemite Falls Trail",
    }

    site_root, _ = generated_site
    for route_id, _, _, _ in ROUTES:
        page = (site_root / "knowledge" / route_id / "index.html").read_text()
        assert "Download generated GeoJSON" in page
        assert "Interactive map" in page


def test_valley_graph_is_one_validated_changeset():
    change = load_changeset(ROOT / "changesets/v0/wp-20260926-yosemite-valley-route-graph.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {item.action for item in change.operations} == {ChangeAction.ADD}
    assert len(change.operations) == len({item.path for item in change.operations})
