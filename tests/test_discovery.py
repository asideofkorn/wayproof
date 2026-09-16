"""Finding a campground you cannot already name.

Run with:  python -m pytest tests/test_discovery.py
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.camping import (
    COORD_CAMPGROUND, COORD_PARK, DRIVE_IN, HIKE_IN, Campground,
    load_campgrounds, located, unknown_access, unlocated,
)
from wayproof.discovery import (
    find_campgrounds, format_campground_list,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMPGROUNDS = os.path.join(ROOT, "data", "campgrounds.csv")
OAKLAND = (37.8044, -122.2712)


def _cg(name, **kw):
    kw.setdefault("park", "P")
    return Campground(name=name, **kw)


# -- filters -----------------------------------------------------------------

def test_a_filter_matches_exactly_and_never_matches_a_blank_field():
    # Asking for drive-in must not return a campground nobody has checked.
    cgs = [_cg("a", access_mode=DRIVE_IN), _cg("b", access_mode=HIKE_IN), _cg("c")]
    got = find_campgrounds(cgs, access=DRIVE_IN)
    assert [m.campground.name for m in got.matches] == ["a"]


def test_filters_compose():
    cgs = [_cg("a", access_mode=DRIVE_IN, campsite_type="family"),
           _cg("b", access_mode=DRIVE_IN, campsite_type="group")]
    got = find_campgrounds(cgs, access=DRIVE_IN, campsite_type="family")
    assert [m.campground.name for m in got.matches] == ["a"]
    assert got.filters == (("access", DRIVE_IN), ("type", "family"))


def test_agency_matches_one_key_of_a_co_managed_list():
    cgs = [_cg("a", agency_id="ebrpd;ebmud"), _cg("b", agency_id="inyo_nf")]
    assert [m.campground.name for m in find_campgrounds(cgs, agency="ebmud").matches] \
        == ["a"]


def test_no_filters_returns_everything_rather_than_nothing():
    cgs = [_cg("a"), _cg("b")]
    got = find_campgrounds(cgs)
    assert len(got.matches) == 2
    assert got.filters == ()


# -- proximity ---------------------------------------------------------------

def test_nearest_first_and_the_far_one_is_dropped_only_when_asked():
    near = _cg("near", latitude=37.81, longitude=-122.27, coord_precision=COORD_CAMPGROUND)
    far = _cg("far", latitude=37.0, longitude=-121.0, coord_precision=COORD_CAMPGROUND)
    got = find_campgrounds([far, near], near=OAKLAND)
    assert [m.campground.name for m in got.matches] == ["near", "far"]
    assert got.matches[0].distance_miles < got.matches[1].distance_miles

    bounded = find_campgrounds([far, near], near=OAKLAND, within_miles=10)
    assert [m.campground.name for m in bounded.matches] == ["near"]


def test_an_unplaceable_campground_is_carried_out_not_dropped():
    # The failure being avoided: a list of three that looks like the answer
    # while twenty-one were never measured. Unmeasured is not far away.
    placed = _cg("placed", latitude=37.81, longitude=-122.27,
                 coord_precision=COORD_CAMPGROUND)
    got = find_campgrounds([placed, _cg("nowhere")], near=OAKLAND)
    assert [m.campground.name for m in got.matches] == ["placed"]
    assert [c.name for c in got.unplaced] == ["nowhere"]


def test_a_within_filter_does_not_swallow_the_unplaceable_ones():
    # They are not "beyond 10 miles"; they are unknown, and a bound must not
    # quietly reclassify them as excluded.
    got = find_campgrounds([_cg("nowhere")], near=OAKLAND, within_miles=10)
    assert got.matches == []
    assert [c.name for c in got.unplaced] == ["nowhere"]


def test_coordinates_decide_nothing_without_a_reference_point():
    got = find_campgrounds([_cg("nowhere")])
    assert len(got.matches) == 1 and got.unplaced == []


def test_a_bound_with_nothing_to_measure_from_is_an_error_not_an_empty_list():
    with pytest.raises(ValueError, match="reference point"):
        find_campgrounds([_cg("a")], within_miles=10)


def test_a_distance_says_what_it_is_a_distance_to():
    park = _cg("p", latitude=37.81, longitude=-122.27, coord_precision=COORD_PARK)
    exact = _cg("c", latitude=37.81, longitude=-122.27, coord_precision=COORD_CAMPGROUND)
    got = find_campgrounds([park, exact], near=OAKLAND)
    bases = {m.campground.name: m.distance_basis for m in got.matches}
    assert bases["p"] == "to the park, not the campground"
    assert bases["c"] == "to the campground"


# -- rendering ---------------------------------------------------------------

def test_the_rendering_names_the_question_the_list_answers():
    got = find_campgrounds([_cg("a", access_mode=DRIVE_IN)], access=DRIVE_IN)
    assert "access=drive_in" in format_campground_list(got)[0]


def test_an_empty_result_says_it_is_not_evidence_of_absence():
    got = find_campgrounds([_cg("a", access_mode=HIKE_IN)], access=DRIVE_IN)
    text = "\n".join(format_campground_list(got))
    assert "NOTHING MATCHED" in text
    assert "not the same as nothing existing" in text


def test_the_rendering_prints_the_unplaceable_and_the_unchecked():
    got = find_campgrounds([_cg("placed", access_mode=DRIVE_IN),
                            _cg("nowhere", access_mode=DRIVE_IN)], near=OAKLAND)
    text = "\n".join(format_campground_list(got, unrecorded_access=[_cg("unchecked")]))
    assert "CANNOT BE PLACED" in text and "nowhere" in text
    assert "ACCESS MODE NOT RECORDED" in text and "unchecked" in text
    assert "Absent is not a value" in text


def test_a_distance_is_labelled_straight_line_not_driving():
    got = find_campgrounds([_cg("a", latitude=37.81, longitude=-122.27,
                                coord_precision=COORD_PARK)], near=OAKLAND)
    text = "\n".join(format_campground_list(got))
    assert "straight-line, not driving" in text
    assert "to the park, not the campground" in text


# -- the committed data ------------------------------------------------------

def test_the_drive_in_question_this_was_built_for():
    cgs = load_campgrounds(CAMPGROUNDS)
    got = find_campgrounds(cgs, access=DRIVE_IN)
    assert [m.campground.name for m in got.matches] == [
        "Del Valle Family Campground",
        "Anthony Chabot Campground",
        "Dumbarton Quarry Campground on the Bay",
    ]
    # Nothing is excluded for being unchecked, because nothing is unchecked.
    assert unknown_access(cgs) == []


def test_the_near_search_can_currently_place_almost_nothing_and_says_so():
    # Two of twenty-four, both at park precision, both off a ReserveAmerica
    # overview page. This test exists to fail loudly if that silently changes
    # in either direction -- and to state that the feature is honest rather
    # than useful until the coordinates land.
    cgs = load_campgrounds(CAMPGROUNDS)
    assert [c.name for c in located(cgs)] == ["Dairy Glen Group Camp",
                                              "Arroyo Flats Group Camp"]
    assert {c.coord_precision for c in located(cgs)} == {COORD_PARK}

    got = find_campgrounds(cgs, access=DRIVE_IN, near=OAKLAND)
    assert got.matches == [], "no drive-in campground has coordinates yet"
    assert len(got.unplaced) == 3
    assert "CANNOT BE PLACED" in "\n".join(format_campground_list(got))
