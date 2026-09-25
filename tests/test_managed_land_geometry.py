"""Managed-land boundary ingestion, projection, and coverage invariants."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from wayproof.managed_land_geometry import (ManagedLandGeometryError,
                                            ManagedLandGeometryService)
from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]
MANAGED_KINDS = ("park", "national_park", "wilderness")


def test_every_published_managed_land_has_reviewed_geometry_or_explicit_gap():
    reads = CanonicalReadService(ROOT)
    for entity in reads.search_entities(kinds=MANAGED_KINDS):
        geometry = reads.managed_land_geometry(entity.entity_id)
        gaps = reads.knowledge_gaps_for(entity.entity_id)
        assert geometry is not None or any("boundary" in gap.question.casefold()
                                           for gap in gaps), entity.entity_id


def test_boundary_projection_preserves_source_feature_semantics():
    reads = CanonicalReadService(ROOT)
    del_valle = reads.managed_land_geometry("park-del-valle-regional-park")
    assert del_valle["geometry"]["type"] == "MultiPolygon"
    assert {item["status"] for item in del_valle["properties"]["source_features"]} == {
        "Parkland", "Landbank"
    }
    seki = reads.managed_land_geometry("park-sequoia-kings-canyon")
    assert {item["source_paid"] for item in seki["properties"]["source_features"]} == {
        "SEQU", "KICA"
    }
    ansel = reads.managed_land_geometry("wilderness-ansel-adams")
    assert {item["mang_name"] for item in ansel["properties"]["source_features"]} == {
        "USFS", "NPS"
    }


def test_boundary_snapshots_are_bounded_hashed_and_normalized():
    reads = CanonicalReadService(ROOT)
    claims = [
        claim for entity in reads.search_entities(kinds=MANAGED_KINDS)
        for claim in reads.claims_for(entity.entity_id)
        if isinstance(claim.value, dict)
        and claim.value.get("boundary_geometry_snapshot")
    ]
    paths = {}
    for claim in claims:
        reference = claim.value["boundary_geometry_snapshot"]
        paths.setdefault(reference["path"], reference["sha256"])
    assert len(claims) == 73
    assert len(paths) == 3
    for relative, expected_hash in paths.items():
        content = (ROOT / relative).read_bytes()
        payload = json.loads(content)
        assert hashlib.sha256(content).hexdigest() == expected_hash
        assert payload["wayproof"]["normalized_coordinate_reference_system"] == "EPSG:4326"
        assert payload["wayproof"]["navigation_grade"] is False
        assert all(feature["geometry"]["type"] in {"Polygon", "MultiPolygon"}
                   for feature in payload["features"])


def test_boundary_snapshot_hash_mismatch_fails_closed(tmp_path):
    target = tmp_path / "geometry/v0/snapshots/test.geojson"
    target.parent.mkdir(parents=True)
    target.write_text('{"type":"FeatureCollection","features":[]}')
    service = ManagedLandGeometryService(tmp_path, object())
    with pytest.raises(ManagedLandGeometryError, match="hash mismatch"):
        service._snapshot({"path": "geometry/v0/snapshots/test.geojson",
                           "sha256": "0" * 64})
