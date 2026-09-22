from datetime import date
from pathlib import Path

from wayproof.operational import OperationalState
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ActivityContext, PartyContext, TripIntent


ROOT = Path(__file__).resolve().parents[1]


def camp_plan(place: str, trip_date: date):
    return CanonicalReadService(ROOT).plan(
        TripIntent(
            (place,), trip_date,
            party=PartyContext(tuple(f"person-{n}" for n in range(10))),
            activities=ActivityContext(("camping",), {"overnight": True}),
        ),
        as_of_date=date(2026, 9, 22),
    )


def test_tilden_closures_are_planning_visible():
    wildcat = camp_plan("Wildcat View Group Camp", date(2026, 9, 30))
    gillespie = camp_plan("Gillespie Group Camp", date(2026, 12, 1))
    assert wildcat.operational.state is OperationalState.NEEDS_CURRENT_CHECK
    assert wildcat.state.value == "blocked"
    assert gillespie.operational.state is OperationalState.BLOCKED


def test_sibley_booking_product_and_access_are_queryable():
    reads = CanonicalReadService(ROOT)
    claim = reads.get("claim", "claim-sibley-backpack-camp-reserveamerica")
    assert claim.value["products"][0]["product_id"] == "1800"
    official = reads.get("claim", "claim-sibley-backpack-camp-official")
    assert official.value["hike_in_distance_miles"] == 0.2
