"""Regression checks for third-party Del Valle group-camp coordinates."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus

ROOT = Path(__file__).resolve().parents[1]


def test_google_maps_coordinates_are_separate_attributed_claims():
    snapshot = load_canonical(ROOT)
    claims = [item for item in snapshot.claims
              if item.predicate == "google_maps_coordinate"]
    assert {item.subject_id for item in claims} == {
        "group-camp-del-valle-ardilla",
        "group-camp-del-valle-cedar",
        "group-camp-del-valle-eagles-view",
        "group-camp-del-valle-hetch-hetchy",
        "group-camp-del-valle-venados",
    }
    classes = {item.subject_id: item.value["provenance_class"] for item in claims}
    assert classes["group-camp-del-valle-eagles-view"] == "user_supplied_map_estimate"
    assert set(classes.values()) == {
        "third_party_labeled_place", "user_supplied_map_estimate"
    }
    assert all(-90 <= item.value["latitude"] <= 90 for item in claims)
    assert all(-180 <= item.value["longitude"] <= 180 for item in claims)
    assert all(item.value["plus_code"] for item in claims)


def test_reserveamerica_profiles_remain_source_faithful_and_unmodified():
    snapshot = load_canonical(ROOT)
    profiles = [item for item in snapshot.claims
                if item.predicate == "reserveamerica_site_profile"
                and item.value.get("booking_url", "").startswith(
                    "https://www.reserveamerica.com/explore/del-valle/EB/110003/")]
    missing = {item.value["name"] for item in profiles
               if item.value["latitude"] is None
               and item.value["longitude"] is None}
    assert missing == {
        "Horse Camp #1", "Horse Camp #2", "Horse Camp #3", "Horse Camp #4",
        "ARDILLA(50)", "EAGLES VIEW (50)", "CEDAR CAMP(50)",
        "HETCH HETCHY (100)", "VENADOS(50)",
    }


def test_coordinate_changeset_is_validated_and_complete():
    change = load_changeset(
        ROOT / "changesets/v0/"
        "wp-20260920-google-maps-del-valle-group-camp-coordinates.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 16
    assert all(item.action.value == "ADD" for item in change.operations)
