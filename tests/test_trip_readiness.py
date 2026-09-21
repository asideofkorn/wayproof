"""Trip Readiness aggregation against the canonical Whitney fixtures."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical
from wayproof.readiness import ReadinessState, evaluate_trip_readiness
from wayproof.schema import (ActivityContext, Coverage, Fulfillment,
                             KnowledgeGap, PartyContext, PlanningContext, Rule,
                             Condition, TripObjective, TripStage)


ROOT = Path(__file__).resolve().parents[1]


def context(*, overnight=True, resolved=True):
    scopes = ("scope-route-whitney-classic", "scope-whitney-zone") if resolved else ()
    return PlanningContext(
        trip_date=date(2027, 8, 12),
        objectives=(TripObjective("summit", "peak-mount-whitney", "summit"),),
        stages=(TripStage("route", 1, "traverse", scopes),),
        party=PartyContext(participant_ids=("alice", "bob")),
        activities=ActivityContext(
            activities=("hiking",), attributes={"overnight": overnight}
        ),
    )


def permit(identifier, participants):
    return Fulfillment(
        identifier,
        "requirement-whitney-classic-overnight-permit",
        "permit",
        ("evidence-whitney-overnight-scope",),
        Coverage(
            participant_ids=participants,
            stage_ids=("route",),
            starts_on=date(2027, 8, 12),
            ends_on=date(2027, 8, 12),
        ),
    )


def sierra_records():
    records = load_canonical(ROOT)
    wanted = {
        "rule-whitney-zone-day-use-permit",
        "rule-whitney-classic-overnight-permit",
        "rule-north-fork-overnight-permit",
        "rule-shepherd-overnight-permit",
    }
    records.rules = [rule for rule in records.rules if rule.rule_id in wanted]
    return records


def test_missing_required_permit_blocks_readiness_with_provenance():
    result = evaluate_trip_readiness(sierra_records(), context())
    assert result.state is ReadinessState.BLOCKED
    assert result.rule_ids == ("rule-whitney-classic-overnight-permit",)
    assert result.claim_ids == ("claim-whitney-overnight-scope",)
    assert "evidence-whitney-overnight-scope" in result.evidence_ids
    assert "no fulfillment" in result.explanations[0]


def test_partial_party_coverage_is_partial_not_ready():
    result = evaluate_trip_readiness(
        sierra_records(), context(), (permit("alice-permit", ("alice",)),)
    )
    assert result.state is ReadinessState.PARTIAL
    assert "coverage is partial" in result.explanations[0]


def test_complete_party_coverage_is_ready_for_the_requirement_slice():
    result = evaluate_trip_readiness(
        sierra_records(), context(),
        (
            permit("alice-permit", ("alice",)),
            permit("bob-permit", ("bob",)),
        ),
    )
    assert result.state is ReadinessState.READY
    assert result.evaluation.requirements_satisfied
    assert result.explanations == (
        "all applicable requirements have complete coverage",
    )


def test_unresolved_route_is_unknown_instead_of_assumed_permit_free():
    result = evaluate_trip_readiness(sierra_records(), context(resolved=False))
    assert result.state is ReadinessState.UNKNOWN
    assert len(result.rule_ids) == 4
    assert all("spatial scope" in message for message in result.explanations)


def test_known_requirements_plus_unknown_applicability_are_partial():
    records = sierra_records()
    records.rules.append(Rule(
        "rule-whitney-unsupported-context",
        "claim-whitney-overnight-scope",
        "A second consequence whose context is not yet supported.",
        (Condition("unsupported_dimension", "equals", True),),
        ("scope-route-whitney-classic",),
    ))
    result = evaluate_trip_readiness(
        records,
        context(),
    )
    assert result.state is ReadinessState.PARTIAL
    assert result.evaluation.requirements


def test_no_applicable_rules_is_explicitly_not_applicable():
    records = sierra_records()
    trip = context()
    trip = PlanningContext(
        trip_date=trip.trip_date,
        objectives=trip.objectives,
        stages=(TripStage("elsewhere", 1, "traverse", ("scope-somewhere-else",)),),
        party=trip.party,
        activities=trip.activities,
    )
    result = evaluate_trip_readiness(records, trip)
    assert result.state is ReadinessState.NOT_APPLICABLE


def test_relevant_knowledge_gap_prevents_a_ready_result():
    records = sierra_records()
    records.gaps.append(KnowledgeGap(
        "gap-whitney-permit-verification",
        "Has the permit been independently verified?",
        ("rule-whitney-classic-overnight-permit",),
    ))
    result = evaluate_trip_readiness(
        records, context(),
        (
            permit("alice-permit", ("alice",)),
            permit("bob-permit", ("bob",)),
        ),
    )
    assert result.state is ReadinessState.PARTIAL
    assert result.gap_ids == ("gap-whitney-permit-verification",)
