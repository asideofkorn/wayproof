"""Bounded discovery context, never rule inheritance or itinerary resolution.

Every hop is an explicit canonical relationship. Adjacency only offers a
separately scoped jurisdiction to inspect; it does not establish traversal.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class JourneyContext:
    entity_id: str
    role: str
    relationship_ids: tuple[str, ...] = ()


def journey_context(reads, entity_id: str) -> tuple[JourneyContext, ...]:
    contexts = {entity_id: JourneyContext(entity_id, "Selected place")}

    def follow(origin, predicates, role):
        found = []
        for rel in reads.relationships_for(origin.entity_id):
            if rel.subject_id != origin.entity_id or rel.predicate not in predicates:
                continue
            target = JourneyContext(rel.object_id, role,
                                    origin.relationship_ids + (rel.relationship_id,))
            if target.entity_id not in contexts:
                contexts[target.entity_id] = target
                found.append(target)
        return found

    selected = contexts[entity_id]
    approaches = follow(selected, {"approached_via"}, "Approach")
    routes = [selected, *approaches]
    for route in routes:
        if reads.entity(route.entity_id).kind not in {"route", "trail", "route_segment"}:
            continue
        starts = follow(route, {"starts_at"}, "Entry")
        follow(route, {"ends_at"}, "Destination")
        follow(route, {"traverses"}, "Traversed place")
        for start in starts:
            for approach in follow(start, {"approached_via"}, "Road or entry approach"):
                follow(approach, {"traverses"}, "Approach conditions")
    for approach in approaches:
        follow(approach, {"traverses"}, "Approach conditions")

    # Only the selected place and evidenced route destinations can introduce
    # adjacent jurisdiction context. Do not fan out through parks or proximity.
    for context in tuple(contexts.values()):
        if context.role not in {"Selected place", "Destination"}:
            continue
        for rel in reads.relationships_for(context.entity_id):
            if rel.predicate != "adjacent_to":
                continue
            other = rel.object_id if rel.subject_id == context.entity_id else rel.subject_id
            if not any(c.predicate == "jurisdiction_transition" for c in reads.claims_for(other)):
                continue
            contexts.setdefault(other, JourneyContext(
                other, "Adjacent jurisdiction — review before continuing",
                context.relationship_ids + (rel.relationship_id,)))
    return tuple(contexts.values())
