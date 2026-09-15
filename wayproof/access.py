"""Peak-specific approach relationships: which named route a peak is climbed
by, and which permit product actually governs that route.

A trailhead's ``permit_group`` (see :mod:`wayproof.permits`) is a useful
default, but it is not a guarantee for every peak reached from that
trailhead. Some trailheads serve more than one named approach, and different
approaches from the same trailhead can fall under different permit products.

Whitney Portal is the clearest example. The classic Mt. Whitney Trail is
subject to the lottery-only Whitney Zone permit. Mount Russell, though
reached from the same trailhead, is commonly climbed via the Mountaineers
Route / North Fork of Lone Pine Creek -- a separate trail that Inyo National
Forest explicitly excludes from the Whitney Zone lottery and instead governs
under the regular Inyo NF wilderness permit.

``data/approaches.csv`` records these peak-specific approach relationships as
first-class, sourced data rather than an opaque peak-name -> permit-group
patch:

- ``status=confirmed`` -- a directly-named source states this peak's real
  approach uses a different permit product than its trailhead's default.
  :func:`~wayproof.permits.clusters_permit_info` emits an extra,
  peak-specific permit entry for these.
- ``status=unconfirmed`` -- a different approach is plausible (for example,
  the dataset's own source-listed trailhead for the peak names a different
  trail than the trailhead's main route) but no source has been found
  confirming which permit product actually governs it. Rather than silently
  assuming the trailhead default applies, or silently omitting the peak,
  these surface as an explicit caution alongside the default permit entry.

This intentionally does not attempt to enumerate every peak's approach --
only the cases where trailhead-default inheritance is known or suspected to
be wrong. A peak absent from this file simply uses its trailhead's default
permit_group, with no caveat.

This is deliberately conservative: a peak should only appear here when there
is a concrete reason (a named alternate trail, a source, or both) to
question the trailhead default. Don't add speculative rows for peaks that
merely share a trailhead with a lottery/special permit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import pandas as pd

CONFIRMED = "confirmed"
UNCONFIRMED = "unconfirmed"
_VALID_STATUSES = {CONFIRMED, UNCONFIRMED}


@dataclass
class ApproachRoute:
    """One row of ``data/approaches.csv``: a peak's known (or suspected) approach.

    ``permit_group`` is the permit product this approach is confirmed to use.
    It is blank when ``status`` is ``unconfirmed`` -- the point of an
    unconfirmed row is to flag uncertainty, not to assert an unverified
    answer.
    """

    peak_name: str
    trailhead: str
    approach_name: str
    permit_group: str
    status: str
    source_url: str = ""
    verified_date: str = ""
    notes: str = ""

    @property
    def confirmed(self) -> bool:
        return self.status == CONFIRMED


def _str_field(row, col: str) -> str:
    val = row.get(col)
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()


def load_approaches(path: str | Path = "data/approaches.csv") -> List[ApproachRoute]:
    """Load known peak-specific approach relationships.

    Returns an empty list if the file doesn't exist -- approaches are opt-in
    extra precision layered on top of a trailhead's default permit_group, not
    a required input.
    """
    path = Path(path)
    if not path.exists():
        return []
    df = pd.read_csv(path)

    routes: List[ApproachRoute] = []
    for _, row in df.iterrows():
        peak_name = _str_field(row, "peak_name")
        if not peak_name:
            continue
        status = _str_field(row, "status") or CONFIRMED
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"Invalid approach status {status!r} for {peak_name!r}; "
                f"expected one of {sorted(_VALID_STATUSES)}"
            )
        routes.append(ApproachRoute(
            peak_name=peak_name,
            trailhead=_str_field(row, "trailhead"),
            approach_name=_str_field(row, "approach_name"),
            permit_group=_str_field(row, "permit_group"),
            status=status,
            source_url=_str_field(row, "source_url"),
            verified_date=_str_field(row, "verified_date"),
            notes=_str_field(row, "notes"),
        ))
    return routes


def approaches_by_peak(routes: Sequence[ApproachRoute]) -> Dict[str, List[ApproachRoute]]:
    """Index approach routes by peak name (a peak may have more than one known approach)."""
    by_peak: Dict[str, List[ApproachRoute]] = {}
    for r in routes:
        by_peak.setdefault(r.peak_name, []).append(r)
    return by_peak


# -- how an objective's entry point was resolved -----------------------------
#
# `plan` reports the permit that governs an objective, and that answer is only
# as good as the objective -> entry-point link behind it. Today that link is
# `Peak.meta["nearest_trailhead"]`, a straight-line assignment computed by
# scripts/assign_trailheads.py -- the same field wayproof.views labels
# "UNVERIFIED: assigned by straight-line proximity, not by a confirmed approach
# relationship". Stating a permit off it while printing a verification date
# underneath is the one claim this project must not make loosely.
#
# There is a second, sourced signal already in the dataset: the collection's own
# route name (`Peak.meta["trailhead"]`, which despite the column name holds a
# TRAIL name -- "Shepherd Pass Trail", "Pacific Crest Trail" -- not an entry
# point). Comparing the two cannot establish the right answer, but it can tell
# the three cases apart: the sourced route agrees, the sourced route names
# somewhere else, or nothing sourced has an opinion.
#
# This is deliberately a stopgap. The real fix is data/entry_trails.csv, keyed
# on the agency's own quota unit; the counts these states produce are the
# burn-down measure for building it.

ENTRY_SOURCED = "sourced"
"""data/approaches.csv confirms which route and permit govern this objective."""

ENTRY_ROUTE_CONSISTENT = "route_consistent"
"""The collection's sourced route name resolves to the trailhead in use."""

ENTRY_CONTRADICTED = "contradicted"
"""The sourced route resolves to a DIFFERENT trailhead than the one in use."""

ENTRY_CORRIDOR = "corridor"
"""The sourced route is a long-distance corridor (PCT, JMT) with no single
entry point. Not a defect in the data -- the objective genuinely has no one
trailhead, and resolving it needs an explicit entry/exit pair."""

ENTRY_INFERRED = "inferred"
"""Straight-line proximity only: no sourced route, or one that resolves to no
trailhead this project holds."""

#: Long-distance corridors, which have no single entry point. Normalised forms.
ENTRY_CORRIDORS = frozenset({
    "pacific crest", "john muir", "high sierra", "sierra high route", "tahoe rim",
})

# Words that distinguish a trail from its entry point rather than naming either.
_ROUTE_NOISE = re.compile(r"\b(trail|trailhead|th|road|rd)\b")
_PARENTHETICAL = re.compile(r"\(([^)]*)\)")


def normalise_entry_name(name: str) -> str:
    """Fold a trail or trailhead name to a comparable key.

    Drops parentheticals and the words that name the *kind* of thing rather
    than the place, so "Shepherd Pass Trail" and "Shepherd Pass" agree.
    """
    stripped = _PARENTHETICAL.sub(" ", str(name or ""))
    folded = _ROUTE_NOISE.sub(" ", stripped.strip().lower())
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def trailhead_name_index(names: Sequence[str]) -> Dict[str, set]:
    """``{normalised form: {trailhead names}}``, for resolving a route name.

    A trailhead is indexed under its own name *and* under each parenthetical,
    because the parenthetical is usually the trail: "Onion Valley (Kearsarge
    Pass)" is what a route called "Kearsarge Pass Trail" reaches. A form
    reaching more than one trailhead is ambiguous and callers must not resolve
    it -- hence a set, not a name.
    """
    index: Dict[str, set] = {}
    for name in names:
        forms = {normalise_entry_name(name)}
        forms.update(normalise_entry_name(p) for p in _PARENTHETICAL.findall(name))
        for form in forms:
            if form:
                index.setdefault(form, set()).add(name)
    return index


@dataclass
class EntryResolution:
    """How one objective's entry point was arrived at, and on what evidence.

    Rendered by :mod:`wayproof.plan` so a reader can tell a sourced answer from
    a geometric guess without reading the source data themselves.
    """

    peak_name: str
    basis: str
    trailhead: str
    """The entry point actually in use -- what the permit was resolved from."""
    sourced_route: str = ""
    """The collection's own route name, verbatim, when it has one."""
    sourced_trailhead: str = ""
    """Where that route resolves, set only when ``basis`` is
    ``contradicted`` or ``route_consistent``."""

    @property
    def confirmed(self) -> bool:
        """Whether a source, rather than geometry, established this entry."""
        return self.basis in (ENTRY_SOURCED, ENTRY_ROUTE_CONSISTENT)

    def to_dict(self) -> dict:
        d = {"peak_name": self.peak_name, "basis": self.basis,
             "trailhead": self.trailhead, "confirmed": self.confirmed}
        if self.sourced_route:
            d["sourced_route"] = self.sourced_route
        if self.sourced_trailhead:
            d["sourced_trailhead"] = self.sourced_trailhead
        return d


def classify_entry(
    peak,
    trailhead_name: str,
    trailhead_index: Dict[str, set],
    approaches: Sequence[ApproachRoute] = (),
) -> EntryResolution:
    """Decide how ``peak``'s entry point was established.

    Conservative in both directions: a route that resolves to no trailhead, or
    to more than one, is reported as ``inferred`` rather than guessed either
    way. Only an exact match on the normalised form claims agreement or
    disagreement.

    An ``unconfirmed`` row in ``data/approaches.csv`` does not count as sourced
    -- that is the point of the status -- so it falls through to the route
    comparison. The permit report raises its own ``UNCERTAIN`` caution for it
    separately.
    """
    def resolution(basis, **kw):
        return EntryResolution(peak_name=peak.name, basis=basis,
                               trailhead=trailhead_name, **kw)

    for route in approaches:
        if route.peak_name == peak.name and route.confirmed and (
                not route.trailhead or route.trailhead == trailhead_name):
            return resolution(ENTRY_SOURCED, sourced_route=route.approach_name)

    sourced_route = str(peak.meta.get("trailhead", "") or "").strip()
    if not sourced_route:
        return resolution(ENTRY_INFERRED)

    key = normalise_entry_name(sourced_route)
    if key in ENTRY_CORRIDORS:
        return resolution(ENTRY_CORRIDOR, sourced_route=sourced_route)

    matches = trailhead_index.get(key, set())
    if len(matches) != 1:
        return resolution(ENTRY_INFERRED, sourced_route=sourced_route)

    resolved = next(iter(matches))
    if resolved == trailhead_name:
        return resolution(ENTRY_ROUTE_CONSISTENT, sourced_route=sourced_route,
                          sourced_trailhead=resolved)
    return resolution(ENTRY_CONTRADICTED, sourced_route=sourced_route,
                      sourced_trailhead=resolved)
