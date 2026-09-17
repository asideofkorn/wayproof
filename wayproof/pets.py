"""Whether the named animal you are bringing may come to one campground.

Reads the booking listing's marker (``campgrounds.csv``) AND the pets rules in
force (``regulations.csv``) -- neither alone is safe. Round Valley Backpack
Camp is marked pets-allowed and its preserve bans dogs outright.

The species rules this encodes are pinned one test each in
``tests/test_pets.py``; read those names for the spec. It does not reach the
``stock`` category, so a horse answer from here is partial.
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
#: ``cat`` excludes "cat hole" -- see test_a_cat_hole_is_not_a_cat.
ANIMAL_PATTERNS = {
    DOG: r"\bdogs?\b",
    CAT: r"\bcats?\b(?!\s+holes?\b)",
    HORSE: r"\bhorses?\b",
}

#: A rule written about animals generally: "dog, cat or other animal".
#: Anchored on "animal" -- see test_other_locations_is_not_other_animals.
GENERAL_ANIMAL_PATTERN = r"\bor\s+other\s+(?:type\s+of\s+)?animals?\b|\bother\s+animals?\b"

PETS_CATEGORY = "pets"

#: Which animals a listing's own category word names. ``domestic`` maps to
#: nothing: no source defines it -- see test_domestic_names_no_species.
CATEGORY_ANIMALS = {
    PETS_HORSE: (HORSE,),
}


def _plural(animals) -> str:
    """``["dog", "dog", "cat"]`` -> ``"cats and dogs"``."""
    unique = sorted(set(animals))
    words = [f"{a}s" for a in unique]
    if len(words) <= 1:
        return "".join(words)
    return " and ".join([", ".join(words[:-1]), words[-1]])


def rule_animals(reg: Regulation) -> List[str]:
    """Which animals a rule's ``summary`` names. SUMMARY ONLY -- passing
    ``detail`` inverts ``ebrpd-pets-count``; see
    test_a_rules_species_come_from_its_summary_not_its_commentary."""
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
    """The ``pets`` rules from a set already resolved for this trip -- pass
    :func:`wayproof.regulations.regulations_in_force`, never the whole table."""
    return [r for r in regulations if r.category == PETS_CATEGORY]


def rules_for_campground(campground: Campground,
                         regulations: Sequence[Regulation]) -> List[Regulation]:
    """Every rule in force at one campground: a thin wrapper over
    :func:`wayproof.regulations.regulations_in_force` with the three scope keys
    a campground can supply. ``plan`` keeps its own call; it unions several."""
    return regulations_in_force(
        regulations,
        agency=[k.strip() for k in campground.agency_id.split(";") if k.strip()],
        jurisdiction=campground.jurisdiction,
        park=campground.park,
    )


def marker_animals(campground: Campground) -> List[str]:
    """Which animals the booking listing itself names. Usually none -- only
    ``horse`` names one."""
    named: List[str] = []
    for category in campground.pets_animal_list:
        for animal in CATEGORY_ANIMALS.get(category, ()):
            if animal not in named:
                named.append(animal)
    return named


@dataclass
class PetsAnswer:
    """What is known about bringing an animal to one campground.

    No single verdict field: at Round Valley the listing says pets and the park
    bans dogs, and a reader needs both."""

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
        """Pets rules scoped to this campground's OWN park -- a structural
        signal, no text analysis. Quoted in :meth:`lines` even where every rule
        prints below; see test_the_park_ban_survives_a_surface_that_suppresses_rule_quotes."""
        return [r for r in self.rules
                if r.scope_type == PARK and r.scope_value == self.campground.park]

    @property
    def silent(self) -> List[Regulation]:
        """Pets rules in force that say nothing about this animal. Carried, not
        filtered: a cat owner needs to know the leash count is not theirs."""
        return [r for r in self.rules if not rule_reaches(r, self.animal)]

    def lines(self, rule_detail: int = 3) -> List[str]:
        """The answer as a reader sees it: what the listing says, then the
        rules, then the gap -- which is never omitted.

        ``rule_detail`` quotes that many governing rules, most-specific-first.
        Pass ``0`` from a surface that prints them in full anyway, as ``plan``
        does; the park's own rule is quoted regardless."""
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

    *regulations* must already be scoped to this trip. *animal* is free text
    and deliberately unvalidated -- a rabbit is a real question. Blank asks the
    general one."""
    return PetsAnswer(campground=campground, animal=str(animal or "").strip().lower(),
                      rules=pets_rules(regulations))
