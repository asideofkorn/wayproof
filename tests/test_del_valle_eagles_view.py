"""Regression checks for the Eagles View evidence bundle."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus

ROOT = Path(__file__).resolve().parents[1]


def records():
    return load_canonical(ROOT)


def claim(claim_id):
    return next(item for item in records().claims if item.claim_id == claim_id)


def test_official_map_and_camping_page_bound_identity_and_facilities():
    location = claim("claim-del-valle-map-eagles-view-location")
    profile = claim("claim-del-valle-camping-eagles-view-details")
    assert location.subject_id == "group-camp-del-valle-eagles-view"
    assert location.value["adjacent_to"] == "parking area 66"
    assert profile.value["capacity"] == {"minimum": 17, "maximum": 50}
    assert profile.value["drinking_fountain"] is True
    assert profile.value["flush_toilets"] == "uphill_from_site"
    assert profile.value["showers"] is False


def test_user_pin_is_approximate_and_does_not_fill_reserveamerica():
    pin = claim("claim-google-maps-del-valle-eagles-view-coordinate")
    reserveamerica = claim("claim-reserveamerica-del-valle-site-243-profile")
    assert pin.value["provenance_class"] == "user_supplied_map_estimate"
    assert pin.value["latitude"] == 37.5833377
    assert pin.value["longitude"] == -121.6930213
    assert reserveamerica.value["latitude"] is None
    assert reserveamerica.value["longitude"] is None


def test_eagles_view_changeset_is_validated():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-del-valle-eagles-view-evidence.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 10
    assert all(item.action.value == "ADD" for item in change.operations)

