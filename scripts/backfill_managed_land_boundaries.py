#!/usr/bin/env python3
"""Prepare the initial managed-land boundary snapshot and canonical ChangeSet.

This is an ingestion tool, not a site-build dependency. It queries reviewed
government services, writes immutable normalized snapshots, and then uses the
ordinary domain write boundary to prepare canonical claims.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wayproof.canonical_storage import load_canonical, write_candidate
from wayproof.schema import (CanonicalRecords, ChangeAction, ChangeOperation,
                             ChangeSet, Claim, Evidence, Observation, Source)
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / "geometry" / "v0" / "snapshots"
CHANGE_ID = "change-managed-land-boundary-backfill-20260924"
RETRIEVED_AT = datetime(2026, 9, 24, 22, 0, tzinfo=timezone.utc)

EBRPD_URL = (
    "https://services2.arcgis.com/jeEP9c9zZoQQwtck/arcgis/rest/services/"
    "EBRPD_Parks/FeatureServer/0"
)
PADUS_FEE_URL = (
    "https://edits.nationalmap.gov/arcgis/rest/services/"
    "PAD-US/PAD_US/MapServer/0"
)
PADUS_MANAGEMENT_URL = (
    "https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
    "Management_Areas/FeatureServer/0"
)

EBRPD_ALIASES = {
    "park-browns-island": "Browns Island Regional Preserve",
    "park-dublin-hills-regional-open-space-preserve": "Dublin Hills Regional Park",
    "park-five-canyons-open-space": "Five Canyons Open Space Regional Preserve",
    "park-sibley-volcanic-regional-preserve": "Robert Sibley Volcanic Regional Preserve",
    "park-thurgood-marshall-regional-park-home-port-chicago-50":
        "Thurgood Marshall Regional Park",
    "park-tilden-nature-area": "Charles Lee Tilden Regional Park Nature Area",
}

NATIONAL_IDS = {
    "park-yosemite-national-park": (3484,),
    "park-lassen-volcanic-national-park": (3462,),
    "park-sequoia-national-park": (3473,),
    "park-sequoia-kings-canyon": (3473, 3459),
}

WILDERNESS_IDS = {
    "wilderness-ansel-adams": (146703, 414735),
    "wilderness-hoover": (247338, 341354),
    "wilderness-john-muir": (4201, 201153),
    "land-lassen-volcanic-wilderness": (118515,),
    "land-yosemite-wilderness": (221430,),
}


def query(url: str, **parameters) -> dict:
    parameters.update({
        "outSR": 4326,
        "returnGeometry": "true",
        "geometryPrecision": 5,
        "f": "geojson",
    })
    request = url + "/query?" + urllib.parse.urlencode(parameters)
    with urllib.request.urlopen(request) as response:
        payload = json.load(response)
    if payload.get("type") != "FeatureCollection":
        raise RuntimeError(f"unexpected ArcGIS response from {url}: {payload}")
    return payload


def _point_segment_distance(point: list[float], start: list[float],
                            end: list[float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    factor = max(0.0, min(1.0, ((point[0] - start[0]) * dx
                               + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)))
    projected = (start[0] + factor * dx, start[1] + factor * dy)
    return math.hypot(point[0] - projected[0], point[1] - projected[1])


def _simplify_line(points: list[list[float]], tolerance: float) -> list[list[float]]:
    if len(points) <= 2:
        return points
    start, end = points[0], points[-1]
    distances = [_point_segment_distance(point, start, end) for point in points[1:-1]]
    if not distances or max(distances) <= tolerance:
        return [start, end]
    index = distances.index(max(distances)) + 1
    return (_simplify_line(points[:index + 1], tolerance)[:-1]
            + _simplify_line(points[index:], tolerance))


def _simplify_ring(ring: list[list[float]], tolerance: float) -> list[list[float]]:
    if len(ring) < 5:
        return ring
    # Split a closed ring at its most distant vertex so Douglas-Peucker does
    # not compare the identical closing endpoints.
    anchor = ring[0]
    split = max(range(1, len(ring) - 1),
                key=lambda index: math.hypot(ring[index][0] - anchor[0],
                                             ring[index][1] - anchor[1]))
    first = _simplify_line(ring[:split + 1], tolerance)
    second = _simplify_line(ring[split:-1] + [anchor], tolerance)
    simplified = first[:-1] + second
    return simplified if len(simplified) >= 4 else ring


def _simplify_geometry(geometry: dict, tolerance: float) -> dict:
    polygons = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
                else geometry["coordinates"])
    simplified = [[_simplify_ring(ring, tolerance) for ring in polygon]
                  for polygon in polygons]
    return ({"type": "Polygon", "coordinates": simplified[0]}
            if geometry["type"] == "Polygon" else
            {"type": "MultiPolygon", "coordinates": simplified})


def normalized_snapshot(source_id: str, service_url: str, classification: str,
                        selection: str, features: list[dict], prefix: str,
                        property_names: tuple[str, ...],
                        simplification_tolerance: float = 0.00003) -> dict:
    normalized = []
    for feature in features:
        properties = feature["properties"]
        object_id = properties["OBJECTID"]
        geometry = feature.get("geometry")
        if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise RuntimeError(f"missing polygon geometry for {prefix}:{object_id}")
        kept = {name.lower(): properties.get(name) for name in property_names}
        kept.update({"feature_id": f"{prefix}:{object_id}",
                     "source_object_id": object_id})
        normalized.append({"type": "Feature",
                           "geometry": _simplify_geometry(
                               geometry, simplification_tolerance),
                           "properties": kept})
    normalized.sort(key=lambda item: item["properties"]["feature_id"])
    return {
        "type": "FeatureCollection",
        "wayproof": {
            "source_id": source_id,
            "source_service": service_url,
            "selection_context": selection,
            "retrieved_at": RETRIEVED_AT.isoformat(),
            "normalized_coordinate_reference_system": "EPSG:4326",
            "coordinate_precision_decimal_degrees": 5,
            "display_simplification_tolerance_decimal_degrees":
                simplification_tolerance,
            "classification": classification,
            "navigation_grade": False,
        },
        "features": normalized,
    }


def write_snapshot(name: str, payload: dict) -> tuple[str, str]:
    relative = f"geometry/v0/snapshots/{name}"
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2, sort_keys=True,
                         ensure_ascii=False) + "\n"
    path.write_text(content, encoding="utf-8")
    return relative, hashlib.sha256(content.encode()).hexdigest()


def operation(record_type: str, record_id: str,
              evidence_refs: tuple[str, ...] = ()) -> ChangeOperation:
    collections = {
        "source": "sources", "observation": "observations",
        "evidence": "evidence", "claim": "claims",
    }
    return ChangeOperation(
        ChangeAction.ADD, record_type, record_id,
        f"canonical/v0/{collections[record_type]}/{record_id}.json",
        "Backfill reviewed managed-land boundary geometry",
        evidence_refs=evidence_refs,
    )


def main() -> None:
    base = load_canonical(ROOT)
    entities = {item.entity_id: item for item in base.entities}

    ebrpd_entities = sorted(
        (item for item in base.entities if item.kind == "park"),
        key=lambda item: item.entity_id,
    )
    official_names = {
        item.entity_id: EBRPD_ALIASES.get(item.entity_id, item.name)
        for item in ebrpd_entities
    }
    ebrpd = query(
        EBRPD_URL,
        where="OFFICIAL_NAME IS NOT NULL",
        outFields="OBJECTID,NAME,STATUS,PARK_UNIT,OFFICIAL_NAME,GIS_ACRES",
    )
    ebrpd_by_name: dict[str, list[dict]] = {}
    for feature in ebrpd["features"]:
        ebrpd_by_name.setdefault(feature["properties"]["OFFICIAL_NAME"], []).append(feature)
    missing = sorted(set(official_names.values()) - set(ebrpd_by_name))
    if missing:
        raise RuntimeError(f"unmatched EBRPD park names: {missing}")
    ebrpd_snapshot = normalized_snapshot(
        "source-ebrpd-managed-land-boundaries-20260924", EBRPD_URL,
        "open_license", "Canonical EBRPD park names matched to OFFICIAL_NAME",
        [feature for name in sorted(set(official_names.values()))
         for feature in ebrpd_by_name[name]], "ebrpd",
        ("OBJECTID", "NAME", "STATUS", "PARK_UNIT", "OFFICIAL_NAME", "GIS_ACRES"),
    )
    ebrpd_path, ebrpd_hash = write_snapshot(
        "ebrpd-managed-land-boundaries-20260924.geojson", ebrpd_snapshot
    )

    national_object_ids = sorted({item for ids in NATIONAL_IDS.values() for item in ids})
    national = query(
        PADUS_FEE_URL,
        objectIds=",".join(map(str, national_object_ids)),
        outFields=("OBJECTID,Unit_Nm,Loc_Nm,Des_Tp,Mang_Name,GIS_Src,Src_Date,"
                   "Source_PAID,GIS_Acres"),
        maxAllowableOffset=0.0001,
    )
    national_snapshot = normalized_snapshot(
        "source-usgs-padus-fee-manager-boundaries-20260924", PADUS_FEE_URL,
        "public_domain", "Selected NPS fee-manager records by PAD-US OBJECTID",
        national["features"], "padus-fee",
        ("OBJECTID", "Unit_Nm", "Loc_Nm", "Des_Tp", "Mang_Name", "GIS_Src",
         "Src_Date", "Source_PAID", "GIS_Acres"),
    )
    national_path, national_hash = write_snapshot(
        "usgs-padus-national-park-fee-boundaries-20260924.geojson",
        national_snapshot,
    )

    wilderness_object_ids = sorted({item for ids in WILDERNESS_IDS.values() for item in ids})
    wilderness = query(
        PADUS_MANAGEMENT_URL,
        objectIds=",".join(map(str, wilderness_object_ids)),
        outFields="OBJECTID,Unit_Nm,Loc_Nm,Des_Tp,Des_Tp_Desc,Mang_Name,GIS_AcreD",
    )
    wilderness_snapshot = normalized_snapshot(
        "source-usgs-padus-management-boundaries-20260924", PADUS_MANAGEMENT_URL,
        "public_domain", "Selected designated wilderness records by PAD-US OBJECTID",
        wilderness["features"], "padus-management",
        ("OBJECTID", "Unit_Nm", "Loc_Nm", "Des_Tp", "Des_Tp_Desc", "Mang_Name",
         "GIS_AcreD"),
    )
    wilderness_path, wilderness_hash = write_snapshot(
        "usgs-padus-wilderness-boundaries-20260924.geojson", wilderness_snapshot
    )

    records = CanonicalRecords()
    sources = (
        ("source-ebrpd-managed-land-boundaries-20260924", EBRPD_URL,
         "East Bay Regional Park District"),
        ("source-usgs-padus-fee-manager-boundaries-20260924", PADUS_FEE_URL,
         "U.S. Geological Survey"),
        ("source-usgs-padus-management-boundaries-20260924", PADUS_MANAGEMENT_URL,
         "U.S. Geological Survey"),
    )
    for source_id, locator, publisher in sources:
        records.sources.append(Source(source_id, locator, publisher))

    datasets = {
        "ebrpd": {
            "source_id": sources[0][0], "path": ebrpd_path, "hash": ebrpd_hash,
            "content": ("EBRPD's open-data layer reports the selected current managed-land "
                        "polygons; parkland and landbank status remain separate."),
        },
        "national": {
            "source_id": sources[1][0], "path": national_path, "hash": national_hash,
            "content": ("USGS PAD-US reports the selected NPS fee-manager polygons and "
                        "identifies their NPS source records."),
        },
        "wilderness": {
            "source_id": sources[2][0], "path": wilderness_path,
            "hash": wilderness_hash,
            "content": ("USGS PAD-US Management Areas reports the selected designated "
                        "wilderness polygons by managing agency."),
        },
    }
    for key, dataset in datasets.items():
        observation_id = f"observation-managed-land-boundaries-{key}-20260924"
        records.observations.append(Observation(
            observation_id, dataset["source_id"], dataset["content"],
            retrieved_at=RETRIEVED_AT, artifact_refs=(dataset["path"],),
        ))
        dataset["observation_id"] = observation_id

    claim_specs: list[tuple[str, str, tuple[str, ...], str]] = []
    for entity_id, official_name in official_names.items():
        ids = tuple(
            f"ebrpd:{feature['properties']['OBJECTID']}"
            for feature in sorted(ebrpd_by_name[official_name],
                                  key=lambda item: item["properties"]["OBJECTID"])
        )
        claim_specs.append((entity_id, "ebrpd", ids, "managed_land_status_polygons"))
    for entity_id, ids in NATIONAL_IDS.items():
        claim_specs.append((entity_id, "national",
                            tuple(f"padus-fee:{item}" for item in ids),
                            "nps_fee_manager_boundary"))
    for entity_id, ids in WILDERNESS_IDS.items():
        claim_specs.append((entity_id, "wilderness",
                            tuple(f"padus-management:{item}" for item in ids),
                            "designated_wilderness_management_area"))

    for entity_id, dataset_key, feature_ids, boundary_type in sorted(claim_specs):
        if entity_id not in entities:
            raise RuntimeError(f"unknown canonical managed land: {entity_id}")
        claim_id = f"claim-{entity_id}-boundary-geometry-20260924"
        evidence_id = f"evidence-{entity_id}-boundary-geometry-20260924"
        dataset = datasets[dataset_key]
        records.evidence.append(Evidence(
            evidence_id, dataset["observation_id"], claim_id,
            notes="Supports the selected source polygons and their retained boundary semantics.",
        ))
        records.claims.append(Claim(
            claim_id, entity_id, "managed_land_boundary_geometry",
            {
                "boundary_type": boundary_type,
                "boundary_geometry_snapshot": {
                    "path": dataset["path"], "sha256": dataset["hash"],
                    "feature_ids": list(feature_ids),
                },
                "coordinate_reference_system": "EPSG:4326",
                "coordinate_precision_decimal_degrees": 5,
                "navigation_grade": False,
            },
            (evidence_id,),
        ))

    operations = []
    for item in records.sources:
        operations.append(operation("source", item.source_id))
    for item in records.observations:
        operations.append(operation("observation", item.observation_id))
    for item in records.evidence:
        operations.append(operation("evidence", item.evidence_id))
    for item in records.claims:
        operations.append(operation("claim", item.claim_id, item.evidence_ids))
    change = ChangeSet(
        CHANGE_ID, records,
        summary=("Backfill reviewed boundary geometry for every published park, national "
                 "park, and wilderness entity"),
        operations=tuple(operations),
    )
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(base))
    writes.propose(change, "boundary-ingestion-agent")
    errors = writes.validate(CHANGE_ID, "boundary-validator")
    if errors:
        raise RuntimeError("boundary ChangeSet validation failed:\n" + "\n".join(errors))
    prepared = writes.prepare(CHANGE_ID, "candidate-builder")
    write_candidate(ROOT, prepared, writes.get(CHANGE_ID))
    print(f"prepared {len(records.claims)} boundary claims in {CHANGE_ID}")


if __name__ == "__main__":
    main()
