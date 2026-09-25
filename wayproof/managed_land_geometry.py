"""Reviewed boundary geometry for parks, wildernesses, and managed lands."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ManagedLandGeometryError(ValueError):
    """Raised when promoted managed-land geometry cannot be reproduced safely."""


class ManagedLandGeometryService:
    """Load immutable source snapshots referenced by canonical boundary claims."""

    def __init__(self, root: Path, reads: Any):
        self._root = Path(root).resolve()
        self._reads = reads
        self._cache: dict[tuple[str, str], dict] = {}

    def _snapshot(self, reference: dict) -> dict:
        relative = reference.get("path", "")
        expected_hash = reference.get("sha256", "")
        if not relative or not expected_hash:
            raise ManagedLandGeometryError("boundary snapshot path and sha256 are required")
        path = (self._root / relative).resolve()
        allowed = (self._root / "geometry" / "v0" / "snapshots").resolve()
        if not path.is_relative_to(allowed):
            raise ManagedLandGeometryError(
                "boundary snapshot must stay under geometry/v0/snapshots"
            )
        try:
            content = path.read_bytes()
        except FileNotFoundError as exc:
            raise ManagedLandGeometryError(
                f"boundary snapshot does not exist: {relative}"
            ) from exc
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != expected_hash:
            raise ManagedLandGeometryError(
                f"boundary snapshot hash mismatch for {relative}: {actual_hash}"
            )
        key = (relative, actual_hash)
        if key not in self._cache:
            payload = json.loads(content)
            if payload.get("type") != "FeatureCollection":
                raise ManagedLandGeometryError(
                    "boundary snapshot must be a GeoJSON FeatureCollection"
                )
            metadata = payload.get("wayproof", {})
            if metadata.get("normalized_coordinate_reference_system") != "EPSG:4326":
                raise ManagedLandGeometryError("boundary snapshot must use EPSG:4326")
            if metadata.get("classification") not in {
                "public_domain", "open_license", "project_created"
            }:
                raise ManagedLandGeometryError(
                    "boundary snapshot must declare an allowed classification"
                )
            if not isinstance(payload.get("features"), list):
                raise ManagedLandGeometryError("boundary snapshot features must be a list")
            self._cache[key] = payload
        return self._cache[key]

    def boundary(self, entity_id: str) -> dict | None:
        """Return one display geometry assembled from explicitly selected features."""
        claims = tuple(
            claim for claim in self._reads.claims_for(entity_id)
            if isinstance(claim.value, dict)
            and claim.value.get("boundary_geometry_snapshot")
        )
        if not claims:
            return None
        if len(claims) != 1:
            raise ManagedLandGeometryError(
                f"managed land {entity_id} has multiple boundary snapshot claims"
            )
        claim = claims[0]
        reference = claim.value["boundary_geometry_snapshot"]
        snapshot = self._snapshot(reference)
        feature_ids = tuple(reference.get("feature_ids", ()))
        if not feature_ids or len(feature_ids) != len(set(feature_ids)):
            raise ManagedLandGeometryError(
                "boundary claim requires unique source feature identifiers"
            )
        indexed = {
            item.get("properties", {}).get("feature_id"): item
            for item in snapshot["features"]
        }
        polygons = []
        source_properties = []
        for feature_id in feature_ids:
            feature = indexed.get(feature_id)
            if feature is None:
                raise ManagedLandGeometryError(
                    f"boundary snapshot does not contain feature {feature_id}"
                )
            geometry = feature.get("geometry", {})
            if geometry.get("type") == "Polygon":
                selected = [geometry.get("coordinates")]
            elif geometry.get("type") == "MultiPolygon":
                selected = geometry.get("coordinates") or []
            else:
                raise ManagedLandGeometryError(
                    f"boundary feature {feature_id} must be Polygon or MultiPolygon"
                )
            if not selected or any(not item for item in selected):
                raise ManagedLandGeometryError(
                    f"boundary feature {feature_id} has empty coordinates"
                )
            polygons.extend(selected)
            source_properties.append(feature.get("properties", {}))
        geometry = (
            {"type": "Polygon", "coordinates": polygons[0]}
            if len(polygons) == 1 else
            {"type": "MultiPolygon", "coordinates": polygons}
        )
        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "entity_id": entity_id,
                "claim_id": claim.claim_id,
                "geometry_status": "reviewed_source_snapshot",
                "navigation_grade": False,
                "source_features": source_properties,
            },
        }
