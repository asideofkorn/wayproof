"""What a trip costs, and the refusal to call an unpriced trip free.

From docs/user_stories/ohlone-traverse-2026-09.md, S2 -- the only finding in
that document that harms someone today:

    True answer: ... Actual total $97.
    Today: The permit block says "Fee: Free" ... the campsite fee does appear,
    but under Facilities, several lines below a headline saying the trip is free.
    Exposes: Fees live on the permit. When the permit is free and the cost is
    elsewhere, the headline is false.

Every figure was already in the dataset, on three different rows nobody was
adding up. So these tests are mostly about what is *said*, not what is stored.

Run with:  python -m pytest tests/test_trip_cost.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.access import load_approaches
from wayproof.camping import Campground, load_campgrounds, load_campsites
from wayproof.data_loader import load_peaks, load_trailheads
from wayproof.park_access import ParkAccess, load_park_access
from wayproof.permits import ClusterPermitInfo, load_permits
from wayproof.plan import (
    CHARGES,
    FREE,
    UNKNOWN,
    CostComponent,
    FacilitiesInfo,
    PlanResult,
    fee_status,
    format_costs,
    format_plan_summary,
    resolve_plan,
    trip_costs,
)
from wayproof.water import load_water_sources, load_water_source_log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)  # noqa: E731


def _inputs(list_filter=None):
    return dict(
        peaks=load_peaks(D("peaks.csv"), list_filter=list_filter,
                         collections_path=D("collections", "sps.csv")),
        trailheads=load_trailheads(D("trailheads.csv")),
        permits=load_permits(D("permits.csv"), D("release_policies.csv")),
        approaches=load_approaches(D("approaches.csv")),
        water_sources=load_water_sources(D("water_sources.csv")),
        water_source_log=load_water_source_log(D("water_source_log.csv")),
        campgrounds=load_campgrounds(D("campgrounds.csv")),
        campsites=load_campsites(D("campsites.csv")),
        park_access=list(load_park_access(D("park_access.csv")).values()),
    )


def _plan(name, trip=date(2027, 5, 1)):
    return resolve_plan([name], trip, **_inputs())


# -- classifying one fee field ----------------------------------------------

def test_a_blank_fee_is_unknown_not_free():
    # The whole bug in one assertion. Del Valle Family Campground carries no
    # fee_notes and charged $43; "absent" must never render as "free".
    assert fee_status("") == UNKNOWN
    assert fee_status("   ") == UNKNOWN
    assert fee_status(None) == UNKNOWN


def test_a_currency_amount_outranks_the_word_free():
    # cpma says the permit is free and then charges for parking in the same
    # field. A free permit is not a free trip.
    cpma = ("No fee for the wilderness permit itself. PARKING, June 1 - October 31, "
            "at USFS-operated lots: $5.00 per day at Carson Pass")
    assert fee_status(cpma) == CHARGES
    assert fee_status("$8/person ages 13+ (12 and under free)") == CHARGES


def test_the_real_fee_fields_all_classify():
    permits = load_permits(D("permits.csv"), D("release_policies.csv"))
    got = {g: fee_status(r.fee_notes) for g, r in permits.items()}
    assert got["none"] == FREE
    assert got["mokelumne_free"] == FREE          # "Free -- confirmed no quota or fee"
    assert got["toiyabe_free"] == FREE            # "Free (assumed, not independently confirmed)"
    assert got["cpma"] == CHARGES                 # free permit, paid parking
    assert got["whitney_zone"] == CHARGES
    assert UNKNOWN not in got.values(), "every permit row states a fee one way or the other"


# -- the story ---------------------------------------------------------------

def test_the_ohlone_end_no_longer_reports_a_paid_trip_as_free():
    # S2. Mission Peak sits at the western end of the traverse; the party paid
    # $46 for the backpack camp alone.
    result = _plan("Mission Peak")
    text = format_plan_summary(result)
    assert "THIS TRIP IS NOT FREE" in text
    kinds = {(c.kind, c.status) for c in result.costs}
    assert ("permit", FREE) in kinds, "the permit really is free; that part was never wrong"
    assert ("campground", CHARGES) in kinds, "and the campground really does charge"


def test_the_cost_headline_reads_before_the_free_permit_line():
    # Order is the fix. The figures were already on the page -- below a headline
    # saying the trip was free, which is how a reader stops reading.
    text = format_plan_summary(_plan("Mission Peak"))
    assert text.index("THIS TRIP IS NOT FREE") < text.index("Permit fee: Free")


def test_the_permit_fee_line_no_longer_claims_to_be_the_trip_cost():
    text = format_plan_summary(_plan("Mission Peak"))
    assert "Permit fee: Free" in text
    assert "\n  Fee: Free" not in text, "an unqualified 'Fee' reads as the trip's cost"


def test_an_unpriced_component_says_so_rather_than_disappearing():
    # Del Valle Family Campground has no fee_notes and took $43 of the $97.
    # Five more joined it when the Ohlone permit map named Del Valle's group
    # and horse camps -- every one of them unpriced, which is the point: a
    # trip through this park now has six components nobody has costed, and
    # each says so rather than vanishing from the roll-up.
    result = _plan("Rose Peak")
    unpriced = [c for c in result.costs if c.status == UNKNOWN]
    assert unpriced[0].label == "Del Valle Family Campground"
    assert len(unpriced) == 6
    assert {c.kind for c in unpriced} == {"campground"}
    text = format_plan_summary(result)
    assert "NO FEE ON FILE" in text
    assert "absent is not free" in text


def test_the_park_entrance_fee_is_counted_with_its_conditions():
    result = _plan("Rose Peak")
    park = next(c for c in result.costs if c.kind == "park_entrance")
    assert park.status == CHARGES
    assert park.detail == "$10"
    assert "weekends & holidays" in park.conditions
    assert "$10 (weekends & holidays" in format_plan_summary(result)


# -- not overclaiming --------------------------------------------------------

def test_a_genuinely_free_trip_still_reads_as_free():
    # Overcorrecting would be its own defect: a free permit with no facilities
    # is a free trip, and must not be hedged into uselessness.
    result = resolve_plan(["Stanislaus Peak"], date(2027, 7, 15), **_inputs())
    text = format_plan_summary(result)
    assert "No component on file charges a fee." in text
    assert "THIS TRIP IS NOT FREE" not in text


def test_a_candidate_permit_yields_a_candidate_price():
    # 153 of 247 SPS objectives resolve to "Permit (CANDIDATE ONLY)". A fee
    # priced off a permit that is only a candidate is only a candidate too.
    result = resolve_plan(["Picket Guard Peak"], date(2027, 7, 15), **_inputs())
    assert result.entry_conflicts, "this objective's entry point is unresolved"
    assert all(c.provisional for c in result.costs if c.kind == "permit")
    assert "[CANDIDATE" in format_plan_summary(result)


def test_a_resolved_entry_prices_without_the_candidate_hedge():
    result = resolve_plan(["Mount Whitney"], date(2027, 7, 15), **_inputs())
    assert not result.entry_conflicts
    assert not any(c.provisional for c in result.costs)
    assert "[CANDIDATE" not in format_plan_summary(result)


def test_the_total_is_never_computed():
    # These are prose from three operators in three shapes. A number derived
    # from them would be false precision of exactly the kind this project
    # refuses elsewhere.
    result = _plan("Rose Peak")
    text = format_plan_summary(result)
    assert "Not totalled" in text
    assert result.to_dict()["cost"]["totalled"] is False


def test_one_permit_appearing_twice_is_priced_once():
    # A trailhead default plus an approach caution emit the same rule twice.
    entry = ClusterPermitInfo(
        cluster_id=0, trailhead="Whitney Portal", wilderness_area="", agency="Inyo NF",
        permit_type="Inyo NF Wilderness Permit", fee_notes="$6/permit + $5/person",
        apply_url="", trip_date=date(2027, 7, 1), status="",
    )
    assert len(trip_costs([entry, entry], None)) == 1


# -- the machine surface -----------------------------------------------------

def test_an_agent_can_answer_is_this_free_without_parsing_prose():
    payload = json.loads(json.dumps(_plan("Mission Peak").to_dict()))
    cost = payload["cost"]
    assert cost["free"] is False and cost["charges"] is True
    # park_entrance joined the set when Mission Peak got a park_access row, and
    # the fee it carries is a community college's $4 rather than the District's
    # -- EBRPD charges nothing at either entrance. An agent that dropped the
    # component because the land manager is free would under-price the trip.
    assert {c["kind"] for c in cost["components"]} == {
        "permit", "campground", "park_entrance"}
    entrance = next(c for c in cost["components"] if c["kind"] == "park_entrance")
    assert "$4" in entrance["detail"]


def test_an_unpriced_component_is_not_free_on_the_machine_surface():
    cost = _plan("Rose Peak").to_dict()["cost"]
    assert cost["has_unpriced_component"] is True
    assert cost["free"] is False, "unknown must never resolve to free for an agent"


def test_an_unpriced_but_uncharged_trip_is_not_free_on_the_machine_surface():
    # The case that actually separates `free` from `not charges`: nothing on
    # file charges, but something has no price at all. An agent reading `free:
    # true` here would tell someone a trip costs nothing on the strength of a
    # blank cell.
    result = PlanResult(
        requested_names=["X"], objectives=[], not_found=[], trip_date=date(2027, 5, 1),
        trailhead=None, trailhead_ambiguous=False,
        costs=[CostComponent("permit", "Free permit", FREE, "Free"),
               CostComponent("campground", "Unpriced camp", UNKNOWN)],
    )
    cost = result.to_dict()["cost"]
    assert cost["charges"] is False
    assert cost["has_unpriced_component"] is True
    assert cost["free"] is False, "no charge on file is not the same as free"


def test_free_on_the_machine_surface_means_every_component_is_priced_and_free():
    cost = resolve_plan(["Stanislaus Peak"], date(2027, 7, 15),
                        **_inputs()).to_dict()["cost"]
    assert cost == {
        "free": True, "charges": False, "has_unpriced_component": False,
        "totalled": False,
        "components": [{"kind": "permit", "provisional": False, "status": "free",
                        "label": "Emigrant / Carson-Iceberg Wilderness Permit "
                                 "(free, self-issue)",
                        "detail": "Free"}],
    }


# -- rendering edge cases ----------------------------------------------------

def test_no_cost_section_when_there_is_nothing_to_price():
    assert format_costs([]) == []


def test_all_unknown_reads_as_unknown_not_as_free():
    costs = [CostComponent("campground", "A", UNKNOWN),
             CostComponent("campground", "B", UNKNOWN)]
    text = "\n".join(format_costs(costs))
    assert "COST UNKNOWN" in text
    assert "THIS TRIP IS NOT FREE" not in text


def test_the_facilities_shape_drives_the_components():
    fac = FacilitiesInfo(
        campgrounds=[Campground(name="Camp", park="P", fee_notes="$15/night")],
        park_access=ParkAccess(park="P", entrance_fee="", fee_conditions=""),
    )
    got = {c.kind: c.status for c in trip_costs([], fac)}
    assert got == {"campground": CHARGES, "park_entrance": UNKNOWN}
