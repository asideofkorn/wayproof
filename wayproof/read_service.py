"""Stable read-only service boundary over canonical Wayproof knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

from .canonical_storage import RECORD_SPECS, load_canonical, load_changeset
from .hike_comparison import HikeComparison, compare_hikes
from .intent import IntentResolution, resolve_trip_intent
from .managed_land_geometry import ManagedLandGeometryService
from .planning import TripPlan, plan_trip
from .planning_inputs import PlanningInputProjection, project_planning_inputs
from .readiness import TripReadiness, evaluate_trip_readiness
from .recheck import PretripRecheck, evaluate_pretrip_recheck
from .requirements import RequirementEvaluation, evaluate_requirements
from .route_geometry import RouteGeometryService
from .schema import (ChangeAction, Claim, Entity, Evidence, Fulfillment,
                     KnowledgeGap, Observation, PlanningContext, Relationship,
                     Source, SpatialScope, TripIntent)


@dataclass(frozen=True)
class ClaimProvenance:
    claim: Claim
    evidence: Tuple[Evidence, ...]
    observations: Tuple[Observation, ...]
    sources: Tuple[Source, ...]


@dataclass(frozen=True)
class ChangeHistoryEntry:
    change_set_id: str
    summary: str
    action: ChangeAction
    record_type: str
    record_id: str
    path: str
    reason: str
    evidence_refs: Tuple[str, ...]
    knowledge_gap_refs: Tuple[str, ...]


class CanonicalReadService:
    """One consumer API for reads; all writes remain behind the write service."""

    def __init__(self, root: Path, *, research_workflow=None):
        self._root = Path(root)
        self._research_workflow = research_workflow
        self.refresh()

    def _build_indexes(self):
        indexes = {}
        for record_type, (collection, identifier, _) in RECORD_SPECS.items():
            indexes[record_type] = {
                getattr(item, identifier): item
                for item in getattr(self._records, collection)
            }
        self._source_observations = {}
        self._observation_claims = {}
        for observation in self._records.observations:
            self._source_observations.setdefault(observation.source_id, []).append(
                observation.observation_id)
        # Only follow evidence actually cited by a claim.
        for claim in self._records.claims:
            for eid in claim.evidence_ids:
                evidence = indexes["evidence"][eid]
                self._observation_claims.setdefault(evidence.observation_id, set()).add(
                    claim.claim_id)
        return indexes

    def refresh(self) -> None:
        """Reload a newly published canonical snapshot from Git-backed files."""
        from .media_migration import REFERENCE_MANIFEST, ReferencePublication
        self._frozen_reference = None
        self._reference = None
        self._reference_keys = set()
        self._reference_subjects = {}
        if (self._root / REFERENCE_MANIFEST).exists():
            self._reference = ReferencePublication(self._root, self._research_workflow)
            snapshot = self._reference_snapshot()
            self._records = snapshot.base
            self._reference_keys = set(snapshot.additions) | snapshot._withdrawn
            for cid, subject_id in self._reference.subjects().items():
                self._reference_subjects.setdefault(subject_id, []).append(cid)
        else:
            self._records = load_canonical(self._root)
        self._indexes = self._build_indexes()
        self._change_history = self._build_change_history()

    def _build_change_history(self) -> Tuple[ChangeHistoryEntry, ...]:
        entries = []
        for path in sorted((self._root / "changesets" / "v0").glob("*.json")):
            change = load_changeset(path)
            for operation in change.operations:
                entries.append(ChangeHistoryEntry(
                    change_set_id=change.change_set_id,
                    summary=change.summary,
                    action=operation.action,
                    record_type=operation.record_type,
                    record_id=operation.record_id,
                    path=operation.path,
                    reason=operation.reason,
                    evidence_refs=operation.evidence_refs,
                    knowledge_gap_refs=operation.knowledge_gap_refs,
                ))
        return tuple(entries)

    def get(self, record_type: str, record_id: str) -> Any:
        if (record_type, record_id) in self._reference_keys:
            return self._reference_snapshot().evidence_detail(record_type, record_id)
        if record_type not in self._indexes:
            raise KeyError(f"unknown record type: {record_type}")
        try:
            return self._indexes[record_type][record_id]
        except KeyError as exc:
            raise KeyError(f"unknown {record_type}: {record_id}") from exc

    def entity(self, entity_id: str) -> Entity:
        return self.get("entity", entity_id)

    def search_entities(self, query: str = "", kinds: Iterable[str] = ()) -> Tuple[Entity, ...]:
        needle = query.strip().casefold()
        allowed = {item.casefold() for item in kinds}
        matches = (
            item for item in self._records.entities
            if (not allowed or item.kind.casefold() in allowed)
            and (not needle or needle in item.name.casefold()
                 or needle in item.entity_id.casefold())
        )
        return tuple(sorted(matches, key=lambda item: (item.name.casefold(), item.entity_id)))

    def compare_hikes(
        self,
        route_ids: Iterable[str],
        maximum_round_trip_miles: float,
    ) -> HikeComparison:
        """Compare an explicit route set against a distance cap."""
        return compare_hikes(
            self._records, tuple(route_ids), maximum_round_trip_miles,
        )

    def claims_for(self, subject_id: str) -> Tuple[Claim, ...]:
        """Return claims whose subject is the requested canonical record."""
        return tuple(sorted(
            (item for item in self._records.claims if item.subject_id == subject_id),
            key=lambda item: (item.predicate.casefold(), item.claim_id),
        ))

    def relationships_for(self, entity_id: str) -> Tuple[Relationship, ...]:
        """Return sourced relationships touching an entity in either direction."""
        return tuple(sorted(
            (item for item in self._records.relationships
             if entity_id in (item.subject_id, item.object_id)),
            key=lambda item: (item.predicate.casefold(), item.relationship_id),
        ))

    def spatial_scopes_for(self, entity_id: str) -> Tuple[SpatialScope, ...]:
        """Return every canonical spatial scope attached to an entity."""
        return tuple(sorted(
            (item for item in self._records.spatial_scopes
             if item.entity_id == entity_id),
            key=lambda item: item.scope_id,
        ))

    def resolve_intent(self, intent: TripIntent) -> IntentResolution:
        """Resolve an intent without guessing at ambiguous routes or access."""
        return resolve_trip_intent(self, intent)

    def plan(self, intent: TripIntent,
             fulfillments: Iterable[Fulfillment] = (),
             recheck_result_ids: Iterable[str] = (),
             as_of_date: Optional[date] = None) -> TripPlan:
        """Resolve and evaluate one trip through the shared domain boundary."""
        return plan_trip(self, intent, fulfillments, recheck_result_ids, as_of_date)

    def planning_inputs(self, resolution: IntentResolution) -> PlanningInputProjection:
        """Project explicitly classified planning inputs onto a resolved trip."""
        return project_planning_inputs(self._records, resolution)

    def knowledge_gaps_for(self, record_id: str) -> Tuple[KnowledgeGap, ...]:
        """Return explicit gaps that name a record as related context."""
        return tuple(sorted(
            (item for item in self._records.gaps if record_id in item.related_ids),
            key=lambda item: (item.question.casefold(), item.gap_id),
        ))

    def knowledge_gaps(self) -> Tuple[KnowledgeGap, ...]:
        """Return every published gap for canonical research/discovery views."""
        return tuple(sorted(self._records.gaps,
                            key=lambda item: (item.question.casefold(), item.gap_id)))

    def explain_claim(self, claim_id: str) -> ClaimProvenance:
        if ('claim', claim_id) in self._reference_keys:
            return self._reference_snapshot().explain_claim(claim_id)
        claim = self.get("claim", claim_id)
        evidence = tuple(self.get("evidence", item) for item in claim.evidence_ids)
        observations = tuple(
            self.get("observation", item.observation_id) for item in evidence
        )
        sources = tuple(dict.fromkeys(
            self.get("source", item.source_id) for item in observations
        ))
        return ClaimProvenance(claim, evidence, observations, sources)

    def evidence_record_ids(self, record_type: str) -> Tuple[str, ...]:
        """Durable identifiers for published evidence-browser records."""
        if record_type not in self.evidence_record_types():
            raise ValueError(f"unsupported evidence record type: {record_type}")
        return tuple(sorted(set(self._indexes.get(record_type, ())) |
                            {rid for kind, rid in self._reference_keys if kind == record_type}))

    def evidence_detail(self, record_type: str, record_id: str) -> dict:
        """Shared evidence projection; follows typed references, never text matches.

        Gaps compare only explicit claim/evidence references. Source, observation,
        and entity references are context and never expand the comparison set.
        """
        if (record_type, record_id) in self._reference_keys:
            return self._reference_snapshot().evidence_detail(record_type, record_id)
        ids = self.evidence_record_ids(record_type)
        record = self.get(record_type, record_id)
        claims = set()
        observations = set()
        sources = set()
        related = []

        def include(kind, identifier):
            if kind == "claim":
                claims.add(identifier)
            elif kind == "evidence":
                evidence = self.get(kind, identifier)
                observations.add(evidence.observation_id)
                claim = self.get("claim", evidence.claim_id)
                if identifier in claim.evidence_ids:
                    claims.add(claim.claim_id)
            elif kind == "observation":
                observations.add(identifier)
                claims.update(self._observation_claims.get(identifier, ()))
            elif kind == "source":
                sources.add(identifier)
                for oid in self._source_observations.get(identifier, ()):
                    observations.add(oid)
                    claims.update(self._observation_claims.get(oid, ()))

        if record_type == "gap":
            for identifier in record.related_ids:
                matches = [(kind, index[identifier]) for kind, index in self._indexes.items()
                           if identifier in index]
                related.extend({"record_type": kind, "record_id": identifier, "record": item}
                               for kind, item in matches)
                # Gap references are untyped in v0. Do not select a type when
                # the same identifier occurs in more than one collection.
                if len(matches) == 1 and matches[0][0] in ("claim", "evidence"):
                    include(matches[0][0], identifier)
        else:
            include(record_type, record_id)
        bundles = tuple(self.explain_claim(cid) for cid in sorted(claims))
        if record_type in ("claim", "gap", "evidence"):
            for bundle in bundles:
                observations.update(item.observation_id for item in bundle.observations)
        for oid in observations:
            sources.add(self.get("observation", oid).source_id)
        entities = {bundle.claim.subject_id for bundle in bundles
                    if bundle.claim.subject_id in self._indexes["entity"]}
        if record_type == "gap":
            entities.update(item for item in record.related_ids
                            if item in self._indexes["entity"])
        position = ids.index(record_id)
        return {
            "record_type": record_type, "record": record,
            "claims": bundles,
            "observations": tuple(self.get("observation", oid) for oid in sorted(observations)),
            "sources": tuple(self.get("source", sid) for sid in sorted(sources)),
            "entities": tuple(self.entity(eid) for eid in sorted(entities)),
            "related_records": tuple(related),
            "history": self.changes(record_id, record_type),
            "navigation": {"position": position + 1, "total": len(ids),
                           "previous_id": ids[position - 1] if position else None,
                           "next_id": ids[position + 1] if position + 1 < len(ids) else None},
        }

    def _reference_snapshot(self):
        return self._frozen_reference if self._frozen_reference is not None else self._reference._snapshot()

    def evidence_record_types(self):
        return tuple(sorted({'source', 'observation', 'evidence', 'claim', 'gap'} |
                            {kind for kind, _ in self._reference_keys}))

    def reference_evidence(self, entity_id=None):
        """Reference context only; never silently registered as a planning input."""
        if self._reference is None:
            return ()
        ids = (self._reference_subjects.get(entity_id, ()) if entity_id else
               sorted(rid for kind, rid in self._reference_keys if kind == 'claim'))
        if not ids:
            return ()
        snapshot = self._reference_snapshot()
        return tuple(snapshot.explain_claim(rid) for rid in ids)

    def changes(self, record_id: Optional[str] = None,
                record_type: Optional[str] = None) -> Tuple[ChangeHistoryEntry, ...]:
        entries = self._change_history
        if self._reference and (record_id is None or any(rid == record_id for _, rid in self._reference_keys)):
            snapshot = self._reference_snapshot()
            for batch in snapshot.batches:
                if batch.change is not None and batch._packet is not None:
                    change = batch.change
                    entries += tuple(ChangeHistoryEntry(change.change_set_id, change.summary, op.action,
                        op.record_type, op.record_id, op.path, op.reason, op.evidence_refs, op.knowledge_gap_refs)
                        for op in change.operations)
                else:
                    entries += tuple(ChangeHistoryEntry(batch.change_id,
                        'Reference support withdrawn or unavailable', ChangeAction.REMOVE,
                        kind, rid, '', 'No substitute selected', (), ())
                        for kind, rid in sorted(set(batch.additions) | batch._withdrawn))
        return tuple(
            entry for entry in entries
            if (record_id is None or entry.record_id == record_id)
            and (record_type is None or entry.record_type == record_type)
        )

    def requirements(self, context: PlanningContext,
                     fulfillments: Iterable[Fulfillment] = ()) -> RequirementEvaluation:
        return evaluate_requirements(self._records.rules, context, fulfillments)

    def readiness(self, context: PlanningContext,
                  fulfillments: Iterable[Fulfillment] = ()) -> TripReadiness:
        return evaluate_trip_readiness(self._records, context, fulfillments)

    def pretrip_recheck(self, context: PlanningContext,
                        result_id: str = "result-del-valle-pretrip-recheck"
                        ) -> PretripRecheck:
        return evaluate_pretrip_recheck(self._records, context, result_id)

    def route_geometry(self, route_id: str, as_of: date) -> dict | None:
        """Project reviewed source geometry through canonical route topology."""
        return RouteGeometryService(self._root, self).route(route_id, as_of)

    def managed_land_geometry(self, entity_id: str) -> dict | None:
        """Return reviewed boundary geometry for one managed-land entity."""
        return ManagedLandGeometryService(self._root, self).boundary(entity_id)
