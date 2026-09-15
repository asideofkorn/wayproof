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
