"""Tests for the plan module (wayproof.plan).

Run with:  python -m pytest tests/test_plan.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.access import (
    ENTRY_CONTRADICTED,
    ENTRY_CORRIDOR,
    ENTRY_INFERRED,
    ENTRY_ROUTE_CONSISTENT,
    ENTRY_SOURCED,
    ApproachRoute,
    classify_entry,
    load_approaches,
    normalise_entry_name,
    trailhead_name_index,
)
from wayproof.approach import choose_trailhead
from wayproof.model import Peak
from wayproof.camping import load_campgrounds, load_campsites
from wayproof.data_loader import load_peaks, load_trailheads
from wayproof.park_access import load_park_access
from wayproof.permits import load_permits
from wayproof.plan import resolve_plan, format_plan_summary
from wayproof.water import load_water_sources, load_water_source_log

PEAKS = os.path.join(os.path.dirname(__file__), "..", "data", "peaks.csv")
COLLECTIONS = os.path.join(os.path.dirname(__file__), "..", "data", "collections", "sps.csv")
TRAILHEADS = os.path.join(os.path.dirname(__file__), "..", "data", "trailheads.csv")
PERMITS = os.path.join(os.path.dirname(__file__), "..", "data", "permits.csv")
RELEASE_POLICIES = os.path.join(os.path.dirname(__file__), "..", "data", "release_policies.csv")
APPROACHES = os.path.join(os.path.dirname(__file__), "..", "data", "approaches.csv")
WATER_SOURCES = os.path.join(os.path.dirname(__file__), "..", "data", "water_sources.csv")
WATER_SOURCE_LOG = os.path.join(os.path.dirname(__file__), "..", "data", "water_source_log.csv")
CAMPGROUNDS = os.path.join(os.path.dirname(__file__), "..", "data", "campgrounds.csv")
CAMPSITES = os.path.join(os.path.dirname(__file__), "..", "data", "campsites.csv")
PARK_ACCESS = os.path.join(os.path.dirname(__file__), "..", "data", "park_access.csv")


def _inputs(list_filter="SPS"):
    peaks = load_peaks(PEAKS, list_filter=list_filter, collections_path=COLLECTIONS)
    trailheads = load_trailheads(TRAILHEADS)
    permits = load_permits(PERMITS, RELEASE_POLICIES)
    approaches = load_approaches(APPROACHES)
    return peaks, trailheads, permits, approaches


def test_resolve_plan_single_objective_matches_case_insensitively():
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["mount whitney"], date(2027, 7, 15), peaks, trailheads,
                           permits, approaches=approaches)
    assert not result.not_found
    assert [p.name for p in result.objectives] == ["Mount Whitney"]
    assert result.trailhead is not None
    assert result.trailhead.name == "Whitney Portal"
    assert len(result.permit_entries) == 1
    assert not result.trailhead_ambiguous


def test_resolve_plan_shared_trailhead_surfaces_approach_override():
    # Mirrors test_permits.test_mount_russell_approach_surfaces_second_permit,
    # but through the plan entry point end to end.
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Mount Whitney", "Mount Russell"], date(2027, 7, 1),
                           peaks, trailheads, permits, approaches=approaches)
    assert not result.not_found
    assert result.trailhead.name == "Whitney Portal"
    assert not result.trailhead_ambiguous  # both default to Whitney Portal
    assert len(result.permit_entries) == 2
    default_entry = next(e for e in result.permit_entries if not e.peak_note)
    russell_entry = next(e for e in result.permit_entries if e.peak_note)
    assert "Whitney" in default_entry.permit_type
    assert "Mount Russell" in russell_entry.peak_note
    assert russell_entry.approach_status == "confirmed"


def test_resolve_plan_reports_not_found_objectives():
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Mount Whitney", "Not A Real Peak"], date(2027, 7, 15),
                           peaks, trailheads, permits, approaches=approaches)
    assert result.not_found == ["Not A Real Peak"]
    assert any("Not A Real Peak" in w for w in result.warnings)
    # The one real objective still resolves.
    assert [p.name for p in result.objectives] == ["Mount Whitney"]
    assert result.trailhead is not None


def test_resolve_plan_flags_mismatched_default_trailheads():
    # Independence Peak defaults to Onion Valley, not Whitney Portal -- a
    # plan combining it with Mount Whitney should flag the mismatch rather
    # than silently picking one.
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Mount Whitney", "Independence Peak"], date(2027, 7, 15),
                           peaks, trailheads, permits, approaches=approaches)
    assert result.trailhead_ambiguous
    assert any("do not share the same default trailhead" in w for w in result.warnings)


def test_resolve_plan_no_objectives_found():
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Not A Real Peak"], date(2027, 7, 15),
                           peaks, trailheads, permits, approaches=approaches)
    assert result.objectives == []
    assert result.trailhead is None
    assert result.permit_entries == []
    summary = format_plan_summary(result)
    assert "nothing to plan" in summary.lower()


def test_format_plan_summary_includes_official_mileage():
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Mount Whitney"], date(2027, 7, 15), peaks, trailheads,
                           permits, approaches=approaches)
    summary = format_plan_summary(result)
    assert "MOUNT WHITNEY" in summary   # the title line is upper-cased by the renderer
    assert "mi round trip" in summary
    assert "not a computed combined route" in summary.lower()


def test_full_dataset_loads_without_cross_list_name_collisions():
    # A couple of names ("Mount Johnson", "Thunder Mountain") used to exist
    # under both list=SPS and list=non-SPS with conflicting elevations,
    # crashing an unfiltered load. scripts/split_collections.py now applies a
    # documented SPS-preferred tie-break when producing data/peaks.csv and
    # data/collections/sps.csv, so this should no longer raise -- this is
    # exactly why plan.py can default --list to "all" now. The underlying
    # discrepancy (which value is actually correct, not just which list to
    # prefer) is still a separate, tracked follow-up.
    peaks = load_peaks(PEAKS, list_filter=None, collections_path=COLLECTIONS)
    assert len({p.name for p in peaks}) == len(peaks)


def test_plan_result_to_dict_is_json_serializable():
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Mount Whitney", "Mount Russell"], date(2027, 7, 1),
                           peaks, trailheads, permits, approaches=approaches)
    payload = result.to_dict()
    serialized = json.dumps(payload)  # must not raise
    assert "Mount Whitney" in serialized
    assert payload["trailhead"]["name"] == "Whitney Portal"
    assert len(payload["permits"]) == 2


def test_resolve_plan_surfaces_open_questions_for_rose_peak():
    # End-to-end check of the scavenger-hunt nudge, against the real
    # committed data: Rose Peak's nearest trailhead (Del Valle (Lichen Bark))
    # has two water sources with no recorded coordinates yet.
    peaks = load_peaks(PEAKS, list_filter=None, collections_path=COLLECTIONS)
    trailheads = load_trailheads(TRAILHEADS)
    permits = load_permits(PERMITS, RELEASE_POLICIES)
    approaches = load_approaches(APPROACHES)
    water_sources = load_water_sources(WATER_SOURCES)
    water_source_log = load_water_source_log(WATER_SOURCE_LOG)
    campgrounds = load_campgrounds(CAMPGROUNDS)
    campsites = load_campsites(CAMPSITES)

    result = resolve_plan(["Rose Peak"], date(2027, 6, 1), peaks, trailheads, permits,
                           approaches=approaches, water_sources=water_sources,
                           water_source_log=water_source_log, campgrounds=campgrounds,
                           campsites=campsites)

    assert result.open_questions
    targets = {q.target_key for q in result.open_questions}
    assert "Lichen Bark (Del Valle)" in targets
    assert "Stromer Springs" in targets
    # Global-only gaps (e.g. Boyd Camp's water conflict, Sunol campsite
    # proximity) must not leak into a Rose-Peak-scoped plan.
    assert "Boyd Camp" not in targets


def test_resolve_plan_without_facilities_data_has_no_open_questions():
    # The new optional params must be fully backward compatible -- an
    # existing caller that doesn't pass them still works exactly as before.
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Mount Whitney"], date(2027, 7, 15), peaks, trailheads,
                           permits, approaches=approaches)
    assert result.open_questions == []


def test_format_plan_summary_includes_help_us_confirm_section():
    peaks = load_peaks(PEAKS, list_filter=None, collections_path=COLLECTIONS)
    trailheads = load_trailheads(TRAILHEADS)
    permits = load_permits(PERMITS, RELEASE_POLICIES)
    water_sources = load_water_sources(WATER_SOURCES)

    result = resolve_plan(["Mission Peak"], date(2027, 6, 1), peaks, trailheads, permits,
                           water_sources=water_sources)
    summary = format_plan_summary(result)
    assert "Help us confirm" in summary
    assert "GNIS" in summary


def test_resolve_plan_populates_facilities_for_rose_peak():
    peaks = load_peaks(PEAKS, list_filter=None, collections_path=COLLECTIONS)
    trailheads = load_trailheads(TRAILHEADS)
    permits = load_permits(PERMITS, RELEASE_POLICIES)
    water_sources = load_water_sources(WATER_SOURCES)
    water_source_log = load_water_source_log(WATER_SOURCE_LOG)
    campgrounds = load_campgrounds(CAMPGROUNDS)
    campsites = load_campsites(CAMPSITES)
    park_access = list(load_park_access(PARK_ACCESS).values())

    result = resolve_plan(["Rose Peak"], date(2027, 6, 1), peaks, trailheads, permits,
                           water_sources=water_sources, water_source_log=water_source_log,
                           campgrounds=campgrounds, campsites=campsites, park_access=park_access)

    assert result.facilities is not None
    water_names = {w.name for w in result.facilities.water_sources}
    assert "Stromer Springs" in water_names
    assert result.facilities.water_status["Stromer Springs"].observed_status == "running"

    campground_names = {c.name for c in result.facilities.campgrounds}
    assert "Del Valle Family Campground" in campground_names
    assert "Eagle Springs" not in campground_names  # Mission Peak's, not Rose Peak's

    assert result.facilities.park_access is not None
    assert result.facilities.park_access.park == "Del Valle Regional Park"


def test_resolve_plan_mission_peak_facilities_dont_leak_del_valle_campgrounds():
    peaks = load_peaks(PEAKS, list_filter=None, collections_path=COLLECTIONS)
    trailheads = load_trailheads(TRAILHEADS)
    permits = load_permits(PERMITS, RELEASE_POLICIES)
    campgrounds = load_campgrounds(CAMPGROUNDS)
    park_access = list(load_park_access(PARK_ACCESS).values())

    result = resolve_plan(["Mission Peak"], date(2027, 6, 1), peaks, trailheads, permits,
                           campgrounds=campgrounds, park_access=park_access)

    campground_names = {c.name for c in result.facilities.campgrounds}
    assert campground_names == {"Eagle Springs"}
    # Mission Peak Regional Preserve has no park_access.csv row -- must not
    # silently show Del Valle's fee/hours as if they applied here too.
    assert result.facilities.park_access is None


def test_resolve_plan_sierra_peak_has_no_facilities():
    # No water_sources/campgrounds/park_access data exists for Sierra
    # trailheads -- facilities must stay None, not an empty-but-present object.
    peaks, trailheads, permits, approaches = _inputs()
    water_sources = load_water_sources(WATER_SOURCES)
    campgrounds = load_campgrounds(CAMPGROUNDS)
    park_access = list(load_park_access(PARK_ACCESS).values())

    result = resolve_plan(["Mount Whitney"], date(2027, 7, 15), peaks, trailheads, permits,
                           approaches=approaches, water_sources=water_sources,
                           campgrounds=campgrounds, park_access=park_access)
    assert result.facilities is None


def test_format_plan_summary_includes_facilities_section():
    peaks = load_peaks(PEAKS, list_filter=None, collections_path=COLLECTIONS)
    trailheads = load_trailheads(TRAILHEADS)
    permits = load_permits(PERMITS, RELEASE_POLICIES)
    water_sources = load_water_sources(WATER_SOURCES)
    water_source_log = load_water_source_log(WATER_SOURCE_LOG)
    campgrounds = load_campgrounds(CAMPGROUNDS)
    campsites = load_campsites(CAMPSITES)
    park_access = list(load_park_access(PARK_ACCESS).values())

    result = resolve_plan(["Rose Peak"], date(2027, 6, 1), peaks, trailheads, permits,
                           water_sources=water_sources, water_source_log=water_source_log,
                           campgrounds=campgrounds, campsites=campsites, park_access=park_access)
    summary = format_plan_summary(result)
    assert "Facilities" in summary
    assert "Del Valle Family Campground" in summary
    assert "Park access (Del Valle Regional Park)" in summary
    assert "Entrance fee: $10" in summary


def test_facilities_serializes_to_json():
    peaks = load_peaks(PEAKS, list_filter=None, collections_path=COLLECTIONS)
    trailheads = load_trailheads(TRAILHEADS)
    permits = load_permits(PERMITS, RELEASE_POLICIES)
    water_sources = load_water_sources(WATER_SOURCES)
    campgrounds = load_campgrounds(CAMPGROUNDS)
    campsites = load_campsites(CAMPSITES)
    park_access = list(load_park_access(PARK_ACCESS).values())

    result = resolve_plan(["Rose Peak"], date(2027, 6, 1), peaks, trailheads, permits,
                           water_sources=water_sources, campgrounds=campgrounds,
                           campsites=campsites, park_access=park_access)
    payload = result.to_dict()
    json.dumps(payload)  # must not raise
    assert "facilities" in payload
    assert payload["facilities"]["park_access"]["park"] == "Del Valle Regional Park"
    campground_payload = next(c for c in payload["facilities"]["campgrounds"]
                               if c["name"] == "Del Valle Family Campground")
    assert "approximate" in campground_payload["nightly_entry_cutoff"].lower()


# -- how the entry point was resolved ---------------------------------------
#
# `plan`'s permit answer rests on objective -> entry point, and that link is
# `nearest_trailhead`: straight-line geometry, which wayproof.views itself
# labels UNVERIFIED. Printing a permit off it under a "we last checked this
# against the source on ..." line implies the whole chain was verified. These
# tests pin the five states apart, and the dataset-wide counts are the burn-down
# measure for building data/entry_trails.csv.

def _entry(name, trip=date(2027, 7, 15), list_filter="SPS"):
    peaks, trailheads, permits, approaches = _inputs(list_filter)
    result = resolve_plan([name], trip, peaks, trailheads, permits,
                          approaches=approaches)
    assert len(result.entry_resolutions) == 1, f"no entry resolution for {name}"
    return result, result.entry_resolutions[0]


def test_a_confirmed_approach_row_reads_as_sourced():
    result, entry = _entry("Mount Russell")
    assert entry.basis == ENTRY_SOURCED
    assert entry.confirmed
    assert not any("DIFFERENT PERMITS" in w for w in result.warnings)


def test_a_route_naming_the_chosen_trailhead_reads_as_consistent():
    _, entry = _entry("Mount Tallac")
    assert entry.basis == ENTRY_ROUTE_CONSISTENT
    assert entry.confirmed
    assert entry.sourced_trailhead == "Mount Tallac"


def test_a_route_naming_a_different_trailhead_is_contradicted_and_warns():
    # Sourced route is the Shepherd Pass Trail (Inyo NF, east of the crest);
    # geometry picks Mineral King (SEKI, west of it).
    result, entry = _entry("Picket Guard Peak")
    assert entry.basis == ENTRY_CONTRADICTED
    assert not entry.confirmed
    assert entry.sourced_trailhead == "Shepherd Pass"
    warning = next(w for w in result.warnings if w.startswith("Picket Guard Peak:"))
    assert "DIFFERENT PERMITS" in warning
    assert "seki" in warning and "inyo_jmw_aaw" in warning


def test_the_lottery_case_is_named_because_missing_the_window_is_unrecoverable():
    # The sharpest instance: geometry sends a reader into the Whitney Zone
    # lottery (Feb 1 - Mar 1) for a peak whose sourced route needs an ordinary
    # Inyo NF rolling reservation. whitney_zone's own `excludes` already says
    # the permit covers the classic Mt. Whitney Trail only.
    result, entry = _entry("Mount LeConte")
    assert entry.basis == ENTRY_CONTRADICTED
    assert any("whitney_zone" in w and "DIFFERENT PERMITS" in w for w in result.warnings)


def test_a_contradiction_within_one_permit_group_says_the_permit_still_stands():
    # 31 objectives are contradicted; only 7 change the permit product. Warning
    # about the other 24 in the same words would make the loud case unreadable.
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Cardinal Mountain"], date(2027, 7, 15), peaks,
                          trailheads, permits, approaches=approaches)
    entry = result.entry_resolutions[0]
    assert entry.basis == ENTRY_CONTRADICTED
    warning = next(w for w in result.warnings if w.startswith("Cardinal Mountain:"))
    assert "DIFFERENT PERMITS" not in warning
    assert "same permit group" in warning


def test_a_long_distance_corridor_is_not_reported_as_a_defect():
    # A PCT/JMT objective genuinely has no single entry point. That needs an
    # explicit entry/exit pair, not a corrected trailhead.
    _, entry = _entry("Sawtooth Peak (S)")
    assert entry.basis == ENTRY_CORRIDOR
    assert not entry.confirmed


def test_geometry_alone_reads_as_inferred():
    _, entry = _entry("Smith Mountain")
    assert entry.basis == ENTRY_INFERRED
    assert not entry.confirmed


def test_an_unconfirmed_approach_row_does_not_count_as_sourced():
    # That is the point of the status. The permit report still raises its own
    # UNCERTAIN caution, so both facts reach the reader.
    result, entry = _entry("Mount Irvine")
    assert entry.basis == ENTRY_INFERRED
    assert any("UNCERTAIN for Mount Irvine" in e.peak_note
               for e in result.permit_entries)


def test_the_basis_reaches_both_the_text_and_the_json():
    peaks, trailheads, permits, approaches = _inputs()
    result = resolve_plan(["Picket Guard Peak"], date(2027, 7, 15), peaks,
                          trailheads, permits, approaches=approaches)
    assert "Entry basis" in format_plan_summary(result)
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["entry_resolutions"][0]["basis"] == ENTRY_CONTRADICTED
    assert payload["entry_resolutions"][0]["confirmed"] is False


def test_the_whole_sps_list_resolves_to_the_expected_mix():
    # The burn-down metric. `inferred` + `contradicted` is the size of the
    # data/entry_trails.csv job; it must only ever go DOWN. If this fails
    # because a number dropped, that is progress -- update it. If it fails
    # because `inferred` rose, something regressed.
    peaks, trailheads, permits, approaches = _inputs()
    index = trailhead_name_index([t.name for t in trailheads])
    counts: dict = {}
    for peak in peaks:
        chosen = choose_trailhead([peak], trailheads)
        entry = classify_entry(peak, chosen.name, index, approaches)
        counts[entry.basis] = counts.get(entry.basis, 0) + 1
    assert counts == {
        ENTRY_SOURCED: 1,
        ENTRY_ROUTE_CONSISTENT: 59,
        ENTRY_CONTRADICTED: 31,
        ENTRY_CORRIDOR: 13,
        ENTRY_INFERRED: 143,
    }, counts
    assert sum(counts.values()) == 247
    unconfirmed = counts[ENTRY_INFERRED] + counts[ENTRY_CONTRADICTED] + counts[ENTRY_CORRIDOR]
    assert unconfirmed == 187, (
        "187 of 247 SPS objectives have no sourced entry relationship -- this is "
        "what data/entry_trails.csv exists to reduce"
    )


# -- the classifier itself, on synthetic data -------------------------------
#
# The tests above pin real peaks, which catches a data regression but not a
# logic one -- and the ambiguity branch has no instance in the dataset at all,
# so nothing above reaches it.

def _peak(name, sourced_route=None, **meta):
    if sourced_route is not None:
        meta["trailhead"] = sourced_route
    return Peak(name=name, latitude=37.0, longitude=-119.0, elevation_ft=12000,
                meta=meta)


def test_normalise_folds_a_trail_name_onto_its_entry_point():
    assert normalise_entry_name("Shepherd Pass Trail") == normalise_entry_name("Shepherd Pass")
    assert normalise_entry_name("McMurray Meadows Road") == "mcmurray meadows"
    assert normalise_entry_name("Onion Valley (Kearsarge Pass)") == "onion valley"
    assert normalise_entry_name("") == ""


def test_a_trailhead_is_indexed_under_its_parenthetical_too():
    # The parenthetical is usually the trail, which is what a route name uses:
    # "Kearsarge Pass Trail" reaches "Onion Valley (Kearsarge Pass)". Without
    # this, 33 more objectives fall back to geometry for no good reason.
    index = trailhead_name_index(["Onion Valley (Kearsarge Pass)"])
    assert index["onion valley"] == {"Onion Valley (Kearsarge Pass)"}
    assert index["kearsarge pass"] == {"Onion Valley (Kearsarge Pass)"}


def test_an_ambiguous_route_name_is_inferred_rather_than_guessed():
    # Two trailheads sharing a normalised form cannot resolve a route name.
    # Picking either would assert an entry point on a coin flip.
    index = trailhead_name_index(["Twin Lakes (Bridgeport)", "Twin Lakes (Mammoth)"])
    assert len(index["twin lakes"]) == 2
    got = classify_entry(_peak("X", sourced_route="Twin Lakes Trail"),
                         "Twin Lakes (Bridgeport)", index)
    assert got.basis == ENTRY_INFERRED
    assert got.sourced_route == "Twin Lakes Trail"
    assert got.sourced_trailhead == ""


def test_classify_entry_branch_table():
    index = trailhead_name_index(["Shepherd Pass", "Mineral King"])
    cases = [
        ("no sourced route", _peak("A"), ENTRY_INFERRED),
        ("route is a corridor", _peak("B", sourced_route="Pacific Crest Trail"),
         ENTRY_CORRIDOR),
        ("route names nothing we hold", _peak("C", sourced_route="Jerky Meadows Trail"),
         ENTRY_INFERRED),
        ("route names the chosen entry", _peak("D", sourced_route="Shepherd Pass Trail"),
         ENTRY_ROUTE_CONSISTENT),
        ("route names another entry", _peak("E", sourced_route="Mineral King Trail"),
         ENTRY_CONTRADICTED),
    ]
    for label, peak, expected in cases:
        got = classify_entry(peak, "Shepherd Pass", index)
        assert got.basis == expected, f"{label}: got {got.basis}"
        assert got.trailhead == "Shepherd Pass"


def test_a_confirmed_row_outranks_a_contradicting_route_name():
    # An explicit sourced relationship is the whole point; a route name that
    # disagrees with it must not downgrade it.
    index = trailhead_name_index(["Whitney Portal", "Mineral King"])
    route = ApproachRoute(peak_name="F", trailhead="Whitney Portal",
                          approach_name="Mountaineers Route",
                          permit_group="inyo_jmw_aaw", status="confirmed")
    got = classify_entry(_peak("F", sourced_route="Mineral King Trail"),
                         "Whitney Portal", index, [route])
    assert got.basis == ENTRY_SOURCED
    assert got.sourced_route == "Mountaineers Route"


def test_a_confirmed_row_for_another_trailhead_is_not_applied_here():
    index = trailhead_name_index(["Whitney Portal", "Mineral King"])
    route = ApproachRoute(peak_name="G", trailhead="Whitney Portal",
                          approach_name="Mountaineers Route",
                          permit_group="inyo_jmw_aaw", status="confirmed")
    got = classify_entry(_peak("G"), "Mineral King", index, [route])
    assert got.basis == ENTRY_INFERRED
