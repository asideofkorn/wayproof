"""Tests for the campground/campsite, water-source, and park-access modules.

Run with:  python -m pytest tests/test_facilities.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from wayproof.camping import (
    DRIVE_IN,
    HIKE_IN,
    UNKNOWN_ACCESS_LABEL,
    Campground,
    Campsite,
    access_label,
    drive_in,
    load_campgrounds,
    load_campsites,
    campsites_by_campground,
    unknown_access,
)
from wayproof.water import (
    WaterSource,
    WaterSourceLogEntry,
    load_water_sources,
    load_water_source_log,
    log_by_source,
    latest_status_by_source,
)
from wayproof.park_access import ParkAccess, load_park_access

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
CAMPGROUNDS = os.path.join(DATA, "campgrounds.csv")
CAMPSITES = os.path.join(DATA, "campsites.csv")
WATER_SOURCES = os.path.join(DATA, "water_sources.csv")
WATER_SOURCE_LOG = os.path.join(DATA, "water_source_log.csv")
PARK_ACCESS = os.path.join(DATA, "park_access.csv")


# --- campgrounds / campsites -------------------------------------------------

def test_load_campgrounds_reads_committed_data():
    campgrounds = load_campgrounds(CAMPGROUNDS)
    by_name = {c.name: c for c in campgrounds}
    assert "Sunol Backpack Camp" in by_name
    sunol = by_name["Sunol Backpack Camp"]
    assert sunol.has_restroom is True
    assert sunol.restroom_type == "pit toilet"
    # Phone only. This row used to name ReserveAmerica; EBRPD's reservations
    # page states that backpack and group campsites are not bookable online at
    # all, and sending someone to a website that cannot sell them the site is
    # the "implies online booking where the channel is phone-only" failure.
    assert "Phone only" in sunol.reservation_method
    assert "ReserveAmerica" not in sunol.reservation_method


def test_family_campgrounds_book_online_and_backpack_ones_do_not():
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    for name in ("Del Valle Family Campground", "Anthony Chabot Campground",
                 "Dumbarton Quarry Campground on the Bay"):
        assert "reserveamerica.com" in by_name[name].reservation_method.lower(), name
    for name in ("Boyd Camp", "Sunol Backpack Camp", "Eagle Springs"):
        assert "Phone only" in by_name[name].reservation_method, name


def test_every_campground_warns_that_email_books_nothing():
    # EBRPD publishes a reservations email address that accepts no
    # reservations. Someone who emails it and waits has not booked a site.
    for c in load_campgrounds(CAMPGROUNDS):
        assert "no reservation is accepted by email" in c.reservation_contact.lower(), c.name


def test_load_campgrounds_missing_file_returns_empty(tmp_path):
    assert load_campgrounds(tmp_path / "nope.csv") == []


def test_del_valle_family_campground_has_nightly_cutoff_caveat():
    campgrounds = load_campgrounds(CAMPGROUNDS)
    by_name = {c.name: c for c in campgrounds}
    del_valle = by_name["Del Valle Family Campground"]
    assert "10:00 PM" in del_valle.nightly_entry_cutoff
    assert "approximate" in del_valle.nightly_entry_cutoff.lower()


def test_load_campsites_reads_committed_data():
    sites = load_campsites(CAMPSITES)
    by_name = {s.name: s for s in sites}
    assert by_name["Eagles Aerie"].capacity == 10
    assert by_name["Hawks Nest"].water_proximity == "closest to water"
    assert by_name["Hawks Nest"].restroom_proximity == "near-ish"
    # Sites with no noted proximity difference stay blank rather than guessed.
    assert by_name["Cathedral"].water_proximity == ""


def test_load_campsites_missing_file_returns_empty(tmp_path):
    assert load_campsites(tmp_path / "nope.csv") == []


def test_campsites_by_campground_groups_all_seven_sunol_sites():
    sites = load_campsites(CAMPSITES)
    grouped = campsites_by_campground(sites)
    assert len(grouped["Sunol Backpack Camp"]) == 7


def test_single_site_campgrounds_have_no_campsites_rows():
    # Boyd Camp etc. aren't split into named sub-sites -- no placeholder rows
    # that just repeat the campground's own name.
    sites = load_campsites(CAMPSITES)
    names = {s.campground for s in sites}
    assert names == {"Sunol Backpack Camp"}


# --- water sources / ledger ---------------------------------------------------

def test_load_water_sources_reads_committed_data():
    sources = load_water_sources(WATER_SOURCES)
    by_name = {s.name: s for s in sources}
    assert "Sunol Backpack Camp" in by_name
    stromer = by_name["Stromer Springs"]
    assert stromer.potable is False
    assert stromer.type == "spigot (spring-fed)"


def test_load_water_sources_missing_file_returns_empty(tmp_path):
    assert load_water_sources(tmp_path / "nope.csv") == []


def test_load_water_source_log_reads_committed_data():
    entries = load_water_source_log(WATER_SOURCE_LOG)
    assert len(entries) > 0
    assert all(isinstance(e, WaterSourceLogEntry) for e in entries)


def test_boyd_camp_has_official_and_conflicting_field_entries():
    entries = load_water_source_log(WATER_SOURCE_LOG)
    boyd = [e for e in entries if e.water_source_name == "Boyd Camp"]
    assert len(boyd) == 2
    official = [e for e in boyd if "EBRPD" in e.source]
    assert official and official[0].observed_status == "running"
    conflicting = [e for e in boyd if "contradicts" in e.observed_status]
    assert conflicting


def test_latest_status_by_source_picks_newest_dated_entry():
    entries = [
        WaterSourceLogEntry("Test Spring", "2026-01-01", "official", "running"),
        WaterSourceLogEntry("Test Spring", "2026-06-01", "field report", "dry"),
    ]
    latest = latest_status_by_source(entries)
    assert latest["Test Spring"].observed_status == "dry"
    assert latest["Test Spring"].checked_date == "2026-06-01"


def test_log_by_source_orders_oldest_to_newest():
    entries = [
        WaterSourceLogEntry("Test Spring", "2026-06-01", "b", "dry"),
        WaterSourceLogEntry("Test Spring", "2026-01-01", "a", "running"),
    ]
    grouped = log_by_source(entries)
    dates = [e.checked_date for e in grouped["Test Spring"]]
    assert dates == ["2026-01-01", "2026-06-01"]


# --- park access ---------------------------------------------------------------

def test_load_park_access_reads_committed_data():
    by_park = load_park_access(PARK_ACCESS)
    assert "Del Valle Regional Park" in by_park
    del_valle = by_park["Del Valle Regional Park"]
    assert del_valle.entrance_fee == "$10"
    assert del_valle.gate_open == "6:00 AM"
    assert "shuttled car" in del_valle.fee_exemptions


def test_park_access_fee_exemption_confidence_is_documented_separately():
    by_park = load_park_access(PARK_ACCESS)
    del_valle = by_park["Del Valle Regional Park"]
    # The exemption is a verbal staff confirmation, not an independently
    # published fact -- that distinction must survive into the data, not be
    # silently flattened to the same confidence as the fee/hours.
    assert "verbal" in del_valle.fee_exemptions.lower() or "verbal" in del_valle.notes.lower()


def test_load_park_access_missing_file_returns_empty_dict(tmp_path):
    assert load_park_access(tmp_path / "nope.csv") == {}


# --- campground access mode (drive-in vs hike-in) ----------------------------

def test_the_ohlone_corridor_camps_are_hike_in_and_the_family_ones_are_not():
    # The six Ohlone Wilderness Trail backpack camps are reached on foot; the
    # family campgrounds are reached by car. Getting this backwards means
    # booking a site up to 16.7 trail miles from where you parked.
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    on_foot = {"Boyd Camp", "Stewart's Camp", "Maggie's Half Acre", "Doe Camp",
               "Sunol Backpack Camp", "Eagle Springs"}
    by_car = {"Del Valle Family Campground", "Anthony Chabot Campground",
              "Dumbarton Quarry Campground on the Bay"}
    assert on_foot | by_car == set(by_name), "a campground is unclassified above"
    assert {by_name[n].access_mode for n in on_foot} == {HIKE_IN}
    assert {by_name[n].access_mode for n in by_car} == {DRIVE_IN}


def test_an_unverified_campground_says_so_rather_than_reading_as_checked():
    # Anthony Chabot and Dumbarton Quarry were built from web-search summaries
    # of pages nobody here could open. They carry a source to check against and
    # a blank verified_date, which is the difference between "not yet confirmed"
    # and "confirmed" -- and their notes must say which facts are in doubt.
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    for name in ("Anthony Chabot Campground", "Dumbarton Quarry Campground on the Bay"):
        cg = by_name[name]
        assert cg.source_url.startswith("https://www.ebparks.org/"), name
        assert cg.verified_date == "", f"{name} must not claim a verification"
        assert "unconfirmed" in cg.notes.lower(), name
        # Absent is not free: no fee was invented for a row nobody has checked.
        assert cg.fee_notes == "", name


def test_every_committed_campground_states_its_access_mode():
    # Not a style rule: a blank here reads as "nobody checked", and shipping a
    # dataset that is silently all-unknown would make the column decorative.
    assert unknown_access(load_campgrounds(CAMPGROUNDS)) == []


def test_blank_access_mode_reads_as_unrecorded_not_as_a_mode():
    unknown = Campground(name="Somewhere", park="P")
    assert unknown.access_mode == ""
    assert access_label(unknown) == UNKNOWN_ACCESS_LABEL
    # Absent is not a value: it must not be counted as drivable.
    assert drive_in([unknown]) == []
    assert unknown_access([unknown]) == [unknown]


def test_access_label_renders_both_known_modes():
    assert access_label(Campground("A", "P", access_mode=DRIVE_IN)) == "drive-in"
    assert access_label(Campground("B", "P", access_mode=HIKE_IN)) == "hike-in"


def test_unknown_access_mode_value_is_rejected_loudly(tmp_path):
    # A typo must fail the load rather than silently becoming "not recorded",
    # which would be indistinguishable from an honest gap.
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,land_agency,access_mode\nX Camp,P,A,driveable\n")
    with pytest.raises(ValueError, match="access_mode"):
        load_campgrounds(path)


def test_access_mode_may_be_blank_in_a_file(tmp_path):
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,land_agency,access_mode\nX Camp,P,A,\n")
    assert load_campgrounds(path)[0].access_mode == ""
