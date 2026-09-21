"""Consumer-facing read service integration tests."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.read_service import CanonicalReadService
from wayproof.readiness import ReadinessState
from wayproof.recheck import RecheckAnswerability
from wayproof.schema import (ActivityContext, Coverage, Fulfillment,
                             PartyContext, PlanningContext, TripObjective,
                             TripStage)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


def whitney_context():
    return PlanningContext(
        trip_date=date(2027, 8, 12),
        objectives=(TripObjective("summit", "peak-mount-whitney", "summit"),),
        stages=(TripStage(
            "route", 1, "traverse",
            ("scope-route-whitney-classic", "scope-whitney-zone"),
        ),),
        party=PartyContext(participant_ids=("alice", "bob")),
        activities=ActivityContext(
            activities=("hiking",), attributes={"overnight": True}
        ),
    )


def test_entity_search_is_deterministic_and_filterable(reads):
    results = reads.search_entities("whitney", kinds=("peak",))
    assert [(item.entity_id, item.name) for item in results] == [
        ("peak-mount-whitney", "Mount Whitney")
    ]
    assert reads.entity("peak-mount-whitney") == results[0]


def test_unknown_records_fail_explicitly(reads):
    with pytest.raises(KeyError, match="unknown entity"):
        reads.entity("peak-does-not-exist")
    with pytest.raises(KeyError, match="unknown record type"):
        reads.get("table", "anything")


def test_entity_context_reads_are_deterministic_and_public(reads):
    entity_id = "park-del-valle-regional-park"
    claims = reads.claims_for(entity_id)
    assert claims
    assert all(item.subject_id == entity_id for item in claims)
    assert list(claims) == sorted(
        claims, key=lambda item: (item.predicate.casefold(), item.claim_id)
    )

    relationships = reads.relationships_for(entity_id)
    assert relationships
    assert all(entity_id in (item.subject_id, item.object_id)
               for item in relationships)

    gaps = reads.knowledge_gaps_for(entity_id)
    assert all(entity_id in item.related_ids for item in gaps)


def test_claim_explanation_traverses_the_complete_provenance_chain(reads):
    bundle = reads.explain_claim("claim-whitney-overnight-scope")
    assert bundle.claim.subject_id == "permit-whitney-trail-overnight"
    assert {item.claim_id for item in bundle.evidence} == {
        "claim-whitney-overnight-scope"
    }
    assert {item.source_id for item in bundle.observations} == {
        "source-recreationgov-mount-whitney"
    }
    assert {item.locator for item in bundle.sources} == {
        "https://www.recreation.gov/permits/445860"
    }


def test_published_changeset_history_is_available_by_record(reads):
    history = reads.changes(record_id="claim-whitney-overnight-scope")
    assert len(history) == 1
    assert history[0].change_set_id == "wp-20260920-sierra-reference-fixtures"
    assert history[0].record_type == "claim"
    assert history[0].evidence_refs == ("evidence-whitney-overnight-scope",)


def test_readiness_and_requirements_share_the_same_service_boundary(reads):
    context = whitney_context()
    requirement = reads.requirements(context).requirements[0].requirement
    fulfillment = Fulfillment(
        "group-permit",
        requirement.requirement_id,
        "permit",
        ("evidence-whitney-overnight-scope",),
        Coverage(
            participant_ids=("alice", "bob"),
            stage_ids=("route",),
            starts_on=context.trip_date,
            ends_on=context.trip_date,
        ),
    )
    assert reads.readiness(context, (fulfillment,)).state is ReadinessState.READY


def test_recheck_is_available_through_the_same_boundary(reads):
    context = PlanningContext(
        trip_date=date(2026, 9, 21),
        objectives=(TripObjective("visit", "park-del-valle-regional-park", "visit"),),
        stages=(TripStage("visit", 1, "visit", ("scope-del-valle-park",)),),
    )
    result = reads.pretrip_recheck(context)
    item = next(
        value for value in result.items
        if value.input_id == "claim-del-valle-volatile-alerts"
    )
    assert item.answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK


def test_service_is_read_only_by_contract(reads):
    assert not hasattr(reads, "propose")
    assert not hasattr(reads, "promote")
