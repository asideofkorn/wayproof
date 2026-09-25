"""Reproducible route geometry projected from canonical traversal evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .traversal import TraversalLeg, TraversalState, resolve_traversal


class RouteGeometryError(ValueError):
    """Raised when promoted geometry evidence cannot be reproduced safely."""


def _close(left: list[float], right: list[float], tolerance: float = 0.00003) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(left[:2], right[:2]))


class RouteGeometryService:
    """Load reviewed snapshots and project them onto an evidenced traversal."""

    def __init__(self, root: Path, reads: Any):
        self._root = Path(root).resolve()
        self._reads = reads
        self._cache: dict[tuple[str, str], dict] = {}

    def _snapshot(self, reference: dict) -> dict:
        relative = reference.get("path", "")
        expected_hash = reference.get("sha256", "")
        if not relative or not expected_hash:
            raise RouteGeometryError("geometry snapshot path and sha256 are required")
        path = (self._root / relative).resolve()
        allowed = (self._root / "geometry" / "v0" / "snapshots").resolve()
        if not path.is_relative_to(allowed):
            raise RouteGeometryError("geometry snapshot must stay under geometry/v0/snapshots")
        try:
            content = path.read_bytes()
        except FileNotFoundError as exc:
            raise RouteGeometryError(f"geometry snapshot does not exist: {relative}") from exc
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != expected_hash:
            raise RouteGeometryError(
                f"geometry snapshot hash mismatch for {relative}: {actual_hash}"
            )
        key = (relative, actual_hash)
        if key not in self._cache:
            payload = json.loads(content)
            if payload.get("type") != "FeatureCollection":
                raise RouteGeometryError("geometry snapshot must be a GeoJSON FeatureCollection")
            features = payload.get("features")
            if not isinstance(features, list):
                raise RouteGeometryError("geometry snapshot features must be a list")
            self._cache[key] = payload
        return self._cache[key]

    def _route_endpoints(self, route_id: str) -> tuple[str, str]:
        relationships = tuple(
            item for item in self._reads.relationships_for(route_id)
            if item.subject_id == route_id
        )
        starts = tuple(item.object_id for item in relationships if item.predicate == "starts_at")
        ends = tuple(item.object_id for item in relationships if item.predicate == "ends_at")
        if len(starts) != 1 or len(ends) != 1:
            raise RouteGeometryError(
                "route geometry requires exactly one canonical start and end"
            )
        return starts[0], ends[0]

    def route(self, route_id: str, as_of: date) -> dict | None:
        """Return generated GeoJSON, or None when the route has no geometry snapshot."""
        route = self._reads.entity(route_id)
        member_segments = tuple(
            item.subject_id for item in self._reads.relationships_for(route_id)
            if item.object_id == route_id and item.predicate == "part_of"
        )
        has_geometry = any(
            isinstance(claim.value, dict) and claim.value.get("geometry_snapshot")
            for segment_id in member_segments
            for claim in self._reads.claims_for(segment_id)
        )
        if not has_geometry:
            return None
        sequence_claims = tuple(
            claim for claim in self._reads.claims_for(route_id)
            if claim.predicate == "ordered_route_geometry"
        )
        route_shape = None
        if sequence_claims:
            if len(sequence_claims) != 1:
                raise RouteGeometryError("route has multiple ordered geometry claims")
            sequence = sequence_claims[0].value
            segment_ids = tuple(sequence.get("segment_ids", ()))
            entry_id = sequence.get("start_node_id", "")
            route_shape = sequence.get("route_shape")
            if not segment_ids or not entry_id:
                raise RouteGeometryError(
                    "ordered route geometry requires segment_ids and start_node_id"
                )
            if not set(segment_ids).issubset(member_segments):
                raise RouteGeometryError(
                    "ordered route geometry contains a segment outside the route"
                )
            legs = []
            current_node = entry_id
            for index, segment_id in enumerate(segment_ids, start=1):
                relationships = tuple(
                    item for item in self._reads.relationships_for(segment_id)
                    if item.subject_id == segment_id
                )
                starts = tuple(
                    item.object_id for item in relationships if item.predicate == "starts_at"
                )
                ends = tuple(
                    item.object_id for item in relationships if item.predicate == "ends_at"
                )
                if len(starts) != 1 or len(ends) != 1:
                    raise RouteGeometryError(
                        f"ordered segment {segment_id} requires one start and one end"
                    )
                if current_node == starts[0]:
                    next_node = ends[0]
                elif current_node == ends[0]:
                    next_node = starts[0]
                else:
                    raise RouteGeometryError(
                        f"ordered segment {segment_id} does not connect to {current_node}"
                    )
                topology_claims = tuple(
                    claim for claim in self._reads.claims_for(segment_id)
                    if isinstance(claim.value, dict)
                    and claim.value.get("geometry_snapshot")
                )
                if len(topology_claims) != 1:
                    raise RouteGeometryError(
                        f"ordered segment {segment_id} requires one geometry claim"
                    )
                value = topology_claims[0].value
                legs.append(TraversalLeg(
                    index,
                    segment_id,
                    current_node,
                    next_node,
                    value.get("distance_miles"),
                    value.get(
                        "distance_status",
                        "known" if value.get("distance_miles") is not None else "unknown",
                    ),
                ))
                current_node = next_node
            exit_id = current_node
            if route_shape == "loop" and exit_id != entry_id:
                raise RouteGeometryError("ordered loop geometry does not return to its start")
            geometry_legs = tuple(legs)
            total_known_distance = round(
                sum(item.distance_miles or 0.0 for item in geometry_legs), 10
            )
            distance_complete = all(
                item.distance_miles is not None for item in geometry_legs
            )
        else:
            entry_id, exit_id = self._route_endpoints(route_id)
            traversal = resolve_traversal(
                self._reads, route, self._reads.entity(entry_id),
                self._reads.entity(exit_id), as_of,
            )
            if traversal.state is not TraversalState.COMPLETE:
                raise RouteGeometryError(
                    f"route traversal is {traversal.state.value}; geometry cannot be projected"
                )
            geometry_legs = traversal.legs
            total_known_distance = traversal.total_known_distance_miles
            distance_complete = traversal.distance_complete

        output = []
        for leg in geometry_legs:
            claims = tuple(
                item for item in self._reads.claims_for(leg.segment_id)
                if isinstance(item.value, dict) and item.value.get("geometry_snapshot")
            )
            if not claims:
                return None
            if len(claims) != 1:
                raise RouteGeometryError(
                    f"segment {leg.segment_id} has multiple geometry snapshot claims"
                )
            claim = claims[0]
            reference = claim.value["geometry_snapshot"]
            snapshot = self._snapshot(reference)
            feature_id = reference.get("feature_id")
            matches = tuple(
                item for item in snapshot["features"]
                if item.get("properties", {}).get("feature_id") == feature_id
            )
            if len(matches) != 1:
                raise RouteGeometryError(
                    f"snapshot must contain exactly one feature {feature_id}; found {len(matches)}"
                )
            feature = matches[0]
            geometry = feature.get("geometry", {})
            coordinates = geometry.get("coordinates")
            if geometry.get("type") != "LineString" or not coordinates:
                raise RouteGeometryError("route segment geometry must be a nonempty LineString")

            start_value = claim.value.get("start_coordinate", {})
            end_value = claim.value.get("end_coordinate", {})
            claim_start = [start_value.get("longitude"), start_value.get("latitude")]
            claim_end = [end_value.get("longitude"), end_value.get("latitude")]
            if None in claim_start or None in claim_end:
                raise RouteGeometryError("geometry claim requires source-backed endpoint coordinates")
            if _close(coordinates[0], claim_start) and _close(coordinates[-1], claim_end):
                canonical_coordinates = coordinates
            elif _close(coordinates[0], claim_end) and _close(coordinates[-1], claim_start):
                canonical_coordinates = list(reversed(coordinates))
            else:
                raise RouteGeometryError(
                    f"feature {feature_id} endpoints do not match claim {claim.claim_id}"
                )

            relationships = tuple(
                item for item in self._reads.relationships_for(leg.segment_id)
                if item.subject_id == leg.segment_id
            )
            canonical_start = next(
                item.object_id for item in relationships if item.predicate == "starts_at"
            )
            if leg.start_node_id != canonical_start:
                canonical_coordinates = list(reversed(canonical_coordinates))
            output.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": canonical_coordinates},
                "properties": {
                    "route_id": route_id,
                    "segment_id": leg.segment_id,
                    "sequence": leg.sequence,
                    "start_node_id": leg.start_node_id,
                    "end_node_id": leg.end_node_id,
                    "distance_miles": leg.distance_miles,
                    "distance_status": leg.distance_status,
                    "route_role": claim.value.get("route_role"),
                    "source_feature_id": feature_id,
                    "source_geometry_accuracy": feature.get("properties", {}).get(
                        "xy_accuracy"
                    ),
                },
            })

        for left, right in zip(output, output[1:]):
            if not _close(
                left["geometry"]["coordinates"][-1],
                right["geometry"]["coordinates"][0],
            ):
                raise RouteGeometryError("generated route geometry is disconnected")
        if route_shape == "loop" and output and not _close(
            output[-1]["geometry"]["coordinates"][-1],
            output[0]["geometry"]["coordinates"][0],
        ):
            raise RouteGeometryError(
                "generated loop geometry does not return to its start"
            )
        result = {
            "type": "FeatureCollection",
            "wayproof": {
                "route_id": route_id,
                "entry_id": entry_id,
                "exit_id": exit_id,
                "distance_miles": total_known_distance,
                "distance_complete": distance_complete,
                "geometry_status": "reviewed_source_snapshot",
                "navigation_grade": False,
            },
            "features": output,
        }
        if route_shape:
            result["wayproof"]["route_shape"] = route_shape
        return result
