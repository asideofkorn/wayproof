"""Constrained additive proposals for untrusted consumer adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .canonical_storage import RECORD_SPECS
from .schema import (CanonicalRecords, ChangeAction, ChangeOperation, ChangeSet,
                     ChangeSetStatus)
from .write_service import (ChangeSetExplanation, ChangeSetWriteService,
                            WorkflowEvent, WriteServiceError)


ALLOWED_PROPOSAL_TYPES = frozenset({
    "entity",
    "spatial_scope",
    "source",
    "observation",
    "evidence",
    "claim",
    "relationship",
    "gap",
})


class ProposalRejected(WriteServiceError):
    pass


@dataclass(frozen=True)
class ProposalRequest:
    change_set_id: str
    summary: str
    reason: str
    records: CanonicalRecords


@dataclass(frozen=True)
class ProposalReceipt:
    change_set_id: str
    status: ChangeSetStatus
    validation_errors: Tuple[str, ...] = ()


def _operations(request: ProposalRequest) -> Tuple[ChangeOperation, ...]:
    if not request.summary.strip():
        raise ProposalRejected("proposal summary must not be blank")
    if not request.reason.strip():
        raise ProposalRejected("proposal reason must not be blank")

    operations = []
    proposed_count = 0
    for record_type, (collection, identifier, _) in RECORD_SPECS.items():
        values = getattr(request.records, collection)
        if values and record_type not in ALLOWED_PROPOSAL_TYPES:
            raise ProposalRejected(
                f"constrained proposals cannot add {record_type} records"
            )
        for record in values:
            proposed_count += 1
            record_id = getattr(record, identifier)
            evidence_refs = tuple(getattr(record, "evidence_ids", ()))
            operations.append(ChangeOperation(
                action=ChangeAction.ADD,
                record_type=record_type,
                record_id=record_id,
                path=f"canonical/v0/{collection}/{record_id}.json",
                reason=request.reason.strip(),
                evidence_refs=evidence_refs,
            ))
    if not proposed_count:
        raise ProposalRejected("proposal must contain at least one record")
    return tuple(operations)


class ConstrainedProposalService:
    """Submit and validate additive drafts without preparation or publication."""

    def __init__(self, writes: ChangeSetWriteService, actor: str):
        actor = actor.strip()
        if not actor:
            raise ProposalRejected("proposal service requires an identified actor")
        self._writes = writes
        self._actor = actor

    def submit(self, request: ProposalRequest) -> ProposalReceipt:
        change = ChangeSet(
            change_set_id=request.change_set_id,
            records=request.records,
            summary=request.summary.strip(),
            operations=_operations(request),
        )
        stored = self._writes.propose(change, self._actor)
        return ProposalReceipt(stored.change_set_id, stored.status)

    def validate(self, change_set_id: str) -> ProposalReceipt:
        errors = self._writes.validate(change_set_id, self._actor)
        stored = self._writes.get(change_set_id)
        return ProposalReceipt(stored.change_set_id, stored.status, errors)

    def explain(self, change_set_id: str) -> ChangeSetExplanation:
        return self._writes.explain(change_set_id)

    def workflow_log(self, change_set_id: str) -> Tuple[WorkflowEvent, ...]:
        return self._writes.workflow_log(change_set_id)
