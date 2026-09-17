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
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

DRIVE_IN = "drive_in"
"""You can park at or beside the site; the car is part of the trip."""

HIKE_IN = "hike_in"
"""Reached on foot (or horseback). Distance from the road belongs in ``notes``."""

BOAT_IN = "boat_in"
"""Reached by water. EBRPD's own field is the source of this value.

Added for Point Pinole's group camp, whose booking page reads "Site Access:
Boat-In, Hike-In" -- two modes, comma-separated, by the operator. That is what
made :attr:`Campground.access_mode` multi-valued: the field was single-valued
because every site read before had one answer, not because sites have one.
"""

_VALID_ACCESS_MODES = {DRIVE_IN, HIKE_IN, BOAT_IN}

ACCESS_MODE_LABELS = {DRIVE_IN: "drive-in", HIKE_IN: "hike-in", BOAT_IN: "boat-in"}

COORD_CAMPGROUND = "campground"
"""The coordinate names the camping area itself."""

COORD_PARK = "park"
"""The coordinate names the PARK the campground is in, not the campground.

Stored separately because the two are not interchangeable and reading one as
the other is the same error as a guessed ``access_mode``: it renders
identically to a precise value. ReserveAmerica publishes a GPS pair on each
park's overview page and none on its campsite pages, so every coordinate this
project has is of this kind. Dumbarton Quarry is why it matters -- it resolves
to Coyote Hills Regional Park and has its own entrance several miles round the
marsh, so that park's coordinate would place it somewhere it is not.
"""

_VALID_COORD_PRECISION = {COORD_CAMPGROUND, COORD_PARK}

COORD_PRECISION_LABELS = {
    COORD_CAMPGROUND: "to the campground",
    COORD_PARK: "to the park, not the campground",
}

UNIT_SITE = "site"
"""This row IS one bookable unit. Reserving it reserves the whole thing.

Corral Group Camp and Wild Turkey Group Camp are this, and so is every camp
whose own ``/campsite-booking`` page was read: that page sells one thing, with
one capacity. The word "Camp" in a name says nothing about the level -- what
decides it is whether a source shows the camp as a single line with a single
capacity, or as a container of lines.
"""

UNIT_CAMP = "camp"
"""This row HOLDS bookable sites; the reservation is for one of them.

Anthony Chabot Campground (75 numbered sites over five loops) and Sunol
Backpack Camp (seven named ones) are this. So is Stewart's Camp, which holds
exactly one -- the Sunol facility lists 'Stewart's' as a site inside the
'Ohlone Backpack' loop, in the same series as Boyd #1 and Boyd #2, and a camp
that happens to hold one site is still a camp.
"""

_VALID_UNIT_LEVELS = {UNIT_SITE, UNIT_CAMP}

UNIT_LEVEL_LABELS = {
    UNIT_SITE: "booked as one unit",
    UNIT_CAMP: "holds individually bookable sites",
}

UNKNOWN_UNIT_LEVEL_LABEL = "booking level not recorded"
"""What a blank ``unit_level`` reads as.

There is no facility level in this vocabulary, deliberately. Every row in
``campgrounds.csv`` is a camp or a site INSIDE a ReserveAmerica facility --
EB/110028 holds Sunol Backpack Camp, Eagle Springs and four Del Valle camps,
across THREE parks -- and no row is a facility. Corrected from "four different
parks", which was written here and in none-2026-09-16-58 while two earlier log
entries already said three; four is the number of Del Valle camps on that
facility, not the number of parks it reaches. The facility level now has a
table, ``data/booking_facilities.csv``, and ``facility_id`` joins to it.
"""

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


def _float_field(row, col: str) -> Optional[float]:
    """A number, or ``None`` when the cell is empty -- never 0.0 for blank."""
    val = row.get(col)
    if val is None or pd.isna(val):
        return None
    text = str(val).strip()
    if not text:
        return None
    return float(text)


def _mmdd_field(row, col: str) -> Optional[tuple]:
    """``(month, day)`` from an ``MM-DD`` cell, or ``None`` when it is empty."""
    val = row.get(col)
    if val is None or pd.isna(val):
        return None
    text = str(val).strip()
    if not text:
        return None
    month, day = text.split("-")
    month, day = int(month), int(day)
    date(2001, month, day)  # raises on 02-30 and friends
    return (month, day)


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
    facility_id: str = ""
    """The booking-system facility this campground is sold through, e.g.
    ``EB/110003``. Keys into ``data/booking_facilities.csv``.

    STORED, NOT DERIVED FROM :attr:`park`, because the two do not line up in
    either direction. EB/110028 sells sites in three parks; Del Valle Regional
    Park is sold through two facilities and so is Coyote Hills. A park cannot
    supply this key, and a campground's own ``source_url`` only sometimes
    carries it -- the seven Anthony Chabot group camps cite a District PDF and
    Dumbarton Quarry an ebparks.org page, and all eight belong to a facility.

    Blank means unrecorded, and one row is: Lil Chaparral Horse Camp, named on
    the Ohlone Wilderness permit map and absent from the Del Valle listing that
    was read. Its pair Caballo Loco is on that listing, which is what gives
    that row a key and not this one.
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
    """How you reach it: ``drive_in``, ``hike_in``, ``boat_in``, or ``""``.

    ";"-separated when a site has more than one, the same shape as
    :attr:`agency_id`, and for the same reason: the operator publishes a list.
    Point Pinole's group camp reads "Site Access: Boat-In, Hike-In" on its own
    booking page. Use :meth:`access_modes` rather than comparing the string.

    See :data:`UNKNOWN_ACCESS_LABEL` -- blank is a stated gap, not a default.
    A CONDITIONAL mode does not belong here: Wee-Ta-Chi can be driven to in dry
    weather and Point Pinole's camp takes four escorted vehicles by prior
    arrangement, and neither is stored as ``drive_in``, because a filter for
    campgrounds you can drive to must not return a site that needs a fortnight's
    notice and a staff escort. Those live in ``notes``.
    """

    def closed_on(self, on: "date") -> Optional[bool]:
        """Is this campground inside its annual closure on *on*?

        ``None`` when no closure is recorded -- which a caller must render as
        "not known", never as "open".
        """
        if not self.season_closed_start or not self.season_closed_end:
            return None
        start, end = self.season_closed_start, self.season_closed_end
        today = (on.month, on.day)
        if start <= end:
            return start <= today <= end
        # Wraps the new year, which every EBRPD closure here does.
        return today >= start or today <= end

    @property
    def season_label(self) -> str:
        """The closure as a reader sees it, or "" when none is recorded."""
        if not self.season_closed_start or not self.season_closed_end:
            return ""
        fmt = lambda md: f"{date(2001, md[0], md[1]):%-d %B}"  # noqa: E731
        return f"{fmt(self.season_closed_start)} to {fmt(self.season_closed_end)}"

    @property
    def access_modes(self) -> List[str]:
        """The modes as a list; empty when nobody has recorded any."""
        return [m for m in (p.strip() for p in self.access_mode.split(";")) if m]
    loop: str = ""
    """The operator's own loop name, verbatim, e.g.
    ``Primitive Group Camp Seasonal``. Free text, and deliberately so.

    THE SAME COLUMN ``campsites.csv`` ALREADY HAD. It is here because the camps
    that were missing one are rows of this file, not that one: every campsite
    row has carried a loop since Anthony Chabot was read, while sixteen
    campgrounds had theirs in prose. No vocabulary, no validation and no
    loops table -- the loop is a label the booking system prints, and inventing
    a level for it would model structure nobody has stated.

    NOT QUITE RULE-FREE, WHICH IS THE ARGUMENT FOR A COLUMN RATHER THAN AGAINST
    ONE. Three things currently live only in this string:

    - ``Seasonal`` in the name against :attr:`season_closed_start`. Round Valley
      Backpack Camp sits in a loop called ``Backpack Seasonal`` and is open year
      round, on EBRPD's own word -- so the token is not a season and must never
      be read as one. It is asked about, never asserted.
    - ``Seasonal A`` against ``Seasonal B`` at Anthony Chabot, where Bort Meadow
      is alone in B and its open period may therefore differ from the other
      five. Anthony Chabot's season is an open conflict, and this is the only
      handle on the split.
    - ``Developed`` against ``Primitive``. Del Valle's two group camps are the
      only ``Developed`` ones read here; everywhere else is ``Primitive``. EBRPD
      does not say what the word buys, so it is recorded, not interpreted.

    Blank means nobody has read one. Puma Point Group Camp is the interesting
    blank: five of its six siblings state ``Seasonal A`` and Bort Meadow is
    stated to be the only one in ``B``, which makes Puma Point ``A`` by
    subtraction. That is arithmetic, and this project has twice been wrong
    following arithmetic that worked.
    """
    unit_level: str = ""
    """Whether this row is one bookable unit or a container of them:
    ``site``, ``camp``, or ``""``.

    A THIRD AXIS, orthogonal to both of the two above. ``campsite_type`` is
    which queue you book in and ``access_mode`` is how you physically arrive;
    this is how many reservations the row is. Nothing else in the table carries
    it, and the table a thing lives in does not either: "Cathedral" is a row of
    ``campsites.csv`` and "Wild Turkey Group Camp" is a row of this file, and
    both are exactly one bookable unit with one booking page.

    IT IS NOT DERIVABLE from whether ``campsites.csv`` holds rows for this
    campground, which is why it is stored. Del Valle Family Campground has 155
    sites and this project records none of them; counting rows would call it a
    single site and be wrong in the direction that matters, telling a camper
    the reservation is the whole campground.

    BLANK MEANS NOBODY HAS ESTABLISHED IT -- see
    :data:`UNKNOWN_UNIT_LEVEL_LABEL`. Four rows are blank and each says why in
    ``notes``: Hetch Hetchy and Venados are named only in a closure list, Lil
    Chaparral only on a map, and Dumbarton Quarry's composition is still
    web-search material behind a deliberately empty ``verified_date``.
    """
    campsite_type: str = ""
    """Which class of site the agency sells this as: ``family``, ``group`` or
    ``backpack``. Keys into ``data/booking_channels.csv``.

    A different axis from :attr:`access_mode`, not a restatement of it. Access
    mode is how you physically reach the site; this is which queue you book it
    in, and EBRPD's two differ -- Anthony Chabot's family campground is
    drive-in and contains ten hike-in sites, so neither axis predicts the
    other even inside one campground. Blank means unknown, and
    :func:`wayproof.booking.channels_for` then returns only agency-wide
    channels rather than guessing a class.
    """
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    """Where it is, or ``None`` when nobody has recorded it.

    ``None`` rather than 0.0: a zero pair is a real place in the Gulf of
    Guinea, and a campground silently sorted 8,000 miles away is worse than
    one the search says it cannot place. :func:`unlocated` is how the gap is
    shown rather than dropped.
    """
    coord_precision: str = ""
    """``campground`` or ``park`` -- what the coordinate above actually names.

    Required whenever a coordinate is present; :func:`load_campgrounds`
    refuses a pair without it. An unlabelled coordinate reads as the campsite's
    own position, which for a park centroid can be miles wrong, and nothing
    downstream could tell the difference.
    """
    coord_source: str = ""
    """Which page the coordinate came off, in prose. Same rule as every other
    field here: a value carries where it came from."""
    season_closed_start: Optional[tuple] = None
    season_closed_end: Optional[tuple] = None
    """The annual closure as ``(month, day)`` pairs, or ``None`` when no source
    states one.

    Stored as MM-DD like ``permits.csv``'s quota season, and read the same way
    -- except that these WRAP THE YEAR and quota seasons do not. Every EBRPD
    closure read for this project runs 1 November to somewhere in spring, so
    ``PermitRule.in_quota_season``'s straight ``start <= today <= end`` would
    answer False on every day of every closure. :meth:`closed_on` handles the
    wrap; the permits version is left alone because its seasons run inside one
    year.

    BLANK IS NOT "OPEN ALL YEAR". It is "nobody has recorded a closure", which
    is the same rule as a blank fee or a blank access mode. Anthony Chabot is
    why it matters: its season is an open conflict -- the brochure says
    year-round and the booking system says closed 1 Nov to 1 Apr -- and filling
    these columns would launder a disputed reading into a fact.
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
        modes = [m for m in (p.strip() for p in access_mode.split(";")) if m]
        for mode in modes:
            if mode not in _VALID_ACCESS_MODES:
                raise ValueError(
                    f"Invalid access_mode {mode!r} for campground {name!r}; "
                    f"expected one of {sorted(_VALID_ACCESS_MODES)} or blank"
                )
        if len(set(modes)) != len(modes):
            raise ValueError(f"Repeated access_mode in {access_mode!r} for {name!r}")
        season_start = _mmdd_field(row, "season_closed_start")
        season_end = _mmdd_field(row, "season_closed_end")
        if (season_start is None) != (season_end is None):
            raise ValueError(
                f"Campground {name!r} has half a closure season; a start "
                f"without an end says nothing about when it reopens"
            )
        unit_level = _str_field(row, "unit_level")
        if unit_level and unit_level not in _VALID_UNIT_LEVELS:
            raise ValueError(
                f"Invalid unit_level {unit_level!r} for campground {name!r}; "
                f"expected one of {sorted(_VALID_UNIT_LEVELS)} or blank. There "
                f"is no 'facility' level here -- see UNKNOWN_UNIT_LEVEL_LABEL."
            )
        latitude = _float_field(row, "latitude")
        longitude = _float_field(row, "longitude")
        coord_precision = _str_field(row, "coord_precision")
        if (latitude is None) != (longitude is None):
            raise ValueError(
                f"Campground {name!r} has half a coordinate; give both or neither"
            )
        if latitude is not None and coord_precision not in _VALID_COORD_PRECISION:
            raise ValueError(
                f"Campground {name!r} has coordinates and coord_precision "
                f"{coord_precision!r}; expected one of "
                f"{sorted(_VALID_COORD_PRECISION)}. An unlabelled coordinate "
                f"reads as the campsite's own position."
            )
        if latitude is None and coord_precision:
            raise ValueError(
                f"Campground {name!r} has coord_precision {coord_precision!r} "
                f"and no coordinates"
            )
        campgrounds.append(Campground(
            season_closed_start=season_start,
            season_closed_end=season_end,
            latitude=latitude,
            longitude=longitude,
            coord_precision=coord_precision,
            coord_source=_str_field(row, "coord_source"),
            name=name,
            park=_str_field(row, "park"),
            land_agency=_str_field(row, "land_agency"),
            agency_id=_str_field(row, "agency_id"),
            facility_id=_str_field(row, "facility_id"),
            jurisdiction=_str_field(row, "jurisdiction"),
            access_mode=access_mode,
            loop=_str_field(row, "loop"),
            unit_level=unit_level,
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

    Blank reads as :data:`UNKNOWN_ACCESS_LABEL`, never as a mode. Several modes
    read as all of them, joined -- "boat-in or hike-in" -- because a reader who
    sees only one has been told the site is harder or easier to reach than it is.
    """
    modes = [ACCESS_MODE_LABELS[m] for m in campground.access_modes
             if m in ACCESS_MODE_LABELS]
    if not modes:
        return UNKNOWN_ACCESS_LABEL
    if len(modes) == 1:
        return modes[0]
    return " or ".join([", ".join(modes[:-1]), modes[-1]])


def drive_in(campgrounds: List[Campground]) -> List[Campground]:
    """Only the campgrounds you can drive to.

    Excludes unrecorded ones: a blank ``access_mode`` is not evidence of a road.
    Pair it with :func:`unknown_access` so the gap is shown rather than dropped.
    """
    return [c for c in campgrounds if DRIVE_IN in c.access_modes]


def unknown_access(campgrounds: List[Campground]) -> List[Campground]:
    """Campgrounds whose access mode nobody has recorded yet."""
    return [c for c in campgrounds if not c.access_mode]


def located(campgrounds: Sequence[Campground]) -> List[Campground]:
    """Campgrounds that can be placed on a map."""
    return [c for c in campgrounds if c.latitude is not None]


def closed_on(campgrounds: Sequence[Campground], on: "date") -> List[Campground]:
    """Campgrounds whose recorded closure covers *on*."""
    return [c for c in campgrounds if c.closed_on(on)]


def season_unrecorded(campgrounds: Sequence[Campground]) -> List[Campground]:
    """Campgrounds with no closure on file.

    Returned so a caller can SAY so. Silence here means nobody looked, and a
    reader shown nothing would reasonably assume the place is open.
    """
    return [c for c in campgrounds if c.season_closed_start is None]


def seasonal_loop_without_a_season(
    campgrounds: Sequence[Campground],
) -> List[Campground]:
    """Campgrounds whose loop name says ``Seasonal`` and whose season is blank.

    A QUESTION, NOT A DERIVATION. The obvious move is to read the token as a
    closure and fill the columns from it, and Round Valley Backpack Camp is why
    that is wrong: its loop is ``Backpack Seasonal`` and EBRPD says the camp is
    open year round. The token means the booking system files it among seasonal
    loops; it does not say when, or whether, anything shuts.

    So this returns rows worth going and reading, which is what the loop name
    is good for and the whole of what it is good for.
    """
    return [c for c in campgrounds
            if "seasonal" in c.loop.lower() and c.season_closed_start is None]


def seasonal_loop_contradicting_a_season(
    campgrounds: Sequence[Campground],
) -> List[Campground]:
    """Campgrounds stated open year round from a loop the operator calls seasonal.

    Distinct from the above and worth its own list: there the season is unread,
    here it is read and disagrees with the loop name. One row, and it is the
    reason the token is never trusted.
    """
    return [c for c in campgrounds
            if "seasonal" in c.loop.lower() and c.season_closed_start is None
            and "open year round" in c.notes.lower()]


def loop_unrecorded(campgrounds: Sequence[Campground]) -> List[Campground]:
    """Campgrounds with no loop name on file."""
    return [c for c in campgrounds if not c.loop]


def unit_level_label(campground: Campground) -> str:
    """How to describe a campground's booking level, blank included."""
    return UNIT_LEVEL_LABELS.get(campground.unit_level, UNKNOWN_UNIT_LEVEL_LABEL)


def unit_level_unrecorded(campgrounds: Sequence[Campground]) -> List[Campground]:
    """Campgrounds whose booking level nobody has established."""
    return [c for c in campgrounds if not c.unit_level]


def camps_without_sites(
    campgrounds: Sequence[Campground], campsites: Sequence["Campsite"]
) -> List[Campground]:
    """Campgrounds recorded as holding sites, of which this project holds none.

    A gap the column created and only the column can see. Before ``unit_level``
    existed, Del Valle Family Campground -- 155 sites, none of them here -- was
    indistinguishable from a one-unit camp, so there was nothing to report.
    """
    have = {s.campground for s in campsites}
    return [c for c in campgrounds if c.unit_level == UNIT_CAMP and c.name not in have]


def unlocated(campgrounds: Sequence[Campground]) -> List[Campground]:
    """Campgrounds with no coordinates recorded.

    Returned so a proximity search can *report* them rather than drop them.
    Dropping is what makes "nothing is near you" and "nobody has looked"
    indistinguishable -- the failure the scorecard already names for Q21.
    """
    return [c for c in campgrounds if c.latitude is None]


def coord_precision_label(campground: Campground) -> str:
    """What this campground's coordinate is a coordinate *of*."""
    return COORD_PRECISION_LABELS.get(campground.coord_precision,
                                      "precision not recorded")


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
