"""Canonical Schema v0 domain records.

These records define what valid Wayproof knowledge is. They deliberately do
not choose an on-disk serialization, database, or package-wide migration path.
The existing CSV-backed planner remains operational while new canonical
knowledge is built through ChangeSet values and validation.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class TemporalScope:
    """An inclusive effective interval; either boundary may be open."""

    starts_on: Optional[date] = None
    ends_on: Optional[date] = None


@dataclass(frozen=True)
class SpatialScope:
    """A named spatial target without committing to a geometry format."""

    scope_id: str
    kind: str
    entity_id: str = ""
    description: str = ""


@dataclass(frozen=True)
class Entity:
    entity_id: str
    kind: str
    name: str


@dataclass(frozen=True)
class Source:
    source_id: str
    locator: str
    publisher: str = ""


@dataclass(frozen=True)
class Observation:
    """What a source or reporter actually stated or recorded."""

    observation_id: str
    source_id: str
    content: str
    observed_at: Optional[datetime] = None
    retrieved_at: Optional[datetime] = None
    observer: str = ""
    artifact_refs: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Evidence:
    """The use of an observation in support of or against a claim."""

    evidence_id: str
    observation_id: str
    claim_id: str
    stance: str = "supports"
    notes: str = ""


@dataclass(frozen=True)
class Claim:
    """An atomic proposition with explicit evidence, time, and scope."""

    claim_id: str
    subject_id: str
    predicate: str
    value: Any
    evidence_ids: Tuple[str, ...]
    temporal_scope: Optional[TemporalScope] = None
    spatial_scope_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Relationship:
    """A sourced, optionally temporal edge between durable entities."""

    relationship_id: str
    subject_id: str
    predicate: str
    object_id: str
    evidence_ids: Tuple[str, ...]
    temporal_scope: Optional[TemporalScope] = None


@dataclass(frozen=True)
class Condition:
    """One bounded input to rule applicability."""

    dimension: str
    operator: str
    value: Any


@dataclass(frozen=True)
class Rule:
    """A normative or operational consequence grounded in a source claim."""

    rule_id: str
    claim_id: str
    consequence: str
    conditions: Tuple[Condition, ...] = ()
    spatial_scope_ids: Tuple[str, ...] = ()
    temporal_scope: Optional[TemporalScope] = None


@dataclass(frozen=True)
class Coverage:
    """The portion of a trip a requirement or fulfillment applies to."""

    participant_ids: Tuple[str, ...] = ()
    equipment_ids: Tuple[str, ...] = ()
    stage_ids: Tuple[str, ...] = ()
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None


def coverage_contains(offered: Coverage, required: Coverage) -> bool:
    """Whether one fulfillment coverage fully contains required coverage.

    Empty ID tuples mean that dimension is unrestricted.  A missing date bound
    is open-ended.  This keeps partial coverage visible rather than treating
    the presence of any credential as satisfaction of the whole requirement.
    """
    dimensions = (
        (set(offered.participant_ids), set(required.participant_ids)),
        (set(offered.equipment_ids), set(required.equipment_ids)),
        (set(offered.stage_ids), set(required.stage_ids)),
    )
    for offered_ids, required_ids in dimensions:
        if not required_ids and offered_ids:
            return False
        if required_ids and offered_ids and not offered_ids.issuperset(required_ids):
            return False
    if offered.starts_on and required.starts_on and offered.starts_on > required.starts_on:
        return False
    if offered.ends_on and required.ends_on and offered.ends_on < required.ends_on:
        return False
    if offered.starts_on and not required.starts_on:
        return False
    if offered.ends_on and not required.ends_on:
        return False
    return True


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    rule_id: str
    description: str
    coverage: Coverage = field(default_factory=Coverage)


@dataclass(frozen=True)
class Fulfillment:
    """Evidence that all or part of one requirement has been satisfied."""

    fulfillment_id: str
    requirement_id: str
    kind: str
    evidence_ids: Tuple[str, ...]
    coverage: Coverage = field(default_factory=Coverage)


@dataclass(frozen=True)
class TripObjective:
    objective_id: str
    entity_id: str
    kind: str


@dataclass(frozen=True)
class TripStage:
    stage_id: str
    sequence: int
    kind: str
    spatial_scope_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PartyContext:
    participant_ids: Tuple[str, ...] = ()
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActivityContext:
    activities: Tuple[str, ...] = ()
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EquipmentContext:
    equipment_ids: Tuple[str, ...] = ()
    attributes: Dict[str, Any] = field(default_factory=dict)
    prior_events: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanningContext:
    trip_date: date
    objectives: Tuple[TripObjective, ...]
    stages: Tuple[TripStage, ...]
    party: PartyContext = field(default_factory=PartyContext)
    activities: ActivityContext = field(default_factory=ActivityContext)
    equipment: EquipmentContext = field(default_factory=EquipmentContext)


@dataclass(frozen=True)
class KnowledgeGap:
    gap_id: str
    question: str
    related_ids: Tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class DerivedResult:
    result_id: str
    kind: str
    value: Any
    input_ids: Tuple[str, ...]
    explanation: str = ""


@dataclass
class CanonicalRecords:
    """An in-memory validation boundary, not a storage decision."""

    entities: List[Entity] = field(default_factory=list)
    spatial_scopes: List[SpatialScope] = field(default_factory=list)
    sources: List[Source] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    evidence: List[Evidence] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)
    requirements: List[Requirement] = field(default_factory=list)
    fulfillments: List[Fulfillment] = field(default_factory=list)
    gaps: List[KnowledgeGap] = field(default_factory=list)
    derived_results: List[DerivedResult] = field(default_factory=list)


class ChangeSetStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"


class ChangeAction(str, Enum):
    ADD = "ADD"
    REPLACE = "REPLACE"
    REMOVE = "REMOVE"


@dataclass(frozen=True)
class ChangeOperation:
    """Domain intent for one canonical path changed by a future Git diff."""

    action: ChangeAction
    record_type: str
    record_id: str
    path: str
    reason: str
    evidence_refs: Tuple[str, ...] = ()
    knowledge_gap_refs: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        required = {
            "record_type": self.record_type,
            "record_id": self.record_id,
            "path": self.path,
            "reason": self.reason,
        }
        for label, value in required.items():
            if not value or not value.strip():
                raise ValueError(f"ChangeOperation {label} must not be blank")
        if not self.path.startswith("canonical/") or ".." in self.path.split("/"):
            raise ValueError("ChangeOperation path must stay under canonical/")


@dataclass
class ChangeSet:
    """The only normal boundary for proposing canonical knowledge changes."""

    change_set_id: str
    records: CanonicalRecords
    summary: str = ""
    operations: Tuple[ChangeOperation, ...] = ()
    artifact_format_version: int = 1
    schema_version: int = 0
    status: ChangeSetStatus = ChangeSetStatus.DRAFT
    validation_errors: Tuple[str, ...] = ()
    _validated_snapshot: Optional[CanonicalRecords] = field(
        default=None, init=False, repr=False, compare=False)
    _validated_operations: Optional[Tuple[ChangeOperation, ...]] = field(
        default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.change_set_id.strip():
            raise ValueError("ChangeSet id must not be blank")
        if self.artifact_format_version < 1:
            raise ValueError("artifact format version must be positive")
        if self.schema_version < 0:
            raise ValueError("schema version must not be negative")

    def validate(self, existing: Optional[CanonicalRecords] = None) -> Tuple[str, ...]:
        """Validate and advance a clean draft to VALIDATED."""
        if self.status not in (ChangeSetStatus.DRAFT, ChangeSetStatus.VALIDATED):
            raise ValueError("only a draft or validated ChangeSet can be validated")

        from .validation import validate_records

        errors = tuple(validate_records(self.records, existing=existing))
        self.validation_errors = errors
        self.status = (ChangeSetStatus.VALIDATED
                       if not errors else ChangeSetStatus.DRAFT)
        self._validated_snapshot = deepcopy(self.records) if not errors else None
        self._validated_operations = deepcopy(self.operations) if not errors else None
        return errors

    def assert_validated_unchanged(self) -> None:
        if self.status is not ChangeSetStatus.VALIDATED:
            raise ValueError("only a validated ChangeSet can be prepared")
        if self.records != self._validated_snapshot:
            raise ValueError("ChangeSet changed after validation; validate it again")
        if self.operations != self._validated_operations:
            raise ValueError("ChangeSet operations changed after validation; validate it again")
