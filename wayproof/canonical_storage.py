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


class UnsupportedSchemaError(CanonicalStorageError):
    """The entire repository must be supported before reading any snapshot."""


def _check_envelope(payload: dict, path: Path, *, changeset: bool = False) -> None:
    allowed = ({'artifact_format_version', 'schema_version', 'change_set_id',
                'status', 'summary', 'operations'} if changeset else
               {'artifact_format_version', 'schema_version', 'record_type', 'record'})
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise UnsupportedSchemaError(f'unsupported fields in schema v0 envelope: {path}')
    if type(payload.get('schema_version')) is not int or payload['schema_version'] != SCHEMA_VERSION:
        raise UnsupportedSchemaError(f'unsupported schema version: {path}')
    if (type(payload.get('artifact_format_version')) is not int or
            payload['artifact_format_version'] != ARTIFACT_FORMAT_VERSION):
        raise UnsupportedSchemaError(f'unsupported artifact format: {path}')


def assert_supported_repository(root: Path) -> None:
    """Fail closed on unknown versions/collections, including unmarked additions.

    No new manifest format is introduced. The existing versioned directory
    contract is the root capability gate; v1 activation is deliberately absent.
    """
    for namespace in ('canonical', 'changesets'):
        parent = root / namespace
        if not parent.exists():
            continue
        if parent.is_symlink() or not parent.is_dir():
            raise UnsupportedSchemaError(f'unsupported schema namespace layout: {parent}')
        for version in parent.iterdir():
            if version.name != 'v0' or not version.is_dir() or version.is_symlink():
                raise UnsupportedSchemaError(f'unsupported schema version/layout: {version}')
            for entry in version.iterdir():
                if namespace == 'canonical':
                    if entry.name not in COLLECTION_TYPES or not entry.is_dir() or entry.is_symlink():
                        raise UnsupportedSchemaError(f'unsupported schema collection: {entry}')
                    paths = entry.iterdir()
                else:
                    paths = (entry,)
                for path in paths:
                    if not path.is_file() or path.is_symlink() or path.suffix != '.json':
                        raise UnsupportedSchemaError(f'unsupported schema artifact layout: {path}')
                    if namespace == 'changesets':
                        # Use the same complete decoder as downstream readers,
                        # including closed operation shapes and record identity.
                        load_changeset(path)


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
        allowed = {field.name for field in fields(annotation) if field.init}
        if not isinstance(value, dict) or set(value) - allowed:
            raise UnsupportedSchemaError('unsupported fields in schema v0 record')
        return annotation(**{field.name: _decode(hints[field.name], value[field.name])
                             for field in fields(annotation)
                             if field.name in value and field.init})
    return value


def _document(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def record_document(record_type: str, record: Any) -> str:
    if record_type not in RECORD_SPECS:
        raise CanonicalStorageError(f"unknown record type: {record_type}")
    cls = RECORD_SPECS[record_type][2]
    if type(record) is not cls or set(vars(record)) != {f.name for f in fields(cls)}:
        raise UnsupportedSchemaError('v1/extended record cannot be serialized as schema v0')
    return _document({
        "artifact_format_version": ARTIFACT_FORMAT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "record_type": record_type,
        "record": _json_value(record),
    })


def changeset_document(change: ChangeSet) -> str:
    # ChangeSet is mutable; recheck identity at the persistence boundary too.
    if (not change.change_set_id.strip() or change.change_set_id in ('.', '..') or
            any(c in change.change_set_id for c in ('/', '\\', '\x00'))):
        raise CanonicalStorageError('ChangeSet id must be a single path component')
    if (type(change.schema_version) is not int or change.schema_version != 0 or
            type(change.artifact_format_version) is not int or change.artifact_format_version != 1):
        raise UnsupportedSchemaError('unsupported schema version for persistence; v1 activation is disabled')
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
    _check_envelope(payload, path, changeset=True)
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
    assert_supported_repository(root)
    # Preflight the whole candidate before the first write/unlink. Caller-made
    # PreparedCandidate values cannot activate v1 or skip the domain boundary.
    changeset_document(change)
    from .record_contract import shape_errors
    from .write_service import _operation_errors, _apply_operations
    errors = shape_errors(prepared.base) + shape_errors(prepared.result) + shape_errors(change.records)
    if errors:
        raise UnsupportedSchemaError('; '.join(errors))
    change.assert_validated_unchanged()
    errors = list(_operation_errors(change, prepared.base)) + validate_records(prepared.result)
    if errors or _apply_operations(prepared.base, change) != prepared.result:
        raise CanonicalStorageError('candidate does not match validated ChangeSet operations')
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
    assert_supported_repository(root)
    values: Dict[str, List[Any]] = {field.name: [] for field in fields(CanonicalRecords)}
    canonical_root = root / "canonical" / "v0"
    for collection, (kind, _, record_class) in COLLECTION_TYPES.items():
        for path in sorted((canonical_root / collection).glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            _check_envelope(payload, path)
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
