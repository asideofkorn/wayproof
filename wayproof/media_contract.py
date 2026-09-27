"""Closed media wire shapes and explicit typed conversion; no file write API."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, is_dataclass
from datetime import date, datetime
import json
from pathlib import Path
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from jsonschema import Draft202012Validator, FormatChecker

from . import schema
from .media_schema import (MEDIA_SPECS, MediaSource, MediaObservation,
                           MediaTombstone)

SCHEMA = json.loads(Path(__file__).with_name('media_contract.json').read_text())
CHECK = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
CORE_SPECS = {
    'source': ('sources', 'source_id', schema.Source),
    'observation': ('observations', 'observation_id', schema.Observation),
    'evidence': ('evidence', 'evidence_id', schema.Evidence),
    'claim': ('claims', 'claim_id', schema.Claim),
}
SPECS = {**CORE_SPECS, **MEDIA_SPECS}
COLLECTIONS = {collection: kind for kind, (collection, _, _) in SPECS.items()}


def wire(value):
    """Return a detached JSON value; never downgrade a v1 record to v0."""
    if is_dataclass(value):
        return {f.name: wire(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [wire(item) for item in value]
    if isinstance(value, dict):
        return {key: wire(item) for key, item in value.items()}
    return deepcopy(value)


def _typed(annotation, value):
    origin, args = get_origin(annotation), get_args(annotation)
    if annotation is Any:
        return deepcopy(value)
    if origin in (Union, UnionType):
        for option in args:
            try:
                return _typed(option, value)
            except (TypeError, ValueError):
                pass
        raise ValueError('value does not match union')
    if origin is Literal:
        if value not in args:
            raise ValueError('invalid literal')
        return value
    if origin in (tuple, list):
        if not isinstance(value, (list, tuple)):
            raise ValueError('expected array')
        return origin(_typed(args[0], item) for item in value)
    if annotation in (datetime, date):
        return annotation.fromisoformat(value)
    if is_dataclass(annotation):
        hints = get_type_hints(annotation)
        if not isinstance(value, dict) or set(value) != {f.name for f in fields(annotation)}:
            raise ValueError('record fields do not match type')
        return annotation(**{key: _typed(hints[key], item) for key, item in value.items()})
    if annotation is float and type(value) in (int, float):
        return float(value)
    if type(value) is not annotation:
        raise ValueError('invalid scalar type')
    return value


def decode_record(kind: str, value: dict):
    if kind not in SPECS:
        raise ValueError(f'unknown media-contract record type: {kind}')
    # Python callers can supply NaN or non-JSON objects even though JSON cannot.
    json.dumps(value, allow_nan=False)
    definition = {'$defs': SCHEMA['$defs'], '$ref': f'#/$defs/{kind}'}
    Draft202012Validator(definition, format_checker=FormatChecker()).validate(value)
    cls = SPECS[kind][2]
    if value.get('state') in ('removed', 'redacted'):
        if kind not in MEDIA_SPECS:
            raise ValueError('core-record removal requires the later deletion workflow')
        cls = MediaTombstone
    elif kind == 'source' and 'source_role' in value:
        cls = MediaSource
    elif kind == 'observation' and 'origin_kind' in value:
        cls = MediaObservation
    return _typed(cls, value)


def public_bundle(records):
    return {'schema_version': 1, 'visibility': 'public', 'records': {
        collection: [wire(item) for item in getattr(records, collection, ())]
        for collection in COLLECTIONS}}
