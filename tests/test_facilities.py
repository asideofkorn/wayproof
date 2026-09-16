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
    RV_HOOKUP,
    TENT_DRIVE_UP,
    TENT_HIKE_IN,
    site_type_label,
    sites_by_type,
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
    assert sunol.campsite_type == "backpack"


def test_the_district_wide_contact_is_not_copied_into_every_campground():
    # It was, in nine rows, and would have been in twenty-one. That is the shape
    # of the campfire permit copied into seven permits.csv rows, which drifted
    # five ways. It lives in booking_channels.csv now, once.
    for c in load_campgrounds(CAMPGROUNDS):
        assert c.reservation_contact == "", (
            f"{c.name} carries a contact of its own; agency-wide booking "
            "mechanics belong in data/booking_channels.csv")
        # "option 2" is the reservations line. Anthony Chabot's row keeps its
        # PARK office number, which shares the toll-free root but is a different
        # option and extension -- that is campground-specific, not duplicated.
        assert "option 2" not in c.reservation_method, c.name


def test_campsite_type_is_set_for_every_campground():
    # Blank means booking resolves only agency-wide channels, so a backpacker
    # would never be told their sites are phone-only.
    blank = [c.name for c in load_campgrounds(CAMPGROUNDS) if not c.campsite_type]
    assert blank == [], f"campgrounds with no campsite_type: {blank}"


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
    # that just repeat the campground's own name. Sunol's sites differ by water
    # and restroom proximity; Anthony Chabot's differ by loop and type.
    sites = load_campsites(CAMPSITES)
    names = {s.campground for s in sites}
    assert names == {"Sunol Backpack Camp", "Anthony Chabot Campground"}


def test_chabots_site_types_reproduce_the_booking_systems_own_filter_counts():
    # 11 RV hookup, 10 tent-only (walk-in), 48 tent/no-hookup. If a row is
    # mistyped the totals stop matching the source they were read from.
    sites = [s for s in load_campsites(CAMPSITES)
             if s.campground == "Anthony Chabot Campground"]
    assert len(sites) == 75, "75 individual sites exist; the group camps are not among them"
    counts = {t: len(g) for t, g in sites_by_type(sites).items()}
    assert counts[RV_HOOKUP] == 11
    assert counts[TENT_HIKE_IN] == 10
    assert counts[TENT_DRIVE_UP] == 48
    assert counts[""] == 6, "the six unlisted sites must not be typed by inference"


def test_the_six_unlisted_sites_are_present_but_not_marked_bookable():
    # They exist, so leaving them out would rebuild the online listing's own
    # blind spot inside this table.
    sites = {s.name: s for s in load_campsites(CAMPSITES)
             if s.campground == "Anthony Chabot Campground"}
    offline = sorted(n for n, s in sites.items() if not s.online_bookable)
    assert offline == ["010", "031", "033", "039", "053", "075"]
    for name in offline:
        assert sites[name].loop, f"{name} should still carry its loop, which the ranges give"
        assert sites[name].site_type == "", f"{name}'s type is not stated by any source"


def test_walk_in_sites_are_not_labelled_with_the_booking_systems_wording():
    # ReserveAmerica calls the ten walk-in sites "Tent Only" and the forty-eight
    # drive-up ones "Tent/No-Hookup". Carrying that through would send someone
    # filtering for a tent site to the ones 1,000 feet from their car.
    sites = [s for s in load_campsites(CAMPSITES)
             if s.campground == "Anthony Chabot Campground"]
    walk_in = [s for s in sites if s.site_type == TENT_HIKE_IN]
    assert all("Hike-In" in s.loop for s in walk_in)
    assert site_type_label(walk_in[0]) == "walk-in tent site"
    assert all("1,000 feet" in s.notes for s in walk_in)


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


def test_boyd_camp_keeps_every_check_including_the_one_that_disagreed():
    # The ledger is append-only: a later check never overwrites an earlier one.
    # Boyd Camp has an official update, this project's own field note
    # contradicting it, and a newer official update -- and all three stay.
    entries = load_water_source_log(WATER_SOURCE_LOG)
    boyd = [e for e in entries if e.water_source_name == "Boyd Camp"]
    assert len(boyd) == 3
    official = [e for e in boyd if "EBRPD" in e.source]
    assert len(official) == 2 and {e.observed_status for e in official} == {"running"}
    conflicting = [e for e in boyd if "contradicts" in e.observed_status]
    assert conflicting, "the disagreement must survive the newer official check"
    # Newest wins for "what is it doing now", without erasing the doubt.
    assert latest_status_by_source(entries)["Boyd Camp"].checked_date == "2026-09-15"


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

# Campgrounds whose source says nothing about how you reach them. Blank is the
# honest value: every other EBRPD group camp here is drive-in, and that is not
# evidence about these three. Named individually so a NEW blank still fails.
# Empty again: Briones' three were here until the maintainer supplied the mode
# directly. Kept because the state recurs -- EBRPD publishes capacity, fees and
# minimums for a group camp without ever saying how you reach it.
ACCESS_MODE_UNRECORDED: set = set()


def test_backpack_sites_are_walked_to_and_family_and_group_sites_are_driven_to():
    # Stated as a rule rather than a list of names, so it keeps holding as the
    # District's parks land. Getting it backwards means booking a site up to
    # 16.7 trail miles from where you parked.
    # Group camps are NOT uniformly drive-in, and assuming so was wrong: Star
    # Mine is classified Hike-In with its parking a quarter mile off. So the
    # rule holds for backpack and family sites, and group sites are checked
    # only for carrying a mode at all.
    expected = {"backpack": HIKE_IN, "family": DRIVE_IN}
    for c in load_campgrounds(CAMPGROUNDS):
        assert c.campsite_type in ("backpack", "family", "group"), (
            f"{c.name}: unclassified campsite_type")
        if c.name in ACCESS_MODE_UNRECORDED:
            assert c.access_mode == "", f"{c.name} is listed as unrecorded but has a mode"
            continue
        if c.campsite_type == "group":
            assert c.access_mode in (DRIVE_IN, HIKE_IN), c.name
            continue
        assert c.access_mode == expected[c.campsite_type], (
            f"{c.name} is {c.campsite_type} but tagged {c.access_mode!r}")


def test_anthony_chabots_hike_in_sites_are_not_mistaken_for_backpack_sites():
    # #13-22 sit inside the family campground with no adjacent parking. Selling
    # them as backpack sites would put them in the phone-only booking queue.
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}["Anthony Chabot Campground"]
    assert cg.campsite_type == "family"
    assert "not backpack sites" in cg.notes.lower()


def test_an_unverified_campground_says_so_rather_than_reading_as_checked():
    # Dumbarton Quarry was built from web-search summaries of a page nobody here
    # could open. It carries a source to check against and a blank
    # verified_date, which is the difference between "not yet confirmed" and
    # "confirmed", and its notes must say which facts are in doubt.
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}[
        "Dumbarton Quarry Campground on the Bay"]
    assert cg.source_url.startswith("https://www.ebparks.org/")
    assert cg.verified_date == "", "must not claim a verification"
    assert "unconfirmed" in cg.notes.lower()
    # Absent is not free: no fee was invented for a row nobody has checked.
    assert cg.fee_notes == ""


def test_anthony_chabot_was_promoted_from_guesswork_to_a_read_source():
    # Added from web-search summaries, then replaced by EBRPD's own park page
    # and brochure. A verified row must carry the facts that read earned.
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}["Anthony Chabot Campground"]
    assert cg.verified_date == "2026-09-15"
    assert "$35" in cg.fee_notes and "$45" in cg.fee_notes and "$25" in cg.fee_notes
    # The reservation fee is charged on top and is easy to leave out of a total.
    assert "$8" in cg.fee_notes
    # The three separate camping rates are why access_mode is mixed here.
    assert "35 feet" in cg.notes.lower(), "the RV length limit is a trip-blocking fact"
    assert "10:00 PM" in cg.nightly_entry_cutoff


def test_every_committed_campground_states_its_access_mode():
    # Not a style rule: a blank here reads as "nobody checked", and shipping a
    # dataset that is silently all-unknown would make the column decorative.
    # The exceptions are named, so an unnoticed blank still fails -- and each
    # one must say in its notes that the mode is unrecorded, rather than
    # leaving a reader to infer it from the column being empty.
    blank = {c.name for c in unknown_access(load_campgrounds(CAMPGROUNDS))}
    assert blank == ACCESS_MODE_UNRECORDED
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    for name in blank:
        assert "ACCESS MODE IS NOT RECORDED" in by_name[name].notes, name


def test_no_access_mode_here_rests_on_an_unsourced_claim_any_more():
    # Briones' three carried drive_in on the maintainer's word, flagged as the
    # one value in this dataset no page stated and filed as report R0002. Their
    # booking pages say Hike-In, so the rows are corrected and the report is
    # rejected. The rows still name R0002, because how a value got here is part
    # of the value.
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    for name in ("Wee-Ta-Chi Group Camp", "Maud Whalen Group Camp",
                 "Homestead Valley Group Camp"):
        cg = by_name[name]
        assert cg.access_mode == HIKE_IN, name
        assert "CORRECTS THE DRIVE-IN THIS ROW CARRIED" in cg.notes, name
        assert "R0002" in cg.notes, name
    # The phrase that marked a LIVE unsourced value is gone. The rows still
    # mention the maintainer's word, because that is now history, not a claim.
    assert not any("MAINTAINER'S WORD RATHER THAN A PUBLISHED PAGE" in c.notes
                   for c in load_campgrounds(CAMPGROUNDS))


def test_wee_ta_chi_keeps_the_half_of_the_rejected_report_that_was_true():
    # Driving to the site is permitted in dry weather -- four vehicles of ten --
    # and forbidden within seven days of rain, when the carry is 1.5 miles.
    # access_mode holds one value and EBRPD's own field says hike-in, so the
    # conditional lives in prose. Losing it would make the correction a lie by
    # omission.
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}["Wee-Ta-Chi Group Camp"]
    assert "within 7 days of rain" in cg.notes
    assert "1.5 MILES" in cg.notes
    assert "NO WATER AT THE SITE" in cg.notes
    assert "ALCOHOL: NOT PERMITTED" in cg.notes


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


def test_the_online_listing_is_not_treated_as_the_full_site_inventory():
    # 69 of Anthony Chabot's 75 individual sites appear on the booking system.
    # A party that concludes the campground is full has checked 69 of 75, so
    # the row must name the six and must not present them as explained.
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}["Anthony Chabot Campground"]
    for site in ("010", "031", "033", "039", "053", "075"):
        assert site in cg.notes, f"unlisted site {site} is not named"
    assert "hypothesis" in cg.notes.lower(), (
        "why those sites are absent is not stated by any source; presenting the "
        "ADA reading as fact is the confident-wrong-answer failure")


def test_group_camp_capacities_are_per_site_not_a_range():
    # "Maximum capacity varies from 35 to 300" is not an answer for any one
    # camp. Booking the wrong one is discovered when the party does not fit.
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    expected = {"El Venado": "35", "Lookout Ridge": "35", "Puma Point": "50",
                "Two Rocks": "50", "Lost Ridge": "100", "Hawk Ridge": "100",
                "Bort Meadow": "300"}
    for camp, capacity in expected.items():
        notes = by_name[f"{camp} Group Camp"].notes
        assert f"CAPACITY {capacity}," in notes, f"{camp} lacks its own capacity"


def test_dumbarton_quarry_is_a_campground_of_coyote_hills_not_a_park():
    # It was its own park as a placeholder. Coyote Hills' brochure lists it
    # under that park's Camping heading, and ReserveAmerica says it is within
    # the park -- so the join now resolves like any other campground's.
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    dq = cg["Dumbarton Quarry Campground on the Bay"]
    assert dq.park == "Coyote Hills Regional Park"
    assert dq.park != dq.name, "a park field pointing at the campground is a placeholder"
    # The inherited fee and gate hours may not be what a camper there meets.
    assert "UNCONFIRMED" in dq.notes


def test_coyote_hills_cannot_store_one_opening_time():
    # Three parks before it open at 8am in every band, so gate_open held one
    # figure. This one opens at 7am for five months and 8am for seven, which is
    # where the single gate_open/gate_close pair stops being an awkward fit and
    # becomes the wrong shape.
    from wayproof.park_access import load_park_access
    pa = load_park_access(PARK_ACCESS)["Coyote Hills Regional Park"]
    assert "varies by season" in pa.gate_open
    assert "varies by season" in pa.gate_close
    # A curfew is not a gate: one governs driving in, the other being there.
    assert "CURFEW" in pa.gate_hours_conditions.upper()


def test_the_only_potable_sources_are_the_two_drinking_fountains():
    # Every other source here is a spigot or trough EBRPD states is non-potable.
    # Both of these are drinking fountains at group camps, and neither has ever
    # been checked -- potable is a reading of what a drinking fountain is for,
    # not a word either page uses.
    from wayproof.water import load_water_sources
    sources = load_water_sources(WATER_SOURCES)
    potable = [w for w in sources if w.potable]
    assert [w.name for w in potable] == ["Dairy Glen Group Camp", "Arroyo Flats Group Camp"]
    assert all(w.type == "drinking fountain" for w in potable)


def test_no_drive_in_row_contradicts_itself_in_its_own_notes():
    # Seven Anthony Chabot group camps carried access_mode drive_in while their
    # own notes said "Vehicles park in the lot nearest the site, no driving in".
    # drive_in here means "you can park at or beside the site", which is the
    # thing that sentence denies. Star Mine and Dairy Glen each needed a new
    # page to catch; this one only needed reading the row against its column.
    #
    # One exemption, and it is the distinction the two files exist for:
    # Anthony Chabot is a drive-up campground whose Loop B is ten "Hike-In
    # Sites (NO driving to site)". There the denial is about SOME of its sites
    # and campsites.csv carries it per site, so the campground-level value is
    # still right. A campground with no such rows has no such excuse.
    denials = ("no driving in", "no driving to site", "hike-in only",
               "no vehicle access")
    sites = load_campsites(CAMPSITES)
    has_hike_in_sites = {s.campground for s in sites if s.site_type == TENT_HIKE_IN}
    for c in load_campgrounds(CAMPGROUNDS):
        if c.access_mode != DRIVE_IN or c.name in has_hike_in_sites:
            continue
        lowered = c.notes.lower()
        for phrase in denials:
            assert phrase not in lowered, f"{c.name} says drive_in and {phrase!r}"
    # The exemption must not be a blanket one: Chabot earns it by having the
    # per-site rows, so those rows have to exist.
    assert len([s for s in sites if s.site_type == TENT_HIKE_IN]) == 10


def test_the_only_drive_in_campgrounds_left_are_the_three_family_ones():
    # Every group and backpack camp in this dataset is reached on foot. That is
    # the answer to "which campgrounds can I drive to", and it is short.
    drivable = drive_in(load_campgrounds(CAMPGROUNDS))
    assert [c.name for c in drivable] == [
        "Del Valle Family Campground",
        "Anthony Chabot Campground",
        "Dumbarton Quarry Campground on the Bay",
    ]
    assert {c.campsite_type for c in drivable} == {"family"}
