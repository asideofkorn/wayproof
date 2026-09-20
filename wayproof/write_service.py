"""Prepare validated canonical candidates for Git-backed publication.

Wayproof owns domain intent and validation. Git owns content identity and exact
diffs; GitHub owns review; merging to main publishes the change. This service
therefore never approves, promotes, or mutates canonical storage.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from .schema import (CanonicalRecords, ChangeAction, ChangeOperation, ChangeSet,
                     ChangeSetStatus)
from .validation import validate_records


class WriteServiceError(ValueError):
    """Base class for rejected candidate-preparation operations."""


class UnknownChangeSet(WriteServiceError):
    pass


class DuplicateChangeSet(WriteServiceError):
    pass


class PreparationRejected(WriteServiceError):
    pass


@dataclass(frozen=True)
class WorkflowEvent:
    """Ephemeral local workflow history; Git is the publication ledger."""

    sequence: int
    change_set_id: str
    action: str
    actor: str
    occurred_at: datetime
    from_status: ChangeSetStatus
    to_status: ChangeSetStatus
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangeSetExplanation:
    change_set_id: str
    status: ChangeSetStatus
    summary: str
    additions: Tuple[Tuple[str, Tuple[str, ...]], ...]
    operations: Tuple[ChangeOperation, ...]
    validation_errors: Tuple[str, ...]

    @property
    def addition_count(self) -> int:
        return sum(len(ids) for _, ids in self.additions)


@dataclass(frozen=True)
class PreparedCandidate:
    """Detached result ready to serialize, commit, and submit as a PR."""

    change_set_id: str
    base: CanonicalRecords
    result: CanonicalRecords
    operations: Tuple[ChangeOperation, ...]


_ID_ATTRIBUTES = {
    "entities": "entity_id",
    "spatial_scopes": "scope_id",
    "sources": "source_id",
    "observations": "observation_id",
    "evidence": "evidence_id",
    "claims": "claim_id",
    "relationships": "relationship_id",
    "rules": "rule_id",
    "requirements": "requirement_id",
    "fulfillments": "fulfillment_id",
    "gaps": "gap_id",
    "derived_results": "result_id",
}

_RECORD_TYPES = {
    "entity": ("entities", "entity_id"),
    "spatial_scope": ("spatial_scopes", "scope_id"),
    "source": ("sources", "source_id"),
    "observation": ("observations", "observation_id"),
    "evidence": ("evidence", "evidence_id"),
    "claim": ("claims", "claim_id"),
    "relationship": ("relationships", "relationship_id"),
    "rule": ("rules", "rule_id"),
    "requirement": ("requirements", "requirement_id"),
    "fulfillment": ("fulfillments", "fulfillment_id"),
    "gap": ("gaps", "gap_id"),
    "derived_result": ("derived_results", "result_id"),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _combined(left: CanonicalRecords,
              right: CanonicalRecords) -> CanonicalRecords:
    values = {}
    for definition in fields(CanonicalRecords):
        values[definition.name] = (
            deepcopy(getattr(left, definition.name))
            + deepcopy(getattr(right, definition.name))
        )
    return CanonicalRecords(**values)


def _operation_errors(change: ChangeSet, base: CanonicalRecords) -> Tuple[str, ...]:
    """Check that typed intent exactly accounts for the additive candidate."""
    errors = []
    if not change.summary.strip():
        errors.append("ChangeSet summary must not be blank")
    candidate_targets = set()
    existing_targets = set()
    for record_type, (collection, attribute) in _RECORD_TYPES.items():
        candidate_targets.update(
            (record_type, getattr(item, attribute))
            for item in getattr(change.records, collection))
        existing_targets.update(
            (record_type, getattr(item, attribute))
            for item in getattr(base, collection)
        )

    operation_targets = [(operation.record_type, operation.record_id)
                         for operation in change.operations]
    if len(operation_targets) != len(set(operation_targets)):
        errors.append("ChangeSet operations repeat a record target")
    paths = [operation.path for operation in change.operations]
    if len(paths) != len(set(paths)):
        errors.append("ChangeSet operations repeat a canonical path")

    add_targets = set()
    for operation in change.operations:
        target = (operation.record_type, operation.record_id)
        if operation.record_type not in _RECORD_TYPES:
            errors.append(f"unknown operation record type: {operation.record_type}")
            continue
        collection, _ = _RECORD_TYPES[operation.record_type]
        expected_path = f"canonical/v0/{collection}/{operation.record_id}.json"
        if operation.path != expected_path:
            errors.append(f"operation path must be {expected_path}")
        if operation.action is ChangeAction.ADD:
            add_targets.add(target)
            if target not in candidate_targets:
                errors.append(f"ADD operation has no candidate record: {operation.record_id}")
        elif operation.action in (ChangeAction.REPLACE, ChangeAction.REMOVE):
            if target not in existing_targets:
                errors.append(f"{operation.action.value} targets missing record: "
                              f"{operation.record_id}")
            errors.append(f"{operation.action.value} preparation is deferred to "
                          "the Git storage adapter")

    missing = sorted(candidate_targets - add_targets)
    extra = sorted(add_targets - candidate_targets)
    errors.extend(f"candidate record has no ADD operation: {kind}:{record_id}"
                  for kind, record_id in missing)
    errors.extend(f"ADD operation has no candidate record: {kind}:{record_id}"
                  for kind, record_id in extra)

    evidence_ids = {item.evidence_id for item in base.evidence + change.records.evidence}
    gap_ids = {item.gap_id for item in base.gaps + change.records.gaps}
    for operation in change.operations:
        for reference in operation.evidence_refs:
            if reference not in evidence_ids:
                errors.append(f"operation references unknown evidence: {reference}")
        for reference in operation.knowledge_gap_refs:
            if reference not in gap_ids:
                errors.append(f"operation references unknown knowledge gap: {reference}")
    return tuple(sorted(set(errors)))


class InMemoryCanonicalRepository:
    """A read-only canonical base used while preparing a Git candidate."""

    def __init__(self, initial: Optional[CanonicalRecords] = None) -> None:
        records = deepcopy(initial or CanonicalRecords())
        errors = validate_records(records)
        if errors:
            raise ValueError("invalid initial canonical records: " + "; ".join(errors))
        self._records = records

    def snapshot(self) -> CanonicalRecords:
        return deepcopy(self._records)


class ChangeSetWriteService:
    """Propose, validate, explain, and prepare—never publish—changes."""

    def __init__(self, repository: InMemoryCanonicalRepository,
                 clock: Callable[[], datetime] = _utc_now) -> None:
        self._repository = repository
        self._clock = clock
        self._changes: Dict[str, ChangeSet] = {}
        self._events: List[WorkflowEvent] = []

    def propose(self, change_set: ChangeSet, actor: str) -> ChangeSet:
        actor = self._require_actor(actor, "proposed")
        occurred_at = self._clock()
        if change_set.change_set_id in self._changes:
            raise DuplicateChangeSet(change_set.change_set_id)
        if change_set.status is not ChangeSetStatus.DRAFT:
            raise WriteServiceError("a proposed ChangeSet must be a draft")
        stored = deepcopy(change_set)
        self._changes[stored.change_set_id] = stored
        self._event(stored.change_set_id, "proposed", actor,
                    ChangeSetStatus.DRAFT, ChangeSetStatus.DRAFT, occurred_at)
        return deepcopy(stored)

    def get(self, change_set_id: str) -> ChangeSet:
        return deepcopy(self._stored(change_set_id))

    def validate(self, change_set_id: str, actor: str) -> Tuple[str, ...]:
        actor = self._require_actor(actor, "validated")
        occurred_at = self._clock()
        change = self._stored(change_set_id)
        before = change.status
        errors = change.validate(existing=self._repository.snapshot())
        action = "validation_failed" if errors else "validated"
        self._event(change_set_id, action, actor, before, change.status,
                    occurred_at, errors)
        return errors

    def explain(self, change_set_id: str) -> ChangeSetExplanation:
        change = self._stored(change_set_id)
        additions = []
        for collection, attribute in _ID_ATTRIBUTES.items():
            ids = tuple(getattr(item, attribute)
                        for item in getattr(change.records, collection))
            if ids:
                additions.append((collection, ids))
        base = self._repository.snapshot()
        errors = tuple(validate_records(change.records, existing=base))
        errors += _operation_errors(change, base)
        return ChangeSetExplanation(
            change_set_id=change.change_set_id,
            status=change.status,
            summary=change.summary,
            additions=tuple(additions),
            operations=change.operations,
            validation_errors=errors,
        )

    def prepare(self, change_set_id: str, actor: str) -> PreparedCandidate:
        """Build a detached candidate; GitHub approval and merge happen later."""
        actor = self._require_actor(actor, "prepared")
        occurred_at = self._clock()
        change = self._stored(change_set_id)
        try:
            change.assert_validated_unchanged()
        except ValueError as exc:
            raise PreparationRejected(str(exc)) from exc

        base = self._repository.snapshot()
        errors = tuple(validate_records(change.records, existing=base))
        errors += _operation_errors(change, base)
        if errors:
            self._event(change_set_id, "preparation_rejected", actor,
                        change.status, change.status, occurred_at, errors)
            raise PreparationRejected("canonical base changed: " + "; ".join(errors))

        result = _combined(base, change.records)
        result_errors = tuple(validate_records(result))
        if result_errors:
            raise PreparationRejected("candidate snapshot invalid: "
                                      + "; ".join(result_errors))
        self._event(change_set_id, "prepared", actor,
                    change.status, change.status, occurred_at)
        return PreparedCandidate(
            change_set_id=change_set_id,
            base=base,
            result=result,
            operations=change.operations,
        )

    def workflow_log(self, change_set_id: Optional[str] = None) -> Tuple[WorkflowEvent, ...]:
        events = self._events
        if change_set_id is not None:
            events = [event for event in events
                      if event.change_set_id == change_set_id]
        return tuple(events)

    def _stored(self, change_set_id: str) -> ChangeSet:
        try:
            return self._changes[change_set_id]
        except KeyError as exc:
            raise UnknownChangeSet(change_set_id) from exc

    def _event(self, change_set_id: str, action: str, actor: str,
               before: ChangeSetStatus, after: ChangeSetStatus,
               occurred_at: datetime, errors: Tuple[str, ...] = ()) -> None:
        self._events.append(WorkflowEvent(
            sequence=len(self._events) + 1,
            change_set_id=change_set_id,
            action=action,
            actor=actor,
            occurred_at=occurred_at,
            from_status=before,
            to_status=after,
            errors=tuple(errors),
        ))

    @staticmethod
    def _require_actor(actor: str, action: str) -> str:
        if not actor or not actor.strip():
            raise WriteServiceError(f"{action} requires an identified actor")
        return actor.strip()
