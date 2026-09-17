"""Tests for the ingest path: a row and the ledger entry that justifies it.

The scorecard's biggest bucket is `no-data` -- 48% of cells, meaning the field
exists and nobody filled it. Filling it by hand goes wrong in three quiet ways:
a column that does not exist (the value is dropped), a value outside its
vocabulary (the join resolves to nothing), a colliding entry id (one entry
shadows another). Each is pinned below.

The load-bearing one is
:func:`test_a_row_cannot_be_written_without_a_source`. "Never write a value you
did not read" was a convention; here it is the only way through.

Run with:  python -m pytest tests/test_ingest.py
"""

from __future__ import annotations

import csv
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof import ingest, schema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def data(tmp_path):
    """A throwaway copy of the real data, so writes are real but discarded."""
    dst = tmp_path / "data"
    dst.mkdir()
    for name in ("campgrounds.csv", "permit_source_log.csv", "regulations.csv"):
        shutil.copy(os.path.join(ROOT, "data", name), dst / name)
    return dst


def _camp(**kw):
    values = {"name": "Test Camp", "park": "Test Park", "agency_id": "ebrpd"}
    values.update(kw)
    return values


def _entry(data, **kw):
    kw.setdefault("source_url", "https://example.org/page")
    kw.setdefault("summary", "The page states the camp takes pets.")
    kw.setdefault("on", "2026-09-17")
    return ingest.build_entry(data_dir=data, **kw)


# -- the invariant this exists to enforce -----------------------------------

def test_a_row_cannot_be_written_without_a_source(data):
    # CLAUDE.md's first data invariant, made mechanical. A row with no source
    # is a guess, and the ledger entry is what makes it not one.
    entry = _entry(data, source_url="")
    with pytest.raises(ValueError, match="source_url is required"):
        ingest.add_row("campgrounds.csv", _camp(), entry, data)
    assert "Test Camp" not in _keys(data, "campgrounds.csv")


def test_a_row_cannot_be_written_without_saying_what_the_source_said(data):
    entry = _entry(data, summary="")
    with pytest.raises(ValueError, match="summary is required"):
        ingest.add_row("campgrounds.csv", _camp(), entry, data)


def test_the_row_and_its_entry_are_written_together(data):
    entry = _entry(data)
    ingest.add_row("campgrounds.csv", _camp(pets_marker="allowed"), entry, data)
    assert "Test Camp" in _keys(data, "campgrounds.csv")
    assert entry.entry_id in _keys(data, ingest.LOG)


def test_neither_lands_when_either_is_invalid(data):
    # A ledger entry for a row that was refused is a claim about a write that
    # did not happen. Checked together, written together.
    before_rows = len(schema.rows("campgrounds.csv", data))
    before_log = len(schema.rows(ingest.LOG, data))
    with pytest.raises(ValueError):
        ingest.add_row("campgrounds.csv", _camp(pets_marker="maybe"),
                       _entry(data), data)
    assert len(schema.rows("campgrounds.csv", data)) == before_rows
    assert len(schema.rows(ingest.LOG, data)) == before_log


# -- the three quiet failures -----------------------------------------------

def test_a_column_that_does_not_exist_is_refused(data):
    # Written by hand this drops the value silently: DictWriter keeps only the
    # header's columns, so the fact vanishes and the row looks fine.
    problems = schema.validate_row("campgrounds.csv", _camp(pets_allowed="yes"), data)
    assert any("columns not in" in p for p in problems)


def test_a_value_outside_its_vocabulary_is_refused(data):
    problems = schema.validate_row("campgrounds.csv", _camp(access_mode="drive"), data)
    assert any("access_mode" in p for p in problems)


def test_a_multi_valued_column_is_checked_part_by_part(data):
    ok = schema.validate_row("campgrounds.csv", _camp(access_mode="drive_in;hike_in"), data)
    bad = schema.validate_row("campgrounds.csv", _camp(access_mode="drive_in;walk"), data)
    assert ok == [] and any("walk" in p for p in bad)


def test_a_duplicate_key_is_refused_where_the_key_is_unique(data):
    problems = schema.validate_row(
        "campgrounds.csv", _camp(name="Anthony Chabot Campground"), data)
    assert any("already exists" in p for p in problems)


def test_a_missing_key_is_refused(data):
    problems = schema.validate_row("campgrounds.csv", {"park": "X"}, data)
    assert any("is required" in p for p in problems)


# -- entry ids ---------------------------------------------------------------

def test_an_entry_id_does_not_collide_with_one_written_by_hand(data):
    # Ids are per group per day. Counting rows would reuse an id the moment
    # anyone appended an entry earlier in the session.
    first = _entry(data)
    ingest.add_row("campgrounds.csv", _camp(name="A"), first, data)
    second = _entry(data)
    assert second.entry_id != first.entry_id
    assert second.entry_id.endswith(f"{int(first.entry_id[-2:]) + 1:02d}")


def test_entry_ids_are_scoped_to_their_day(data):
    a = _entry(data, on="2026-09-17")
    b = _entry(data, on="2026-09-18")
    assert a.entry_id.startswith("none-2026-09-17-")
    assert b.entry_id.endswith("-01"), "a new day starts its own sequence"


def test_a_verdict_outside_the_ledgers_vocabulary_is_refused(data):
    problems = ingest.validate_entry(_entry(data, verdict="looks-right"))
    assert any("verdict" in p for p in problems)


def test_a_conflict_kind_with_no_conflict_id_is_refused(data):
    problems = ingest.validate_entry(_entry(data, conflict_kind="internal"))
    assert any("names no disagreement" in p for p in problems)


def test_a_malformed_date_is_refused(data):
    problems = ingest.validate_entry(_entry(data, on="17/09/2026"))
    assert any("date_checked" in p for p in problems)


# -- what it writes still loads ----------------------------------------------

def test_a_written_row_loads_through_the_real_loader(data):
    from wayproof.camping import load_campgrounds
    ingest.add_row("campgrounds.csv",
                   _camp(name="Loadable Camp", access_mode="drive_in",
                         pets_marker="not_marked"),
                   _entry(data), data)
    names = {c.name for c in load_campgrounds(data / "campgrounds.csv")}
    assert "Loadable Camp" in names


def _keys(data, table):
    col = schema.header(table, data)[0]
    return {r[col] for r in schema.rows(table, data)}
