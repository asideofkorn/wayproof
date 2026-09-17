"""Guards that the CSVs and the code that loads them still agree.

Written after a prototype data dictionary found `campgrounds.csv:campsite_type`
holding `equestrian`, which no channel vocabulary contains: `channels_for()`
matches nothing and falls back to agency-wide channels, so a party booking a
horse camp gets the generic District phone number and no warning. That column
is deliberately still unbound below -- binding it needs a site-class vocabulary
that does not exist yet. A document would not have found it; these guard the
columns that do have one.

Run with:  python -m pytest tests/test_schema_integrity.py
"""

from __future__ import annotations

import csv
import os
import pathlib
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.schema import BOUND, NOT_STORED

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

def _values(table, column, multi):
    path = DATA / table
    out = []
    with open(path, newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            raw = (row.get(column) or "").strip()
            if not raw:
                continue
            parts = [p.strip() for p in raw.split(";")] if multi else [raw]
            out += [(i, p) for p in parts if p]
    return out


@pytest.mark.parametrize("table,column,allowed,multi", BOUND,
                         ids=[f"{t}:{c}" for t, c, _, _ in BOUND])
def test_stored_values_are_inside_their_vocabulary(table, column, allowed, multi):
    # The equestrian failure, generalised. A value outside its vocabulary does
    # not raise -- it resolves to nothing, quietly, wherever the join is used.
    bad = [(line, v) for line, v in _values(table, column, multi) if v not in allowed]
    assert bad == [], (
        f"data/{table}:{column} holds values outside {sorted(allowed)}: {bad}"
    )


@pytest.mark.parametrize("table,column,allowed,multi", BOUND,
                         ids=[f"{t}:{c}" for t, c, _, _ in BOUND])
def test_every_bound_column_exists(table, column, allowed, multi):
    with open(DATA / table, newline="") as f:
        header = next(csv.reader(f))
    assert column in header, f"{table} has no column {column!r}; this binding is stale"


def _declared_vocabularies():
    """``{name: set}`` for every ``_VALID_*`` in the package."""
    import importlib
    out = {}
    for p in sorted((ROOT / "wayproof").glob("*.py")):
        if p.stem == "__init__":
            continue
        mod = importlib.import_module(f"wayproof.{p.stem}")
        for name in re.findall(r"^(_VALID_\w+)\s*=", p.read_text(), re.M):
            out[name] = getattr(mod, name)
    return out


def test_every_vocabulary_is_accounted_for():
    # What keeps BOUND honest. Add a _VALID_* set and this fails until you say
    # which column it governs, or declare that it governs none. Without it the
    # coverage test above passes by omission -- which is how
    # `permit_source_log.csv:verdict` came to have a vocabulary that no loader
    # and no test ever checked.
    declared = _declared_vocabularies()
    bound = {name for name, vocab in declared.items()
             if any(vocab is v for _, _, v, _ in BOUND)}
    missing = sorted(set(declared) - bound - NOT_STORED)
    assert missing == [], (
        f"vocabularies governing nothing declared: {missing}. Add each to BOUND "
        f"with the column it governs, or to NOT_STORED with why it governs no "
        f"stored column."
    )


#: Columns present in a CSV that no loader reads by name. Some are read through
#: a generic path (`peaks.csv` collects the rest into a `meta` dict); the rest
#: are candidates for deletion. Pinned rather than asserted empty: the point is
#: that the number must not grow unnoticed.
UNREAD_ALLOWED = 32


def test_unread_columns_do_not_grow():
    read = set()
    for folder in ("wayproof", "scripts"):
        for p in (ROOT / folder).glob("*.py"):
            src = p.read_text()
            read |= set(re.findall(r'_\w*field\(row,\s*["\'](\w+)["\']', src))
            read |= set(re.findall(r'row\.get\(["\'](\w+)["\']', src))
            read |= set(re.findall(r'row\[["\'](\w+)["\']\]', src))
    cols = set()
    for p in DATA.rglob("*.csv"):
        with open(p, newline="") as f:
            cols |= set(next(csv.reader(f)))
    unread = sorted(cols - read)
    assert len(unread) <= UNREAD_ALLOWED, (
        f"{len(unread)} columns no loader reads by name (was {UNREAD_ALLOWED}): "
        f"{unread}. Either wire the new column up or delete it."
    )
