"""Conservative TripIntent resolution over canonical identities and relationships."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, Tuple

from .schema import Entity, PlanningContext, Relationship, SpatialScope, TripIntent, TripObjective, TripStage
from .traversal import TraversalPlan, TraversalState, resolve_traversal


ROUTE_KINDS = {"route", "trail"}
ACCESS_KINDS = {"trailhead", "park_entrance", "staging_area", "walk_in_entrance"}
ROUTE_REQUIRED_KINDS = {"peak", "route", "trail"}


class IntentResolutionState(str, Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntentResolutionIssue:
    code: str
    message: str
    candidates: Tuple[str, ...] = ()


@dataclass(frozen=True)
class IntentResolution:
    state: IntentResolutionState
    intent: TripIntent
    objectives: Tuple[Entity, ...] = ()
    route: Optional[Entity] = None
    entry: Optional[Entity] = None
    exit: Optional[Entity] = None
    traversal: Optional[TraversalPlan] = None
    context: Optional[PlanningContext] = None
    issues: Tuple[IntentResolutionIssue, ...] = ()


class IntentReads(Protocol):
    def search_entities(self, query: str = "", kinds=()) -> Tuple[Entity, ...]: ...
    def entity(self, entity_id: str) -> Entity: ...
    def relationships_for(self, entity_id: str) -> Tuple[Relationship, ...]: ...
    def spatial_scopes_for(self, entity_id: str) -> Tuple[SpatialScope, ...]: ...


def _resolve_name(reads: IntentReads, query: str, kinds=()) -> tuple[Optional[Entity], tuple[Entity, ...]]:
    matches = reads.search_entities(query, kinds)
    exact = tuple(item for item in matches
                  if query.casefold() in (item.entity_id.casefold(), item.name.casefold()))
    candidates = exact or matches
    return (candidates[0], candidates) if len(candidates) == 1 else (None, candidates)


def _route_candidates(reads: IntentReads, objective: Entity) -> set[str]:
    if objective.kind in ROUTE_KINDS:
        return {objective.entity_id}
    return {
        item.object_id for item in reads.relationships_for(objective.entity_id)
        if item.subject_id == objective.entity_id and item.predicate == "approached_via"
    }


def _route_access_candidates(reads: IntentReads, route: Entity, predicate: str) -> set[str]:
    """Find evidenced direct or member-segment endpoints for a route/trail."""
    route_ids = {route.entity_id}
    for relationship in reads.relationships_for(route.entity_id):
        if relationship.object_id == route.entity_id and relationship.predicate == "part_of":
            route_ids.add(relationship.subject_id)
    candidates = set()
    for route_id in route_ids:
        for relationship in reads.relationships_for(route_id):
            if relationship.subject_id != route_id or relationship.predicate != predicate:
                continue
            try:
                entity = reads.entity(relationship.object_id)
            except KeyError:
                continue
            if entity.kind in ACCESS_KINDS:
                candidates.add(entity.entity_id)
    return candidates


def _scopes(reads: IntentReads, entity: Entity) -> tuple[str, ...]:
    return tuple(item.scope_id for item in reads.spatial_scopes_for(entity.entity_id))


def _objective_kind(entity: Entity) -> str:
    return {
        "peak": "summit", "route": "traverse", "trail": "traverse",
        "campground": "camp", "campsite": "camp", "family_campsite": "camp",
        "group_campsite": "camp", "backcountry_camp": "camp",
    }.get(entity.kind, "visit")


def resolve_trip_intent(reads: IntentReads, intent: TripIntent) -> IntentResolution:
    """Resolve only choices supported by canonical identity and relationship evidence."""
    if not intent.objective_queries:
        return IntentResolution(IntentResolutionState.UNKNOWN, intent, issues=(
            IntentResolutionIssue("missing_objective", "At least one objective is required."),
        ))

    objectives = []
    issues = []
    for query in intent.objective_queries:
        entity, candidates = _resolve_name(reads, query)
        if entity is None:
            code = "objective_unknown" if not candidates else "objective_ambiguous"
            message = (f'No canonical entity matches objective "{query}".' if not candidates
                       else f'Objective "{query}" matches multiple canonical entities.')
            issues.append(IntentResolutionIssue(
                code, message, tuple(item.entity_id for item in candidates)
            ))
        else:
            objectives.append(entity)
    if issues:
        state = (IntentResolutionState.AMBIGUOUS
                 if any(item.code.endswith("ambiguous") for item in issues)
                 else IntentResolutionState.UNKNOWN)
        return IntentResolution(state, intent, tuple(objectives), issues=tuple(issues))

    route_sets = [_route_candidates(reads, item) for item in objectives
                  if item.kind in ROUTE_REQUIRED_KINDS]
    shared_routes = set.intersection(*route_sets) if route_sets else set()
    route = None
    if intent.route_query:
        route, candidates = _resolve_name(reads, intent.route_query, ROUTE_KINDS)
        if route is None:
            issues.append(IntentResolutionIssue(
                "route_unknown" if not candidates else "route_ambiguous",
                f'Route "{intent.route_query}" could not be uniquely resolved.',
                tuple(item.entity_id for item in candidates),
            ))
        elif route_sets and any(route.entity_id not in choices for choices in route_sets):
            issues.append(IntentResolutionIssue(
                "route_not_supported",
                "The selected route is not a sourced approach for every route-dependent objective.",
                tuple(sorted(shared_routes)),
            ))
            route = None
    elif len(shared_routes) == 1:
        route = reads.entity(next(iter(shared_routes)))
    elif len(shared_routes) > 1:
        issues.append(IntentResolutionIssue(
            "route_ambiguous", "Multiple sourced routes serve the requested objectives.",
            tuple(sorted(shared_routes)),
        ))
    elif route_sets:
        issues.append(IntentResolutionIssue(
            "route_unresolved", "No single sourced route serves every requested objective.",
            tuple(sorted(set().union(*route_sets))),
        ))

    if any(item.code in {"route_ambiguous", "route_unknown", "route_not_supported"}
           for item in issues):
        return IntentResolution(IntentResolutionState.AMBIGUOUS, intent,
                                tuple(objectives), issues=tuple(issues))

    entry = exit_entity = None
    if route:
        starts = _route_access_candidates(reads, route, "starts_at")
        ends = _route_access_candidates(reads, route, "ends_at")
        if intent.entry_query:
            entry, candidates = _resolve_name(reads, intent.entry_query, ACCESS_KINDS)
            if entry is None or entry.entity_id not in starts:
                issues.append(IntentResolutionIssue(
                    "entry_not_supported", "The requested entry is not a sourced route start.",
                    tuple(sorted(starts)),
                ))
                entry = None
        elif len(starts) == 1:
            entry = reads.entity(next(iter(starts)))
        elif starts:
            issues.append(IntentResolutionIssue(
                "entry_ambiguous", "The route has multiple sourced entry candidates.",
                tuple(sorted(starts)),
            ))
        else:
            issues.append(IntentResolutionIssue(
                "entry_unknown", "No sourced entry is published for the selected route."
            ))

        if intent.exit_query:
            exit_entity, candidates = _resolve_name(reads, intent.exit_query, ACCESS_KINDS)
            allowed = starts | ends
            if exit_entity is None or exit_entity.entity_id not in allowed:
                issues.append(IntentResolutionIssue(
                    "exit_not_supported", "The requested exit is not a sourced route endpoint.",
                    tuple(sorted(allowed)),
                ))
                exit_entity = None
        else:
            issues.append(IntentResolutionIssue(
                "exit_unknown",
                "No exit was requested; Wayproof does not infer a loop or return to start.",
                tuple(sorted(starts | ends)),
            ))

    if any(item.code.endswith("ambiguous") or item.code.endswith("not_supported")
           for item in issues):
        return IntentResolution(
            state=IntentResolutionState.AMBIGUOUS, intent=intent,
            objectives=tuple(objectives), route=route, entry=entry,
            exit=exit_entity, issues=tuple(issues),
        )

    traversal = None
    if route and entry and exit_entity:
        traversal = resolve_traversal(
            reads, route, entry, exit_entity, intent.trip_date,
        )
        if traversal.state is not TraversalState.COMPLETE:
            issues.append(IntentResolutionIssue(
                f"traversal_{traversal.state.value}", traversal.message,
                traversal.alternate_segment_ids,
            ))

    stages = []
    sequence = 1
    if entry:
        stages.append(TripStage("entry", sequence, "entry", _scopes(reads, entry)))
        sequence += 1
    if route and (not traversal or traversal.state is not TraversalState.COMPLETE):
        stages.append(TripStage("route", sequence, "traverse", _scopes(reads, route)))
        sequence += 1
    elif traversal:
        for leg in traversal.legs:
            stages.append(TripStage(
                leg.segment_id, sequence, "traverse", leg.spatial_scope_ids,
            ))
            sequence += 1
    trip_objectives = []
    for index, entity in enumerate(objectives, start=1):
        objective_id = f"objective-{index}"
        kind = _objective_kind(entity)
        trip_objectives.append(TripObjective(objective_id, entity.entity_id, kind))
        stages.append(TripStage(objective_id, sequence, kind, _scopes(reads, entity)))
        sequence += 1
    if exit_entity:
        stages.append(TripStage("exit", sequence, "exit", _scopes(reads, exit_entity)))

    context = PlanningContext(
        intent.trip_date, tuple(trip_objectives), tuple(stages), intent.party,
        intent.activities, intent.equipment,
    )
    state = IntentResolutionState.PARTIAL if issues else IntentResolutionState.RESOLVED
    return IntentResolution(
        state=state, intent=intent, objectives=tuple(objectives), route=route,
        entry=entry, exit=exit_entity, traversal=traversal, context=context,
        issues=tuple(issues),
    )
