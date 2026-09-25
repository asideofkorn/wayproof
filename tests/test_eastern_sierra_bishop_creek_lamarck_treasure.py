"""Lamarck and Treasure Lakes retain connected, source-bounded route depth."""

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


def test_lamarck_and_treasure_routes_traverse_both_directions():
    reads = CanonicalReadService(ROOT)
    expectations = (
        ("route-lamarck-lakes", "trailhead-north-lake-bishop", "place-upper-lamarck-lake", 6),
        ("route-treasure-lakes", "trailhead-south-lake-bishop", "place-treasure-lakes-bishop-creek", 4),
    )
    for route_id, start_id, end_id, segment_count in expectations:
        route = reads.entity(route_id)
        start = reads.entity(start_id)
        end = reads.entity(end_id)
        forward = resolve_traversal(reads, route, start, end, date(2026, 10, 1))
        reverse = resolve_traversal(reads, route, end, start, date(2026, 10, 1))
        assert forward.state.value == reverse.state.value == "complete"
        assert len(forward.legs) == len(reverse.legs) == segment_count
        assert [leg.segment_id for leg in reverse.legs] == [
            leg.segment_id for leg in reversed(forward.legs)
        ]
        assert reads.route_geometry(route_id, date(2026, 10, 1)) is not None


def test_routes_now_have_bounded_under_ten_mile_results():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    gaps = indexed(records, "gaps", "gap_id")
    comparison = CanonicalReadService(ROOT).compare_hikes(
        ("route-lamarck-lakes", "route-treasure-lakes"), 10,
    )
    by_id = {item.route_id: item for item in comparison.candidates}

    assert claims["claim-route-lamarck-lakes-dataset-profile"].value[
        "one_way_distance_miles"
    ] == 2.5316595
    assert claims["claim-route-treasure-lakes-dataset-profile"].value[
        "one_way_distance_miles"
    ] == 3.42474871
    assert by_id["route-lamarck-lakes"].round_trip_miles == 5.063319
    assert by_id["route-treasure-lakes"].round_trip_miles == 6.84949742
    assert {item.distance_fit for item in comparison.candidates} == {DistanceFit.FITS}
    assert "gap-bishop-creek-day-hike-distances" not in gaps


def test_shared_piute_prefix_and_named_destinations_remain_explicit():
    records = load_canonical(ROOT)
    relationships = {
        (item.subject_id, item.predicate, item.object_id)
        for item in records.relationships
    }
    assert (
        "route-segment-piute-pass-01", "part_of", "route-lamarck-lakes",
    ) in relationships
    assert (
        "route-lamarck-lakes", "passes", "place-lower-lamarck-lake",
    ) in relationships
    assert (
        "route-treasure-lakes", "ends_at", "place-treasure-lakes-bishop-creek",
    ) in relationships


def test_routes_publish_interactive_maps(generated_site):
    site_root, _ = generated_site
    for route_id, destination in (
        ("route-lamarck-lakes", "Upper Lamarck Lake"),
        ("route-treasure-lakes", "Treasure Lakes (Bishop Creek)"),
    ):
        page = (site_root / "knowledge" / route_id / "index.html").read_text()
        assert "Interactive evidence-backed route map" in page
        assert destination in page


def test_one_validated_changeset_accounts_for_batch():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260925-bishop-creek-lamarck-treasure-depth.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert {item.action for item in change.operations} == {
        ChangeAction.ADD, ChangeAction.REMOVE,
    }
    assert len(change.operations) == len({item.path for item in change.operations})
