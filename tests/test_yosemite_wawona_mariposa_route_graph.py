"""Wawona and Mariposa Grove trail features publish as bounded route graphs."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]
ROUTES = {
    "route-wawona-meadow-loop",
    "route-swinging-bridge-wawona",
    "route-alder-creek-wawona",
    "route-mariposa-big-trees-loop",
    "route-mariposa-grizzly-giant-loop",
    "route-mariposa-guardians-loop",
    "route-washburn-trail-mariposa-access",
    "route-mariposa-grove-road-walking-access",
}
ALL_ROUTES = ROUTES | {
    "route-chilnualna-falls",
    "route-mariposa-grove-to-wawona-point",
}


def test_every_reviewed_segment_has_endpoints_membership_and_dataset_claim():
    records = load_canonical(ROOT)
    relationships = records.relationships
    segment_ids = {
        entity.entity_id
        for entity in records.entities
        if entity.entity_id.startswith("route-segment-yosemite-wawona-mariposa-nps-")
    }
    assert len(segment_ids) == 30
    for segment_id in segment_ids:
        outgoing = [item for item in relationships if item.subject_id == segment_id]
        assert len([item for item in outgoing if item.predicate == "starts_at"]) == 1
        assert len([item for item in outgoing if item.predicate == "ends_at"]) == 1
        membership = [item.object_id for item in outgoing if item.predicate == "part_of"]
        assert len(membership) == 1
        assert membership[0] in ROUTES
        claims = [item for item in records.claims if item.subject_id == segment_id]
        assert len(claims) == 1
        assert claims[0].predicate == "official_dataset_route_segment"


def test_snapshot_contains_only_reviewed_unbranched_named_chains():
    snapshot = json.loads(
        (ROOT / "geometry/v0/snapshots/nps-yose-wawona-mariposa-route-features-20260926.geojson").read_text()
    )
    assert len(snapshot["features"]) == 30
    assert {item["properties"]["route_id"] for item in snapshot["features"]} == ROUTES


def test_each_published_route_has_one_exact_endpoint_ordered_geometry_claim():
    records = load_canonical(ROOT)
    for route_id in ROUTES:
        claims = [
            item for item in records.claims
            if item.subject_id == route_id and item.predicate == "ordered_route_geometry"
        ]
        assert len(claims) == 1
        segment_ids = claims[0].value["segment_ids"]
        assert segment_ids
        assert claims[0].value["start_node_id"].startswith("route-node-yosemite-wawona-mariposa-")


def test_physical_endpoint_work_remains_explicit_not_proximity_inferred():
    records = load_canonical(ROOT)
    gap = next(item for item in records.gaps if item.gap_id == "gap-yosemite-wawona-mariposa-route-topology")
    assert set(ALL_ROUTES).issubset(gap.related_ids)
    assert "proximity is not used" in gap.reason
    assert "Chilnualna Falls" in gap.reason


def test_all_reviewed_routes_publish_interactive_maps(generated_site):
    site_root, _ = generated_site
    for route_id in ROUTES:
        page = (site_root / "knowledge" / route_id / "index.html").read_text()
        assert "Download generated GeoJSON" in page
        assert "Interactive map" in page


def test_wawona_mariposa_graph_is_one_validated_changeset():
    change = load_changeset(ROOT / "changesets/v0/wp-20260926-yosemite-wawona-mariposa-route-graph.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {item.action for item in change.operations} == {ChangeAction.ADD, ChangeAction.REPLACE}
    assert len(change.operations) == len({item.path for item in change.operations})
