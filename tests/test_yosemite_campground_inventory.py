"""Official Yosemite campground and campsite inventory is complete and usable."""

from datetime import date
import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.schema import (
    ActivityContext, ChangeSetStatus, PartyContext, PlanningContext, TripStage,
)


ROOT = Path(__file__).resolve().parents[1]


def by_id(records, collection, identifier):
    return {getattr(item, identifier): item for item in getattr(records, collection)}


def campsite_context():
    return PlanningContext(
        trip_date=date(2026, 10, 1),
        objectives=(),
        stages=(TripStage(
            "yosemite-camping", 1, "overnight",
            ("scope-yosemite-national-park", "scope-yosemite-developed-campgrounds"),
        ),),
        party=PartyContext(("traveler",)),
        activities=ActivityContext(("camping",), {"overnight": True}),
    )


def test_all_13_developed_campgrounds_have_profiles_and_collection_edges():
    records = load_canonical(ROOT)
    entities = by_id(records, "entities", "entity_id")
    claims = by_id(records, "claims", "claim_id")
    relationships = by_id(records, "relationships", "relationship_id")

    campground_ids = {
        f"campground-yosemite-{slug}" for slug in (
            "upper-pines", "lower-pines", "north-pines", "camp-4", "wawona",
            "bridalveil-creek", "hodgdon-meadow", "crane-flat", "tamarack-flat",
            "white-wolf", "yosemite-creek", "porcupine-flat", "tuolumne-meadows",
        )
    }
    assert campground_ids <= entities.keys()
    assert all(entities[item].kind == "campground" for item in campground_ids)
    assert all(
        relationships[f"relationship-yosemite-developed-campgrounds-contains-{item.removeprefix('campground-yosemite-')}"]
        .object_id == item
        for item in campground_ids
    )
    assert claims["claim-yosemite-upper-pines-site-inventory-2026"].value == {
        "sites": 236,
        "accessible_sites": 10,
    }
    assert claims["claim-yosemite-tuolumne-meadows-reservation-release-2026"].value == (
        "2 months ahead on the 15th and 14 days ahead"
    )


def test_every_currently_open_recreation_site_has_one_profile_and_parent():
    records = load_canonical(ROOT)
    profiles = [item for item in records.claims
                if item.predicate == "recreation_gov_site_profile"
                and item.subject_id.startswith("campsite-recreation-yosemite-")]
    relationships = by_id(records, "relationships", "relationship_id")

    assert len(profiles) == 1435
    assert len({item.subject_id for item in profiles}) == 1435
    assert len({item.value["campsite_id"] for item in profiles}) == 1435
    assert all(item.value["record_status"] == "Open" for item in profiles)
    assert all(item.value["booking_url"].endswith(item.value["campsite_id"])
               for item in profiles)
    assert all(any(
        edge.subject_id == item.subject_id and edge.predicate == "part_of"
        for edge in relationships.values()
    ) for item in profiles)


def test_booking_snapshot_disagreement_is_preserved_not_flattened():
    claims = by_id(load_canonical(ROOT), "claims", "claim_id")
    nps = claims["claim-yosemite-upper-pines-site-inventory-2026"]
    booking = claims["claim-recreation-yosemite-upper-pines-site-inventory-20260922"]

    assert nps.value["sites"] == 236
    assert booking.value["total_records"] == 240
    assert booking.value["public_open_records"] == 235
    assert booking.value["status_counts"] == {
        "Not Available": 2,
        "Not Reservable Management": 3,
        "Open": 235,
    }
    assert booking.temporal_scope.starts_on == date(2026, 9, 22)
    assert booking.temporal_scope.ends_on == date(2026, 9, 22)


def test_site_profiles_keep_coordinates_equipment_accessibility_and_details():
    profiles = [item for item in load_canonical(ROOT).claims
                if item.predicate == "recreation_gov_site_profile"
                and item.subject_id.startswith("campsite-recreation-yosemite-")]
    assert any(item.value["accessible"] for item in profiles)
    assert any(item.value["latitude"] and item.value["longitude"] for item in profiles)
    assert any(item.value["permitted_equipment"] for item in profiles)
    assert any(item.value["details"] for item in profiles)
    assert all(item.temporal_scope.starts_on == date(2026, 9, 22)
               for item in profiles)


def test_horse_and_backcountry_camping_are_not_lost_in_developed_inventory():
    records = load_canonical(ROOT)
    entities = by_id(records, "entities", "entity_id")
    claims = by_id(records, "claims", "claim_id")

    horse_profiles = [item for item in records.claims
                      if item.predicate == "recreation_gov_site_profile"
                      and item.subject_id.startswith("campsite-recreation-yosemite-")
                      and entities[item.subject_id].kind == "equestrian_campsite"]
    assert len(horse_profiles) == 9
    assert len([item for item in entities.values()
                if item.kind == "backcountry_camp"
                and item.entity_id.startswith("backcountry-camp-yosemite-")]) == 6
    assert claims["claim-yosemite-backcountry-campground-policy"].value == {
        "part_of_developed_reservation_system": False,
        "wilderness_permit_required": True,
    }


def test_missed_camping_rules_have_the_correct_official_source_lineage():
    reads = CanonicalReadService(ROOT)
    quiet = reads.explain_claim("claim-yosemite-campground-quiet-hours")
    group = reads.explain_claim("claim-yosemite-campground-group-camping")

    assert quiet.sources[0].locator.endswith("/campregs.htm")
    assert group.sources[0].locator.endswith("/campgrounds.htm")


def test_live_site_selection_remains_a_consumer_visible_recheck():
    reads = CanonicalReadService(ROOT)
    result = reads.pretrip_recheck(campsite_context(), "result-yosemite-pretrip-recheck")
    items = {item.input_id: item for item in result.items}

    assert result.state is RecheckState.REQUIRED
    current = items["claim-yosemite-live-campsite-availability-recheck"]
    assert current.answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    assert current.source_ids == ("source-recreation-yosemite-campground-search",)
    gap = items["gap-yosemite-campground-availability"]
    assert gap.answerability is RecheckAnswerability.UNKNOWN


def test_generated_camping_directory_contains_campgrounds_and_sites(generated_site):
    tmp_path, _ = generated_site
    camping = json.loads((tmp_path / "camping" / "index.json").read_text())
    ids = {item["entity_id"] for item in camping["entities"]}

    assert "campground-yosemite-upper-pines" in ids
    assert any(item.startswith("campsite-recreation-yosemite-") for item in ids)
    assert (tmp_path / "knowledge" / "campground-yosemite-upper-pines" /
            "index.html").exists()


def test_inventory_changeset_is_validated_and_exact():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260922-yosemite-campground-inventory.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 6089
    assert len({item.path for item in change.operations}) == 6089
