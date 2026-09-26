"""Reviewed Tuolumne route graphs remain connected, bounded, and publishable."""

import json
from datetime import date
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeAction, ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]

TRAVERSALS = (
    ("route-pothole-dome", "trailhead-pothole-dome", "peak-pothole-dome", 2),
    ("route-parsons-lodge-soda-springs", "trailhead-soda-springs-tuolumne", "place-parsons-memorial-lodge", 4),
    ("route-dog-lake-lembert-dome", "trailhead-dog-lake-tuolumne", "waterbody-dog-lake-yosemite", 6),
    ("route-dog-lake-lembert-dome", "trailhead-dog-lake-tuolumne", "peak-lembert-dome", 4),
    ("route-gaylor-lakes", "trailhead-gaylor-lakes", "waterbody-middle-gaylor-lake", 2),
    ("route-elizabeth-lake-yosemite", "trailhead-elizabeth-lake-yosemite", "waterbody-elizabeth-lake-yosemite", 2),
    ("route-cathedral-lakes-yosemite", "trailhead-cathedral-lakes-yosemite", "waterbody-lower-cathedral-lake", 4),
    ("route-mono-pass-yosemite", "trailhead-mono-parker-pass-yosemite", "pass-mono-yosemite", 2),
    ("route-glen-aulin-day-hike", "access-lembert-dome-parking", "place-glen-aulin", 14),
    ("route-young-lakes-day-hike", "access-lembert-dome-parking", "waterbody-young-lakes", 7),
)


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


@pytest.mark.parametrize("route_id,entry_id,exit_id,leg_count", TRAVERSALS)
def test_reviewed_routes_resolve_both_directions(reads, route_id, entry_id, exit_id, leg_count):
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


def test_printed_atomic_mileages_are_not_manufactured_for_unlabeled_legs(reads):
    gaylor = resolve_traversal(
        reads,
        reads.entity("route-gaylor-lakes"),
        reads.entity("trailhead-gaylor-lakes"),
        reads.entity("waterbody-middle-gaylor-lake"),
        date(2026, 9, 30),
    )
    young = resolve_traversal(
        reads,
        reads.entity("route-young-lakes-day-hike"),
        reads.entity("access-lembert-dome-parking"),
        reads.entity("waterbody-young-lakes"),
        date(2026, 9, 30),
    )

    assert gaylor.total_known_distance_miles == pytest.approx(1.3)
    assert gaylor.distance_complete is True
    assert young.total_known_distance_miles == pytest.approx(5.0)
    assert young.distance_complete is False
    assert any(leg.distance_status == "not_printed" for leg in young.legs)


def test_shared_corridor_is_one_physical_set_of_segments(reads):
    relationships = load_canonical(ROOT).relationships
    for suffix in ("01", "02", "03", "04"):
        segment_id = f"route-segment-tuolumne-pct-{suffix}"
        memberships = {
            edge.object_id
            for edge in relationships
            if edge.subject_id == segment_id and edge.predicate == "part_of"
        }
        assert memberships == {
            "route-glen-aulin-day-hike",
            "route-young-lakes-day-hike",
        }


def test_twin_bridges_is_the_only_remaining_topology_gap():
    records = load_canonical(ROOT)
    gap = next(item for item in records.gaps if item.gap_id == "gap-tuolumne-route-segment-topology")
    assert gap.related_ids == (
        "route-twin-bridges-tuolumne",
        "source-nps-yosemite-tuolumne-trails-map-2024",
        "source-nps-public-trails-feature-service",
    )
    assert "rather than inferring a connector from proximity" in gap.reason


def test_reviewed_geometry_snapshot_and_route_pages_publish(generated_site):
    snapshot = json.loads((ROOT / "geometry/v0/snapshots/nps-yose-tuolumne-route-features-20260925.geojson").read_text())
    assert len(snapshot["features"]) == 34
    assert {item["id"] for item in snapshot["features"]} >= {
        "nps-trail-20557-approach",
        "nps-trail-20557-lake",
        "nps-trail-19869",
        "nps-trail-17944",
    }

    site_root, _ = generated_site
    for route_id, _, _, _ in TRAVERSALS:
        page = (site_root / "knowledge" / route_id / "index.html").read_text()
        assert "National Park Service" in page

    for route_id in (
        "route-gaylor-lakes",
        "route-elizabeth-lake-yosemite",
        "route-mono-pass-yosemite",
    ):
        page = (site_root / "knowledge" / route_id / "index.html").read_text()
        assert "Download generated GeoJSON" in page
        assert "Interactive map" in page


def test_route_depth_is_one_validated_changeset():
    change = load_changeset(ROOT / "changesets/v0/wp-20260925-tuolumne-route-depth.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {item.action for item in change.operations} == {
        ChangeAction.ADD,
        ChangeAction.REPLACE,
    }
    assert len(change.operations) == len({item.path for item in change.operations})
