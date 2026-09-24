"""Eastern Sierra foliage alternatives retain source precision and gaps."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_published_distances_and_convict_hazard_remain_explicit():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")

    parker = claims["claim-parker-lake-route-profile"].value
    assert parker["one_way_miles"] == 1.8
    assert parker["round_trip_miles"] == 3.6

    yost_fern = claims["claim-yost-fern-route-profile"].value
    assert yost_fern["fern_total_one_way_miles"] == 2.2
    assert yost_fern["yost_total_one_way_miles"] == 3.8

    convict = claims["claim-convict-canyon-route-profile"].value
    assert convict["hazardous_stream_crossing_within_miles"] == 3
    assert convict["destinations_one_way_miles"] == {
        "Dorothy Lake": 6, "Mildred Lake": 5,
    }


def test_every_candidate_route_has_evidenced_trailhead_access():
    records = load_canonical(ROOT)
    relationships = records.relationships
    routes = {
        "route-mcgee-creek", "route-convict-canyon", "route-parker-lake",
        "route-fern-lake-june", "route-yost-lake", "route-lundy-canyon",
        "route-crystal-lake-mammoth", "route-heart-lake-mammoth",
        "route-mcleod-lake", "route-sabrina-blue-lake", "route-piute-pass",
        "route-lamarck-lakes", "route-treasure-lakes", "route-virginia-lakes",
    }
    accessed = {
        item.object_id for item in relationships if item.predicate == "accesses"
        and item.subject_id.startswith("trailhead-") and item.evidence_ids
    }
    assert routes <= accessed


def test_unknown_details_are_gaps_not_invented_route_segments():
    records = load_canonical(ROOT)
    gaps = indexed(records, "gaps", "gap_id")
    entities = indexed(records, "entities", "entity_id")

    assert "does not publish" in gaps["gap-mcgee-creek-day-hike-distance"].reason
    assert "does not infer distances" in gaps[
        "gap-mammoth-lakes-basin-route-distances"
    ].reason
    assert "exceeds" in gaps["gap-lundy-canyon-sub-ten-turnaround"].reason
    assert not any(
        item.kind == "route_segment" and any(
            word in item.entity_id for word in ("mcgee", "lundy", "virginia")
        ) for item in entities.values()
    )


def test_management_boundary_is_not_flattened():
    records = load_canonical(ROOT)
    relationships = records.relationships
    manages = {
        (item.subject_id, item.object_id) for item in relationships
        if item.predicate == "manages"
    }
    assert ("agency-humboldt-toiyabe-national-forest", "trailhead-virginia-lakes") in manages
    assert ("agency-inyo-national-forest", "route-lundy-canyon") in manages
    assert ("agency-inyo-national-forest", "wilderness-john-muir") in manages
    assert ("agency-inyo-national-forest", "wilderness-ansel-adams") in manages
    assert ("agency-inyo-national-forest", "place-mammoth-lakes-basin") in manages
    assert ("agency-inyo-national-forest", "place-bishop-creek-canyon") in manages


def test_routes_retain_their_distinct_wilderness_context():
    records = load_canonical(ROOT)
    traverses = {
        (item.subject_id, item.object_id) for item in records.relationships
        if item.predicate == "traverses"
    }
    assert ("route-mcgee-creek", "wilderness-john-muir") in traverses
    assert ("route-convict-canyon", "wilderness-john-muir") in traverses
    assert ("route-treasure-lakes", "wilderness-john-muir") in traverses
    assert ("route-parker-lake", "wilderness-ansel-adams") in traverses
    assert ("route-yost-lake", "wilderness-ansel-adams") in traverses
    assert ("route-lundy-canyon", "wilderness-hoover") in traverses
    assert ("route-virginia-lakes", "wilderness-hoover") in traverses


def test_read_service_and_generated_site_expose_candidates(tmp_path):
    reads = CanonicalReadService(ROOT)
    assert reads.search_entities("Parker Lake", kinds=("route",))[0].entity_id == "route-parker-lake"
    assert reads.knowledge_gaps_for("route-virginia-lakes")

    from scripts import build_site

    build_site.build(tmp_path)
    trails = json.loads((tmp_path / "trails" / "index.json").read_text())
    trail_ids = {item["entity_id"] for item in trails["entities"]}
    assert {"route-parker-lake", "route-lundy-canyon", "route-sabrina-blue-lake"} <= trail_ids
    assert (tmp_path / "knowledge" / "trailhead-convict-lake" / "index.html").exists()
    assert (tmp_path / "knowledge" / "wilderness-ansel-adams" / "index.html").exists()
    page = (tmp_path / "knowledge" / "route-convict-canyon" / "index.html").read_text()
    assert "Hazardous stream crossing within miles" in page


def test_one_validated_changeset_accounts_for_batch():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260923-eastern-sierra-foliage-hikes.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD"}
