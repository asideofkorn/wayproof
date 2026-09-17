"""Resolving one topic at one place: which rules govern, and which decided.

Nobody asks whether dogs are allowed at the district level, the park level or
the site level. They ask whether their dog may come to this campsite. The
levels are how that gets answered, and which level decided is part of the
answer.

This holds the part that is the same whatever the topic -- scoping to a place,
reading which subjects a rule names, splitting what governs you from what is
about something else. The sentences a reader sees stay with the topic, because
a pets answer talks about animals and a fire answer about what you may burn.

Rules are pinned one test each in ``tests/test_topic.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Mapping, Optional, Sequence

from .regulations import (
    PARK, Regulation, SPECIFICITY, regulations_in_force, supersessions,
)


@dataclass(frozen=True)
class Topic:
    """One question a place can be asked, and the subjects it distinguishes."""

    category: str
    """The ``regulations.csv`` category this reads."""
    label: str
    subjects: Mapping[str, str]
    """``subject -> regex``, matched against a rule's SUMMARY only. Never its
    ``detail``: see test_a_rules_subjects_come_from_its_summary_not_its_commentary."""
    general: str = ""
    """Regex for wording that reaches a subject the rule does not name --
    "or other animal". Blank when the topic has no such wording."""
    general_phrase: str = ""
    """How to quote that wording to a reader."""


PETS = Topic(
    category="pets",
    label="Pets",
    subjects={
        # "cat" excludes "cat hole", the waste category's term.
        "dog": r"\bdogs?\b",
        "cat": r"\bcats?\b(?!\s+holes?\b)",
        "horse": r"\bhorses?\b",
    },
    general=r"\bor\s+other\s+(?:type\s+of\s+)?animals?\b|\bother\s+animals?\b",
    general_phrase="or other animal",
)

FIRE = Topic(
    category="fire",
    label="Fire",
    subjects={
        # "open fire" is a campfire by another name: Sunol bans "open fires",
        # Black Diamond bans "campfires", and they mean the same thing to
        # someone holding a match.
        "campfire": r"\bcamp\s?fires?\b|\bopen\s+(?:outdoor\s+)?fires?\b",
        # ONE barbecue subject, not charcoal and gas. The rules do distinguish
        # them -- the backpack rule bans charcoal and Ordinance 38 permits
        # propane -- but both wordings contain "barbecue", so a regex cannot
        # cut it. Splitting them here modelled a distinction the matcher could
        # not make: see test_barbecue_is_one_subject_because_the_text_cannot_split_it.
        "barbecue": r"\bbarbecues?\b|\bBBQ\b|\bhibachis?\b|\bcharcoal\b",
        "camp stove": r"\bcamp\s?stoves?\b|\bstoves?\b",
        "lantern": r"\blanterns?\b",
    },
    # Fire rules name what they govern. Nothing here reaches an unnamed thing,
    # and inventing a catch-all would let "no fires of ANY type" answer for a
    # lantern, which Mokelumne explicitly permits.
    general="",
)

TOPICS = {t.category: t for t in (PETS, FIRE)}


def subjects_named(topic: Topic, reg: Regulation) -> List[str]:
    """Which of the topic's subjects a rule's ``summary`` names.

    SUMMARY ONLY. ``ebrpd-pets-count``'s summary is a dog rule and its detail
    says a party bringing cats has no number here; reading detail inverts it.
    """
    text = reg.summary or ""
    return [s for s, pattern in topic.subjects.items()
            if re.search(pattern, text, re.I)]


def is_general(topic: Topic, reg: Regulation) -> bool:
    """Does this rule reach a subject it does not name?"""
    if not topic.general:
        return False
    return bool(re.search(topic.general, reg.summary or "", re.I))


def reaches(topic: Topic, reg: Regulation, subject: str) -> bool:
    """Does this rule govern *subject*, by name or by the topic's general wording?"""
    if not subject:
        return True
    return subject.lower() in subjects_named(topic, reg) or is_general(topic, reg)


def rules_for_place(regulations: Sequence[Regulation], agency_id: str = "",
                    jurisdiction: str = "", park: str = "") -> List[Regulation]:
    """Every rule in force at a place, scoped the way every other surface scopes.

    A thin wrapper over :func:`wayproof.regulations.regulations_in_force` with
    the three keys a place can supply.
    """
    return regulations_in_force(
        regulations,
        agency=[k.strip() for k in agency_id.split(";") if k.strip()],
        jurisdiction=jurisdiction,
        park=park,
    )


@dataclass
class Marker:
    """What a place's own listing said about this topic, where one exists.

    ``states`` is the sentence a reader sees; ``names`` is which subjects it
    actually names, usually none. Fire has no marker at all -- the amenity
    flags are still prose -- and an answer without one is rules-only.
    """

    states: str
    names: Sequence[str] = ()


@dataclass
class Answer:
    """What is known about *subject* at one place, and which level decided."""

    place: str
    park: str
    topic: Topic
    subject: str = ""
    rules: List[Regulation] = field(default_factory=list)
    marker: Optional[Marker] = None

    @property
    def governing(self) -> List[Regulation]:
        """The rules that reach :attr:`subject`."""
        return [r for r in self.rules if reaches(self.topic, r, self.subject)]

    @property
    def silent(self) -> List[Regulation]:
        """In force here, and about something else.

        Carried rather than filtered: "four rules apply and two are about dogs"
        is a different state from "four rules apply", and a cat owner needs to
        know the leash count on the page is not theirs.
        """
        return [r for r in self.rules if not reaches(self.topic, r, self.subject)]

    @property
    def park_rules(self) -> List[Regulation]:
        """Rules scoped to this place's OWN park -- a structural signal, no text
        analysis. Round Valley's listing says pets and its preserve bans dogs."""
        return [r for r in self.rules
                if r.scope_type == PARK and r.scope_value == self.park]

    @property
    def displaced(self) -> dict:
        """``{regulation_id: [rules displacing it]}`` among the rules in force."""
        return supersessions(self.rules)

    def deciding(self) -> List[Regulation]:
        """The rules that answer for :attr:`subject`, most specific first, with
        displaced ones dropped -- they do not apply here."""
        out = [r for r in self.governing if r.regulation_id not in self.displaced]
        return sorted(out, key=lambda r: SPECIFICITY.get(r.scope_type, 4))

    def lines(self, rule_detail: int = 3) -> List[str]:
        """The answer as a reader sees it: the marker, the rules that decided,
        then what is silent. The gap goes last and is never omitted."""
        out: List[str] = []
        if self.marker is not None:
            out.append(f"{self.topic.label}: {self.marker.states}")
        subject = self.subject or "this"

        park_here = [r for r in self.park_rules if reaches(self.topic, r, self.subject)]
        if park_here:
            out.append(f"  {self.park} has its own rule, and it reaches "
                       f"{'a ' + subject if self.subject else 'this'}:")
            out.extend(f"    - {r.summary}" for r in park_here)

        deciding = self.deciding()
        if deciding:
            by_name = [r for r in deciding if self.subject.lower()
                       in subjects_named(self.topic, r)]
            general = [r for r in deciding if r not in by_name]
            bits = []
            if by_name:
                bits.append(f"{len(by_name)} name{'s' if len(by_name) == 1 else ''} it")
            if general and self.topic.general_phrase:
                bits.append(f"{len(general)} reach it as "
                            f"'{self.topic.general_phrase}'")
            tail = f"; {' and '.join(bits)}" if bits else ""
            # No dangling "Those govern you:" when the caller suppresses the
            # quotes -- plan prints every rule further down, and a colon
            # introducing nothing reads as a bug.
            lead = "Those govern you:" if rule_detail else "See the rules in force below."
            out.append(f"  {len(self.rules)} {self.topic.label.lower()} rule(s) apply "
                       f"to this land{tail}. {lead}")
            for r in deciding[:rule_detail] if rule_detail else ():
                out.append(f"    - {r.summary}")
            hidden = len(deciding) - rule_detail
            if rule_detail and hidden > 0:
                out.append(f"    - and {hidden} more, published with the rules "
                           f"in force for this land.")
        elif self.rules:
            out.append(f"  NO RULE ON FILE GOVERNS {subject.upper()} HERE. "
                       f"{len(self.rules)} {self.topic.label.lower()} rule(s) apply "
                       f"and every one is about something else, so nothing here "
                       f"says yes and nothing says no.")
        else:
            out.append(f"  No {self.topic.label.lower()} rule is on file for this "
                       f"land at all, which is a gap and not a permission.")

        if self.subject and self.silent:
            about = sorted({s for r in self.silent for s in subjects_named(self.topic, r)})
            named = ", ".join(about) or "something else"
            out.append(f"  {len(self.silent)} more apply here and are about {named} "
                       f"alone. They are not an answer about {subject}.")
        return out


def answer(place: str, park: str, topic: Topic,
           regulations: Sequence[Regulation], subject: str = "",
           marker: Optional[Marker] = None) -> Answer:
    """What is known about *subject* at *place*.

    *regulations* must already be scoped to this place -- pass
    :func:`rules_for_place`, never the whole table.
    """
    return Answer(place=place, park=park, topic=topic,
                  subject=str(subject or "").strip().lower(),
                  rules=[r for r in regulations if r.category == topic.category],
                  marker=marker)
