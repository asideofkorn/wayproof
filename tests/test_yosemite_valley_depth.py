"""Yosemite Valley depth remains source-bounded and useful to consumers."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]

ROUTES = {
    "route-bridalveil-fall",
    "route-lower-yosemite-fall",
    "route-yosemite-valley-loop",
    "route-mirror-lake",
    "route-four-mile-trail",
    "route-upper-yosemite-fall",
    "route-vernal-nevada-falls",
    "route-half-dome-day-hike",
    "route-little-yosemite-valley",
    "route-snow-creek",
    "route-eagle-peak-yosemite",
    "route-el-capitan-yosemite-valley",
    "route-jmt-yosemite-valley-to-tuolumne",
    "route-yosemite-full-north-rim",
    "route-yosemite-eastern-north-rim",
}


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_valley_routes_have_sourced_starts_objectives_and_explicit_topology_limit():
    records = load_canonical(ROOT)
    entities = indexed(records, "entities", "entity_id")
    claims = indexed(records, "claims", "claim_id")
    relationships = indexed(records, "relationships", "relationship_id")
    gaps = indexed(records, "gaps", "gap_id")

    assert ROUTES <= entities.keys()
    for route_id in ROUTES:
        profile_id = f"claim-{route_id.removeprefix('route-')}-published-profile"
        assert claims[profile_id].evidence_ids
        assert claims[profile_id].value["operational_status_requires_current_check"] is True
        assert any(edge.subject_id == route_id and edge.predicate == "starts_at" for edge in relationships.values())
        assert any(edge.subject_id == route_id and edge.predicate == "reaches" for edge in relationships.values())

    assert set(gaps["gap-yosemite-valley-route-segment-topology"].related_ids) >= ROUTES


def test_valley_access_preserves_parking_and_distance_uncertainty():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    gaps = indexed(records, "gaps", "gap_id")

    parking = claims["claim-yosemite-valley-trailhead-parking-profile"].value
    assert parking["location"] == "just beyond Curry Village"
    assert parking["happy_isles_walking_distance_miles"] == 0.5
    assert parking["capacity"] == "not_published"

    restriction = claims["claim-happy-isles-mirror-lake-parking-restriction"].value
    assert restriction["parking_unavailable_at"] == ["trailhead-happy-isles", "trailhead-mirror-lake"]

    falls = claims["claim-upper-yosemite-fall-published-profile"].value
    assert falls["round_trip_miles"] == 7.2
    assert falls["alternate_current_nps_miles"] == 7.4
    assert falls["distance_conflict_preserved"] is True
    assert "gap-yosemite-valley-yosemite-falls-distance-conflict" in gaps


def test_reviewed_valley_points_and_pages_publish(generated_site):
    site_root, _ = generated_site
    payload = json.loads((site_root / "map" / "features.geojson").read_text())
    by_entity = {item["properties"]["entity_id"]: item for item in payload["features"]}

    expected = {
        "trailhead-happy-isles",
        "trailhead-mirror-lake",
        "trailhead-four-mile-yosemite-valley",
        "access-bridalveil-fall-parking",
        "facility-happy-isles-restroom",
    }
    assert expected <= by_entity.keys()
    assert all(by_entity[item]["geometry"]["type"] == "Point" for item in expected)

    for route_id in ROUTES:
        page = site_root / "knowledge" / route_id / "index.html"
        assert page.exists()
        html = page.read_text()
        assert "National Park Service" in html
        assert "Evidence and sources" in html


def test_valley_batch_has_one_validated_changeset():
    change = load_changeset(ROOT / "changesets/v0/wp-20260925-yosemite-valley-depth.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {operation.action for operation in change.operations} == {ChangeAction.ADD}
    assert len(change.operations) == len({operation.path for operation in change.operations})
