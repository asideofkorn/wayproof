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
    # The only campground here restricted by the character of the party.
    cg = {c.name: c for c in load_campgrounds(D("campgrounds.csv"))}["Star Mine Group Camp"]
    assert "ORGANIZED, EDUCATIONAL GROUPS ONLY" in cg.notes
    assert "NO WATER AT THE SITE" in cg.notes
    assert cg.fee_notes == "", "no fee is published for this camp; absent is not free"


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
