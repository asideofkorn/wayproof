"""Real rule-to-requirement-to-fulfillment evaluation regressions."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical
from wayproof.requirements import (Applicability, CoverageStatus,
                                   evaluate_requirements)
from wayproof.schema import (ActivityContext, Coverage, Fulfillment,
                             PartyContext, PlanningContext, TripObjective,
                             TripStage)


ROOT = Path(__file__).resolve().parents[1]


def whitney_context(*, overnight: bool, scope: str) -> PlanningContext:
    return PlanningContext(
        trip_date=date(2027, 8, 12),
        objectives=(TripObjective("summit-whitney", "peak-mount-whitney", "summit"),),
        stages=(TripStage("whitney-route", 1, "traverse", (scope, "scope-whitney-zone")),),
        party=PartyContext(participant_ids=("alice", "bob")),
        activities=ActivityContext(
            activities=("hiking",), attributes={"overnight": overnight}
        ),
    )


def sierra_rules():
    return tuple(
        rule for rule in load_canonical(ROOT).rules
        if rule.rule_id in {
            "rule-whitney-zone-day-use-permit",
            "rule-whitney-classic-overnight-permit",
            "rule-north-fork-overnight-permit",
            "rule-shepherd-overnight-permit",
        }
    )


def fulfillment(identifier: str, requirement_id: str, participants):
    return Fulfillment(
        identifier,
        requirement_id,
        "permit",
        ("evidence-whitney-overnight-scope",),
        Coverage(
            participant_ids=participants,
            stage_ids=("whitney-route",),
            starts_on=date(2027, 8, 12),
            ends_on=date(2027, 8, 12),
        ),
    )


def test_classic_overnight_trip_selects_only_the_classic_overnight_rule():
    result = evaluate_requirements(
        sierra_rules(),
        whitney_context(overnight=True, scope="scope-route-whitney-classic"),
    )
    applicable = {
        item.rule_id for item in result.rule_assessments
        if item.applicability is Applicability.APPLIES
    }
    assert applicable == {"rule-whitney-classic-overnight-permit"}
    assert len(result.requirements) == 1
    assert result.requirements[0].status is CoverageStatus.MISSING
    assert not result.requirements_satisfied


def test_one_persons_permit_is_visible_as_partial_party_coverage():
    context = whitney_context(overnight=True, scope="scope-route-whitney-classic")
    result = evaluate_requirements(
        sierra_rules(), context,
        (fulfillment("alice-permit", "requirement-whitney-classic-overnight-permit",
                     ("alice",)),),
    )
    assessment = result.requirements[0]
    assert assessment.requirement.coverage.participant_ids == ("alice", "bob")
    assert assessment.status is CoverageStatus.PARTIAL
    assert not result.requirements_satisfied


def test_multiple_fulfillments_can_cover_one_requirement_together():
    context = whitney_context(overnight=True, scope="scope-route-whitney-classic")
    result = evaluate_requirements(
        sierra_rules(), context,
        (
            fulfillment("alice-permit", "requirement-whitney-classic-overnight-permit",
                        ("alice",)),
            fulfillment("bob-permit", "requirement-whitney-classic-overnight-permit",
                        ("bob",)),
        ),
    )
    assert result.requirements[0].status is CoverageStatus.COMPLETE
    assert result.requirements_satisfied


def test_north_fork_overnight_does_not_inherit_the_classic_permit_rule():
    result = evaluate_requirements(
        sierra_rules(),
        whitney_context(overnight=True, scope="scope-route-north-fork-lone-pine"),
    )
    applicable = {
        item.rule_id for item in result.rule_assessments
        if item.applicability is Applicability.APPLIES
    }
    assert applicable == {"rule-north-fork-overnight-permit"}


def test_missing_context_is_unknown_and_never_makes_the_trip_ready():
    context = whitney_context(overnight=True, scope="scope-route-whitney-classic")
    context = PlanningContext(
        trip_date=context.trip_date,
        objectives=context.objectives,
        stages=context.stages,
        party=context.party,
        activities=ActivityContext(activities=("hiking",)),
    )
    result = evaluate_requirements(sierra_rules(), context)
    assert any(
        item.applicability is Applicability.UNKNOWN
        and "activity.overnight" in item.reason
        for item in result.rule_assessments
    )
    assert not result.requirements_satisfied


def test_missing_spatial_projection_is_unknown_not_not_applicable():
    context = whitney_context(overnight=True, scope="scope-route-whitney-classic")
    context = PlanningContext(
        trip_date=context.trip_date,
        objectives=context.objectives,
        stages=(TripStage("unresolved-route", 1, "traverse"),),
        party=context.party,
        activities=context.activities,
    )
    result = evaluate_requirements(sierra_rules(), context)
    assert all(
        item.applicability is Applicability.UNKNOWN
        for item in result.rule_assessments
    )
    assert not result.requirements_satisfied


def test_day_trip_uses_the_zone_rule_for_either_whitney_route():
    for scope in ("scope-route-whitney-classic", "scope-route-north-fork-lone-pine"):
        result = evaluate_requirements(
            sierra_rules(), whitney_context(overnight=False, scope=scope)
        )
        assert [item.requirement.rule_id for item in result.requirements] == [
            "rule-whitney-zone-day-use-permit"
        ]
