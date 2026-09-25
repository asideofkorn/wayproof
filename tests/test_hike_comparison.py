"""Hike comparison preserves distance provenance and unknowns."""

from pathlib import Path

import pytest

from wayproof.hike_comparison import DistanceFit
from wayproof.mcp_server import WayproofReadTools
from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


def test_east_fork_hike_candidates_compare_against_ten_mile_cap():
    reads = CanonicalReadService(ROOT)
    comparison = reads.compare_hikes((
        "route-little-lakes-valley",
        "route-hilton-lakes-rock-creek",
        "route-tamarack-lakes-rock-creek",
        "route-parker-lake",
        "route-heart-lake-mammoth",
        "route-convict-lake-loop",
        "route-mcgee-creek-beaver-pond",
        "route-mcgee-creek",
        "route-lundy-canyon-waterfall-beaver-dam",
        "route-lundy-canyon",
    ), 10)
    by_id = {item.route_id: item for item in comparison.candidates}

    assert by_id["route-convict-lake-loop"].round_trip_miles == 2
    assert by_id["route-parker-lake"].distance_fit is DistanceFit.FITS
    assert by_id["route-little-lakes-valley"].distance_fit is DistanceFit.FITS
    assert by_id["route-tamarack-lakes-rock-creek"].distance_fit is DistanceFit.EXCEEDS
    assert by_id["route-mcgee-creek-beaver-pond"].distance_fit is DistanceFit.FITS
    assert by_id["route-mcgee-creek"].distance_fit is DistanceFit.EXCEEDS
    assert by_id["route-lundy-canyon-waterfall-beaver-dam"].distance_fit is DistanceFit.UNKNOWN
    assert by_id["route-lundy-canyon"].distance_fit is DistanceFit.EXCEEDS
    assert by_id["route-parker-lake"].distance_claim_ids == ("claim-parker-lake-route-profile",)
    assert "gap-mcgee-creek-day-hike-distance" in by_id["route-mcgee-creek"].knowledge_gap_ids
    assert by_id["route-mcgee-creek"].needs_current_check is True


def test_comparison_orders_fit_then_unknown_then_exceeds():
    reads = CanonicalReadService(ROOT)
    comparison = reads.compare_hikes((
        "route-tamarack-lakes-rock-creek", "route-mcgee-creek", "route-parker-lake",
    ), 10)
    assert [item.distance_fit for item in comparison.candidates] == [
        DistanceFit.FITS, DistanceFit.EXCEEDS, DistanceFit.EXCEEDS,
    ]


def test_comparison_rejects_implicit_or_invalid_scope():
    reads = CanonicalReadService(ROOT)
    with pytest.raises(ValueError, match="greater than zero"):
        reads.compare_hikes(("route-parker-lake",), 0)
    with pytest.raises(KeyError, match="unknown route"):
        reads.compare_hikes(("place-parker-lake",), 10)


def test_mcp_compare_hikes_exposes_plain_provenance_and_gaps():
    tools = WayproofReadTools(CanonicalReadService(ROOT))
    result = tools.compare_hikes([
        "route-parker-lake", "route-mcgee-creek",
    ], 10)
    assert result["maximum_round_trip_miles"] == 10
    assert result["candidates"][0]["distance_fit"] == "fits"
    assert result["candidates"][0]["distance_claim_ids"]
    assert result["candidates"][1]["distance_fit"] == "exceeds"
