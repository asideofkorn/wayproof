"""Evidence-bounded route traversal over canonical segment topology."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional, Protocol, Tuple

from .schema import Claim, Entity, Relationship, SpatialScope, TemporalScope


class TraversalState(str, Enum):
    COMPLETE = "complete"
    UNAVAILABLE = "unavailable"
    DISCONNECTED = "disconnected"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class TraversalLeg:
    sequence: int
    segment_id: str
    start_node_id: str
    end_node_id: str
    distance_miles: Optional[float]
    distance_status: str
    spatial_scope_ids: Tuple[str, ...] = ()
    accessible_entity_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TraversalPlan:
    state: TraversalState
    route_id: str
    entry_id: str
    exit_id: str
    legs: Tuple[TraversalLeg, ...] = ()
    total_known_distance_miles: float = 0.0
    distance_complete: bool = False
    accessible_entity_ids: Tuple[str, ...] = ()
    alternate_legs: Tuple[TraversalLeg, ...] = ()
    alternate_segment_ids: Tuple[str, ...] = ()
    message: str = ""


class TraversalReads(Protocol):
    def entity(self, entity_id: str) -> Entity: ...
    def claims_for(self, subject_id: str) -> Tuple[Claim, ...]: ...
    def relationships_for(self, entity_id: str) -> Tuple[Relationship, ...]: ...
    def spatial_scopes_for(self, entity_id: str) -> Tuple[SpatialScope, ...]: ...


def _effective(scope: Optional[TemporalScope], trip_date: date) -> bool:
    return not scope or (
        (scope.starts_on is None or scope.starts_on <= trip_date)
        and (scope.ends_on is None or scope.ends_on >= trip_date)
    )


def _segment_description(reads: TraversalReads, segment_id: str, trip_date: date):
    relationships = tuple(
        item for item in reads.relationships_for(segment_id)
        if item.subject_id == segment_id and _effective(item.temporal_scope, trip_date)
    )
    starts = tuple(item.object_id for item in relationships if item.predicate == "starts_at")
    ends = tuple(item.object_id for item in relationships if item.predicate == "ends_at")
    access = tuple(sorted(
        item.object_id for item in relationships if item.predicate == "provides_access_to"
    ))
    topology_claims = tuple(
        item for item in reads.claims_for(segment_id)
        if item.predicate in {
            "printed_atomic_route_distance_miles", "mapped_route_connector",
            "described_route_connector", "printed_route_distance_miles",
            "official_dataset_route_segment",
        }
        and _effective(item.temporal_scope, trip_date)
    )
    if len(starts) != 1 or len(ends) != 1 or len(topology_claims) != 1:
        return None
    claim = topology_claims[0]
    value = claim.value
    role = value.get("route_role", "")
    distance = value.get("distance_miles")
    status = value.get("distance_status", "known" if distance is not None else "unknown")
    scopes = {
        *claim.spatial_scope_ids,
        *(item.scope_id for item in reads.spatial_scopes_for(segment_id)),
    }
    return (
        starts[0], ends[0], role, distance, status, tuple(sorted(scopes)), access,
        claim.predicate,
    )


def resolve_traversal(
    reads: TraversalReads,
    route: Entity,
    entry: Entity,
    exit_entity: Entity,
    trip_date: date,
    *,
    route_role: str = "official_mainline",
) -> TraversalPlan:
    """Resolve one evidenced directed path without selecting an alternate."""
    members = {
        item.subject_id for item in reads.relationships_for(route.entity_id)
        if item.object_id == route.entity_id and item.predicate == "part_of"
    }
    described = {}
    official_descriptions = {}
    alternate_descriptions = {}
    alternate_ids = []
    for segment_id in sorted(members):
        try:
            if reads.entity(segment_id).kind != "route_segment":
                continue
        except KeyError:
            continue
        description = _segment_description(reads, segment_id, trip_date)
        if description is None:
            continue
        if description[2] == route_role:
            described[segment_id] = description
            official_descriptions[segment_id] = description
        else:
            alternate_ids.append(segment_id)
            alternate_descriptions[segment_id] = description

    atomic_predicates = {
        "printed_atomic_route_distance_miles", "mapped_route_connector",
        "described_route_connector", "official_dataset_route_segment",
    }
    atomic = {
        segment_id: description
        for segment_id, description in described.items()
        if description[7] in atomic_predicates
    }
    if atomic:
        described = atomic

    if not described:
        return TraversalPlan(
            TraversalState.UNAVAILABLE, route.entity_id, entry.entity_id,
            exit_entity.entity_id, alternate_segment_ids=tuple(alternate_ids),
            message="No canonical segment topology is published for this route.",
        )

    graph = defaultdict(list)
    for segment_id, description in described.items():
        graph[description[0]].append((description[1], segment_id))
        # starts_at/ends_at preserve a stable map-transcription orientation;
        # they do not make an ordinary official trail mainline one-way. Roles
        # such as one_way_spur stay outside this graph and are not reversed.
        graph[description[1]].append((description[0], segment_id))

    queue = deque([(entry.entity_id, ())])
    paths = []
    shortest_length = None
    while queue:
        node, segment_ids = queue.popleft()
        if shortest_length is not None and len(segment_ids) > shortest_length:
            continue
        if node == exit_entity.entity_id:
            shortest_length = len(segment_ids)
            paths.append(segment_ids)
            continue
        visited_nodes = {entry.entity_id, node}
        cursor = entry.entity_id
        for segment_id in segment_ids:
            start, end = described[segment_id][0:2]
            cursor = end if cursor == start else start
            visited_nodes.add(cursor)
        for next_node, segment_id in sorted(graph[node]):
            if next_node not in visited_nodes:
                queue.append((next_node, (*segment_ids, segment_id)))

    if not paths:
        return TraversalPlan(
            TraversalState.DISCONNECTED, route.entity_id, entry.entity_id,
            exit_entity.entity_id, alternate_segment_ids=tuple(alternate_ids),
            message="Published segments do not connect the requested endpoints.",
        )
    if len(paths) > 1:
        return TraversalPlan(
            TraversalState.AMBIGUOUS, route.entity_id, entry.entity_id,
            exit_entity.entity_id, alternate_segment_ids=tuple(alternate_ids),
            message="Multiple equally short published mainline traversals connect the endpoints.",
        )

    legs = []
    current_node = entry.entity_id
    for sequence, segment_id in enumerate(paths[0], start=1):
        start, end, _, distance, status, scopes, access, _ = described[segment_id]
        if current_node == end:
            start, end = end, start
        legs.append(TraversalLeg(
            sequence, segment_id, start, end, distance, status, scopes, access,
        ))
        current_node = end
    path_nodes = [entry.entity_id, *(item.end_node_id for item in legs)]
    node_positions = {node_id: index for index, node_id in enumerate(path_nodes)}
    accessible = {
        entity_id
        for description in official_descriptions.values()
        if description[0] in node_positions
        and description[1] in node_positions
        for entity_id in description[6]
    }
    alternate_legs = tuple(
        TraversalLeg(
            index, segment_id, description[0], description[1], description[3],
            description[4], description[5], description[6],
        )
        for index, (segment_id, description) in enumerate(
            sorted(alternate_descriptions.items()), start=1,
        )
        if description[0] in node_positions
    )
    known_total = round(sum(item.distance_miles or 0.0 for item in legs), 10)
    return TraversalPlan(
        TraversalState.COMPLETE, route.entity_id, entry.entity_id,
        exit_entity.entity_id, tuple(legs), known_total,
        all(item.distance_miles is not None for item in legs),
        tuple(sorted(accessible)), alternate_legs, tuple(alternate_ids),
    )
