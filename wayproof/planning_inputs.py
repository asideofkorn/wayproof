"""Source-backed cost, deadline, inventory, closure, and conflict inputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Tuple

from .intent import IntentResolution
from .schema import CanonicalRecords, Claim, KnowledgeGap, TemporalScope


class PlanningInputCategory(str, Enum):
    COST = "cost"
    DEADLINE = "deadline"
    INVENTORY = "inventory"
    CLOSURE = "closure"
    CONFLICT = "conflict"


class PlanningInputAnswerability(str, Enum):
    ANSWERED = "answered"
    NEEDS_CURRENT_CHECK = "needs_current_check"
    UNKNOWN = "unknown"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class PlanningInput:
    input_id: str
    category: PlanningInputCategory
    answerability: PlanningInputAnswerability
    subject_id: str
    predicate: str
    value: Any
    evidence_ids: Tuple[str, ...] = ()
    related_ids: Tuple[str, ...] = ()
    explanation: str = ""


@dataclass(frozen=True)
class PlanningInputProjection:
    inputs: Tuple[PlanningInput, ...]
    counts: Dict[str, int]


# Deliberately explicit: a new canonical predicate is not silently assigned
# planning semantics merely because its spelling contains a familiar word.
PREDICATE_CATEGORIES = {
    "fees": (PlanningInputCategory.COST,),
    "inspection_fees": (PlanningInputCategory.COST,),
    "published_boating_fees": (PlanningInputCategory.COST,),
    "published_entry_fees": (PlanningInputCategory.COST,),
    "published_swimming_page_parking_fee_usd": (PlanningInputCategory.COST,),
    "reservation_release": (PlanningInputCategory.COST, PlanningInputCategory.DEADLINE),
    "reserveamerica_campsite_inventory": (
        PlanningInputCategory.COST, PlanningInputCategory.INVENTORY,
    ),
    "backpacking_reservation_window": (PlanningInputCategory.DEADLINE,),
    "group_camping_reservation": (PlanningInputCategory.DEADLINE,),
    "no_show_deadlines": (PlanningInputCategory.DEADLINE,),
    "overnight_camping_reservation": (PlanningInputCategory.DEADLINE,),
    "published_group_reservation_minimum_business_days": (
        PlanningInputCategory.DEADLINE,
    ),
    "reservation_release_policy": (PlanningInputCategory.DEADLINE,),
    "reservation_window": (PlanningInputCategory.DEADLINE,),
    "cabin_inventory": (PlanningInputCategory.INVENTORY,),
    "group_camp_inventory": (PlanningInputCategory.INVENTORY,),
    "ordered_backpack_camp_inventory": (PlanningInputCategory.INVENTORY,),
    "published_site_listing_inventory": (PlanningInputCategory.INVENTORY,),
    "reservable_picnic_inventory": (PlanningInputCategory.INVENTORY,),
    "site_inventory": (PlanningInputCategory.INVENTORY,),
    "operating_status": (PlanningInputCategory.CLOSURE,),
    "published_seasonal_closures": (PlanningInputCategory.CLOSURE,),
    "trail_closure": (PlanningInputCategory.CLOSURE,),
}

VOLATILE_PREDICATES = {
    "operating_status", "published_seasonal_closures", "trail_closure",
}

PREDICATE_ACTIVITIES = {
    "inspection_fees": {"boating"},
    "published_boating_fees": {"boating"},
    "published_swimming_page_parking_fee_usd": {"swimming"},
    "cabin_inventory": {"camping"},
    "group_camp_inventory": {"camping"},
    "ordered_backpack_camp_inventory": {"backpacking", "camping"},
    "published_site_listing_inventory": {"camping"},
    "reservable_picnic_inventory": {"picnicking"},
    "reserveamerica_campsite_inventory": {"backpacking", "camping"},
    "site_inventory": {"camping"},
    "backpacking_reservation_window": {"backpacking", "camping"},
    "group_camping_reservation": {"camping"},
    "overnight_camping_reservation": {"backpacking", "camping"},
    "published_group_reservation_minimum_business_days": {"camping"},
    "reservation_release_policy": {"backpacking", "camping"},
    "reservation_window": {"camping"},
}

CONFLICT_GAP_CATEGORIES = {
    "gap-del-valle-family-site-inventory-conflict": PlanningInputCategory.INVENTORY,
    "gap-del-valle-seasonal-closures-current": PlanningInputCategory.CLOSURE,
    "gap-del-valle-swimming-parking-fee": PlanningInputCategory.COST,
}


def _trip_scopes(resolution: IntentResolution) -> set[str]:
    if not resolution.context:
        return set()
    return {
        scope_id for stage in resolution.context.stages
        for scope_id in stage.spatial_scope_ids
    }


def _relevant_entity_ids(records: CanonicalRecords,
                         resolution: IntentResolution) -> set[str]:
    ids = {item.entity_id for item in resolution.objectives}
    ids.update(
        item.entity_id for item in (resolution.route, resolution.entry, resolution.exit)
        if item is not None
    )
    if resolution.traversal:
        ids.update(item.segment_id for item in resolution.traversal.legs)
        ids.update(resolution.traversal.accessible_entity_ids)
        ids.update(resolution.traversal.alternate_segment_ids)
        ids.update(
            entity_id for leg in resolution.traversal.alternate_legs
            for entity_id in leg.accessible_entity_ids
        )
    # One sourced relationship hop includes contained facilities, managers,
    # booking systems, and permits without turning the whole graph relevant.
    overnight = resolution.context.activities.attributes.get("overnight")
    relationships = (
        item for item in records.relationships
        if not (item.predicate == "day_use_governed_by" and overnight is True)
        and not (item.predicate == "overnight_governed_by" and overnight is False)
    )
    adjacent = {
        endpoint
        for relationship in relationships
        if relationship.subject_id in ids or relationship.object_id in ids
        for endpoint in (relationship.subject_id, relationship.object_id)
    }
    return ids | adjacent


def _effective(scope: TemporalScope | None, day) -> bool:
    return not scope or (
        (scope.starts_on is None or scope.starts_on <= day)
        and (scope.ends_on is None or day <= scope.ends_on)
    )


def _answerability(claim: Claim, trip_date) -> tuple[PlanningInputAnswerability, str]:
    if not _effective(claim.temporal_scope, trip_date):
        return (
            PlanningInputAnswerability.NEEDS_CURRENT_CHECK,
            "the dated claim does not establish this input on the trip date",
        )
    if claim.predicate in VOLATILE_PREDICATES and (
        claim.temporal_scope is None or claim.temporal_scope.ends_on is None
    ):
        return (
            PlanningInputAnswerability.NEEDS_CURRENT_CHECK,
            "the operational input is open-ended or timeless and must be rechecked",
        )
    return PlanningInputAnswerability.ANSWERED, "the claim applies to the trip context"


def _claim_relevant(claim: Claim, scopes: set[str], entity_ids: set[str]) -> bool:
    return claim.subject_id in entity_ids or bool(scopes.intersection(
        claim.spatial_scope_ids
    ))


def project_planning_inputs(records: CanonicalRecords,
                            resolution: IntentResolution) -> PlanningInputProjection:
    """Project only explicitly classified and context-relevant canonical inputs."""
    if resolution.context is None:
        return PlanningInputProjection((), {})
    scopes = _trip_scopes(resolution)
    entity_ids = _relevant_entity_ids(records, resolution)
    activities = set(resolution.context.activities.activities)
    projected = []
    included_claim_ids = set()
    for claim in sorted(records.claims, key=lambda item: item.claim_id):
        categories = PREDICATE_CATEGORIES.get(claim.predicate, ())
        if not categories or not _claim_relevant(claim, scopes, entity_ids):
            continue
        required_activities = PREDICATE_ACTIVITIES.get(claim.predicate)
        if required_activities and activities and not activities.intersection(
            required_activities
        ):
            continue
        answerability, explanation = _answerability(claim, resolution.context.trip_date)
        if required_activities and not activities:
            answerability = PlanningInputAnswerability.UNKNOWN
            explanation = (
                "activity context is required before this input can apply to the trip"
            )
        included_claim_ids.add(claim.claim_id)
        for category in categories:
            projected.append(PlanningInput(
                f"{claim.claim_id}:{category.value}", category, answerability,
                claim.subject_id, claim.predicate, claim.value,
                claim.evidence_ids, explanation=explanation,
            ))

    gaps_by_id = {item.gap_id: item for item in records.gaps}
    for gap_id, category in CONFLICT_GAP_CATEGORIES.items():
        gap: KnowledgeGap | None = gaps_by_id.get(gap_id)
        if not gap or not included_claim_ids.intersection(gap.related_ids):
            continue
        projected.append(PlanningInput(
            gap.gap_id, PlanningInputCategory.CONFLICT,
            PlanningInputAnswerability.CONFLICTING, "", category.value,
            {"category": category.value, "question": gap.question},
            related_ids=gap.related_ids, explanation=gap.reason,
        ))

    inputs = tuple(sorted(projected, key=lambda item: (
        item.category.value, item.input_id,
    )))
    counts = {
        category.value: sum(item.category is category for item in inputs)
        for category in PlanningInputCategory
        if any(item.category is category for item in inputs)
    }
    return PlanningInputProjection(inputs, counts)
