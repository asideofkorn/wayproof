"""Every cross-file join in data/ resolves.

Twenty-one CSVs are related by roughly a dozen joins keyed on hand-typed free
text -- a peak name, a trailhead name, a permit_group, a campground name. None
of those joins is declared anywhere, and the loaders fail silently when one
breaks: ``wayproof.data_loader.load_peaks`` merges the collection file with
``how="left"``, so a single casing difference in a name drops that peak's
collection metadata with no error, and because ``--list SPS`` then filters on a
now-blank ``list`` column, the peak disappears from the dataset entirely.

So the joins are asserted here rather than trusted. Deliberately read with the
stdlib ``csv`` module rather than through the loaders: the point is to guard the
*data files*, so a change in loader behaviour cannot mask a break.

This file matters most while the schema is being reshaped. Every new join
(peak_id/peak_aliases, land_unit_id, entry_trail_id) belongs here in the same
change that introduces it, not in a cleanup pass afterwards.

Run with:  python -m pytest tests/test_referential_integrity.py
"""

from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def rows(name: str) -> list:
    with open(os.path.join(DATA, name), newline="") as fh:
        return list(csv.DictReader(fh))


def values(name: str, column: str) -> set:
    """Non-blank values of one column."""
    return {r[column].strip() for r in rows(name) if r[column].strip()}


def ids(name: str, column: str) -> set:
    """Non-blank values of a semicolon-separated list column, flattened."""
    out = set()
    for r in rows(name):
        out.update(p.strip() for p in r[column].split(";") if p.strip())
    return out


def scoped(scope_type: str) -> set:
    """`regulations.scope_value` for one scope_type."""
    return {r["scope_value"].strip() for r in rows("regulations.csv")
            if r["scope_type"].strip() == scope_type and r["scope_value"].strip()}


# `park` is referenced by three files and keyed by none of them: it has no table
# of its own, so a park with a campground but no trailhead (Sunol) is neither a
# broken reference nor a satisfied one. PR B2's `land_units.csv` gives it a key
# and this allowlist goes away. Until then a NEW orphan still fails.
UNKEYED_PARKS = {"Sunol Regional Wilderness"}


#: ``(label, child values, parent values)`` -- every declared join in data/.
JOINS = [
    ("approaches.peak_name -> peaks.name",
     lambda: values("approaches.csv", "peak_name"), lambda: values("peaks.csv", "name")),
    ("approaches.trailhead -> trailheads.name",
     lambda: values("approaches.csv", "trailhead"), lambda: values("trailheads.csv", "name")),
    ("approaches.permit_group -> permits.permit_group",
     lambda: values("approaches.csv", "permit_group"),
     lambda: values("permits.csv", "permit_group")),
    ("trailheads.permit_group -> permits.permit_group",
     lambda: values("trailheads.csv", "permit_group"),
     lambda: values("permits.csv", "permit_group")),
    ("collections/sps.csv.name -> peaks.name",
     lambda: values(os.path.join("collections", "sps.csv"), "name"),
     lambda: values("peaks.csv", "name")),
    ("campsites.campground -> campgrounds.name",
     lambda: values("campsites.csv", "campground"), lambda: values("campgrounds.csv", "name")),
    ("water_source_log.water_source_name -> water_sources.name",
     lambda: values("water_source_log.csv", "water_source_name"),
     lambda: values("water_sources.csv", "name")),
    ("water_sources.location -> trailheads.name | campgrounds.name",
     lambda: values("water_sources.csv", "location"),
     lambda: values("trailheads.csv", "name") | values("campgrounds.csv", "name")),
    ("permit_zones.permit_group -> permits.permit_group",
     lambda: values("permit_zones.csv", "permit_group"),
     lambda: values("permits.csv", "permit_group")),
    ("permits.log_entry_ids -> permit_source_log.entry_id",
     lambda: ids("permits.csv", "log_entry_ids"),
     lambda: values("permit_source_log.csv", "entry_id")),
    ("regulations.log_entry_ids -> permit_source_log.entry_id",
     lambda: ids("regulations.csv", "log_entry_ids"),
     lambda: values("permit_source_log.csv", "entry_id")),
    ("permit_source_log.permit_group -> permits.permit_group",
     lambda: values("permit_source_log.csv", "permit_group"),
     lambda: values("permits.csv", "permit_group")),
    ("regulations[scope=permit_group] -> permits.permit_group",
     lambda: scoped("permit_group"), lambda: values("permits.csv", "permit_group")),
    ("regulations[scope=wilderness] -> permits.wilderness_area",
     lambda: scoped("wilderness"), lambda: values("permits.csv", "wilderness_area")),
    # Both sides, because agency identity lives in two places: a permit row
    # carries its issuer, and a trailhead carries the agency whose land it is
    # on. Permit-free land (permit_group "none") has only the latter -- EBRPD's
    # rules exist under no permit at all -- so scoping this join to permits.csv
    # alone would reject every rule written for land you can walk onto freely.
    ("regulations[scope=agency] -> permits.agency_id | trailheads.agency_id",
     lambda: scoped("agency"),
     lambda: ids("permits.csv", "agency_id") | ids("trailheads.csv", "agency_id")),
    ("regulations[scope=jurisdiction] -> permits.jurisdiction",
     lambda: scoped("jurisdiction"), lambda: values("permits.csv", "jurisdiction")),
    ("campgrounds.park -> trailheads.park | park_access.park",
     lambda: values("campgrounds.csv", "park") - UNKEYED_PARKS,
     lambda: values("trailheads.csv", "park") | values("park_access.csv", "park")),
    ("park_access.park -> trailheads.park | campgrounds.park",
     lambda: values("park_access.csv", "park"),
     lambda: values("trailheads.csv", "park") | values("campgrounds.csv", "park")),
]


@pytest.mark.parametrize("label,child,parent", JOINS, ids=[j[0] for j in JOINS])
def test_join_resolves(label, child, parent):
    orphans = sorted(child() - parent())
    assert orphans == [], f"{label}: unresolvable value(s) {orphans}"


# -- keys that must stay usable as keys -------------------------------------

@pytest.mark.parametrize("filename", ["permits.csv", "trailheads.csv"])
def test_agency_id_values_are_keys_not_display_names(filename):
    # This column exists because matching on the display string silently made a
    # forest-wide rule apply to nobody. A value that looks like prose invites
    # exactly that mistake back in.
    bad = sorted(a for a in ids(filename, "agency_id")
                 if not re.fullmatch(r"[a-z0-9_]+", a))
    assert bad == [], f"{filename} agency_id must be lowercase snake_case keys: {bad}"


def test_peak_names_are_unique_case_insensitively():
    # The collection join is case-SENSITIVE (pandas merge on `name`) while
    # plan.py's lookup is case-INSENSITIVE, so a case-only duplicate is
    # resolvable by one path and ambiguous by the other.
    counts = Counter(r["name"].strip().lower() for r in rows("peaks.csv"))
    dupes = sorted(n for n, c in counts.items() if c > 1)
    assert dupes == [], f"names differing only by case: {dupes}"


def test_no_key_column_carries_leading_or_trailing_whitespace():
    # A trailing space is invisible in a diff and breaks an exact-match join.
    checks = [
        ("peaks.csv", "name"), ("trailheads.csv", "name"),
        ("permits.csv", "permit_group"), ("campgrounds.csv", "name"),
        ("campsites.csv", "campground"), ("water_sources.csv", "name"),
        (os.path.join("collections", "sps.csv"), "name"),
    ]
    bad = [f"{f}:{c}={v!r}" for f, c in checks
           for v in (r[c] for r in rows(f)) if v != v.strip()]
    assert bad == [], f"key values with surrounding whitespace: {bad}"


def test_every_pending_report_targets_a_real_file():
    missing = sorted({r["target_file"] for r in rows("pending_reports.csv")
                      if r["target_file"].strip()
                      and not os.path.exists(os.path.join(ROOT, r["target_file"].strip()))})
    assert missing == [], f"reports filed against files that do not exist: {missing}"
