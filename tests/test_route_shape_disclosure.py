"""`plan` says it models one end, because it does.

From docs/user_stories/ohlone-traverse-2026-09.md, S1 -- a completed trip:

    True answer: Entry is Del Valle, exit is Stanford Ave, ~29 miles apart, in
    two different park units. Both need arrangements, and they are different
    arrangements.
    Today: `plan.py "Mission Peak"` names one trailhead, Stanford Ave. There is
    no way to express an entry and an exit. `Cluster.trailhead` is a single field.
    Exposes: The schema assumes out-and-back. A point-to-point traverse is a
    normal objective, not an edge case.

That schema gap is not closed here and these tests must not be read as closing
it. What changes is that the assumption stops being silent: the scorecard knew
(Q5 scores `no-model` for every objective) and the tool told the reader nothing,
which is the same held-and-hidden shape #35 drove to zero elsewhere.

Two things are therefore pinned deliberately:

- The disclosure states an ASSUMPTION, never a finding. Route shape is not in
  this dataset, and "out-and-back" is the common case and so the tempting
  default -- defaulting to it would repeat the blank-fee-reads-as-free bug with
  a field that now looks authoritative.
- Q5 stays `no-model`. Admitting a gap is not a place to put an exit. A test
  keeps anyone from reading this disclosure as coverage.

Run with:  python -m pytest tests/test_route_shape_disclosure.py
"""

from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts"))

from wayproof.access import load_approaches
from wayproof.camping import load_campgrounds, load_campsites
from wayproof.data_loader import load_peaks, load_trailheads
from wayproof.model import Peak
from wayproof.park_access import load_park_access
from wayproof.permits import load_permits
from wayproof.plan import PlanResult, format_plan_summary, resolve_plan
from wayproof.water import load_water_source_log, load_water_sources

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)  # noqa: E731
TRIP = date(2027, 7, 15)

ANCHOR = "MODELS ONE END ONLY"


def _inputs():
    return dict(
        peaks=load_peaks(D("peaks.csv"), collections_path=D("collections", "sps.csv")),
        trailheads=load_trailheads(D("trailheads.csv")),
        permits=load_permits(D("permits.csv"), D("release_policies.csv")),
        approaches=load_approaches(D("approaches.csv")),
        water_sources=load_water_sources(D("water_sources.csv")),
        water_source_log=load_water_source_log(D("water_source_log.csv")),
        campgrounds=load_campgrounds(D("campgrounds.csv")),
        campsites=load_campsites(D("campsites.csv")),
        park_access=list(load_park_access(D("park_access.csv")).values()),
    )


def _plan(name, trip=TRIP):
    return resolve_plan([name], trip, **_inputs())


# -- the story ---------------------------------------------------------------

def test_the_ohlone_end_no_longer_hides_that_the_other_end_is_missing():
    # S1. Mission Peak is the western end; the party's entry was Del Valle, 29
    # miles east. The plan still cannot express that -- but it now says so.
    text = format_plan_summary(_plan("Mission Peak"))
    assert ANCHOR in text
    assert "Del Valle" not in text, (
        "if the exit end is now actually modelled, this test is obsolete and S1 "
        "should be marked fixed rather than this assertion loosened"
    )


# -- it states an assumption, not a finding ---------------------------------

def test_the_disclosure_is_an_assumption_and_says_so():
    text = format_plan_summary(_plan("Mount Whitney"))
    assert "assumes you start and finish here" in text
    assert "not a finding about your route" in text


def test_no_route_shape_is_ever_claimed():
    # The trap: returning to start is the commonest case, so it is the tempting
    # default. Defaulting to it would be the blank-fee-reads-as-free bug again.
    #
    # Checked as asserting CONSTRUCTIONS rather than bare shape words. A first
    # version of this test failed on the disclosure's own conditional, "if yours
    # is one-way" -- the test was wrong, not the text. Bare "loop" is no good
    # either: permit prose names Rae Lakes Loop and the Tahoe Rim Trail loop.
    CLAIMS = ("route is an out-and-back", "route is a loop", "route is one-way",
              "this is an out-and-back", "this is a loop", "this is one-way",
              "route shape: ", "shape is out-and-back", "assumes an out-and-back",
              "assumes a loop")
    for name in ("Mount Whitney", "Mission Peak", "Mount Tallac", "Stanislaus Peak"):
        text = format_plan_summary(_plan(name))
        low = text.lower()
        for claim in CLAIMS:
            assert claim not in low, f"{name}: plan asserts a route shape: {claim!r}"
        # And the tempting default is never even named. An earlier draft listed
        # "(out-and-back, loop, one-way)" to explain the term; that enumeration
        # was dropped because the model has two states, not three -- naming three
        # implies a distinction this tool does not draw, and approach.py already
        # computes loop-vs-out-and-back for the distance it affects.
        assert "out-and-back" not in low, f"{name}: names the tempting default"


def test_the_unknown_state_says_it_was_not_guessed_and_names_the_remedy():
    text = format_plan_summary(_plan("Mount Whitney"))
    assert "has not been guessed" in text
    assert "--exit" in text


# -- placement --------------------------------------------------------------

def test_the_disclosure_reads_before_the_cost_block():
    # Cost is precisely what is incomplete for a one-way trip: the other end's
    # parking and entrance fee are not in it. A caveat printed after the money
    # is a caveat nobody reads, which is the S2 fee lesson.
    text = format_plan_summary(_plan("Rose Peak"))
    assert ANCHOR in text and "Cost" in text
    assert text.index(ANCHOR) < text.index("Cost")


def test_the_disclosure_sits_in_the_access_block():
    text = format_plan_summary(_plan("Mount Whitney"))
    assert text.index("Access") < text.index(ANCHOR)


def test_it_shows_even_when_the_entry_point_is_unresolved():
    # Both branches. An unresolved entry is a bigger problem, not a reason to
    # drop this one -- 153 of 462 objectives take that branch.
    result = _plan("Picket Guard Peak")
    assert result.entry_conflicts, "this objective's entry point is unresolved"
    text = format_plan_summary(result)
    assert "ENTRY POINT UNRESOLVED" in text
    assert ANCHOR in text


def test_nothing_is_disclosed_when_there_is_no_trailhead_at_all():
    # Nothing to assume about, so no assumption to confess.
    result = PlanResult(
        requested_names=["X"], objectives=[Peak("X", 0.0, 0.0, 1000.0)],
        not_found=[], trip_date=TRIP, trailhead=None, trailhead_ambiguous=False,
    )
    text = format_plan_summary(result)
    assert "No trailhead data available." in text
    assert ANCHOR not in text


# -- the machine surface ----------------------------------------------------

def test_an_agent_can_see_that_the_exit_is_missing():
    d = _plan("Mount Whitney").to_dict()
    assert d["exit_modelled"] is False
    assert d["route_shape"] == "unknown"


def test_the_machine_surface_does_not_default_the_shape():
    for name in ("Mission Peak", "Mount Tallac", "Picket Guard Peak"):
        d = _plan(name).to_dict()
        assert d["route_shape"] == "unknown", (
            f"{name}: a defaulted shape is a guess an agent cannot distinguish "
            "from a sourced fact"
        )


def test_the_keys_are_absent_rather_than_false_when_there_is_no_trailhead():
    result = PlanResult(
        requested_names=["X"], objectives=[], not_found=[], trip_date=TRIP,
        trailhead=None, trailhead_ambiguous=False,
    )
    d = result.to_dict()
    assert "route_shape" not in d and "exit_modelled" not in d


# -- this is not coverage ---------------------------------------------------

def test_q5_is_declined_not_no_model_now_that_there_is_somewhere_to_put_it():
    # This test previously asserted NO_MODEL, written when `plan` only disclosed
    # the gap. That was right then and is wrong now: `--exit` gives the other end
    # somewhere to live, so "the schema has no place to put this yet" is false.
    # Rewritten rather than loosened -- it was pinning the old state of the world.
    #
    # DECLINED is the honest replacement: "resolve the underlying uncertainty, or
    # accept it". The uncertainty is the caller's, because which end you finish at
    # is a choice rather than a fact about the terrain.
    import scorecard
    from scorecard import DECLINED, NO_MODEL, QUESTIONS, build
    built = build(TRIP)
    q5 = next(q for q in QUESTIONS if q.qid == "Q5")
    assert q5.text == "What do I need at the other end?"
    assert built["scores"]["Q5"][DECLINED] == built["n"]
    assert built["scores"]["Q5"][NO_MODEL] == 0


def test_q5_is_not_scored_as_answered_by_a_default_plan():
    # The line that must not be crossed. A plan that names no exit still tells
    # you nothing about one; declining is not answering.
    from scorecard import ANSWERED, PARTIAL, build
    built = build(TRIP)
    assert built["scores"]["Q5"][ANSWERED] == 0
    assert built["scores"]["Q5"][PARTIAL] == 0


def test_q5_states_where_naming_an_exit_still_comes_up_empty():
    # park_access.csv has one row and no Sierra trailhead carries a `park`, so
    # the parking half -- the half the question is named for -- is answerable for
    # the Ohlone trip and empty across the Sierra. A reader must not read
    # "declined" as "solved once you pass --exit".
    from scorecard import QUESTIONS
    q5 = next(q for q in QUESTIONS if q.qid == "Q5")
    assert "park_access.csv" in q5.limit
    assert "one row" in q5.limit


def test_the_schema_gap_count_drops_by_exactly_one():
    from scorecard import NO_MODEL, QUESTIONS, VERDICTS, build
    built = build(TRIP)
    structural = [q for q in QUESTIONS if q.structural]
    gaps = [q for q in structural
            if [v for v in VERDICTS if built["scores"][q.qid][v]] == [NO_MODEL]]
    assert len(structural) == 3, (
        "3 questions are constant for every objective. Q8 and Q17 left this set "
        "when booking_channels.change_cancel and advisories.csv gave them "
        "somewhere to live -- they now vary, which is what having a field means"
    )
    assert len(gaps) == 2, (
        "2 of them are genuine schema gaps -- Q11 and Q18. Q5 stopped being one "
        "when the other end got a field, Q8 when cancellation did, Q17 when "
        "advisories did. Conflating 'constant' with 'the schema cannot express "
        "it' overstates the gap; so does leaving NO_MODEL on a question the "
        "schema has since grown a place for"
    )


# ===========================================================================
# Two ends: `--exit` names the other one, and the shape falls out of it
# ===========================================================================
#
# The shape is DERIVED, never stored and never an input of its own. A trailhead
# is a place; "loop" is a property of a trip through places. Storing it on
# trailheads.csv would be the category error permit_zones.csv was keyed by
# permit_group to avoid -- "one trailhead reaches many zones".
#
# `returns_to_start` deliberately does not distinguish a loop from an
# out-and-back. Q5 only asks whether there IS another end, and approach.py
# already computes that distinction for the distance it affects, so a stored
# enum would assert a fact twice -- what test_notes_split.py exists to stop.

from wayproof.plan import ONE_WAY, RETURNS_TO_START, UNKNOWN_SHAPE  # noqa: E402


def _two_ended(name, exit_name, trip=TRIP):
    return resolve_plan([name], trip, exit_trailhead=exit_name, **_inputs())


# -- the story, finally answered --------------------------------------------

def test_the_ohlone_exit_ends_fee_now_reaches_the_cost_block():
    # S1's actual question. Entry is the Mission Peak end, exit is Del Valle --
    # a different park unit, with a $10 entrance fee that was in park_access.csv
    # all along and reachable from nothing. Q5's own falsification criterion is
    # "wrong if it treats exit parking as unrelated".
    result = _two_ended("Mission Peak", "Del Valle", trip=date(2027, 5, 1))
    assert result.route_shape == ONE_WAY
    exit_fees = [c for c in result.costs
                 if c.kind == "park_entrance" and "at the exit" in c.label]
    assert len(exit_fees) == 1
    assert exit_fees[0].detail == "$10"
    assert "weekends & holidays" in exit_fees[0].conditions
    text = format_plan_summary(result)
    assert "Del Valle Regional Park (at the exit)" in text
    assert "Exit: Del Valle (Lichen Bark)" in text


def test_the_one_end_disclosure_stops_once_both_ends_are_known():
    result = _two_ended("Mission Peak", "Del Valle", trip=date(2027, 5, 1))
    assert ANCHOR not in format_plan_summary(result)


# -- the shape is derived ---------------------------------------------------

def test_the_same_trailhead_at_both_ends_is_returns_to_start():
    result = _two_ended("Mount Whitney", "Whitney Portal")
    assert result.route_shape == RETURNS_TO_START
    assert result.returns_to_start is True
    assert result.exit_modelled is True
    text = format_plan_summary(result)
    assert "Returns to start" in text
    assert ANCHOR not in text


def test_a_different_trailhead_is_one_way():
    result = _two_ended("Mount Whitney", "Onion Valley")
    assert result.route_shape == ONE_WAY
    assert result.returns_to_start is False


def test_no_exit_named_stays_unknown_and_is_never_read_as_returning():
    result = _plan("Mount Whitney")
    assert result.route_shape == UNKNOWN_SHAPE
    assert result.exit_modelled is False
    assert result.returns_to_start is False, (
        "silence must not resolve to returns-to-start; it is the commonest case "
        "and therefore the tempting default, which is the blank-fee bug"
    )


# -- the computable half of reciprocity -------------------------------------

def test_two_ends_under_two_permit_groups_are_flagged():
    result = _two_ended("Mount Whitney", "Onion Valley")
    assert result.trailhead.permit_group == "whitney_zone"
    assert result.exit_trailhead.permit_group == "inyo_jmw_aaw"
    assert result.exit_permit_group_differs is True
    text = format_plan_summary(result)
    assert "TWO PERMIT GROUPS" in text
    assert "has NOT resolved it" in text, "flagging it is not answering it"


def test_two_ends_in_one_permit_group_are_not_flagged():
    # Both Ohlone ends are `none`. A spurious flag would train the reader to
    # ignore the real one.
    result = _two_ended("Mission Peak", "Del Valle", trip=date(2027, 5, 1))
    assert result.trailhead.permit_group == result.exit_trailhead.permit_group
    assert result.exit_permit_group_differs is False
    assert "TWO PERMIT GROUPS" not in format_plan_summary(result)


def test_returning_to_start_can_never_differ_from_itself():
    result = _two_ended("Mount Whitney", "Whitney Portal")
    assert result.exit_permit_group_differs is False


# -- the middle is still not modelled --------------------------------------

def test_both_modelled_shapes_admit_the_route_between_is_unresolved():
    # True of a returns-to-start plan as much as a one-way one: Onion Valley out
    # and back over Kearsarge Pass into SEKI ends where it started and still
    # crosses an agency line. Endpoints do not determine crossings.
    for exit_name in ("Whitney Portal", "Onion Valley"):
        text = format_plan_summary(_two_ended("Mount Whitney", exit_name))
        assert "ENDS ONLY, NOT THE ROUTE BETWEEN THEM" in text


def test_the_machine_surface_says_the_middle_is_not_modelled():
    d = _two_ended("Mount Whitney", "Onion Valley").to_dict()
    assert d["exit"]["route_between_ends_modelled"] is False


# -- one gate is charged once ----------------------------------------------

def test_the_same_park_at_both_ends_is_not_charged_twice():
    from wayproof.park_access import ParkAccess
    from wayproof.plan import FacilitiesInfo, trip_costs
    pa = ParkAccess(park="P", entrance_fee="$10", fee_conditions="")
    fac = FacilitiesInfo(park_access=pa)
    both = trip_costs([], fac, exit_park_access=pa, entry_park="P")
    assert len([c for c in both if c.kind == "park_entrance"]) == 1, (
        "one gate, charged once -- listing it twice inflates the trip"
    )
    other = ParkAccess(park="Q", entrance_fee="$7", fee_conditions="")
    two = trip_costs([], fac, exit_park_access=other, entry_park="P")
    assert len([c for c in two if c.kind == "park_entrance"]) == 2


# -- a name that does not resolve fails loudly ------------------------------

def test_an_unmatched_exit_name_is_reported_not_ignored():
    result = _two_ended("Mount Whitney", "Nowhere Trailhead")
    assert result.exit_trailhead is None
    assert result.route_shape == UNKNOWN_SHAPE
    text = format_plan_summary(result)
    assert "EXIT NOT RESOLVED" in text
    assert text.index("EXIT NOT RESOLVED") < text.index("Cost")
    assert any("Nowhere Trailhead" in w for w in result.warnings)


def test_an_ambiguous_exit_name_lists_candidates_and_picks_nothing():
    result = _two_ended("Mount Whitney", "Valley")
    assert result.exit_trailhead is None
    assert "Onion Valley (Kearsarge Pass)" in result.exit_candidates
    assert "Squaw Valley (Granite Chief)" in result.exit_candidates
    assert "EXIT NOT RESOLVED" in format_plan_summary(result)


def test_the_remedy_hint_is_not_shown_to_someone_who_already_tried():
    tried = format_plan_summary(_two_ended("Mount Whitney", "Nowhere Trailhead"))
    assert "Name it with --exit" not in tried
    assert "Name it with --exit" in format_plan_summary(_plan("Mount Whitney"))


def test_a_partial_name_resolves_when_it_is_unambiguous():
    # Stored names carry parentheticals nobody types.
    result = _two_ended("Mount Whitney", "Onion Valley")
    assert result.exit_trailhead.name == "Onion Valley (Kearsarge Pass)"


def test_an_unresolved_exit_is_visible_on_the_machine_surface():
    d = _two_ended("Mount Whitney", "Nowhere Trailhead").to_dict()
    assert d["exit_modelled"] is False
    assert "exit" not in d
    assert d["exit_unresolved"]["requested"] == "Nowhere Trailhead"
