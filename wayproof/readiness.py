"""Explainable Trip Readiness aggregation over canonical rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Tuple

from .requirements import (Applicability, CoverageStatus, RequirementEvaluation,
                           evaluate_requirements)
from .schema import CanonicalRecords, Fulfillment, PlanningContext


class ReadinessState(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class TripReadiness:
    state: ReadinessState
    evaluation: RequirementEvaluation
    rule_ids: Tuple[str, ...]
    claim_ids: Tuple[str, ...]
    evidence_ids: Tuple[str, ...]
    gap_ids: Tuple[str, ...]
    explanations: Tuple[str, ...]


def _state(evaluation: RequirementEvaluation, has_gaps: bool = False) -> ReadinessState:
    unknown = any(
        item.applicability is Applicability.UNKNOWN
        for item in evaluation.rule_assessments
    )
    statuses = {item.status for item in evaluation.requirements}
    if unknown and evaluation.requirements:
        return ReadinessState.PARTIAL
    if unknown:
        return ReadinessState.UNKNOWN
    if CoverageStatus.PARTIAL in statuses:
        return ReadinessState.PARTIAL
    if CoverageStatus.MISSING in statuses:
        return ReadinessState.BLOCKED
    if evaluation.requirements:
        return ReadinessState.PARTIAL if has_gaps else ReadinessState.READY
    return ReadinessState.NOT_APPLICABLE


def _explanations(evaluation: RequirementEvaluation,
                  gap_ids: Tuple[str, ...] = ()) -> Tuple[str, ...]:
    messages = []
    for item in evaluation.rule_assessments:
        if item.applicability is Applicability.UNKNOWN:
            messages.append(f"{item.rule_id}: {item.reason}")
    for item in evaluation.requirements:
        if item.status is CoverageStatus.MISSING:
            messages.append(
                f"{item.requirement.requirement_id}: no fulfillment covers the requirement"
            )
        elif item.status is CoverageStatus.PARTIAL:
            messages.append(
                f"{item.requirement.requirement_id}: fulfillment coverage is partial"
            )
    for gap_id in gap_ids:
        messages.append(f"{gap_id}: unresolved knowledge gap affects readiness")
    if not messages and evaluation.requirements:
        messages.append("all applicable requirements have complete coverage")
    if not messages:
        messages.append("no canonical rule applies to the supplied trip context")
    return tuple(messages)


def evaluate_trip_readiness(records: CanonicalRecords, context: PlanningContext,
                            fulfillments: Iterable[Fulfillment] = ()) -> TripReadiness:
    """Return readiness plus the canonical provenance used to reach it."""
    evaluation = evaluate_requirements(records.rules, context, fulfillments)
    relevant_rule_ids = tuple(
        item.rule_id for item in evaluation.rule_assessments
        if item.applicability in (Applicability.APPLIES, Applicability.UNKNOWN)
    )
    rules = {item.rule_id: item for item in records.rules}
    relevant_claim_ids = tuple(dict.fromkeys(
        rules[rule_id].claim_id for rule_id in relevant_rule_ids
    ))
    claims = {item.claim_id: item for item in records.claims}
    relevant_evidence_ids = tuple(dict.fromkeys(
        evidence_id
        for claim_id in relevant_claim_ids
        for evidence_id in claims[claim_id].evidence_ids
    ))
    relevant_ids = set(relevant_rule_ids) | set(relevant_claim_ids)
    gap_ids = tuple(
        gap.gap_id for gap in records.gaps
        if relevant_ids.intersection(gap.related_ids)
    )
    return TripReadiness(
        state=_state(evaluation, bool(gap_ids)),
        evaluation=evaluation,
        rule_ids=relevant_rule_ids,
        claim_ids=relevant_claim_ids,
        evidence_ids=relevant_evidence_ids,
        gap_ids=gap_ids,
        explanations=_explanations(evaluation, gap_ids),
    )
