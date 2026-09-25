"""McGee and Lundy preserve full corridors and bounded turnaround options."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.hike_comparison import DistanceFit
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_mcgee_full_corridor_is_not_truncated_by_trip_limit():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    value = claims["claim-route-mcgee-creek-dataset-profile"].value

    assert value["one_way_distance_miles"] > 14
    segments = [
        item for item in records.entities
        if item.kind == "route_segment" and item.entity_id.startswith("route-segment-mcgee-pass-")
    ]
    assert len(segments) == 16

    comparison = CanonicalReadService(ROOT).compare_hikes((
        "route-mcgee-creek-beaver-pond", "route-mcgee-creek",
    ), 10)
    by_id = {item.route_id: item for item in comparison.candidates}
    assert by_id["route-mcgee-creek-beaver-pond"].round_trip_miles == 6
    assert by_id["route-mcgee-creek-beaver-pond"].distance_fit is DistanceFit.FITS
    assert by_id["route-mcgee-creek"].distance_fit is DistanceFit.EXCEEDS


def test_lundy_turnaround_preserves_published_approximation_and_extension():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    value = claims["claim-route-lundy-canyon-waterfall-beaver-dam-profile"].value

    assert value["published_distance_miles"] == 3
    assert value["distance_precision"] == "about"
    assert value["route_shape"] == "out_and_back"
    assert value["features"] == ["waterfall", "beaver dam"]
    assert "20 Lakes Basin" in value["extension_destinations"]


def test_turnarounds_are_evidenced_routes_but_unproven_junctions_remain_gaps():
    records = load_canonical(ROOT)
    relationships = records.relationships
    gaps = indexed(records, "gaps", "gap_id")

    accessed = {(item.subject_id, item.object_id) for item in relationships if item.predicate == "accesses"}
    assert ("trailhead-mcgee-creek", "route-mcgee-creek-beaver-pond") in accessed
    assert ("trailhead-lundy-canyon", "route-lundy-canyon-waterfall-beaver-dam") in accessed
    assert "does not publish a coordinate" in gaps["gap-mcgee-creek-day-hike-distance"].reason
    assert "does not publish an exact turnaround" in gaps["gap-lundy-canyon-sub-ten-turnaround"].reason


def test_site_publishes_full_and_turnaround_routes(generated_site):
    site_root, _ = generated_site
    for route_id in (
        "route-mcgee-creek", "route-mcgee-creek-beaver-pond",
        "route-lundy-canyon", "route-lundy-canyon-waterfall-beaver-dam",
    ):
        assert (site_root / "knowledge" / route_id / "index.html").exists()

    full_page = (site_root / "knowledge" / "route-mcgee-creek" / "index.html").read_text()
    assert "Interactive evidence-backed route map" in full_page
    short_page = (site_root / "knowledge" / "route-mcgee-creek-beaver-pond" / "index.html").read_text()
    assert "McGee Creek Beaver Pond" in short_page


def test_one_validated_changeset_accounts_for_batch():
    change = load_changeset(ROOT / "changesets/v0/wp-20260925-eastern-sierra-turnaround-options.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {item.action for item in change.operations} == {ChangeAction.ADD, ChangeAction.REPLACE}
    assert len(change.operations) == len({item.path for item in change.operations})
