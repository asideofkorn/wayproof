"""Backpack campgrounds and their individually-bookable campsites.

A campground is a physical cluster with shared infrastructure (a restroom, a
water source, one reservation contact) at one location. Some campgrounds --
Boyd Camp, Stewart's Camp -- are effectively a single bookable site; others,
like Sunol Backpack Camp, contain several individually-named sites (Cathedral,
Eagles Aerie, Hawks Nest...) that share the campground's facilities but have
their own capacity and, sometimes, a genuinely different proximity to those
shared facilities (e.g. Hawks Nest is closer to both water and the restroom
than Sunol Backpack Camp's other sites).

That's why this is two files, not one: ``data/campgrounds.csv`` (the shared,
physical facts -- location, restroom, water source, how to reserve) and
``data/campsites.csv`` (the individually-bookable units within a campground).
A campground with no differentiated sub-sites simply has no rows in
``campsites.csv`` -- don't invent a placeholder row that just repeats the
campground's own name.

``access_mode`` is the separate question of whether you can *drive* to the
site. It is a column rather than prose because it is the first thing a car
camper filters on, and six of this dataset's seven campgrounds are backpack
camps reached only on foot -- listing them beside a drive-in campground with
no distinction invites someone to book a site 10.72 trail miles from their
car. It was previously recoverable only by reading ``notes`` ("~mile 6.58 on
the Ohlone Wilderness Trail", "General car-camping area"), which is exactly
the filing-cabinet use of ``notes`` this project warns against.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd

DRIVE_IN = "drive_in"
"""You can park at or beside the site; the car is part of the trip."""

HIKE_IN = "hike_in"
"""Reached on foot (or horseback). Distance from the road belongs in ``notes``."""

_VALID_ACCESS_MODES = {DRIVE_IN, HIKE_IN}

ACCESS_MODE_LABELS = {DRIVE_IN: "drive-in", HIKE_IN: "hike-in"}

UNKNOWN_ACCESS_LABEL = "access mode not recorded"
"""What a blank ``access_mode`` reads as.

Blank means nobody has checked, and it renders as that rather than defaulting
to either mode. Guessing "drive-in" strands someone at a trailhead; guessing
"hike-in" hides a site they could have used. Same rule as a missing fee:
absent is not a value.
"""


def _str_field(row, col: str) -> str:
    val = row.get(col)
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()


def _bool_field(row, col: str) -> bool:
    val = row.get(col)
    if val is None or pd.isna(val):
        return False
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes")


@dataclass
class Campground:
    """One row of ``data/campgrounds.csv``: a physical camping cluster."""

    name: str
    park: str
    land_agency: str = ""
    agency_id: str = ""
    """Stable key(s) for :attr:`land_agency`, ";"-separated for co-managed land.

    The same display-string/key split ``Trailhead.agency_id`` makes, and here
    for a sharper reason: a campground reached without a permit has no permit
    row to borrow an agency from, so without this key an agency-scoped rule
    cannot reach a trip that is only ever a campsite.
    """
    jurisdiction: str = ""
    """State whose law applies, e.g. ``"CA"``.

    A column rather than an inference for the same reason ``permits.csv``
    carries one: state law reaches a trip through the permit's jurisdiction,
    and a campground booked without a permit would otherwise inherit no state
    law at all -- silently dropping the California Campfire Permit from every
    car-camping plan.
    """
    access_mode: str = ""
    """``drive_in``, ``hike_in``, or ``""`` when nobody has recorded it.

    See :data:`UNKNOWN_ACCESS_LABEL` -- blank is a stated gap, not a default.
    """
    campsite_type: str = ""
    """Which class of site the agency sells this as: ``family``, ``group`` or
    ``backpack``. Keys into ``data/booking_channels.csv``.

    A different axis from :attr:`access_mode`, not a restatement of it. Access
    mode is how you physically reach the site; this is which queue you book it
    in, and EBRPD's two differ -- a group camp can be drive-in, and Anthony
    Chabot's family campground contains hike-in sites. Blank means unknown, and
    :func:`wayproof.booking.channels_for` then returns only agency-wide
    channels rather than guessing a class.
    """
    has_restroom: bool = False
    restroom_type: str = ""
    reservation_method: str = ""
    reservation_contact: str = ""
    checkin_time: str = ""
    checkout_time: str = ""
    nightly_entry_cutoff: str = ""
    fee_notes: str = ""
    notes: str = ""
    source_url: str = ""
    verified_date: str = ""
    """When this row was last checked against :attr:`source_url`.

    Blank means never. The table carried no provenance at all until EBRPD
    campgrounds outside the Ohlone corridor were added, so most rows are blank
    and honestly so -- a citation invented for them now would be worse than the
    visible gap.
    """


RV_HOOKUP = "rv_hookup"
TENT_DRIVE_UP = "tent_drive_up"
TENT_HIKE_IN = "tent_hike_in"
_VALID_SITE_TYPES = {RV_HOOKUP, TENT_DRIVE_UP, TENT_HIKE_IN}

SITE_TYPE_LABELS = {
    RV_HOOKUP: "RV site with hookups",
    TENT_DRIVE_UP: "drive-up tent site",
    TENT_HIKE_IN: "walk-in tent site",
}


@dataclass
class Campsite:
    """One row of ``data/campsites.csv``: an individually-bookable site
    within a :class:`Campground`."""

    name: str
    campground: str
    capacity: int = 0
    water_proximity: str = ""
    restroom_proximity: str = ""
    notes: str = ""
    loop: str = ""
    site_type: str = ""
    """``rv_hookup``, ``tent_drive_up``, ``tent_hike_in``, or ``""`` when
    nobody has recorded it.

    Deliberately not named after the booking system's own filters, which are
    actively misleading here: ReserveAmerica calls Anthony Chabot's ten walk-in
    sites "Tent Only" and its forty-eight drive-up tent sites "Tent/No-Hookup",
    so someone filtering for a tent site on foot-free terms gets the ones a
    thousand feet from their car. The label a reader sees comes from
    :data:`SITE_TYPE_LABELS`.
    """
    hookups: str = ""
    online_bookable: bool = True
    """False when the site exists but never appears in the online listing.

    Six of Anthony Chabot's seventy-five do. A party browsing online and
    concluding a campground is full has checked sixty-nine of them, so the
    absence is data rather than a gap in this table.
    """


def load_campgrounds(path: str | Path = "data/campgrounds.csv") -> List[Campground]:
    """Load campgrounds. Returns an empty list if the file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return []
    df = pd.read_csv(path)

    campgrounds: List[Campground] = []
    for _, row in df.iterrows():
        name = _str_field(row, "name")
        if not name:
            continue
        access_mode = _str_field(row, "access_mode")
        if access_mode and access_mode not in _VALID_ACCESS_MODES:
            raise ValueError(
                f"Invalid access_mode {access_mode!r} for campground {name!r}; "
                f"expected one of {sorted(_VALID_ACCESS_MODES)} or blank"
            )
        campgrounds.append(Campground(
            name=name,
            park=_str_field(row, "park"),
            land_agency=_str_field(row, "land_agency"),
            agency_id=_str_field(row, "agency_id"),
            jurisdiction=_str_field(row, "jurisdiction"),
            access_mode=access_mode,
            campsite_type=_str_field(row, "campsite_type"),
            has_restroom=_bool_field(row, "has_restroom"),
            restroom_type=_str_field(row, "restroom_type"),
            reservation_method=_str_field(row, "reservation_method"),
            reservation_contact=_str_field(row, "reservation_contact"),
            checkin_time=_str_field(row, "checkin_time"),
            checkout_time=_str_field(row, "checkout_time"),
            nightly_entry_cutoff=_str_field(row, "nightly_entry_cutoff"),
            fee_notes=_str_field(row, "fee_notes"),
            notes=_str_field(row, "notes"),
            source_url=_str_field(row, "source_url"),
            verified_date=_str_field(row, "verified_date"),
        ))
    return campgrounds


def load_campsites(path: str | Path = "data/campsites.csv") -> List[Campsite]:
    """Load campsites. Returns an empty list if the file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return []
    df = pd.read_csv(path)

    campsites: List[Campsite] = []
    for _, row in df.iterrows():
        name = _str_field(row, "name")
        if not name:
            continue
        capacity = row.get("capacity")
        site_type = _str_field(row, "site_type")
        if site_type and site_type not in _VALID_SITE_TYPES:
            raise ValueError(
                f"Invalid site_type {site_type!r} for campsite {name!r}; "
                f"expected one of {sorted(_VALID_SITE_TYPES)} or blank"
            )
        bookable = row.get("online_bookable")
        campsites.append(Campsite(
            name=name,
            campground=_str_field(row, "campground"),
            capacity=int(capacity) if capacity is not None and not pd.isna(capacity) else 0,
            water_proximity=_str_field(row, "water_proximity"),
            restroom_proximity=_str_field(row, "restroom_proximity"),
            notes=_str_field(row, "notes"),
            loop=_str_field(row, "loop"),
            site_type=site_type,
            hookups=_str_field(row, "hookups"),
            online_bookable=(True if bookable is None or pd.isna(bookable)
                             else str(bookable).strip().lower() in ("true", "1", "yes")),
        ))
    return campsites


def campsites_by_campground(sites: List[Campsite]) -> Dict[str, List[Campsite]]:
    """Index campsites by their campground's name."""
    by_campground: Dict[str, List[Campsite]] = {}
    for s in sites:
        by_campground.setdefault(s.campground, []).append(s)
    return by_campground


def access_label(campground: Campground) -> str:
    """How to describe a campground's access to a reader.

    Blank reads as :data:`UNKNOWN_ACCESS_LABEL`, never as a mode.
    """
    return ACCESS_MODE_LABELS.get(campground.access_mode, UNKNOWN_ACCESS_LABEL)


def drive_in(campgrounds: List[Campground]) -> List[Campground]:
    """Only the campgrounds you can drive to.

    Excludes unrecorded ones: a blank ``access_mode`` is not evidence of a road.
    Pair it with :func:`unknown_access` so the gap is shown rather than dropped.
    """
    return [c for c in campgrounds if c.access_mode == DRIVE_IN]


def unknown_access(campgrounds: List[Campground]) -> List[Campground]:
    """Campgrounds whose access mode nobody has recorded yet."""
    return [c for c in campgrounds if not c.access_mode]


def site_type_label(campsite: Campsite) -> str:
    """How to describe a campsite's type to a reader."""
    return SITE_TYPE_LABELS.get(campsite.site_type, "type not recorded")


def sites_by_type(campsites: List[Campsite]) -> Dict[str, List[Campsite]]:
    """Index campsites by :attr:`Campsite.site_type`, unrecorded ones under ``""``."""
    out: Dict[str, List[Campsite]] = {}
    for s in campsites:
        out.setdefault(s.site_type, []).append(s)
    return out


def resolve_campground_name(query: str, campgrounds: List[Campground]) -> tuple:
    """``(campground, candidates)`` for a typed name.

    Mirrors :func:`wayproof.data_loader.resolve_peak_name` and for the same
    reason: exactly one of the two is meaningful. A unique match returns
    ``(campground, [])``; an ambiguous one returns ``(None, [...])`` so the
    caller can show the options instead of picking. "Bort Meadow" alone matches
    a group camp here and could match a staging area elsewhere, and choosing one
    is how someone books the wrong thing.

    Matching is exact first, then case-insensitive, then against the name with a
    generic trailing words dropped -- someone typing "Anthony Chabot" means the
    campground, and making them type its full stored name is a lookup failure
    dressed up as precision. A park name is not enough: "Del Valle" resolves to
    nothing, because that park has five campgrounds and picking one would be the
    same error as guessing a trailhead.
    """
    wanted = str(query or "").strip()
    if not wanted:
        return None, []

    by_exact = {c.name: c for c in campgrounds}
    if wanted in by_exact:
        return by_exact[wanted], []

    lowered = wanted.lower()
    exact_ci = [c for c in campgrounds if c.name.strip().lower() == lowered]
    if len(exact_ci) == 1:
        return exact_ci[0], []
    if len(exact_ci) > 1:
        return None, sorted(c.name for c in exact_ci)

    def _bare(name: str) -> str:
        # Trailing generic words only, stripped one at a time so the same text
        # reduces the same way whether it was typed or stored. Taking " family
        # campground" as one unit did not: it reduced the stored name to "del
        # valle" while "Del Valle Family" stayed put, and the two stopped
        # matching. Qualifiers that name a different place -- "family",
        # "backpack" -- are deliberately kept, so "Del Valle" alone still
        # resolves to nothing rather than to one of that park's five campgrounds.
        words = name.strip().lower().split()
        while words and words[-1] in ("campground", "camp", "group"):
            words.pop()
        return " ".join(words)

    target = _bare(wanted)
    loose = [c for c in campgrounds if _bare(c.name) == target]
    if len(loose) == 1:
        return loose[0], []
    return None, sorted(c.name for c in loose)
