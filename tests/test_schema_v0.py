"""Canonical Schema v0 foundation and controlled-write tests."""

from datetime import date, datetime

import pytest

from wayproof.schema import (
    CanonicalRecords,
    ChangeSet,
    ChangeSetStatus,
    Claim,
    Condition,
    Coverage,
    DerivedResult,
    Entity,
    EquipmentContext,
    Evidence,
    Fulfillment,
    KnowledgeGap,
    Observation,
    PlanningContext,
    Requirement,
    Rule,
    Source,
    SpatialScope,
    TemporalScope,
    TripObjective,
    TripStage,
    coverage_contains,
)
from wayproof.validation import validate_records


def evidence_chain(predicate="status", value="open", *, claim_id="claim-1",
                   entity_id="place-1", observed_at=None, temporal_scope=None):
    return CanonicalRecords(
        entities=[Entity(entity_id, "place", "Place One")],
        sources=[Source("source-1", "https://example.test/source")],
        observations=[Observation("observation-1", "source-1", "reported value",
                                  observed_at=observed_at)],
        evidence=[Evidence("evidence-1", "observation-1", claim_id)],
        claims=[Claim(claim_id, entity_id, predicate, value, ("evidence-1",),
                      temporal_scope=temporal_scope)],
    )


def test_a_complete_evidence_chain_validates():
    assert validate_records(evidence_chain()) == []


def test_claims_cannot_become_canonical_without_evidence():
    records = CanonicalRecords(
        entities=[Entity("road-1", "road", "Road One")],
        claims=[Claim("claim-1", "road-1", "legal_status", "open", ())],
    )
    assert "claim claim-1 requires evidence" in validate_records(records)


def test_dangling_and_misdirected_evidence_is_rejected():
    records = evidence_chain()
    records.claims[0] = Claim("claim-1", "place-1", "status", "open",
                              ("missing",))
    errors = validate_records(records)
    assert "claim claim-1 references unknown id: missing" in errors

    records = evidence_chain()
    records.evidence[0] = Evidence("evidence-1", "observation-1", "another-claim")
    errors = validate_records(records)
    assert "evidence evidence-1 references unknown id: another-claim" in errors
    assert "claim claim-1 cites evidence evidence-1 for claim another-claim" in errors


def test_temporal_intervals_cannot_run_backwards():
    records = evidence_chain(temporal_scope=TemporalScope(
        starts_on=date(2027, 2, 1), ends_on=date(2027, 1, 1)))
    assert "claim claim-1 starts after it ends" in validate_records(records)


def test_incremental_validation_resolves_existing_ids_but_rejects_collisions():
    existing = CanonicalRecords(
        entities=[Entity("place-1", "place", "Place One")],
        sources=[Source("source-1", "https://example.test/source")],
    )
    proposed = CanonicalRecords(
        observations=[Observation("observation-1", "source-1", "new report")]
    )
    assert validate_records(proposed, existing=existing) == []
    proposed.entities.append(Entity("place-1", "place", "Duplicate"))
    assert "entity id already exists: place-1" in validate_records(
        proposed, existing=existing)


def test_changeset_lifecycle_is_enforced():
    change = ChangeSet("change-1", evidence_chain())
    with pytest.raises(ValueError, match="validated"):
        change.approve("reviewer")
    with pytest.raises(ValueError, match="approved"):
        change.promote()

    assert change.validate() == ()
    assert change.status is ChangeSetStatus.VALIDATED
    with pytest.raises(ValueError, match="identified reviewer"):
        change.approve(" ")
    change.approve("human-reviewer", "evidence checked")
    assert change.status is ChangeSetStatus.APPROVED
    change.promote()
    assert change.status is ChangeSetStatus.PROMOTED
    assert change.approved_by == "human-reviewer"


def test_failed_validation_remains_a_draft():
    change = ChangeSet("change-1", CanonicalRecords(
        claims=[Claim("claim-1", "missing", "status", "open", ())]))
    assert change.validate()
    assert change.status is ChangeSetStatus.DRAFT
    assert change.validation_errors


def test_requirement_coverage_detects_partial_fulfillment():
    required = Coverage(participant_ids=("a", "b"), stage_ids=("entry", "camp"),
                        starts_on=date(2027, 7, 1), ends_on=date(2027, 7, 3))
    partial = Coverage(participant_ids=("a",), stage_ids=("entry",),
                       starts_on=date(2027, 7, 1), ends_on=date(2027, 7, 2))
    complete = Coverage(participant_ids=("a", "b"),
                        stage_ids=("entry", "camp", "exit"),
                        starts_on=date(2027, 6, 30), ends_on=date(2027, 7, 3))
    assert not coverage_contains(partial, required)
    assert coverage_contains(complete, required)
    assert not coverage_contains(
        Coverage(participant_ids=("a",)), Coverage(participant_ids=()))
    assert coverage_contains(
        Coverage(participant_ids=()), Coverage(participant_ids=("a", "b")))


def test_planning_context_supports_objectives_stages_party_activity_and_history():
    context = PlanningContext(
        trip_date=date(2027, 7, 1),
        objectives=(TripObjective("objective-1", "lake-b", "boating"),),
        stages=(TripStage("launch", 1, "launch", ("scope-lake-b",)),),
        equipment=EquipmentContext(
            equipment_ids=("boat-1",),
            prior_events=("boat-1 visited lake-a on 2027-06-30",),
        ),
    )
    assert context.objectives[0].kind == "boating"
    assert context.equipment.prior_events


# The eight frozen adversarial cases below are representability regressions.
# Resolution policy arrives in M1; M0 proves the cases need no special-purpose
# schema object and remain explicit enough for deterministic validation.


def test_adversarial_1_legal_access_and_physical_condition_are_separate_claims():
    records = _two_claims("legal_access_status", "open",
                          "physical_condition", "washout")
    assert validate_records(records) == []


def test_adversarial_2_facility_existence_and_water_availability_are_separate():
    records = _two_claims("facility_type", "spigot",
                          "water_availability", "dry")
    records.claims[1] = Claim(
        "claim-2", "place-1", "water_availability", "dry", ("evidence-2",),
        temporal_scope=TemporalScope(date(2027, 9, 17), date(2027, 9, 17)))
    assert validate_records(records) == []


def test_adversarial_3_partial_route_keeps_known_endpoints_and_a_gap():
    records = evidence_chain(predicate="entry_status")
    records.entities.extend([
        Entity("entry-1", "access_point", "Entry"),
        Entity("exit-1", "access_point", "Exit"),
    ])
    records.gaps.append(KnowledgeGap(
        "gap-route", "Which traversal connects the known endpoints?",
        ("entry-1", "exit-1"), "endpoints do not determine a route"))
    assert validate_records(records) == []


def test_adversarial_4_coverage_mismatch_stays_unsatisfied():
    assert not coverage_contains(
        Coverage(participant_ids=("one",), stage_ids=("entry",)),
        Coverage(participant_ids=("one", "two"), stage_ids=("entry", "camp")),
    )


def test_adversarial_5_supersession_preserves_historical_claims():
    records = _two_claims("entry_rule", "old", "entry_rule", "new")
    records.claims[0] = Claim(
        "claim-1", "place-1", "entry_rule", "old", ("evidence-1",),
        temporal_scope=TemporalScope(None, date(2026, 12, 31)))
    records.claims[1] = Claim(
        "claim-2", "place-1", "entry_rule", "new", ("evidence-2",),
        temporal_scope=TemporalScope(date(2027, 1, 1), None))
    assert validate_records(records) == []


def test_adversarial_6_unknown_and_unavailable_have_different_records():
    records = evidence_chain(predicate="inventory_status", value="unavailable")
    records.gaps.append(KnowledgeGap(
        "gap-live-inventory", "Can current inventory be checked?",
        ("claim-1",), "live system not queried"))
    assert validate_records(records) == []


def test_adversarial_7_compound_scope_uses_general_conditions():
    records = evidence_chain(predicate="launch_protocol", value="required")
    records.spatial_scopes.append(SpatialScope(
        "scope-1", "route_segment", description="Lake B launch ramp"))
    records.rules.append(Rule(
        "rule-1", "claim-1", "inspection required",
        conditions=(
            Condition("activity", "equals", "boating"),
            Condition("equipment.type", "equals", "trailered_motorboat"),
            Condition("equipment.history.waterbody", "in", "high_risk"),
        ),
        spatial_scope_ids=("scope-1",),
    ))
    assert validate_records(records) == []


def test_adversarial_8_disagreement_preserves_both_observations():
    records = _two_claims("water_availability", "flowing",
                          "water_availability", "dry")
    records.derived_results.append(DerivedResult(
        "result-1", "answerability", "conflicting",
        ("claim-1", "claim-2"), "same predicate and date, incompatible values"))
    assert validate_records(records) == []


def _two_claims(predicate_1, value_1, predicate_2, value_2):
    return CanonicalRecords(
        entities=[Entity("place-1", "place", "Place One")],
        sources=[
            Source("source-1", "https://example.test/one"),
            Source("source-2", "https://example.test/two"),
        ],
        observations=[
            Observation("observation-1", "source-1", "first report",
                        observed_at=datetime(2027, 9, 18, 10, 0)),
            Observation("observation-2", "source-2", "second report",
                        observed_at=datetime(2027, 9, 18, 11, 0)),
        ],
        evidence=[
            Evidence("evidence-1", "observation-1", "claim-1"),
            Evidence("evidence-2", "observation-2", "claim-2"),
        ],
        claims=[
            Claim("claim-1", "place-1", predicate_1, value_1, ("evidence-1",)),
            Claim("claim-2", "place-1", predicate_2, value_2, ("evidence-2",)),
        ],
    )
