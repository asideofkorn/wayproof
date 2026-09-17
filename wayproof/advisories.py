"""Conditions that are true today and will stop being true.

Every other table here holds facts that stay true until someone corrects them:
a permit's quota, a leash rule, a campground's fee. An advisory is different in
kind. A trail is closed *until the culvert is repaired*; an algae warning is
posted *this week*; a water supply is off *until further notice*. The fact has
an end, and the end is usually not written down.

That is why the scorecard reports "What is closed?" as no-model for every
objective in this project: there was nowhere to put a fact that expires, so
sixty live District notices -- trail closures across six parks, algae
advisories, a mussel quarantine, a boil-water notice -- were read and dropped.

Storing them badly would be worse than dropping them. A closure copied here in
September and read in March is not stale data, it is a wrong answer with a
date on it, and this project's whole argument is that those are worse than
silence. So three things are structural rather than optional:

- **``observed_date`` is required.** An advisory with no date is refused at
  load. It is the only thing that lets a reader judge the rest.
- **``ends`` and ``until_further_notice`` are separate.** A closure that ends
  on a stated date can be resolved against a trip date and dropped when it
  passes. One with no end cannot, and must never be quietly treated as though
  it had expired.
- **Age is reported, not hidden.** An open-ended advisory read months ago is
  the dangerous case: it may have been lifted the week after, and nothing here
  would know. :func:`stale` says so instead of letting it read as current.

Scope reuses :func:`wayproof.regulations.scope_applies`, the same four-way
logic regulations and booking channels resolve on -- which is what that
function was split out for, its own docstring naming "conditions, hazards,
seasonal access" as the cases to come.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional, Sequence

import pandas as pd

from .regulations import scope_applies

TRAIL_CLOSURE = "trail_closure"
AREA_CLOSURE = "area_closure"
WATER_OUTAGE = "water_outage"
WATER_QUALITY = "water_quality"
FIRE = "fire"
FACILITY = "facility"
OTHER = "other"
_VALID_KINDS = {TRAIL_CLOSURE, AREA_CLOSURE, WATER_OUTAGE, WATER_QUALITY,
                FIRE, FACILITY, OTHER}

KIND_LABELS = {
    TRAIL_CLOSURE: "Trail closure",
    AREA_CLOSURE: "Area closure",
    WATER_OUTAGE: "Water out",
    WATER_QUALITY: "Water quality",
    FIRE: "Fire restriction",
    FACILITY: "Facility",
    OTHER: "Notice",
}

INFO, CAUTION, DANGER = "info", "caution", "danger"
_VALID_SEVERITY = {INFO, CAUTION, DANGER}

STALE_DAYS = 30
"""How long an open-ended advisory goes before its age is worth flagging.

A month is not a claim about how long closures last -- it is how long this
project is willing to repeat one without saying when it last looked. Storm
damage can be repaired in a fortnight and an algae bloom clears faster than
that, so a notice older than this is as likely to be wrong as right.
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


def _as_date(text: str) -> Optional[date]:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


@dataclass
class Advisory:
    """One row of ``data/advisories.csv``: a condition with an end."""

    advisory_id: str
    scope_type: str
    scope_value: str
    kind: str
    summary: str
    observed_date: str
    """When the issuing agency last updated this, or failing that when it was
    read here. Required -- see the module docstring."""
    severity: str = INFO
    location: str = ""
    """The specific trail, beach or facility, which scope cannot express: this
    project has no trail entity, and inventing one to hold a closure would be a
    route model built by accident."""
    detail: str = ""
    starts: str = ""
    ends: str = ""
    until_further_notice: bool = False
    source_url: str = ""
    verified_date: str = ""
    log_entry_ids: str = ""
    scope_display: str = ""

    @property
    def scope_label(self) -> str:
        return self.scope_display or self.scope_value

    @property
    def kind_label(self) -> str:
        return KIND_LABELS.get(self.kind, self.kind.replace("_", " ").capitalize())

    def in_force(self, on: date) -> bool:
        """Is this advisory in force on ``on``?

        An advisory with a stated end is dropped once the date passes. One with
        no stated end is ALWAYS in force, however old -- the agency has not
        said it is over, and deciding that for them is exactly the confident
        wrong answer this table risks. Pair it with :meth:`stale`.
        """
        starts = _as_date(self.starts)
        if starts and on < starts:
            return False
        ends = _as_date(self.ends)
        if ends and on > ends:
            return False
        return True

    def age_days(self, today: date) -> Optional[int]:
        observed = _as_date(self.observed_date)
        return (today - observed).days if observed else None

    def stale(self, today: date) -> bool:
        """True when this has gone unchecked long enough to be doubted.

        Only ever true for an open-ended advisory. One with a stated end is
        either in force or over; its age says nothing about which.
        """
        if self.ends:
            return False
        age = self.age_days(today)
        return age is not None and age > STALE_DAYS


def load_advisories(path: str | Path = "data/advisories.csv") -> List[Advisory]:
    """Load advisories. Empty list if the file doesn't exist."""
    path = Path(path)
    if not path.exists():
        return []
    df = pd.read_csv(path)

    out: List[Advisory] = []
    for _, row in df.iterrows():
        advisory_id = _str_field(row, "advisory_id")
        if not advisory_id:
            continue
        kind = _str_field(row, "kind")
        if kind not in _VALID_KINDS:
            raise ValueError(
                f"Invalid kind {kind!r} for advisory {advisory_id!r}; "
                f"expected one of {sorted(_VALID_KINDS)}"
            )
        severity = _str_field(row, "severity") or INFO
        if severity not in _VALID_SEVERITY:
            raise ValueError(
                f"Invalid severity {severity!r} for advisory {advisory_id!r}; "
                f"expected one of {sorted(_VALID_SEVERITY)}"
            )
        observed = _str_field(row, "observed_date")
        if not _as_date(observed):
            raise ValueError(
                f"Advisory {advisory_id!r} has no usable observed_date "
                f"({observed!r}). A condition with no date cannot be judged, and "
                "repeating one is how a lifted closure outlives the closure."
            )
        ends = _str_field(row, "ends")
        ufn = _bool_field(row, "until_further_notice")
        if ends and ufn:
            raise ValueError(
                f"Advisory {advisory_id!r} states both an end date ({ends}) and "
                "until_further_notice. They are the two answers this table "
                "exists to keep apart."
            )
        out.append(Advisory(
            advisory_id=advisory_id,
            scope_type=_str_field(row, "scope_type"),
            scope_value=_str_field(row, "scope_value"),
            kind=kind, severity=severity,
            summary=_str_field(row, "summary"),
            location=_str_field(row, "location"),
            detail=_str_field(row, "detail"),
            observed_date=observed,
            starts=_str_field(row, "starts"), ends=ends,
            until_further_notice=ufn,
            source_url=_str_field(row, "source_url"),
            verified_date=_str_field(row, "verified_date"),
            log_entry_ids=_str_field(row, "log_entry_ids"),
            scope_display=_str_field(row, "scope_display"),
        ))
    return out


_SEVERITY_RANK = {DANGER: 0, CAUTION: 1, INFO: 2}


def advisories_for(
    advisories: Sequence[Advisory],
    on: date,
    permit_group: str = "",
    agency: "str | Sequence[str]" = "",
    jurisdiction: str = "",
    wilderness: str = "",
    park: str = "",
) -> List[Advisory]:
    """Advisories in force on ``on`` for this scope, worst first.

    Filtered by date as well as scope, so a trip planned after a stated
    reopening is not warned about a closure that will be over. Open-ended ones
    survive every date, which is the point.
    """
    def applies(a: Advisory) -> bool:
        return a.in_force(on) and scope_applies(
            a.scope_type, a.scope_value, permit_group=permit_group, agency=agency,
            jurisdiction=jurisdiction, wilderness=wilderness, park=park)

    return sorted((a for a in advisories if applies(a)),
                  key=lambda a: (_SEVERITY_RANK.get(a.severity, 3), a.advisory_id))
