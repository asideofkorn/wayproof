"""End-to-end tests for the controlled Canonical Schema v0 write path."""

from datetime import date, datetime, timezone

import pytest

from wayproof.schema import (
    CanonicalRecords,
    ChangeSet,
    ChangeSetStatus,
    Claim,
    DerivedResult,
    Entity,
    Evidence,
    KnowledgeGap,
    Observation,
    Source,
    SpatialScope,
    TemporalScope,
)
from wayproof.write_service import (
    ChangeSetWriteService,
    DuplicateChangeSet,
    InMemoryCanonicalRepository,
    PromotionRejected,
    UnknownChangeSet,
    WriteServiceError,
)


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def one_claim_change(change_id="change-1", entity_id="place-1"):
    records = CanonicalRecords(
        entities=[Entity(entity_id, "place", "Place One")],
        sources=[Source("source-" + entity_id, "https://example.test/source")],
        observations=[Observation(
            "observation-" + entity_id, "source-" + entity_id, "Place is open")],
        evidence=[Evidence(
            "evidence-" + entity_id, "observation-" + entity_id,
            "claim-" + entity_id)],
        claims=[Claim(
            "claim-" + entity_id, entity_id, "legal_status", "open",
            ("evidence-" + entity_id,))],
    )
    return ChangeSet(change_id, records)


def service():
    repository = InMemoryCanonicalRepository()
    return repository, ChangeSetWriteService(repository, clock=lambda: NOW)


def test_repository_snapshots_cannot_mutate_canonical_state():
    repository = InMemoryCanonicalRepository()
    snapshot = repository.snapshot()
    snapshot.entities.append(Entity("outside", "place", "Outside"))
    assert repository.snapshot().entities == []


def test_propose_stores_a_defensive_copy_and_rejects_duplicate_ids():
    _, writes = service()
    candidate = one_claim_change()
    writes.propose(candidate, "researcher")
    candidate.records.entities.append(Entity("late", "place", "Late mutation"))
    assert [entity.entity_id for entity in writes.get("change-1").records.entities] == [
        "place-1"]
    with pytest.raises(DuplicateChangeSet):
        writes.propose(one_claim_change(), "researcher")


def test_actor_is_required_before_any_state_changes():
    _, writes = service()
    with pytest.raises(WriteServiceError, match="identified actor"):
        writes.propose(one_claim_change(), " ")
    with pytest.raises(UnknownChangeSet):
        writes.get("change-1")


def test_audit_clock_failure_cannot_leave_an_unaudited_proposal():
    repository = InMemoryCanonicalRepository()

    def broken_clock():
        raise RuntimeError("clock unavailable")

    writes = ChangeSetWriteService(repository, clock=broken_clock)
    with pytest.raises(RuntimeError, match="clock unavailable"):
        writes.propose(one_claim_change(), "researcher")
    with pytest.raises(UnknownChangeSet):
        writes.get("change-1")
    assert writes.audit_log() == ()


def test_explain_lists_exact_additions_without_mutating_status():
    _, writes = service()
    writes.propose(one_claim_change(), "researcher")
    explanation = writes.explain("change-1")
    assert explanation.status is ChangeSetStatus.DRAFT
    assert explanation.validation_errors == ()
    assert explanation.addition_count == 5
    assert ("claims", ("claim-place-1",)) in explanation.additions
    assert writes.get("change-1").status is ChangeSetStatus.DRAFT


def test_full_lifecycle_promotes_atomically_and_records_every_transition():
    repository, writes = service()
    writes.propose(one_claim_change(), "researcher")
    assert writes.validate("change-1", "validator") == ()
    writes.approve("change-1", "human-reviewer", "source checked")
    writes.promote("change-1", "promoter")

    assert writes.get("change-1").status is ChangeSetStatus.PROMOTED
    assert [entity.entity_id for entity in repository.snapshot().entities] == [
        "place-1"]
    events = writes.audit_log("change-1")
    assert [event.action for event in events] == [
        "proposed", "validated", "approved", "promoted"]
    assert [event.sequence for event in events] == [1, 2, 3, 4]
    assert all(event.occurred_at == NOW for event in events)
    assert events[2].note == "source checked"


def test_invalid_change_stays_out_of_canonical_state_and_is_audited():
    repository, writes = service()
    invalid = ChangeSet("bad", CanonicalRecords(
        claims=[Claim("claim-1", "missing", "status", "open", ())]))
    writes.propose(invalid, "researcher")
    errors = writes.validate("bad", "validator")
    assert errors
    assert writes.get("bad").status is ChangeSetStatus.DRAFT
    assert repository.snapshot() == CanonicalRecords()
    event = writes.audit_log("bad")[-1]
    assert event.action == "validation_failed"
    assert event.from_status is event.to_status is ChangeSetStatus.DRAFT
    assert event.errors == errors


def test_concurrent_id_collision_rejects_the_second_promotion_without_partial_write():
    repository, writes = service()
    writes.propose(one_claim_change("first"), "researcher")
    writes.propose(one_claim_change("second"), "researcher")
    for change_id in ("first", "second"):
        assert writes.validate(change_id, "validator") == ()
        writes.approve(change_id, "reviewer")

    writes.promote("first", "promoter")
    before = repository.snapshot()
    with pytest.raises(PromotionRejected, match="already exists"):
        writes.promote("second", "promoter")
    assert repository.snapshot() == before
    assert writes.get("second").status is ChangeSetStatus.APPROVED
    assert writes.audit_log("second")[-1].action == "promotion_rejected"


def test_returned_changesets_cannot_mutate_the_stored_proposal():
    _, writes = service()
    returned = writes.propose(one_claim_change(), "researcher")
    returned.records.entities.clear()
    fetched = writes.get("change-1")
    fetched.records.entities.clear()
    assert len(writes.get("change-1").records.entities) == 1


def test_california_14ers_social_water_evidence_runs_end_to_end():
    """Messy social evidence remains bounded and never implies current flow."""
    repository, writes = service()
    thread_url = (
        "https://m.facebook.com/groups/307870769581548/"
        "permalink/2926262804408985/"
    )
    records = CanonicalRecords(
        entities=[
            Entity("water-birch-creek", "water_source", "Birch Creek"),
            Entity("water-cabin-creek", "water_source", "Cabin Creek"),
        ],
        spatial_scopes=[
            SpatialScope("scope-birch", "water_source",
                         entity_id="water-birch-creek"),
            SpatialScope("scope-cabin-report", "reported_location",
                         description="Cabin Creek report; exact route fit uncertain"),
        ],
        sources=[Source("source-facebook-thread", thread_url,
                        publisher="California 14ers Facebook group")],
        observations=[
            Observation(
                "observation-birch-historical", "source-facebook-thread",
                "Reporter described Birch Creek as reliable historically",
                retrieved_at=NOW, observer="social reporter A",
                artifact_refs=("screenshot-1",)),
            Observation(
                "observation-cabin-2026-08", "source-facebook-thread",
                "Reporter described flowing water at a Cabin Creek location",
                observed_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
                retrieved_at=NOW, observer="social reporter B",
                artifact_refs=("screenshot-3",)),
        ],
        evidence=[
            Evidence("evidence-birch", "observation-birch-historical",
                     "claim-birch-historical"),
            Evidence("evidence-cabin", "observation-cabin-2026-08",
                     "claim-cabin-2026-08"),
        ],
        claims=[
            Claim("claim-birch-historical", "water-birch-creek",
                  "reported_water_reliability", "historically reliable",
                  ("evidence-birch",), spatial_scope_ids=("scope-birch",)),
            Claim("claim-cabin-2026-08", "water-cabin-creek",
                  "reported_water_availability", "flowing",
                  ("evidence-cabin",),
                  temporal_scope=TemporalScope(date(2026, 8, 15),
                                               date(2026, 8, 15)),
                  spatial_scope_ids=("scope-cabin-report",)),
        ],
        gaps=[
            KnowledgeGap(
                "gap-birch-observed-date",
                "When was Birch Creek directly observed?",
                ("claim-birch-historical",), "report supplied no observation date"),
            KnowledgeGap(
                "gap-cabin-route-fit",
                "Does the Cabin Creek report match the planned crossing?",
                ("claim-cabin-2026-08", "scope-cabin-report"),
                "reported location may be lower on the drainage"),
        ],
        derived_results=[DerivedResult(
            "result-current-water", "answerability", "needs_current_check",
            ("claim-birch-historical", "claim-cabin-2026-08",
             "gap-birch-observed-date", "gap-cabin-route-fit"),
            "Neither report establishes current water for a future trip")],
    )
    change = ChangeSet("water-california-14ers-thread", records)

    writes.propose(change, "agent-researcher")
    explanation = writes.explain(change.change_set_id)
    assert explanation.addition_count == 14
    assert explanation.validation_errors == ()
    assert writes.validate(change.change_set_id, "schema-validator") == ()
    writes.approve(change.change_set_id, "human-reviewer",
                   "observations preserved without inferring current flow")
    writes.promote(change.change_set_id, "canonical-promoter")

    canonical = repository.snapshot()
    assert canonical.derived_results[0].value == "needs_current_check"
    assert len(canonical.observations) == 2
    assert len(canonical.gaps) == 2
    assert [event.action for event in writes.audit_log(change.change_set_id)] == [
        "proposed", "validated", "approved", "promoted"]
