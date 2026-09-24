"""Rock Creek route, campground, and peak depth remains source-fidelitous."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "route-little-lakes-valley": (1080, 190),
    "route-mono-pass-rock-creek": (1820, 10),
    "route-morgan-pass-rock-creek": (1140, 810),
    "route-tamarack-lakes-rock-creek": (2200, 330),
    "route-hilton-lakes-rock-creek": (770, 530),
}
PEAKS = {
    "peak-mount-morgan-south": 13748,
    "peak-mount-starr-rock-creek": 12835,
    "peak-mount-dade": 13600,
    "peak-mount-abbot": 13704,
    "peak-bear-creek-spire": 13713,
}


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_five_routes_publish_approximate_3dep_profiles_without_invented_difficulty():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    gaps = indexed(records, "gaps", "gap_id")
    for route_id, (gain, loss) in ROUTES.items():
        profile = claims[f"claim-{route_id}-profile"].value["sampled_elevation_profile"]
        assert profile["approximate_cumulative_gain_ft"] == gain
        assert profile["approximate_cumulative_loss_ft"] == loss
        assert profile["sample_spacing_meters"] == 100
        assert profile["precision"] == "approximate"
    gap = gaps["gap-rock-creek-route-time-and-difficulty"]
    assert set(gap.related_ids) == set(ROUTES)
    assert "does not derive one" in gap.reason


def test_booking_profiles_deepen_two_campgrounds_and_preserve_source_precision():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    rock = claims["claim-campground-rock-creek-lake-booking-profile"].value
    palisades = claims["claim-campground-palisade-rock-creek-booking-profile"].value

    assert rock["booking_facility_id"] == "233907"
    assert rock["published_elevation_ft"] == 9600
    assert rock["pets"] == {"maximum": 2, "leash_required": True}
    assert rock["trail_access"] == "Tamarack Trail begins in the campground"
    assert palisades["booking_facility_id"] == "234663"
    assert palisades["facilities"] == {"tables": 5, "campfire_rings": True}
    assert palisades["published_elevation_text"] == "8.800 feet"


def test_official_peak_identity_only_adds_evidenced_planning_grade_approaches():
    records = load_canonical(ROOT)
    entities = indexed(records, "entities", "entity_id")
    claims = indexed(records, "claims", "claim_id")
    gaps = indexed(records, "gaps", "gap_id")
    relationships = records.relationships

    for peak_id, elevation in PEAKS.items():
        assert entities[peak_id].kind == "peak"
        assert claims[f"claim-{peak_id}-official-map-elevation"].value["elevation_ft"] == elevation
        assert claims[f"claim-{peak_id}-gnis-coordinate"].value["source_system"] == "GNIS"
        assert not any(
            item.subject_id == peak_id and item.predicate in {"starts_at", "traverses"}
            for item in relationships
        )
        profile = claims[f"claim-{peak_id}-summit-approach-profile"].value
        assert profile["navigation_grade"] is False
        assert profile["off_trail_continuation"]
    assert set(gaps["gap-rock-creek-peak-summit-access"].related_ids) == set(PEAKS)


def test_generated_site_adds_peaks_and_keeps_route_profile_qualifiers(tmp_path):
    from scripts import build_site

    build_site.build(tmp_path)
    peaks = json.loads((tmp_path / "peaks" / "index.json").read_text())
    assert PEAKS.keys() <= {item["entity_id"] for item in peaks["entities"]}
    route_page = (tmp_path / "knowledge" / "route-little-lakes-valley" / "index.html").read_text()
    assert "Approximate cumulative gain ft" in route_page
    assert "Precision</dt><dd>approximate" in route_page
    peak_page = (tmp_path / "knowledge" / "peak-mount-dade" / "index.html").read_text()
    assert "13600" in peak_page
    assert "south slope or Hourglass Couloir" in peak_page
    assert "Navigation grade</dt><dd>No" in peak_page


def test_one_validated_changeset_accounts_for_additions_and_replacements():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260923-rock-creek-planning-depth.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action for item in change.operations} == {
        ChangeAction.ADD, ChangeAction.REPLACE,
    }
