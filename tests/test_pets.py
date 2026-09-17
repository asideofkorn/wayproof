"""Tests for the pets columns and the species question they exist to answer.

The README's Q13 carries two falsification criteria, and the second one is
unusual in this project because it is about the ANSWERER rather than the data:

    **Can I bring a pet?** Wrong if it says "under control" where the forest
    requires a leash under six feet. Also wrong if it answers for a dog when
    the animal is not one [...] Say which animal the rule governs, or say there
    is no rule on file.

So these tests are mostly about not answering. Four failures are pinned, each
one something the code would do if written the obvious way:

- **Reading a rule's commentary as the rule.** ``ebrpd-pets-count`` says
  "MAXIMUM THREE DOGS PER SITE" and its ``detail`` explains that a party
  bringing cats has no number. Search the detail and the rule answers for cats,
  which is the inverse of what it says.
  :func:`test_a_rules_species_come_from_its_summary_not_its_commentary`.
- **Reading a marker as a rulebook.** Round Valley Backpack Camp's listing
  marks it pets-allowed; its preserve bans dogs outright.
  :func:`test_round_valley_does_not_read_as_permission_for_a_dog`.
- **Reading silence as no.** ``--animal cat`` must exclude nothing, and an
  unmarked listing is not a ban.
  :func:`test_the_animal_question_filters_nothing`,
  :func:`test_an_unmarked_listing_never_renders_as_a_ban`.
- **Letting the prose grow back.** The fields these columns replaced said the
  same thing twenty-two ways. :func:`test_notes_no_longer_restates_the_pets_columns`
  is the guard that would catch it refilling, in the pattern
  ``tests/test_notes_split.py`` established for permits.

Run with:  python -m pytest tests/test_pets.py
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof import pets
from wayproof.camping import (
    PETS_ALLOWED, PETS_NOT_MARKED, Campground, load_campgrounds,
    pets_marked, pets_marked_without_animals, pets_not_marked, pets_unrecorded,
)
from wayproof.regulations import Regulation, load_regulations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPGROUNDS = os.path.join(ROOT, "data", "campgrounds.csv")
REGS = os.path.join(ROOT, "data", "regulations.csv")


def _campgrounds():
    return load_campgrounds(CAMPGROUNDS)


def _by_name():
    return {c.name: c for c in _campgrounds()}


def _answer(name, animal=""):
    c = _by_name()[name]
    return pets.answer(c, pets.rules_for_campground(c, load_regulations(REGS)), animal)


def _text(answer, **kw):
    return " ".join(answer.lines(**kw))


# -- the column loads, and refuses what it cannot mean --------------------

def _row(**kw):
    base = {"name": "Test Camp", "park": "Test Park"}
    base.update(kw)
    return base


def _write(tmp_path, rows):
    import csv
    path = tmp_path / "campgrounds.csv"
    fields = ["name", "park", "pets_marker", "pets_animals"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    return path


def test_an_unknown_marker_is_refused(tmp_path):
    path = _write(tmp_path, [_row(pets_marker="prohibited")])
    with pytest.raises(ValueError) as e:
        load_campgrounds(path)
    # The message has to say where a ban belongs, or the next person adds the
    # value instead of the rule.
    assert "regulations.csv" in str(e.value)


def test_an_unknown_category_word_is_refused(tmp_path):
    # The failure this prevents: a new operator's word ("Service Animal",
    # "Livestock") passing silently into a species answer as if it named
    # nothing, which is indistinguishable from "Domestic" and is not the same.
    path = _write(tmp_path, [_row(pets_marker="allowed", pets_animals="domestic;fowl")])
    with pytest.raises(ValueError) as e:
        load_campgrounds(path)
    assert "fowl" in str(e.value)


def test_a_category_without_a_marker_is_refused(tmp_path):
    path = _write(tmp_path, [_row(pets_animals="horse")])
    with pytest.raises(ValueError):
        load_campgrounds(path)


def test_blank_stays_blank(tmp_path):
    (c,) = load_campgrounds(_write(tmp_path, [_row()]))
    assert c.pets_marker == ""
    assert c.pets_animal_list == []


# -- which animal a rule is about -----------------------------------------

def _reg(summary, **kw):
    kw.setdefault("regulation_id", "test")
    kw.setdefault("scope_type", "agency")
    kw.setdefault("scope_value", "test")
    kw.setdefault("category", "pets")
    return Regulation(summary=summary, **kw)


def test_a_rules_species_come_from_its_summary_not_its_commentary():
    # THE TRAP, from real data. ebrpd-pets-count's summary is a dog rule; its
    # detail mentions cats precisely in order to say the rule does not reach
    # them. A species check that reads `detail` inverts the rule.
    count = next(r for r in load_regulations(REGS)
                 if r.regulation_id == "ebrpd-pets-count")
    assert "cat" in count.detail.lower(), "fixture moved; this test needs the trap"
    assert pets.rule_animals(count) == [pets.DOG]
    assert not pets.rule_reaches(count, pets.CAT)


def test_a_cat_hole_is_not_a_cat():
    # regulations.py's own category vocabulary documents this hazard for the
    # waste category; the same word would claim a human-waste rule as a cat
    # rule here.
    assert pets.rule_animals(_reg("Bury waste in a cat hole 200 ft from water.")) == []


def test_other_locations_is_not_other_animals():
    # Real text: ebrpd-backpack-no-dogs-ohlone's summary ends "Other locations
    # vary and must be checked per site." A loose "other" match would make a
    # dog-only ban reach every animal.
    ohlone = next(r for r in load_regulations(REGS)
                  if r.regulation_id == "ebrpd-backpack-no-dogs-ohlone")
    assert "other locations" in ohlone.summary.lower()
    assert not pets.rule_is_species_general(ohlone)
    assert not pets.rule_reaches(ohlone, pets.CAT)


def test_or_other_animal_reaches_an_animal_nobody_legislated_about():
    ordinance = _reg("No dog, cat or other animal may be left unattended.")
    assert pets.rule_is_species_general(ordinance)
    assert pets.rule_reaches(ordinance, "rabbit")


def test_a_dog_rule_does_not_answer_for_a_cat():
    assert not pets.rule_reaches(_reg("Dogs must be leashed."), pets.CAT)


# -- the marker names what it names, and nothing more ---------------------

def test_domestic_names_no_species():
    # The single inference this module refuses to make. EBRPD prints
    # "Domestic" and defines it nowhere; guessing it means dogs-and-cats would
    # answer fifteen rows' worth of questions from a hunch.
    c = Campground(name="X", park="Y", pets_marker=PETS_ALLOWED,
                   pets_animals="domestic")
    assert pets.marker_animals(c) == []


def test_horse_names_a_horse():
    c = Campground(name="X", park="Y", pets_marker=PETS_ALLOWED,
                   pets_animals="domestic;horse")
    assert pets.marker_animals(c) == [pets.HORSE]
    assert pets.answer(c, [], "horse").marker_names_animal is True
    assert pets.answer(c, [], "cat").marker_names_animal is False


# -- the case the whole design exists for ---------------------------------

def test_round_valley_does_not_read_as_permission_for_a_dog():
    # The listing marks this camp pets-allowed. Its preserve bans dogs
    # outright, for the San Joaquin kit fox. A surface that shows the marker
    # and not the ban sends a dog to the one camp here it must not go to.
    answer = _answer("Round Valley Backpack Camp", "dog")
    assert answer.campground.pets_marker == PETS_ALLOWED
    ban = "No dogs are allowed anywhere in Round Valley Regional Preserve"
    assert any(ban in r.summary for r in answer.park_rules)
    assert ban in _text(answer)


def test_the_park_ban_is_named_even_when_no_animal_was_asked_about():
    # `plan` does not know which animal you are bringing. It must still not
    # print "pets-allowed" over a park-wide ban.
    assert "No dogs are allowed anywhere" in _text(_answer("Round Valley Backpack Camp"))


def test_the_park_ban_survives_a_surface_that_suppresses_rule_quotes():
    # plan passes rule_detail=0 because it prints every rule further down. The
    # park's own rule is the exception, for the same reason plan prints the
    # Whitney exclusion above "Rules in force" rather than inside it.
    text = _text(_answer("Round Valley Backpack Camp", "dog"), rule_detail=0)
    assert "No dogs are allowed anywhere" in text


def test_a_park_with_no_pets_rule_of_its_own_says_nothing_about_one():
    assert _answer("Anthony Chabot Campground", "dog").park_rules == []


# -- answering for a cat, which is where this started ---------------------

def test_a_cat_at_a_marked_campground_gets_the_rules_that_name_a_cat():
    answer = _answer("Anthony Chabot Campground", "cat")
    assert answer.marker_names_animal is False
    governing = {r.regulation_id for r in answer.governing}
    assert "ebrpd-pets-campground" in governing, "Ordinance 38 names cats directly"
    silent = {r.regulation_id for r in answer.silent}
    assert "ebrpd-pets-count" in silent, "the three-per-site cap is a dog rule"
    text = _text(answer)
    assert "dogs, cats or other animals must be attended" in text
    # And it must say the dog-only rules are not an answer, rather than
    # quietly dropping them.
    assert "are not an answer about a cat" in text


def test_the_marker_never_answers_for_an_animal_it_does_not_name():
    for name in ("Anthony Chabot Campground", "Corral Group Camp"):
        text = _text(_answer(name, "cat"))
        assert "does not answer for a cat" in text


def test_an_animal_nobody_wrote_a_rule_about_still_gets_an_answer():
    answer = _answer("Anthony Chabot Campground", "rabbit")
    assert answer.governing, "Ordinance 38's 'or other animal' reaches a rabbit"
    assert "or other animal" in _text(answer)


def test_no_rule_on_file_is_said_plainly_when_that_is_the_answer():
    # The README's own instruction: "say there is no rule on file". Built from
    # a dog-only rule set so the sentence is reachable.
    c = Campground(name="X", park="Y", pets_marker=PETS_ALLOWED)
    text = _text(pets.answer(c, [_reg("Dogs must be leashed.")], "cat"))
    assert "NO RULE ON FILE GOVERNS A CAT HERE" in text


def test_no_pets_rule_at_all_is_a_gap_and_not_a_permission():
    c = Campground(name="X", park="Y", pets_marker=PETS_ALLOWED)
    assert "gap and not a permission" in _text(pets.answer(c, []))


# -- silence never renders as no ------------------------------------------

def test_an_unmarked_listing_never_renders_as_a_ban():
    text = _text(_answer("Star Mine Group Camp", "cat"))
    assert "NOT A STATED BAN" in text
    assert "not allowed" not in text.lower()


def test_an_unread_listing_says_nobody_checked():
    assert "Nobody has checked" in _text(_answer("Del Valle Family Campground", "cat"))


def test_the_three_states_are_three_different_sentences():
    # Collapsing any two of them is the Q17 failure ("closed and never-existed
    # look the same") wearing a different hat.
    said = {_answer(n).lines()[0] for n in ("Anthony Chabot Campground",
                                            "Star Mine Group Camp",
                                            "Del Valle Family Campground")}
    assert len(said) == 3


# -- the query -------------------------------------------------------------

def test_the_filter_excludes_both_kinds_of_silence():
    campgrounds = _campgrounds()
    marked = pets_marked(campgrounds)
    assert marked, "fixture has no marked campgrounds"
    assert all(c.pets_marker == PETS_ALLOWED for c in marked)
    names = lambda cs: {c.name for c in cs}  # noqa: E731
    assert not names(marked) & names(pets_not_marked(campgrounds))
    assert not names(marked) & names(pets_unrecorded(campgrounds))
    # And the three partitions cover the table, so nothing can be dropped
    # silently by adding a fourth state later.
    assert (len(marked) + len(pets_not_marked(campgrounds))
            + len(pets_unrecorded(campgrounds))) == len(campgrounds)


def test_the_animal_question_filters_nothing():
    from wayproof.discovery import find_campgrounds
    campgrounds = _campgrounds()
    without = find_campgrounds(campgrounds)
    with_cat = find_campgrounds(campgrounds, animal="cat")
    assert len(with_cat.matches) == len(without.matches)
    assert with_cat.animal == "cat"


def test_the_list_says_the_animal_was_not_a_filter():
    from wayproof.discovery import find_campgrounds, format_campground_list
    search = find_campgrounds(_campgrounds(), pets=PETS_ALLOWED, animal="cat")
    text = "\n".join(format_campground_list(search, regulations=load_regulations(REGS)))
    assert "THAT IS NOT A FILTER" in text


def test_the_list_reports_both_kinds_of_excluded_silence():
    from wayproof.discovery import find_campgrounds, format_campground_list
    campgrounds = _campgrounds()
    search = find_campgrounds(campgrounds, pets=PETS_ALLOWED)
    text = "\n".join(format_campground_list(
        search, regulations=load_regulations(REGS),
        unmarked_pets=pets_not_marked(campgrounds),
        unrecorded_pets=pets_unrecorded(campgrounds)))
    assert "PETS FIELD READ AND EMPTY" in text
    assert "NO PETS FIELD READ" in text
    assert "Star Mine Group Camp" in text
    assert "Del Valle Family Campground" in text


def test_a_search_that_did_not_ask_about_pets_does_not_answer_about_them():
    # Four lines per campground on a search about access is how a reader learns
    # to skip them, and the Round Valley line is the one they would skip.
    from wayproof.discovery import find_campgrounds, format_campground_list
    search = find_campgrounds(_campgrounds(), access="drive_in")
    text = "\n".join(format_campground_list(search, regulations=load_regulations(REGS)))
    assert "Pets:" not in text


# -- the data itself -------------------------------------------------------

def test_every_marked_row_is_marked_by_a_source_the_row_names():
    # A pets marker comes off the row's own listing, so a row asserting one
    # without a source URL is asserting it from nowhere.
    missing = [c.name for c in pets_marked(_campgrounds()) if not c.source_url]
    assert missing == [], f"pets marker with no source: {missing}"


def test_the_ohlone_corridor_names_one_animal_and_it_is_a_horse():
    # The most informative pets value in the table, and the reason `horse` is
    # worth a vocabulary entry: ten corridor sites were read at site level and
    # only Doe's name an animal, corroborating a no-dogs rule this project
    # otherwise held on the booking platform's word alone.
    by_name = _by_name()
    assert by_name["Doe Camp"].pets_animal_list == ["horse"]
    for name in ("Boyd Camp", "Stewart's Camp", "Maggie's Half Acre",
                 "Sunol Backpack Camp"):
        assert by_name[name].pets_marker == PETS_NOT_MARKED


def test_the_marked_but_unspecified_rows_are_reported_as_a_gap():
    from wayproof.reports import open_questions
    unspecified = pets_marked_without_animals(_campgrounds())
    assert unspecified, "fixture has no marked-without-species rows"
    questions = open_questions(campgrounds=_campgrounds(),
                               regulations=load_regulations(REGS))
    text = " ".join(q.question for q in questions)
    assert "names no category of animal" in text


def test_campgrounds_with_no_pets_source_are_reported_as_a_gap():
    from wayproof.reports import open_questions
    questions = open_questions(campgrounds=_campgrounds(),
                               regulations=load_regulations(REGS))
    text = " ".join(q.question for q in questions)
    assert "No source carrying a pets field has been read" in text
    assert "Del Valle Family Campground" in text


# -- and the prose does not grow back --------------------------------------

def test_notes_no_longer_restates_the_pets_columns():
    # The guard `tests/test_notes_split.py` established for permits, applied to
    # the field these columns came out of. Twenty-two rows said "Pets Allowed:
    # Domestic" or "Pets are allowed here" in prose; a row saying it again is a
    # fact maintained in two places, which is how the campfire rule drifted
    # into seven copies.
    import re
    pattern = re.compile(r"pets?\s+(are\s+)?allowed", re.I)
    offenders = [c.name for c in _campgrounds() if pattern.search(c.notes)]
    assert offenders == [], f"pets marker restated in notes: {offenders}"


def test_notes_no_longer_restates_a_resolved_pets_rule():
    # Anthony Chabot's notes carried Ordinance 38's leash, count, confinement
    # and unattended rules in prose while all four existed as regulations,
    # created from the same sources. This is what would have caught it.
    import re
    pattern = re.compile(r"\b801\.\d|leashed?\b|during quiet hours", re.I)
    offenders = [c.name for c in _campgrounds() if pattern.search(c.notes)]
    assert offenders == [], f"pets rules restated in campground notes: {offenders}"


def test_what_the_columns_cannot_hold_is_still_in_notes():
    # The other half of a split: deleting prose is only safe if the fact is
    # resolvable afterwards. These four are not column-shaped and had to stay.
    by_name = _by_name()
    assert "Reservations" in by_name["Star Mine Group Camp"].notes
    assert "round-valley-no-dogs" in by_name["Round Valley Backpack Camp"].notes
    assert "horse camp" in by_name["Doe Camp"].notes.lower()
