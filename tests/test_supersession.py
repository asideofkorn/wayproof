"""Tests for supersession: a narrower rule displacing a broader one.

Rules are layered, and layered is not the same as equal. At Stewartville
Backpack Camp three alcohol rules reach you at once -- the District's "beer
and wine, 21 and over", Black Diamond's "no alcohol at all", and the
District's own backpack-site ban -- and before this existed all three printed
as peer bullets with nothing saying which one you are under. A camper reading
top-down got the permissive one.

The design decision these tests protect is that supersession is **recorded,
never derived**. Deriving it from scope looks obviously right and is wrong:
:func:`test_a_narrower_rule_does_not_supersede_merely_by_being_narrower` is
the counterexample, in real data.

Four failures pinned, each one something the obvious implementation does:

- **Deriving the edge from specificity.** Point Pinole's per-PERSON dog limit
  is narrower than the District's per-SITE limit and displaces nothing --
  they govern different things and the stricter applies where both do.
- **Firing the edge everywhere.** Black Diamond's ban displaces the District
  rule at Black Diamond and nowhere else.
- **Dropping the displaced rule.** Silence is not an answer; a camper who read
  the District rule elsewhere needs to be told it does not reach them.
- **A typo disabling the edge silently.** A dangling id renders as "still
  applies", which is the answer the edge exists to prevent, so it fails at
  load.

Run with:  python -m pytest tests/test_supersession.py
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.regulations import (
    AGENCY, PARK, Regulation, SUPERSEDED_FLAG, load_regulations,
    regulations_for, supersession_note, supersessions,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGS = os.path.join(ROOT, "data", "regulations.csv")


def _regs():
    return load_regulations(REGS)


def _by_id():
    return {r.regulation_id: r for r in _regs()}


def _reg(rid, scope_type=AGENCY, scope_value="ebrpd", category="camping",
         summary="", supersedes=""):
    return Regulation(regulation_id=rid, scope_type=scope_type,
                      scope_value=scope_value, category=category,
                      summary=summary or rid, supersedes=supersedes)


# -- recorded, not derived -------------------------------------------------

def test_a_narrower_rule_does_not_supersede_merely_by_being_narrower():
    # THE COUNTEREXAMPLE, in real data. point-pinole-dogs is park-scoped and
    # caps dogs at three PER PERSON; ebrpd-pets-count is agency-scoped and caps
    # them at three PER SITE. Narrower, and it displaces nothing: the two
    # measure different things and the stricter applies where both do. Derive
    # supersession from scope and a party of ten may bring thirty dogs to one
    # campsite.
    by_id = _by_id()
    assert by_id["point-pinole-dogs"].superseded_ids == []
    both = [by_id["point-pinole-dogs"], by_id["ebrpd-pets-count"]]
    assert supersessions(both) == {}


def test_a_rule_that_declares_nothing_displaces_nothing():
    assert supersessions([_reg("a"), _reg("b")]) == {}


def test_a_rule_narrow_only_in_its_wording_declares_no_edge():
    # THE BUG THIS FEATURE MADE, pinned. ebrpd-backpack-no-fire-no-alcohol is
    # narrow by naming a CLASS OF SITE, which this table has no scope level
    # for, so it is filed at AGENCY scope and is in force at every EBRPD
    # campground. Given an edge onto the District's fire rule it fired at
    # Anthony Chabot's drive-in family campground -- every site there has a
    # fire ring with a grill -- and marked Ordinance 38's barbecue permission
    # "does not apply here". It carries no edge, and the loader now refuses
    # one.
    backpack = _by_id()["ebrpd-backpack-no-fire-no-alcohol"]
    assert backpack.scope_type == AGENCY
    assert backpack.superseded_ids == []


def test_an_edge_onto_a_rule_at_the_same_scope_is_refused(tmp_path):
    rows = [_row("narrow-in-wording", supersedes="district-wide"),
            _row("district-wide")]
    with pytest.raises(ValueError, match="not broader than it"):
        load_regulations(_write(tmp_path, rows))


def test_every_recorded_edge_is_declared_by_a_narrower_scope():
    from wayproof.regulations import SPECIFICITY
    by_id = _by_id()
    for reg in _regs():
        for target in reg.superseded_ids:
            assert (SPECIFICITY[reg.scope_type]
                    < SPECIFICITY[by_id[target].scope_type]), reg.regulation_id


def test_the_family_campground_keeps_the_rule_it_is_actually_under():
    # The other half of the same bug: Anthony Chabot must show Ordinance 38's
    # fire rule as applying, unmarked.
    from wayproof.regulations import regulations_for
    at_chabot = regulations_for(_regs(), agency="ebrpd", jurisdiction="CA",
                                park="Anthony Chabot Regional Park")
    assert "ebrpd-fire" not in supersessions(at_chabot)


# -- it fires only where both rules are in force ---------------------------

def test_a_park_rule_displaces_only_inside_that_park():
    regs = _regs()
    at_black_diamond = regulations_for(regs, agency="ebrpd", jurisdiction="CA",
                                       park="Black Diamond Mines Regional Preserve")
    assert "ebrpd-alcohol" in supersessions(at_black_diamond)

    # Same agency, different park. The displacing rule is simply not in force,
    # so its edge cannot fire -- nothing here needed to know where we are.
    at_chabot = regulations_for(regs, agency="ebrpd", jurisdiction="CA",
                                park="Anthony Chabot Regional Park")
    assert "ebrpd-alcohol" not in supersessions(at_chabot)
    assert any(r.regulation_id == "ebrpd-alcohol" for r in at_chabot)


def test_the_whole_table_is_not_a_place_this_may_be_asked():
    # Passing every rule would report Sunol's fire ban as displacing the
    # District rule at Anthony Chabot. The guard is the docstring and this
    # test, which pins what the wrong call would produce.
    everywhere = supersessions(_regs())
    at_chabot = supersessions(regulations_for(
        _regs(), agency="ebrpd", jurisdiction="CA",
        park="Anthony Chabot Regional Park"))
    assert "ebrpd-fire" in everywhere
    assert at_chabot == {}, "no EBRPD rule displaces another at Anthony Chabot"


# -- the displaced rule is shown, never dropped ----------------------------

def test_the_displaced_rule_still_reaches_the_reader():
    from wayproof.camping import load_campgrounds
    from wayproof.plan import resolve_plan
    # Rendered through plan so this tests the surface, not just the helper.
    result = _stewartville()
    assert any(r.regulation_id == "ebrpd-alcohol" for r in result.regulations)


def _stewartville():
    import datetime
    from wayproof.camping import load_campgrounds, load_campsites
    from wayproof.permits import load_permits
    from wayproof.plan import resolve_plan
    return resolve_plan(
        ["Stewartville Backpack Camp"],
        peaks=[], trailheads=[],
        permits=load_permits(os.path.join(ROOT, "data", "permits.csv"),
                             os.path.join(ROOT, "data", "release_policies.csv")),
        trip_date=datetime.date(2026, 10, 17),
        campgrounds=load_campgrounds(os.path.join(ROOT, "data", "campgrounds.csv")),
        campsites=load_campsites(os.path.join(ROOT, "data", "campsites.csv")),
        regulations=_regs(),
    )


def test_the_plan_marks_it_rather_than_printing_it_as_a_peer():
    from wayproof.plan import format_plan_summary as format_plan
    text = format_plan(_stewartville())
    assert SUPERSEDED_FLAG in text
    # The District norm is present AND marked, on the same line.
    line = next(l for l in text.splitlines()
                if "No hard alcohol anywhere" in l)
    assert SUPERSEDED_FLAG in line


def test_the_note_quotes_the_rule_that_governs():
    from wayproof.plan import format_plan_summary as format_plan
    text = format_plan(_stewartville())
    assert "No alcohol at all is allowed at Black Diamond Mines" in text
    assert "Read that, not this." in text


def test_the_rule_doing_the_displacing_is_not_also_badged():
    # A badge on both halves is twice the text for one fact, and on a page of
    # twenty rules it is how the one that matters stops standing out.
    from wayproof.plan import format_plan_summary as format_plan
    text = format_plan(_stewartville())
    line = next(l for l in text.splitlines()
                if "No alcohol at all is allowed at Black Diamond" in l)
    assert SUPERSEDED_FLAG not in line


# -- the quote has to carry the clause that does the displacing ------------

def test_the_note_is_not_truncated_before_the_operative_clause():
    # ebrpd-backpack-no-fire-no-alcohol's alcohol clause is its LAST, and it is
    # the clause that displaces ebrpd-alcohol. A quote ending before it
    # explains nothing, which is what a 90-character limit did.
    note = supersession_note([_by_id()["ebrpd-backpack-no-fire-no-alcohol"]])
    assert "No alcohol at all, beer and wine included" in note
    assert "..." not in note


def test_the_note_names_the_stricter_rule_first():
    by_id = _by_id()
    note = supersession_note([by_id["ebrpd-backpack-no-fire-no-alcohol"],
                              by_id["black-diamond-no-alcohol"]])
    assert note.index("Black Diamond") < note.index("BACKPACK")


def test_no_displacers_means_no_note():
    assert supersession_note([]) == ""


# -- an edge that cannot mean anything is refused at load ------------------

def _write(tmp_path, rows):
    import csv
    path = tmp_path / "regulations.csv"
    fields = ["regulation_id", "scope_type", "scope_value", "category",
              "summary", "supersedes"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return path


def _row(rid, supersedes=""):
    return {"regulation_id": rid, "scope_type": "agency", "scope_value": "ebrpd",
            "category": "camping", "summary": rid, "supersedes": supersedes}


def test_a_dangling_id_fails_at_load_not_silently_at_render(tmp_path):
    # The dangerous failure: a typo does not raise when rendering, it quietly
    # leaves the displaced rule reading as if it still applied.
    path = _write(tmp_path, [_row("a", supersedes="ebrpd-alcohl")])
    with pytest.raises(ValueError, match="unknown rule"):
        load_regulations(path)


def test_a_rule_may_not_supersede_itself(tmp_path):
    path = _write(tmp_path, [_row("a", supersedes="a")])
    with pytest.raises(ValueError, match="supersedes itself"):
        load_regulations(path)


def test_mutual_supersession_is_refused(tmp_path):
    # What you write if you read "stricter than" in both rows' detail and fill
    # in both. It names no winner and cannot be rendered.
    path = _write(tmp_path, [_row("a", supersedes="b"), _row("b", supersedes="a")])
    with pytest.raises(ValueError, match="supersede each other"):
        load_regulations(path)


def test_a_blank_column_loads_clean(tmp_path):
    (reg,) = load_regulations(_write(tmp_path, [_row("a")]))
    assert reg.superseded_ids == []


# -- only full displacement is recorded ------------------------------------

def test_a_partial_override_is_not_recorded_as_supersession():
    # round-valley-no-dogs bans DOGS from a preserve whose campground rule
    # governs "dog, cat or other animal". Recording it as superseding would
    # tell someone arriving with a cat that Ordinance 38 does not apply to
    # them -- which is the confident wrong answer this project exists to
    # avoid, produced by the mechanism built to prevent one.
    by_id = _by_id()
    assert by_id["round-valley-no-dogs"].superseded_ids == []
    assert by_id["ebrpd-backpack-no-dogs-ohlone"].superseded_ids == []


def test_the_pets_answer_is_unaffected_by_the_dog_bans_staying_peers():
    # The consequence of the line above, checked where it would bite: a cat at
    # Round Valley is still governed by Ordinance 38's campground rule.
    from wayproof import pets
    from wayproof.camping import load_campgrounds
    camp = next(c for c in load_campgrounds(os.path.join(ROOT, "data", "campgrounds.csv"))
                if c.name == "Round Valley Backpack Camp")
    answer = pets.answer(camp, pets.rules_for_campground(camp, _regs()), "cat")
    assert "ebrpd-pets-campground" in {r.regulation_id for r in answer.governing}


# -- and the broad rule stops hand-maintaining its own exception list ------

def test_the_general_rule_no_longer_lists_its_own_exceptions():
    # ebrpd-alcohol's detail enumerated the two rules that override it, and
    # said in the same breath that the list was incomplete. That list is now
    # derived from the edges and must not be restated -- it is the
    # maintained-in-two-places failure tests/test_notes_split.py exists for.
    detail = _by_id()["ebrpd-alcohol"].detail
    assert "Two narrower rules override it" not in detail
    # What could NOT become an edge stays: Wee-Ta-Chi's ban is published for
    # one site and this table's narrowest scope is park, so it has nowhere to
    # go. That is a missing scope level, and saying so is the point.
    assert "nowhere to go" in detail
