"""Regression checks for the complete Sunol ReserveAmerica site corpus."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus

ROOT = Path(__file__).resolve().parents[1]


def records():
    return load_canonical(ROOT)


def profiles():
    return [item for item in records().claims
            if item.predicate == "reserveamerica_site_profile"
            and item.value.get("booking_url", "").startswith(
                "https://www.reserveamerica.com/explore/sunol/EB/110028/")]


def test_all_19_live_site_pages_have_profiles_and_provenance():
    snapshot = records()
    items = profiles()
    assert len(items) == 19
    assert len({item.subject_id for item in items}) == 19
    assert len({item.value["product_id"] for item in items}) == 19
    evidence = {item.evidence_id: item for item in snapshot.evidence}
    observations = {item.observation_id: item for item in snapshot.observations}
    source_ids = {item.source_id for item in snapshot.sources}
    for item in items:
        assert len(item.evidence_ids) == 1
        assert observations[evidence[item.evidence_ids[0]].observation_id].source_id in source_ids


def test_inventory_spans_three_geographic_loops():
    inventory = next(item for item in records().claims
                     if item.claim_id == "claim-reserveamerica-sunol-campsites-inventory")
    assert inventory.value["total_sites"] == 19
    assert inventory.value["loops"] == {
        "Mission Peak Backpack": 4,
        "Ohlone Backpack": 8,
        "Sunol Backpack": 7,
    }
    assert {item.value["loop"] for item in profiles()} == set(
        inventory.value["loops"])


def test_booking_facility_is_not_misidentified_as_sunol_backpack_camp():
    profile = next(item for item in records().claims
                   if item.claim_id == "claim-reserveamerica-sunol-backpack-facility")
    assert profile.subject_id == "facility-reserveamerica-sunol-eb-110028"
    assert profile.spatial_scope_ids == ("scope-reserveamerica-sunol-eb-110028",)


def test_site_parent_relationships_reuse_existing_camp_entities():
    snapshot = records()
    rels = [item for item in snapshot.relationships
            if item.relationship_id.startswith(
                "relationship-reserveamerica-sunol-site-")]
    assert len(rels) == 19
    counts = {}
    for item in rels:
        counts[item.object_id] = counts.get(item.object_id, 0) + 1
    assert counts == {
        "camp-ohlone-map-eagle-spring": 4,
        "camp-ohlone-map-boyd": 2,
        "camp-ohlone-map-doe-canyon-horse": 2,
        "camp-ohlone-map-maggies-half-acre": 3,
        "camp-ohlone-map-stewarts": 1,
        "camp-ohlone-map-sunol-backpack": 7,
    }


def test_source_omissions_are_preserved_as_gaps_not_inferences():
    items = profiles()
    assert all(item.value["latitude"] is None
               and item.value["longitude"] is None for item in items)
    eagle = [item for item in items
             if item.value["loop"] == "Mission Peak Backpack"]
    assert len(eagle) == 4
    assert all("shade_or_tree_cover" not in item.value["details"]
               for item in eagle)
    gap_ids = {item.gap_id for item in records().gaps}
    assert "gap-reserveamerica-sunol-site-water-restroom-proximity" in gap_ids
    assert "gap-reserveamerica-sunol-site-coordinates" in gap_ids
    assert "gap-reserveamerica-eagle-springs-site-shade" in gap_ids


def test_site_detail_changeset_is_validated_and_complete():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-reserveamerica-sunol-site-details.json")
    assert change.status is ChangeSetStatus.VALIDATED
    counts = {action: sum(item.action.value == action
                          for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 124, "REPLACE": 1, "REMOVE": 0}
