"""Pilot coverage for reproducible, evidence-backed route geometry."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from wayproof.read_service import CanonicalReadService
from wayproof.route_geometry import RouteGeometryError, RouteGeometryService


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path("geometry/v0/snapshots/nps-lavo-cinder-cone-approach-20260923.geojson")
SNAPSHOT_HASH = "50d218a1cec59453ce4e12aa84a9a0f9768914c10faa715e307b32db764c4b6a"


def test_cinder_cone_geometry_projects_canonical_segment_order_and_continuity():
    geometry = CanonicalReadService(ROOT).route_geometry(
        "route-cinder-cone-trail", date(2026, 9, 23)
    )

    assert geometry is not None
    assert geometry["wayproof"] == {
        "route_id": "route-cinder-cone-trail",
        "entry_id": "trailhead-cinder-cone-butte-lake",
        "exit_id": "peak-cinder-cone",
        "distance_miles": 1.58296735,
        "distance_complete": True,
        "geometry_status": "reviewed_source_snapshot",
        "navigation_grade": False,
    }
    assert [item["properties"]["segment_id"] for item in geometry["features"]] == [
        "route-segment-cinder-trailhead-nobles-junction",
        "route-segment-cinder-nobles-junction-base-fork",
        "route-segment-cinder-base-fork-summit",
    ]
    assert sum(len(item["geometry"]["coordinates"])
               for item in geometry["features"]) == 143
    for left, right in zip(geometry["features"], geometry["features"][1:]):
        assert left["geometry"]["coordinates"][-1] == right["geometry"]["coordinates"][0]


def test_snapshot_is_bounded_to_reviewed_features_and_matches_promoted_hash():
    content = (ROOT / SNAPSHOT).read_bytes()
    snapshot = json.loads(content)

    assert hashlib.sha256(content).hexdigest() == SNAPSHOT_HASH
    assert snapshot["type"] == "FeatureCollection"
    assert snapshot["wayproof"]["source_id"] == "source-nps-public-trails-feature-service"
    assert snapshot["wayproof"]["normalized_coordinate_reference_system"] == "EPSG:4326"
    assert snapshot["wayproof"]["classification"] == "public_domain"
    assert len(snapshot["features"]) == 3


def test_snapshot_hash_mismatch_fails_closed(tmp_path):
    target = tmp_path / SNAPSHOT
    target.parent.mkdir(parents=True)
    target.write_text('{"type":"FeatureCollection","features":[]}')
    service = RouteGeometryService(tmp_path, object())

    with pytest.raises(RouteGeometryError, match="hash mismatch"):
        service._snapshot({"path": str(SNAPSHOT), "sha256": SNAPSHOT_HASH})


def test_route_without_promoted_geometry_remains_unmapped():
    reads = CanonicalReadService(ROOT)
    assert reads.route_geometry("route-brokeoff-mountain-trail", date(2026, 9, 23)) is None
