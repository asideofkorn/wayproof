"""Outcome contracts for Contra Loma and Quarry Lakes water recreation."""

from pathlib import Path

from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


def test_quarry_lakes_waterbodies_keep_distinct_conditions_and_rules():
    reads = CanonicalReadService(ROOT)
    expected = {
        "waterbody-quarry-horseshoe-lake": "danger_advisory",
        "waterbody-quarry-rainbow-lake": "caution_advisory",
        "waterbody-quarry-shinn-pond": "caution_advisory",
        "waterbody-quarry-lago-los-osos": "caution_advisory",
    }
    for entity_id, status in expected.items():
        claims = [
            claim for claim in reads.claims_for(entity_id)
            if claim.predicate == "water_quality_status"
        ]
        assert len(claims) == 1
        assert claims[0].value["status"] == status
        assert claims[0].value["water_contact_rule"]


def test_contra_loma_water_contact_rules_are_equipment_specific():
    reads = CanonicalReadService(ROOT)
    claim = next(
        claim for claim in reads.claims_for("park-contra-loma-regional-park")
        if claim.claim_id == "claim-contra-loma-water-contact-rules"
    )
    assert claim.value["windsurfers_and_paddleboarders"]["pre_entry_shower_minutes"] == 2
    assert claim.value["float_tubes"]["waders_or_wetsuit_required"] is True
    assert claim.value["dry_kayaks"]["rollovers_or_body_contact_activity_permitted"] is False


def test_quarry_access_facilities_have_coordinates_and_park_relationships():
    reads = CanonicalReadService(ROOT)
    expected = {
        "facility-quarry-niles-beach",
        "facility-quarry-boat-launch",
        "facility-quarry-ada-fishing-pier",
        "entrance-quarry-alameda-creek-west-walk-in",
        "entrance-quarry-alameda-creek-east-walk-in",
    }
    for entity_id in expected:
        profile = next(
            claim for claim in reads.claims_for(entity_id)
            if claim.predicate == "access_profile"
        )
        assert 37 < profile.value["latitude"] < 38
        assert -123 < profile.value["longitude"] < -121
        assert any(
            edge.object_id == "park-quarry-lakes-regional-recreation-area"
            for edge in reads.relationships_for(entity_id)
        )


def test_contra_loma_route_connection_to_black_diamond_is_explicit():
    reads = CanonicalReadService(ROOT)
    assert any(
        edge.predicate == "trail_connects_to"
        and edge.object_id == "park-black-diamond-mines-regional-preserve"
        for edge in reads.relationships_for("park-contra-loma-regional-park")
    )
