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
    # The trap: out-and-back is the commonest shape, so it is the tempting
    # default. Defaulting to it would be the blank-fee-reads-as-free bug again.
    #
    # Checked as asserting CONSTRUCTIONS rather than bare shape words. A first
    # version of this test failed on the disclosure's own conditional, "if yours
    # is one-way" -- the test was wrong, not the text. Bare "loop" is no good
    # either: permit prose names Rae Lakes Loop and the Tahoe Rim Trail loop.
    CLAIMS = ("route is an out-and-back", "route is a loop", "route is one-way",
              "this is an out-and-back", "this is a loop", "this is one-way",
              "route shape: ", "shape is out-and-back", "assumes an out-and-back")
    for name in ("Mount Whitney", "Mission Peak", "Mount Tallac", "Stanislaus Peak"):
        text = format_plan_summary(_plan(name))
        low = text.lower()
        for claim in CLAIMS:
            assert claim not in low, f"{name}: plan asserts a route shape: {claim!r}"
        # And the tempting default may appear only once, inside the sentence
        # listing the possibilities -- never a second time as an assertion.
        assert low.count("out-and-back") == 1, (
            f"{name}: 'out-and-back' appears {low.count('out-and-back')} times; the "
            "only licensed use is the list of shapes the dataset does not hold"
        )


def test_the_named_shapes_appear_only_as_possibilities():
    text = format_plan_summary(_plan("Mount Whitney"))
    assert "Route shape (out-and-back, loop, one-way) is not in this dataset" in text


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

def test_q5_is_still_no_model_because_the_schema_gap_is_untouched():
    # `declined` would mean "resolve the underlying uncertainty, or accept it".
    # `no-model` means "the schema has no place to put this yet", and that is
    # still the true statement: there is nowhere to record an exit. Saying so
    # out loud is honesty, not coverage, and must not move the number.
    import scorecard
    from scorecard import NO_MODEL, QUESTIONS, build
    built = build(TRIP)
    q5 = next(q for q in QUESTIONS if q.qid == "Q5")
    assert q5.text == "What do I need at the other end?"
    assert built["scores"]["Q5"][NO_MODEL] == built["n"], (
        "Q5 moved off no-model. If an exit is genuinely modelled now, update the "
        "proxy deliberately -- a disclosure must not be scored as an answer."
    )
