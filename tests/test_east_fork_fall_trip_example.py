"""The East Fork trip example composes public facts with private runtime context."""

import json
from pathlib import Path

from wayproof.mcp_server import WayproofReadTools
from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "examples" / "trips" / "east-fork-fall-2026.json"


def test_trip_bundle_drives_existing_plan_and_comparison_services():
    payload = json.loads(BUNDLE.read_text())
    tools = WayproofReadTools(CanonicalReadService(ROOT))

    request = payload["plan_trip"]
    plan = tools.plan_trip(
        request["intent"],
        request["fulfillments"],
        as_of_date=request["as_of_date"],
    )
    comparison_request = payload["compare_hikes"]
    comparison = tools.compare_hikes(
        comparison_request["route_ids"],
        comparison_request["maximum_round_trip_miles"],
    )

    assert plan["resolution"]["state"] == "resolved"
    assert plan["resolution"]["objectives"][0]["entity_id"] == "campsite-east-fork-126"
    reservation = next(
        item for item in plan["readiness"]["evaluation"]["requirements"]
        if item["requirement"]["requirement_id"]
        == "requirement-east-fork-site-126-reservation"
    )
    assert reservation["status"] == "complete"
    assert comparison["maximum_round_trip_miles"] == 10
    assert {item["distance_fit"] for item in comparison["candidates"]} == {
        "fits", "unknown", "exceeds",
    }
    by_fit = {
        state: [item for item in comparison["candidates"] if item["distance_fit"] == state]
        for state in ("fits", "unknown", "exceeds")
    }
    assert {state: len(items) for state, items in by_fit.items()} == {
        "fits": 13,
        "unknown": 1,
        "exceeds": 3,
    }
    assert {
        item["route_id"] for item in comparison["candidates"]
    } >= {
        "route-upper-rock-creek-canyon",
        "route-fern-lake-june",
        "route-yost-lake",
        "route-sabrina-blue-lake",
        "route-piute-pass",
        "route-lamarck-lakes",
        "route-treasure-lakes",
    }
    assert next(
        item for item in comparison["candidates"]
        if item["route_id"] == "route-upper-rock-creek-canyon"
    )["knowledge_gap_ids"] == []
    assert "gap-lundy-canyon-sub-ten-turnaround" in next(
        item for item in comparison["candidates"]
        if item["route_id"] == "route-lundy-canyon-waterfall-beaver-dam"
    )["knowledge_gap_ids"]


def test_trip_bundle_keeps_private_and_unsourced_material_out_of_canonical():
    payload = json.loads(BUNDLE.read_text())
    canonical_text = "\n".join(
        path.read_text() for path in (ROOT / "canonical" / "v0").rglob("*.json")
    )

    assert payload["trip"]["ends_on"] == "2026-10-04"
    assert payload["deferred"]["pretrip_rechecks"] is True
    assert "Jenna" not in BUNDLE.read_text()
    assert "private-east-fork-booking" not in canonical_text
    assert "Drive in the morning via Tioga Pass" not in canonical_text
