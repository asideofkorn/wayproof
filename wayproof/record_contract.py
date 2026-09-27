"""Runtime record-shape checks at version boundaries."""
from dataclasses import fields
from typing import get_args, get_type_hints

from .schema import CanonicalRecords


def shape_errors(records, *, media=False):
    """Reject subclasses/extra fields rather than silently dropping extensions."""
    from .media_schema import MediaRecords, MEDIA_SPECS, MediaSource, MediaObservation, MediaTombstone
    cls = MediaRecords if media else CanonicalRecords
    if type(records) is not cls or set(vars(records)) != {f.name for f in fields(cls)}:
        return ['record container does not match schema version']
    errors = []
    hints = get_type_hints(CanonicalRecords)
    extras = {collection: (typ, MediaTombstone) for collection, _, typ in MEDIA_SPECS.values()}
    for field in fields(cls):
        items = getattr(records, field.name)
        if type(items) is not list:
            errors.append(f'{field.name} must be a record list')
            continue
        allowed = extras[field.name] if field.name in extras else (get_args(hints[field.name])[0],)
        if media and field.name == 'sources':
            # This container is the proposed delta; unclassified Sources are
            # allowed only in the separately validated v0 baseline.
            allowed = (MediaSource,)
        if media and field.name == 'observations':
            allowed += (MediaObservation,)
        for item in items:
            if type(item) not in allowed or set(vars(item)) != {f.name for f in fields(item)}:
                errors.append(f'{field.name} record does not match schema version')
    return errors
