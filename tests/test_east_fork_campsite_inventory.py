"""The official East Fork numbered campsite inventory is complete and usable."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def by_id(records, collection, identifier):
    return {getattr(item, identifier): item for item in getattr(records, collection)}


def test_all_133_numbered_sites_have_profiles_and_parent_relationships():
    records = load_canonical(ROOT)
    entities = by_id(records, "entities", "entity_id")
    profiles = {
        item.subject_id: item for item in records.claims
        if item.predicate == "recreation_gov_site_profile"
        and item.subject_id.startswith("campsite-east-fork-")
    }
    relationships = by_id(records, "relationships", "relationship_id")

    expected = {f"campsite-east-fork-{number}" for number in range(1, 134)}
    assert expected <= entities.keys()
    assert profiles.keys() == expected
    assert all(entities[item].kind == "campsite" for item in expected)
    assert all(
        relationships[
            f"relationship-east-fork-site-{item.removeprefix('campsite-east-fork-')}-part-of-campground"
        ].object_id == "campground-east-fork-inyo"
        for item in expected
    )
    assert "campsite-east-fork-xxx" not in entities


def test_inventory_snapshot_separates_numbered_sites_from_management_record():
    claims = by_id(load_canonical(ROOT), "claims", "claim_id")
    snapshot = claims["claim-recreation-east-fork-campsite-inventory-20260924"]

    assert snapshot.value == {
        "excluded_management_records": 1,
        "numbered_public_sites": 133,
        "public_site_range": {"first": "001", "last": "0133"},
        "public_status_counts": {"Not Reservable": 69, "Open": 64},
        "retrieved_on": "2026-09-24",
        "total_api_records": 134,
    }


def test_site_profiles_keep_coordinates_equipment_details_notices_and_status():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")
    site_1 = claims["claim-recreation-east-fork-campsite-1-profile"].value

    assert site_1["name"] == "001"
    assert site_1["campsite_id"] == "62504"
    assert site_1["latitude"] == 37.4925489999999
    assert site_1["longitude"] == -118.719542
    assert site_1["site_details"]["campfire_allowed"] == "Yes"
    assert site_1["equipment_details"]["driveway_length"] == "30"
    assert {item["name"] for item in site_1["permitted_equipment"]} == {
        "Tent", "RV", "Trailer",
    }
    assert site_1["record_status"] == "Open"
    assert any(item["name"] == "Food Storage Locker" for item in site_1["amenities"])


def test_recreation_api_internal_conflicts_are_consumer_visible():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")
    gaps = by_id(records, "gaps", "gap_id")
    site_1 = claims["claim-recreation-east-fork-campsite-1-profile"].value

    assert site_1["site_details"]["checkout_time"] == "11:00 AM"
    assert any(
        item["code"] == "checkout_time" and item["value"] == "1:00 PM"
        for item in site_1["published_attributes"]
    )
    gap = gaps["gap-east-fork-site-1-published-field-conflict"]
    assert "claim-recreation-east-fork-campsite-1-profile" in gap.related_ids
    assert "site_details.checkout_time" in gap.reason
    assert len([
        item for item in records.gaps
        if item.gap_id.startswith("gap-east-fork-site-")
        and item.gap_id.endswith("-published-field-conflict")
    ]) == 70


def test_profile_provenance_resolves_to_official_bulk_endpoint():
    explanation = CanonicalReadService(ROOT).explain_claim(
        "claim-recreation-east-fork-campsite-1-profile"
    )
    assert explanation.sources[0].publisher == "Recreation.gov"
    assert explanation.sources[0].locator.endswith("/campgrounds/232396/campsites")


def test_generated_camping_directory_contains_all_east_fork_sites(generated_site):
    tmp_path, _ = generated_site
    camping = json.loads((tmp_path / "camping" / "index.json").read_text())
    ids = {item["entity_id"] for item in camping["entities"]}

    assert {f"campsite-east-fork-{number}" for number in range(1, 134)} <= ids
    page = tmp_path / "knowledge" / "campsite-east-fork-1" / "index.html"
    assert page.exists()
    html = page.read_text()
    assert "East Fork Campground Site 001" in html
    assert "Food Storage Locker" in html


def test_inventory_changeset_is_validated_and_exact():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260924-east-fork-campsite-inventory.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 602
    assert len({item.path for item in change.operations}) == 602
