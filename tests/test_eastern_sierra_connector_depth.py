"""Source-bounded East Side connectors and pre-trip status remain explicit."""

from pathlib import Path

import pytest

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_convict_hiker_parking_connector_joins_reviewed_loop_node():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")
    relationships = indexed(records, "relationships", "relationship_id")

    profile = claims["claim-route-segment-convict-hiker-parking-connector"].value
    assert profile["distance_miles"] == pytest.approx(0.44399712)
    assert profile["surface"] == "unpaved_native"
    assert profile["end_coordinate"] == {
        "longitude": -118.85592573184694,
        "latitude": 37.594313472938715,
    }
    assert profile["joins_route_node_id"] == "route-node-convict-lake-loop-02"
    assert relationships[
        "relationship-convict-hiker-parking-connector-ends-at"
    ].object_id == "route-node-convict-lake-loop-02"
    assert relationships[
        "relationship-convict-hiker-parking-accesses-loop"
    ].object_id == "route-convict-lake-loop"


def test_horseshoe_point_and_dated_status_do_not_overstate_facilities():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")

    point = claims["claim-trailhead-horseshoe-lake-mammoth-map-point"].value
    assert point["source_feature_id"] == "USFS recreation area 20494"
    assert point["navigation_grade"] is False

    horseshoe = claims["claim-trailhead-horseshoe-lake-trip-status-20260925"].value
    assert horseshoe["lakes_basin_road"] == "open"
    assert horseshoe["restroom_current_status"] == "not_stated"
    assert horseshoe["potable_water_current_status"] == "not_stated"

    convict = claims["claim-trailhead-convict-lake-open-status-20260925"].value
    assert convict["trailhead_status"] == "open"
    assert convict["restroom_current_status"] == "not_stated"


def test_convict_parking_connector_publishes_as_a_mappable_route(generated_site):
    site_root, _ = generated_site
    geometry = (
        site_root / "geometry/routes/route-convict-hiker-parking-connector.geojson"
    )
    assert geometry.exists()
    payload = __import__("json").loads(geometry.read_text())
    assert len(payload["features"]) == 1
    assert payload["features"][0]["geometry"]["type"] == "LineString"
    assert payload["wayproof"]["distance_miles"] == pytest.approx(0.44399712)


def test_connector_batch_has_one_validated_changeset():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260925-eastern-sierra-connector-depth.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert {item.action for item in change.operations} == {
        ChangeAction.ADD, ChangeAction.REPLACE,
    }
    assert len(change.operations) == len({item.path for item in change.operations})
