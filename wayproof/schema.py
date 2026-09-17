"""Which vocabulary governs which stored column, and whether a row is well formed.

Moved out of ``tests/test_schema_integrity.py`` when the ingest path needed the
same registry: a value is checked the same way whether it is already committed
or about to be written.

Rules are pinned one test each in ``tests/test_schema_integrity.py`` and
``tests/test_ingest.py``.
"""

from __future__ import annotations

import csv
import pathlib
from typing import Dict, List, Mapping, Sequence, Tuple

from . import booking, camping, permits
from .access import _VALID_STATUSES
from .advisories import _VALID_KINDS, _VALID_SEVERITY
from .regulations import _VALID_SCOPES

DATA = pathlib.Path("data")

#: ``(csv, column, allowed values, multi-valued)``. Every vocabulary that
#: governs stored data belongs here, whether or not its loader also checks it --
#: `permit_source_log.csv:verdict` is the case that does not.
#:
#: `campgrounds.csv:campsite_type` is absent on purpose: it has no vocabulary to
#: bind to. See CLAUDE.md's Known list.
BOUND: List[Tuple[str, str, set, bool]] = [
    ("campgrounds.csv", "access_mode", camping._VALID_ACCESS_MODES, True),
    ("campgrounds.csv", "coord_precision", camping._VALID_COORD_PRECISION, False),
    ("campgrounds.csv", "unit_level", camping._VALID_UNIT_LEVELS, False),
    ("campgrounds.csv", "pets_marker", camping._VALID_PETS_MARKERS, False),
    ("campgrounds.csv", "pets_animals", camping._VALID_PETS_ANIMALS, True),
    ("campsites.csv", "site_type", camping._VALID_SITE_TYPES, False),
    ("booking_channels.csv", "applies_to", booking._VALID_APPLIES_TO, False),
    ("booking_channels.csv", "scope_type", _VALID_SCOPES, False),
    ("regulations.csv", "scope_type", _VALID_SCOPES, False),
    ("advisories.csv", "scope_type", _VALID_SCOPES, False),
    ("advisories.csv", "kind", _VALID_KINDS, False),
    ("advisories.csv", "severity", _VALID_SEVERITY, False),
    ("approaches.csv", "status", _VALID_STATUSES, False),
    ("permit_source_log.csv", "verdict", permits._VALID_VERDICTS, False),
]

#: Vocabularies that guard a function argument or a derived value rather than a
#: stored column. Listed so the coverage test cannot pass by forgetting one.
NOT_STORED = {
    "_VALID_CONFIDENCE", "_VALID_STATUS",   # reports.py, set at submit time
    "_VALID_ROLES",                          # provenance.py
    "_VALID_MECHANISMS", "_VALID_SEASONS",   # release_policy.py, parsed from prose
}


def vocabularies_for(table: str) -> List[Tuple[str, set, bool]]:
    """``[(column, allowed, multi), ...]`` bound for one table."""
    return [(c, v, m) for t, c, v, m in BOUND if t == table]


def header(table: str, data_dir: pathlib.Path = DATA) -> List[str]:
    with open(data_dir / table, newline="") as f:
        return next(csv.reader(f))


def rows(table: str, data_dir: pathlib.Path = DATA) -> List[dict]:
    with open(data_dir / table, newline="") as f:
        return list(csv.DictReader(f))


def key_is_unique(table: str, data_dir: pathlib.Path = DATA) -> bool:
    """Is this table's first column currently a unique key?

    Derived rather than declared: five tables are legitimately one-to-many
    (`timed_entry`, `release_policies`, ...) and hard-coding a list of them
    would go stale. What matters is that a table which IS keyed stays keyed.
    """
    col = header(table, data_dir)[0]
    values = [r[col] for r in rows(table, data_dir)]
    return len(values) == len(set(values))


def validate_row(table: str, values: Mapping[str, str],
                 data_dir: pathlib.Path = DATA) -> List[str]:
    """Everything wrong with a row about to be written. Empty means writable.

    Checks the three things that fail silently once committed: a column that
    does not exist (the value is simply dropped), a value outside its
    vocabulary (the join resolves to nothing), and a duplicate key in a table
    that has unique keys (one row shadows the other).
    """
    problems: List[str] = []
    cols = header(table, data_dir)

    unknown = [c for c in values if c not in cols]
    if unknown:
        problems.append(f"columns not in {table}: {sorted(unknown)}")

    for column, allowed, multi in vocabularies_for(table):
        raw = str(values.get(column, "") or "").strip()
        if not raw:
            continue
        parts = [p.strip() for p in raw.split(";")] if multi else [raw]
        bad = [p for p in parts if p and p not in allowed]
        if bad:
            problems.append(f"{column}={bad} outside {sorted(allowed)}")

    key = cols[0]
    new_key = str(values.get(key, "") or "").strip()
    if not new_key:
        problems.append(f"{key} is required: it is this table's key")
    elif key_is_unique(table, data_dir):
        existing = {r[key] for r in rows(table, data_dir)}
        if new_key in existing:
            problems.append(f"{key}={new_key!r} already exists in {table}")

    return problems
