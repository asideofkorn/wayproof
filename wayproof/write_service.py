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


def _is_v0_change(change: ChangeSet) -> bool:
    return (type(change.schema_version) is int and change.schema_version == 0 and
            type(change.artifact_format_version) is int and change.artifact_format_version == 1)


def _without_targets(base: CanonicalRecords,
                     operations: Tuple[ChangeOperation, ...]) -> CanonicalRecords:
    """Return the validation base after records being replaced/removed vanish."""
    removed = {
        (operation.record_type, operation.record_id)
        for operation in operations
        if operation.action in (ChangeAction.REPLACE, ChangeAction.REMOVE)
    }
    values = {}
    for record_type, (collection, attribute) in _RECORD_TYPES.items():
        values[collection] = [
            deepcopy(item) for item in getattr(base, collection)
            if (record_type, getattr(item, attribute)) not in removed
        ]
    return CanonicalRecords(**values)


def _apply_operations(base: CanonicalRecords, change: ChangeSet) -> CanonicalRecords:
    """Apply a fully checked ChangeSet to a detached canonical snapshot."""
    result = _without_targets(base, change.operations)
    for definition in fields(CanonicalRecords):
        getattr(result, definition.name).extend(
            deepcopy(getattr(change.records, definition.name)))
    return result


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

    value_targets = set()
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
            value_targets.add(target)
            if target not in candidate_targets:
                errors.append(f"ADD operation has no candidate record: {operation.record_id}")
            if target in existing_targets:
                errors.append(f"ADD targets existing record: {operation.record_id}")
        elif operation.action is ChangeAction.REPLACE:
            value_targets.add(target)
            if target not in existing_targets:
                errors.append(f"REPLACE targets missing record: {operation.record_id}")
            if target not in candidate_targets:
                errors.append(f"REPLACE operation has no candidate record: "
                              f"{operation.record_id}")
        elif operation.action is ChangeAction.REMOVE:
            if target not in existing_targets:
                errors.append(f"REMOVE targets missing record: {operation.record_id}")
            if target in candidate_targets:
                errors.append(f"REMOVE operation must not include a candidate record: "
                              f"{operation.record_id}")

    missing = sorted(candidate_targets - value_targets)
    extra = sorted(value_targets - candidate_targets)
    errors.extend(f"candidate record has no ADD or REPLACE operation: {kind}:{record_id}"
                  for kind, record_id in missing)
    errors.extend(f"value operation has no candidate record: {kind}:{record_id}"
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
                 clock: Callable[[], datetime] = _utc_now, *, research_reviews=None) -> None:
        self._repository = repository
        self._clock = clock
        self._changes: Dict[str, ChangeSet] = {}
        self._events: List[WorkflowEvent] = []
        from .public_research import ReviewedResearch
        self._research_reviews = research_reviews if research_reviews is not None else ReviewedResearch()
        self._research_packets = {}
        self._withdrawn_research = set()

    def propose(self, change_set: ChangeSet, actor: str) -> ChangeSet:
        actor = self._require_actor(actor, "proposed")
        occurred_at = self._clock()
        if change_set.change_set_id in self._changes or change_set.change_set_id in self._withdrawn_research:
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
        base = self._repository.snapshot()
        if not _is_v0_change(change):
            errors = change.validate(existing=base)
            self._event(change_set_id, 'validation_failed' if errors else 'validated',
                        actor, before, change.status, occurred_at, errors)
            return errors
        operation_errors = _operation_errors(change, base)
        errors = change.validate(existing=_without_targets(base, change.operations))
        result_errors = tuple(validate_records(_apply_operations(base, change)))
        errors = tuple(sorted(set(errors + operation_errors + result_errors)))
        change.validation_errors = errors
        if errors:
            change.status = ChangeSetStatus.DRAFT
            change._validated_snapshot = None
            change._validated_operations = None
        action = "validation_failed" if errors else "validated"
        self._event(change_set_id, action, actor, before, change.status,
                    occurred_at, errors)
        return errors

    def explain(self, change_set_id: str) -> ChangeSetExplanation:
        change = self._stored(change_set_id)
        additions = []
        attributes = dict(_ID_ATTRIBUTES)
        if change.schema_version == 1:
            from .media_schema import MEDIA_SPECS
            attributes.update({col: attr for col, attr, _ in MEDIA_SPECS.values()})
        for collection, attribute in attributes.items():
            ids = tuple(getattr(item, attribute)
                        for item in getattr(change.records, collection, ()))
            if ids:
                additions.append((collection, ids))
        base = self._repository.snapshot()
        if not _is_v0_change(change):
            candidate = deepcopy(change)
            errors = candidate.validate(existing=base)
            return ChangeSetExplanation(change.change_set_id, change.status, change.summary,
                                        tuple(additions), change.operations, errors)
        errors = tuple(validate_records(
            change.records, existing=_without_targets(base, change.operations)))
        errors += _operation_errors(change, base)
        errors += tuple(validate_records(_apply_operations(base, change)))
        return ChangeSetExplanation(
            change_set_id=change.change_set_id,
            status=change.status,
            summary=change.summary,
            additions=tuple(additions),
            operations=change.operations,
            validation_errors=tuple(sorted(set(errors))),
        )

    def assess_public_research(self, change_set_id: str, packet) -> Tuple[str, ...]:
        """Policy assessment separate from structural VALIDATED; never a grant to publish."""
        from .public_research import assess
        change = deepcopy(self._stored(change_set_id))
        errors = change.validate(existing=self._repository.snapshot())
        if errors:
            return ('public research requires a structurally valid draft',)
        errors = assess(change, packet, self._research_reviews, self._repository.snapshot())
        if not errors:
            self._research_packets[change_set_id] = deepcopy(packet)
        else:
            self._research_packets.pop(change_set_id, None)
        return errors

    def public_research_preview(self, change_set_id: str):
        """Detached shared preview for later consumer integration; no public v1 reads."""
        from .public_research import fingerprint, projection, assess
        if change_set_id in self._withdrawn_research:
            return {'texts': [], 'source_states': [], 'versions': [],
                    'support': 'removed', 'publication': 'disabled'}
        change = self._stored(change_set_id)
        packet = self._research_packets.get(change_set_id)
        if packet is None:
            return {'texts': [], 'source_states': [], 'versions': [],
                    'support': 'not_reviewed', 'publication': 'disabled'}
        review = self._research_reviews.lookup(fingerprint(change, packet, self._repository.snapshot()))
        if assess(change, packet, self._research_reviews, self._repository.snapshot()):
            # A stale/revoked review cannot keep exposing text from an old approval.
            states = ([{'source_id': s.source_id, 'state': s.current_state}
                       for s in review.sources] if review else [])
            return {'texts': [], 'source_states': states, 'versions': [],
                    'support': 'unavailable', 'publication': 'disabled'}
        model = projection(packet, [{'source_id': s.source_id, 'state': s.current_state,
                                    'inspected_at': s.inspected_at.isoformat(), 'locator': s.locator,
                                    'publisher_kind': s.publisher_kind}
                                   for s in review.sources])
        model['versions'] = [{'id': v.id, 'identity_basis': v.identity_basis,
                              'reproducibility': v.reproducibility,
                              'limitations': list(v.limitations)} for v in change.records.media_versions]
        model['support'] = 'reviewed_draft_only'
        return model

    def remove_public_research(self, source_ids: Tuple[str, ...], actor: str):
        """Withdraw whole owned drafts so copies of retained text cannot survive in them.

        Published v0 data is never modified here. Returned output invalidations
        are tasks for the later reviewed migration/publication integration.
        """
        from .public_research import removal_impact
        actor = self._require_actor(actor, 'research_removed')
        targets = set(source_ids)
        if not targets:
            raise WriteServiceError('removal requires source IDs')
        from .media_schema import MediaRecords
        base = self._repository.snapshot()
        def referenced(change):
            ids = {s.source_id for s in change.records.sources}
            for collection in ('observations', 'source_attachments', 'attributed_statements', 'analysis_runs'):
                ids.update(r.source_id for r in getattr(change.records, collection))
            return ids
        owned = [(s.source_id, s.locator) for c in self._changes.values() if c.schema_version == 1
                 for s in base.sources + c.records.sources if s.source_id in referenced(c)]
        if not targets <= {sid for sid, _ in owned}:
            raise WriteServiceError('removal source is not referenced by owned v1 research drafts')
        locators = {locator for sid, locator in owned if sid in targets}
        targets.update(sid for sid, locator in owned if locator in locators)
        affected = []
        known = set()
        impacts = []
        for change_id, change in self._changes.items():
            if change.schema_version != 1:
                continue
            ids = referenced(change)
            matched = ids & targets
            if matched:
                known.update(matched)
                affected.append(change_id)
                combined = MediaRecords(**{f.name: list(getattr(base, f.name, ())) +
                                           list(getattr(change.records, f.name)) for f in fields(MediaRecords)})
                impacts.append(removal_impact(combined, matched))
        if known != targets:
            raise WriteServiceError('removal source is not in owned v1 research drafts')
        withdrawn_source_ids = set().union(*(referenced(self._changes[cid]) for cid in affected))
        self._research_reviews.forget_sources(withdrawn_source_ids)
        for change_id in affected:
            change = self._changes.pop(change_id)
            self._research_packets.pop(change_id, None)
            self._withdrawn_research.add(change_id)
            self._event(change_id, 'research_removed', actor, change.status,
                        ChangeSetStatus.DRAFT, self._clock())
        return {'withdrawn_changesets': tuple(sorted(affected)), 'impacts': impacts,
                'owned_drafts': 'removed', 'published_outputs': 'not_modified'}

    def prepare(self, change_set_id: str, actor: str) -> PreparedCandidate:
        """Build a detached candidate; GitHub approval and merge happen later."""
        actor = self._require_actor(actor, "prepared")
        occurred_at = self._clock()
        change = self._stored(change_set_id)
        if not _is_v0_change(change):
            raise PreparationRejected('unsupported schema version for preparation; v1 activation is disabled')
        try:
            change.assert_validated_unchanged()
        except ValueError as exc:
            raise PreparationRejected(str(exc)) from exc

        base = self._repository.snapshot()
        errors = tuple(validate_records(
            change.records, existing=_without_targets(base, change.operations)))
        errors += _operation_errors(change, base)
        if errors:
            self._event(change_set_id, "preparation_rejected", actor,
                        change.status, change.status, occurred_at, errors)
            raise PreparationRejected("canonical base changed: " + "; ".join(errors))

        result = _apply_operations(base, change)
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

    def prepare_reference(self, change_set_id, actor, root, packet, receipt, workflow=None):
        """Prepare only reviewed reference records; GitHub still publishes the candidate."""
        from .canonical_storage import load_v0_baseline
        from .media_migration import ReferencePublication
        actor = self._require_actor(actor, 'prepared')
        change = self._stored(change_set_id)
        change.assert_validated_unchanged()
        ReferencePublication(root, workflow).recover_preparation()
        if self._repository.snapshot() != load_v0_baseline(root, research_workflow=workflow):
            raise PreparationRejected('canonical base changed')
        result = ReferencePublication.prepare(root, change, packet, receipt, workflow)
        self._event(change_set_id, 'prepared', actor, change.status, change.status, self._clock())
        return result

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
