"""Tests for wayproof.topic: one topic resolved at one place.

Built by generalising `pets.py` and proving it on a second topic before
committing to the abstraction. Fire was the right second case: it shares the
shape (a place, subjects a rule names, a park rule that displaces a District
one) and it broke the model in a way pets never would have -- see
:func:`test_naming_a_subject_is_not_the_same_as_permitting_it`.

Run with:  python -m pytest tests/test_topic.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof import topic
from wayproof.camping import load_campgrounds
from wayproof.regulations import Regulation, load_regulations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGS = os.path.join(ROOT, "data", "regulations.csv")
CAMPGROUNDS = os.path.join(ROOT, "data", "campgrounds.csv")


def _regs():
    return load_regulations(REGS)


def _camp(name):
    return next(c for c in load_campgrounds(CAMPGROUNDS) if c.name == name)


def _answer(camp_name, topic_def, subject=""):
    c = _camp(camp_name)
    in_force = topic.rules_for_place(_regs(), c.agency_id, c.jurisdiction, c.park)
    return topic.answer(c.name, c.park, topic_def, in_force, subject)


def _reg(summary, category="fire", scope_type="agency", scope_value="ebrpd", **kw):
    return Regulation(regulation_id=kw.pop("rid", "test"), scope_type=scope_type,
                      scope_value=scope_value, category=category, summary=summary, **kw)


# -- what the second topic proved, and what it broke ------------------------

def test_naming_a_subject_is_not_the_same_as_permitting_it():
    # THE LIMIT THIS EXERCISE FOUND, pinned so nobody builds on top of it
    # believing otherwise. Black Diamond's rule bans campfires and permits camp
    # stoves IN ONE SENTENCE. The model records which subjects a rule names,
    # not what it says about them, so both resolve to the same rules and the
    # answer cannot say that one is banned and the other fine.
    banned = _answer("Stewartville Backpack Camp", topic.FIRE, "campfire")
    fine = _answer("Stewartville Backpack Camp", topic.FIRE, "camp stove")
    assert [r.regulation_id for r in banned.deciding()] == \
           [r.regulation_id for r in fine.deciding()]
    rule = next(r for r in banned.rules if r.regulation_id == "black-diamond-no-fire")
    assert {"campfire", "camp stove"} <= set(topic.subjects_named(topic.FIRE, rule))


def test_barbecue_is_one_subject_because_the_text_cannot_split_it():
    # Charcoal and gas ARE distinguished by the rules -- the backpack rule bans
    # charcoal, Ordinance 38 permits propane -- but both wordings contain
    # "barbecue", so a regex cannot cut it. Two subjects would have been a
    # distinction the matcher could not make.
    assert "barbecue" in topic.FIRE.subjects
    assert not any(s.endswith(" barbecue") for s in topic.FIRE.subjects)


def test_fire_has_no_general_wording_and_says_so():
    # Pets has "or other animal", which reaches a rabbit. Fire has nothing of
    # the kind, and inventing one would let "no fires of ANY type" answer for a
    # lantern, which Mokelumne explicitly permits.
    assert topic.FIRE.general == ""
    assert not topic.is_general(topic.FIRE, _reg("No open fires or barbecues of ANY type."))


def test_a_topic_without_a_marker_answers_from_rules_alone():
    # Fire has no per-place marker: the amenity flags are still prose. An
    # answer without one must not pretend there was a listing.
    a = _answer("Anthony Chabot Campground", topic.FIRE, "campfire")
    assert a.marker is None
    assert not any(line.startswith("Fire:") for line in a.lines())


# -- the parts that did generalise ------------------------------------------

def test_a_rules_subjects_come_from_its_summary_not_its_commentary():
    reg = next(r for r in _regs() if r.regulation_id == "ebrpd-pets-count")
    assert "cat" in reg.detail.lower(), "fixture moved; this test needs the trap"
    assert topic.subjects_named(topic.PETS, reg) == ["dog"]


def test_a_cat_hole_is_not_a_cat():
    reg = _reg("Bury waste in a cat hole 200 ft from water.", category="waste")
    assert topic.subjects_named(topic.PETS, reg) == []


def test_or_other_animal_reaches_a_subject_it_does_not_name():
    reg = _reg("No dog, cat or other animal may be left unattended.", category="pets")
    assert topic.reaches(topic.PETS, reg, "rabbit")


def test_a_park_rule_is_found_structurally_for_either_topic():
    # scope_type == park matching the place's park. No text analysis, and it
    # works the same for a dog ban and a fire ban.
    dogs = _answer("Round Valley Backpack Camp", topic.PETS, "dog")
    fires = _answer("Stewartville Backpack Camp", topic.FIRE, "campfire")
    assert any("No dogs are allowed anywhere" in r.summary for r in dogs.park_rules)
    assert any("Black Diamond" in r.summary for r in fires.park_rules)


def test_a_displaced_rule_is_not_offered_as_deciding():
    # Ordinance 38's fire rule is displaced at Black Diamond by the park's own.
    a = _answer("Stewartville Backpack Camp", topic.FIRE, "campfire")
    assert "ebrpd-fire" in a.displaced
    assert "ebrpd-fire" not in [r.regulation_id for r in a.deciding()]


def test_the_deciding_rules_read_most_specific_first():
    a = _answer("Stewartville Backpack Camp", topic.FIRE, "campfire")
    assert a.deciding()[0].scope_type == "park"


def test_what_is_silent_is_carried_not_filtered_away():
    a = _answer("Anthony Chabot Campground", topic.PETS, "cat")
    assert any(r.regulation_id == "ebrpd-pets-count" for r in a.silent)
    assert "not an answer about cat" in " ".join(a.lines())


def test_no_rule_on_file_is_said_plainly():
    a = topic.Answer(place="X", park="Y", topic=topic.PETS, subject="cat",
                     rules=[_reg("Dogs must be leashed.", category="pets")])
    assert "NO RULE ON FILE GOVERNS CAT HERE" in " ".join(a.lines())


def test_no_rules_at_all_is_a_gap_not_a_permission():
    a = topic.Answer(place="X", park="Y", topic=topic.FIRE, subject="campfire")
    assert "gap and not a permission" in " ".join(a.lines())


def test_the_whole_table_is_not_a_place_to_ask_from():
    # rules_for_place scopes; passing every rule would answer with Desolation's
    # campfire ban at an East Bay campground.
    c = _camp("Anthony Chabot Campground")
    scoped = topic.rules_for_place(_regs(), c.agency_id, c.jurisdiction, c.park)
    ids = {r.regulation_id for r in scoped}
    assert "desolation-campfire-ban" not in ids
    assert "ebrpd-fire" in ids
