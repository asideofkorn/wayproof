"""Bounded evaluation of projected planning inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Any, Optional, Tuple

from .planning_inputs import (PlanningInput, PlanningInputAnswerability,
                              PlanningInputCategory, PlanningInputProjection)


class OperationalState(str, Enum):
    ANSWERED = "answered"
    PARTIAL = "partial"
    NEEDS_CURRENT_CHECK = "needs_current_check"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class DeadlineStatus(str, Enum):
    NOT_OPEN = "not_open"
    ACTIONABLE = "actionable"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CostComponent:
    input_id: str
    label: str
    amount_usd: float


@dataclass(frozen=True)
class CostEvaluation:
    state: OperationalState
    components: Tuple[CostComponent, ...] = ()
    total_usd: Optional[float] = None
    unresolved_input_ids: Tuple[str, ...] = ()
    explanation: str = ""


@dataclass(frozen=True)
class DeadlineEvaluationItem:
    input_id: str
    status: DeadlineStatus
    opens_on: Optional[date] = None
    closes_on: Optional[date] = None
    explanation: str = ""


@dataclass(frozen=True)
class InventoryEvaluationItem:
    input_id: str
    state: OperationalState
    explanation: str
    fits_party: Optional[bool] = None
    capacity: Optional[int] = None


@dataclass(frozen=True)
class ClosureEvaluationItem:
    input_id: str
    state: OperationalState
    explanation: str


@dataclass(frozen=True)
class ConflictEvaluationItem:
    input_id: str
    state: OperationalState
    related_ids: Tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class OperationalEvaluation:
    state: OperationalState
    costs: CostEvaluation
    deadlines: Tuple[DeadlineEvaluationItem, ...] = ()
    inventory: Tuple[InventoryEvaluationItem, ...] = ()
    closures: Tuple[ClosureEvaluationItem, ...] = ()
    conflicts: Tuple[ConflictEvaluationItem, ...] = ()


def _usd_values(value: Any, prefix: str = "") -> list[tuple[str, float]]:
    if not isinstance(value, dict):
        return []
    values = []
    for key, item in value.items():
        label = f"{prefix}.{key}" if prefix else key
        if key.endswith("_usd") and isinstance(item, (int, float)) and not isinstance(
            item, bool
        ):
            values.append((label, float(item)))
        elif isinstance(item, dict):
            values.extend(_usd_values(item, label))
    return values


def _costs(inputs: tuple[PlanningInput, ...]) -> CostEvaluation:
    if not inputs:
        return CostEvaluation(OperationalState.NOT_APPLICABLE,
                              explanation="no cost input applies")
    components = []
    unresolved = []
    one_amount_per_input = True
    for item in inputs:
        if item.answerability is not PlanningInputAnswerability.ANSWERED:
            unresolved.append(item.input_id)
            continue
        if isinstance(item.value, (int, float)) and not isinstance(item.value, bool):
            amounts = [(item.predicate, float(item.value))]
        else:
            amounts = _usd_values(item.value)
        if len(amounts) != 1:
            one_amount_per_input = False
            unresolved.append(item.input_id)
        components.extend(CostComponent(item.input_id, label, amount)
                          for label, amount in amounts)
    if not unresolved and one_amount_per_input:
        return CostEvaluation(
            OperationalState.ANSWERED, tuple(components),
            round(sum(item.amount_usd for item in components), 2),
            explanation="every applicable cost input has one unambiguous amount",
        )
    return CostEvaluation(
        OperationalState.PARTIAL, tuple(components), None,
        tuple(dict.fromkeys(unresolved)),
        "components are visible, but alternatives or unresolved applicability prevent a total",
    )


def _subtract_business_days(day: date, count: int) -> date:
    current = day
    remaining = count
    while remaining:
        current -= timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def _deadline(item: PlanningInput, trip_date: date,
              as_of_date: Optional[date]) -> DeadlineEvaluationItem:
    if item.answerability is not PlanningInputAnswerability.ANSWERED:
        return DeadlineEvaluationItem(
            item.input_id, DeadlineStatus.UNKNOWN,
            explanation="the source input is not currently answerable",
        )
    value = item.value if isinstance(item.value, dict) else {}
    opens_on = closes_on = None
    if isinstance(value.get("maximum_advance_weeks"), int):
        opens_on = trip_date - timedelta(weeks=value["maximum_advance_weeks"])
    if isinstance(value.get("minimum_advance_hours"), int):
        closes_on = trip_date - timedelta(hours=value["minimum_advance_hours"])
    elif isinstance(value.get("minimum_advance_days"), int):
        closes_on = trip_date - timedelta(days=value["minimum_advance_days"])
    elif isinstance(value.get("minimum_advance_business_days"), int):
        closes_on = _subtract_business_days(
            trip_date, value["minimum_advance_business_days"]
        )
    if opens_on is None and closes_on is None:
        return DeadlineEvaluationItem(
            item.input_id, DeadlineStatus.UNKNOWN,
            explanation="the published deadline is not machine-resolved into trip dates",
        )
    if as_of_date is None:
        return DeadlineEvaluationItem(
            item.input_id, DeadlineStatus.UNKNOWN, opens_on, closes_on,
            "an explicit as_of_date is required to determine deadline status",
        )
    if opens_on and as_of_date < opens_on:
        status = DeadlineStatus.NOT_OPEN
    elif closes_on and as_of_date > closes_on:
        status = DeadlineStatus.EXPIRED
    else:
        status = DeadlineStatus.ACTIONABLE
    return DeadlineEvaluationItem(
        item.input_id, status, opens_on, closes_on,
        "status is calculated from structured advance-window fields",
    )


def evaluate_operational_inputs(
    projection: PlanningInputProjection,
    trip_date: date,
    as_of_date: Optional[date] = None,
    party_size: int = 0,
) -> OperationalEvaluation:
    grouped = {
        category: tuple(item for item in projection.inputs if item.category is category)
        for category in PlanningInputCategory
    }
    costs = _costs(grouped[PlanningInputCategory.COST])
    deadlines = tuple(
        _deadline(item, trip_date, as_of_date)
        for item in grouped[PlanningInputCategory.DEADLINE]
    )
    inventory_items = []
    for item in grouped[PlanningInputCategory.INVENTORY]:
        capacity = None
        if item.predicate in {"reserveamerica_site_profile", "recreation_gov_site_profile"} and isinstance(
            item.value, dict
        ):
            value = item.value.get("listed_capacity")
            capacity = value if isinstance(value, int) else None
        fits = capacity >= party_size if capacity is not None and party_size else None
        if fits is False:
            explanation = (
                f"published capacity {capacity} does not fit party size {party_size}; "
                "this site is not a candidate"
            )
        elif fits is True:
            explanation = (
                f"published capacity {capacity} fits party size {party_size}; "
                "live availability still requires a current check"
            )
        else:
            explanation = "published inventory describes the offering, not live availability"
        inventory_items.append(InventoryEvaluationItem(
            item.input_id, OperationalState.NEEDS_CURRENT_CHECK, explanation,
            fits, capacity,
        ))
    inventory = tuple(inventory_items)
    closures = tuple(ClosureEvaluationItem(
        item.input_id,
        (OperationalState.NEEDS_CURRENT_CHECK
         if item.answerability is not PlanningInputAnswerability.ANSWERED
         or item.predicate == "published_seasonal_closures"
         else OperationalState.BLOCKED
         if isinstance(item.value, dict) and item.value.get("status") == "closed"
         else OperationalState.ANSWERED),
        ("closure status must be checked for the trip date"
         if item.answerability is not PlanningInputAnswerability.ANSWERED
         or item.predicate == "published_seasonal_closures"
         else "the effective operational claim is closed"
         if isinstance(item.value, dict) and item.value.get("status") == "closed"
         else "the effective operational claim does not establish a closure"),
    ) for item in grouped[PlanningInputCategory.CLOSURE])
    conflicts = tuple(ConflictEvaluationItem(
        item.input_id, OperationalState.PARTIAL, item.related_ids,
        item.explanation or "canonical sources remain in conflict",
    ) for item in grouped[PlanningInputCategory.CONFLICT])

    states = {costs.state}
    if any(item.status is DeadlineStatus.UNKNOWN for item in deadlines):
        states.add(OperationalState.PARTIAL)
    if inventory or any(item.state is OperationalState.NEEDS_CURRENT_CHECK
                        for item in closures):
        states.add(OperationalState.NEEDS_CURRENT_CHECK)
    if conflicts:
        states.add(OperationalState.PARTIAL)
    if any(item.state is OperationalState.BLOCKED for item in closures):
        state = OperationalState.BLOCKED
    elif OperationalState.PARTIAL in states:
        state = OperationalState.PARTIAL
    elif OperationalState.NEEDS_CURRENT_CHECK in states:
        state = OperationalState.NEEDS_CURRENT_CHECK
    elif states == {OperationalState.NOT_APPLICABLE} and not deadlines:
        state = OperationalState.NOT_APPLICABLE
    else:
        state = OperationalState.ANSWERED
    return OperationalEvaluation(state, costs, deadlines, inventory, closures, conflicts)
