"""Contracts for location-specific volatile EBRPD water status."""

from pathlib import Path

from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


def _status(reads, entity_id):
    return next(
        claim for claim in reads.claims_for(entity_id)
        if claim.predicate == "water_quality_status"
        and claim.value.get("as_of_retrieval") == "2026-09-22"
    )


def test_each_monitored_location_has_its_own_volatile_status():
    reads = CanonicalReadService(ROOT)
    expected = {
        "beach-crown": "no_advisory_posted",
        "beach-keller": "water_advisory",
        "waterbody-tilden-lake-anza": "no_advisory_posted",
        "waterbody-martinez-shoreline": "danger_advisory",
        "reservoir-lake-chabot": "caution_advisory",
        "waterbody-shadow-cliffs-lake": "caution_advisory",
        "waterbody-shadow-cliffs-arroyo": "no_advisory_posted",
        "waterbody-lake-temescal": "caution_advisory",
        "waterbody-big-break-shoreline": "danger_advisory",
        "reservoir-contra-loma": "no_advisory_posted",
    }
    for entity_id, status in expected.items():
        claim = _status(reads, entity_id)
        assert claim.value["status"] == status
        assert claim.value["volatile"] is True


def test_shadow_cliffs_lake_and_arroyo_are_not_collapsed():
    reads = CanonicalReadService(ROOT)
    assert _status(reads, "waterbody-shadow-cliffs-lake").value["status"] == "caution_advisory"
    assert _status(reads, "waterbody-shadow-cliffs-arroyo").value["status"] == "no_advisory_posted"


def test_every_new_water_location_is_related_to_its_park():
    reads = CanonicalReadService(ROOT)
    new_entities = {
        "beach-crown", "beach-keller", "waterbody-tilden-lake-anza",
        "waterbody-martinez-shoreline", "reservoir-lake-chabot",
        "waterbody-shadow-cliffs-lake", "waterbody-shadow-cliffs-arroyo",
        "waterbody-lake-temescal", "waterbody-big-break-shoreline",
    }
    for entity_id in new_entities:
        assert any(
            edge.predicate == "located_in"
            for edge in reads.relationships_for(entity_id)
        )
