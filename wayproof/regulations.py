"""Rules that govern what you may do once you hold a permit.

``data/permits.csv`` answers *how do I get and keep a permit* -- quota, release
dates, fees, cancellation, what makes the document valid. This module answers
the separate question of *what rules apply while I'm out there*: fire, food
storage, waste, pets, stock, group size, and so on.

Splitting them apart fixed a real problem rather than a theoretical one. The
California Campfire Permit requirement is state law (PRC 4433), restated by
every forest, and it had been copy-pasted into seven ``permits.csv`` rows --
which promptly drifted. Five of the seven described it as covering a "stove"
when it actually covers campfires, stoves, lanterns and barbeques; they
offered three different URLs between them; and none carried the 18-and-over
signer requirement or the legal citation. A fact asserted in seven places is
a fact maintained in none of them.

So a regulation is stored once and *inherited*, via ``scope_type``:

- ``jurisdiction`` -- state law, applying to every permit group in that state
  (``scope_value`` matches ``PermitRule.jurisdiction``)
- ``agency`` -- a forest- or District-wide rule (matches ``PermitRule.agency_ids``,
  and ``Trailhead.agency_id`` for land you can enter without a permit)
- ``park`` -- one park unit's own rule, stricter than its agency's (matches
  ``Campground.park``/``Trailhead.park``)
- ``wilderness`` -- one designated wilderness's own rulebook, which can span
  several permit products (matches ``PermitRule.wilderness_area``, falling back
  to ``Trailhead.wilderness_area``)
- ``permit_group`` -- specific to one permit product

The wilderness layer exists because Mokelumne Wilderness is entered on two
different permits -- the free general self-issue one, and the quota'd Carson
Pass Management Area permit -- governed by a single set of wilderness
regulations. Scoping those to a permit group would have meant maintaining
ten rules in two places, which is the drift this module was built to stop.

``regulations_for`` resolves all three layers for a given permit group, and
``regulations_in_force`` is what callers should use -- it derives those keys
from a permit and a trailhead together, so permit-free land still inherits the
rules of the agency that manages it. The
jurisdiction layer is why ``permits.csv`` carries an explicit ``jurisdiction``
column even though every group in the dataset is currently Californian: "all
our groups are in California" is true today by coincidence of coverage, and
inheriting statewide law off that coincidence would break silently the first
time a Nevada or Oregon group is added.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

import pandas as pd

if TYPE_CHECKING:  # annotations only -- keeps this module at the bottom layer
    from .model import Trailhead
    from .permits import PermitRule

JURISDICTION = "jurisdiction"
AGENCY = "agency"
WILDERNESS = "wilderness"
PARK = "park"
PERMIT_GROUP = "permit_group"
_VALID_SCOPES = {JURISDICTION, AGENCY, WILDERNESS, PARK, PERMIT_GROUP}

NO_PERMIT_GROUP = "none"
"""``permits.csv``'s shared "no wilderness permit required" row.

Not a permit product. It is the fallback for every trailhead that needs no
permit -- currently sixteen of them, across six different agencies -- which is
why nothing may be scoped to it and why ``Trailhead.agency_id`` exists.
"""

# Ordered for presentation: the ones that carry a fine or ruin a trip first.
CATEGORY_ORDER = [
    "fire", "food_storage", "group_size", "camping", "waste", "water",
    "fishing", "pets", "stock", "weapons", "aircraft", "natural_features",
    "commercial",
]

CATEGORY_LABELS = {
    "fire": "Fire",
    "food_storage": "Food storage",
    "group_size": "Group size",
    "camping": "Camping",
    "waste": "Waste",
    "water": "Water",
    "fishing": "Fishing",
    # "Pets", not "Dogs", and the distinction is load-bearing. MOST pets rows in
    # this dataset are written about dogs, because that is how the agencies
    # write them -- but not all: EBRPD's Ordinance 38 says "dog, cat or other
    # animal" throughout, which is what lets this project answer for an animal
    # nobody legislated about by name. Someone arriving with a cat, a rabbit or
    # a horse-adjacent animal is asking a question a dog leash rule does not
    # answer, and reading a dog rule as a pet rule is the confident-wrong-answer
    # failure this project exists to avoid. Label the category honestly and let
    # the rule's own summary say which animal it actually governs --
    # :mod:`wayproof.pets` is what reads it, and it reads the summary only.
    "pets": "Pets",
    "stock": "Stock and livestock",
    "weapons": "Firearms",
    "aircraft": "Drones and aircraft",
    "natural_features": "Natural features",
    "commercial": "Commercial use",
}


#: Words that signal prose is talking about a regulation category. Used to spot
#: a fact being restated in a permit's free text when a rule already carries it.
#:
#: Deliberately a *vocabulary* check rather than a text-similarity one. The
#: duplication this is meant to catch was a paraphrase, not a copy: "Max group
#: size 8 people outside the CPMA" against "Maximum group size is 8 people
#: overnight and 12 for a day hike" share no six-word phrase, so shingle
#: matching found nothing. What they share is the subject.
#:
#: Noisy by design, which is why it feeds ``open_questions()`` rather than a
#: test. A permit's prose can mention camping without restating the camping
#: rule, and a human has to look. Silence would be worse: the campfire rule was
#: copied into seven rows and drifted before anyone noticed.
CATEGORY_VOCABULARY = {
    "fire": ("campfire", "camp fire", "wood fire", "camp stove", "fire ban", "fire danger"),
    "food_storage": ("bear canister", "bear-resistant", "bear proof", "food storage"),
    # "party size" is excluded: "changing party size costs $5" is a fee
    # mechanic, not a restatement of a group limit.
    "group_size": ("group size", "people per permit", "max group"),
    # "setback" and "designated site" are excluded: prose legitimately
    # cross-references a rule ("the water setbacks still apply") and describes
    # permit allocation ("14 designated sites") without restating either.
    "camping": ("camp within", "camping within", "stay limit", "consecutive days"),
    "waste": ("cat hole", "human waste", "pack out", "toilet paper"),
    "water": ("treat all water", "purification"),
    # "pet"/"pets" and not a bare "cat": "cat hole" is the waste category's own
    # vocabulary, and a bare "cat" would claim every waste rule in the dataset
    # as a pet rule. "dog" stays because agencies overwhelmingly write "dogs"
    # even where the rule is about pets generally -- see CATEGORY_LABELS.
    "pets": ("leash", "pet waste", "dog waste", "pets", "pet", "dog"),
    "stock": ("livestock", "pack animal", "weed free", "weed-free"),
    "weapons": ("firearm", "discharge"),
    "fishing": ("fish and game", "fishing licence", "fishing license"),
    "aircraft": ("drone", "hang glider", "over-snow", "game cart"),
}


@dataclass
class Regulation:
    """One row of ``data/regulations.csv``."""

    regulation_id: str
    scope_type: str
    scope_value: str
    category: str
    summary: str
    detail: str = ""
    citation: str = ""
    source_url: str = ""
    source_last_updated: str = ""
    verified_date: str = ""
    log_entry_ids: str = ""
    """Semicolon-separated ``entry_id`` values from the permit source log.

    Blank means nobody has logged a check of this rule, which renders as
    unverified rather than as fine. See :mod:`wayproof.evidence`.
    """
    supersedes: str = ""
    """Semicolon-separated ``regulation_id`` values this rule DISPLACES where
    both are in force. Use :attr:`superseded_ids` rather than the string.

    THE EDGE IS RECORDED, NEVER COMPUTED, and that is the whole of the design.
    The tempting shortcut is to derive it from :data:`SPECIFICITY` -- the
    narrower rule wins -- and ``point-pinole-dogs`` is why it would be wrong.
    That park caps dogs at three PER PERSON where the District's campground
    rule caps them at three PER SITE. It is narrower, and it does not displace
    anything: the two govern different things, one a walking limit and one a
    campsite occupancy limit, and the stricter applies where both do. Derived
    supersession would let a party of ten bring thirty dogs to a campsite.

    So a rule declares what it displaces, and a rule that declares nothing
    displaces nothing.

    DECLARED BY THE NARROW RULE, not the broad one, because that is the row
    being written when the relationship is discovered. The alternative --
    ``superseded_by`` on the general rule -- means editing a rule every time an
    exception is found somewhere else, which is exactly how ``ebrpd-alcohol``
    came to hand-maintain a list of its own exceptions in prose and to admit,
    in that same prose, that the list was incomplete.

    NEITHER SCOPE NOR CATEGORY IS REQUIRED TO DIFFER, because in this dataset
    they do not. ``ebrpd-backpack-no-fire-no-alcohol`` is scoped ``agency``
    exactly like the ``ebrpd-fire`` and ``ebrpd-alcohol`` rules it displaces --
    it is narrow by naming a CLASS OF SITE, which no scope level expresses --
    and it is filed under ``fire`` while ``ebrpd-alcohol`` is under
    ``camping``. A validator demanding a narrower scope or a matching category
    would reject the clearest real case in the table.

    ONLY FULL DISPLACEMENT GOES HERE. A rule that overrides part of another is
    not representable and must not be written as if it were. ``round-valley-no-
    dogs`` bans dogs from a preserve whose campground rule
    (``ebrpd-pets-campground``) governs "dog, cat or other animal" -- recording
    it as superseding would tell someone arriving with a cat that Ordinance 38
    does not apply to them. Those partial relationships stay in ``detail``,
    where they are prose a person reads rather than an edge code acts on.
    """
    scope_display: str = ""
    """How to name this rule's scope to a reader, when the key isn't readable.

    ``scope_value`` is a matching key, not prose: an agency scope reads
    ``eldorado_nf``. Set this to ``Eldorado National Forest`` and the surfaces
    show that instead.
    """

    @property
    def superseded_ids(self) -> List[str]:
        """:attr:`supersedes` as a list; empty when it displaces nothing."""
        return [p.strip() for p in self.supersedes.split(";") if p.strip()]

    @property
    def inherited(self) -> bool:
        """True when this rule comes from state law or an agency-wide policy
        rather than from the permit product itself."""
        return self.scope_type != PERMIT_GROUP

    @property
    def scope_label(self) -> str:
        if self.scope_type == JURISDICTION:
            return f"{self.scope_display or self.scope_value} state law"
        if self.scope_type in (AGENCY, WILDERNESS, PARK):
            return self.scope_display or self.scope_value
        return "this permit"


def _str_field(row, col: str) -> str:
    val = row.get(col)
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()


def load_regulations(path: str | Path = "data/regulations.csv") -> List[Regulation]:
    """Load every regulation, in file order.

    Returns an empty list if the file doesn't exist -- regulations are layered
    context on top of a permit lookup, not required input for one.
    """
    path = Path(path)
    if not path.exists():
        return []
    df = pd.read_csv(path)

    out: List[Regulation] = []
    for _, row in df.iterrows():
        regulation_id = _str_field(row, "regulation_id")
        if not regulation_id:
            continue
        scope_type = _str_field(row, "scope_type")
        if scope_type not in _VALID_SCOPES:
            raise ValueError(
                f"Invalid scope_type {scope_type!r} for {regulation_id!r}; "
                f"expected one of {sorted(_VALID_SCOPES)}"
            )
        scope_value = _str_field(row, "scope_value")
        if scope_type == PERMIT_GROUP and scope_value == NO_PERMIT_GROUP:
            # The obvious place to file a rule for land that needs no permit,
            # and the one place it must never go. permits.csv's "none" row is a
            # shared placeholder, not a permit product: sixteen trailheads
            # across six agencies resolve to it, so a rule scoped here would
            # hand an East Bay leash law to a trailhead in Plumas NF. Scope it
            # to the agency or the wilderness that actually issues it.
            raise ValueError(
                f"Regulation {regulation_id!r} is scoped to permit_group "
                f"{NO_PERMIT_GROUP!r}, which is the shared 'no permit required' "
                "placeholder rather than a permit product -- every permit-free "
                "trailhead in the dataset would inherit it, whatever agency "
                "manages it. Scope it to an 'agency' or 'wilderness' instead."
            )
        out.append(Regulation(
            regulation_id=regulation_id,
            scope_type=scope_type,
            scope_value=scope_value,
            category=_str_field(row, "category"),
            summary=_str_field(row, "summary"),
            detail=_str_field(row, "detail"),
            citation=_str_field(row, "citation"),
            source_url=_str_field(row, "source_url"),
            source_last_updated=_str_field(row, "source_last_updated"),
            verified_date=_str_field(row, "verified_date"),
            log_entry_ids=_str_field(row, "log_entry_ids"),
            supersedes=_str_field(row, "supersedes"),
            scope_display=_str_field(row, "scope_display"),
        ))

    _validate_supersessions(out)
    return out


def _validate_supersessions(regulations: List[Regulation]) -> None:
    """Refuse a supersession edge that cannot mean anything.

    A dangling id is the dangerous one: it does not raise at render time, it
    silently renders the general rule as still applying, which is the failure
    the edge exists to prevent. So it is caught at load.
    """
    known = {r.regulation_id for r in regulations}
    for reg in regulations:
        for target in reg.superseded_ids:
            if target == reg.regulation_id:
                raise ValueError(
                    f"Regulation {reg.regulation_id!r} supersedes itself"
                )
            if target not in known:
                raise ValueError(
                    f"Regulation {reg.regulation_id!r} supersedes unknown rule "
                    f"{target!r}. A typo here does not fail at render time -- it "
                    f"quietly leaves the displaced rule reading as if it still "
                    f"applied, which is the answer this edge exists to prevent."
                )
    by_id = {r.regulation_id: r for r in regulations}
    # Checked BEFORE the scope rule below, which would otherwise catch every
    # mutual pair and report it as a scope error. A pair cannot satisfy the
    # scope rule in both directions -- each would have to be narrower than
    # the other -- so this only ever fires on an authoring mistake, and it
    # names that mistake instead of a symptom of it.
    #
    # Mutual supersession is two rules each claiming to be the exception to the
    # other, which names no winner and cannot be rendered. It is a real
    # authoring mistake rather than a hypothetical: it is what you write if you
    # read "stricter than" in both rows' detail and fill in both.
    for reg in regulations:
        for target in reg.superseded_ids:
            if reg.regulation_id in by_id[target].superseded_ids:
                raise ValueError(
                    f"Regulations {reg.regulation_id!r} and {target!r} supersede "
                    f"each other, so neither governs. One of them is the "
                    f"exception; say which."
                )
    # A rule may only displace something BROADER than itself, and this check
    # was added because its absence produced a wrong answer within an hour of
    # the column existing. `ebrpd-backpack-no-fire-no-alcohol` is filed at
    # AGENCY scope -- it is narrow by naming a class of site, which this table
    # has no level for -- and it was given edges onto the District's fire and
    # alcohol rules. Both are also AGENCY scope, so the edge fired everywhere
    # the class-of-site rule did: at Anthony Chabot's drive-in family
    # campground, where every site has a fire ring with a grill, the tool
    # marked Ordinance 38's barbecue permission "does not apply here".
    #
    # SPECIFICITY IS A PROXY for the real invariant, which is that a rule may
    # only declare an edge if its scope covers everything it reaches. That is
    # not computable -- it is a fact about the rule's own words. Requiring a
    # strictly narrower scope is computable, catches the whole class of
    # mistake, and its false rejection is exactly the case that should be
    # rejected today: a rule too narrow for any scope level here needs a new
    # level, not an edge.
    for reg in regulations:
        for target in reg.superseded_ids:
            mine = SPECIFICITY.get(reg.scope_type, 4)
            theirs = SPECIFICITY.get(by_id[target].scope_type, 4)
            if mine >= theirs:
                raise ValueError(
                    f"Regulation {reg.regulation_id!r} ({reg.scope_type}) "
                    f"supersedes {target!r} ({by_id[target].scope_type}), which is "
                    f"not broader than it. A rule may only displace something it "
                    f"is narrower THAN BY SCOPE: an edge fires everywhere the "
                    f"declaring rule is in force, so one that is narrow only in "
                    f"its wording -- 'at a BACKPACK site' filed at agency scope -- "
                    f"displaces the general rule at every site the agency manages. "
                    f"Such a rule needs a narrower scope level, not an edge."
                )




SPECIFICITY = {PERMIT_GROUP: 0, PARK: 1, WILDERNESS: 2, AGENCY: 3, JURISDICTION: 4}
"""Lower is more specific. A permit's own rule reads above one park's rule,
which reads above the wilderness rulebook, which reads above agency policy,
which reads above state law.

A park sits above its agency because that is the direction real strictness
runs: EBRPD permits portable barbecues District-wide and Black Diamond Mines
bans every fire and barbecue outright. A reader shown only the agency rule
brings a barbecue."""


def scope_applies(scope_type: str, scope_value: str, permit_group: str = "",
                  agency: "str | Sequence[str]" = "", jurisdiction: str = "",
                  wilderness: str = "", park: str = "") -> bool:
    """Does a rule at ``scope_type``/``scope_value`` reach this permit group?

    Split out of :func:`regulations_for` so any other scoped table -- conditions,
    hazards, seasonal access -- resolves identically instead of copying four-way
    scope logic and drifting from it.

    ``agency`` takes one key or several, because a wilderness can be co-managed.
    Pass ``PermitRule.agency_ids``, never ``PermitRule.agency``: the latter is a
    display string, and matching on it once made a forest-wide rule inherit to
    nothing.
    """
    if scope_type == PERMIT_GROUP:
        return bool(permit_group) and scope_value == permit_group
    if scope_type == WILDERNESS:
        return bool(wilderness) and scope_value == wilderness
    if scope_type == PARK:
        return bool(park) and scope_value == park
    if scope_type == AGENCY:
        agencies = {agency} if isinstance(agency, str) else set(agency)
        agencies.discard("")
        return scope_value in agencies
    return bool(jurisdiction) and scope_value == jurisdiction


def regulations_for(
    regulations: Sequence[Regulation],
    permit_group: str = "",
    agency: "str | Sequence[str]" = "",
    jurisdiction: str = "",
    wilderness: str = "",
    park: str = "",
) -> List[Regulation]:
    """Every regulation applying to one permit group, all three scopes resolved.

    Ordered by :data:`CATEGORY_ORDER`, then by how specific the rule is, so a
    wilderness's own fire ban reads before the statewide permit requirement it
    sits on top of. Unknown categories sort last rather than being dropped.

    ``agency`` takes one key or several. Pass ``PermitRule.agency_ids``, never
    ``PermitRule.agency`` -- the latter is a display string. Several because a
    wilderness can be co-managed, as Desolation is by Eldorado NF and the Lake
    Tahoe Basin Management Unit; a rule from either manager applies.
    """
    def applies(reg: Regulation) -> bool:
        return scope_applies(reg.scope_type, reg.scope_value, permit_group=permit_group,
                             agency=agency, jurisdiction=jurisdiction,
                             wilderness=wilderness, park=park)

    def sort_key(reg: Regulation):
        category_rank = (CATEGORY_ORDER.index(reg.category)
                         if reg.category in CATEGORY_ORDER else len(CATEGORY_ORDER))
        return (category_rank, SPECIFICITY.get(reg.scope_type, 4), reg.regulation_id)

    return sorted((r for r in regulations if applies(r)), key=sort_key)


def supersessions(regulations: Sequence[Regulation]) -> "Dict[str, List[Regulation]]":
    """``{displaced regulation_id: [rules displacing it]}``, among these rules only.

    SCOPE FALLS OUT AND IS NOT COMPUTED. Black Diamond's alcohol ban displaces
    the District's beer-and-wine rule at Black Diamond and nowhere else, and
    that is automatic: pass the rules in force for THIS trip and the park rule
    is simply absent everywhere else, so its edge cannot fire. Nothing here
    needs to know where the caller is.

    Pass the output of :func:`regulations_in_force`. Passing the whole table
    would report Sunol's fire ban as displacing the District rule at Anthony
    Chabot.
    """
    present = {r.regulation_id: r for r in regulations}
    out: "Dict[str, List[Regulation]]" = {}
    for reg in regulations:
        for target in reg.superseded_ids:
            if target in present:
                out.setdefault(target, []).append(reg)
    return out


def in_force_after_supersession(
    regulations: Sequence[Regulation],
) -> "List[Tuple[Regulation, List[Regulation]]]":
    """``[(rule, rules displacing it), ...]`` in the order they should read.

    A DISPLACED RULE IS RETURNED, NOT DROPPED. Two reasons, and the second is
    the one that decides it. Dropping hides that a District norm exists at all,
    so a camper who read "beer and wine for over-21s" on EBRPD's own page and
    then sees nothing about alcohol here concludes this project has no data
    rather than that the rule does not reach them. And this project does not
    silently drop: the whole of ``discovery`` and the ``pets`` marker states
    what it excluded and why.

    The caller renders the pair. What it must not do is print a displaced rule
    as a peer of the one displacing it, which is what every surface did before
    this existed -- at Stewartville, "No alcohol at all" and "beer and wine, 21
    and over" read as two bullets of equal weight, one above the other, with
    nothing saying which one you are actually under.
    """
    displaced = supersessions(regulations)
    return [(r, displaced.get(r.regulation_id, [])) for r in regulations]


SUPERSEDED_FLAG = "DOES NOT APPLY HERE"
"""What a displaced rule is marked with, on every surface.

In the bullet itself rather than in a note under it. The failure being fixed
is a reader skimming rules and taking the District norm for their answer, and
a caveat on the line below is exactly what such a reader skips.
"""


def supersession_note(displacers: Sequence[Regulation], limit: int = 160) -> str:
    """One line saying which rules displace this one, quoting them.

    QUOTED, NOT NAMED BY SCOPE, because scope does not identify them. Both
    ``ebrpd-fire`` and ``ebrpd-backpack-no-fire-no-alcohol`` carry the scope
    label "East Bay Regional Park District", so "displaced by the rule from
    East Bay Regional Park District" reads, on the District's own rule, as
    gibberish. The rule's own words are the only handle a reader has, and they
    are also the answer they came for.

    The limit is 160 rather than something tidier because the longest rule
    here is 152 and TRUNCATING IT CUTS OFF THE HALF THAT DOES THE DISPLACING.
    ``ebrpd-backpack-no-fire-no-alcohol`` reads "no campfires and no charcoal
    barbecues. Camp stoves are permitted. No alcohol at all, beer and wine
    included" -- the alcohol clause is last, and it is the clause that
    displaces ``ebrpd-alcohol``. A quote ending before it explains nothing.

    Shared by all four surfaces for the reason ``regulations_in_force`` is:
    each one phrasing this itself is how they drift into four different
    answers to the same question.
    """
    if not displacers:
        return ""
    quotes = []
    # Most specific first, the same order regulations_for sorts into, so a
    # park's own ban reads before a District-wide class-of-site rule.
    for reg in sorted(displacers, key=lambda r: SPECIFICITY.get(r.scope_type, 4)):
        text = " ".join((reg.summary or "").split())
        quotes.append(f'"{text[:limit].rstrip()}..."' if len(text) > limit
                      else f'"{text}"')
    joined = "; ".join(quotes)
    return (f"The District-wide rule, displaced here by "
            f"{'a stricter rule' if len(quotes) == 1 else 'stricter rules'}: "
            f"{joined} Read that, not this.")


def group_by_category(regulations: Sequence[Regulation]) -> List[tuple]:
    """``[(label, [Regulation, ...]), ...]`` in :data:`CATEGORY_ORDER`."""
    grouped: dict = {}
    for reg in regulations:
        grouped.setdefault(reg.category, []).append(reg)
    return [
        (CATEGORY_LABELS.get(category, category.replace("_", " ").capitalize()),
         grouped[category])
        for category in sorted(
            grouped,
            key=lambda c: CATEGORY_ORDER.index(c) if c in CATEGORY_ORDER else len(CATEGORY_ORDER),
        )
    ]


def regulations_in_force(
    regulations: Sequence[Regulation],
    rule: "Optional[PermitRule]" = None,
    trailhead: "Optional[Trailhead]" = None,
    agency: "str | Sequence[str]" = (),
    jurisdiction: str = "",
    park: str = "",
) -> List[Regulation]:
    """Every regulation applying to a trip, resolved from both what admits you
    and where you actually are.

    :func:`regulations_for` takes scope keys; this takes the two objects a
    caller already has and works out those keys, so the four surfaces that ask
    "what rules apply here" -- ``plan``, the site views, the reports, and the
    scorecard -- cannot answer it four subtly different ways. They previously
    each built the call by hand off ``PermitRule`` alone, which is the same
    copy-it-into-every-caller drift the regulations table itself was built to
    stop.

    Reading scope off the permit alone left a hole. A trailhead with no permit
    resolves to ``permits.csv``'s shared ``none`` row, which carries no agency
    and no wilderness -- and cannot, because sixteen trailheads across six
    agencies share it. So every agency-scoped rule was unreachable from every
    permit-free trailhead in the dataset: EBRPD's East Bay parks, but also
    Plumas, Tahoe, and the LTBMU. ``Trailhead.agency_id`` closes that, and the
    agencies are unioned rather than replaced because a permit's issuer and the
    land you start on are both real (an Inyo trailhead into SEKI is under Inyo
    forest rules for the Inyo part of the walk).

    Wilderness resolves permit-first and falls back to the trailhead's, rather
    than unioning: two named wildernesses on one trip is a route question this
    project does not model, and asserting a second rulebook applies without
    evidence would broaden rules onto a trip rather than narrow them. The
    fallback alone fixes a real case -- Horseshoe Meadows (Cottonwood) sits in
    the Golden Trout Wilderness while its ``inyo_gtw`` permit row leaves
    ``wilderness_area`` blank, so that rulebook reached nothing.

    ``agency`` and ``jurisdiction`` carry scope from somewhere that is neither a
    permit nor a trailhead -- a campground planned as the objective in its own
    right. Jurisdiction especially: state law reaches a trip through the
    permit's ``jurisdiction``, so a campsite booked without a permit would
    otherwise inherit no state law at all, and every car-camping plan would
    silently drop the California Campfire Permit.
    """
    permit_group = rule.permit_group if rule is not None else ""
    jurisdiction = (rule.jurisdiction if rule is not None else "") or jurisdiction
    wilderness = rule.wilderness_area if rule is not None else ""
    agencies = set(rule.agency_ids) if rule is not None else set()
    agencies |= ({agency} if isinstance(agency, str) else set(agency))

    if trailhead is not None:
        if not permit_group:
            permit_group = trailhead.permit_group
        agencies |= {key.strip() for key in trailhead.agency_id.split(";")}
        wilderness = wilderness or trailhead.wilderness_area

    if trailhead is not None:
        park = park or trailhead.park

    agencies.discard("")
    return regulations_for(regulations, permit_group, sorted(agencies),
                           jurisdiction, wilderness, park)
