"""A campground is an objective in its own right.

Run with:  python -m pytest tests/test_campground_objective.py
"""

from __future__ import annotations

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.booking import load_booking_channels
from wayproof.camping import (
    Campground, load_campgrounds, load_campsites, resolve_campground_name,
)
from wayproof.data_loader import load_peaks, load_trailheads
from wayproof.park_access import load_park_access
from wayproof.permits import load_permits
from wayproof.plan import resolve_plan, format_plan_summary
from wayproof.regulations import load_regulations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda n: os.path.join(ROOT, "data", n)
DATE = datetime.date(2026, 10, 17)


def _plan(*names, **over):
    kwargs = dict(
        peaks=load_peaks(D("peaks.csv")), trailheads=load_trailheads(D("trailheads.csv")),
        permits=load_permits(D("permits.csv"), D("release_policies.csv")),
        campgrounds=load_campgrounds(D("campgrounds.csv")),
        campsites=load_campsites(D("campsites.csv")),
        park_access=list(load_park_access(D("park_access.csv")).values()),
        regulations=load_regulations(D("regulations.csv")),
        booking_channels=load_booking_channels(D("booking_channels.csv")),
    )
    kwargs.update(over)
    return resolve_plan(list(names), DATE, **kwargs)


# -- name resolution ---------------------------------------------------------

def test_a_park_name_resolves_to_no_campground():
    # Del Valle Regional Park holds five. Picking one would be the same error
    # as guessing a trailhead.
    cgs = load_campgrounds(D("campgrounds.csv"))
    assert resolve_campground_name("Del Valle", cgs) == (None, [])


def test_a_generic_suffix_is_optional_but_a_qualifier_is_not():
    cgs = load_campgrounds(D("campgrounds.csv"))
    assert resolve_campground_name("Anthony Chabot", cgs)[0].name == "Anthony Chabot Campground"
    assert resolve_campground_name("Bort Meadow", cgs)[0].name == "Bort Meadow Group Camp"
    # "Family" distinguishes it from the park's four backpack camps, so it stays.
    assert resolve_campground_name("Del Valle Family", cgs)[0].name == "Del Valle Family Campground"


def test_an_ambiguous_campground_name_offers_candidates_rather_than_picking():
    cgs = [Campground(name="Ridge Camp", park="A"), Campground(name="Ridge Camp", park="B")]
    site, candidates = resolve_campground_name("ridge camp", cgs)
    assert site is None
    assert candidates == ["Ridge Camp", "Ridge Camp"]


# -- the plan ----------------------------------------------------------------

def test_a_campground_alone_resolves_a_plan():
    r = _plan("Anthony Chabot Campground")
    assert [c.name for c in r.campground_objectives] == ["Anthony Chabot Campground"]
    assert r.objectives == []
    assert r.not_found == []
    assert r.has_objectives


def test_no_trailhead_is_invented_for_a_campground():
    # Car camping has no approach. A trailhead here would produce an entry
    # point, a route shape and a permit that no source supports.
    r = _plan("Anthony Chabot Campground")
    assert r.trailhead is None
    assert r.permit_entries == []
    assert r.route_shape == "unknown"
    assert r.to_dict()["trailhead_modelled"] is False


def test_the_campground_carries_state_law_without_a_permit_to_inherit_it_from():
    # Jurisdiction reaches a trip through the permit. A campsite booked without
    # one would otherwise silently drop the California Campfire Permit.
    r = _plan("Anthony Chabot Campground")
    ids = {x.regulation_id for x in r.regulations}
    assert "ca-campfire-permit" in ids, "state law must still apply"
    assert "ebrpd-pets-campground" in ids, "the agency's own rules must apply"


def test_the_plan_answers_about_the_named_campground_not_its_neighbours():
    # The trailhead flow lists every campground in the park, because there the
    # question is "where can I sleep near this peak". Here the caller named one.
    r = _plan("Anthony Chabot Campground")
    assert [c.name for c in r.facilities.campgrounds] == ["Anthony Chabot Campground"]


def test_costs_and_booking_resolve_for_a_campground_trip():
    r = _plan("Anthony Chabot Campground")
    kinds = {c.kind for c in r.costs}
    assert "campground" in kinds and "park_entrance" in kinds
    assert "permit" not in kinds, "no permit governs this trip"
    channels = {c.channel_id for c in r.facilities.booking_channels}
    assert "ebrpd-family" in channels, "the family queue is how this site is booked"


def test_a_backpack_campground_objective_says_it_is_walked_to():
    r = _plan("Sunol Backpack Camp")
    out = format_plan_summary(r)
    assert "Reached on foot" in out
    channels = {c.channel_id for c in r.facilities.booking_channels}
    assert "ebrpd-backpack" in channels, "backpack sites are a different queue"


def test_an_unknown_name_still_reports_both_namespaces():
    r = _plan("Nowhere At All")
    assert r.not_found == ["Nowhere At All"]
    assert "peak or campground data" in format_plan_summary(r)


def test_a_peak_objective_is_unaffected_by_the_campground_path():
    r = _plan("Rose Peak")
    assert r.campground_objectives == []
    assert r.trailhead is not None
    assert r.permit_entries, "the peak flow still resolves a permit"


def test_a_group_camps_minimum_is_its_own_not_the_districts_floor():
    # The District floor is 17. Bort Meadow holds 300 and needs 100, so a party
    # of twenty reading 17 would plan a trip it cannot book.
    by_name = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}
    assert "MINIMUM PARTY SIZE IS 100" in by_name["Bort Meadow Group Camp"].notes
    assert "MINIMUM PARTY SIZE IS 50" in by_name["Hawk Ridge Group Camp"].notes
    assert "MINIMUM PARTY SIZE 17" in by_name["Puma Point Group Camp"].notes
    for name in ("Bort Meadow Group Camp", "Hawk Ridge Group Camp"):
        assert "reconstructed" in by_name[name].notes, (
            "the tier table extracted as flattened columns; the row alignment "
            "is a reading and must not read as a stated per-site figure")


def test_each_briones_camp_gives_its_own_minimum_not_a_shared_range():
    # The park page published one 50-to-300 range across all three, which is no
    # answer for any of them: a party of twenty can book Wee-Ta-Chi, cannot book
    # Maud Whalen, and is eighty short of Homestead Valley.
    by_name = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}
    for camp, minimum, maximum in (("Wee-Ta-Chi", "17", "50"),
                                   ("Maud Whalen", "25", "75"),
                                   ("Homestead Valley", "100", "300")):
        notes = by_name[f"{camp} Group Camp"].notes
        assert f"MINIMUM {minimum}, MAXIMUM {maximum}" in notes, camp
        # Closed for over five months; booking a winter date is not possible.
        assert "SEASONALLY CLOSED 1 NOVEMBER - 15 MAY" in notes, camp


def test_the_flattened_tier_reading_is_marked_as_having_had_a_wrong_row():
    # Maud Whalen is 25 at 75 capacity; the reconstruction said 17. No Anthony
    # Chabot camp is 75, so nothing there rested on it -- but the rows that used
    # the reading must say it was tested and partly failed, not just that it was
    # a reading.
    by_name = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}
    for camp in ("Bort Meadow Group Camp", "Puma Point Group Camp"):
        assert "ONE ROW OF IT WAS WRONG" in by_name[camp].notes, camp


def test_star_mine_states_who_may_book_it_not_only_how_many():
    # The only campground here restricted by the character of the party -- and
    # the booking system is narrower than the park page: "School Groups and
    # Scouts", not "organized, educational groups". A community group reading
    # the park page as permission would be refused at the gate.
    cg = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}["Star Mine Group Camp"]
    assert "SCHOOL GROUPS AND SCOUTS ONLY" in cg.notes.upper()
    assert "NO WATER" in cg.notes.upper()
    assert cg.fee_notes == "", "no fee is published for this camp; absent is not free"


def test_a_group_camp_can_be_hike_in():
    # Star Mine is classified Hike-In with parking a quarter mile off, so the
    # assumption that group camps are driven to was wrong. Booking one for a
    # party of 35 means carrying everything that distance.
    cg = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}["Star Mine Group Camp"]
    assert cg.campsite_type == "group"
    assert cg.access_mode == "hike_in"
    assert "quarter mile" in cg.notes.lower()


def test_black_diamonds_seven_gate_bands_are_not_flattened_to_one_time():
    # park_access holds one closing time and this park has seven. A single
    # figure would be wrong for most of the year, and the gate shuts on a
    # backpacker walking out 3.2 miles from Stewartville.
    from wayproof.park_access import load_park_access
    pa = load_park_access(D("park_access.csv"))["Black Diamond Mines Regional Preserve"]
    assert pa.gate_open == "8:00 AM", "opening is 8am in every band, so it is storable"
    assert "varies by season" in pa.gate_close
    for band in ("Jan 1-Jan 30 8am-5pm", "Apr 4-Sept 7 8am-8pm", "Nov 1-Dec 31 8am-5pm"):
        assert band in pa.gate_hours_conditions


def test_group_and_backpack_sites_are_block_released_not_rolling():
    # A date is unbookable until its six-month block opens, however far ahead
    # you plan -- which a rolling horizon would have implied otherwise.
    from wayproof.booking import BACKPACK, FAMILY, channels_for, load_booking_channels
    chans = load_booking_channels(D("booking_channels.csv"))
    backpack = " ".join(c.release_mechanics for c in channels_for(chans, BACKPACK, agency="ebrpd"))
    assert "SIX-MONTH BLOCK" in backpack
    family = " ".join(c.release_mechanics for c in channels_for(chans, FAMILY, agency="ebrpd"))
    assert "rolling 12-week" in family


def test_planning_dairy_glen_surfaces_the_parks_deadline_and_the_districts():
    # The park-scoped channel is only worth storing if the objective actually
    # reaches it. Coyote Hills is the park that made booking.channels_for take
    # a park at all; before that the plan would have shown three days only.
    res = _plan("Dairy Glen Group Camp")
    lead = " ".join(c.lead_time for c in res.facilities.booking_channels)
    assert "5 working days" in lead, "the park's own deadline"
    assert "3 days before arrival" in lead, "and the District's, still shown"


def test_dairy_glen_is_hike_in_and_says_so_where_a_planner_reads_it():
    # Corrected from a drive_in that no source supported. Fifty people carry
    # their kit a quarter mile; ten vehicles stay at the lot.
    cg = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}["Dairy Glen Group Camp"]
    assert cg.access_mode == "hike_in"
    text = format_plan_summary(_plan("Dairy Glen Group Camp"))
    assert "HIKE-IN" in text.upper()


def test_every_group_camp_whose_access_a_page_states_is_hike_in():
    # Three for three: Star Mine, Dairy Glen, Arroyo Flats, each a quarter-mile
    # carry. Briones' three carry drive_in from a single unsourced answer and
    # are excluded here deliberately -- this test is about what pages say.
    cgs = load_campgrounds(D("campgrounds.csv"))
    sourced = {"Star Mine Group Camp", "Dairy Glen Group Camp", "Arroyo Flats Group Camp"}
    assert {c.access_mode for c in cgs if c.name in sourced} == {"hike_in"}
    assert len([c for c in cgs if c.name in sourced]) == 3


def test_arroyo_flats_carries_both_minimums_rather_than_choosing_one():
    # 17 on the booking system, 25 on the park page and in the tier table. A
    # party of twenty is booked by one and refused by the other, and the site
    # is booked by phone, so neither number is enforced by a checkout.
    cg = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}["Arroyo Flats Group Camp"]
    assert "minimum 17" in cg.notes
    assert "25 people or more" in cg.notes
    assert "arroyo-flats-minimum" in cg.notes, "points at the open thread"


def test_garins_published_gate_bands_leave_two_days_of_the_year_uncovered():
    # Six bands running Nov 1 to Oct 29. October 30 and 31 fall in none of
    # them, at a park whose group camp says to check the gate before arriving.
    from wayproof.park_access import load_park_access
    pa = load_park_access(D("park_access.csv"))["Garin Regional Park"]
    assert pa.gate_open == "8:00 AM", "opening is 8am in every band, so it is storable"
    assert "OCTOBER 30 AND 31 FALL IN NO BAND" in pa.gate_hours_conditions
    for band in ("Nov 1-Mar 5 8am-6pm", "May 22-Aug 27 8am-9pm", "Sep 25-Oct 29 8am-7pm"):
        assert band in pa.gate_hours_conditions


def test_the_group_alcohol_permit_is_priced_on_the_row_that_costs_it():
    # $25, bought in advance by phone, and not the site fee. A group that turns
    # up with beer and no permit is in breach although beer is allowed.
    cg = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}["Arroyo Flats Group Camp"]
    assert "$25.00" in cg.fee_notes
    assert "NOT THAT FEE" in cg.fee_notes
    # And the side charge must not be allowed to read as the nightly rate: the
    # row still carries the project's own guard for a fee nobody has recorded.
    assert "absent is not free" in cg.fee_notes
