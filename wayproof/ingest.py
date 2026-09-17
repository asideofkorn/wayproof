"""Writing a row and the ledger entry that justifies it, in one step.

Reading a source and turning it into rows is the whole bottleneck -- the
scorecard's biggest bucket is `no-data`, meaning the field exists and nobody
filled it. The judgement stays human: which facts, which table, what scope.
What this removes is the mechanical part that goes wrong quietly -- a column
that does not exist, a value outside its vocabulary, a colliding entry id.

It cannot write a row without a source and a ledger entry. That is the point:
"never write a value you did not read" stops being a convention and becomes
the only way through.

Rules are pinned one test each in ``tests/test_ingest.py``.
"""

from __future__ import annotations

import csv
import datetime
import pathlib
import re
from dataclasses import dataclass
from typing import List, Mapping, Optional

from . import schema
from .permits import _VALID_VERDICTS

LOG = "permit_source_log.csv"

NO_GROUP = "none"
"""The ledger's key for an entry that belongs to no permit group.

Most of what is ingested now is campgrounds, parks and regulations, which have
no permit group. The ledger has always taken `none` for these -- 60 entries
already use it -- so this is the existing convention, not a new one.
"""


@dataclass
class Entry:
    """A ledger entry justifying one write."""

    entry_id: str
    date_checked: str
    permit_group: str
    source_url: str
    method: str
    verdict: str
    summary: str
    source_last_updated: str = ""
    conflict_id: str = ""
    conflict_kind: str = ""

    def as_row(self) -> dict:
        return {
            "entry_id": self.entry_id, "date_checked": self.date_checked,
            "permit_group": self.permit_group, "source_url": self.source_url,
            "source_last_updated": self.source_last_updated, "method": self.method,
            "verdict": self.verdict, "summary": self.summary,
            "conflict_id": self.conflict_id, "conflict_kind": self.conflict_kind,
        }


def next_entry_id(permit_group: str, on: str,
                  data_dir: pathlib.Path = schema.DATA) -> str:
    """The next free ``group-YYYY-MM-DD-NN`` id for that group and day.

    Scans the ledger rather than counting rows: ids are per group per day, and
    a hand-written entry earlier in the session must not be overwritten.
    """
    prefix = f"{permit_group}-{on}-"
    used = []
    for row in schema.rows(LOG, data_dir):
        rid = row.get("entry_id", "")
        if rid.startswith(prefix):
            tail = rid[len(prefix):]
            if tail.isdigit():
                used.append(int(tail))
    return f"{prefix}{max(used, default=0) + 1:02d}"


def validate_entry(entry: Entry) -> List[str]:
    """Everything wrong with a ledger entry. Empty means writable."""
    problems = []
    if entry.verdict not in _VALID_VERDICTS:
        problems.append(f"verdict={entry.verdict!r} outside {sorted(_VALID_VERDICTS)}")
    if not entry.source_url.strip():
        problems.append("source_url is required: a row with no source is a guess")
    if not entry.summary.strip():
        problems.append("summary is required: say what the source actually said")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry.date_checked or ""):
        problems.append(f"date_checked={entry.date_checked!r} is not YYYY-MM-DD")
    if entry.conflict_kind and not entry.conflict_id:
        problems.append("conflict_kind without conflict_id names no disagreement")
    return problems


def _append(table: str, values: Mapping[str, str],
            data_dir: pathlib.Path = schema.DATA) -> None:
    cols = schema.header(table, data_dir)
    with open(data_dir / table, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=cols).writerow(
            {c: values.get(c, "") for c in cols})


def add_row(table: str, values: Mapping[str, str], entry: Entry,
            data_dir: pathlib.Path = schema.DATA) -> Entry:
    """Append a row AND its ledger entry, or raise having written neither.

    Validated together and written together: a row whose justification failed
    validation must not land, and a ledger entry for a row that was refused is
    a claim about a write that did not happen.
    """
    problems = schema.validate_row(table, values, data_dir) + validate_entry(entry)
    if problems:
        raise ValueError("; ".join(problems))
    _append(table, values, data_dir)
    _append(LOG, entry.as_row(), data_dir)
    return entry


def build_entry(source_url: str, summary: str, method: str = "page read",
                verdict: str = "new-group", permit_group: str = NO_GROUP,
                on: Optional[str] = None, source_last_updated: str = "",
                conflict_id: str = "", conflict_kind: str = "",
                data_dir: pathlib.Path = schema.DATA) -> Entry:
    """A ledger entry with its id allocated, ready to pass to :func:`add_row`."""
    on = on or datetime.date.today().isoformat()
    return Entry(
        entry_id=next_entry_id(permit_group, on, data_dir), date_checked=on,
        permit_group=permit_group, source_url=source_url, method=method,
        verdict=verdict, summary=summary, source_last_updated=source_last_updated,
        conflict_id=conflict_id, conflict_kind=conflict_kind,
    )
