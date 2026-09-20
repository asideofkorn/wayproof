"""Controlled in-memory write boundary for Canonical Schema v0.

The service proves the ChangeSet workflow before Wayproof chooses a canonical
file serialization.  Callers receive defensive copies: the repository is not a
mutable storage API, and promotion is the only operation that changes canonical
records.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from .schema import CanonicalRecords, ChangeSet, ChangeSetStatus
from .validation import validate_records


class WriteServiceError(ValueError):
    """Base class for rejected write-service operations."""


class UnknownChangeSet(WriteServiceError):
    pass


class DuplicateChangeSet(WriteServiceError):
    pass


class PromotionRejected(WriteServiceError):
    pass


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    change_set_id: str
    action: str
    actor: str
    occurred_at: datetime
    from_status: ChangeSetStatus
    to_status: ChangeSetStatus
    note: str = ""
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ChangeSetExplanation:
    change_set_id: str
    status: ChangeSetStatus
    additions: Tuple[Tuple[str, Tuple[str, ...]], ...]
    validation_errors: Tuple[str, ...]
    approved_by: str

    @property
    def addition_count(self) -> int:
        return sum(len(ids) for _, ids in self.additions)


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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _combined(left: CanonicalRecords,
              right: CanonicalRecords) -> CanonicalRecords:
    """Create a detached union without choosing a persistence format."""
    values = {}
    for definition in fields(CanonicalRecords):
        values[definition.name] = (
            deepcopy(getattr(left, definition.name))
            + deepcopy(getattr(right, definition.name))
        )
    return CanonicalRecords(**values)


class InMemoryCanonicalRepository:
    """Read-only snapshots plus one private, atomic promotion operation."""

    def __init__(self, initial: Optional[CanonicalRecords] = None) -> None:
        records = deepcopy(initial or CanonicalRecords())
        errors = validate_records(records)
        if errors:
            raise ValueError("invalid initial canonical records: " + "; ".join(errors))
        self._records = records

    def snapshot(self) -> CanonicalRecords:
        return deepcopy(self._records)

    def _promote(self, candidate: CanonicalRecords) -> None:
        """Replace state only after the complete proposed state validates."""
        proposed = _combined(self._records, candidate)
        errors = validate_records(proposed)
        if errors:
            raise PromotionRejected("atomic promotion rejected: " + "; ".join(errors))
        self._records = proposed


class ChangeSetWriteService:
    """The sole normal mutation path into a canonical repository."""

    def __init__(self, repository: InMemoryCanonicalRepository,
                 clock: Callable[[], datetime] = _utc_now) -> None:
        self._repository = repository
        self._clock = clock
        self._changes: Dict[str, ChangeSet] = {}
        self._events: List[AuditEvent] = []

    def propose(self, change_set: ChangeSet, actor: str) -> ChangeSet:
        actor = self._require_actor(actor, "proposed")
        occurred_at = self._clock()
        if change_set.change_set_id in self._changes:
            raise DuplicateChangeSet(change_set.change_set_id)
        if change_set.status is not ChangeSetStatus.DRAFT:
            raise WriteServiceError("a proposed ChangeSet must be a draft")
        stored = deepcopy(change_set)
        self._changes[stored.change_set_id] = stored
        self._audit(stored.change_set_id, "proposed", actor,
                    ChangeSetStatus.DRAFT, ChangeSetStatus.DRAFT,
                    occurred_at=occurred_at)
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
        self._audit(change_set_id, action, actor, before, change.status,
                    errors=errors, occurred_at=occurred_at)
        return errors

    def explain(self, change_set_id: str) -> ChangeSetExplanation:
        change = self._stored(change_set_id)
        additions = []
        for collection, attribute in _ID_ATTRIBUTES.items():
            ids = tuple(getattr(item, attribute)
                        for item in getattr(change.records, collection))
            if ids:
                additions.append((collection, ids))
        errors = tuple(validate_records(
            change.records, existing=self._repository.snapshot()))
        return ChangeSetExplanation(
            change_set_id=change.change_set_id,
            status=change.status,
            additions=tuple(additions),
            validation_errors=errors,
            approved_by=change.approved_by,
        )

    def approve(self, change_set_id: str, reviewer: str,
                note: str = "") -> None:
        reviewer = self._require_actor(reviewer, "approved")
        occurred_at = self._clock()
        change = self._stored(change_set_id)
        before = change.status
        change.approve(reviewer, note)
        self._audit(change_set_id, "approved", reviewer, before, change.status,
                    note=note, occurred_at=occurred_at)

    def promote(self, change_set_id: str, actor: str) -> None:
        actor = self._require_actor(actor, "promoted")
        occurred_at = self._clock()
        change = self._stored(change_set_id)
        if change.status is not ChangeSetStatus.APPROVED:
            raise PromotionRejected("only an approved ChangeSet can be promoted")

        # Re-check against the current repository. Another ChangeSet may have
        # promoted between this one's validation and approval.
        errors = tuple(validate_records(
            change.records, existing=self._repository.snapshot()))
        if errors:
            self._audit(change_set_id, "promotion_rejected", actor,
                        change.status, change.status, errors=errors,
                        occurred_at=occurred_at)
            raise PromotionRejected("canonical state changed: " + "; ".join(errors))

        before = change.status
        # The ChangeSet verifies that approved content still equals its
        # validated snapshot; the repository validates the complete new state
        # before swapping it in. Neither operation partially mutates storage.
        try:
            change.promote()
            self._repository._promote(change.records)
        except Exception:
            change.status = before
            raise
        self._audit(change_set_id, "promoted", actor, before, change.status,
                    occurred_at=occurred_at)

    def audit_log(self, change_set_id: Optional[str] = None) -> Tuple[AuditEvent, ...]:
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

    def _audit(self, change_set_id: str, action: str, actor: str,
               before: ChangeSetStatus, after: ChangeSetStatus,
               note: str = "", errors: Tuple[str, ...] = (),
               occurred_at: Optional[datetime] = None) -> None:
        self._events.append(AuditEvent(
            sequence=len(self._events) + 1,
            change_set_id=change_set_id,
            action=action,
            actor=actor.strip(),
            occurred_at=occurred_at or self._clock(),
            from_status=before,
            to_status=after,
            note=note.strip(),
            errors=tuple(errors),
        ))

    @staticmethod
    def _require_actor(actor: str, action: str) -> str:
        if not actor or not actor.strip():
            raise WriteServiceError(f"{action} requires an identified actor")
        return actor.strip()
