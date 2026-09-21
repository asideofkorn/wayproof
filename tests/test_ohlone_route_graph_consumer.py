"""Consumer-style queries against the published Ohlone route-graph pilot.

These tests intentionally use only canonical entities, claims, and
relationships.  They prove what a downstream consumer can answer today and
that an incomplete full-traverse graph fails closed instead of inventing
connectivity.
"""

from collections import defaultdict, deque
from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical


ROOT = Path(__file__).resolve().parents[1]


def _route_graph(snapshot, *, role="official_mainline"):
    """Return directed adjacency built from canonical segment relationships."""
    relationships = defaultdict(list)
    for item in snapshot.relationships:
        relationships[item.subject_id].append((item.predicate, item.object_id))

    distance_claims = {
        item.subject_id: item.value
        for item in snapshot.claims
        if item.predicate == "printed_route_distance_miles"
        and item.value.get("route_role") == role
    }
    graph = defaultdict(list)
    for segment_id, value in distance_claims.items():
        edges = relationships[segment_id]
        starts = [target for predicate, target in edges if predicate == "starts_at"]
        ends = [target for predicate, target in edges if predicate == "ends_at"]
        if len(starts) == len(ends) == 1:
            graph[starts[0]].append(
                (ends[0], segment_id, value["distance_miles"])
            )
    return graph


def _path(graph, start, end):
    queue = deque([(start, [], 0.0)])
    visited = {start}
    while queue:
        node, segments, miles = queue.popleft()
        if node == end:
            return segments, miles
        for next_node, segment_id, distance in graph[node]:
            if next_node not in visited:
                visited.add(next_node)
                queue.append(
                    (next_node, [*segments, segment_id], miles + distance)
                )
    return None


@pytest.fixture(scope="module")
def snapshot():
    return load_canonical(ROOT)


def test_consumer_can_traverse_the_detailed_ot26_ot35_mainline(snapshot):
    result = _path(
        _route_graph(snapshot),
        "route-node-ohlone-ot26",
        "route-node-ohlone-ot35",
    )
    assert result is not None
    segments, miles = result
    assert segments == [
        "route-segment-ohlone-ot26-ot27",
        "route-segment-ohlone-ot27-ot28",
        "route-segment-ohlone-ot28-ot29-rose",
        "route-segment-ohlone-ot29-ot30",
        "route-segment-ohlone-ot30-ot31",
        "route-segment-ohlone-ot31-ot32",
        "route-segment-ohlone-ot32-ot33",
        "route-segment-ohlone-ot33-ot34",
        "route-segment-ohlone-ot34-ot35",
    ]
    assert miles == pytest.approx(5.19)


def test_consumer_can_retrieve_the_ordered_outside_slice_labels(snapshot):
    labels = sorted(
        (
            item.value
            for item in snapshot.claims
            if item.predicate == "printed_route_mileage_label"
        ),
        key=lambda value: value["ordinal_stanford_to_lichen_bark"],
    )
    assert len(labels) == 39
    assert sum(value["distance_miles"] for value in labels) == pytest.approx(21.71)
    assert labels[0]["printed_label"] == ".08"
    assert labels[-1]["printed_label"] == ".91"


def test_full_traverse_query_fails_closed_until_tick_topology_is_published(snapshot):
    graph = _route_graph(snapshot)
    assert _path(
        graph,
        "access-point-mission-peak-stanford-avenue",
        "trailhead-ohlone-lichen-bark",
    ) is None

    gaps = {item.gap_id: item for item in snapshot.gaps}
    gap = gaps["gap-ohlone-route-graph-unmodeled-sections"]
    assert "exact map coordinates and junction identities" in gap.question
    assert "complete Stanford-to-Del-Valle endpoint graph" in gap.reason

