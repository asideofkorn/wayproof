"""Pre-trip recheck projection for volatile canonical knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from .schema import CanonicalRecords, Claim, PlanningContext


class RecheckAnswerability(str, Enum):
    ANSWERED = "answered"
    NEEDS_CURRENT_CHECK = "needs_current_check"
    UNKNOWN = "unknown"


class RecheckState(str, Enum):
    COMPLETE = "complete"
    REQUIRED = "required"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class RecheckItem:
    input_id: str
    answerability: RecheckAnswerability
    explanation: str
    claim_id: str = ""
    evidence_ids: Tuple[str, ...] = ()
    source_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PretripRecheck:
    result_id: str
    state: RecheckState
    topics: Tuple[str, ...]
    items: Tuple[RecheckItem, ...]


def _trip_scopes(context: PlanningContext) -> set:
    return {
        scope_id for stage in context.stages for scope_id in stage.spatial_scope_ids
    }


def _relevant(claim: Claim, scopes: set) -> bool:
    return not claim.spatial_scope_ids or bool(scopes.intersection(claim.spatial_scope_ids))


def _claim_item(claim: Claim, context: PlanningContext, records: CanonicalRecords,
                timeless_is_volatile: bool) -> RecheckItem:
    scope = claim.temporal_scope
    if scope and (scope.starts_on is None or scope.starts_on <= context.trip_date) and (
        scope.ends_on is None or context.trip_date <= scope.ends_on
    ):
        answerability = RecheckAnswerability.ANSWERED
        explanation = "claim is effective on the trip date"
    elif scope:
        answerability = RecheckAnswerability.NEEDS_CURRENT_CHECK
        explanation = "dated claim does not establish the condition on the trip date"
    elif timeless_is_volatile:
        answerability = RecheckAnswerability.NEEDS_CURRENT_CHECK
        explanation = "volatile input has no trip-date-bounded observation"
    else:
        answerability = RecheckAnswerability.ANSWERED
        explanation = "claim is not time-bounded"

    evidence = {item.evidence_id: item for item in records.evidence}
    observations = {item.observation_id: item for item in records.observations}
    source_ids = tuple(dict.fromkeys(
        observations[evidence[evidence_id].observation_id].source_id
        for evidence_id in claim.evidence_ids
    ))
    return RecheckItem(
        input_id=claim.claim_id,
        claim_id=claim.claim_id,
        answerability=answerability,
        explanation=explanation,
        evidence_ids=claim.evidence_ids,
        source_ids=source_ids,
    )


def evaluate_pretrip_recheck(records: CanonicalRecords, context: PlanningContext,
                             result_id: str = "result-del-valle-pretrip-recheck"
                             ) -> PretripRecheck:
    """Project one canonical recheck manifest onto a bounded trip context."""
    manifests = {item.result_id: item for item in records.derived_results}
    manifest = manifests[result_id]
    input_ids = set(manifest.input_ids)
    scopes = _trip_scopes(context)
    claims = {
        item.claim_id: item for item in records.claims
        if item.claim_id in input_ids and _relevant(item, scopes)
    }

    items = [
        _claim_item(claim, context, records, timeless_is_volatile=True)
        for claim in claims.values()
    ]
    selected_ids = set(claims)
    for gap in records.gaps:
        if gap.gap_id not in input_ids:
            continue
        if not selected_ids.intersection(gap.related_ids):
            continue
        items.append(RecheckItem(
            input_id=gap.gap_id,
            answerability=RecheckAnswerability.UNKNOWN,
            explanation=gap.reason or gap.question,
        ))

    ordered = tuple(sorted(items, key=lambda item: item.input_id))
    if not ordered:
        state = RecheckState.NOT_APPLICABLE
    elif any(item.answerability is not RecheckAnswerability.ANSWERED for item in ordered):
        state = RecheckState.REQUIRED
    else:
        state = RecheckState.COMPLETE
    topics = tuple(manifest.value.get("topics", ())) if isinstance(manifest.value, dict) else ()
    return PretripRecheck(result_id, state, topics, ordered)
