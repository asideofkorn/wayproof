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

from .regulations import scope_applies

ALL = "all"
FAMILY = "family"
GROUP = "group"
BACKPACK = "backpack"
_VALID_APPLIES_TO = {ALL, FAMILY, GROUP, BACKPACK}

APPLIES_TO_LABELS = {
    ALL: "Any campsite",
    FAMILY: "Family campsites",
    GROUP: "Group campsites",
    BACKPACK: "Backpack campsites",
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
    """What looks like a booking channel and is not.

    Its own field for the same reason :attr:`wayproof.permits.PermitRule.carry`
    is: being wrong about it is discovered too late to fix. EBRPD publishes a
    reservations email address that accepts no reservations, and someone who
    emails it and waits has not booked anything -- they find that out when the
    site is gone.
    """
    lead_time: str = ""
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
) -> List[BookingChannel]:
    """Channels reaching one class of campsite, general ones first.

    A blank ``campsite_type`` means the caller does not know what class of site
    is being booked, so only ``all`` channels are returned. Guessing ``family``
    there would tell a backpacker to book online, which EBRPD does not allow.
    """
    def applies(channel: BookingChannel) -> bool:
        if not scope_applies(channel.scope_type, channel.scope_value,
                             permit_group=permit_group, agency=agency,
                             jurisdiction=jurisdiction, wilderness=wilderness):
            return False
        if channel.applies_to == ALL:
            return True
        return bool(campsite_type) and channel.applies_to == campsite_type

    # `all` first: the District-wide contact reads as context for the
    # class-specific method that follows it, not as a competing answer.
    return sorted((c for c in channels if applies(c)),
                  key=lambda c: (c.applies_to != ALL, c.channel_id))
