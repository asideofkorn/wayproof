"""Upper Rock Creek, lake spurs, and summit approaches stay evidence-bounded."""

from datetime import date
import hashlib
import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path("geometry/v0/snapshots/usgs-rock-creek-route-extensions-20260924.geojson")
PEAKS = {
    "peak-mount-morgan-south": None,
    "peak-mount-starr-rock-creek": "route-mono-pass-rock-creek",
    "peak-mount-dade": "route-little-lakes-valley",
    "peak-mount-abbot": "route-mono-pass-rock-creek",
    "peak-bear-creek-spire": "route-little-lakes-valley",
}


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_upper_rock_creek_is_a_nine_segment_bidirectional_route():
    reads = CanonicalReadService(ROOT)
    route = reads.entity("route-upper-rock-creek-canyon")
    north = reads.entity("access-upper-rock-creek-east-fork")
    south = reads.entity("route-node-upper-rock-creek-lake-south-end")

    outbound = resolve_traversal(reads, route, north, south, date(2026, 9, 30))
    inbound = resolve_traversal(reads, route, south, north, date(2026, 9, 30))

    assert outbound.state is TraversalState.COMPLETE
    assert outbound.distance_complete is True
    assert outbound.total_known_distance_miles == 4.19867235
    assert len(outbound.legs) == 9
    assert inbound.state is TraversalState.COMPLETE
    assert inbound.total_known_distance_miles == outbound.total_known_distance_miles
    assert [item.segment_id for item in inbound.legs] == [
        item.segment_id for item in reversed(outbound.legs)
    ]


def test_extension_snapshot_is_bounded_and_routes_project_geometry():
    content = (ROOT / SNAPSHOT).read_bytes()
    snapshot = json.loads(content)
    reads = CanonicalReadService(ROOT)

    assert len(snapshot["features"]) == 11
    assert len(hashlib.sha256(content).hexdigest()) == 64
    assert {item["properties"]["source_originator"] for item in snapshot["features"]} == {
        "U.S. Forest Service"
    }
    geometry = reads.route_geometry("route-upper-rock-creek-canyon", date(2026, 9, 30))
    assert len(geometry["features"]) == 9
    assert geometry["wayproof"]["navigation_grade"] is False
    assert geometry["wayproof"]["distance_miles"] == 4.19867235


def test_named_spurs_preserve_lengths_without_false_mainline_traversal():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    relationships = records.relationships
    gaps = indexed(records, "gaps", "gap_id")

    assert claims["claim-route-chickenfoot-lake-spur-profile"].value["one_way_distance_miles"] == 0.24964325
    assert claims["claim-route-gem-lakes-spur-profile"].value["one_way_distance_miles"] == 0.37391222
    for route_id in ("route-chickenfoot-lake-spur", "route-gem-lakes-spur"):
        assert any(
            item.subject_id == route_id
            and item.predicate == "branches_from"
            and item.object_id == "route-little-lakes-valley"
            for item in relationships
        )
    gap = gaps["gap-rock-creek-gem-chickenfoot-spur-connectors"]
    assert "without proximity-snapping" in gap.reason
    assert gaps["gap-rock-creek-little-lakes-intermediate-mileages"]


def test_five_peaks_publish_planning_context_not_navigation_tracks():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    relationships = records.relationships
    gaps = indexed(records, "gaps", "gap_id")

    for peak_id, route_id in PEAKS.items():
        profile = claims[f"claim-{peak_id}-summit-approach-profile"].value
        assert profile["source_tier"] == "third_party_reference_only"
        assert profile["navigation_grade"] is False
        assert profile["current_conditions_required"] is True
        assert profile["off_trail_continuation"]
        if route_id:
            assert any(
                item.subject_id == peak_id
                and item.predicate == "approached_via"
                and item.object_id == route_id
                for item in relationships
            )
        else:
            assert not any(
                item.subject_id == peak_id and item.predicate == "approached_via"
                for item in relationships
            )
    assert "navigation-grade geometry" in gaps["gap-rock-creek-peak-summit-access"].reason


def test_generated_pages_surface_new_route_spurs_and_peak_context(tmp_path):
    from scripts import build_site

    build_site.build(tmp_path)
    route_page = (tmp_path / "knowledge" / "route-upper-rock-creek-canyon" / "index.html").read_text()
    spur_page = (tmp_path / "knowledge" / "route-gem-lakes-spur" / "index.html").read_text()
    peak_page = (tmp_path / "knowledge" / "peak-mount-abbot" / "index.html").read_text()
    assert "Upper Rock Creek Canyon" in route_page
    assert "4.19867235" in route_page
    assert "0.37391222" in spur_page
    assert "Northeast Couloir" in peak_page
    assert "Navigation grade</dt><dd>No" in peak_page


def test_one_validated_changeset_accounts_for_additions_and_replacements():
    change = load_changeset(ROOT / "changesets/v0/wp-20260924-rock-creek-route-and-summit-depth.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD", "REPLACE"}
