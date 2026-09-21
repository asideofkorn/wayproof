"""Evaluate canonical rules into trip requirements and fulfillment coverage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

from .schema import (Coverage, Fulfillment, PlanningContext, Requirement, Rule,
                     TemporalScope, coverage_contains)


class Applicability(str, Enum):
    APPLIES = "applies"
    DOES_NOT_APPLY = "does_not_apply"
    UNKNOWN = "unknown"


class CoverageStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    MISSING = "missing"


@dataclass(frozen=True)
class RuleAssessment:
    rule_id: str
    applicability: Applicability
    reason: str = ""


@dataclass(frozen=True)
class RequirementAssessment:
    requirement: Requirement
    status: CoverageStatus
    fulfillment_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementEvaluation:
    rule_assessments: Tuple[RuleAssessment, ...]
    requirements: Tuple[RequirementAssessment, ...]

    @property
    def requirements_satisfied(self) -> bool:
        """Whether this requirement slice is complete, not whole-trip readiness."""
        return all(
            item.status is CoverageStatus.COMPLETE for item in self.requirements
        ) and all(
            item.applicability is not Applicability.UNKNOWN
            for item in self.rule_assessments
        )


def _during(day: date, scope: Optional[TemporalScope]) -> bool:
    return scope is None or (
        (scope.starts_on is None or scope.starts_on <= day)
        and (scope.ends_on is None or day <= scope.ends_on)
    )


def _condition_value(dimension: str, context: PlanningContext) -> Any:
    if dimension == "trip_date":
        return context.trip_date
    if dimension == "trip_stage":
        kinds = [stage.kind for stage in context.stages]
        if context.activities.attributes.get("overnight") is True:
            # These are semantic planning stages, not invented geographic
            # legs. Existing canonical rules use them to gate overnight and
            # booking obligations across any resolved route direction.
            kinds.extend(("overnight", "booking", "campground_stay"))
        return tuple(dict.fromkeys(kinds))
    if dimension in ("activity", "trip_activity"):
        return context.activities.activities
    if dimension.startswith("activity."):
        return context.activities.attributes.get(dimension.split(".", 1)[1])

    for attributes in (
        context.party.attributes,
        context.activities.attributes,
        context.equipment.attributes,
    ):
        if dimension in attributes:
            return attributes[dimension]
    return None


def _compare(actual: Any, operator: str, expected: Any) -> Optional[bool]:
    if actual is None:
        return None
    if isinstance(actual, date) and isinstance(expected, str):
        try:
            expected = date.fromisoformat(expected)
        except ValueError:
            return None
    if operator == "equals":
        if isinstance(actual, (tuple, list, set, frozenset)):
            return expected in actual
        return actual == expected
    if operator == "contains":
        try:
            return expected in actual
        except TypeError:
            return False
    if operator == "in":
        try:
            return actual in expected
        except TypeError:
            return False
    try:
        if operator == "less_than":
            return actual < expected
        if operator == "less_than_or_equal":
            return actual <= expected
        if operator == "greater_than_or_equal":
            return actual >= expected
    except TypeError:
        return None
    return None


def assess_rule(rule: Rule, context: PlanningContext) -> RuleAssessment:
    if not _during(context.trip_date, rule.temporal_scope):
        return RuleAssessment(rule.rule_id, Applicability.DOES_NOT_APPLY,
                              "rule is not effective on the trip date")

    trip_scopes = {
        scope_id for stage in context.stages for scope_id in stage.spatial_scope_ids
    }
    if rule.spatial_scope_ids and not trip_scopes:
        return RuleAssessment(rule.rule_id, Applicability.UNKNOWN,
                              "trip context has no spatial scope")
    if rule.spatial_scope_ids and not trip_scopes.intersection(rule.spatial_scope_ids):
        return RuleAssessment(rule.rule_id, Applicability.DOES_NOT_APPLY,
                              "trip stages do not intersect the rule scope")

    unknown = []
    for condition in rule.conditions:
        result = _compare(_condition_value(condition.dimension, context),
                          condition.operator, condition.value)
        if result is False:
            return RuleAssessment(
                rule.rule_id, Applicability.DOES_NOT_APPLY,
                f"condition does not match: {condition.dimension}",
            )
        if result is None:
            unknown.append(condition.dimension)
    if unknown:
        return RuleAssessment(
            rule.rule_id, Applicability.UNKNOWN,
            "missing or unsupported context: " + ", ".join(sorted(unknown)),
        )
    return RuleAssessment(rule.rule_id, Applicability.APPLIES)


def requirement_for(rule: Rule, context: PlanningContext) -> Requirement:
    matching_stages = tuple(
        stage.stage_id for stage in sorted(context.stages, key=lambda item: item.sequence)
        if not rule.spatial_scope_ids
        or set(stage.spatial_scope_ids).intersection(rule.spatial_scope_ids)
    )
    return Requirement(
        requirement_id=f"requirement-{rule.rule_id.removeprefix('rule-')}",
        rule_id=rule.rule_id,
        description=rule.consequence,
        coverage=Coverage(
            participant_ids=context.party.participant_ids,
            stage_ids=matching_stages,
            starts_on=context.trip_date,
            ends_on=context.trip_date,
        ),
    )


def _dimension_complete(coverages: Sequence[Coverage], required: Tuple[str, ...],
                        attribute: str) -> bool:
    offered = [getattr(item, attribute) for item in coverages]
    if any(not values for values in offered):
        return True
    return set().union(*(set(values) for values in offered)).issuperset(required)


def _dates_complete(coverages: Sequence[Coverage], required: Coverage) -> bool:
    if required.starts_on is None and required.ends_on is None:
        return any(item.starts_on is None and item.ends_on is None for item in coverages)
    start = required.starts_on or date.min
    end = required.ends_on or date.max
    intervals = sorted(
        (item.starts_on or date.min, item.ends_on or date.max) for item in coverages
    )
    cursor = start
    for interval_start, interval_end in intervals:
        if interval_end < cursor:
            continue
        if interval_start > cursor:
            return False
        if interval_end >= end:
            return True
        cursor = interval_end + timedelta(days=1)
    return False


def _combined_coverage_contains(coverages: Sequence[Coverage], required: Coverage) -> bool:
    if not coverages:
        return False
    return all(
        _dimension_complete(coverages, getattr(required, attribute), attribute)
        for attribute in ("participant_ids", "equipment_ids", "stage_ids")
    ) and _dates_complete(coverages, required)


def _coverage_overlaps(offered: Coverage, required: Coverage) -> bool:
    for attribute in ("participant_ids", "equipment_ids", "stage_ids"):
        left = set(getattr(offered, attribute))
        right = set(getattr(required, attribute))
        if left and right and not left.intersection(right):
            return False
    left_start, left_end = offered.starts_on or date.min, offered.ends_on or date.max
    right_start, right_end = required.starts_on or date.min, required.ends_on or date.max
    return left_start <= right_end and right_start <= left_end


def assess_requirement(requirement: Requirement,
                       fulfillments: Iterable[Fulfillment]) -> RequirementAssessment:
    matches = tuple(
        item for item in fulfillments if item.requirement_id == requirement.requirement_id
    )
    if any(coverage_contains(item.coverage, requirement.coverage) for item in matches):
        status = CoverageStatus.COMPLETE
    elif _combined_coverage_contains([item.coverage for item in matches],
                                     requirement.coverage):
        status = CoverageStatus.COMPLETE
    elif any(_coverage_overlaps(item.coverage, requirement.coverage) for item in matches):
        status = CoverageStatus.PARTIAL
    else:
        status = CoverageStatus.MISSING
    return RequirementAssessment(
        requirement=requirement,
        status=status,
        fulfillment_ids=tuple(item.fulfillment_id for item in matches),
    )


def evaluate_requirements(rules: Iterable[Rule], context: PlanningContext,
                          fulfillments: Iterable[Fulfillment] = ()) -> RequirementEvaluation:
    """Evaluate rules without treating unknown applicability as permission."""
    rule_list = tuple(rules)
    fulfillment_list = tuple(fulfillments)
    assessments = tuple(assess_rule(rule, context) for rule in rule_list)
    rules_by_id: Mapping[str, Rule] = {rule.rule_id: rule for rule in rule_list}
    requirements = tuple(
        assess_requirement(requirement_for(rules_by_id[item.rule_id], context),
                           fulfillment_list)
        for item in assessments if item.applicability is Applicability.APPLIES
    )
    return RequirementEvaluation(assessments, requirements)
