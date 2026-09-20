"""Tests for preparing Git-backed Canonical Schema v0 candidates."""

from datetime import date, datetime, timezone

import pytest

from wayproof.schema import (
    CanonicalRecords,
    ChangeAction,
    ChangeOperation,
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
    PreparationRejected,
    UnknownChangeSet,
    WriteServiceError,
)


NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def add_operation(record_type, record_id, reason="Add source-backed knowledge"):
    collections = {
        "entity": "entities", "spatial_scope": "spatial_scopes",
        "source": "sources", "observation": "observations",
        "evidence": "evidence", "claim": "claims",
        "relationship": "relationships", "rule": "rules",
        "requirement": "requirements", "fulfillment": "fulfillments",
        "gap": "gaps", "derived_result": "derived_results",
    }
    collection = collections[record_type]
    return ChangeOperation(
        ChangeAction.ADD, record_type, record_id,
        f"canonical/v0/{collection}/{record_id}.json", reason)


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
    ids = (
        ("entity", entity_id),
        ("source", "source-" + entity_id),
        ("observation", "observation-" + entity_id),
        ("evidence", "evidence-" + entity_id),
        ("claim", "claim-" + entity_id),
    )
    return ChangeSet(
        change_id, records, summary="Add an open-status claim",
        operations=tuple(add_operation(kind, item_id) for kind, item_id in ids))


def service(initial=None):
    repository = InMemoryCanonicalRepository(initial)
    return repository, ChangeSetWriteService(repository, clock=lambda: NOW)


def test_repository_snapshots_cannot_mutate_canonical_base():
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


def test_workflow_clock_failure_cannot_leave_an_unlogged_proposal():
    repository = InMemoryCanonicalRepository()

    def broken_clock():
        raise RuntimeError("clock unavailable")

    writes = ChangeSetWriteService(repository, clock=broken_clock)
    with pytest.raises(RuntimeError, match="clock unavailable"):
        writes.propose(one_claim_change(), "researcher")
    with pytest.raises(UnknownChangeSet):
        writes.get("change-1")
    assert writes.workflow_log() == ()


def test_explain_lists_domain_operations_without_mutating_status():
    _, writes = service()
    writes.propose(one_claim_change(), "researcher")
    explanation = writes.explain("change-1")
    assert explanation.status is ChangeSetStatus.DRAFT
    assert explanation.validation_errors == ()
    assert explanation.addition_count == 5
    assert len(explanation.operations) == 5
    assert explanation.summary == "Add an open-status claim"
    assert writes.get("change-1").status is ChangeSetStatus.DRAFT


def test_prepare_requires_operations_to_account_for_every_candidate_record():
    _, writes = service()
    change = one_claim_change()
    change.operations = change.operations[:-1]
    writes.propose(change, "researcher")
    assert writes.validate("change-1", "validator") == ()
    explanation = writes.explain("change-1")
    assert "candidate record has no ADD operation: claim:claim-place-1" in (
        explanation.validation_errors)
    with pytest.raises(PreparationRejected, match="no ADD operation"):
        writes.prepare("change-1", "candidate-builder")


def test_prepare_builds_a_detached_candidate_without_publishing_it():
    repository, writes = service()
    writes.propose(one_claim_change(), "researcher")
    assert writes.validate("change-1", "validator") == ()
    prepared = writes.prepare("change-1", "candidate-builder")

    assert writes.get("change-1").status is ChangeSetStatus.VALIDATED
    assert repository.snapshot() == CanonicalRecords()
    assert prepared.base == CanonicalRecords()
    assert [entity.entity_id for entity in prepared.result.entities] == ["place-1"]
    assert len(prepared.operations) == 5
    assert [event.action for event in writes.workflow_log("change-1")] == [
        "proposed", "validated", "prepared"]
    assert all(event.occurred_at == NOW
               for event in writes.workflow_log("change-1"))


def test_invalid_change_cannot_be_prepared():
    repository, writes = service()
    invalid = ChangeSet("bad", CanonicalRecords(
        claims=[Claim("claim-1", "missing", "status", "open", ())]))
    writes.propose(invalid, "researcher")
    assert writes.validate("bad", "validator")
    with pytest.raises(PreparationRejected, match="validated"):
        writes.prepare("bad", "candidate-builder")
    assert repository.snapshot() == CanonicalRecords()


def test_a_changed_canonical_base_rejects_candidate_preparation():
    existing = one_claim_change("existing", "place-1").records
    _, writes = service(initial=existing)
    duplicate = one_claim_change("duplicate", "place-1")
    writes.propose(duplicate, "researcher")
    errors = writes.validate("duplicate", "validator")
    assert any("already exists" in error for error in errors)
    with pytest.raises(PreparationRejected):
        writes.prepare("duplicate", "candidate-builder")


def test_returned_changesets_cannot_mutate_the_stored_proposal():
    _, writes = service()
    returned = writes.propose(one_claim_change(), "researcher")
    returned.records.entities.clear()
    fetched = writes.get("change-1")
    fetched.records.entities.clear()
    assert len(writes.get("change-1").records.entities) == 1


def test_california_14ers_social_water_evidence_prepares_for_git_review():
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
                  "reported_water_availability", "flowing", ("evidence-cabin",),
                  temporal_scope=TemporalScope(date(2026, 8, 15),
                                               date(2026, 8, 15)),
                  spatial_scope_ids=("scope-cabin-report",)),
        ],
        gaps=[
            KnowledgeGap("gap-birch-observed-date",
                         "When was Birch Creek directly observed?",
                         ("claim-birch-historical",),
                         "report supplied no observation date"),
            KnowledgeGap("gap-cabin-route-fit",
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
    operations = tuple(
        add_operation(kind, item_id, "Preserve social water evidence")
        for kind, item_id in (
            ("entity", "water-birch-creek"),
            ("entity", "water-cabin-creek"),
            ("spatial_scope", "scope-birch"),
            ("spatial_scope", "scope-cabin-report"),
            ("source", "source-facebook-thread"),
            ("observation", "observation-birch-historical"),
            ("observation", "observation-cabin-2026-08"),
            ("evidence", "evidence-birch"),
            ("evidence", "evidence-cabin"),
            ("claim", "claim-birch-historical"),
            ("claim", "claim-cabin-2026-08"),
            ("gap", "gap-birch-observed-date"),
            ("gap", "gap-cabin-route-fit"),
            ("derived_result", "result-current-water"),
        )
    )
    change = ChangeSet(
        "wp-20260920-water14ers", records,
        summary="Preserve dated social water evidence without claiming current flow",
        operations=operations)

    writes.propose(change, "agent-researcher")
    assert writes.validate(change.change_set_id, "schema-validator") == ()
    prepared = writes.prepare(change.change_set_id, "candidate-builder")

    assert repository.snapshot() == CanonicalRecords()
    assert prepared.result.derived_results[0].value == "needs_current_check"
    assert len(prepared.result.observations) == 2
    assert len(prepared.result.gaps) == 2
    assert [event.action for event in writes.workflow_log(change.change_set_id)] == [
        "proposed", "validated", "prepared"]
