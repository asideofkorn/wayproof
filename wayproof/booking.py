"""How you actually get a campsite, stored once per agency rather than per site.

``data/campgrounds.csv`` answers *what is this place like*. This module answers
the separate question of *how do I book it*, and it is a separate table for the
reason ``regulations.csv`` is: the answer belongs to the agency, not the site.

EBRPD's reservations line, its walk-in counter, and the fact that its published
reservations email accepts no reservations are true of every campground the
District runs. Stored per campground, that text sat in nine rows and would have
sat in twenty-one once the rest of the District's parks landed -- the same shape
as the California Campfire Permit copied into seven ``permits.csv`` rows, which
drifted in five different ways before anyone noticed. A fact asserted in nine
places is a fact maintained in none of them.

Two axes select a channel, and both are needed:

- **scope** -- ``agency``/``ebrpd``, resolved by
  :func:`wayproof.regulations.scope_applies`, the same four-way logic
  regulations use. Booking mechanics are the second scoped table, which is what
  that function was split out for.
- **applies_to** -- the class of site the channel sells. EBRPD's split is the
  point: family campsites book online at ReserveAmerica, while group and
  backpack sites are phone-only and cannot be booked online at all. Answering
  that per agency instead of per class would send a backpacker to a website
  that cannot sell them the site.

A channel scoped ``all`` applies to every class, and resolution returns it
*alongside* the class-specific one rather than instead of it -- the same
specific-plus-general layering ``regulations_for`` does. That is how the
District-wide contact is stored once while the per-class booking method and
lead time stay separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import pandas as pd

from .regulations import SPECIFICITY, scope_applies

ALL = "all"
FAMILY = "family"
GROUP = "group"
BACKPACK = "backpack"
CABIN = "cabin"
"""EBRPD's fourth class, and its mechanics belong to neither neighbour.

Added when Del Valle's facility turned out to sell five cabins: booked on the
family calendar's far end, twelve weeks, and on the GROUP clock at the near
end, seventy-two hours rather than forty-eight -- then cancelled on the group
tiers. A class that borrows one rule from each is why ``applies_to`` is a
vocabulary rather than a boolean for "is this a group site".
"""

EQUESTRIAN = "equestrian"
"""A horse camp. Two campground rows carried this before it was a value here."""

SITE_CLASSES = {FAMILY, GROUP, BACKPACK, CABIN, EQUESTRIAN}
"""The classes a site can BE. Shared with ``campgrounds.csv``'s
``campsite_type``, which keys into this table and was unvalidated until a
schema-integrity test found ``equestrian`` in it and no channel to match."""

_VALID_APPLIES_TO = SITE_CLASSES | {ALL}
"""What a CHANNEL can sell: any site class, or ``all`` of them."""

UNKNOWN_FACILITY_LABEL = "booking facility not recorded"
"""What a blank ``facility_id`` reads as.

Not the park's facility. A park does not have one: Del Valle is sold through
two and Coyote Hills through two, so inheriting would be a coin toss dressed
as a fact.
"""

APPLIES_TO_LABELS = {
    EQUESTRIAN: "Equestrian campsites",
    ALL: "Any campsite",
    FAMILY: "Family campsites",
    GROUP: "Group campsites",
    BACKPACK: "Backpack campsites",
    CABIN: "Cabins",
}


def _str_field(row, col: str) -> str:
    val = row.get(col)
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()


@dataclass
class BookingChannel:
    """One row of ``data/booking_channels.csv``."""

    channel_id: str
    scope_type: str
    scope_value: str
    applies_to: str
    method: str = ""
    contact: str = ""
    not_accepted: str = ""
    """What looks like a booking channel and is not, or what voids a booking.

    Its own field for the same reason :attr:`wayproof.permits.PermitRule.carry`
    is: being wrong about it is discovered too late to fix. EBRPD publishes a
    reservations email address that accepts no reservations, and someone who
    emails it and waits has not booked anything -- they find that out when the
    site is gone.
    """
    lead_time: str = ""
    change_cancel: str = ""
    """How to change or cancel, and through which channel.

    The scorecard reports "Can I change or cancel, and by when?" as no-model
    for every objective: nothing in the schema could express it. It belongs
    here because the answer is a channel fact and splits by channel -- EBRPD
    lets a family campsite be cancelled online but not changed online, and
    neither changes nor cancellations are accepted by email even though the
    email address is published.
    """
    release_mechanics: str = ""
    """What changes on the day inventory opens, when the ordinary channel is not
    the one that gets you a site."""
    horizon: str = ""
    horizon_as_of: str = ""
    """When :attr:`horizon` was read. A rolling booking window is a fact that
    expires, so it is never shown without the date it was true on."""
    source_url: str = ""
    verified_date: str = ""
    log_entry_ids: str = ""
    scope_display: str = ""

    @property
    def scope_label(self) -> str:
        return self.scope_display or self.scope_value

    @property
    def applies_label(self) -> str:
        return APPLIES_TO_LABELS.get(self.applies_to, self.applies_to)


def load_booking_channels(
    path: str | Path = "data/booking_channels.csv",
) -> List[BookingChannel]:
    """Load booking channels. Empty list if the file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return []
    df = pd.read_csv(path)

    out: List[BookingChannel] = []
    for _, row in df.iterrows():
        channel_id = _str_field(row, "channel_id")
        if not channel_id:
            continue
        applies_to = _str_field(row, "applies_to")
        if applies_to not in _VALID_APPLIES_TO:
            raise ValueError(
                f"Invalid applies_to {applies_to!r} for {channel_id!r}; "
                f"expected one of {sorted(_VALID_APPLIES_TO)}"
            )
        out.append(BookingChannel(
            channel_id=channel_id,
            scope_type=_str_field(row, "scope_type"),
            scope_value=_str_field(row, "scope_value"),
            applies_to=applies_to,
            method=_str_field(row, "method"),
            contact=_str_field(row, "contact"),
            not_accepted=_str_field(row, "not_accepted"),
            lead_time=_str_field(row, "lead_time"),
            change_cancel=_str_field(row, "change_cancel"),
            release_mechanics=_str_field(row, "release_mechanics"),
            horizon=_str_field(row, "horizon"),
            horizon_as_of=_str_field(row, "horizon_as_of"),
            source_url=_str_field(row, "source_url"),
            verified_date=_str_field(row, "verified_date"),
            log_entry_ids=_str_field(row, "log_entry_ids"),
            scope_display=_str_field(row, "scope_display"),
        ))
    return out


def channels_for(
    channels: Sequence[BookingChannel],
    campsite_type: str = "",
    permit_group: str = "",
    agency: "str | Sequence[str]" = "",
    jurisdiction: str = "",
    wilderness: str = "",
    park: str = "",
) -> List[BookingChannel]:
    """Channels reaching one class of campsite, general ones first.

    A blank ``campsite_type`` means the caller does not know what class of site
    is being booked, so only ``all`` channels are returned. Guessing ``family``
    there would tell a backpacker to book online, which EBRPD does not allow.

    ``park`` reaches park-scoped channels, added when Coyote Hills turned out to
    state a group booking deadline of its own -- five working days, paid in full
    -- against the District's three. Before that every booking mechanic here was
    agency-wide, and a park-scoped row would have loaded and resolved to nothing.
    """
    def applies(channel: BookingChannel) -> bool:
        if not scope_applies(channel.scope_type, channel.scope_value,
                             permit_group=permit_group, agency=agency,
                             jurisdiction=jurisdiction, wilderness=wilderness,
                             park=park):
            return False
        if channel.applies_to == ALL:
            return True
        return bool(campsite_type) and channel.applies_to == campsite_type

    # `all` first: the District-wide contact reads as context for the
    # class-specific method that follows it, not as a competing answer. Within a
    # class, the agency-wide row reads before a park's narrower one, so Coyote
    # Hills' five-working-day deadline lands as a tightening of the District's
    # three rather than as a free-standing claim.
    return sorted((c for c in channels if applies(c)),
                  key=lambda c: (c.applies_to != ALL,
                                 SPECIFICITY.get(c.scope_type, 0) * -1,
                                 c.channel_id))


@dataclass
class BookingFacility:
    """One row of ``data/booking_facilities.csv``: a page in a booking system.

    THE LEVEL ABOVE A CAMPGROUND, AND IT IS NOT A PARK. A ReserveAmerica
    facility is the thing a booking URL names -- ``EB/110028``, slug ``sunol``
    -- and EBRPD's facilities do not line up with EBRPD's parks in either
    direction. EB/110028 sells nineteen backpack sites across THREE parks under
    one listing, while Del Valle Regional Park is sold through TWO facilities:
    EB/110003 for its family campground, group camps and horse camps, and
    EB/110028 for its four Ohlone corridor backpack camps.

    That is why :attr:`Campground.facility_id` is a stored column and not
    something derived from a campground's park. A park cannot supply it, and a
    campground's own ``source_url`` only sometimes carries it -- the seven
    Anthony Chabot group camps are sourced to a District PDF and Dumbarton
    Quarry to an ebparks.org page, and all eight belong to facilities anyway.
    """

    facility_id: str
    """The booking system's own key, e.g. ``EB/110003``. Primary key here."""
    operator: str = ""
    """Who runs the booking system, e.g. ``ReserveAmerica``. A column rather
    than an assumption: EBRPD backpack and group sites are phone-only through
    the District, and the day a second operator appears, nothing here should
    have to be renamed."""
    slug: str = ""
    """The URL segment, e.g. ``del-valle``.

    Stored separately from :attr:`facility_name` because the two are NOT the
    same and this project has the counterexample: EB/110028's slug is ``sunol``
    and its published title is ``Sunol`` -- neither of which is the park's name,
    which is Sunol Regional Wilderness. A slug is a URL segment. Treating one as
    a name is one step from constructing a URL out of a name, which is exactly
    how two citations came to be fabricated here.
    """
    facility_name: str = ""
    """The operator's own published title, or ``""`` where nobody has read it.

    Twelve of thirteen are blank and honestly so. The one that is filled is the
    one that matters: ``Sunol``, which is what showed that a slug is not a name.
    """
    land_agency: str = ""
    agency_id: str = ""
    url: str = ""
    verified_date: str = ""
    notes: str = ""
    log_entry_ids: str = ""


def load_booking_facilities(
    path: str | Path = "data/booking_facilities.csv",
) -> List[BookingFacility]:
    """Load booking facilities. Empty list if the file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return []
    df = pd.read_csv(path)

    out: List[BookingFacility] = []
    seen_id: dict = {}
    seen_slug: dict = {}
    for _, row in df.iterrows():
        facility_id = _str_field(row, "facility_id")
        if not facility_id:
            continue
        slug = _str_field(row, "slug")
        # The bijection guard, at load rather than only in a test. A repeated ID
        # under two slugs is the exact shape of the fabricated citation that put
        # Las Trampas' 110455 under a del-valle slug.
        if facility_id in seen_id:
            raise ValueError(
                f"Facility {facility_id!r} appears twice, under slugs "
                f"{seen_id[facility_id]!r} and {slug!r}"
            )
        if slug and slug in seen_slug:
            raise ValueError(
                f"Slug {slug!r} appears under two facility ids "
                f"{seen_slug[slug]!r} and {facility_id!r}"
            )
        seen_id[facility_id] = slug
        if slug:
            seen_slug[slug] = facility_id
        out.append(BookingFacility(
            facility_id=facility_id,
            operator=_str_field(row, "operator"),
            slug=slug,
            facility_name=_str_field(row, "facility_name"),
            land_agency=_str_field(row, "land_agency"),
            agency_id=_str_field(row, "agency_id"),
            url=_str_field(row, "url"),
            verified_date=_str_field(row, "verified_date"),
            notes=_str_field(row, "notes"),
            log_entry_ids=_str_field(row, "log_entry_ids"),
        ))
    return out


def facility_for(
    campground, facilities: Sequence[BookingFacility]
) -> "BookingFacility | None":
    """The facility a campground books through, or ``None`` when unrecorded.

    ``None`` is never filled in from the campground's park. Del Valle has two
    facilities and Coyote Hills has two, so a park cannot answer this, and the
    one campground with no key -- Lil Chaparral Horse Camp, named on a map and
    absent from the Del Valle page that was read -- would get the wrong one
    exactly as often as the right one.
    """
    if not getattr(campground, "facility_id", ""):
        return None
    for f in facilities:
        if f.facility_id == campground.facility_id:
            return f
    return None


def facility_label(facility: "BookingFacility | None") -> str:
    """How to name a facility to a reader, title or slug, never inventing one."""
    if facility is None:
        return UNKNOWN_FACILITY_LABEL
    if facility.facility_name:
        return f"{facility.facility_name} ({facility.facility_id})"
    # No published title has been read, so the URL segment stands in and says
    # so. Dressing the slug up as a name is how 'del-valle-regional-park'
    # became a citation.
    return f"{facility.facility_id}, slug '{facility.slug}'"


def parks_by_facility(campgrounds: Sequence) -> "dict[str, set]":
    """``facility_id -> {park}``, for the facilities that span several."""
    out: dict = {}
    for c in campgrounds:
        if getattr(c, "facility_id", ""):
            out.setdefault(c.facility_id, set()).add(c.park)
    return out


def facilities_by_park(campgrounds: Sequence) -> "dict[str, set]":
    """``park -> {facility_id}``, for the parks sold through several."""
    out: dict = {}
    for c in campgrounds:
        if getattr(c, "facility_id", ""):
            out.setdefault(c.park, set()).add(c.facility_id)
    return out


def dangling_facility_ids(
    campgrounds: Sequence, facilities: Sequence[BookingFacility]
) -> List[str]:
    """Campground names whose ``facility_id`` matches no facility row."""
    known = {f.facility_id for f in facilities}
    return [c.name for c in campgrounds
            if getattr(c, "facility_id", "") and c.facility_id not in known]


def facilities_without_campgrounds(
    campgrounds: Sequence, facilities: Sequence[BookingFacility]
) -> List[BookingFacility]:
    """Facilities no campground books through -- the other end of the join."""
    used = {getattr(c, "facility_id", "") for c in campgrounds}
    return [f for f in facilities if f.facility_id not in used]
