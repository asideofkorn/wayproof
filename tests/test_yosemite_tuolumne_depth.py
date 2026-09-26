"""Tuolumne Meadows day-use depth remains source-bounded and publishable."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]

ROUTES = {
    "route-pothole-dome": 1.0,
    "route-parsons-lodge-soda-springs": 1.4,
    "route-twin-bridges-tuolumne": 3.0,
    "route-gaylor-lakes": 2.6,
    "route-dog-lake-lembert-dome": 3.8,
    "route-elizabeth-lake-yosemite": 6.8,
    "route-cathedral-lakes-yosemite": 7.6,
    "route-mono-pass-yosemite": 8.0,
    "route-glen-aulin-day-hike": 11.0,
    "route-young-lakes-day-hike": 13.6,
}

MAPPED_ACCESS = {
    "trailhead-pothole-dome",
    "trailhead-soda-springs-tuolumne",
    "trailhead-dog-lake-tuolumne",
    "trailhead-gaylor-lakes",
    "trailhead-elizabeth-lake-yosemite",
    "trailhead-cathedral-lakes-yosemite",
    "trailhead-mono-parker-pass-yosemite",
    "trailhead-glen-aulin-tuolumne",
    "access-lembert-dome-parking",
    "access-dog-lake-parking",
    "access-cathedral-lakes-visitor-center-parking",
    "access-tuolumne-wilderness-center-parking",
    "access-tioga-pass-entrance",
}


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_published_day_hike_profiles_preserve_nps_distance_and_operational_context():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    relationships = indexed(records, "relationships", "relationship_id")

    for route_id, miles in ROUTES.items():
        claim_id = f"claim-{route_id.removeprefix('route-')}-published-profile"
        value = claims[claim_id].value
        assert value["round_trip_miles"] == miles
        assert value["tioga_road_vehicle_access_required"] is True
        assert value["operational_status_requires_current_check"] is True
        assert any(
            edge.subject_id == route_id and edge.predicate == "starts_at"
            for edge in relationships.values()
        )
        assert any(
            edge.subject_id == route_id and edge.predicate == "reaches"
            for edge in relationships.values()
        )

    assert claims["claim-tuolumne-meadows-day-hike-permit"].value == {
        "required": False,
        "exception": "Half Dome day hike",
        "overnight_permit_required": True,
    }


def test_facility_and_current_status_claims_do_not_turn_map_presence_into_live_status():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    gaps = indexed(records, "gaps", "gap_id")

    center = claims["claim-tuolumne-wilderness-center-profile"].value
    assert "potable water" in center["amenities"]
    assert center["operational_status_requires_current_check"] is True
    assert center["designated_accessible_parking_spaces"] is False

    mono = claims["claim-mono-parker-pass-yosemite-operational-profile"].value
    assert mono["toilet"] == "vault"
    assert mono["drinking_water"] is False

    dated = claims["claim-tuolumne-current-access-20260925"]
    assert dated.temporal_scope.starts_on.isoformat() == "2026-09-25"
    assert dated.temporal_scope.ends_on.isoformat() == "2026-09-25"
    assert dated.value["wilderness_center_to_lembert_trail"] == "closed_for_construction"
    assert dated.value["alternate_trail"] == "available"
    assert "gap-tuolumne-trip-date-operations" in gaps


def test_reviewed_nps_points_publish_to_global_map(generated_site):
    site_root, _ = generated_site
    payload = json.loads((site_root / "map" / "features.geojson").read_text())
    by_entity = {item["properties"]["entity_id"]: item for item in payload["features"]}

    assert MAPPED_ACCESS <= by_entity.keys()
    assert all(by_entity[item]["geometry"]["type"] == "Point" for item in MAPPED_ACCESS)
    assert by_entity["trailhead-gaylor-lakes"]["properties"]["layer"] == "access"
    assert by_entity["facility-tuolumne-wilderness-center"]["properties"]["layer"] == "facilities"

    for route_id in ROUTES:
        page = site_root / "knowledge" / route_id / "index.html"
        assert page.exists()
        assert "National Park Service" in page.read_text()


def test_tuolumne_batch_has_one_validated_changeset_and_explicit_geometry_gap():
    records = load_canonical(ROOT)
    gaps = indexed(records, "gaps", "gap_id")
    gap = gaps["gap-tuolumne-route-segment-topology"]
    assert "route-twin-bridges-tuolumne" in gap.related_ids
    assert "proximity" in gap.reason

    change = load_changeset(
        ROOT / "changesets/v0/wp-20260925-tuolumne-meadows-depth.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert {item.action for item in change.operations} == {
        ChangeAction.ADD,
        ChangeAction.REPLACE,
    }
    assert len(change.operations) == len({item.path for item in change.operations})
