"""Tests for the provenance check: rows added without a reading behind them.

The outcome check, not a path check. Every convention in this repo has drifted
and every mechanical check has held, so this does not care how a row arrived --
`wayproof.ingest.add_row`, a heredoc, an editor -- only that the ledger grew
when the data did.

Run with:  python -m pytest tests/test_provenance_check.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from check_provenance import LEDGER, MIGRATION, verdict


def test_a_row_added_with_no_ledger_entry_fails():
    # The failure this exists for, and the one I committed twice tonight.
    problems = verdict({"data/campgrounds.csv": 37, LEDGER: 150},
                       {"data/campgrounds.csv": 38, LEDGER: 150})
    assert problems and "no new entry" in problems[0]


def test_a_row_added_with_a_ledger_entry_passes():
    assert verdict({"data/campgrounds.csv": 37, LEDGER: 150},
                   {"data/campgrounds.csv": 38, LEDGER: 151}) == []


def test_one_entry_may_justify_many_rows():
    # A single page read added seven Anthony Chabot group camps. Asking for one
    # entry per row would make the honest path the expensive one.
    assert verdict({"data/campgrounds.csv": 30, LEDGER: 150},
                   {"data/campgrounds.csv": 37, LEDGER: 151}) == []


def test_a_migration_stands_the_check_down():
    # Splitting pets out of `notes` moved facts already sourced on those rows.
    # It adds no reading and owes no entry -- but it has to say so.
    assert verdict({"data/campgrounds.csv": 37, LEDGER: 150},
                   {"data/campgrounds.csv": 40, LEDGER: 150},
                   f"Split pets out of notes {MIGRATION}") == []


def test_changing_a_row_without_adding_one_is_not_this_checks_business():
    # Corrections go through append-conflict-correct, which touches the ledger
    # by its own rules. Row counts do not move, and this must stay quiet rather
    # than duplicate that procedure badly.
    assert verdict({"data/campgrounds.csv": 37, LEDGER: 150},
                   {"data/campgrounds.csv": 37, LEDGER: 150}) == []


def test_growth_in_the_ledger_alone_is_not_growth_in_the_data():
    # The ledger is excluded from the tables it guards; otherwise appending an
    # entry would satisfy the check by counting itself.
    assert verdict({LEDGER: 150}, {LEDGER: 151}) == []


def test_a_brand_new_data_file_counts_as_added_rows():
    problems = verdict({LEDGER: 150},
                       {"data/new_table.csv": 4, LEDGER: 150})
    assert problems and "new_table.csv +4" in problems[0]


def test_a_deleted_file_is_not_reported_as_growth():
    assert verdict({"data/gone.csv": 9, LEDGER: 150}, {LEDGER: 150}) == []


def test_the_message_names_the_way_out():
    problems = verdict({"data/campgrounds.csv": 1, LEDGER: 1},
                       {"data/campgrounds.csv": 2, LEDGER: 1})
    assert "wayproof.ingest.add_row" in problems[0] and MIGRATION in problems[0]
