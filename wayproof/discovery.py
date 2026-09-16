"""Finding a campground you cannot already name.

``plan.py`` answers questions about a *named* objective. That is the whole
interface, and it assumes the hard part is already done: you know the place
exists and you know what it is called. Someone choosing where to go knows
neither.

This module is the other direction -- filter the campgrounds by the things a
person actually decides on (can I drive to it, what class of site is it, how
far is it from home) and return what survives.

Two rules shape all of it, and both come from mistakes this dataset has
already made.

**A filter must not turn a gap into an answer.** ``drive_in()`` excludes a
blank ``access_mode`` because blank is not evidence of a road -- but a person
reading a list of three does not see the twenty-one that were never checked.
Every function here returns what it could not place alongside what it could,
and :func:`format_campground_list` prints both. The failure being avoided is
the one the scorecard names for Q21: not being able to tell "nothing is near
you" from "nobody has looked".

**A distance must say what it is a distance to.** Every coordinate in this
project came off a park's overview page, so it locates the PARK. Dumbarton
Quarry sits inside Coyote Hills Regional Park with its own entrance miles
round the marsh; the park's coordinate would put it somewhere it is not.
:class:`CampgroundMatch` carries the precision alongside the number so the
rendering can say so, and the number is straight-line -- no road network is
modelled here, and a bay or a ridge between you and a park makes the drive
much longer than the line.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .camping import (
    COORD_PRECISION_LABELS, Campground, access_label, coord_precision_label,
)
from .distances import haversine_miles

STRAIGHT_LINE = ("straight-line, not driving -- no road network is modelled "
                 "here, and a bay or a ridge makes the drive longer")


@dataclass
class CampgroundMatch:
    """A campground that passed the filters, with its distance if one exists."""

    campground: Campground
    distance_miles: Optional[float] = None
    """``None`` when no reference point was given, never when one was: an
    unplaceable campground goes in :attr:`CampgroundSearch.unplaced` instead."""

    @property
    def distance_basis(self) -> str:
        return coord_precision_label(self.campground)


@dataclass
class CampgroundSearch:
    """What a search found, and what it could not judge."""

    matches: List[CampgroundMatch]
    unplaced: List[Campground]
    """Passed every other filter, and has no coordinates.

    Never empty-by-omission: these are campgrounds a proximity search cannot
    rank, and they are carried out of the function rather than dropped inside
    it. Only populated when a reference point was given -- without one,
    coordinates decide nothing.
    """
    near: Optional[Tuple[float, float]] = None
    within_miles: Optional[float] = None
    filters: Tuple[Tuple[str, str], ...] = ()
    """The filters as given, for rendering. A list of three means nothing
    without the question it answers."""


def find_campgrounds(
    campgrounds: Sequence[Campground],
    access: str = "",
    campsite_type: str = "",
    park: str = "",
    agency: str = "",
    near: Optional[Tuple[float, float]] = None,
    within_miles: Optional[float] = None,
) -> CampgroundSearch:
    """Campgrounds matching every filter given, nearest first when ``near`` is set.

    A blank filter is not applied. ``access`` and ``campsite_type`` match
    exactly and therefore never match a blank field on the row -- asking for
    drive-in campgrounds excludes the ones nobody has checked, which is the
    conservative direction and is why :attr:`CampgroundSearch.unplaced` and the
    unrecorded count are reported separately.

    ``within_miles`` without ``near`` is a programming error rather than an
    empty result, so it raises.
    """
    if within_miles is not None and near is None:
        raise ValueError("within_miles needs a reference point; pass near=(lat, lon)")

    filters: List[Tuple[str, str]] = []
    kept = list(campgrounds)
    for label, value, attr in (("access", access, "access_mode"),
                               ("type", campsite_type, "campsite_type"),
                               ("park", park, "park"),
                               ("agency", agency, "agency_id")):
        if not value:
            continue
        filters.append((label, value))
        if attr == "agency_id":
            kept = [c for c in kept
                    if value in {k.strip() for k in c.agency_id.split(";")}]
        else:
            kept = [c for c in kept if getattr(c, attr) == value]

    if near is None:
        return CampgroundSearch(
            matches=[CampgroundMatch(c) for c in kept],
            unplaced=[], filters=tuple(filters),
        )

    lat, lon = near
    matches, unplaced = [], []
    for c in kept:
        if c.latitude is None:
            unplaced.append(c)
            continue
        miles = haversine_miles(lat, lon, c.latitude, c.longitude)
        if within_miles is not None and miles > within_miles:
            continue
        matches.append(CampgroundMatch(c, distance_miles=float(miles)))
    matches.sort(key=lambda m: m.distance_miles)
    return CampgroundSearch(matches=matches, unplaced=unplaced, near=near,
                            within_miles=within_miles, filters=tuple(filters))


def format_campground_list(search: CampgroundSearch,
                           unrecorded_access: Sequence[Campground] = ()) -> List[str]:
    """Render a search, leading with what the question was.

    ``unrecorded_access`` is the campgrounds whose ``access_mode`` is blank. It
    is passed in rather than recomputed because only the caller knows whether
    the filter that dropped them was about access at all -- and when it was,
    naming them is the difference between "three can be driven to" and "three
    can be driven to and nobody checked the rest".
    """
    asked = ", ".join(f"{k}={v}" for k, v in search.filters) or "no filters"
    lines = [f"Campgrounds ({asked})"]
    if search.near is not None:
        lat, lon = search.near
        within = f" within {search.within_miles:g} miles" if search.within_miles else ""
        lines.append(f"  Measured from {lat:.5f}, {lon:.5f}{within}. "
                     f"Distances are {STRAIGHT_LINE}.")

    if not search.matches:
        lines.append("  NOTHING MATCHED. That is not the same as nothing "
                     "existing -- see the gaps below.")
    for m in search.matches:
        c = m.campground
        head = f"  {c.name} -- {c.park}" if c.park else f"  {c.name}"
        lines.append(head)
        bits = [access_label(c)]
        if c.campsite_type:
            bits.append(f"{c.campsite_type} site")
        if m.distance_miles is not None:
            bits.append(f"{m.distance_miles:.1f} mi {m.distance_basis}")
        lines.append(f"      {'; '.join(bits)}")

    if search.unplaced:
        lines.append(f"  CANNOT BE PLACED -- {len(search.unplaced)} matched every "
                     "other filter and have no coordinates on file. They are not "
                     "far away; they are unmeasured, and this list is not a "
                     "ranking until they have coordinates.")
        for c in search.unplaced:
            lines.append(f"    - {c.name} ({c.park})" if c.park else f"    - {c.name}")

    if unrecorded_access:
        lines.append(f"  ACCESS MODE NOT RECORDED -- {len(unrecorded_access)} "
                     "campgrounds were excluded because nobody has checked "
                     "whether you can drive to them. Absent is not a value.")
        for c in unrecorded_access:
            lines.append(f"    - {c.name}")

    return lines
