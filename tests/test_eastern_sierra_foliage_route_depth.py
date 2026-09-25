"""Priority foliage options retain useful, evidence-bounded route depth."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical
from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


def keyed(items, attribute):
    return {getattr(item, attribute): item for item in items}


def test_parker_and_heart_routes_have_connected_bidirectional_geometry():
    reads = CanonicalReadService(ROOT)
    for route_id, expected_features in (("route-parker-lake", 5), ("route-heart-lake-mammoth", 4)):
        geometry = reads.route_geometry(route_id, date(2026, 10, 1))
        assert len(geometry["features"]) == expected_features
        assert all(feature["properties"]["distance_status"] == "known" for feature in geometry["features"])


def test_foliage_choices_fit_trip_distance_cap_without_duration_invention():
    records = load_canonical(ROOT)
    results = keyed(records.derived_results, "result_id")
    for route_id in ("route-parker-lake", "route-heart-lake-mammoth", "route-convict-lake-loop"):
        result = results[f"result-{route_id}-ten-mile-day-hike-fit"]
        assert result.value["fits_distance_limit"] is True
        assert "duration" not in result.value


def test_convict_loop_preserves_map_backed_closure_without_invented_distance():
    records = load_canonical(ROOT)
    claims = keyed(records.claims, "claim_id")
    gaps = keyed(records.gaps, "gap_id")
    assert claims["claim-convict-lake-loop-published-profile"].value["round_trip_miles"] == 2
    connector = claims["claim-route-segment-convict-lake-loop-east-connector"].value
    assert connector["distance_status"] == "unknown"
    assert connector["geometry_status"] == "official_map_depiction_without_reusable_line_geometry"
    assert connector["route_role"] == "east_shore_closure"
    assert "gap-convict-lake-loop-dataset-closure" not in gaps

    edges = {
        (item.subject_id, item.predicate, item.object_id)
        for item in records.relationships
        if item.subject_id == "route-segment-convict-lake-loop-east-connector"
    }
    assert edges == {
        (
            "route-segment-convict-lake-loop-east-connector",
            "starts_at",
            "route-node-convict-lake-loop-south",
        ),
        (
            "route-segment-convict-lake-loop-east-connector",
            "ends_at",
            "route-node-convict-lake-loop-east",
        ),
        (
            "route-segment-convict-lake-loop-east-connector",
            "part_of",
            "route-convict-lake-loop",
        ),
    }


def test_foliage_route_depth_publishes_to_human_pages(generated_site):
    site_root, _ = generated_site
    parker = (site_root / "knowledge" / "route-parker-lake" / "index.html").read_text()
    convict = (site_root / "knowledge" / "route-convict-lake-loop" / "index.html").read_text()
    assert "1.84699256" in parker
    assert "U.S. Geological Survey / U.S. Forest Service" in parker
    assert "Mount Morrison" in convict
