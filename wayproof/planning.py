"""One bounded orchestration result for intent, readiness, and rechecks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Protocol, Tuple

from .intent import IntentResolution, IntentResolutionState
from .readiness import ReadinessState, TripReadiness
from .recheck import PretripRecheck
from .schema import Fulfillment, PlanningContext, TripIntent


class PlanningOutcomeState(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class TripPlan:
    state: PlanningOutcomeState
    resolution: IntentResolution
    readiness: Optional[TripReadiness] = None
    rechecks: Tuple[PretripRecheck, ...] = ()


class PlanningReads(Protocol):
    def resolve_intent(self, intent: TripIntent) -> IntentResolution: ...
    def readiness(
        self, context: PlanningContext, fulfillments: Iterable[Fulfillment] = (),
    ) -> TripReadiness: ...
    def pretrip_recheck(
        self, context: PlanningContext, result_id: str,
    ) -> PretripRecheck: ...


def _outcome_state(
    resolution: IntentResolution, readiness: Optional[TripReadiness],
) -> PlanningOutcomeState:
    if resolution.state is IntentResolutionState.AMBIGUOUS:
        return PlanningOutcomeState.AMBIGUOUS
    if resolution.state is IntentResolutionState.UNKNOWN or readiness is None:
        return PlanningOutcomeState.UNKNOWN
    if resolution.state is IntentResolutionState.PARTIAL:
        return PlanningOutcomeState.PARTIAL
    return {
        ReadinessState.READY: PlanningOutcomeState.READY,
        ReadinessState.BLOCKED: PlanningOutcomeState.BLOCKED,
        ReadinessState.PARTIAL: PlanningOutcomeState.PARTIAL,
        ReadinessState.UNKNOWN: PlanningOutcomeState.UNKNOWN,
        ReadinessState.NOT_APPLICABLE: PlanningOutcomeState.NOT_APPLICABLE,
    }[readiness.state]


def plan_trip(
    reads: PlanningReads,
    intent: TripIntent,
    fulfillments: Iterable[Fulfillment] = (),
    recheck_result_ids: Iterable[str] = (),
) -> TripPlan:
    """Resolve and evaluate one trip without allowing adapters to reimplement it."""
    resolution = reads.resolve_intent(intent)
    if resolution.context is None:
        return TripPlan(_outcome_state(resolution, None), resolution)

    readiness = reads.readiness(resolution.context, fulfillments)
    rechecks = tuple(
        reads.pretrip_recheck(resolution.context, result_id)
        for result_id in recheck_result_ids
    )
    return TripPlan(_outcome_state(resolution, readiness), resolution,
                    readiness, rechecks)
