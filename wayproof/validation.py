"""Deterministic validation for Canonical Schema v0 records."""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Optional, Set, Tuple

from .schema import CanonicalRecords, Coverage, TemporalScope


def _nonblank(value: str, label: str, errors: List[str]) -> None:
    if not value or not value.strip():
        errors.append(f"{label} must not be blank")


def _index(records: Iterable[object], attribute: str, kind: str,
           errors: List[str]) -> Dict[str, object]:
    values = [getattr(record, attribute) for record in records]
    for value in values:
        _nonblank(value, f"{kind} id", errors)
    duplicates = sorted(value for value, count in Counter(values).items()
                        if value and count > 1)
    errors.extend(f"duplicate {kind} id: {value}" for value in duplicates)
    return {getattr(record, attribute): record for record in records
            if getattr(record, attribute)}


def _interval(scope: Optional[TemporalScope], label: str,
              errors: List[str]) -> None:
    if scope and scope.starts_on and scope.ends_on and scope.starts_on > scope.ends_on:
        errors.append(f"{label} starts after it ends")


def _coverage(coverage: Coverage, label: str, errors: List[str]) -> None:
    if coverage.starts_on and coverage.ends_on and coverage.starts_on > coverage.ends_on:
        errors.append(f"{label} coverage starts after it ends")


def _missing(values: Iterable[str], known: Set[str], label: str,
             errors: List[str]) -> None:
    for value in values:
        if value not in known:
            errors.append(f"{label} references unknown id: {value}")


def validate_records(records: CanonicalRecords,
                     existing: Optional[CanonicalRecords] = None) -> List[str]:
    """Return stable invariant violations for an incremental ChangeSet."""
    errors: List[str] = []
    prior = existing or CanonicalRecords()

    specs: Tuple[Tuple[str, str, str], ...] = (
        ("entities", "entity_id", "entity"),
        ("spatial_scopes", "scope_id", "spatial scope"),
        ("sources", "source_id", "source"),
        ("observations", "observation_id", "observation"),
        ("evidence", "evidence_id", "evidence"),
        ("claims", "claim_id", "claim"),
        ("relationships", "relationship_id", "relationship"),
        ("rules", "rule_id", "rule"),
        ("requirements", "requirement_id", "requirement"),
        ("fulfillments", "fulfillment_id", "fulfillment"),
        ("gaps", "gap_id", "knowledge gap"),
        ("derived_results", "result_id", "derived result"),
    )
    indexes: Dict[str, Dict[str, object]] = {}
    for collection, attribute, kind in specs:
        new_index = _index(getattr(records, collection), attribute, kind, errors)
        old_index = {getattr(item, attribute): item
                     for item in getattr(prior, collection)}
        for collision in sorted(set(new_index).intersection(old_index)):
            errors.append(f"{kind} id already exists: {collision}")
        old_index.update(new_index)
        indexes[collection] = old_index

    entity_ids = set(indexes["entities"])
    scope_ids = set(indexes["spatial_scopes"])
    source_ids = set(indexes["sources"])
    observation_ids = set(indexes["observations"])
    evidence_ids = set(indexes["evidence"])
    claim_ids = set(indexes["claims"])
    rule_ids = set(indexes["rules"])
    requirement_ids = set(indexes["requirements"])

    for entity in records.entities:
        _nonblank(entity.kind, f"entity {entity.entity_id} kind", errors)
        _nonblank(entity.name, f"entity {entity.entity_id} name", errors)

    for scope in records.spatial_scopes:
        _nonblank(scope.kind, f"spatial scope {scope.scope_id} kind", errors)
        if scope.entity_id:
            _missing((scope.entity_id,), entity_ids,
                     f"spatial scope {scope.scope_id}", errors)
        if not scope.entity_id and not scope.description.strip():
            errors.append(f"spatial scope {scope.scope_id} needs an entity or description")

    for source in records.sources:
        _nonblank(source.locator, f"source {source.source_id} locator", errors)

    for observation in records.observations:
        _missing((observation.source_id,), source_ids,
                 f"observation {observation.observation_id}", errors)
        _nonblank(observation.content,
                  f"observation {observation.observation_id} content", errors)

    for item in records.evidence:
        _missing((item.observation_id,), observation_ids,
                 f"evidence {item.evidence_id}", errors)
        _missing((item.claim_id,), claim_ids, f"evidence {item.evidence_id}", errors)
        _nonblank(item.stance, f"evidence {item.evidence_id} stance", errors)

    for claim in records.claims:
        _missing((claim.subject_id,), entity_ids, f"claim {claim.claim_id}", errors)
        _missing(claim.evidence_ids, evidence_ids, f"claim {claim.claim_id}", errors)
        _missing(claim.spatial_scope_ids, scope_ids, f"claim {claim.claim_id}", errors)
        _nonblank(claim.predicate, f"claim {claim.claim_id} predicate", errors)
        if not claim.evidence_ids:
            errors.append(f"claim {claim.claim_id} requires evidence")
        _interval(claim.temporal_scope, f"claim {claim.claim_id}", errors)
        for evidence_id in claim.evidence_ids:
            item = indexes["evidence"].get(evidence_id)
            if item and item.claim_id != claim.claim_id:
                errors.append(f"claim {claim.claim_id} cites evidence {evidence_id} "
                              f"for claim {item.claim_id}")

    for relationship in records.relationships:
        _missing((relationship.subject_id, relationship.object_id), entity_ids,
                 f"relationship {relationship.relationship_id}", errors)
        _missing(relationship.evidence_ids, evidence_ids,
                 f"relationship {relationship.relationship_id}", errors)
        _nonblank(relationship.predicate,
                  f"relationship {relationship.relationship_id} predicate", errors)
        if not relationship.evidence_ids:
            errors.append(f"relationship {relationship.relationship_id} requires evidence")
        _interval(relationship.temporal_scope,
                  f"relationship {relationship.relationship_id}", errors)

    for rule in records.rules:
        _missing((rule.claim_id,), claim_ids, f"rule {rule.rule_id}", errors)
        _missing(rule.spatial_scope_ids, scope_ids, f"rule {rule.rule_id}", errors)
        _nonblank(rule.consequence, f"rule {rule.rule_id} consequence", errors)
        _interval(rule.temporal_scope, f"rule {rule.rule_id}", errors)
        for number, condition in enumerate(rule.conditions, start=1):
            _nonblank(condition.dimension,
                      f"rule {rule.rule_id} condition {number} dimension", errors)
            _nonblank(condition.operator,
                      f"rule {rule.rule_id} condition {number} operator", errors)

    for requirement in records.requirements:
        _missing((requirement.rule_id,), rule_ids,
                 f"requirement {requirement.requirement_id}", errors)
        _nonblank(requirement.description,
                  f"requirement {requirement.requirement_id} description", errors)
        _coverage(requirement.coverage,
                  f"requirement {requirement.requirement_id}", errors)

    for fulfillment in records.fulfillments:
        _missing((fulfillment.requirement_id,), requirement_ids,
                 f"fulfillment {fulfillment.fulfillment_id}", errors)
        _missing(fulfillment.evidence_ids, evidence_ids,
                 f"fulfillment {fulfillment.fulfillment_id}", errors)
        if not fulfillment.evidence_ids:
            errors.append(f"fulfillment {fulfillment.fulfillment_id} requires evidence")
        _nonblank(fulfillment.kind,
                  f"fulfillment {fulfillment.fulfillment_id} kind", errors)
        _coverage(fulfillment.coverage,
                  f"fulfillment {fulfillment.fulfillment_id}", errors)

    all_ids: Set[str] = set()
    for index in indexes.values():
        all_ids.update(index)
    for gap in records.gaps:
        _nonblank(gap.question, f"knowledge gap {gap.gap_id} question", errors)
        _missing(gap.related_ids, all_ids, f"knowledge gap {gap.gap_id}", errors)
    for result in records.derived_results:
        _nonblank(result.kind, f"derived result {result.result_id} kind", errors)
        if not result.input_ids:
            errors.append(f"derived result {result.result_id} requires inputs")
        _missing(result.input_ids, all_ids,
                 f"derived result {result.result_id}", errors)

    return sorted(set(errors))
