"""Resolve trip logistics for a specific, named set of objectives.

Unlike the experimental geographic clustering pipeline
(:mod:`wayproof.clustering` / :mod:`wayproof.tsp`), this module does
not discover or group objectives -- it assumes the user already knows what
they want to do (e.g. "Mount Williamson and Mount Tyndall") and answers: what
access applies, what permit governs it, when do you need to act, and what
evidence backs the answer?

Almost nothing here is new domain logic. :func:`resolve_plan` looks the named
objectives up, picks their shared trailhead with
:func:`wayproof.approach.choose_trailhead`, wraps them in a single-use
:class:`~wayproof.model.Cluster`, and hands that to
:func:`wayproof.permits.clusters_permit_info` -- reusing the approach
override/uncertainty handling and computable release-rule dates already
built for the clustering pipeline, rather than duplicating any of it.

Current scope, deliberately: a plan's objectives must share a single
trailhead, the same assumption already made everywhere else access is
modeled in this project (a ``Cluster`` has exactly one ``trailhead``).
Objectives that don't share one aren't rejected -- ``resolve_plan`` still
picks its best guess and reports the mismatch as a warning rather than
silently trusting it. A loop or point-to-point traverse with a genuinely
different entry and exit (e.g. an Evolution Loop-style objective) needs an
explicit entry/exit pair, which is a natural additive extension, not
something this module models yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Sequence

from .access import ApproachRoute
from .camping import Campground, Campsite
from .model import Cluster, Peak, Trailhead
from .approach import EntryConflict, choose_trailhead, entry_conflicts
from .data_loader import resolve_peak_name
from .park_access import ParkAccess
from .permits import (
    ClusterPermitInfo,
    PermitRule,
    clusters_permit_info,
    format_permit_entry_body,
)
from .regulations import Regulation, group_by_category, regulations_for
from .reports import OpenQuestion, open_questions
from .water import WaterSource, WaterSourceLogEntry, latest_status_by_source


@dataclass
class FacilitiesInfo:
    """What IS known about the resolved trailhead's nearby facilities --
    the counterpart to ``PlanResult.open_questions``, which is what isn't.

    Linked to the trailhead via ``Trailhead.park`` (campgrounds/park_access)
    and exact ``WaterSource.location`` match (water sources) -- the same
    conservative linking :func:`wayproof.reports.open_questions` uses, so a
    trailhead with no known ``park`` (most Sierra trailheads today) simply
    gets no campground/park-access facts here, rather than a guessed one.
    """

    water_sources: List[WaterSource] = field(default_factory=list)
    water_status: Dict[str, WaterSourceLogEntry] = field(default_factory=dict)
    campgrounds: List[Campground] = field(default_factory=list)
    campsites: List[Campsite] = field(default_factory=list)
    park_access: Optional[ParkAccess] = None


@dataclass
class PlanResult:
    """The resolved logistics for a specific, named set of objectives."""

    requested_names: List[str]
    objectives: List[Peak]
    not_found: List[str]
    trip_date: date
    trailhead: Optional[Trailhead]
    trailhead_ambiguous: bool
    entry_conflicts: List[EntryConflict] = field(default_factory=list)
    """Objectives whose sourced route contradicts the trailhead geometry chose.

    Non-empty means this project cannot say which entry point governs, so the
    permit below is a candidate rather than an answer.
    """
    permit_entries: List[ClusterPermitInfo] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    open_questions: List[OpenQuestion] = field(default_factory=list)
    facilities: Optional[FacilitiesInfo] = None
    regulations: List[Regulation] = field(default_factory=list)
    """What applies once you hold the permit, resolved across all four scopes.

    The project has held these since the regulations refactor and the website
    has rendered them since; `plan` did not, so the flagship command omitted the
    Desolation bear-canister requirement -- a $5,000 fine under 36 CFR
    261.58(cc) -- for every objective. Held data the surface hides is worse than
    data nobody entered: nothing signals the gap.
    """
    costs: List["CostComponent"] = field(default_factory=list)
    """Every component of this trip that may charge, permit and otherwise.

    The permit's own fee is one of these, not the trip's cost. Reporting it as
    the cost is what made a $97 trip read as free."""

    def to_dict(self) -> dict:
        d: dict = {
            "requested_objectives": self.requested_names,
            "trip_date": self.trip_date.isoformat(),
            "objectives": [p.to_dict() for p in self.objectives],
        }
        if self.not_found:
            d["not_found"] = self.not_found
        if self.trailhead:
            d["trailhead"] = {
                "name": self.trailhead.name,
                "side": self.trailhead.side,
                "wilderness_area": self.trailhead.wilderness_area,
                "land_agency": self.trailhead.land_agency,
            }
            d["trailhead_ambiguous"] = self.trailhead_ambiguous
            # The JSON must carry this too. The site already had a bug where
            # the machine surface said "unverified" and the human surfaces
            # said nothing; the reverse would be worse, since an agent acting
            # on this cannot see the warning text.
            d["entry_point_resolved"] = not self.entry_conflicts
            # An agent must be able to see that the other end is MISSING, rather
            # than infer from its absence that there isn't one. "unknown" is the
            # honest value: not "out_and_back", which is the common shape and so
            # the tempting default -- the same mistake as a blank fee reading as
            # free. When route shape is modelled these two become derived.
            d["route_shape"] = "unknown"
            d["exit_modelled"] = False
            if self.entry_conflicts:
                d["entry_conflicts"] = [
                    {"peak": c.peak_name, "sourced_route": c.sourced_route,
                     "computed_trailhead": c.computed_trailhead}
                    for c in self.entry_conflicts
                ]
        if self.costs:
            charging = [c for c in self.costs if c.status == CHARGES]
            unknown = [c for c in self.costs if c.status == UNKNOWN]
            # An agent reading this must be able to answer "is this free" without
            # parsing prose, and must not get "yes" from a missing fee.
            d["cost"] = {
                "free": not charging and not unknown,
                "charges": bool(charging),
                "has_unpriced_component": bool(unknown),
                "totalled": False,
                "components": [c.to_dict() for c in self.costs],
            }
        if self.regulations:
            d["regulations"] = [
                {"label": label,
                 "rules": [{"id": r.regulation_id, "category": r.category,
                            "summary": r.summary, "citation": r.citation,
                            "scope": r.scope_label, "inherited": r.inherited,
                            "source_url": r.source_url} for r in items]}
                for label, items in group_by_category(self.regulations)
            ]
        d["permits"] = [
            {
                "agency": e.agency,
                "wilderness_area": e.wilderness_area,
                "permit_type": e.permit_type,
                "status": e.status,
                "fee_notes": e.fee_notes,
                "apply_url": e.apply_url,
                "notes": e.notes,
                "interagency_note": e.interagency_note,
                "peak_note": e.peak_note,
                "approach_name": e.approach_name,
                "approach_status": e.approach_status,
                "source_last_updated": e.source_last_updated,
                "verified_date": e.verified_date,
            }
            for e in self.permit_entries
        ]
        if self.warnings:
            d["warnings"] = self.warnings
        if self.open_questions:
            d["open_questions"] = [
                {"target_file": q.target_file, "target_key": q.target_key,
                 "question": q.question, "context": q.context}
                for q in self.open_questions
            ]
        if self.facilities:
            fac = self.facilities
            facilities_d: dict = {}
            if fac.water_sources:
                facilities_d["water_sources"] = [
                    {
                        "name": w.name,
                        "type": w.type,
                        "potable": w.potable,
                        "status": (fac.water_status[w.name].observed_status
                                   if w.name in fac.water_status else None),
                        "status_checked_date": (fac.water_status[w.name].checked_date
                                                 if w.name in fac.water_status else None),
                        "status_source": (fac.water_status[w.name].source
                                          if w.name in fac.water_status else None),
                    }
                    for w in fac.water_sources
                ]
            if fac.campgrounds:
                facilities_d["campgrounds"] = [
                    {
                        "name": c.name,
                        "reservation_method": c.reservation_method,
                        "reservation_contact": c.reservation_contact,
                        "fee_notes": c.fee_notes,
                        "nightly_entry_cutoff": c.nightly_entry_cutoff,
                        "campsites": [
                            {"name": s.name, "capacity": s.capacity,
                             "water_proximity": s.water_proximity,
                             "restroom_proximity": s.restroom_proximity}
                            for s in fac.campsites if s.campground == c.name
                        ],
                    }
                    for c in fac.campgrounds
                ]
            if fac.park_access:
                pa = fac.park_access
                facilities_d["park_access"] = {
                    "park": pa.park,
                    "entrance_fee": pa.entrance_fee,
                    "fee_conditions": pa.fee_conditions,
                    "fee_exemptions": pa.fee_exemptions,
                    "gate_open": pa.gate_open,
                    "gate_close": pa.gate_close,
                    "gate_hours_conditions": pa.gate_hours_conditions,
                }
            if facilities_d:
                d["facilities"] = facilities_d
        return d


def resolve_plan(
    objective_names: Sequence[str],
    trip_date: date,
    peaks: Sequence[Peak],
    trailheads: Sequence[Trailhead],
    permits: Dict[str, PermitRule],
    approaches: Optional[Sequence[ApproachRoute]] = None,
    water_sources: Optional[Sequence[WaterSource]] = None,
    water_source_log: Optional[Sequence[WaterSourceLogEntry]] = None,
    campgrounds: Optional[Sequence[Campground]] = None,
    campsites: Optional[Sequence[Campsite]] = None,
    park_access: Optional[Sequence[ParkAccess]] = None,
    regulations: Optional[Sequence[Regulation]] = None,
    today: Optional[date] = None,
) -> PlanResult:
    """Resolve access and permit logistics for a specific, named set of objectives.

    Objective names are matched case-insensitively against ``peaks``. A name
    that doesn't match anything is reported in ``PlanResult.not_found``
    rather than raising -- a plan for a partially-known trip is more useful
    than none.

    ``water_sources``/``water_source_log``/``campgrounds``/``campsites``/
    ``park_access`` are optional; when given, they feed two different things:
    :func:`wayproof.reports.open_questions` derives ``PlanResult.open_questions``
    -- unconfirmed or missing facts relevant to these specific objectives,
    e.g. "we don't have coordinates for this trailhead's water source yet"
    (the scavenger-hunt nudge, shown exactly when someone is already
    planning to be at that location) -- while ``PlanResult.facilities``
    holds what IS already known and confirmed (a water source's last-checked
    status, a nearby campground's reservation method, the park's entrance
    fee), linked to the resolved trailhead the same conservative way.
    """
    objectives: List[Peak] = []
    not_found: List[str] = []
    ambiguous: Dict[str, List[str]] = {}
    for name in objective_names:
        # Not a plain lowercase lookup: peaks.csv keys on the source list's own
        # formatting, so "Mount Carillon" (the GNIS spelling), "Duane Bliss
        # Peak" (stored with a trailing emblem marker) and "Mount Whitney"
        # (stored ALLCAPS) all used to return nothing.
        peak, candidates = resolve_peak_name(name, peaks)
        if peak is not None:
            objectives.append(peak)
        elif candidates:
            ambiguous[name] = candidates
        else:
            not_found.append(name)

    warnings: List[str] = [
        f"Objective not found in peak data: {name!r}" for name in not_found
    ]
    for name, candidates in ambiguous.items():
        warnings.append(
            f"{name!r} matches more than one peak: {', '.join(candidates)}. "
            "Name the one you mean -- these are different summits, and picking "
            "for you is how you end up planning the wrong trip."
        )

    trailhead: Optional[Trailhead] = None
    trailhead_ambiguous = False
    conflicts: List[EntryConflict] = []
    permit_entries: List[ClusterPermitInfo] = []

    if objectives:
        trailhead = choose_trailhead(objectives, trailheads)

        nearest_names = {
            str(p.meta["nearest_trailhead"]).strip()
            for p in objectives
            if p.meta.get("nearest_trailhead") and str(p.meta["nearest_trailhead"]).strip()
        }
        # A single objective whose OWN sourced route contradicts the geometry
        # used to be silent: `trailhead_ambiguous` only fires when objectives
        # disagree with each other. That silence is what let this tool answer
        # "Mineral King, SEKI permit" for a peak its own data routes over
        # Shepherd Pass on the far side of the crest.
        conflicts = entry_conflicts(objectives, trailhead)
        for conflict in conflicts:
            warnings.append(
                f"UNRESOLVED ENTRY POINT -- {conflict} This project has no sourced row "
                "linking this objective to an entry point, so the permit below follows "
                "geometry and is NOT verified. Confirm the approach before booking."
            )

        trailhead_ambiguous = len(nearest_names) > 1
        if trailhead_ambiguous:
            warnings.append(
                "Objectives do not share the same default trailhead "
                f"({', '.join(sorted(nearest_names))}) -- this plan assumes a single "
                f"shared entry point ({trailhead.name if trailhead else 'none found'}); "
                "verify access independently before relying on this."
            )

        if trailhead is None:
            warnings.append("No trailhead data available -- cannot resolve permit logistics.")
        else:
            cluster = Cluster(
                cluster_id=0, peaks=list(objectives),
                trailhead=trailhead.name, trailhead_side=trailhead.side,
            )
            permit_entries = clusters_permit_info(
                [cluster], trailheads, permits, trip_date, today, approaches=approaches,
            )
            if not permit_entries:
                warnings.append(
                    f"No permit data found for trailhead {trailhead.name!r} "
                    f"(permit_group {trailhead.permit_group!r})."
                )

    questions: List[OpenQuestion] = []
    if objectives:
        questions = open_questions(
            peaks=objectives,
            approaches=approaches or [],
            water_sources=water_sources or [],
            water_source_log=water_source_log or [],
            campgrounds=campgrounds or [],
            campsites=campsites or [],
            trailheads=trailheads,
            park_access=park_access or [],
            peak_names=[p.name for p in objectives],
        )

    facilities: Optional[FacilitiesInfo] = None
    if trailhead is not None:
        ws = [w for w in (water_sources or [])
              if w.location and w.location.strip() == trailhead.name]
        water_status = {
            name: entry for name, entry in latest_status_by_source(water_source_log or []).items()
            if name in {w.name for w in ws}
        }
        cgs = ([c for c in (campgrounds or []) if c.park == trailhead.park]
               if trailhead.park else [])
        cg_names = {c.name for c in cgs}
        sites = [s for s in (campsites or []) if s.campground in cg_names]
        pa = next((p for p in (park_access or []) if trailhead.park and p.park == trailhead.park),
                  None)
        if ws or cgs or sites or pa:
            facilities = FacilitiesInfo(
                water_sources=ws, water_status=water_status,
                campgrounds=cgs, campsites=sites, park_access=pa,
            )

    applicable: List[Regulation] = []
    if trailhead is not None and regulations:
        rule = permits.get(trailhead.permit_group)
        if rule is not None:
            applicable = regulations_for(regulations, rule.permit_group, rule.agency_ids,
                                         rule.jurisdiction, rule.wilderness_area)

    costs = trip_costs(permit_entries, facilities, entry_unresolved=bool(conflicts))

    return PlanResult(
        requested_names=list(objective_names),
        objectives=objectives,
        not_found=not_found,
        trip_date=trip_date,
        trailhead=trailhead,
        trailhead_ambiguous=trailhead_ambiguous,
        entry_conflicts=conflicts,
        permit_entries=permit_entries,
        warnings=warnings,
        open_questions=questions,
        facilities=facilities,
        regulations=applicable,
        costs=costs,
    )


def format_plan_summary(result: PlanResult) -> str:
    """Render a :class:`PlanResult` as a human-readable trip summary."""
    lines: List[str] = []
    title = " + ".join(p.name for p in result.objectives) or " + ".join(result.requested_names)
    lines.append(title.upper() if result.objectives else title)
    lines.append(f"Trip date: {result.trip_date:%Y-%m-%d}")
    lines.append("")

    if result.not_found:
        lines.append(f"Not found in peak data: {', '.join(result.not_found)}")
        lines.append("")

    if not result.objectives:
        lines.append("No objectives resolved -- nothing to plan.")
        return "\n".join(lines)

    lines.append("Access")
    if result.trailhead:
        side = f"  ({result.trailhead.side} side)" if result.trailhead.side else ""
        if result.entry_conflicts:
            # Lead with the doubt. Printing the trailhead first and the caveat
            # afterwards is how a reader ends up acting on the headline and
            # skimming the qualifier.
            lines.append("  ENTRY POINT UNRESOLVED -- sources disagree, see below.")
            lines.append(f"  Geometry suggests: {result.trailhead.name}{side}")
            for conflict in result.entry_conflicts:
                lines.append(f"  Sourced route for {conflict.peak_name}: "
                             f"{conflict.sourced_route}")
            lines.append("  These may be different entry points under different agencies, "
                         "which would mean a different permit entirely.")
        else:
            lines.append(f"  Trailhead: {result.trailhead.name}{side}")
        # Said out loud because the assumption is invisible otherwise, and it is
        # load-bearing: docs/user_stories/ohlone-traverse-2026-09.md S1 is a real
        # trip whose two ends were 29 miles apart in different park units, and
        # permits.py rests its reciprocity conclusion on "the single-trailhead
        # loop trips this tool plans". Stating the assumption is NOT a claim
        # about the shape of the caller's route -- that is not in the dataset.
        lines.append("  MODELS ONE END ONLY: this plan assumes you start and finish here. "
                     "Route shape (out-and-back, loop, one-way) is not in this dataset, so "
                     "that is an assumption, not a finding about your route. If yours is "
                     "one-way, the other end is absent from everything below -- its parking, "
                     "entrance fee and access hours are not in Cost, and the permit reasoning "
                     "assumes continuous travel from this one trailhead.")
    else:
        lines.append("  No trailhead data available.")
    lines.append("")

    cost_lines = format_costs(result.costs)
    if cost_lines:
        lines.extend(cost_lines)
        lines.append("")

    if result.facilities:
        fac = result.facilities
        lines.append("Facilities")
        if fac.water_sources:
            lines.append(f"  Water sources at {result.trailhead.name}:")
            for w in fac.water_sources:
                status = fac.water_status.get(w.name)
                if status:
                    lines.append(f"    - {w.name}: {status.observed_status} "
                                 f"(checked {status.checked_date})")
                else:
                    lines.append(f"    - {w.name}: no availability check on file")
        for c in fac.campgrounds:
            lines.append(f"  Campground: {c.name}")
            if c.reservation_method:
                lines.append(f"    Reservation: {c.reservation_method}")
            if c.fee_notes:
                lines.append(f"    Fee: {c.fee_notes}")
            if c.nightly_entry_cutoff:
                lines.append(f"    Nightly entry cutoff: {c.nightly_entry_cutoff}")
            sites = [s for s in fac.campsites if s.campground == c.name]
            if sites:
                lines.append(f"    Sites: {', '.join(f'{s.name} ({s.capacity})' for s in sites)}")
        if fac.park_access:
            pa = fac.park_access
            lines.append(f"  Park access ({pa.park}):")
            if pa.entrance_fee:
                cond = f" ({pa.fee_conditions})" if pa.fee_conditions else ""
                lines.append(f"    Entrance fee: {pa.entrance_fee}{cond}")
            if pa.gate_open or pa.gate_close:
                cond = f" ({pa.gate_hours_conditions})" if pa.gate_hours_conditions else ""
                lines.append(f"    Gate hours: {pa.gate_open}-{pa.gate_close}{cond}")
            if pa.fee_exemptions:
                lines.append(f"    Fee exemptions: {pa.fee_exemptions}")
        lines.append("")

    if result.entry_conflicts:
        lines.append("Permit (CANDIDATE ONLY -- follows the unresolved entry point above)")
        lines.append("  The verification dates below belong to the permit rule, not to the "
                     "claim that this permit governs your route. Do not read them as "
                     "confirming the entry point.")
    else:
        lines.append("Permit")
    if result.permit_entries:
        for e in result.permit_entries:
            if e.peak_note:
                lines.append(f"  [{e.peak_note}]")
            lines.extend(format_permit_entry_body(e))
            lines.append("")
    else:
        lines.append("  No permit data resolved for this trailhead.")
        lines.append("")

    if result.regulations:
        lines.append("Rules in force")
        lines.append("  What applies once you hold the permit. A rule scoped to anything "
                     "other than")
        lines.append("  this permit is inherited -- state law, a wilderness rulebook or an "
                     "agency")
        lines.append("  policy -- and applies to other permits in the same scope too.")
        for label, items in group_by_category(result.regulations):
            lines.append(f"  {label}")
            for rule in items:
                bits = [rule.summary]
                if rule.citation:
                    bits.append(f"({rule.citation})")
                if rule.inherited:
                    bits.append(f"[{rule.scope_label}]")
                lines.append(f"    - {' '.join(bits)}")
        lines.append("  Summaries only. Each rule's full text, source and last check are "
                     "published per trailhead.")
        lines.append("")

    lines.append("Known per-objective mileage (official round trip, from source data)")
    any_known = False
    for p in result.objectives:
        mileage = p.meta.get("mileage_rt")
        gain = p.meta.get("gain_ft")
        if mileage:
            any_known = True
            gain_str = f", {int(gain):,} ft gain" if gain else ""
            lines.append(f"  {p.name}: {mileage} mi round trip{gain_str}")
        else:
            lines.append(f"  {p.name}: no official mileage on file")
    if any_known:
        lines.append(
            "  These are each objective's own official round-trip stats from its "
            "standard trailhead -- not a computed combined route. Whether they can "
            "reasonably be linked into one continuous trip is not modeled here; "
            "treat as reference points, not a verified itinerary."
        )
        if result.entry_conflicts:
            # Picket Guard Peak reported 23.2 mi beside a Mineral King trailhead;
            # that figure is measured from Shepherd Pass. Two inconsistent facts
            # in one output, and the mileage looked like it corroborated the
            # trailhead above it.
            lines.append(
                "  NOTE: that standard trailhead is the one in each objective's source "
                "data, which is exactly what the entry point above is unresolved about. "
                "These distances are probably NOT measured from the trailhead named above."
            )
    lines.append("")

    if result.warnings:
        lines.append("Warnings")
        for w in result.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    if result.open_questions:
        lines.append("Help us confirm (if you're going, and you check, please report back)")
        for q in result.open_questions:
            lines.append(f"  - {q.question}")
        lines.append("")

    lines.append(
        "Planning aid, not a booking guarantee -- verify the current rule at the "
        "official source before acting on any date above."
    )
    return "\n".join(lines)


# -- what the trip actually costs -------------------------------------------
#
# The permit block carried a line reading "Fee: <permit fee>", and for a trip
# whose permit is free that rendered as "Fee: Free" -- above a campground fee,
# in a plan for a trip that charged $97. See
# docs/user_stories/ohlone-traverse-2026-09.md, S2: "This trip cost $97 and the
# tool says free." It is the only finding in that document that harms someone
# today, and it is a presentation defect: every figure below is already in the
# dataset, on three different rows nobody was adding up.

CHARGES = "charges"
FREE = "free"
UNKNOWN = "unknown"

_CURRENCY = re.compile(r"\$\s?\d")
_FREE_PHRASES = ("free", "no fee", "no charge", "no cost")


def fee_status(text: str) -> str:
    """Whether a fee field charges, is free, or says nothing at all.

    Three-valued for the same reason :mod:`wayproof.evidence`'s status is: a
    blank fee is **unknown**, and rendering unknown as free is exactly how a
    paid trip reports as costing nothing. Del Valle Family Campground carries
    no ``fee_notes`` and charged $43.

    A currency amount outranks the word "free", because a row can say both.
    ``cpma``'s fee reads "No fee for the wilderness permit itself. PARKING,
    June 1 - October 31 ... $5.00 per day" -- a free permit is not a free trip.
    """
    body = str(text or "").strip()
    if not body:
        return UNKNOWN
    if _CURRENCY.search(body):
        return CHARGES
    if any(phrase in body.lower() for phrase in _FREE_PHRASES):
        return FREE
    return UNKNOWN


@dataclass
class CostComponent:
    """One thing that may charge for this trip, and what the source says."""

    kind: str          # "permit" | "campground" | "park_entrance"
    label: str
    status: str        # CHARGES | FREE | UNKNOWN
    detail: str = ""   # the source's own wording, verbatim -- never parsed into a number
    conditions: str = ""
    provisional: bool = False
    """True when this component hangs off an unresolved entry point.

    A permit that is only a candidate has a fee that is only a candidate. The
    entry-point doubt has to propagate into the cost, or the cost reads as
    settled while the thing it prices does not."""

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "label": self.label, "status": self.status,
             "provisional": self.provisional}
        if self.detail:
            d["detail"] = self.detail
        if self.conditions:
            d["conditions"] = self.conditions
        return d


def trip_costs(
    permit_entries: Sequence[ClusterPermitInfo],
    facilities: Optional[FacilitiesInfo],
    entry_unresolved: bool = False,
) -> List[CostComponent]:
    """Every chargeable component of this trip, from data already resolved.

    Deliberately does NOT total them. The figures are prose written by three
    different operators in three different shapes ("$15/night per site + $8
    non-refundable reservation service fee", "$6/permit + $5/person", "$10"),
    and a number computed from those would be false precision of exactly the
    kind this project refuses elsewhere. Naming every component that charges is
    the answer; adding them up is not.
    """
    out: List[CostComponent] = []
    seen = set()

    for entry in permit_entries:
        key = (entry.permit_type, entry.fee_notes)
        if key in seen:
            continue  # the same rule can appear twice (default + an approach caution)
        seen.add(key)
        out.append(CostComponent("permit", entry.permit_type,
                                 fee_status(entry.fee_notes), entry.fee_notes,
                                 provisional=entry_unresolved))

    if facilities:
        for campground in facilities.campgrounds:
            out.append(CostComponent("campground", campground.name,
                                     fee_status(campground.fee_notes),
                                     campground.fee_notes))
        park = facilities.park_access
        if park:
            out.append(CostComponent("park_entrance", park.park,
                                     fee_status(park.entrance_fee),
                                     park.entrance_fee, park.fee_conditions))
    return out


_COST_KIND_LABELS = {"permit": "Permit", "campground": "Campground",
                     "park_entrance": "Park entrance"}


def format_costs(costs: Sequence[CostComponent]) -> List[str]:
    """Render the cost section, leading with whether the trip is free.

    Follows the entry-conflict precedent above: state the doubt first. A reader
    who sees a component charge and then reads the detail has the right answer;
    one who sees "Free" and skims the rest does not.
    """
    if not costs:
        return []
    charging = [c for c in costs if c.status == CHARGES]
    unknown = [c for c in costs if c.status == UNKNOWN]

    lines = ["Cost"]
    if charging:
        if len(costs) == 1:
            lines.append("  THIS TRIP IS NOT FREE -- the one component on file "
                         "carries a fee.")
        else:
            lines.append(f"  THIS TRIP IS NOT FREE -- {len(charging)} of "
                         f"{len(costs)} components carry a fee.")
    elif unknown:
        lines.append("  COST UNKNOWN -- nothing on file charges, but "
                     f"{len(unknown)} of {len(costs)} components have no fee "
                     "recorded at all.")
    else:
        lines.append("  No component on file charges a fee.")

    for c in costs:
        head = f"  {_COST_KIND_LABELS.get(c.kind, c.kind)} ({c.label}): "
        if c.status == UNKNOWN:
            lines.append(f"{head}NO FEE ON FILE -- absent is not free, and must "
                         "be confirmed with the operator.")
            continue
        detail = c.detail
        if c.conditions:
            detail += f" ({c.conditions})"
        if c.provisional:
            detail += "  [CANDIDATE -- priced from the unresolved entry point above]"
        lines.append(f"{head}{detail}")

    if charging:
        lines.append("  Not totalled: these are separate charges, in prose, from "
                     "different operators. Add them yourself against each source.")
    return lines
