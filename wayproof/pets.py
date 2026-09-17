"""Whether the animal you are bringing may come.

That is not the same question as "does this campground allow pets", and this
project has the README bullet to prove it:

    **Can I bring a pet?** Wrong if it says "under control" where the forest
    requires a leash under six feet. Also wrong if it answers for a dog when
    the animal is not one: most pets rules in this dataset are written about
    dogs, because that is how the agencies write them, and a leash rule is not
    an answer to whether a cat, a rabbit or a bird may come. Say which animal
    the rule governs, or say there is no rule on file.

Answering it needs two things that live apart, and neither is sufficient:

- ``campgrounds.csv``'s ``pets_marker``/``pets_animals`` -- what the BOOKING
  LISTING says. It is per-campground and it is the only per-campground pets
  fact this project holds. It is also weak: eight rows say pets are allowed
  and name no animal, and one (Round Valley Backpack Camp) says pets are
  allowed at a camp whose park bans dogs outright.
- ``regulations.csv``'s ``pets`` rules -- what the LAND MANAGER says, scoped to
  an agency, a park or a wilderness. These carry the bans and the leash lengths
  and they are what actually governs you. They are also mostly written about
  dogs.

Read either alone and you get a confident wrong answer in a different
direction: the marker alone admits a dog to Round Valley, and the rules alone
never mention the campground you asked about. :func:`answer` reads both.

Three things about species, all of them learned from the data
-------------------------------------------------------------

**A rule's species come from its ``summary``, never its ``detail``.** The
summary is the rule as the agency states it; the detail is this project's
commentary, and the commentary talks about animals precisely in order to say
the rule does NOT cover them. ``ebrpd-pets-count`` is the trap in full: its
summary is "MAXIMUM THREE DOGS PER SITE" and its detail says "a party bringing
cats has no number here". Search the detail and you conclude the rule answers
for cats, which is the exact inversion of what it says.

**"or other animal" is a species-general rule, and it is the good news.**
EBRPD's Ordinance 38 is written as "dog, cat or other animal", so it reaches a
rabbit and a bird as well. A rule that names only dogs reaches only dogs, and
the honest answer for any other animal is that there is no rule on file --
which is a usable answer, and is the one this project prefers to a guess.

**A bare "cat" is not safe to match on.** ``regulations.py``'s own category
vocabulary already warns about it: "cat hole" is the waste category's term, and
matching it here would claim a human-waste rule as a cat rule. The pattern
excludes it.

What this deliberately does not do
----------------------------------

It does not reach the ``stock`` category. Three stock rules exist and a horse
is plainly stock as well as a listed pets category, so a horse answer from here
is partial and says so. Joining the two categories is a real piece of work
about pack animals, not a line of regex, and pretending otherwise would put a
confident answer where a stated limit belongs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .camping import (
    PETS_ALLOWED, PETS_ANIMAL_LABELS, PETS_HORSE, PETS_NOT_MARKED, Campground,
    pets_animals_label,
)
from .regulations import PARK, Regulation, regulations_in_force

DOG = "dog"
CAT = "cat"
HORSE = "horse"

#: How an agency writes each animal. Matched against a rule's ``summary`` only.
#:
#: ``cat`` excludes "cat hole", the waste category's own term -- the same
#: hazard ``regulations.CATEGORY_VOCABULARY`` documents, and for the same
#: reason: a human-waste rule read as a cat rule would answer the user's
#: question with someone else's.
ANIMAL_PATTERNS = {
    DOG: r"\bdogs?\b",
    CAT: r"\bcats?\b(?!\s+holes?\b)",
    HORSE: r"\bhorses?\b",
}

#: A rule written about animals generally rather than a named species.
#:
#: "dog, cat or other animal" is Ordinance 38's phrasing throughout, and it is
#: what lets this project answer for an animal nobody legislated about by name.
#: Anchored on "animal" so that "Other locations vary" -- which really is in
#: ``ebrpd-backpack-no-dogs-ohlone``'s summary -- does not read as one.
GENERAL_ANIMAL_PATTERN = r"\bor\s+other\s+(?:type\s+of\s+)?animals?\b|\bother\s+animals?\b"

PETS_CATEGORY = "pets"

#: Which animals a booking listing's own category word actually names.
#:
#: ``domestic`` maps to nothing, and that is the single most important entry in
#: this module. EBRPD prints "Pets Allowed: Domestic" and, on equestrian sites,
#: "Pets Allowed: Domestic, Horse"; no source read here defines the word. The
#: pairing rules out its being a superset of ``horse``, and says nothing at all
#: about a cat. Guessing that "domestic" means "dogs and cats" would answer
#: fifteen rows' worth of questions with an inference, which is how a
#: confident wrong answer gets into a dataset.
CATEGORY_ANIMALS = {
    PETS_HORSE: (HORSE,),
}


def _plural(animals) -> str:
    """``["dog", "dog", "cat"]`` -> ``"cats and dogs"``.

    Plural because a rule is about dogs, not about dog, and the singular read
    as a typo in every line this module emitted before it existed.
    """
    unique = sorted(set(animals))
    words = [f"{a}s" for a in unique]
    if len(words) <= 1:
        return "".join(words)
    return " and ".join([", ".join(words[:-1]), words[-1]])


def rule_animals(reg: Regulation) -> List[str]:
    """Which animals a rule's ``summary`` names, in :data:`ANIMAL_PATTERNS` order.

    Summary only -- see the module docstring. Passing ``detail`` in here makes
    ``ebrpd-pets-count`` answer for cats when its whole point is that it does
    not.
    """
    text = reg.summary or ""
    return [animal for animal, pattern in ANIMAL_PATTERNS.items()
            if re.search(pattern, text, re.I)]


def rule_is_species_general(reg: Regulation) -> bool:
    """Does this rule reach an animal it does not name -- "or other animal"?"""
    return bool(re.search(GENERAL_ANIMAL_PATTERN, reg.summary or "", re.I))


def rule_reaches(reg: Regulation, animal: str) -> bool:
    """Does this rule govern *animal*, by name or by "or other animal"?"""
    if not animal:
        return True
    return animal.lower() in rule_animals(reg) or rule_is_species_general(reg)


def pets_rules(regulations: Sequence[Regulation]) -> List[Regulation]:
    """The ``pets`` rules from a set already resolved for this trip.

    Takes rules IN FORCE, not the whole table: scope resolution belongs to
    :func:`wayproof.regulations.regulations_in_force`, which four surfaces
    already share, and re-deriving it here is how those surfaces drift apart.
    """
    return [r for r in regulations if r.category == PETS_CATEGORY]


def rules_for_campground(campground: Campground,
                         regulations: Sequence[Regulation]) -> List[Regulation]:
    """Every rule in force at one campground, scoped the shared way.

    A thin wrapper over :func:`wayproof.regulations.regulations_in_force` and
    deliberately nothing more -- the three scope keys a campground can supply
    are its agencies, its jurisdiction and its park, and a campground objective
    resolves no trailhead and no permit to add any others. ``plan`` keeps its
    own call because it unions several campgrounds at once; everything asking
    about one should come through here rather than rebuild the argument list.
    """
    return regulations_in_force(
        regulations,
        agency=[k.strip() for k in campground.agency_id.split(";") if k.strip()],
        jurisdiction=campground.jurisdiction,
        park=campground.park,
    )


def marker_animals(campground: Campground) -> List[str]:
    """Which animals the booking listing itself names. Usually none.

    Fifteen of the twenty-two marked rows say "Domestic", which names no
    species; eight say nothing but "allowed". Only ``horse`` names an animal.
    """
    named: List[str] = []
    for category in campground.pets_animal_list:
        for animal in CATEGORY_ANIMALS.get(category, ()):
            if animal not in named:
                named.append(animal)
    return named


@dataclass
class PetsAnswer:
    """What is known about bringing an animal to one campground.

    Four fields and not one verdict, deliberately. A single allowed/denied
    would have to pick a side on the case this exists for: Round Valley
    Backpack Camp, where the listing says pets and the park bans dogs. The
    answer there is that two sources say different things about different
    animals, and a reader needs both.
    """

    campground: Campground
    animal: str = ""
    """Lower-cased, as asked. "" means the general question was asked."""
    rules: List[Regulation] = field(default_factory=list)
    """Every pets rule in force here, whatever animal it is about."""

    @property
    def marker_names_animal(self) -> Optional[bool]:
        """Does the listing name this animal? ``None`` when no animal was asked."""
        if not self.animal:
            return None
        return self.animal in marker_animals(self.campground)

    @property
    def governing(self) -> List[Regulation]:
        """The rules that reach :attr:`animal`, by name or as "other animal"."""
        return [r for r in self.rules if rule_reaches(r, self.animal)]

    @property
    def park_rules(self) -> List[Regulation]:
        """Pets rules scoped to this campground's OWN park.

        A structural signal, not a reading of anybody's prose, and the one that
        keeps the marker honest. Round Valley Backpack Camp's listing marks it
        pets-allowed and its preserve bans dogs outright, so the marker and the
        rulebook disagree about the only thing a dog owner needs -- and the
        disagreement is visible here as a ``scope_type == "park"`` row matching
        ``campground.park``, with no text analysis and nothing inferred.

        Quoted in :meth:`lines` even by surfaces that print every rule further
        down. That is the same call ``plan`` already makes for the Whitney
        exclusion: a fact that is discovered on arrival and cannot be fixed
        there must not sit below a wall of regulations.
        """
        return [r for r in self.rules
                if r.scope_type == PARK and r.scope_value == self.campground.park]

    @property
    def silent(self) -> List[Regulation]:
        """Pets rules in force that say nothing about this animal.

        Carried rather than filtered away, because "four rules apply to you and
        two are about dogs" is a different state from "four rules apply to
        you", and a reader planning around a cat needs to know the leash count
        they can see on the page is not theirs.
        """
        return [r for r in self.rules if not rule_reaches(r, self.animal)]

    def lines(self, rule_detail: int = 3) -> List[str]:
        """The answer as a reader sees it.

        Order is fixed and is the point: what the listing says, then what the
        rules say, then what nobody says. The gap goes LAST and is never
        omitted -- silence reading as permission is the failure this whole
        module is built around.

        ``rule_detail`` is how many governing rules to quote when an animal was
        named. COUNTING THEM IS NOT ENOUGH, and Round Valley Backpack Camp is
        why: "seven pets rules govern you" is true of a dog there and hides
        that one of the seven bans dogs from the whole preserve. They are
        quoted most-specific-first, which is the order
        :func:`wayproof.regulations.regulations_for` already sorts them into,
        so a park's own ban reads before the District's leash rule.

        Pass ``0`` from a surface that prints the rules in full anyway -- as
        ``plan`` does, under "Rules in force" -- rather than saying it twice.
        """
        c = self.campground
        out: List[str] = []

        if c.pets_marker == PETS_ALLOWED:
            categories = pets_animals_label(c)
            if categories:
                out.append(f"Pets: the booking listing marks this camp pets-allowed, "
                           f"in its own categories -- {categories}.")
            else:
                out.append("Pets: the booking listing marks this camp pets-allowed "
                           "and gives no category, so it does not say which animals.")
        elif c.pets_marker == PETS_NOT_MARKED:
            out.append("Pets: the listing carries a pets field and this camp is not "
                       "marked in it. THAT IS NOT A STATED BAN -- it is the absence "
                       "of a statement, and worth a call to the operator.")
        else:
            out.append("Pets: no source carrying a pets field has been read for this "
                       "campground. Nobody has checked; that is not the same as no.")

        park_rules = self.park_rules
        if park_rules and not self.animal:
            out.append(f"  {c.park} HAS ITS OWN PETS RULE, over and above the "
                       f"agency's, and the listing's marker does not reflect it:")
            out.extend(f"    - {r.summary}" for r in park_rules)

        if not self.animal:
            if self.rules:
                named = _plural([a for r in self.rules for a in rule_animals(r)])
                general = [r for r in self.rules if rule_is_species_general(r)]
                which = f"are written about {named}" if named else "name no animal"
                tail = (f", and {len(general)} of them reach any animal at all "
                        f"('or other animal')" if general else
                        " and nothing else")
                out.append(f"  {len(self.rules)} pets rule(s) in force here "
                           f"{which}{tail}. A rule about another animal is not an "
                           f"answer about yours.")
            else:
                out.append("  No pets rule is on file for this land at all, which is "
                           "a gap and not a permission.")
            return out

        animal = self.animal
        if self.marker_names_animal:
            out.append(f"  {animal.upper()}: the listing names one itself.")
        elif c.pets_marker == PETS_ALLOWED:
            categories = pets_animals_label(c) or "nothing at all"
            out.append(f"  {animal.upper()}: the marker names {categories}, which is "
                       f"the operator's own vocabulary and is defined by no source "
                       f"read here. It does not answer for a {animal}; the rules "
                       f"below are what does.")

        park_reaching = [r for r in park_rules if rule_reaches(r, animal)]
        if park_reaching:
            out.append(f"  {c.park} HAS ITS OWN PETS RULE and it reaches a "
                       f"{animal}. It is not in the marker:")
            out.extend(f"    - {r.summary}" for r in park_reaching)

        governing, silent = self.governing, self.silent
        if governing:
            by_name = [r for r in governing if animal in rule_animals(r)]
            general = [r for r in governing if r not in by_name]
            bits = []
            if by_name:
                bits.append(f"{len(by_name)} name a {animal}")
            if general:
                bits.append(f"{len(general)} reach one as 'or other animal'")
            out.append(f"  {len(self.rules)} pets rule(s) apply to this land; "
                       f"{' and '.join(bits)}. Those govern you:")
            for reg in governing[:rule_detail] if rule_detail else ():
                out.append(f"    - {reg.summary}")
            hidden = len(governing) - rule_detail
            if rule_detail and hidden > 0:
                out.append(f"    - and {hidden} more; all of them are published "
                           f"under the rules in force for this land.")
        else:
            out.append(f"  NO RULE ON FILE GOVERNS A {animal.upper()} HERE. "
                       f"{len(self.rules)} pets rule(s) apply to this land and every "
                       f"one is written about another animal, so nothing here says "
                       f"yes and nothing says no.")
        if silent:
            about = _plural([a for r in silent for a in rule_animals(r)])
            out.append(f"  {len(silent)} more pets rule(s) apply here and are written "
                       f"about {about or 'other animals'} alone -- including any leash "
                       f"length or head count you can see on the page. Those are not "
                       f"an answer about a {animal}.")
        return out


def answer(campground: Campground, regulations: Sequence[Regulation] = (),
           animal: str = "") -> PetsAnswer:
    """What is known about bringing *animal* to *campground*.

    *regulations* must already be scoped to this trip -- pass the output of
    :func:`wayproof.regulations.regulations_in_force`, which is what ``plan``,
    the site views, the reports and the scorecard all use. Passing the whole
    table would answer with Desolation's dog rules at an East Bay campground.

    *animal* is free text and is not validated against a species list: someone
    arriving with a rabbit is asking a real question, and the honest answer --
    no rule on file names a rabbit, and these rules reach any animal -- is one
    this can give. Blank asks the general question instead.
    """
    return PetsAnswer(campground=campground, animal=str(animal or "").strip().lower(),
                      rules=pets_rules(regulations))
