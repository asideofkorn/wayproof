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
        "Corral Group Camp",
    ]
    # Five campgrounds ARE excluded for being unchecked -- Del Valle's group
    # and horse camps, named on a map that says nothing about reaching them --
    # and the rendering has to say so. A list of four that hides five nobody
    # looked at is the failure this whole command is shaped around.
    unchecked = unknown_access(cgs)
    assert len(unchecked) == 6
    text = "\n".join(format_campground_list(got, unrecorded_access=unchecked))
    assert "ACCESS MODE NOT RECORDED" in text
    assert "Caballo Loco Horse Camp" in text


def test_the_question_this_was_built_for_now_has_a_ranked_answer():
    # The whole point: "which campgrounds near me can I drive to". Nearest
    # first, from Oakland City Hall. If this ever returns an empty list again,
    # coordinates have been lost, not campgrounds.
    cgs = load_campgrounds(CAMPGROUNDS)
    got = find_campgrounds(cgs, access=DRIVE_IN, near=OAKLAND)
    assert [m.campground.name for m in got.matches] == [
        "Anthony Chabot Campground",
        "Corral Group Camp",
        "Dumbarton Quarry Campground on the Bay",
        "Del Valle Family Campground",
    ]
    assert got.unplaced == [], "every drive-in campground is placed"
    # Ordered, and the spread is real rather than noise in a centroid.
    miles = [m.distance_miles for m in got.matches]
    assert miles == sorted(miles)
    assert miles[0] < 15 < miles[-1]


def test_the_one_campground_precision_coordinate_renders_differently():
    # Dumbarton has its own ReserveAmerica facility page, so its GPS names the
    # camp. Every other coordinate here names a park and says so.
    cgs = load_campgrounds(CAMPGROUNDS)
    got = find_campgrounds(cgs, access=DRIVE_IN, near=OAKLAND)
    bases = {m.campground.name: m.distance_basis for m in got.matches}
    assert bases["Dumbarton Quarry Campground on the Bay"] == "to the campground"
    assert bases["Anthony Chabot Campground"] == "to the park, not the campground"
    assert {c.coord_precision for c in located(cgs)} == {COORD_PARK, COORD_CAMPGROUND}


def test_what_is_still_unplaced_is_still_reported_rather_than_dropped():
    # Ten campgrounds have no coordinates: Black Diamond's two, Briones' three,
    # Round Valley, Sunol, Mission Peak, and Del Valle's four Ohlone-trail
    # camps minus none -- the search must still carry them out.
    cgs = load_campgrounds(CAMPGROUNDS)
    got = find_campgrounds(cgs, near=OAKLAND)
    assert len(got.unplaced) == len(unlocated(cgs)) > 0
    assert "CANNOT BE PLACED" in "\n".join(format_campground_list(got))
