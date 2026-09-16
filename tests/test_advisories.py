"""Tests for conditions that expire.

Run with:  python -m pytest tests/test_advisories.py
"""

from __future__ import annotations

import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.advisories import (
    CAUTION, DANGER, INFO, STALE_DAYS, TRAIL_CLOSURE, WATER_QUALITY,
    Advisory, advisories_for, load_advisories,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADVISORIES = os.path.join(ROOT, "data", "advisories.csv")
D = datetime.date


def _adv(aid="a", park="P", kind=TRAIL_CLOSURE, observed="2026-09-01", **kw):
    return Advisory(advisory_id=aid, scope_type="park", scope_value=park, kind=kind,
                    summary="x", observed_date=observed, **kw)


def test_missing_file_is_not_an_error(tmp_path):
    assert load_advisories(tmp_path / "nope.csv") == []


def test_an_advisory_with_no_date_is_refused(tmp_path):
    # The date is the only thing that lets a reader judge the rest. Repeating
    # an undated closure is how a lifted one outlives the closure.
    p = tmp_path / "advisories.csv"
    p.write_text("advisory_id,scope_type,scope_value,kind,severity,summary,observed_date\n"
                 "a,park,P,trail_closure,info,Closed,\n")
    with pytest.raises(ValueError, match="observed_date"):
        load_advisories(p)


def test_an_end_date_and_until_further_notice_cannot_both_be_stated(tmp_path):
    # They are the two answers this table exists to keep apart.
    p = tmp_path / "advisories.csv"
    p.write_text("advisory_id,scope_type,scope_value,kind,severity,summary,observed_date,"
                 "ends,until_further_notice\n"
                 "a,park,P,trail_closure,info,Closed,2026-09-01,2026-10-01,True\n")
    with pytest.raises(ValueError, match="until_further_notice"):
        load_advisories(p)


def test_invalid_kind_and_severity_are_refused(tmp_path):
    p = tmp_path / "advisories.csv"
    p.write_text("advisory_id,scope_type,scope_value,kind,severity,summary,observed_date\n"
                 "a,park,P,mudslide,info,x,2026-09-01\n")
    with pytest.raises(ValueError, match="kind"):
        load_advisories(p)


# -- the date behaviour that makes this table safe --------------------------

def test_an_advisory_with_a_stated_end_drops_after_it():
    a = _adv(ends="2026-10-01")
    assert a.in_force(D(2026, 9, 30))
    assert not a.in_force(D(2026, 10, 2))


def test_an_advisory_that_has_not_started_is_not_in_force():
    a = _adv(starts="2026-10-05", ends="2026-10-12")
    assert not a.in_force(D(2026, 10, 1))
    assert a.in_force(D(2026, 10, 6))


def test_an_open_ended_advisory_never_expires_on_its_own():
    # The agency has not said it is over. Deciding that for them would be the
    # confident wrong answer this table risks.
    a = _adv(until_further_notice=True)
    assert a.in_force(D(2030, 1, 1))


def test_an_open_ended_advisory_reports_its_age_instead():
    a = _adv(observed="2026-09-01", until_further_notice=True)
    assert not a.stale(D(2026, 9, 20))
    assert a.stale(D(2026, 9, 1) + datetime.timedelta(days=STALE_DAYS + 1))


def test_a_dated_advisory_is_never_called_stale():
    # It is either in force or over; its age says nothing about which.
    a = _adv(observed="2020-01-01", ends="2020-02-01")
    assert not a.stale(D(2026, 9, 16))


# -- resolution --------------------------------------------------------------

def test_advisories_resolve_by_scope_and_by_date():
    here = _adv("here", park="Mine", ends="2026-12-01")
    gone = _adv("gone", park="Mine", ends="2026-01-01")
    elsewhere = _adv("elsewhere", park="Yours", until_further_notice=True)
    got = advisories_for([here, gone, elsewhere], D(2026, 10, 17), park="Mine")
    assert [a.advisory_id for a in got] == ["here"]


def test_the_worst_reads_first():
    mild = _adv("mild", severity=INFO, until_further_notice=True)
    bad = _adv("bad", severity=DANGER, until_further_notice=True)
    mid = _adv("mid", severity=CAUTION, until_further_notice=True)
    got = advisories_for([mild, bad, mid], D(2026, 10, 17), park="P")
    assert [a.advisory_id for a in got] == ["bad", "mid", "mild"]


# -- the committed data ------------------------------------------------------

def test_every_committed_advisory_is_dated_and_sourced():
    for a in load_advisories(ADVISORIES):
        assert a.observed_date, a.advisory_id
        assert a.source_url and a.log_entry_ids, a.advisory_id
        assert a.ends or a.until_further_notice, (
            f"{a.advisory_id}: an advisory must say whether it has an end")


def test_anthony_chabots_storm_closures_are_in_force_and_open_ended():
    adv = advisories_for(load_advisories(ADVISORIES), D(2026, 10, 17),
                         park="Anthony Chabot Regional Park")
    storm = next(a for a in adv if a.advisory_id == "chabot-storm-trails-2026")
    assert storm.kind == TRAIL_CLOSURE and storm.severity == CAUTION
    assert storm.until_further_notice and not storm.ends


def test_the_algae_advisory_notes_that_animals_were_never_allowed_there():
    # Ordinance 38 s.801.1 bars every animal from a bathing beach, leashed or
    # not, so the advisory changes nothing for a dog or a cat -- and saying so
    # stops a reader inferring that the beach is otherwise pet-friendly.
    adv = load_advisories(ADVISORIES)
    west = next(a for a in adv if a.advisory_id == "del-valle-algae-west")
    assert west.kind == WATER_QUALITY
    assert "801.1" in west.detail


# -- fields that had never been used until Reinhardt Redwood ------------------

def test_the_start_date_field_finally_carries_a_value():
    # Every advisory before this one was already in force when it was read, so
    # `starts` was a column nothing used. A closure that began three weeks
    # before it was read is the case it exists for.
    advisories = {a.advisory_id: a for a in load_advisories(ADVISORIES)}
    repairs = advisories["reinhardt-stream-trail-repairs"]
    assert repairs.starts == "2026-08-24"
    assert repairs.in_force(datetime.date(2026, 9, 16))
    assert not repairs.in_force(datetime.date(2026, 8, 1)), "not yet begun"


def test_a_vague_window_is_stored_as_words_not_as_invented_dates():
    # "late September and early October" is not a date. Writing 2026-09-20
    # would be inventing precision EBRPD did not publish -- the same error as a
    # guessed coordinate or a guessed access mode.
    a = {x.advisory_id: x for x in load_advisories(ADVISORIES)}["reinhardt-stream-trail-old-church"]
    assert a.starts == "" and a.ends == ""
    assert a.until_further_notice is True
    assert "late September and early October" in a.detail
    assert "OVERSTATES" in a.detail, "says openly that open-ended is too strong here"


def test_the_boil_water_notice_is_rated_danger_and_says_why_it_is_not_a_water_row():
    # The first danger-rated advisory, and the first water fact here that is
    # not about availability: the spigot runs and must not be drunk untreated.
    a = {x.advisory_id: x
         for x in load_advisories(ADVISORIES)}["reinhardt-piedmont-stables-boil-water"]
    assert a.kind == "water_quality" and a.severity == "danger"
    assert "water_sources.location must resolve" in a.detail
