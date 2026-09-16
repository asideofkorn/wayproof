"""Tests for the campground/campsite, water-source, and park-access modules.

Run with:  python -m pytest tests/test_facilities.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from wayproof.camping import (
    COORD_CAMPGROUND,
    COORD_PARK,
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
    located,
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


# Campgrounds whose CLASS no source states. Blank means booking resolves only
# the District-wide channel and no class-specific method -- which is the honest
# answer, and the reason this is a named allowlist rather than an empty one.
#
# Hetch Hetchy and Venados appear only in Del Valle's six-name seasonal closure
# list. An arithmetic argument makes them very likely group camps -- 7 GROUP
# CAMPING sites, 1 equestrian group camp which is Caballo Loco, four of the
# other five closure names already known to be group camps -- and this project
# has twice been wrong following arithmetic that worked.
CAMPSITE_TYPE_UNSTATED = {
    "Hetch Hetchy",
    "Venados",
}


def test_campsite_type_is_set_wherever_a_source_states_one():
    # Blank means booking resolves only agency-wide channels, so a backpacker
    # would never be told their sites are phone-only. The exceptions are named,
    # so a NEW blank still fails.
    blank = {c.name for c in load_campgrounds(CAMPGROUNDS) if not c.campsite_type}
    assert blank == CAMPSITE_TYPE_UNSTATED
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    for name in blank:
        assert "campsite_type IS DELIBERATELY BLANK" in by_name[name].notes, name


def test_a_class_less_campground_gets_the_district_channel_and_no_method():
    from wayproof.booking import channels_for, load_booking_channels
    chans = channels_for(load_booking_channels(os.path.join(DATA, "booking_channels.csv")),
                         "", agency="ebrpd")
    assert [c.applies_to for c in chans] == ["all"]


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


def test_campgrounds_are_split_into_sites_only_where_a_source_names_them():
    # This test used to assert Boyd Camp had no sub-sites, on the strength of no
    # source naming any. The Sunol booking facility -- one ReserveAmerica
    # listing selling nineteen sites across three parks -- names them: Boyd has
    # two, Doe two, Maggie's three, Eagle Springs four. So the rule was never
    # "these camps are single sites", it was "nobody had read the page".
    #
    # What the rule actually is, and still holds: no placeholder row that just
    # repeats its campground's name. Every row here is a site a source names.
    sites = load_campsites(CAMPSITES)
    by_cg = {}
    for s in sites:
        by_cg.setdefault(s.campground, []).append(s)
    assert sorted(by_cg) == [
        "Anthony Chabot Campground", "Boyd Camp", "Doe Camp", "Eagle Springs",
        "Maggie's Half Acre", "Stewart's Camp", "Sunol Backpack Camp",
    ]
    assert [len(by_cg[c]) for c in ("Boyd Camp", "Doe Camp", "Eagle Springs",
                                    "Maggie's Half Acre", "Stewart's Camp")] == [2, 2, 4, 3, 1]
    for s in sites:
        assert s.name != s.campground, f"{s.name} just repeats its campground"


def test_no_backpack_site_claims_to_be_bookable_online():
    # ReserveAmerica lists all nineteen and sells none of them: EBRPD's backpack
    # sites are phone-only District-wide, which booking_channels has said since
    # it was built while seven Sunol rows quietly contradicted it. Listing is
    # not selling, and the column means sellable.
    backpack_camps = {c.name for c in load_campgrounds(CAMPGROUNDS)
                      if c.campsite_type == "backpack"}
    sites = [s for s in load_campsites(CAMPSITES) if s.campground in backpack_camps]
    assert len(sites) == 19
    assert not any(s.online_bookable for s in sites)


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
# honest value, and it is named here individually so a NEW blank still fails.
#
# Briones' three sat here, then left on the maintainer's word, then came back
# corrected to hike-in off their own booking pages. That round trip is the
# argument for this set existing: the value that was wrong is the one that was
# never blank. Girls' Camp sat here for one commit and left the honest way --
# its own booking page said Hike-In, so a blank became a sourced value without
# ever having been a guess. Empty again, and kept for the next one.
ACCESS_MODE_UNRECORDED = {
    # Del Valle's five, named on the Ohlone Wilderness permit map and nowhere
    # else read here. The map gives their names and their type and says nothing
    # about how you reach them. Del Valle's own ReserveAmerica campsites page
    # would fill this and has never been read.
    "Wild Turkey Group Camp",
    "Punta Vaca Group Camp",
    "Cedar Group Camp",
    "Lil Chaparral Horse Camp",
    "Caballo Loco Horse Camp",
    # Named only in a seasonal closure list: a name and a season, nothing else.
    "Hetch Hetchy",
    "Venados",
}


def test_backpack_sites_are_walked_to_and_family_and_group_sites_are_driven_to():
    # Stated as a rule rather than a list of names, so it keeps holding as the
    # District's parks land. Getting it backwards means booking a site up to
    # 16.7 trail miles from where you parked.
    # Group camps are NOT uniformly drive-in, and assuming so was wrong: Star
    # Mine is classified Hike-In with its parking a quarter mile off. So the
    # rule holds for backpack and family sites, and group sites are checked
    # only for carrying a mode at all.
    # "equestrian" joined the vocabulary with Del Valle's two horse camps. It
    # is EBRPD's own word, from the cancellation text attached to every
    # reservation -- "backpacking, equestrian, or group camping" -- not a class
    # invented here to hold a row that did not fit.
    expected = {"backpack": HIKE_IN, "family": DRIVE_IN}
    for c in load_campgrounds(CAMPGROUNDS):
        if c.name == "Point Pinole Group Camp":
            # "Boat-In, Hike-In" -- EBRPD's own pair, the only multi-valued
            # access_mode here and the reason the field takes a list at all.
            assert c.access_modes == ["boat_in", "hike_in"]
            continue
        if c.name in CAMPSITE_TYPE_UNSTATED:
            assert c.campsite_type == "", c.name
            continue
        assert c.campsite_type in ("backpack", "family", "group", "equestrian"), (
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


def test_every_potable_source_here_is_a_drinking_fountain_at_a_group_camp():
    # Three now, and the rule has held every time: the only sources this project
    # reads as drinkable are drinking fountains, and every one is at a group
    # camp. Potable is a reading of what a drinking fountain is for, not a word
    # any of the three pages uses. None has ever been checked.
    from wayproof.water import load_water_sources
    sources = load_water_sources(WATER_SOURCES)
    potable = [w for w in sources if w.potable]
    assert [w.name for w in potable] == ["Dairy Glen Group Camp", "Arroyo Flats Group Camp",
                                         "Point Pinole Group Camp"]
    assert all(w.type == "drinking fountain" for w in potable)
    group_camps = {c.name for c in load_campgrounds(CAMPGROUNDS)
                   if c.campsite_type == "group"}
    assert all(w.location in group_camps for w in potable)


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


def test_the_drive_in_list_is_three_family_campgrounds_and_one_group_camp():
    # Every group and backpack camp in the eight parks read first is walked to,
    # which looked like a District fact until Las Trampas' Corral stated
    # Drive-In. Ordered as the file is, so a new row cannot slip in unnoticed.
    drivable = drive_in(load_campgrounds(CAMPGROUNDS))
    assert [c.name for c in drivable] == [
        "Del Valle Family Campground",
        "Anthony Chabot Campground",
        "Dumbarton Quarry Campground on the Bay",
        "Corral Group Camp",
    ]
    assert [c.campsite_type for c in drivable] == ["family"] * 3 + ["group"]


# -- coordinates -------------------------------------------------------------

def test_a_coordinate_without_a_precision_is_rejected_loudly(tmp_path):
    # An unlabelled coordinate reads as the campsite's own position. For a park
    # centroid that can be miles wrong, and nothing downstream could tell --
    # the same shape as the guessed access_mode this project already got wrong.
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,latitude,longitude,coord_precision\n"
                    "X,P,37.5,-122.0,\n")
    with pytest.raises(ValueError, match="coord_precision"):
        load_campgrounds(path)


def test_half_a_coordinate_is_rejected(tmp_path):
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,latitude,longitude,coord_precision\n"
                    "X,P,37.5,,campground\n")
    with pytest.raises(ValueError, match="half a coordinate"):
        load_campgrounds(path)


def test_a_precision_with_no_coordinate_is_rejected(tmp_path):
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,latitude,longitude,coord_precision\n"
                    "X,P,,,park\n")
    with pytest.raises(ValueError, match="no coordinates"):
        load_campgrounds(path)


def test_a_blank_coordinate_is_none_and_never_zero():
    # 0.0 is a real place in the Gulf of Guinea. A campground silently sorted
    # 8,000 miles away is worse than one the search says it cannot place.
    unplaced = [c for c in load_campgrounds(CAMPGROUNDS) if c.latitude is None]
    assert unplaced, "this dataset still has campgrounds with no coordinates"
    assert all(c.longitude is None and c.coord_precision == "" for c in unplaced)


def test_refusing_to_borrow_dumbartons_park_centroid_was_worth_about_two_miles():
    # It was left unplaced while its park had a coordinate. Its own facility
    # page then gave it one, and the two points are ~2 miles apart -- which is
    # what borrowing the centroid would have cost, in the direction of the marsh.
    from wayproof.distances import haversine_miles
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    dumbarton = by_name["Dumbarton Quarry Campground on the Bay"]
    dairy_glen = by_name["Dairy Glen Group Camp"]  # carries the park's point
    assert dumbarton.park == dairy_glen.park == "Coyote Hills Regional Park"
    assert dumbarton.coord_precision == COORD_CAMPGROUND
    assert dairy_glen.coord_precision == COORD_PARK
    gap = haversine_miles(dumbarton.latitude, dumbarton.longitude,
                          dairy_glen.latitude, dairy_glen.longitude)
    assert 1.0 < gap < 3.0


def test_the_ohlone_trail_camps_are_left_unplaced_on_purpose_and_say_why():
    # Del Valle has a coordinate and these four are in that park. They sit 2 to
    # 11.5 miles up the Ohlone Wilderness Trail, so the park's point would
    # misplace them by that much. A blank that is a decision has to read as one.
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    assert by_name["Del Valle Family Campground"].latitude is not None
    for name in ("Boyd Camp", "Stewart's Camp", "Maggie's Half Acre", "Doe Camp"):
        c = by_name[name]
        assert c.latitude is None, name
        assert "DELIBERATELY UNPLACED" in c.coord_source, name
        assert "Ohlone Wilderness Trail" in c.coord_source, name


def test_every_stored_coordinate_says_which_page_it_came_off():
    for c in located(load_campgrounds(CAMPGROUNDS)):
        assert "ReserveAmerica" in c.coord_source, c.name
        assert "PRECISION" in c.coord_source.upper(), c.name


def test_las_trampas_water_is_unreliable_by_the_operators_own_account():
    # Every other row in this table is a source nobody has verified lately.
    # This is one the agency verifies as unpromised, which is a different fact
    # and must not read as "unchecked".
    from wayproof.water import (
        latest_status_by_source, load_water_source_log, load_water_sources,
    )
    src = {w.name: w for w in load_water_sources(WATER_SOURCES)}["Corral Group Camp faucets"]
    assert src.location == "Corral Group Camp"
    assert src.potable is None, "nothing read says whether it is drinkable when it flows"
    assert "unreliable" in src.notes

    entry = latest_status_by_source(
        load_water_source_log(WATER_SOURCE_LOG))["Corral Group Camp faucets"]
    assert "not guaranteed" in entry.observed_status
    assert "Nobody has turned these taps" in entry.notes


def test_a_blank_potable_is_unknown_not_a_statement_that_it_is_undrinkable():
    # It loaded as False until Las Trampas, which reads as "the agency says do
    # not drink this" -- a claim nobody made, about the one field where being
    # wrong either way is a health question. No committed row changed meaning:
    # every other row states True or False explicitly.
    from wayproof.water import WaterSource, load_water_sources
    assert WaterSource(name="x").potable is None
    sources = load_water_sources(WATER_SOURCES)
    unknown = [w.name for w in sources if w.potable is None]
    assert unknown == ["Corral Group Camp faucets"]
    assert all(isinstance(w.potable, bool) for w in sources if w.name not in unknown)


def test_a_blank_potable_column_does_not_load_as_false(tmp_path):
    from wayproof.water import load_water_sources
    path = tmp_path / "water_sources.csv"
    path.write_text("name,type,potable,location\nSpring,spring,,Somewhere\n")
    assert load_water_sources(path)[0].potable is None


def test_mission_peaks_hours_are_one_entrances_and_the_row_says_which():
    # Two entrances, two published schedules, one gate_open/gate_close pair.
    # Stanford Avenue's are stored because it is the only entrance where a
    # camper may park overnight -- a choice, written down rather than inferred.
    from wayproof.park_access import load_park_access
    pa = load_park_access(PARK_ACCESS)["Mission Peak Regional Preserve"]
    assert pa.gate_open == "6:30 AM", "Stanford Avenue's, not Ohlone College's 6am"
    assert "STANFORD AVENUE HOURS" in pa.gate_hours_conditions
    assert "6am-10pm" in pa.gate_hours_conditions, "the other entrance is still shown"
    assert "PER-ENTRANCE FAILURE" in pa.gate_hours_conditions


def test_the_only_fee_at_mission_peak_is_charged_by_a_college():
    # EBRPD charges nothing at either entrance. An agent that dropped the
    # park_entrance component because the land manager is free would
    # under-price the trip by $4 and send a camper to the wrong lot.
    from wayproof.park_access import load_park_access
    pa = load_park_access(PARK_ACCESS)["Mission Peak Regional Preserve"]
    assert "$4" in pa.entrance_fee and "Ohlone College" in pa.entrance_fee
    assert "OVERNIGHT PARKING IS NOT ALLOWED AT OHLONE COLLEGE" in pa.fee_conditions


def test_eagle_spring_keeps_both_of_ebrpds_spellings_for_itself():
    # The park page and map say "Eagle Spring Backpack Camp"; the District's
    # own water update says "Eagle Springs". The plural stays as the key
    # because the water source and its append-only ledger are built on it.
    from wayproof.water import load_water_source_log, load_water_sources
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}["Eagle Springs"]
    assert "EAGLE SPRING BACKPACK CAMP" in cg.notes
    assert "append-only" in cg.notes
    assert {w.location for w in load_water_sources(WATER_SOURCES)
            if w.name == "Eagle Springs"} == {"Eagle Springs"}
    assert any(e.water_source_name == "Eagle Springs"
               for e in load_water_source_log(WATER_SOURCE_LOG))


def test_eagle_springs_water_is_treatable_not_merely_undrinkable():
    # "Water needs to be treated or boiled" is a stronger and more useful claim
    # than the non-potable flag: the water is there and usable with a stove.
    from wayproof.water import load_water_sources
    w = {x.name: x for x in load_water_sources(WATER_SOURCES)}["Eagle Springs"]
    assert w.potable is False
    assert "treated or boiled" in w.notes


def test_the_looking_for_category_is_a_search_facet_not_a_booking_class():
    # Morgan Territory's camp is filed under BACKPACK SITE, its loop is
    # "Backpack Seasonal" and its minimum is 1 -- while its Looking For
    # Category reads "Group Site, Horse Site, Tent Site". That field is
    # multi-valued, so it cannot be read as the class that keys booking
    # channels, which is most of why a neighbouring map could call Round
    # Valley's camp a group camp.
    by_name = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    morgan = by_name["Morgan Territory Backpack Camp"]
    assert morgan.campsite_type == "backpack"
    assert "multi-valued search facet, not a class" in morgan.notes
    assert by_name["Round Valley Backpack Camp"].campsite_type == "backpack"


def test_a_gravel_driveway_on_a_site_four_miles_up_a_trail_is_not_read_literally():
    # ReserveAmerica publishes "Driveway Surface: Gravel" and "Maximum Number
    # of Vehicles: 1" for camps two to eleven miles from any road. Both fields
    # exist for drive-in campgrounds and get filled in anyway. The rows record
    # what they are rather than storing either as a fact about the site --
    # the same care "Looking For Category" needed.
    sites = {s.name: s for s in load_campsites(CAMPSITES)}
    assert "SCHEMA LEAKING" in sites["Boyd #1"].notes
    assert "one car at the trailhead, not at the pitch" in sites["Boyd #1"].notes


def test_the_one_stated_hike_in_distance_is_not_read_across_to_its_neighbours():
    # Eagle Springs #4 gives 21,120 feet -- exactly 4.0 miles. Its three
    # siblings leave the field empty, and four sites at one camp are unlikely
    # to differ much, which is not a reason to write a number on three rows.
    sites = {s.name: s for s in load_campsites(CAMPSITES)}
    assert "21120" in sites["Eagle Springs #4"].notes
    assert "EXACTLY 4.0 MILES" in sites["Eagle Springs #4"].notes
    for sibling in ("Eagle Springs #1", "Eagle Springs #2", "Eagle Springs #3"):
        assert "4.0 MILES" not in sites[sibling].notes, sibling


def test_no_ohlone_corridor_site_is_marked_pets_allowed_domestic():
    # Structural corroboration for a rule carried on the booking platform's
    # word alone. Ten sites read at site level, none marked Domestic, where
    # every EBRPD group camp read for this project is. The only animal named
    # anywhere on the corridor is Doe #1's horse.
    from wayproof.regulations import load_regulations
    rule = {r.regulation_id: r for r in load_regulations(
        os.path.join(DATA, "regulations.csv"))}["ebrpd-backpack-no-dogs-ohlone"]
    assert "NOT ONE carries a 'Pets Allowed: Domestic' marker" in rule.detail
    assert "is not a second source for the rule" in rule.detail
    sites = {s.name: s for s in load_campsites(CAMPSITES)}
    assert "PETS FIELD READS 'HORSE' AND NOTHING ELSE" in sites["Doe #1"].notes


def test_every_site_on_the_sunol_facility_has_been_read():
    # Nineteen sites across three parks. Reading the whole set is what makes
    # the cross-site patterns visible; reading nine of them showed none of it.
    sites = [s for s in load_campsites(CAMPSITES) if s.loop.endswith("Backpack")]
    assert len(sites) == 19
    assert all("PER-SITE DETAIL" in s.notes for s in sites)


def test_picnic_tables_split_perfectly_between_sunol_and_everywhere_else():
    # Seven for seven against none for twelve. An absent marker is not a stated
    # absence, and a table is still the difference between cooking on the
    # ground and not after four to eleven miles with a stove on your back.
    sites = [s for s in load_campsites(CAMPSITES) if s.loop.endswith("Backpack")]
    tabled = {s.name for s in sites if "PICNIC TABLE" in s.notes}
    assert tabled == {s.name for s in sites if s.loop == "Sunol Backpack"}
    assert len(tabled) == 7


def test_the_group_site_facet_tracks_capacity_and_no_site_sits_in_the_gap():
    # It appears on every site of 14 or more and none of 10 or less. Nothing
    # here is 11, 12 or 13, so the threshold is unknown -- which is the honest
    # shape of the finding, and why round-valley-camp-class is narrowed and not
    # closed by it.
    sites = [s for s in load_campsites(CAMPSITES) if s.loop.endswith("Backpack")]
    grouped = [s for s in sites if "Category: Group Site" in s.notes]
    plain = [s for s in sites if "Category: Group Site" not in s.notes]
    assert min(s.capacity for s in grouped) == 14
    assert max(s.capacity for s in plain) == 10
    assert not [s for s in sites if 10 < s.capacity < 14]


def test_eagle_springs_is_the_only_camp_with_no_shade_rating_anywhere():
    # Fifteen of fifteen others carry one. This is the park whose own page
    # leads with dogs dying of heat stroke, so the gap is recorded rather than
    # filled in with a guess.
    sites = [s for s in load_campsites(CAMPSITES) if s.loop.endswith("Backpack")]
    unrated = {s.campground for s in sites if "shade" not in s.notes.lower()}
    assert unrated == {"Eagle Springs"}
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}["Eagle Springs"]
    assert "NO SHADE RATING AT ALL" in cg.notes
    assert "heat stroke" in cg.notes


def test_the_only_shower_at_a_primitive_camp_is_at_point_pinole():
    # This test was first written as "the only shower in this dataset" and
    # failed at once: Anthony Chabot's family campground has hot showers and
    # Puma Point Group Camp has access to them. A superlative is a claim about
    # the whole dataset and has to be checked against it, so it is now the
    # narrower claim the sources actually support.
    cgs = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    pinole = cgs["Point Pinole Group Camp"]
    assert "RINSING SHOWER" in pinole.notes
    assert "STORAGE CONTAINER WITH A COMBO LOCK" in pinole.notes
    assert "Hot showers" in cgs["Anthony Chabot Campground"].notes
    assert "PRIVATE showers" in pinole.notes, "the rinsing shower is open-air"
    # Every other mention is a camp saying it has none, or one borrowing the
    # family campground's.
    for c in load_campgrounds(CAMPGROUNDS):
        if c.name in ("Point Pinole Group Camp", "Anthony Chabot Campground",
                      "Puma Point Group Camp"):
            continue
        if "shower" in c.notes.lower():
            assert "no access to showers" in c.notes.lower() \
                or "no showers" in c.notes.lower(), c.name


def test_two_ebrpd_dog_limits_count_the_same_number_differently():
    # Three per SITE District-wide, three per PERSON at Point Pinole. Not a
    # conflict -- a campsite occupancy cap and a park-wide walking limit -- and
    # for a party of ten they differ by twenty-seven dogs.
    from wayproof.regulations import load_regulations
    regs = {r.regulation_id: r for r in
            load_regulations(os.path.join(DATA, "regulations.csv"))}
    assert "THREE DOGS PER SITE" in regs["ebrpd-pets-count"].summary
    pinole = regs["point-pinole-dogs"]
    assert pinole.scope_type == "park"
    assert "THREE DOGS PER PERSON" in pinole.summary
    assert "the stricter applies where both do" in pinole.detail


# -- access_mode takes a list because EBRPD publishes one --------------------

def test_a_site_can_have_two_access_modes_and_reads_as_both():
    cg = Campground(name="X", park="P", access_mode="boat_in;hike_in")
    assert cg.access_modes == ["boat_in", "hike_in"]
    assert access_label(cg) == "boat-in or hike-in"


def test_one_mode_still_reads_as_one_and_blank_still_reads_as_unrecorded():
    assert access_label(Campground(name="X", park="P", access_mode=HIKE_IN)) == "hike-in"
    assert access_label(Campground(name="X", park="P")) == UNKNOWN_ACCESS_LABEL


def test_an_invalid_mode_inside_a_list_is_rejected_loudly(tmp_path):
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,access_mode\nX,P,hike_in;helicopter\n")
    with pytest.raises(ValueError, match="helicopter"):
        load_campgrounds(path)


def test_a_repeated_mode_is_rejected(tmp_path):
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,access_mode\nX,P,hike_in;hike_in\n")
    with pytest.raises(ValueError, match="Repeated"):
        load_campgrounds(path)


def test_the_boat_in_camp_is_found_by_asking_for_either_of_its_modes():
    # Membership, not equality: a site EBRPD calls "Boat-In, Hike-In" is a
    # hike-in campground, and asking for hike-in must return it.
    from wayproof.discovery import find_campgrounds
    cgs = load_campgrounds(CAMPGROUNDS)
    for mode in ("hike_in", "boat_in"):
        found = {m.campground.name for m in find_campgrounds(cgs, access=mode).matches}
        assert "Point Pinole Group Camp" in found, mode
    # And it is still not a campground you can drive to: the four escorted
    # vehicles need a fortnight's notice and a staff escort out.
    drivable = {m.campground.name for m in find_campgrounds(cgs, access=DRIVE_IN).matches}
    assert "Point Pinole Group Camp" not in drivable


def test_the_escorted_vehicles_are_recorded_and_not_stored_as_drive_in():
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}["Point Pinole Group Camp"]
    assert DRIVE_IN not in cg.access_modes
    assert "at least 2 WEEKS before trip" in cg.notes
    assert "2 pm-3:30 pm for staff escort" in cg.notes


def test_every_campground_now_cites_a_source():
    # Six had none: Del Valle Family Campground and the five camps sold through
    # the Sunol facility. They were the oldest rows in the file, added before
    # per-park reading began, and nothing flagged them -- campgrounds.csv has no
    # guard requiring a citation where regulations.csv does. This is that guard.
    missing = [c.name for c in load_campgrounds(CAMPGROUNDS) if not c.source_url]
    assert missing == [], f"campgrounds citing nothing: {missing}"


def test_the_sunol_facility_is_cited_by_every_camp_it_sells():
    # One facility, three parks. The five camps whose sites it sells all point
    # at it, which is the closest this schema gets to recording the
    # relationship -- there is no facility table to join on.
    cgs = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}
    for name in ("Boyd Camp", "Stewart's Camp", "Maggie's Half Acre", "Doe Camp",
                 "Sunol Backpack Camp"):
        assert "/explore/sunol/EB/110028/" in cgs[name].source_url, name
    # And Eagle Springs, the sixth, cites the Mission Peak map it came from --
    # a different source for the same facility's sites, left as it is because
    # that is where its facts were read.
    assert cgs["Eagle Springs"].source_url.endswith("mission-peak-map.pdf")


def test_a_closure_that_wraps_the_new_year_is_handled():
    # Every EBRPD closure here runs 1 November into spring. PermitRule's quota
    # season uses a straight start <= today <= end, which would answer False on
    # every day of every one of them; its own seasons run inside one year, so it
    # is left alone and this does the wrap.
    import datetime
    c = Campground(name="X", park="P",
                   season_closed_start=(11, 1), season_closed_end=(3, 31))
    assert c.closed_on(datetime.date(2027, 1, 15)) is True
    assert c.closed_on(datetime.date(2026, 11, 1)) is True, "closes on the first day"
    assert c.closed_on(datetime.date(2027, 3, 31)) is True, "and on the last"
    assert c.closed_on(datetime.date(2027, 4, 1)) is False
    assert c.closed_on(datetime.date(2027, 7, 1)) is False
    assert c.season_label == "1 November to 31 March"


def test_a_season_inside_one_year_still_works():
    import datetime
    c = Campground(name="X", park="P",
                   season_closed_start=(1, 1), season_closed_end=(1, 31))
    assert c.closed_on(datetime.date(2027, 1, 15)) is True
    assert c.closed_on(datetime.date(2027, 2, 1)) is False


def test_no_season_is_none_rather_than_open():
    import datetime
    assert Campground(name="X", park="P").closed_on(datetime.date(2027, 1, 15)) is None
    assert Campground(name="X", park="P").season_label == ""


def test_half_a_season_is_rejected(tmp_path):
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,season_closed_start,season_closed_end\nX,P,11-01,\n")
    with pytest.raises(ValueError, match="half a closure season"):
        load_campgrounds(path)


def test_an_impossible_date_is_rejected(tmp_path):
    path = tmp_path / "campgrounds.csv"
    path.write_text("name,park,season_closed_start,season_closed_end\nX,P,11-01,02-30\n")
    with pytest.raises(ValueError):
        load_campgrounds(path)


def test_fifteen_campgrounds_close_for_the_winter_and_the_rest_say_nothing():
    import datetime
    from wayproof.camping import closed_on as closed_list, season_unrecorded
    cgs = load_campgrounds(CAMPGROUNDS)
    shut = closed_list(cgs, datetime.date(2027, 1, 15))
    assert len(shut) == 15
    # Three windows, all EBRPD's own wording, none of them the same.
    assert {c.season_label for c in shut} == {
        "1 November to 15 May", "1 November to 31 March", "1 November to 1 April"}
    # And the rest are unrecorded, not open.
    assert len(season_unrecorded(cgs)) == len(cgs) - 15
