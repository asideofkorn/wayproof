"""Wawona and Mariposa Grove depth remains source-bounded and useful."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "route-wawona-meadow-loop",
    "route-swinging-bridge-wawona",
    "route-chilnualna-falls",
    "route-alder-creek-wawona",
    "route-mariposa-big-trees-loop",
    "route-mariposa-grizzly-giant-loop",
    "route-mariposa-guardians-loop",
    "route-mariposa-grove-to-wawona-point",
    "route-washburn-trail-mariposa-access",
    "route-mariposa-grove-road-walking-access",
}


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_routes_have_sourced_starts_objectives_and_visible_topology_gap():
    records = load_canonical(ROOT)
    entities = indexed(records, "entities", "entity_id")
    claims = indexed(records, "claims", "claim_id")
    relationships = indexed(records, "relationships", "relationship_id")
    gaps = indexed(records, "gaps", "gap_id")

    assert ROUTES <= entities.keys()
    for route_id in ROUTES:
        profile = claims[f"claim-{route_id.removeprefix('route-')}-published-profile"]
        assert profile.evidence_ids
        assert profile.value["operational_status_requires_current_check"] is True
        assert any(edge.subject_id == route_id and edge.predicate == "starts_at" for edge in relationships.values())
        assert any(edge.subject_id == route_id and edge.predicate == "reaches" for edge in relationships.values())
    assert set(gaps["gap-yosemite-wawona-mariposa-route-topology"].related_ids) == ROUTES


def test_access_facilities_distance_disagreement_and_closure_are_preserved():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")

    access = claims["claim-mariposa-grove-access-profile-2026"].value
    assert access["welcome_plaza_parking_spaces_approx"] == 300
    assert access["shuttle_frequency_minutes_approx"] == 15
    assert access["private_vehicle_access"].startswith("Mariposa Grove Road is limited")

    facilities = claims["claim-mariposa-grove-facility-profile"].value
    assert facilities["drinking_water"]["welcome_plaza"] == "year-round"
    assert facilities["drinking_water"]["arrival_area"] == "summer only"
    assert facilities["food_service"] is False

    wawona_point = claims["claim-mariposa-grove-to-wawona-point-published-profile"].value
    assert wawona_point["round_trip_miles"] == 7.0
    assert wawona_point["alternate_nps_hikes_page_round_trip_miles"] == 7.75
    assert wawona_point["distance_conflict_preserved"] is True

    closure = claims["claim-chilnualna-falls-observed-closure-20260925"].value
    assert closure == {
        "status": "closed",
        "as_of": "2026-09-25",
        "reason": "Dome Fire",
        "also_applies_to": "trails from the top toward Buena Vista and Crescent Lakes",
        "recheck_required": True,
    }


def test_reviewed_points_and_human_pages_publish(generated_site):
    site_root, _ = generated_site
    payload = json.loads((site_root / "map" / "features.geojson").read_text())
    by_entity = {item["properties"]["entity_id"]: item for item in payload["features"]}
    expected = {
        "trailhead-chilnualna-falls",
        "trailhead-mariposa-grove-arrival",
        "access-mariposa-grove-welcome-plaza",
        "facility-mariposa-welcome-water",
        "facility-grizzly-giant-vault-toilet",
    }
    assert expected <= by_entity.keys()
    assert all(by_entity[item]["geometry"]["type"] == "Point" for item in expected)
    for entity_id in ROUTES | {"place-wawona", "place-mariposa-grove"}:
        page = site_root / "knowledge" / entity_id / "index.html"
        assert page.exists()
        html = page.read_text()
        assert "National Park Service" in html
        assert "Evidence and sources" in html


def test_batch_has_one_validated_add_only_changeset():
    change = load_changeset(ROOT / "changesets/v0/wp-20260925-yosemite-wawona-mariposa-depth.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {operation.action for operation in change.operations} == {ChangeAction.ADD}
    assert len(change.operations) == len({operation.path for operation in change.operations})
