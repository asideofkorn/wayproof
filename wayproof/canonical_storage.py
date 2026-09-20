"""Deterministic Git-backed storage for Canonical Schema v0 artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Tuple, Type, Union, get_args, get_origin, get_type_hints

from . import schema
from .schema import (CanonicalRecords, ChangeAction, ChangeOperation, ChangeSet,
                     ChangeSetStatus)
from .validation import validate_records
from .write_service import PreparedCandidate


ARTIFACT_FORMAT_VERSION = 1
SCHEMA_VERSION = 0

RECORD_SPECS: Dict[str, Tuple[str, str, Type[Any]]] = {
    "entity": ("entities", "entity_id", schema.Entity),
    "spatial_scope": ("spatial_scopes", "scope_id", schema.SpatialScope),
    "source": ("sources", "source_id", schema.Source),
    "observation": ("observations", "observation_id", schema.Observation),
    "evidence": ("evidence", "evidence_id", schema.Evidence),
    "claim": ("claims", "claim_id", schema.Claim),
    "relationship": ("relationships", "relationship_id", schema.Relationship),
    "rule": ("rules", "rule_id", schema.Rule),
    "requirement": ("requirements", "requirement_id", schema.Requirement),
    "fulfillment": ("fulfillments", "fulfillment_id", schema.Fulfillment),
    "gap": ("gaps", "gap_id", schema.KnowledgeGap),
    "derived_result": ("derived_results", "result_id", schema.DerivedResult),
}
COLLECTION_TYPES = {collection: (kind, identifier, record_class)
                    for kind, (collection, identifier, record_class)
                    in RECORD_SPECS.items()}


class CanonicalStorageError(ValueError):
    pass


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return {field.name: _json_value(getattr(value, field.name))
                for field in fields(value) if not field.name.startswith("_")}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in sorted(value.items())}
    return value


def _decode(annotation: Any, value: Any) -> Any:
    if annotation is Any:
        return value
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Union:
        if value is None and type(None) in arguments:
            return None
        return _decode(next(item for item in arguments if item is not type(None)), value)
    if origin in (tuple, Tuple):
        item_type = arguments[0] if arguments else Any
        return tuple(_decode(item_type, item) for item in value)
    if origin in (list, List):
        item_type = arguments[0] if arguments else Any
        return [_decode(item_type, item) for item in value]
    if origin in (dict, Dict):
        value_type = arguments[1] if len(arguments) > 1 else Any
        return {key: _decode(value_type, item) for key, item in value.items()}
    if annotation is datetime:
        return datetime.fromisoformat(value)
    if annotation is date:
        return date.fromisoformat(value)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)
    if isinstance(annotation, type) and is_dataclass(annotation):
        hints = get_type_hints(annotation)
        return annotation(**{field.name: _decode(hints[field.name], value[field.name])
                             for field in fields(annotation)
                             if field.name in value and field.init})
    return value


def _document(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def record_document(record_type: str, record: Any) -> str:
    if record_type not in RECORD_SPECS:
        raise CanonicalStorageError(f"unknown record type: {record_type}")
    return _document({
        "artifact_format_version": ARTIFACT_FORMAT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "record_type": record_type,
        "record": _json_value(record),
    })


def changeset_document(change: ChangeSet) -> str:
    if change.status is not ChangeSetStatus.VALIDATED:
        raise CanonicalStorageError("only a validated ChangeSet can be persisted")
    return _document({
        "artifact_format_version": change.artifact_format_version,
        "schema_version": change.schema_version,
        "change_set_id": change.change_set_id,
        "status": change.status.value,
        "summary": change.summary,
        "operations": _json_value(change.operations),
    })


def load_changeset(path: Path) -> ChangeSet:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("artifact_format_version") != ARTIFACT_FORMAT_VERSION:
        raise CanonicalStorageError(f"unsupported ChangeSet artifact format: {path}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise CanonicalStorageError(f"unsupported ChangeSet schema version: {path}")
    if path.stem != payload.get("change_set_id"):
        raise CanonicalStorageError(f"ChangeSet id does not match filename: {path}")
    operations = tuple(_decode(ChangeOperation, item)
                       for item in payload["operations"])
    return ChangeSet(
        change_set_id=payload["change_set_id"],
        records=CanonicalRecords(),
        summary=payload["summary"],
        operations=operations,
        artifact_format_version=payload["artifact_format_version"],
        schema_version=payload["schema_version"],
        status=ChangeSetStatus(payload["status"]),
    )


def _result_index(records: CanonicalRecords) -> Dict[Tuple[str, str], Any]:
    result = {}
    for kind, (collection, identifier, _) in RECORD_SPECS.items():
        for record in getattr(records, collection):
            result[(kind, getattr(record, identifier))] = record
    return result


def write_candidate(root: Path, prepared: PreparedCandidate,
                    change: ChangeSet) -> Tuple[Path, ...]:
    """Write only the paths authorized by a validated prepared candidate."""
    if prepared.change_set_id != change.change_set_id:
        raise CanonicalStorageError("prepared candidate and ChangeSet ids differ")
    if tuple(prepared.operations) != tuple(change.operations):
        raise CanonicalStorageError("prepared candidate and ChangeSet operations differ")
    index = _result_index(prepared.result)
    touched = []
    for operation in prepared.operations:
        path = root / operation.path
        if operation.action is ChangeAction.REMOVE:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(record_document(
                operation.record_type,
                index[(operation.record_type, operation.record_id)]),
                encoding="utf-8")
        touched.append(path)
    change_path = root / "changesets" / "v0" / f"{change.change_set_id}.json"
    change_path.parent.mkdir(parents=True, exist_ok=True)
    change_path.write_text(changeset_document(change), encoding="utf-8")
    touched.append(change_path)
    return tuple(touched)


def load_canonical(root: Path) -> CanonicalRecords:
    values: Dict[str, List[Any]] = {field.name: [] for field in fields(CanonicalRecords)}
    canonical_root = root / "canonical" / "v0"
    for collection, (kind, _, record_class) in COLLECTION_TYPES.items():
        for path in sorted((canonical_root / collection).glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("artifact_format_version") != ARTIFACT_FORMAT_VERSION:
                raise CanonicalStorageError(f"unsupported artifact format: {path}")
            if payload.get("schema_version") != SCHEMA_VERSION:
                raise CanonicalStorageError(f"unsupported schema version: {path}")
            if payload.get("record_type") != kind:
                raise CanonicalStorageError(f"record type does not match path: {path}")
            record = _decode(record_class, payload["record"])
            _, identifier, _ = RECORD_SPECS[kind]
            if path.stem != getattr(record, identifier):
                raise CanonicalStorageError(f"record id does not match filename: {path}")
            values[collection].append(record)
    records = CanonicalRecords(**values)
    errors = validate_records(records)
    if errors:
        raise CanonicalStorageError("invalid canonical snapshot: " + "; ".join(errors))
    return records
