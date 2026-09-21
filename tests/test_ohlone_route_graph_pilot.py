"""Regression checks for the bounded Ohlone route-graph pilot."""

from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def snapshot():
    return load_canonical(ROOT)


def by_id(items, attribute):
    return {getattr(item, attribute): item for item in items}


def test_pilot_changeset_is_validated_and_exactly_accounts_for_the_slice():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ohlone-route-graph-pilot.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 467
    assert len({item.path for item in change.operations}) == 467
    assert {item.action.value for item in change.operations} == {"ADD"}


def test_numbered_posts_and_route_segments_are_durable_entities(snapshot):
    entities = by_id(snapshot.entities, "entity_id")
    for number in range(1, 41):
        item = entities[f"route-node-ohlone-ot{number}"]
        assert item.kind == "numbered_trail_post"
    segments = [item for item in snapshot.entities
                if item.entity_id.startswith("route-segment-ohlone-")]
    assert len(segments) == 13
    assert {item.kind for item in segments} == {"route_segment"}
    atomic = [item for item in snapshot.entities
              if item.entity_id.startswith("route-leg-ohlone-mainline-")]
    assert len(atomic) == 52
    assert {item.kind for item in atomic} == {"route_segment"}


def test_every_segment_has_explicit_endpoints_and_trail_membership(snapshot):
    segment_ids = {
        item.entity_id for item in snapshot.entities
        if item.entity_id.startswith("route-segment-ohlone-")
    }
    relationships = snapshot.relationships
    for segment_id in segment_ids:
        edges = [item for item in relationships if item.subject_id == segment_id]
        assert sum(item.predicate == "starts_at" for item in edges) == 1
        assert sum(item.predicate == "ends_at" for item in edges) == 1
        assert any(item.predicate == "part_of"
                   and item.object_id == "trail-ohlone-wilderness" for item in edges)


def test_printed_components_are_preserved_and_sums_are_disclosed(snapshot):
    claims = by_id(snapshot.claims, "claim_id")
    rose = claims["claim-ohlone-route-segment-ot28-ot29-rose"].value
    assert rose["printed_components_miles"] == [0.22, 0.21, 0.35]
    assert rose["distance_miles"] == pytest.approx(0.78)
    assert rose["calculation"] == "sum_of_printed_components"

    stewarts = claims["claim-ohlone-route-segment-ot33-ot35-stewarts"].value
    assert stewarts["printed_components_miles"] == [0.6, 0.46, 0.61, 0.28]
    assert stewarts["distance_miles"] == pytest.approx(1.95)
    assert stewarts["route_role"] == "parallel_alternate"


def test_parallel_routes_remain_alternatives_with_planning_tradeoffs(snapshot):
    results = by_id(snapshot.derived_results, "result_id")
    maggies = results["result-ohlone-ot27-ot29-route-comparison"]
    assert maggies.value == {
        "official_mainline_miles": 0.94,
        "maggies_alternate_miles": 0.89,
        "alternate_difference_miles": -0.05,
    }
    stewarts = results["result-ohlone-ot33-ot35-route-comparison"]
    assert stewarts.value["official_mainline_miles"] == pytest.approx(1.18)
    assert stewarts.value["stewarts_alternate_miles"] == pytest.approx(1.95)
    assert stewarts.value["alternate_difference_miles"] == pytest.approx(0.77)


def test_alternates_and_spur_expose_their_facility_access(snapshot):
    access = {
        (item.subject_id, item.object_id)
        for item in snapshot.relationships if item.predicate == "provides_access_to"
    }
    assert (
        "route-segment-ohlone-ot27-ot29-maggies",
        "water-ohlone-maggies-half-acre",
    ) in access
    assert (
        "route-segment-ohlone-ot33-ot35-stewarts",
        "facility-ohlone-stewarts-restroom",
    ) in access
    assert (
        "route-segment-ohlone-ot26-doe-canyon",
        "water-ohlone-doe-camp",
    ) in access
    detour = next(item for item in snapshot.derived_results
                  if item.result_id == "result-ohlone-doe-canyon-roundtrip-detour")
    assert detour.value == {"one_way_miles": 0.16, "roundtrip_miles": 0.32}


def test_lichen_bark_is_one_start_area_not_duplicate_access_points(snapshot):
    entities = by_id(snapshot.entities, "entity_id")
    trailheads = [item for item in snapshot.entities
                  if item.kind == "trailhead" and "Lichen Bark" in item.name]
    assert [item.entity_id for item in trailheads] == ["trailhead-ohlone-lichen-bark"]
    assert entities["water-del-valle-lichen-bark"].kind == "water_source"
    assert entities["restroom-del-valle-lichen-bark"].kind == "restroom"

    claims = by_id(snapshot.claims, "claim_id")
    coordinate = claims["claim-google-maps-ohlone-lichen-bark-start-coordinate"]
    assert coordinate.value["latitude"] == pytest.approx(37.5787566)
    assert coordinate.value["longitude"] == pytest.approx(-121.6974062)
    start = claims["claim-ohlone-lichen-bark-start-area"].value
    assert start["first_numbered_post"] == "route-node-ohlone-ot40"
    assert start["printed_distance_to_first_numbered_post_miles"] == 0.91


def test_mapped_water_presence_does_not_become_a_current_availability_claim(snapshot):
    gap_ids = {item.gap_id for item in snapshot.gaps}
    assert "gap-ohlone-lichen-bark-water-current-status" in gap_ids
    result = next(item for item in snapshot.derived_results
                  if item.result_id == "result-ohlone-lichen-bark-pretrip-recheck")
    assert result.value == {
        "required": True,
        "topics": ["drinking_water_operational_status"],
    }


def test_completed_topology_retires_the_unmodeled_route_gap(snapshot):
    assert "gap-ohlone-route-graph-unmodeled-sections" not in {
        item.gap_id for item in snapshot.gaps
    }


def test_every_mainline_mileage_label_outside_detailed_slice_is_preserved(snapshot):
    claims = sorted(
        (
            item
            for item in snapshot.claims
            if item.claim_id.startswith("claim-ohlone-map-mainline-mileage-label-")
        ),
        key=lambda item: item.value["ordinal_stanford_to_lichen_bark"],
    )
    assert len(claims) == 39
    assert [item.value["ordinal_stanford_to_lichen_bark"] for item in claims] == list(
        range(1, 40)
    )
    assert [item.value["printed_label"] for item in claims] == [
        ".08", "1.51", ".65", ".18", ".12", ".15", ".23", ".24",
        ".24", ".48", "1.56", "1.33", ".77", ".17", ".22", ".06",
        ".36", ".94", ".38", "1.28", ".26", ".19", "1.46", ".20",
        ".36", "1.24", ".34", ".25", ".13", "1.10", ".45", ".25",
        "1.91", ".35", ".20", ".33", ".12", ".71", ".91",
    ]
    assert {item.value["topology_status"] for item in claims} == {"atomic_leg"}
    assert all(item.value["start_node_id"] for item in claims)
    assert all(item.value["end_node_id"] for item in claims)
    assert sum(item.value["distance_miles"] for item in claims) == pytest.approx(
        21.71
    )
