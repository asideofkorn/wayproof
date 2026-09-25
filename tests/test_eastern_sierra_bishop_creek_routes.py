"""Bishop Creek route depth supports Blue Lake and Piute Pass planning."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.hike_comparison import DistanceFit
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeAction, ChangeSetStatus
from wayproof.traversal import resolve_traversal


ROOT = Path(__file__).resolve().parents[1]


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_blue_lake_and_piute_pass_have_connected_bidirectional_geometry():
    reads = CanonicalReadService(ROOT)
    for route_id, expected_segments in (
        ("route-sabrina-blue-lake", 4), ("route-piute-pass", 3),
    ):
        route = reads.entity(route_id)
        starts = next(
            item.object_id for item in reads.relationships_for(route_id)
            if item.subject_id == route_id and item.predicate == "starts_at"
        )
        ends = next(
            item.object_id for item in reads.relationships_for(route_id)
            if item.subject_id == route_id and item.predicate == "ends_at"
        )
        forward = resolve_traversal(
            reads, route, reads.entity(starts), reads.entity(ends), date(2026, 10, 1),
        )
        reverse = resolve_traversal(
            reads, route, reads.entity(ends), reads.entity(starts), date(2026, 10, 1),
        )
        assert forward.state.value == reverse.state.value == "complete"
        assert len(forward.legs) == len(reverse.legs) == expected_segments
        assert [leg.segment_id for leg in reverse.legs] == [
            leg.segment_id for leg in reversed(forward.legs)
        ]
        assert reads.route_geometry(route_id, date(2026, 10, 1)) is not None


def test_trip_limit_distinguishes_trail_from_north_lake_parking_approach():
    records = load_canonical(ROOT)
    results = indexed(records, "derived_results", "result_id")
    piute = results["result-route-piute-pass-ten-mile-day-hike-fit"].value
    assert piute["trail_only_fits_distance_limit"] is True
    assert piute["parking_inclusive_fits_distance_limit"] is False
    assert piute["parking_approach_round_trip_miles"] == 1.0

    comparison = CanonicalReadService(ROOT).compare_hikes(
        ("route-sabrina-blue-lake", "route-piute-pass"), 10,
    )
    by_id = {item.route_id: item for item in comparison.candidates}
    assert by_id["route-sabrina-blue-lake"].distance_fit is DistanceFit.FITS
    assert by_id["route-piute-pass"].distance_fit is DistanceFit.FITS
    assert by_id["route-sabrina-blue-lake"].round_trip_miles < 10
    assert by_id["route-piute-pass"].round_trip_miles < 10


def test_parking_and_named_endpoints_are_evidenced_not_proximity_inferred():
    records = load_canonical(ROOT)
    relationships = records.relationships
    links = {(item.subject_id, item.predicate, item.object_id) for item in relationships}
    assert (
        "access-north-lake-hiker-parking", "provides_access_to",
        "trailhead-north-lake-bishop",
    ) in links
    assert ("route-piute-pass", "ends_at", "place-piute-pass") in links
    claims = indexed(records, "claims", "claim_id")
    assert claims["claim-blue-lake-sabrina-geographic-reference"].value[
        "geometry_role"
    ] == "named_feature_reference_point"


def test_site_publishes_both_interactive_route_maps(generated_site):
    site_root, _ = generated_site
    for route_id in ("route-sabrina-blue-lake", "route-piute-pass"):
        page = (site_root / "knowledge" / route_id / "index.html").read_text()
        assert "Interactive evidence-backed route map" in page
        assert "Download generated GeoJSON" in page


def test_batch_narrows_but_does_not_erase_unresolved_bishop_creek_work():
    records = load_canonical(ROOT)
    gaps = indexed(records, "gaps", "gap_id")
    gap = gaps["gap-bishop-creek-day-hike-distances"]
    assert gap.related_ids == ("route-lamarck-lakes", "route-treasure-lakes")

    change = load_changeset(ROOT / "changesets/v0/wp-20260924-bishop-creek-route-depth.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert {item.action for item in change.operations} == {
        ChangeAction.ADD, ChangeAction.REPLACE,
    }
    assert len(change.operations) == len({item.path for item in change.operations})
