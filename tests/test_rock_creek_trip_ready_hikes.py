"""Rock Creek hike choices expose useful trip-planning context."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical


ROOT = Path(__file__).resolve().parents[1]


def records_by_id(items, key):
    return {getattr(item, key): item for item in items}


def test_rock_creek_hikes_expose_access_and_trail_character():
    records = load_canonical(ROOT)
    claims = records_by_id(records.claims, "claim_id")
    relationships = records_by_id(records.relationships, "relationship_id")

    assert claims["claim-rock-creek-hilton-day-hike-context"].value["trailhead_elevation_ft"] == 9600
    assert "steep initially" in claims["claim-rock-creek-tamarack-day-hike-context"].value["trail_character"]
    assert relationships["relationship-rock-creek-road-accesses-mosquito-flat"].object_id == "trailhead-mosquito-flat"
    assert relationships["relationship-east-fork-near-upper-rock-creek-day-hike-access"].subject_id == "campground-east-fork-inyo"


def test_ten_mile_fit_is_derived_and_keeps_duration_unknown():
    records = load_canonical(ROOT)
    results = records_by_id(records.derived_results, "result_id")

    expected = {
        "route-little-lakes-valley": True,
        "route-hilton-lakes-rock-creek": True,
        "route-tamarack-lakes-rock-creek": False,
        "route-upper-rock-creek-canyon": True,
    }
    for route_id, fits in expected.items():
        result = results[f"result-{route_id}-ten-mile-day-hike-fit"]
        assert result.value["fits_distance_limit"] is fits
        assert result.value["duration_status"] == "unknown"
        assert result.input_ids


def test_rock_creek_trip_ready_records_publish_to_site(generated_site):
    site_root, _ = generated_site
    route_page = (site_root / "knowledge" / "route-hilton-lakes-rock-creek" / "index.html").read_text()
    east_fork_page = (site_root / "knowledge" / "campground-east-fork-inyo" / "index.html").read_text()

    assert "forest of whitebark and lodgepole pine" in route_page
    assert "Upper Rock Creek Canyon Trail" in east_fork_page
