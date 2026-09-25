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


def _route_graph(snapshot, *, atomic=False, role="official_mainline"):
    """Return directed adjacency built from canonical segment relationships."""
    relationships = defaultdict(list)
    for item in snapshot.relationships:
        relationships[item.subject_id].append((item.predicate, item.object_id))

    predicate = (
        "printed_atomic_route_distance_miles"
        if atomic else "printed_route_distance_miles"
    )
    distance_claims = {
        item.subject_id: item.value
        for item in snapshot.claims
        if item.predicate == predicate
        and item.value.get("route_role") == role
    }
    if atomic:
        distance_claims.update({
            item.subject_id: {**item.value, "distance_miles": 0.0}
            for item in snapshot.claims
            if item.predicate == "mapped_route_connector"
            and item.value.get("route_role") == role
        })
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
            if item.claim_id.startswith("claim-ohlone-map-mainline-mileage-label-")
        ),
        key=lambda value: value["ordinal_stanford_to_lichen_bark"],
    )
    assert len(labels) == 39
    assert sum(value["distance_miles"] for value in labels) == pytest.approx(21.71)
    assert labels[0]["printed_label"] == ".08"
    assert labels[-1]["printed_label"] == ".91"


def test_consumer_can_traverse_stanford_to_lichen_bark(snapshot):
    result = _path(
        _route_graph(snapshot, atomic=True),
        "staging-mission-peak-stanford-avenue",
        "trailhead-ohlone-lichen-bark",
    )
    assert result is not None
    segments, miles = result
    assert len(segments) == 52
    assert miles == pytest.approx(26.90)


def test_atomic_path_visits_every_ot_anchor_in_order(snapshot):
    graph = _route_graph(snapshot, atomic=True)
    expected = [f"route-node-ohlone-ot{number}" for number in range(1, 41)]
    node = "staging-mission-peak-stanford-avenue"
    visited = []
    while node != "trailhead-ohlone-lichen-bark":
        assert len(graph[node]) == 1
        node = graph[node][0][0]
        if node.startswith("route-node-ohlone-ot"):
            visited.append(node)
    assert visited == expected


def test_two_connectors_disclose_that_the_map_prints_no_distance(snapshot):
    graph = _route_graph(snapshot, atomic=True)
    connectors = [
        item for item in snapshot.claims
        if item.predicate == "mapped_route_connector"
        and item.subject_id.startswith("route-leg-ohlone-mainline-connector-")
    ]
    assert len(connectors) == 2
    assert {item.value["distance_status"] for item in connectors} == {
        "not_printed"
    }
    assert _path(
        graph,
        "route-node-ohlone-ot9",
        "route-node-ohlone-ot10",
    )[1] == 0.0
    assert _path(
        graph,
        "route-node-ohlone-ot16",
        "route-node-ohlone-ot17",
    )[1] == 0.0
