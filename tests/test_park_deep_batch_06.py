from datetime import date
from pathlib import Path

from wayproof.operational import OperationalState
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ActivityContext, PartyContext, TripIntent

ROOT = Path(__file__).resolve().parents[1]

def plan(place, when):
    return CanonicalReadService(ROOT).plan(TripIntent((place,), when, party=PartyContext(("one",)), activities=ActivityContext(("backpacking",), {"overnight": True})), as_of_date=date(2026, 9, 22))

def test_seasonal_backpack_closures_block_winter_plans():
    assert plan("Stewartville Backpack Camp", date(2026, 12, 1)).operational.state is OperationalState.BLOCKED
    assert plan("Morgan Territory Backpack Camp", date(2026, 12, 1)).operational.state is OperationalState.BLOCKED

def test_round_valley_product_and_dog_rule_are_queryable():
    reads = CanonicalReadService(ROOT)
    assert reads.get("claim", "claim-round-valley-backpack-reserveamerica").value["products"][0]["product_id"] == "1165"
    assert reads.get("claim", "claim-round-valley-backpack-official").value["dogs_allowed"] is False
