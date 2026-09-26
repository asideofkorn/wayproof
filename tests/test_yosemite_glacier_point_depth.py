"""Glacier Point Road depth preserves operational and topology limits."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus

ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "route-glacier-point-overlook", "route-mcgurk-meadow", "route-sentinel-dome",
    "route-taft-point", "route-sentinel-dome-taft-point-loop", "route-mono-meadow",
    "route-dewey-point", "route-ostrander-lake", "route-panorama-trail",
    "route-pohono-glacier-point-to-tunnel-view",
}


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_glacier_point_routes_have_evidence_starts_objectives_and_topology_gap():
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
    assert set(gaps["gap-yosemite-glacier-point-route-topology"].related_ids) == ROUTES


def test_access_vehicle_and_dated_closure_profiles_are_preserved():
    claims = indexed(load_canonical(ROOT), "claims", "claim_id")
    access = claims["claim-glacier-point-road-access-profile"].value
    assert access["valley_shuttle"] is False
    assert access["operational_status_requires_current_check"] is True
    vehicle = claims["claim-glacier-point-road-vehicle-profile"].value
    assert vehicle["beyond_sentinel_taft_max_single_vehicle_ft"] == 30
    assert vehicle["trailers_beyond_sentinel_taft"] is False
    closure = claims["claim-glacier-point-road-observed-status-20260925"].value
    assert closure["status"] == "temporarily closed"
    assert closure["as_of"] == "2026-09-25"
    assert closure["recheck_required"] is True


def test_map_points_and_pages_publish(generated_site):
    site_root, _ = generated_site
    payload = json.loads((site_root / "map" / "features.geojson").read_text())
    by_entity = {item["properties"]["entity_id"] for item in payload["features"]}
    assert {"trailhead-sentinel-dome-taft-point", "trailhead-ostrander-lake", "access-glacier-point-parking", "facility-sentinel-taft-vault-toilet"} <= by_entity
    for entity_id in ROUTES | {"place-glacier-point-road-corridor"}:
        page = site_root / "knowledge" / entity_id / "index.html"
        assert page.exists()
        assert "National Park Service" in page.read_text()


def test_batch_has_one_validated_add_only_changeset():
    change = load_changeset(ROOT / "changesets/v0/wp-20260925-yosemite-glacier-point-depth.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {operation.action for operation in change.operations} == {ChangeAction.ADD}
    assert len(change.operations) == len({operation.path for operation in change.operations})
