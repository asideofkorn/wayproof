"""East Side access identities publish evidence-backed map points."""

import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical


ROOT = Path(__file__).resolve().parents[1]
MAPPED_ACCESS = {
    "access-upper-rock-creek-east-fork",
    "trailhead-convict-lake",
    "trailhead-hilton-lakes-rock-creek",
    "trailhead-horseshoe-lake-mammoth",
    "trailhead-lundy-canyon",
    "trailhead-mcgee-creek",
    "trailhead-mosquito-flat",
    "trailhead-north-lake-bishop",
    "trailhead-parker-lake",
    "trailhead-sabrina-basin",
    "trailhead-south-lake-bishop",
    "trailhead-tamarack-lakes-rock-creek",
    "trailhead-virginia-lakes",
    "trailhead-yost-fern",
}


def test_access_point_claims_preserve_source_authority_and_gaps():
    records = load_canonical(ROOT)
    claims = {item.claim_id: item for item in records.claims}
    gaps = {item.gap_id: item for item in records.gaps}

    for entity_id in MAPPED_ACCESS:
        value = claims[f"claim-{entity_id}-map-point"].value
        assert -90 <= value["latitude"] <= 90
        assert -180 <= value["longitude"] <= 180
        assert value["navigation_grade"] is False
        assert value["geometry_snapshot"]["feature_id"] == entity_id

    virginia = claims["claim-trailhead-virginia-lakes-map-point"].value
    assert virginia["provenance"] == "openstreetmap_named_trailhead_point"
    assert virginia["source_ids"] == [
        "source-osm-nominatim-eastern-sierra-trailheads-20260925"
    ]
    horseshoe_gap = gaps["gap-trailhead-horseshoe-lake-mammoth-map-point"]
    assert "exact pedestrian connector" in horseshoe_gap.question
    assert "about 55 meters" in horseshoe_gap.reason
    assert "gap-hilton-lakes-trailhead-route-connector" in gaps
    assert "gap-convict-lake-trailhead-loop-connector" in gaps


def test_east_side_access_points_publish_to_global_map(generated_site):
    site_root, _ = generated_site
    payload = json.loads((site_root / "map" / "features.geojson").read_text())
    access = {
        item["properties"]["entity_id"]: item
        for item in payload["features"]
        if item["properties"]["layer"] == "access"
    }
    facilities = {
        item["properties"]["entity_id"]: item
        for item in payload["features"]
        if item["properties"]["layer"] == "facilities"
    }

    assert MAPPED_ACCESS <= access.keys()
    assert all(access[entity_id]["geometry"]["type"] == "Point"
               for entity_id in MAPPED_ACCESS)
    assert access["trailhead-horseshoe-lake-mammoth"]["properties"]["kind"] == "trailhead"
    assert facilities["access-convict-hiker-parking"]["properties"]["kind"] == "parking"
    assert access["access-upper-rock-creek-east-fork"]["properties"]["kind"] == "trail_access"

    page = (site_root / "map" / "index.html").read_text()
    assert 'data-map-layer="access" checked' in page
