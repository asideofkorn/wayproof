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
                                   ("Homestead Valley", "100", "300")):
        notes = by_name[f"{camp} Group Camp"].notes
        assert f"MINIMUM {minimum}, MAXIMUM {maximum}" in notes, camp
        # Closed for over five months; booking a winter date is not possible.
        assert "SEASONALLY CLOSED 1 NOVEMBER - 15 MAY" in notes, camp
    # Maud Whalen is deliberately not in that list: its two EBRPD pages give
    # two different floors, so the row states both rather than picking one.
    maud = by_name["Maud Whalen Group Camp"].notes
    assert "SEASONALLY CLOSED 1 NOVEMBER - 15 MAY" in maud
    assert "Minimum Number of People 17" in maud and "overview says 25" in maud
    assert "arroyo-flats-minimum" in maud


def test_the_flattened_tier_reading_is_marked_as_no_longer_deciding_anything():
    # Its 75-capacity row was corrected once and then contradicted back: the
    # per-site pages say 17, the summary pages say 25. Neither reading is
    # restored. No Chabot camp is 75, and the only two sites that row governed
    # now state their own numbers, so the table has nothing left to decide --
    # and the rows that used it have to say so rather than look confident.
    by_name = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}
    for camp in ("Bort Meadow Group Camp", "Puma Point Group Camp"):
        notes = by_name[camp].notes
        assert "ONE ROW OF IT WAS WRONG BOTH TIMES" in notes, camp
        assert "DECIDES NOTHING ANYWHERE" in notes, camp


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


def test_group_camp_access_is_mostly_hike_in_with_one_exception_and_five_blanks():
    # Sixteen were hike-in, three of them corrected from a wrong drive_in, and
    # that looked like a District fact until Las Trampas' Corral said Drive-In.
    # Del Valle's three then arrived off a map that names them and says nothing
    # about how you reach them. Assert all three states, so neither the
    # majority, the exception, nor the blanks can quietly disappear.
    cgs = load_campgrounds(D("campgrounds.csv"))
    group = [c for c in cgs if c.campsite_type == "group"]
    assert len(group) == 20
    by_mode = {}
    for c in group:
        by_mode.setdefault(c.access_mode, []).append(c.name)
    assert sorted(by_mode) == ["", "drive_in", "hike_in"]
    assert by_mode["drive_in"] == ["Corral Group Camp"]
    assert sorted(by_mode[""]) == ["Cedar Group Camp", "Punta Vaca Group Camp",
                                   "Wild Turkey Group Camp"]
    assert "FIRST DRIVE-IN GROUP CAMP" in {c.name: c for c in group}["Corral Group Camp"].notes


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


def test_the_unsourced_access_report_is_rejected_and_says_what_it_got_right():
    # R0002 claimed Briones' camps are drive-in. The booking pages say hike-in,
    # so it is rejected -- but Wee-Ta-Chi does permit driving in dry weather,
    # and a ledger that records only "wrong" teaches the wrong lesson.
    from wayproof.reports import pending_reports
    r = {x.report_id: x for x in pending_reports(D("pending_reports.csv"))}["R0002"]
    assert r.status == "rejected"
    assert "SCHEMA GAP" in r.resolution_notes
    assert "conditions permitting" in r.resolution_notes
    # The earlier acceptance text survives: the ledger shows its own reversals.
    assert "ACCEPTED 2026-09-16" in r.resolution_notes


def test_the_alcohol_rule_names_the_exception_it_cannot_hold():
    # Wee-Ta-Chi bans alcohol on its own page. regulations.csv has no site
    # scope, so the ban lives on the campground row and the agency rule has to
    # point at it -- otherwise the District rule reads as reaching everywhere.
    from wayproof.regulations import load_regulations
    rule = {r.regulation_id: r for r in
            load_regulations(D("regulations.csv"))}["ebrpd-alcohol"]
    assert "Wee-Ta-Chi" in rule.detail
    assert "nowhere to go" in rule.detail


def test_the_only_reservable_camp_across_both_halves_of_one_parkland():
    # Garin and Dry Creek Pioneer share one brochure map whose legend has a
    # single "Reservable Camp" symbol, used once. 5,800 acres, one camp -- and
    # Dry Creek Pioneer is tagged for camping anyway, which is what makes it an
    # over-count in the 15-versus-18 thread rather than a second camping park.
    cgs = load_campgrounds(D("campgrounds.csv"))
    parkland = [c for c in cgs if c.park in ("Garin Regional Park",
                                             "Dry Creek Pioneer Regional Park")]
    assert [c.name for c in parkland] == ["Arroyo Flats Group Camp"]
    assert "only reservable camp across both parks" in parkland[0].notes
    # And the four reservable areas beside it on the same inset are picnic
    # areas, the call already made for Briones' Oak Grove, Newt Hollow and Crow.
    for picnic in ("Cattlemen", "Buttonwood", "Ranchside", "Pioneer"):
        assert picnic not in {c.name for c in cgs}


def test_a_park_held_without_a_camp_is_not_filed_as_one_not_yet_checked():
    # "Nobody has checked" and "checked, and there is nothing" are the two
    # states this project spends its time separating, and the integrity guard
    # has a separate allowlist for each.
    from tests.test_referential_integrity import (
        PARKS_HELD_WITHOUT_A_SITE, PARKS_WITH_NO_SITE_YET,
    )
    assert "Dry Creek Pioneer Regional Park" in PARKS_HELD_WITHOUT_A_SITE
    assert PARKS_HELD_WITHOUT_A_SITE.isdisjoint(PARKS_WITH_NO_SITE_YET)


def test_the_garden_closure_stays_where_a_reader_will_meet_it():
    # The garden is in Dry Creek Pioneer. Nothing in this dataset sits in that
    # park, so an advisory scoped there could never reach a plan. It stays on
    # Garin, where EBRPD posts it and where Arroyo Flats is -- and the row says
    # it is mis-scoped rather than pretending otherwise.
    from wayproof.advisories import load_advisories
    advisories = {a.advisory_id: a for a in load_advisories(D("advisories.csv"))}
    assert "dry-creek-pioneer-garden" not in advisories, "no unreachable duplicate"
    garden = advisories["garin-dry-creek-garden"]
    assert garden.scope_value == "Garin Regional Park"
    assert "ACTUALLY IN THE ADJOINING PARK" in garden.detail
    assert "can never reach a plan" in garden.detail


def test_reinhardts_three_camps_answer_the_several_the_map_could_not():
    # The park page said "several", the map named one, and this project
    # recorded one rather than guessing from eight labels. Two of those eight
    # were camps -- guessing would have been wrong five times out of eight.
    cgs = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}
    reinhardt = [c for c in cgs.values()
                 if c.park == "Dr. Aurelia Reinhardt Redwood Regional Park"]
    assert sorted(c.name for c in reinhardt) == ["Fern Dell", "Girls' Camp", "Trail's End"]
    assert all(c.access_mode == "hike_in" for c in reinhardt)
    # Named places that turned out NOT to be camps stayed out of the dataset.
    for label in ("Big Bend Meadow", "Orchard", "Old Church", "Anna Costa", "Quail", "Owl"):
        assert label not in cgs


def test_trails_end_has_the_tightest_party_band_in_the_dataset():
    # 17 to 25. Eight people wide, at the closest camping to Oakland here: a
    # party of 16 cannot book it and a party of 26 cannot fit.
    cg = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}["Trail's End"]
    assert "MINIMUM 17, MAXIMUM 25" in cg.notes
    assert "TIGHTEST PARTY-SIZE BAND" in cg.notes


def test_the_briones_season_no_longer_leans_on_the_misread_field():
    # "Open through 31 October" was counted as a surface confirming the 1 Nov
    # closure. Reinhardt's copy of that field says 06 Jan 2027 on a page that
    # also states a 1 Nov closure, so it is a booking horizon, not a season.
    # The closure stands on three other surfaces; the count was what was wrong.
    for name in ("Wee-Ta-Chi Group Camp", "Maud Whalen Group Camp",
                 "Homestead Valley Group Camp"):
        notes = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}[name].notes
        assert "fourth surface" not in notes, name
        assert "WAS MISREAD" in notes, name
        assert "three independent surfaces" in notes, name


def test_the_constructed_name_turned_out_right_and_the_flag_was_still_correct():
    # Keyed "Morgan Territory Backpack Camp" when nothing read named the camp.
    # The booking system calls it exactly that. A convention holding is not a
    # licence to construct names: the row still records that it was a guess,
    # because the flag would have been just as right if the name had been wrong.
    cg = {c.name: c for c in
          load_campgrounds(D("campgrounds.csv"))}["Morgan Territory Backpack Camp"]
    assert "CONSTRUCTED NAME TURNED OUT TO BE THE PUBLISHED ONE" in cg.notes
    assert "not a licence to construct names" in cg.notes


def test_the_longest_carry_in_the_dataset_is_on_the_row_that_has_it():
    # 4.5 miles from the parking, against 3.2 at Stewartville, 1.5 at
    # Wee-Ta-Chi and a quarter mile at three others. A park-precision
    # coordinate is nowhere near this camp and the row says so.
    cg = {c.name: c for c in
          load_campgrounds(D("campgrounds.csv"))}["Morgan Territory Backpack Camp"]
    assert "4.5 MILES FROM THE SITE" in cg.notes
    assert cg.coord_precision == "park"
    assert "nowhere near it" in cg.coord_source


def test_a_reservation_buys_the_night_and_costs_the_freedom_to_move():
    # "Campers are restricted to campsite during curfew hours (10pm-5am)" is
    # the sentence that answers whether a booking exempts you from a park's
    # posted hours -- left open at Mission Peak, where the penalty is a $300
    # minimum citation and the page says nothing about campers.
    cg = {c.name: c for c in
          load_campgrounds(D("campgrounds.csv"))}["Morgan Territory Backpack Camp"]
    assert "RESTRICTED TO THE CAMPSITE DURING CURFEW HOURS" in cg.notes
    assert "$300" in cg.notes, "names the Mission Peak penalty it bears on"



def test_morgan_territorys_gate_bands_cover_the_year_exactly():
    # Third clean set, with Reinhardt Redwood -- against Garin and Dry Creek
    # Pioneer leaving two days in no band and Las Trampas doubling one.
    from wayproof.park_access import load_park_access
    pa = load_park_access(D("park_access.csv"))["Morgan Territory Regional Preserve"]
    assert pa.gate_open == "8:00 AM"
    assert "no hole and no overlap" in pa.gate_hours_conditions
    for band in ("January 8am-5pm", "Apr 18-Sept 5 8am-8pm", "Nov 6-Dec 31 8am-5pm"):
        assert band in pa.gate_hours_conditions, band


def test_a_stated_no_fee_is_not_filed_like_an_absent_fee_section():
    # Morgan Territory says "Parking: No fee". Las Trampas' page has no Fees
    # section at all. Reading those the same way is how absent becomes free.
    from wayproof.park_access import load_park_access
    by_park = load_park_access(D("park_access.csv"))
    stated = by_park["Morgan Territory Regional Preserve"]
    silent = by_park["Las Trampas Wilderness Regional Preserve"]
    assert stated.entrance_fee == "No fee"
    assert silent.entrance_fee == ""
    assert "NO PARKING FEE IS PUBLISHED" in silent.fee_conditions
    assert "Absent is not free" in silent.fee_conditions


def test_the_ohlone_permit_is_gone_and_two_ebrpd_maps_still_require_it():
    # permit_group has always been "none" on this corridor, so nothing changed.
    # A blank nobody filled and a sourced absence with a date look identical in
    # a column and are not the same claim -- and EBRPD still links two maps
    # telling a planner to buy a permit that is no longer sold.
    from wayproof.data_loader import load_trailheads
    ths = {t.name: t for t in load_trailheads(D("trailheads.csv"))}
    for name in ("Del Valle (Lichen Bark)", "Stanford Ave Staging Area"):
        th = ths[name]
        assert th.permit_group == "none", name
        assert "ABOLISHED ON 1 JANUARY 2026" in th.notes, name
        assert "STALE-SOURCE TRAP IS LIVE" in th.notes, name
    cg = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}["Sunol Backpack Camp"]
    assert "Backpacking reservations are still required" in cg.notes


def test_del_valles_five_camps_answer_a_gap_this_project_logged_itself():
    # ReserveAmerica said "Group campsite gate hours change seasonally" at a
    # park where this project held no group campsite. The Ohlone permit map
    # names five, with the type in the name -- which is why they are added
    # where Reinhardt Redwood's symbol-coded labels were not.
    cgs = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}
    named = ["Wild Turkey Group Camp", "Punta Vaca Group Camp", "Cedar Group Camp",
             "Lil Chaparral Horse Camp", "Caballo Loco Horse Camp"]
    for name in named:
        c = cgs[name]
        assert c.park == "Del Valle Regional Park", name
        assert c.access_mode == "", name
        assert "ACCESS MODE IS NOT RECORDED" in c.notes, name
    assert {cgs[n].campsite_type for n in named} == {"group", "equestrian"}


def test_equestrian_resolves_no_class_specific_booking_channel_and_that_is_honest():
    # EBRPD names equestrian as a class in its own cancellation text, so the
    # word is the District's. No equestrian channel exists here, so a plan gets
    # the District-wide contact and no method -- which is what nobody knowing
    # how an equestrian site is booked should look like.
    from wayproof.booking import channels_for, load_booking_channels
    chans = channels_for(load_booking_channels(D("booking_channels.csv")),
                         "equestrian", agency="ebrpd")
    assert [c.applies_to for c in chans] == ["all"]


def test_one_booking_facility_sells_three_parks_worth_of_backpack_sites():
    # EB/110028 is titled just "Sunol" and lists MIS:, OHL: and SUN: sites.
    # That is why Mission Peak has no facility of its own -- and why searching
    # the booking system for a park's name is not a way to find out whether the
    # park has camping.
    sites = load_campsites(D("campsites.csv"))
    loops = {s.loop for s in sites if s.loop.endswith("Backpack")}
    assert loops == {"Mission Peak Backpack", "Ohlone Backpack", "Sunol Backpack"}
    cgs = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}
    assert "NOT NAMED FOR THIS PARK" in cgs["Eagle Springs"].notes
    assert "OPEN YEAR ROUND" in cgs["Sunol Backpack Camp"].notes


def test_the_ohlone_camps_park_field_is_right_about_the_fee_and_maybe_wrong_about_the_land():
    # Filed under Del Valle, prefixed OHL: by the facility. park_access joins
    # on this field, so as filed they inherit Del Valle's $10 weekend fee --
    # which is what a backpacker walking in from Lichen Bark actually pays,
    # whatever the boundary says.
    cgs = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}
    for name in ("Boyd Camp", "Stewart's Camp", "Maggie's Half Acre", "Doe Camp"):
        assert cgs[name].park == "Del Valle Regional Park", name
    sites = [s for s in load_campsites(D("campsites.csv")) if s.loop == "Ohlone Backpack"]
    assert {s.campground for s in sites} == {
        "Boyd Camp", "Doe Camp", "Maggie's Half Acre", "Stewart's Camp"}
