"""Static website adapter for canonical read-service results.

This module renders consumer pages, but owns no planning or evidence logic. All
knowledge discovery, provenance, gaps, relationships, and history enter through
``CanonicalReadService`` so another adapter can consume the same contract.
"""

from __future__ import annotations

import html
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from .read_service import CanonicalReadService
from .schema import PlanningContext, TripObjective, TripStage


DEL_VALLE_ID = "park-del-valle-regional-park"
DEL_VALLE_PATH = "/destinations/del-valle/"
OHLONE_ID = "trail-ohlone-wilderness"
OHLONE_PATH = "/trails/ohlone-wilderness/"
ROUTE_MAP_ASSET_VERSION = "20260925-1"
EXPLORE_MAP_ASSET_VERSION = "20260925-2"
PRIMARY_NAV = (
    ("Home", "/"),
    ("Map", "/map/"),
    ("Parks", "/parks/"),
    ("Trails", "/trails/"),
    ("Camping", "/camping/"),
    ("Peaks", "/peaks/"),
    ("How it works", "/how-it-works/"),
    ("Changes", "/changes/"),
    ("Search", "/search/"),
)
DIRECTORIES = {
    "parks": {
        "title": "Parks and preserves",
        "description": "Browse published parks, preserves, recreation areas, wildernesses, and national parks.",
        "kinds": ("park", "national_park", "wilderness"),
    },
    "trails": {
        "title": "Trails and routes",
        "description": "Browse human-level trails and routes. Detailed segments remain inside their parent route records.",
        "kinds": ("trail", "route"),
    },
    "camping": {
        "title": "Camping",
        "description": "Browse campgrounds, developed sites, group camps, equestrian camps, cabins, and backcountry camps.",
        "kinds": ("campground", "campground_collection", "campsite",
                  "family_campsite", "group_campsite",
                  "cabin_campsite", "backcountry_camp", "equestrian_campsite",
                  "equestrian_campsite_area", "equestrian_group_campsite"),
    },
    "peaks": {
        "title": "Peaks",
        "description": "Browse published summits and peaks.",
        "kinds": ("peak",),
    },
}
DEL_VALLE_SCOPES = (
    "scope-del-valle-park",
    "scope-lake-del-valle",
    "scope-del-valle-family-campground",
    "scope-del-valle-east-beach",
    "scope-del-valle-west-beach",
)

# Presentation choices, not a second knowledge model: ids and predicates select
# canonical records for the questions a Del Valle visitor asks first.
DEL_VALLE_SECTIONS = (
    ("Getting there and entering", (
        (DEL_VALLE_ID, ("street_address", "seasonal_gate_hours", "published_entry_fees",
                       "operating_status", "trail_condition")),
        ("entrance-del-valle-main", ("accesses",)),
    )),
    ("Camping", (
        (DEL_VALLE_ID, ("group_camping_reservation", "developed_group_camping_capacity",
                       "published_seasonal_closures")),
        ("campground-del-valle-family", (
            "reservation_window", "site_inventory", "people_per_family_site",
            "vehicles_per_family_site", "shared_facilities", "gate_hours",
            "quiet_hours", "fire_rules", "dog_rules", "generators_allowed",
            "connectivity_warning",
        )),
    )),
    ("Swimming, boating, and lake conditions", (
        ("beach-del-valle-east", ("water_quality_advisory",)),
        ("beach-del-valle-west", ("water_availability",)),
        ("lake-del-valle", (
            "published_swimming_facilities", "swimming_safety_guidance",
            "boat_inspection_required", "watercraft_preparation",
            "cross_lake_boat_quarantine", "published_boating_fees",
        )),
    )),
    ("Ohlone Wilderness Trail", (
        ("trail-ohlone-wilderness", (
            "eastern_gateway", "trail_permit_required", "overnight_camping_reservation",
        )),
    )),
)

OHLONE_SECTIONS = (
    ("Permits, reservations, and parking", (
        (OHLONE_ID, (
            "trail_permit_required", "overnight_camping_reservation",
            "reserved_overnight_parking", "maximum_consecutive_nights",
        )),
    )),
    ("Western access at Mission Peak", (
        ("park-mission-peak-regional-preserve", (
            "visitor_access_policy", "official_map_route_distances",
        )),
        ("staging-mission-peak-stanford-avenue", (
            "official_page_linked_map_point",
        )),
        ("restroom-mission-peak-stanford-avenue", (
            "official_map_facility_presence",
        )),
        ("entrance-mission-peak-ohlone-college", (
            "access_address", "published_daily_parking_permit_policy",
        )),
        ("entrance-mission-peak-anza-pine", (
            "official_page_linked_map_point",
        )),
    )),
    ("Route, access, and distance", (
        (OHLONE_ID, (
            "eastern_gateway", "published_corridor_distances_miles",
            "mapped_access_restrictions", "trail_use", "traversed_parks",
        )),
    )),
    ("Camps and water", (
        (OHLONE_ID, (
            "ordered_backpack_camp_inventory", "mapped_backcountry_camps",
            "reported_water_availability", "backpack_fire_policy",
            "dogs_allowed_overnight", "alcohol_allowed",
        )),
    )),
)


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _json(payload: Any) -> str:
    return json.dumps(_plain(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_primary_nav() -> str:
    """Render the shared, stable navigation used by every public page."""
    links = "".join(
        f'<a href="{_e(path)}">{_e(label)}</a>' for label, path in PRIMARY_NAV[1:]
    )
    return ('<nav class="site-nav" aria-label="Primary">'
            '<a class="site-brand" href="/" aria-label="Wayproof home">Wayproof</a>'
            f'<div class="site-links">{links}</div></nav>')


def render_site_footer() -> str:
    return (
        '<footer class="site-footer"><div><strong>Wayproof</strong>'
        '<p>Source-backed outdoor planning with uncertainty left visible.</p></div>'
        '<div class="footer-links"><a href="/map/">Map</a><a href="/search/">Search</a>'
        '<a href="/how-it-works/">How it works</a>'
        '<a href="/changes/">Published changes</a>'
        '<a href="https://github.com/asideofkorn/wayproof">GitHub</a></div>'
        '<p class="meta footer-note">Planning aid, not a booking or safety guarantee. '
        'Confirm volatile conditions with the linked official source.</p></footer>'
    )


MAP_LAYERS = {
    "boundaries": ("park", "national_park", "wilderness"),
    "routes": ("route", "trail", "route_segment"),
    "peaks": ("peak", "pass", "mountain_pass"),
    "access": ("trailhead", "trail_access", "entrance", "walk_in_entrance", "staging_area"),
    "camping": ("campground", "campground_collection", "campsite",
                "family_campsite", "group_campsite", "cabin_campsite",
                "backcountry_camp", "equestrian_campsite",
                "equestrian_campsite_area", "equestrian_group_campsite"),
    "facilities": ("parking", "water_source", "restroom", "facility", "waterbody",
                   "lake", "visitor_center", "store"),
}


def _map_layer(kind: str) -> str | None:
    return next((layer for layer, kinds in MAP_LAYERS.items() if kind in kinds), None)


def _coordinate_geometry(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    candidate = value.get("geometry")
    if isinstance(candidate, dict) and candidate.get("type") in {
        "Point", "LineString", "MultiLineString", "Polygon", "MultiPolygon"
    } and candidate.get("coordinates"):
        return candidate
    latitude, longitude = value.get("latitude"), value.get("longitude")
    if (isinstance(latitude, (int, float)) and isinstance(longitude, (int, float))
            and -90 <= latitude <= 90 and -180 <= longitude <= 180):
        return {"type": "Point", "coordinates": [longitude, latitude]}
    return None


def explore_map_payload(reads: CanonicalReadService, entities: Iterable[dict],
                        as_of: date) -> dict:
    """Project only evidenced canonical geometry into the public map."""
    features = []
    for entity in entities:
        layer = _map_layer(entity["kind"])
        if not layer:
            continue
        if layer == "boundaries":
            boundary = reads.managed_land_geometry(entity["entity_id"])
            if boundary:
                properties = dict(boundary["properties"])
                properties.update({
                    "name": entity["name"], "kind": entity["kind"],
                    "layer": "boundaries",
                    "evidence_status": "reviewed, versioned source geometry",
                    "url": f'/knowledge/{entity["entity_id"]}/',
                })
                features.append({
                    "type": "Feature", "id": properties["claim_id"],
                    "properties": properties, "geometry": boundary["geometry"],
                })
        for claim in reads.claims_for(entity["entity_id"]):
            geometry = _coordinate_geometry(claim.value)
            if not geometry:
                continue
            geometry_type = geometry["type"]
            if layer == "boundaries" and geometry_type not in {"Polygon", "MultiPolygon"}:
                continue
            feature_layer = (
                "boundaries" if geometry_type in {"Polygon", "MultiPolygon"}
                and entity["kind"] in MAP_LAYERS["boundaries"] else layer
            )
            features.append({
                "type": "Feature",
                "id": claim.claim_id,
                "properties": {
                    "entity_id": entity["entity_id"],
                    "name": entity["name"],
                    "kind": entity["kind"],
                    "layer": feature_layer,
                    "evidence_status": "evidence-backed claim",
                    "claim_id": claim.claim_id,
                    "predicate": claim.predicate,
                    "url": f'/knowledge/{entity["entity_id"]}/',
                },
                "geometry": geometry,
            })
        if entity["kind"] == "route":
            route = reads.route_geometry(entity["entity_id"], as_of)
            if route:
                for index, feature in enumerate(route["features"]):
                    properties = dict(feature.get("properties", {}))
                    properties.update({
                        "entity_id": entity["entity_id"], "name": entity["name"],
                        "kind": "route", "layer": "routes",
                        "evidence_status": "reviewed, versioned source geometry",
                        "url": f'/knowledge/{entity["entity_id"]}/',
                    })
                    features.append({"type": "Feature",
                                     "id": f'{entity["entity_id"]}-{index}',
                                     "properties": properties,
                                     "geometry": feature["geometry"]})
    return {
        "type": "FeatureCollection",
        "features": features,
        "wayproof": {
            "generated_from": "CanonicalReadService",
            "as_of": as_of.isoformat(),
            "feature_count": len(features),
            "boundary_policy": "Only source-backed polygon geometry is shown.",
            "navigation_grade": False,
        },
    }


def render_explore_map_html(payload: dict, site_url: str) -> str:
    counts = {layer: 0 for layer in MAP_LAYERS}
    for feature in payload["features"]:
        counts[feature["properties"]["layer"]] += 1
    controls = "".join(
        f'<label><input type="checkbox" data-map-layer="{_e(layer)}" '
        f'{"checked" if count and layer != "camping" else ""} '
        f'{"disabled" if not count else ""}> '
        f'{_e(layer.title())} <span>{count}</span></label>'
        for layer, count in counts.items()
    )
    body = f'''{render_primary_nav()}
<header class="page-header"><span class="eyebrow">Explore Wayproof</span>
<h1>Map the published planning graph</h1>
<p class="subtitle">Browse source-backed routes, places, access, camping, and facilities.
Missing geometry stays missing; proximity is not treated as access.</p></header>
<main class="explore-map-shell" data-explore-map data-geometry-url="/map/features.geojson">
<div class="explore-map-toolbar"><div class="route-map-controls" role="group" aria-label="Basemap layer">
<button type="button" data-basemap="topo" aria-pressed="true">Topo</button>
<button type="button" data-basemap="aerial" aria-pressed="false">Aerial</button>
<button type="button" data-basemap="aerial-labels" aria-pressed="false">Aerial + labels</button></div>
<button class="button map-expand" type="button" data-map-expand aria-expanded="false">Full screen</button></div>
<div class="explore-map-layout"><aside class="map-layer-panel" aria-label="Map layers"><strong>Layers</strong>{controls}</aside>
<div class="explore-map-canvas" data-map-canvas aria-label="Interactive map of published Wayproof geometry"></div>
<aside class="map-selection" data-map-selection aria-live="polite"><strong>Select a feature</strong>
<p>Tap or click a route, place, or facility to inspect it.</p></aside></div>
<p class="meta" data-map-status>Interactive map loads when scrolled into view.</p>
<p class="meta">{len(payload["features"])} published geometry features · planning evidence, not navigation-grade mapping ·
<a href="/map/features.geojson">Download GeoJSON</a></p></main>
<script type="module" src="/assets/explore-map.js?v={EXPLORE_MAP_ASSET_VERSION}"></script>'''
    return _page("Explore Map — Wayproof",
                 "Explore source-backed routes, places, access, camping, and facilities.",
                 f"{site_url}/map/", body,
                 '<link rel="stylesheet" href="/assets/vendor/maplibre/maplibre-gl.css">')


def _page(title: str, description: str, canonical: str, body: str,
          head_extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<meta name="description" content="{_e(description)}">
<link rel="canonical" href="{_e(canonical)}">
<link rel="stylesheet" href="/style.css">
{head_extra}
</head>
<body>
{body}
{render_site_footer()}
</body>
</html>
"""


def _source_label(source: dict) -> str:
    locator = source["locator"]
    label = source.get("publisher") or locator
    parsed = urlparse(locator)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return f'<a href="{_e(locator)}" rel="noopener">{_e(label)}</a>'
    return f'<code>{_e(label)}</code>'


def _claim_bundle(reads: CanonicalReadService, claim) -> dict:
    provenance = reads.explain_claim(claim.claim_id)
    return {
        "claim": claim,
        "evidence": provenance.evidence,
        "observations": provenance.observations,
        "sources": provenance.sources,
    }


def entity_payload(reads: CanonicalReadService, entity_id: str,
                   route_geometry: dict | None = None,
                   geometry_url: str | None = None) -> dict:
    """Build one transport-neutral entity view exclusively through read APIs."""
    entity = reads.entity(entity_id)
    claims = []
    gaps_by_id = {item.gap_id: item for item in reads.knowledge_gaps_for(entity_id)}
    history = list(reads.changes(record_id=entity_id))
    for claim in reads.claims_for(entity_id):
        claims.append(_claim_bundle(reads, claim))
        gaps_by_id.update(
            (item.gap_id, item) for item in reads.knowledge_gaps_for(claim.claim_id)
        )
        history.extend(reads.changes(record_id=claim.claim_id, record_type="claim"))
    return _plain({
        "type": "canonical_entity",
        "entity": entity,
        "answerability": (
            "evidence_backed_claims_available" if claims else "no_direct_claims_published"
        ),
        "claims": claims,
        "relationships": reads.relationships_for(entity_id),
        "knowledge_gaps": tuple(gaps_by_id.values()),
        "history": history,
        "route_geometry": route_geometry,
        "route_geometry_url": geometry_url,
    })


def _route_map_html(geometry: dict, geometry_url: str) -> str:
    """Render an interactive map from generated route GeoJSON."""
    features = geometry["features"]
    total = geometry["wayproof"]["distance_miles"]
    is_loop = geometry["wayproof"].get("route_shape") == "loop"
    interactive_map = (
        '<div class="interactive-route-map" data-interactive-route-map '
        f'data-geometry-url="{_e(geometry_url)}">'
        '<div class="route-map-controls" role="group" aria-label="Basemap layer">'
        '<button type="button" data-basemap="topo" aria-pressed="true">Topo</button>'
        '<button type="button" data-basemap="aerial" aria-pressed="false">Aerial</button>'
        '<button type="button" data-basemap="aerial-labels" aria-pressed="false">Aerial + labels</button>'
        '</div><div class="route-map-canvas" data-map-canvas '
        'aria-label="Interactive evidence-backed route map"></div>'
        '<p class="meta route-map-status" data-map-status aria-live="polite">'
        'Interactive map loads when scrolled into view.</p></div>'
    )
    script = (
        '<script type="module" '
        f'src="/assets/route-map.js?v={ROUTE_MAP_ASSET_VERSION}"></script>'
    )
    return (
        '<section id="route-map" class="route-map"><h2>Route map</h2>'
        '<p>This overview is built from a reviewed, versioned source snapshot. '
        'It is planning evidence, not navigation-grade mapping.</p>'
        + interactive_map + '<div class="route-map-legend">'
        + (
            '<span><i class="start-dot"></i>Start / finish</span>'
            f'<span>{_e(round(total, 2))} miles mapped loop</span></div>'
            if is_loop else
            '<span><i class="start-dot"></i>Start</span>'
            '<span><i class="end-dot"></i>Destination</span>'
            f'<span>{_e(round(total, 2))} miles one way</span></div>'
        )
        + f'<p class="meta"><a href="{_e(geometry_url)}">Download generated GeoJSON</a> · '
        f'{len(features)} canonical segments · source geometry accuracy not reported</p>'
        + script + '</section>'
    )


def del_valle_destination_payload(reads: CanonicalReadService,
                                  as_of: date) -> dict:
    """Compose a visitor-oriented Del Valle view from canonical read APIs."""
    sections = []
    for title, selections in DEL_VALLE_SECTIONS:
        bundles = []
        for entity_id, predicates in selections:
            wanted = set(predicates)
            bundles.extend(
                _claim_bundle(reads, claim)
                for claim in reads.claims_for(entity_id)
                if claim.predicate in wanted
            )
        sections.append({"title": title, "claims": bundles})

    context = PlanningContext(
        trip_date=as_of,
        objectives=(TripObjective("visit", DEL_VALLE_ID, "visit"),),
        stages=(TripStage("visit", 1, "visit", DEL_VALLE_SCOPES),),
    )
    recheck = reads.pretrip_recheck(context)
    recheck_items = []
    for item in recheck.items:
        entry = {"result": item}
        if item.claim_id:
            claim = reads.get("claim", item.claim_id)
            entry["claim"] = _claim_bundle(reads, claim)
        else:
            entry["gap"] = reads.get("gap", item.input_id)
        recheck_items.append(entry)

    related = []
    for relationship in reads.relationships_for(DEL_VALLE_ID):
        other_id = (relationship.object_id
                    if relationship.subject_id == DEL_VALLE_ID
                    else relationship.subject_id)
        try:
            entity = reads.entity(other_id)
        except KeyError:
            continue
        related.append({"relationship": relationship, "entity": entity})

    return _plain({
        "type": "destination",
        "as_of": as_of,
        "entity": reads.entity(DEL_VALLE_ID),
        "recheck": {
            "result_id": recheck.result_id,
            "state": recheck.state,
            "topics": recheck.topics,
            "items": recheck_items,
        },
        "sections": sections,
        "related": related,
    })


def ohlone_trail_payload(reads: CanonicalReadService) -> dict:
    """Compose the public Ohlone guide from canonical reads only."""
    sections = []
    for title, selections in OHLONE_SECTIONS:
        bundles = []
        for entity_id, predicates in selections:
            wanted = set(predicates)
            for claim in reads.claims_for(entity_id):
                if claim.predicate in wanted:
                    bundle = _claim_bundle(reads, claim)
                    bundle["subject"] = reads.entity(entity_id)
                    bundles.append(bundle)
        sections.append({"title": title, "claims": bundles})
    results = [reads.get("derived_result", result_id) for result_id in (
        "result-ohlone-doe-canyon-roundtrip-detour",
        "result-ohlone-ot27-ot29-route-comparison",
        "result-ohlone-ot33-ot35-route-comparison",
    )]
    return _plain({
        "type": "trail_guide", "entity": reads.entity(OHLONE_ID),
        "sections": sections, "route_results": results,
        "knowledge_gaps": reads.knowledge_gaps_for(OHLONE_ID),
    })


def _claim_html(bundle: dict) -> str:
    claim = bundle["claim"]
    sources = []
    observations = {item["source_id"]: item for item in bundle["observations"]}
    for source in bundle["sources"]:
        observation = observations.get(source["source_id"], {})
        checked = observation.get("observed_at") or observation.get("retrieved_at")
        date_text = f" · observed/retrieved {_e(checked)}" if checked else ""
        sources.append(f'<li>{_source_label(source)}{date_text}</li>')
    source_html = "".join(sources) or "<li>No source is attached.</li>"
    return (
        '<article class="fact-row">'
        f'<h4>{_e(_human_label(claim["predicate"]))}</h4>'
        f'{_human_value(claim["value"])}'
        f'<details><summary>Evidence and sources ({len(bundle["evidence"])})</summary>'
        f'<ul>{source_html}</ul></details>'
        '</article>'
    )


def _human_label(value: str) -> str:
    labels = {
        "operating_status": "Park status", "reservation_window": "Book a campsite",
        "gate_hours": "Campground gate", "water_quality_advisory": "Swimming advisory",
        "boat_inspection_required": "Boat inspection", "overnight_camping_reservation": "Ohlone overnights",
        "published_corridor_distances_miles": "Trail distance",
        "mapped_access_restrictions": "Who can use the trail",
        "reported_water_availability": "Water sources",
        "visitor_access_policy": "Parking and access choices",
        "official_map_route_distances": "Published route distances",
        "official_page_linked_map_point": "Official map location",
        "official_map_facility_presence": "Trailhead restroom",
        "access_address": "Access address",
        "published_daily_parking_permit_policy": "College parking permit",
    }
    return labels.get(value, value.replace("_", " ").strip().capitalize())


def _claim_section(predicate: str) -> str:
    """Place canonical predicates into a small, stable human hierarchy."""
    if any(token in predicate for token in (
        "permit", "reservation", "fee", "status", "condition", "advisory",
        "availability", "hours", "restriction", "allowed", "required", "policy",
    )):
        return "Requirements and current conditions"
    if any(token in predicate for token in (
        "access", "address", "parking", "entrance", "gateway", "transport",
    )):
        return "Getting there"
    if any(token in predicate for token in (
        "route", "trail", "approach", "distance", "corridor", "elevation",
        "topographic", "geographic",
    )):
        return "Routes and geography"
    if any(token in predicate for token in (
        "camp", "site", "facility", "restroom", "water", "boat", "swim",
        "dog", "fire", "generator", "connectivity",
    )):
        return "Facilities and services"
    return "More planning facts"


def _relationship_section(predicate: str) -> str:
    if any(token in predicate for token in (
        "access", "entrance", "gateway", "starts", "approach", "uses_corridor",
    )):
        return "Access and approaches"
    if any(token in predicate for token in (
        "contain", "located", "serves", "facility", "camp", "books",
    )):
        return "Places and facilities"
    if any(token in predicate for token in (
        "manage", "boundary", "jurisdiction", "part_of",
    )):
        return "Land and management"
    return "Routes and related places"


def _short_fact(bundle: dict) -> bool:
    """Select compact facts for the overview without inventing priority data."""
    claim = bundle["claim"]
    predicate = claim["predicate"]
    value = claim["value"]
    preferred = any(token in predicate for token in (
        "status", "elevation", "distance", "address", "capacity", "identity",
        "reservation_window", "gate_hours",
    ))
    return preferred and len(json.dumps(value, ensure_ascii=False)) <= 500


def _human_value(value: Any) -> str:
    """Render structured claim values as readable nested HTML."""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if value is None:
        return "Unknown"
    if isinstance(value, dict):
        return '<dl>' + ''.join(
            f'<dt>{_e(_human_label(str(key)))}</dt><dd>{_human_value(item)}</dd>'
            for key, item in value.items()) + '</dl>'
    if isinstance(value, list):
        return '<ul>' + ''.join(f'<li>{_human_value(item)}</li>' for item in value) + '</ul>'
    if isinstance(value, str):
        parsed = urlparse(value)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return f'<a href="{_e(value)}" rel="noopener">{_e(value)}</a>'
        return _e(value.replace("_", " "))
    return _e(value)


def _destination_claim_html(bundle: dict) -> str:
    claim = bundle["claim"]
    sources = ''.join(f'<li>{_source_label(source)}</li>' for source in bundle["sources"])
    return (
        '<article class="fact-row">'
        f'<h3>{_e(_human_label(claim["predicate"]))}</h3>'
        f'{_human_value(claim["value"])}'
        f'<details><summary>Sources and details</summary><ul>{sources}</ul>'
        f'<p class="meta">Canonical claim <code>{_e(claim["claim_id"])}</code></p></details>'
        '</article>'
    )


def _corridor_claim_html(bundle: dict) -> str:
    """Render a claim while preserving which corridor place it describes."""
    claim = bundle["claim"]
    subject = bundle.get("subject")
    subject_html = (f'<p class="meta fact-subject">{_e(subject["name"])}</p>'
                    if subject and subject["entity_id"] != OHLONE_ID else "")
    sources = ''.join(f'<li>{_source_label(source)}</li>' for source in bundle["sources"])
    return (
        '<article class="fact-row">'
        f'{subject_html}<h3>{_e(_human_label(claim["predicate"]))}</h3>'
        f'{_human_value(claim["value"])}'
        f'<details><summary>Sources and details</summary><ul>{sources}</ul>'
        f'<p class="meta">Canonical claim <code>{_e(claim["claim_id"])}</code></p></details>'
        '</article>'
    )


def _recheck_item_html(item: dict) -> str:
    result = item["result"]
    status = result["answerability"]
    if "claim" in item:
        bundle = item["claim"]
        claim = bundle["claim"]
        title = _human_label(claim["predicate"])
        detail = _human_value(claim["value"])
        sources = ''.join(f'<li>{_source_label(source)}</li>'
                          for source in bundle["sources"])
    else:
        gap = item["gap"]
        title = gap["question"]
        detail = f'<p>{_e(gap["reason"] or result["explanation"])}</p>'
        sources = ""
    explanation = ("" if "gap" in item and gap.get("reason") == result["explanation"]
                   else f'<p class="meta">{_e(result["explanation"])}</p>')
    source_block = (f'<details><summary>Sources</summary><ul>{sources}</ul></details>'
                    if sources else "")
    return (
        f'<article class="notice {"notice-unknown" if status == "unknown" else ""}">'
        f'<h3>{_e(title)}</h3>{detail}'
        f'{explanation}{source_block}'
        '</article>'
    )


def render_del_valle_destination_html(payload: dict, site_url: str) -> str:
    entity = payload["entity"]
    recheck = payload["recheck"]
    priority = {"unknown": 0, "needs_current_check": 1, "answered": 2}
    items = sorted(recheck["items"],
                   key=lambda item: (priority[item["result"]["answerability"]],
                                     item["result"]["input_id"]))
    current_checks = [item for item in items
                      if item["result"]["answerability"] == "needs_current_check"]
    unknown = [item for item in items if item["result"]["answerability"] == "unknown"]
    answered = [item for item in items
                if item["result"]["answerability"] == "answered"]
    claims = {bundle["claim"]["predicate"]: bundle
              for section in payload["sections"] for bundle in section["claims"]}
    summary_predicates = (
        "operating_status", "reservation_window", "gate_hours",
        "water_quality_advisory", "boat_inspection_required",
        "overnight_camping_reservation",
    )
    summary = [claims[item] for item in summary_predicates if item in claims]
    body = [
        render_primary_nav(),
        '<header class="page-header">', f'<h1>{_e(entity["name"])}</h1>',
        '<p class="tagline">Plan access, camping, lake recreation, and the '
        'Ohlone Wilderness Trail from one evidence-backed view.</p>',
        f'<p class="meta page-meta">Updated {_e(payload["as_of"])}</p></header>',
        '<ul class="section-nav" aria-label="On this page">'
        '<li><a href="#before-you-go">Before you go</a></li>'
        '<li><a href="#getting-there-and-entering">Getting there</a></li>'
        '<li><a href="#camping">Camping</a></li>'
        '<li><a href="#swimming-boating-and-lake-conditions">Lake recreation</a></li>'
        '<li><a href="#ohlone-wilderness-trail">Ohlone Trail</a></li></ul>',
        '<section aria-labelledby="at-a-glance"><h2 id="at-a-glance">At a glance</h2>',
        '<div class="summary-grid">',
    ]
    for bundle in summary:
        claim = bundle["claim"]
        body.append('<div class="summary-item">'
                    f'<strong>{_e(_human_label(claim["predicate"]))}</strong>'
                    f'{_human_value(claim["value"])}</div>')
    body.append('</div></section><section id="before-you-go"><h2>Check before you go</h2>'
                f'<p><strong>Recheck {_e(recheck["state"])}</strong>. Conditions below can '
                'change. Follow the linked official source before leaving.</p>')
    body.extend(_recheck_item_html(item) for item in current_checks)
    if unknown:
        body.append(f'<details><summary>{len(unknown)} questions Wayproof cannot currently answer</summary>')
        body.extend(_recheck_item_html(item) for item in unknown)
        body.append('</details>')
    if answered:
        body.append(f'<details><summary>{len(answered)} dated/current inputs available</summary>')
        body.extend(_recheck_item_html(item) for item in answered)
        body.append('</details>')
    body.append('</section>')

    for section in payload["sections"]:
        anchor = section["title"].lower().replace(",", "").replace(" ", "-")
        body.append(f'<section id="{_e(anchor)}"><h2>{_e(section["title"])}</h2><div class="fact-list">')
        if section["title"] == "Ohlone Wilderness Trail":
            body.append('<p>Del Valle is the eastern gateway to the corridor. For Mission Peak, '
                        'Stanford Avenue, Ohlone College, camps, water, route distances, and '
                        f'alternatives, use the <a href="{OHLONE_PATH}">complete Ohlone Trail guide</a>.</p>')
        if section["claims"]:
            body.extend(_destination_claim_html(bundle) for bundle in section["claims"])
        else:
            body.append('<p>No canonical answer is published for this section.</p>')
        body.append('</div></section>')

    body.append('<section><h2>Explore related places and facilities</h2><ul>')
    for item in payload["related"]:
        relationship = item["relationship"]
        related = item["entity"]
        path = (DEL_VALLE_PATH if related["entity_id"] == DEL_VALLE_ID
                else f'/knowledge/{related["entity_id"]}/')
        body.append(
            f'<li>{_e(_human_label(relationship["predicate"]))}: '
            f'<a href="{_e(path)}">{_e(related["name"])}</a></li>'
        )
    body.append('</ul></section>')
    body.append(f'<aside class="technical-links"><strong>Reference formats</strong><p>'
                f'<a href="/knowledge/{_e(entity["entity_id"])}/">Canonical record</a> · '
                f'<a href="{DEL_VALLE_PATH}index.json">JSON</a></p></aside>')
    return _page(
        'Plan Del Valle Regional Park — Wayproof',
        'Evidence-backed Del Valle access, camping, lake conditions, and Ohlone Trail planning.',
        f'{site_url}{DEL_VALLE_PATH}', "\n".join(body),
    )


def render_ohlone_trail_html(payload: dict, site_url: str) -> str:
    body = [
        render_primary_nav(),
        '<header class="page-header"><h1>Ohlone Wilderness Trail</h1>',
        '<p class="tagline">Plan the full corridor from Del Valle through Sunol to Mission '
        'Peak, including trailheads, parking, camps, water, and route choices.</p></header>',
        '<ul class="section-nav" aria-label="On this page">'
        '<li><a href="#permits-reservations-and-parking">Permits</a></li>'
        '<li><a href="#western-access-at-mission-peak">Mission Peak access</a></li>'
        '<li><a href="#route-access-and-distance">Route</a></li>'
        '<li><a href="#camps-and-water">Camps and water</a></li>'
        '<li><a href="#route-choices-and-detours">Alternatives</a></li></ul>',
        '<section class="notice"><h2>Choose your endpoint</h2>'
        '<p><strong>Del Valle</strong> is the eastern gateway. At the western end, use '
        '<strong>Stanford Avenue</strong> for the staging area and permitted overnight '
        'parking, or approach the <strong>Anza–Pine walk-in entrance</strong> from '
        '<strong>Ohlone College</strong> for greater daytime parking capacity.</p></section>',
    ]
    for section in payload["sections"]:
        anchor = section["title"].lower().replace(",", "").replace(" ", "-")
        body.append(f'<section id="{_e(anchor)}"><h2>{_e(section["title"])}</h2>'
                    '<div class="fact-list">')
        body.extend(_corridor_claim_html(item) for item in section["claims"])
        body.append('</div></section>')
    body.append('<section id="route-choices-and-detours"><h2>Route choices and detours</h2>')
    for result in payload["route_results"]:
        body.append('<article class="card">'
                    f'<h3>{_e(_human_label(result["kind"]))}</h3>'
                    f'{_human_value(result["value"])}'
                    f'<p>{_e(result["explanation"])}</p></article>')
    body.append(f'</section><aside class="technical-links"><strong>Reference formats</strong>'
                f'<p><a href="/knowledge/{OHLONE_ID}/">Canonical record</a> · '
                f'<a href="{OHLONE_PATH}index.json">JSON</a></p></aside>')
    return _page('Plan the Ohlone Wilderness Trail — Wayproof',
                 'Evidence-backed Ohlone Trail permits, camps, water, access, and route choices.',
                 f'{site_url}{OHLONE_PATH}', "\n".join(body))


def render_entity_html(payload: dict, site_url: str,
                       entities_by_id: dict[str, dict]) -> str:
    entity = payload["entity"]
    claims = payload["claims"]
    gaps = payload["knowledge_gaps"]
    claim_groups: dict[str, list[dict]] = {}
    for bundle in claims:
        claim_groups.setdefault(_claim_section(bundle["claim"]["predicate"]), []).append(bundle)
    summary = [bundle for bundle in claims if _short_fact(bundle)][:4]
    relationship_groups: dict[str, list[dict]] = {}
    for relationship in payload["relationships"]:
        relationship_groups.setdefault(
            _relationship_section(relationship["predicate"]), []).append(relationship)
    body = [
        render_primary_nav(),
        '<header class="page-header">', f'<h1>{_e(entity["name"])}</h1>',
        f'<p class="subtitle"><span class="eyebrow">{_e(_human_label(entity["kind"]))}</span></p>',
        f'<p class="tagline">Plan with {len(claims)} source-backed fact'
        f'{"" if len(claims) == 1 else "s"}, {len(payload["relationships"])} related record'
        f'{"" if len(payload["relationships"]) == 1 else "s"}, and explicit uncertainty.</p>',
        '</header>',
        '<ul class="section-nav" aria-label="On this page">'
        + ('<li><a href="#route-map">Map</a></li>' if payload["route_geometry"] else '')
        + '<li><a href="#plan">Plan</a></li><li><a href="#explore">Explore</a></li>'
        '<li><a href="#before-you-go">Before you go</a></li>'
        '<li><a href="#evidence">Evidence</a></li></ul>',
    ]
    if payload["route_geometry"]:
        body.append(_route_map_html(
            payload["route_geometry"], payload["route_geometry_url"],
        ))
    if summary:
        body.append('<section aria-labelledby="at-a-glance"><h2 id="at-a-glance">At a glance</h2>'
                    '<div class="summary-grid">')
        for bundle in summary:
            claim = bundle["claim"]
            body.append('<div class="summary-item">'
                        f'<strong>{_e(_human_label(claim["predicate"]))}</strong>'
                        f'{_human_value(claim["value"])}</div>')
        body.append('</div></section>')
    body.append('<section id="plan"><h2>Plan a visit</h2>')
    if claims:
        for title in (
            "Requirements and current conditions", "Getting there",
            "Routes and geography", "Facilities and services", "More planning facts",
        ):
            bundles = claim_groups.get(title, [])
            if bundles:
                body.append(f'<section class="planning-group"><h3>{_e(title)}</h3>'
                            '<div class="fact-list">')
                body.extend(_claim_html(bundle) for bundle in bundles)
                body.append('</div></section>')
    else:
        body.append('<div class="notice notice-unknown"><p>No direct planning facts are '
                    'published yet. That absence is not confirmation.</p></div>')
    body.append('</section>')
    body.append('<section id="explore"><h2>Explore related places</h2>')
    if relationship_groups:
        for title in ("Access and approaches", "Places and facilities",
                      "Land and management", "Routes and related places"):
            items = relationship_groups.get(title, [])
            if not items:
                continue
            body.append(f'<h3>{_e(title)} <span class="meta">({len(items)})</span></h3>')
            visible_items = items[:8]
            remaining_items = items[8:]
            body.append('<ul class="related-list">')
            for item in visible_items:
                other = (item["object_id"] if item["subject_id"] == entity["entity_id"]
                         else item["subject_id"])
                related = entities_by_id.get(other)
                label = related["name"] if related else other
                link = (f'<a href="/knowledge/{_e(other)}/">{_e(label)}</a>'
                        if related else f'<span>{_e(label)}</span>')
                direction = ("From this record" if item["subject_id"] == entity["entity_id"]
                             else "To this record")
                body.append('<li class="related-card">'
                            f'<span class="relationship-label">{_e(_human_label(item["predicate"]))}</span>'
                            f'{link}<span class="meta">{_e(direction)}</span></li>')
            body.append('</ul>')
            if remaining_items:
                body.append(f'<details class="related-more"><summary>Show {len(remaining_items)} more</summary>'
                            '<ul class="related-list">')
                for item in remaining_items:
                    other = (item["object_id"] if item["subject_id"] == entity["entity_id"]
                             else item["subject_id"])
                    related = entities_by_id.get(other)
                    label = related["name"] if related else other
                    link = (f'<a href="/knowledge/{_e(other)}/">{_e(label)}</a>'
                            if related else f'<span>{_e(label)}</span>')
                    direction = ("From this record" if item["subject_id"] == entity["entity_id"]
                                 else "To this record")
                    body.append('<li class="related-card">'
                                f'<span class="relationship-label">{_e(_human_label(item["predicate"]))}</span>'
                                f'{link}<span class="meta">{_e(direction)}</span></li>')
                body.append('</ul></details>')
    else:
        body.append('<p>No related canonical records are published yet.</p>')
    body.append('</section>')
    body.append('<section id="before-you-go"><h2>Before you go</h2>')
    if gaps:
        body.append('<p>These open questions need confirmation; Wayproof does not fill them '
                    'with guesses.</p>')
        body.extend('<article class="notice notice-unknown">'
                    f'<h3>{_e(item["question"])}</h3>'
                    f'{"<p>" + _e(item["reason"]) + "</p>" if item.get("reason") else ""}'
                    '</article>' for item in gaps)
    else:
        body.append('<p>No explicit knowledge gap is linked to this entity. That does not '
                    'mean the record is complete.</p>')
    body.append('</section>')
    body.append('<section id="evidence"><h2>Sources, evidence, and history</h2>'
                '<p>Planning facts above are readable first. Open these records when you need '
                'to audit a source or see when knowledge changed.</p>')
    if claims:
        body.append(f'<details><summary>Evidence for {len(claims)} published claim'
                    f'{"" if len(claims) == 1 else "s"}</summary><ul class="evidence-list">')
        for bundle in claims:
            source_items = ''.join(f'<li>{_source_label(source)}</li>'
                                   for source in bundle["sources"])
            body.append('<li><strong>'
                        f'{_e(_human_label(bundle["claim"]["predicate"]))}</strong>'
                        f'<ul>{source_items or "<li>No source is attached.</li>"}</ul></li>')
        body.append('</ul></details>')
    body.append('<details><summary>Published ChangeSet history</summary>')
    if payload["history"]:
        body.append('<ul>' + ''.join(
            f'<li><code>{_e(item["change_set_id"])}</code> — '
            f'{_e(item["action"])} <code>{_e(item["record_id"])}</code>: '
            f'{_e(item["reason"] or item["summary"])}</li>'
            for item in payload["history"]) + '</ul>')
    else:
        body.append('<p>No matching published ChangeSet operation was found.</p>')
    body.append('</details></section>')
    body.append(
        f'<aside class="technical-links"><strong>Reference formats</strong><p>'
        f'<a href="/knowledge/{_e(entity["entity_id"])}.json">JSON</a> · '
        f'<code>{_e(entity["entity_id"])}</code></p></aside><p class="meta">'
        'Canonical data is historical evidence, not a guarantee of current conditions. '
        'Recheck volatile facts before travel.</p>'
    )
    head_extra = (
        '<link rel="stylesheet" href="/assets/vendor/maplibre/maplibre-gl.css">'
        if payload["route_geometry"] else ""
    )
    return _page(
        f'{entity["name"]} — Wayproof',
        f'Canonical claims, sources, gaps, and history for {entity["name"]}.',
        f'{site_url}/knowledge/{entity["entity_id"]}/',
        "\n".join(body),
        head_extra=head_extra,
    )


def render_search_html(entities: Iterable[dict], site_url: str,
                       preferred_paths: dict[str, str] | None = None) -> str:
    entities = list(entities)
    preferred_paths = preferred_paths or {}
    kinds = sorted({item["kind"] for item in entities})
    rows = "".join(
        f'<li class="result-card" data-search="{_e((item["name"] + " " + item["entity_id"]).casefold())}" '
        f'data-kind="{_e(item["kind"])}">'
        f'<a href="{_e(preferred_paths.get(item["entity_id"], "/knowledge/" + item["entity_id"] + "/"))}">'
        f'{_e(item["name"])}</a> '
        f'<span class="pill">{_e(item["kind"])}</span></li>'
        for item in entities
    )
    options = ''.join(f'<option value="{_e(kind)}">{_e(kind)}</option>' for kind in kinds)
    body = f"""
{render_primary_nav()}
<header class="page-header"><span class="eyebrow">Explore the knowledge base</span>
<h1>Find a place, route, or campsite</h1>
<p class="subtitle">Search {len(entities)} published entities. Every result opens a page
that separates supported facts, open questions, sources, and history.</p></header>
<form id="entity-search-form" class="search-controls" action="/search/" method="get">
<label for="entity-search">Search by name</label>
<input id="entity-search" name="q" type="search" placeholder="Try Mount Whitney or Del Valle">
<label for="entity-kind">Narrow by type</label>
<select id="entity-kind" name="kind"><option value="">All types</option>{options}</select>
<button class="button primary search-submit" type="submit">Search</button></form>
<p id="result-count" class="meta" role="status" aria-live="polite" tabindex="-1">Enter a name or choose a type to search.</p>
<p id="no-results" class="notice notice-unknown" hidden>No matching places, routes, or campsites. Try a shorter name or select a different type.</p>
<ul id="entity-results" class="result-grid">{rows}</ul>
<noscript><p>All entities are listed above; browser filtering requires JavaScript.</p></noscript>
<script>
const query = document.getElementById('entity-search');
const kind = document.getElementById('entity-kind');
const form = document.getElementById('entity-search-form');
const count = document.getElementById('result-count');
const empty = document.getElementById('no-results');
const rows = [...document.querySelectorAll('#entity-results li')];
function filterEntities() {{
  const needle = query.value.trim().toLocaleLowerCase();
  const hasCriteria = Boolean(needle || kind.value);
  let visible = 0;
  for (const row of rows) {{
    const show = hasCriteria && (!needle || row.dataset.search.includes(needle)) &&
                 (!kind.value || row.dataset.kind === kind.value);
    row.hidden = !show;
    if (show) visible += 1;
  }}
  count.textContent = hasCriteria
    ? `${{visible}} ${{visible === 1 ? 'result' : 'results'}}`
    : 'Enter a name or choose a type to search.';
  empty.hidden = !hasCriteria || visible !== 0;
  return visible;
}}
query.addEventListener('input', filterEntities);
kind.addEventListener('change', filterEntities);
query.addEventListener('keydown', event => {{
  if (event.key === 'Enter') {{
    event.preventDefault();
    form.requestSubmit();
  }}
}});
form.addEventListener('submit', event => {{
  event.preventDefault();
  filterEntities();
  const params = new URLSearchParams();
  if (query.value.trim()) params.set('q', query.value.trim());
  if (kind.value) params.set('kind', kind.value);
  const suffix = params.toString();
  history.replaceState(null, '', suffix ? `/search/?${{suffix}}` : '/search/');
  query.blur();
  count.focus();
}});
const initial = new URLSearchParams(location.search);
query.value = initial.get('q') || '';
if ([...kind.options].some(option => option.value === initial.get('kind'))) {{
  kind.value = initial.get('kind') || '';
}}
filterEntities();
</script>
"""
    return _page(
        'Canonical search — Wayproof',
        'Search published Wayproof entities and inspect evidence, gaps, and history.',
        f'{site_url}/search/', body,
    )


def render_directory_html(key: str, entities: Iterable[dict], site_url: str,
                          preferred_paths: dict[str, str] | None = None) -> str:
    """Render one automatically populated, canonical entity directory."""
    spec = DIRECTORIES[key]
    entities = list(entities)
    preferred_paths = preferred_paths or {}
    kinds = sorted({item["kind"] for item in entities})
    options = ''.join(f'<option value="{_e(kind)}">{_e(_human_label(kind))}</option>'
                      for kind in kinds)
    rows = "".join(
        '<li class="directory-card" '
        f'data-search="{_e((item["name"] + " " + item["entity_id"]).casefold())}" '
        f'data-kind="{_e(item["kind"])}">'
        f'<a href="{_e(preferred_paths.get(item["entity_id"], "/knowledge/" + item["entity_id"] + "/"))}">'
        f'<strong>{_e(item["name"])}</strong></a>'
        f'<span class="meta">{_e(_human_label(item["kind"]))}</span></li>'
        for item in entities
    )
    body = (
        render_primary_nav()
        + f'<header class="page-header"><span class="eyebrow">Browse Wayproof</span>'
        + f'<h1>{_e(spec["title"])}</h1>'
        + f'<p class="tagline">{_e(spec["description"])}</p>'
        + f'<p class="meta">{len(entities)} published records</p></header>'
        + '<div class="directory-controls">'
        + f'<label for="directory-search">Filter { _e(spec["title"].lower()) }</label>'
        + '<input id="directory-search" type="search" placeholder="Type a name">'
        + '<label for="directory-kind">Type</label>'
        + f'<select id="directory-kind"><option value="">All types</option>{options}</select></div>'
        + f'<p id="directory-count" class="meta">{len(entities)} results</p>'
        + f'<ul id="directory-results" class="directory-grid">{rows}</ul>'
        + '''<script>
const directoryQuery = document.getElementById('directory-search');
const directoryKind = document.getElementById('directory-kind');
const directoryRows = [...document.querySelectorAll('#directory-results li')];
function filterDirectory() {
  const needle = directoryQuery.value.trim().toLocaleLowerCase();
  let visible = 0;
  for (const row of directoryRows) {
    const show = (!needle || row.dataset.search.includes(needle)) &&
                 (!directoryKind.value || row.dataset.kind === directoryKind.value);
    row.hidden = !show;
    if (show) visible += 1;
  }
  document.getElementById('directory-count').textContent = `${visible} results`;
}
directoryQuery.addEventListener('input', filterDirectory);
directoryKind.addEventListener('change', filterDirectory);
</script>'''
    )
    return _page(
        f'{spec["title"]} — Wayproof', spec["description"],
        f'{site_url}/{key}/', body,
    )


def render_changes_html(entries: Iterable[dict], site_url: str) -> str:
    """Render ChangeSet history grouped into one readable entry per change."""
    grouped: dict[str, dict] = {}
    for entry in entries:
        group = grouped.setdefault(entry["change_set_id"], {
            "summary": entry["summary"], "operations": [],
        })
        group["operations"].append(entry)
    articles = []
    for change_set_id, group in reversed(tuple(grouped.items())):
        operations = group["operations"]
        rows = "".join(
            f'<li>{_e(_human_label(item["action"]))} '
            f'<code>{_e(item["record_type"])}</code> '
            f'<code>{_e(item["record_id"])}</code>'
            f'{" — " + _e(item["reason"]) if item["reason"] else ""}</li>'
            for item in operations
        )
        articles.append(
            '<article class="change-card">'
            f'<p class="eyebrow">Published ChangeSet</p><h2><code>{_e(change_set_id)}</code></h2>'
            f'<p>{_e(group["summary"])}</p>'
            f'<details><summary>{len(operations)} published operations</summary>'
            f'<ul>{rows}</ul></details></article>'
        )
    body = (
        render_primary_nav()
        + '<header class="page-header"><span class="eyebrow">Public history</span>'
        + '<h1>What changed, and why</h1>'
        + '<p class="tagline">See when canonical knowledge was added, replaced, or removed. '
          'Current snapshots stay concise while ChangeSets preserve the public history.</p>'
        + f'<p class="meta">{len(grouped)} published ChangeSets</p></header>'
        + '<div class="change-list">' + "".join(articles) + '</div>'
    )
    return _page(
        'Published changes — Wayproof',
        'Chronological history of published Wayproof canonical ChangeSets.',
        f'{site_url}/changes/', body,
    )


def build_canonical_site(reads: CanonicalReadService, output_dir: Path,
                         site_url: str, as_of: date) -> dict:
    """Write canonical search and detail pages into an existing site artifact."""
    entities = tuple(_plain(item) for item in reads.search_entities())
    entities_by_id = {item["entity_id"]: item for item in entities}
    preferred_paths = {DEL_VALLE_ID: DEL_VALLE_PATH, OHLONE_ID: OHLONE_PATH}
    map_dir = output_dir / "map"
    map_dir.mkdir(parents=True, exist_ok=True)
    map_payload = explore_map_payload(reads, entities, as_of)
    (map_dir / "features.geojson").write_text(_json(map_payload), encoding="utf-8")
    (map_dir / "index.html").write_text(
        render_explore_map_html(map_payload, site_url), encoding="utf-8")
    search_dir = output_dir / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    (search_dir / "index.html").write_text(render_search_html(
        entities, site_url, preferred_paths),
        encoding="utf-8")
    (search_dir / "index.json").write_text(_json({
        "type": "canonical_entity_index", "count": len(entities), "entities": entities,
    }), encoding="utf-8")

    directory_urls = [f"{site_url}/map/"]
    for key, spec in DIRECTORIES.items():
        directory_entities = tuple(
            item for item in entities if item["kind"] in spec["kinds"]
        )
        directory = output_dir / key
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index.html").write_text(
            render_directory_html(key, directory_entities, site_url, preferred_paths),
            encoding="utf-8",
        )
        (directory / "index.json").write_text(_json({
            "type": "canonical_entity_directory", "directory": key,
            "count": len(directory_entities), "entities": directory_entities,
        }), encoding="utf-8")
        directory_urls.append(f"{site_url}/{key}/")

    changes = tuple(_plain(item) for item in reads.changes())
    changes_dir = output_dir / "changes"
    changes_dir.mkdir(parents=True, exist_ok=True)
    (changes_dir / "index.html").write_text(
        render_changes_html(changes, site_url), encoding="utf-8")
    (changes_dir / "index.json").write_text(_json({
        "type": "canonical_change_history", "operations": changes,
    }), encoding="utf-8")
    directory_urls.append(f"{site_url}/changes/")

    knowledge_dir = output_dir / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    for entity in entities:
        geometry = (reads.route_geometry(entity["entity_id"], as_of)
                    if entity["kind"] == "route" else None)
        geometry_url = None
        if geometry:
            geometry_url = f'/geometry/routes/{entity["entity_id"]}.geojson'
            geometry_path = output_dir / geometry_url.removeprefix("/")
            geometry_path.parent.mkdir(parents=True, exist_ok=True)
            geometry_path.write_text(_json(geometry), encoding="utf-8")
        payload = entity_payload(
            reads, entity["entity_id"], geometry, geometry_url
        )
        page_dir = knowledge_dir / entity["entity_id"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(
            render_entity_html(payload, site_url, entities_by_id), encoding="utf-8")
        (knowledge_dir / f'{entity["entity_id"]}.json').write_text(
            _json(payload), encoding="utf-8")

    destination_dir = output_dir / "destinations" / "del-valle"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = del_valle_destination_payload(reads, as_of)
    (destination_dir / "index.html").write_text(
        render_del_valle_destination_html(destination, site_url), encoding="utf-8")
    (destination_dir / "index.json").write_text(_json(destination), encoding="utf-8")
    trail_dir = output_dir / "trails" / "ohlone-wilderness"
    trail_dir.mkdir(parents=True, exist_ok=True)
    trail = ohlone_trail_payload(reads)
    (trail_dir / "index.html").write_text(
        render_ohlone_trail_html(trail, site_url), encoding="utf-8")
    (trail_dir / "index.json").write_text(_json(trail), encoding="utf-8")
    return {"canonical_entities": len(entities),
            "destination_urls": (f"{site_url}{DEL_VALLE_PATH}",
                                 f"{site_url}{OHLONE_PATH}", *directory_urls)}
