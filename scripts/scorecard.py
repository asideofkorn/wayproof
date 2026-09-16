#!/usr/bin/env python3
"""Score the README's questions against every objective in the dataset.

The README lists the questions this project exists to answer, each with what
makes an answer *wrong*. This turns that list into a number that moves.

It answers **can the tool answer at all**, for every objective, on every commit.
It does **not** answer whether the answer is right -- only a completed trip does
that, and those live in `docs/user_stories/`. Two loops at different speeds:

    fast (this)   coverage    every commit, no trip needed
    slow (trips)  correctness a few times a year, one trip at a time

Both are needed, and the fast one is worthless without the slow one: a question
can score `answered` while the answer is wrong. `Q7 cost` is the clearest case
-- see its `limit`. The Ohlone trip that reported a $97 trip as free would have
scored green here.

**This is a measurement, not an assertion.** It does not fail the build. A
coverage number that breaks CI becomes a target within a week, and the cheapest
way to move most rows is to add unchecked data -- which is the failure this
project already has guards against. Read it, do not chase it.

Usage
-----
    python scripts/scorecard.py                 # table
    python scripts/scorecard.py --by-question Q6  # which objectives, and why
"""

from __future__ import annotations

import argparse
import collections
import datetime
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wayproof.access import load_approaches
from wayproof.advisories import load_advisories
from wayproof.booking import load_booking_channels
from wayproof.camping import load_campgrounds, load_campsites
from wayproof.data_loader import load_peaks, load_trailheads
from wayproof.park_access import load_park_access
from wayproof.permits import PermitRule, load_permits
from wayproof.plan import UNKNOWN, PlanResult, resolve_plan
from wayproof.regulations import Regulation, load_regulations, regulations_in_force
from wayproof.release_policy import CONTACT_REQUIRED, OFF_SEASON, WALKUP
from wayproof.water import load_water_source_log, load_water_sources

# -- verdicts ---------------------------------------------------------------
#
# Six, because each one has a different fix. Collapsing them loses the
# distinction that matters most: DECLINED is the tool being honest, OMITTED is
# the tool being silent about something this project already knows.

ANSWERED = "answered"    # the tool gives an answer
PARTIAL = "partial"      # an answer with a hole the tool names
DECLINED = "declined"    # the tool says it does not know -- honest, and a usable answer
OMITTED = "omitted"      # the project HOLDS this and the surface does not show it
NO_DATA = "no-data"      # the field exists; no row covers this objective
NO_MODEL = "no-model"    # no field exists anywhere -- a schema gap, not a data gap

VERDICTS = [ANSWERED, PARTIAL, DECLINED, OMITTED, NO_DATA, NO_MODEL]

#: Fix implied by each verdict, printed under the table so the number is
#: actionable rather than merely bad.
VERDICT_MEANING = {
    ANSWERED: "nothing -- but only a trip can say whether it was right",
    PARTIAL: "finish the row, or state the hole more precisely",
    DECLINED: "resolve the underlying uncertainty, or accept it",
    OMITTED: "wire the data to the surface -- this is the cheapest fix on the board",
    NO_DATA: "enter data against the existing schema",
    NO_MODEL: "the schema has no place to put this yet",
}


@dataclass
class Question:
    """One README question, with a mechanical proxy for 'could the tool answer'."""

    qid: str
    tier: int            # 1 costs you the trip, 2 costs money or a day, 3 recoverable
    text: str            # verbatim from README's "What Someone Actually Asks"
    wrong_if: str        # verbatim -- the falsification criterion
    proxy: Callable      # (ctx) -> verdict
    limit: str = ""      # where the proxy is weaker than the question
    structural: bool = False
    """The verdict does not depend on the objective -- no field exists anywhere,
    so every objective scores the same. Counted once, not 462 times: leaving
    these in the per-objective aggregate buries the rows that actually vary."""


@dataclass
class Ctx:
    """Everything a proxy may look at for one objective."""

    result: PlanResult
    rule: Optional[PermitRule]
    regs: List[Regulation] = field(default_factory=list)

    @property
    def declined(self) -> bool:
        """The tool refused to name an entry point, so anything hanging off the
        permit is a candidate rather than an answer."""
        return bool(self.result.entry_conflicts)

    def category(self, name: str) -> bool:
        return any(r.category == name for r in self.regs)


# -- proxies ----------------------------------------------------------------
#
# Deliberately generous to the tool: each asks "could it answer", never "was it
# right". Where a proxy is weaker than its question, `limit` says so and the
# report prints it.

def _q2(c: Ctx) -> str:
    if c.declined:
        return DECLINED
    return ANSWERED if c.rule else NO_DATA


def _q3(c: Ctx) -> str:
    if not c.rule:
        return NO_DATA
    if c.declined:
        return DECLINED
    if c.rule.release_phases or not c.rule.quota_required:
        return ANSWERED
    return PARTIAL  # quota'd, but no computable release date


def _q5_other_end(c: Ctx) -> str:
    """DECLINED, not NO_MODEL: there is now somewhere to put the other end.

    `resolve_plan(exit_trailhead=...)` resolves a named exit's permit group and
    its park access, and the exit's entrance fee reaches the Cost block -- which
    is this question's own "wrong if it treats exit parking as unrelated". So
    "the schema has no place to put this yet" is no longer true.

    What is left is genuine uncertainty only the caller can settle: which end you
    finish at is a choice, not a fact about the terrain, and the same peak from
    the same trailhead is an out-and-back or a one-way depending on the person.
    The scored plan names no exit, so the tool states the assumption and names
    the remedy rather than guessing -- which is what DECLINED means here.

    Deliberately NOT ANSWERED. A default plan still tells you nothing about an
    exit, and silence is never read as returns-to-start.
    """
    return DECLINED


def _q6_carry(c: Ctx) -> str:
    """Both halves, because the README's 'wrong if' names the second one.

    Equipment (a bear canister) comes from the food-storage rule. The *document*
    -- "a digital reservation confirmation is not a permit" -- comes from
    `permits.carry`. Scoring only the first would have let this row go green
    while the thing the question says makes an answer wrong was still prose in
    `notes`.
    """
    equipment = c.category("food_storage")
    document = bool(c.rule and c.rule.carry.strip())
    if equipment and document:
        return ANSWERED
    if equipment or document:
        return PARTIAL
    return NO_DATA


def _q7_cost(c: Ctx) -> str:
    if not c.result.costs:
        return NO_DATA
    if any(x.status == UNKNOWN for x in c.result.costs):
        return PARTIAL
    return DECLINED if c.declined else ANSWERED


def _q8_change_cancel(c: Ctx) -> str:
    # Was NO_MODEL until booking_channels.csv gained a change_cancel field.
    # It has one now, so this is a data gap rather than a schema gap -- but
    # only for the half of the question the field answers. "Can I change or
    # cancel" is now expressible; "and by when" is not: the field holds the
    # CHANNEL (online, phone, not email), and no structured cutoff exists
    # anywhere. A permit's refund deadline is still prose in permits.notes.
    fac = c.result.facilities
    channels = fac.booking_channels if fac else []
    return ANSWERED if any(ch.change_cancel for ch in channels) else NO_DATA


def _q9_party(c: Ctx) -> str:
    return ANSWERED if c.category("group_size") else NO_DATA


def _q10_missed_release(c: Ctx) -> str:
    if not c.rule:
        return NO_DATA
    phases = c.rule.release_phases
    if not phases:
        return NO_DATA
    fallback = any(p.mechanism in (WALKUP, CONTACT_REQUIRED) or p.season == OFF_SEASON
                   for p in phases)
    return ANSWERED if fallback else PARTIAL


def _q11_reachable(c: Ctx) -> str:
    # Seasonal road closure, snow window, vehicle capability: no field holds any
    # of it. Trailheads carry coordinates and a `notes` string.
    return NO_MODEL


def _q12_fire(c: Ctx) -> str:
    local = any(r.category == "fire" and r.scope_type in ("permit_group", "wilderness")
                for r in c.regs)
    if local:
        return ANSWERED
    # Only the statewide campfire permit applies, which the README itself says
    # reads as permission when nothing local sits on top of it.
    return PARTIAL if c.category("fire") else NO_DATA


def _q13_pet(c: Ctx) -> str:
    return ANSWERED if c.category("pets") else NO_DATA


def _q14_camp(c: Ctx) -> str:
    return ANSWERED if c.category("camping") else NO_DATA


def _q15_reciprocity(c: Ctx) -> str:
    if not c.rule:
        return NO_DATA
    return ANSWERED if c.rule.interagency_note.strip() else NO_DATA


def _q16_water(c: Ctx) -> str:
    fac = c.result.facilities
    if not fac or not fac.water_sources:
        return NO_DATA
    dated = any(w.name in fac.water_status for w in fac.water_sources)
    return ANSWERED if dated else PARTIAL


def _q17_closed(c: Ctx) -> str:
    # Was NO_MODEL until data/advisories.csv existed. It does now, so the
    # schema gap is closed and what remains is a data gap: most parks in this
    # project have no advisory recorded, which is a different and lesser
    # failure than being unable to express one.
    #
    # Still NOT the whole question. Ohlone S6 was about a closed facility and
    # one that never existed being indistinguishable, and that is a lifecycle
    # field on campgrounds, which no table has. An advisory says "closed until
    # further notice"; it cannot say "this camp no longer exists".
    closures = [a for a in c.result.advisories
                if a.kind in ("trail_closure", "area_closure", "facility")]
    if closures:
        return ANSWERED
    return NO_DATA if c.result.advisories else NO_DATA


def _q18_hazard(c: Ctx) -> str:
    # Burn scars, snow windows, exposure. Desolation's `notes` mentions the
    # Caldor Fire scar and an October-to-July snow window as prose; no table has
    # a hazard field, and none is dated, so nothing can say "right now".
    return NO_MODEL


def _q20_how_do_you_know(c: Ctx) -> str:
    if not c.rule:
        return NO_DATA
    if not c.rule.verified_date:
        return NO_DATA
    return ANSWERED if c.rule.log_entry_ids.strip() else PARTIAL


def _q21_what_dont_you_know(c: Ctx) -> str:
    return ANSWERED if c.result.open_questions else NO_DATA


QUESTIONS: List[Question] = [
    Question("Q2", 1, "Does my specific route change which permit I need?",
             "Wrong if it answers per trailhead.", _q2),
    Question("Q3", 1, "What is the scarce thing, and when does it become available?",
             "Wrong if it assumes the scarce thing is a permit.", _q3),
    Question("Q5", 1, "What do I need at the other end?",
             "Wrong if it treats exit parking as unrelated.", _q5_other_end, structural=True,
             limit="Scores the DEFAULT plan, which names no exit, so it is DECLINED "
                   "for all 462 rather than measured. Naming --exit resolves the "
                   "exit's permit group everywhere and compares it against the "
                   "entry's; the PARKING half depends on park_access.csv, which has "
                   "one row (Del Valle) and no Sierra trailhead carries a `park` at "
                   "all -- so the half this question is named for is answerable for "
                   "the Ohlone trip and empty across the Sierra. The route BETWEEN "
                   "the ends is not modelled either way."),
    Question("Q6", 1, "What must I carry?",
             "Wrong if it says 'required' without saying that a digital reservation "
             "confirmation is not a permit.", _q6_carry,
             limit="ANSWERED needs both halves: the equipment rule AND a stated "
                   "`carry` requirement. 11 of 15 permit groups have no `carry` "
                   "value, so most objectives are PARTIAL -- the food-storage rule "
                   "reaches them and nothing says which document is valid."),
    Question("Q7", 2, "What will it cost, all in?",
             "Wrong if entrance, parking and reservation fees are reported away "
             "from the headline figure.", _q7_cost,
             limit="Trivially satisfied when the permit is the ONLY component known. "
                   "Measures 'did we price what we know of', not 'did we know of "
                   "everything'. The $97-reported-as-free trip would score ANSWERED."),
    Question("Q8", 2, "Can I change or cancel, and by when?",
             "Wrong if it gives a refund rule without its cutoff.", _q8_change_cancel,
             limit="Scores only that a change/cancel CHANNEL is recorded. That is "
                   "half the question: no structured cutoff exists anywhere, and a "
                   "permit's refund deadline is still prose in permits.notes, so "
                   "'and by when' remains unanswerable."),
    Question("Q9", 2, "How many of us can go?",
             "Wrong if it gives one number.", _q9_party,
             limit="Scores the group-size REGULATION. Party size as a booking and "
                   "pricing parameter is a different thing and has no field."),
    Question("Q10", 2, "If I miss the release, what are my options?",
             "Wrong if it reports 'sold out' where a walk-up share, a cancellation "
             "window or an off-season route exists.", _q10_missed_release),
    Question("Q11", 2, "Is the trailhead reachable on my dates?",
             "Wrong if it ignores seasonal road closure or snow.", _q11_reachable, structural=True),
    Question("Q12", 3, "Can I have a fire?",
             "Wrong if it reports the statewide permit requirement without the "
             "local ban sitting on top of it.", _q12_fire),
    Question("Q13", 3, "Can I bring a pet?",
             "Wrong if it says 'under control' where the forest requires a leash, "
             "or if it answers for dogs when the animal is not a dog.",
             _q13_pet,
             limit="Scores only that a pets rule resolves. Every pets rule in "
                   "the dataset is written about dogs; nothing checks that one "
                   "answers for the animal actually being brought."),
    Question("Q14", 3, "Where can and cannot I camp?",
             "Setbacks, designated sites, restoration closures.", _q14_camp),
    Question("Q15", 3, "Does my permit still cover me in the next wilderness?",
             "Reciprocity, and where it stops.", _q15_reciprocity,
             limit="Scores only that interagency_note is non-empty. It is a "
                   "paragraph of prose; nothing checks it against a route."),
    Question("Q16", 3, "Where is water, and when was it last confirmed?",
             "Wrong if availability is reported without a date.", _q16_water),
    Question("Q17", 3, "What is closed?",
             "Wrong if closed and never-existed look the same.", _q17_closed,
             limit="Scores only whether a closure is recorded for this objective's "
                   "park. advisories.csv can say a thing is closed; nothing can yet "
                   "say a facility was removed, which is the half of Ohlone S6 that "
                   "made closed and never-existed indistinguishable."),
    Question("Q18", 3, "What is hazardous right now?",
             "Burn scars, snow windows, exposure.", _q18_hazard, structural=True),
    Question("Q20", 0, "How do you know, and when did you last check?",
             "Wrong if a verification date is attached to a claim it does not cover.",
             _q20_how_do_you_know,
             limit="Scores that a citation EXISTS, not that it covers the claim -- "
                   "which is exactly what the question says makes an answer wrong."),
    Question("Q21", 0, "What do you not know here?",
             "Wrong if silence reads as confirmation.", _q21_what_dont_you_know,
             limit="Cannot distinguish 'nothing is open here' from 'nobody has "
                   "looked'. 153 objectives have an unresolved entry point and only "
                   "13 raise any open question, so silence is not confirmation."),
]

#: README questions with no honest mechanical proxy, and why. Listed so the
#: scorecard's own coverage is visible rather than silently partial.
NOT_SCORED = {
    "Q1 What do I need to do this trip?":
        "Too broad to falsify mechanically -- it is the union of the rest.",
    "Q4 How do I actually get it?":
        "reservation_method is always non-empty prose, so any proxy scores 100%. "
        "Needs a structured booking channel first.",
    "Q19 This is wrong, and here is what I found.":
        "A property of the report loop, not of any one objective.",
}


def build(trip_date: datetime.date) -> dict:
    """Score every question against every objective. Returns {qid: Counter}."""
    d = Path(__file__).resolve().parent.parent / "data"
    peaks = load_peaks(d / "peaks.csv", collections_path=d / "collections" / "sps.csv")
    permits = load_permits(d / "permits.csv", d / "release_policies.csv")
    regs = load_regulations(d / "regulations.csv")
    inputs = dict(
        trailheads=load_trailheads(d / "trailheads.csv"),
        permits=permits,
        approaches=load_approaches(d / "approaches.csv"),
        water_sources=load_water_sources(d / "water_sources.csv"),
        water_source_log=load_water_source_log(d / "water_source_log.csv"),
        advisories=load_advisories(d / "advisories.csv"),
        booking_channels=load_booking_channels(d / "booking_channels.csv"),
        campgrounds=load_campgrounds(d / "campgrounds.csv"),
        campsites=load_campsites(d / "campsites.csv"),
        park_access=list(load_park_access(d / "park_access.csv").values()),
    )

    scores = {q.qid: collections.Counter() for q in QUESTIONS}
    detail: dict = {q.qid: collections.defaultdict(list) for q in QUESTIONS}
    for peak in peaks:
        result = resolve_plan([peak.name], trip_date, peaks=peaks, **inputs)
        rule = permits.get(result.trailhead.permit_group) if result.trailhead else None
        applicable = (regulations_in_force(regs, rule, result.trailhead)
                      if result.trailhead else [])
        ctx = Ctx(result=result, rule=rule, regs=applicable)
        for q in QUESTIONS:
            verdict = q.proxy(ctx)
            scores[q.qid][verdict] += 1
            detail[q.qid][verdict].append(peak.name)
    return {"scores": scores, "detail": detail, "n": len(peaks)}


def format_report(built: dict) -> str:
    scores, n = built["scores"], built["n"]
    by_qid = {q.qid: q for q in QUESTIONS}
    out = [f"Wayproof scorecard -- {n} objectives", ""]
    out.append("Can the tool answer? (NOT whether the answer is right -- see module docstring)")
    out.append("")
    head = f"{'':5s} {'tier':>4s}  " + "".join(f"{v:>9s}" for v in VERDICTS) + "  question"
    out.append(head)
    out.append("-" * len(head))
    for q in QUESTIONS:
        c = scores[q.qid]
        row = f"{q.qid:5s} {q.tier or '-':>4}  " + "".join(f"{c[v] or '':>9}" for v in VERDICTS)
        out.append(f"{row}  {q.text}")

    # Structural rows score the same for every objective, so they are counted
    # once. Leaving 4 x 462 constant cells in the aggregate made `no-model` 24%
    # of it and buried every row that actually varies.
    varying = [q for q in QUESTIONS if not q.structural]
    structural = [q for q in QUESTIONS if q.structural]
    # `structural` means "constant for every objective"; NO_MODEL means "the
    # schema has no place for it". Those coincided until Q5 gained one and became
    # a constant DECLINED, so counting structural rows as schema gaps would now
    # overstate the gap by one. Verdict, not flag, decides.
    def _constant_verdict(q):
        seen = [v for v in VERDICTS if scores[q.qid][v]]
        return seen[0] if len(seen) == 1 else None
    no_model_qs = [q for q in structural if _constant_verdict(q) == NO_MODEL]
    total = sum(sum(scores[q.qid].values()) for q in varying)
    agg = collections.Counter()
    for q in varying:
        agg.update(scores[q.qid])
    out.append("")
    out.append(f"{len(varying)} objective-varying questions x {n} objectives = {total} cells")
    out.append("  " + "   ".join(f"{v} {agg[v]} ({100*agg[v]/total:.0f}%)"
                                 for v in VERDICTS if agg[v]))
    if structural:
        out.append("")
        out.append(f"+ {len(structural)} questions with the same verdict for every "
                   f"objective, of which {len(no_model_qs)} the schema cannot express at "
                   "all (counted once, not per objective):")
        for q in structural:
            out.append(f"    {q.qid} tier {q.tier}  [{_constant_verdict(q) or 'varies'}]  "
                       f"{q.text}")

    answered, declined = agg[ANSWERED], agg[DECLINED]
    if answered + declined:
        out.append("")
        out.append(f"calibration -- declined / (answered + declined) = "
                   f"{100*declined/(answered+declined):.0f}%")
        out.append("  Declining is a usable answer; this is how often it is the answer.")
        out.append("  Near 0% risks confident wrong answers. Near 100% is honest and unusable.")

    tier1 = [q for q in QUESTIONS if q.tier == 1 and not q.structural]
    out.append("")
    out.append("tier 1 -- 'getting these wrong costs you the trip':")
    for q in sorted(tier1, key=lambda q: scores[q.qid][ANSWERED]):
        out.append(f"    {q.qid} answered {scores[q.qid][ANSWERED]:4d} / {n}   {q.text}")
    worst = min((scores[q.qid][ANSWERED], q.qid) for q in tier1)
    out.append(f"  At most {worst[0]} objectives can have all {len(tier1)} answered, "
               f"bounded by {worst[1]}.")
    t1s = [q for q in QUESTIONS if q.tier == 1 and q.structural]
    if t1s:
        for q in t1s:
            verdict = _constant_verdict(q)
            why = ("until the schema changes" if verdict == NO_MODEL
                   else "for a plan that does not name one -- see its limit below")
            out.append(f"  {q.qid} is also tier 1 and scores {verdict} for every "
                       f"objective, so the real figure is 0 {why}.")

    out.append("")
    out.append("what each verdict asks of you:")
    for v in VERDICTS:
        if v == NO_MODEL:
            # Every no-model cell belongs to a structural question, and those are
            # counted once rather than per objective -- so the cell count here is
            # 0 and reads as "no schema gaps", which is the opposite of true.
            out.append(f"  {v:9s} {len(no_model_qs):5d}  {VERDICT_MEANING[v]} "
                       f"({len(no_model_qs)} whole questions, listed above)")
            continue
        if not agg[v]:
            continue
        out.append(f"  {v:9s} {agg[v]:5d}  {VERDICT_MEANING[v]}")

    limits = [q for q in QUESTIONS if q.limit]
    if limits:
        out.append("")
        out.append("where a proxy is weaker than its question:")
        for q in limits:
            out.append(f"  {q.qid}: {q.limit}")

    out.append("")
    out.append("README questions with no honest proxy:")
    for question, why in NOT_SCORED.items():
        out.append(f"  {question}\n       {why}")
    return "\n".join(out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--date", default="2027-07-15", help="Trip date to score against")
    p.add_argument("--by-question", metavar="QID",
                   help="List the objectives behind one question's verdicts")
    args = p.parse_args(argv)

    built = build(datetime.date.fromisoformat(args.date))
    if args.by_question:
        qid = args.by_question.upper()
        if qid not in built["detail"]:
            print(f"Unknown question {qid}. Known: {', '.join(built['detail'])}")
            return 2
        q = next(x for x in QUESTIONS if x.qid == qid)
        print(f"{qid} -- {q.text}\n  wrong if: {q.wrong_if}")
        if q.limit:
            print(f"  proxy limit: {q.limit}")
        for verdict in VERDICTS:
            names = built["detail"][qid][verdict]
            if names:
                print(f"\n{verdict} ({len(names)}): {', '.join(sorted(names)[:12])}"
                      f"{' ...' if len(names) > 12 else ''}")
        return 0

    print(format_report(built))
    return 0


if __name__ == "__main__":
    sys.exit(main())
