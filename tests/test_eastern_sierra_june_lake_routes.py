"""Yost and Fern retain shared topology, source distances, and uncertainty."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.hike_comparison import DistanceFit
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_yost_and_fern_share_corridor_then_branch():
    records = load_canonical(ROOT)
    relationships = records.relationships
    shared = {
        item.subject_id for item in relationships
        if item.predicate == "part_of" and item.object_id == "route-fern-lake-june"
    } & {
        item.subject_id for item in relationships
        if item.predicate == "part_of" and item.object_id == "route-yost-lake"
    }
    assert shared == {
        "route-segment-yost-fern-shared-01",
        "route-segment-yost-fern-shared-02",
    }
    assert sum(
        item.predicate == "part_of" and item.object_id == "route-fern-lake-june"
        for item in relationships
    ) == 6
    assert sum(
        item.predicate == "part_of" and item.object_id == "route-yost-lake"
        for item in relationships
    ) == 6


def test_published_distance_drives_trip_fit_while_dataset_difference_stays_visible():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    gaps = indexed(records, "gaps", "gap_id")
    assert claims["claim-route-fern-lake-june-published-profile"].value["one_way_miles"] == 2.2
    assert claims["claim-route-yost-lake-published-profile"].value["one_way_miles"] == 3.8
    assert claims["claim-route-yost-lake-dataset-profile"].value["distance_disagreement_preserved"] is True
    assert "does not replace" in gaps["gap-yost-fern-dataset-distance-disagreement"].reason

    comparison = CanonicalReadService(ROOT).compare_hikes(
        ("route-fern-lake-june", "route-yost-lake"), 10,
    )
    by_id = {item.route_id: item for item in comparison.candidates}
    assert by_id["route-fern-lake-june"].round_trip_miles == 4.4
    assert by_id["route-yost-lake"].round_trip_miles == 7.6
    assert {item.distance_fit for item in comparison.candidates} == {DistanceFit.FITS}


def test_generated_pages_include_interactive_route_maps(generated_site):
    site_root, _ = generated_site
    for route_id in ("route-fern-lake-june", "route-yost-lake"):
        page = (site_root / "knowledge" / route_id / "index.html").read_text()
        assert "Interactive evidence-backed route map" in page
        assert "Download generated GeoJSON" in page


def test_one_validated_changeset_accounts_for_june_lake_batch():
    change = load_changeset(ROOT / "changesets/v0/wp-20260924-june-lake-yost-fern-route-depth.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD"}
