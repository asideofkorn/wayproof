"""Regression checks for the complete Del Valle ReserveAmerica site corpus."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def records():
    return load_canonical(ROOT)


def profiles():
    return [item for item in records().claims
            if item.predicate == "reserveamerica_site_profile"]


def test_all_155_site_pages_have_unique_profiles_and_sources():
    snapshot = records()
    items = profiles()
    assert len(items) == 155
    assert len({item.subject_id for item in items}) == 155
    assert len({item.value["product_id"] for item in items}) == 155
    assert len({item.value["booking_url"] for item in items}) == 155

    source_ids = {item.source_id for item in snapshot.sources}
    observations = {item.observation_id: item for item in snapshot.observations}
    evidence = {item.evidence_id: item for item in snapshot.evidence}
    for item in items:
        assert len(item.evidence_ids) == 1
        evidence_item = evidence[item.evidence_ids[0]]
        observation = observations[evidence_item.observation_id]
        assert observation.source_id in source_ids
        assert item.value["booking_url"].endswith(
            f"/{item.value['product_id']}/campsite-booking")


def test_coordinates_are_present_only_when_the_source_publishes_them():
    items = profiles()
    located = [item for item in items
               if item.value["latitude"] is not None
               and item.value["longitude"] is not None]
    missing = [item for item in items
               if item.value["latitude"] is None
               and item.value["longitude"] is None]
    assert len(located) == 146
    assert len(missing) == 9
    assert {item.value["name"] for item in missing} == {
        "Horse Camp #1", "Horse Camp #2", "Horse Camp #3", "Horse Camp #4",
        "ARDILLA(50)", "EAGLES VIEW (50)", "CEDAR CAMP(50)",
        "HETCH HETCHY (100)", "VENADOS(50)",
    }
    assert all(-90 <= item.value["latitude"] <= 90 for item in located)
    assert all(-180 <= item.value["longitude"] <= 180 for item in located)


def test_listing_inventory_conflict_remains_explicit():
    snapshot = records()
    listing = next(item for item in snapshot.claims
                   if item.claim_id == "claim-reserveamerica-del-valle-campsites-inventory")
    assert listing.value["total_entries"] == 155
    assert listing.value["family_category_total"] == 143
    assert listing.value["missing_family_site_numbers_1_through_150"] == [
        33, 42, 54, 67, 88, 97, 150,
    ]
    gap = next(item for item in snapshot.gaps
               if item.gap_id == "gap-del-valle-family-site-inventory-conflict")
    assert set(gap.related_ids) == {
        "claim-del-valle-campground-inventory",
        "claim-reserveamerica-del-valle-campsites-inventory",
    }


def test_existing_group_camp_entities_are_reused_not_duplicated():
    snapshot = records()
    hetch = next(item for item in profiles()
                 if item.value["product_id"] == "382")
    assert hetch.subject_id == "group-camp-del-valle-hetch-hetchy"
    assert hetch.value["details"]["site_access"] == "Boat-In, Hike-In"
    assert hetch.value["details"]["maximum_number_of_people"] == 100
    assert len([item for item in snapshot.entities
                if item.name.lower() == "hetch hetchy"]) == 1


def test_little_chaparral_identity_is_not_inferred():
    snapshot = records()
    gap = next(item for item in snapshot.gaps
               if item.gap_id == "gap-del-valle-little-chaparral-site-identity")
    assert "camp-del-valle-little-chaparral" in gap.related_ids
    assert len([item for item in profiles()
                if item.value["site_type"] == "EQUESTRIAN SITE"]) == 4


def test_site_detail_changeset_is_validated_and_complete():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-reserveamerica-del-valle-site-details.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 933
    assert len({item.path for item in change.operations}) == 933
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 932, "REPLACE": 1, "REMOVE": 0}
