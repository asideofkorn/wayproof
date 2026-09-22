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
PRIMARY_NAV = (
    ("Home", "/"),
    ("Parks", "/parks/"),
    ("Trails", "/trails/"),
    ("Camping", "/camping/"),
    ("Peaks", "/peaks/"),
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
    links = "\n".join(
        f'<a href="{_e(path)}">{_e(label)}</a>' for label, path in PRIMARY_NAV
    )
    return f'<nav aria-label="Primary">\n{links}\n</nav>'


def _page(title: str, description: str, canonical: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<meta name="description" content="{_e(description)}">
<link rel="canonical" href="{_e(canonical)}">
<link rel="stylesheet" href="/style.css">
</head>
<body>
{body}
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


def entity_payload(reads: CanonicalReadService, entity_id: str) -> dict:
    """Build one transport-neutral entity view exclusively through read APIs."""
    entity = reads.entity(entity_id)
    claims = []
    history = list(reads.changes(record_id=entity_id))
    for claim in reads.claims_for(entity_id):
        claims.append(_claim_bundle(reads, claim))
        history.extend(reads.changes(record_id=claim.claim_id, record_type="claim"))
    return _plain({
        "type": "canonical_entity",
        "entity": entity,
        "answerability": (
            "evidence_backed_claims_available" if claims else "no_direct_claims_published"
        ),
        "claims": claims,
        "relationships": reads.relationships_for(entity_id),
        "knowledge_gaps": reads.knowledge_gaps_for(entity_id),
        "history": history,
    })


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
    value = _e(json.dumps(claim["value"], ensure_ascii=False, sort_keys=True))
    sources = []
    observations = {item["source_id"]: item for item in bundle["observations"]}
    for source in bundle["sources"]:
        observation = observations.get(source["source_id"], {})
        checked = observation.get("observed_at") or observation.get("retrieved_at")
        date_text = f" · observed/retrieved {_e(checked)}" if checked else ""
        sources.append(f'<li>{_source_label(source)}{date_text}</li>')
    source_html = "".join(sources) or "<li>No source is attached.</li>"
    return (
        '<article class="card">'
        f'<h3>{_e(claim["predicate"].replace("_", " "))}</h3>'
        f'<p><code>{value}</code></p>'
        f'<p class="meta">Claim <code>{_e(claim["claim_id"])}</code></p>'
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
    body.append('<footer><p class="meta">Wayproof is a planning aid, not a booking or '
                'safety guarantee. Follow linked official sources before acting.</p></footer>')
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
                f'<a href="{OHLONE_PATH}index.json">JSON</a></p></aside>'
                '<footer><p class="meta">Wayproof is a planning aid. '
                'Confirm current conditions with the linked official sources.</p></footer>')
    return _page('Plan the Ohlone Wilderness Trail — Wayproof',
                 'Evidence-backed Ohlone Trail permits, camps, water, access, and route choices.',
                 f'{site_url}{OHLONE_PATH}', "\n".join(body))


def render_entity_html(payload: dict, site_url: str, known_ids: set[str]) -> str:
    entity = payload["entity"]
    claims = payload["claims"]
    gaps = payload["knowledge_gaps"]
    answer = (
        f'{len(claims)} evidence-backed claim(s) are published for this entity.'
        if claims else
        'No direct claim is published for this entity. That absence is not confirmation.'
    )
    body = [
        render_primary_nav(),
        f'<h1>{_e(entity["name"])}</h1>',
        f'<p class="subtitle"><span class="pill">{_e(entity["kind"])}</span> '
        f'<code>{_e(entity["entity_id"])}</code></p>',
        f'<section><h2>Answerability</h2><p>{_e(answer)}</p></section>',
    ]
    if claims:
        body.append(f'<section><h2>Published claims ({len(claims)})</h2>')
        body.extend(_claim_html(bundle) for bundle in claims)
        body.append('</section>')
    if payload["relationships"]:
        body.append('<section><h2>Relationships</h2><ul>')
        for item in payload["relationships"]:
            other = (item["object_id"] if item["subject_id"] == entity["entity_id"]
                     else item["subject_id"])
            label = (f'<a href="/knowledge/{_e(other)}/">{_e(other)}</a>'
                     if other in known_ids else f'<code>{_e(other)}</code>')
            body.append(f'<li>{_e(item["predicate"].replace("_", " "))}: {label}</li>')
        body.append('</ul></section>')
    body.append('<section><h2>Known gaps</h2>')
    if gaps:
        body.append('<ul>' + ''.join(
            f'<li>{_e(item["question"])}'
            f'{" — " + _e(item["reason"]) if item.get("reason") else ""}</li>'
            for item in gaps) + '</ul>')
    else:
        body.append('<p>No explicit knowledge gap is linked to this entity. That does not '
                    'mean the record is complete.</p>')
    body.append('</section>')
    body.append('<section><h2>Published history</h2>')
    if payload["history"]:
        body.append('<ul>' + ''.join(
            f'<li><code>{_e(item["change_set_id"])}</code> — '
            f'{_e(item["action"])} <code>{_e(item["record_id"])}</code>: '
            f'{_e(item["reason"] or item["summary"])}</li>'
            for item in payload["history"]) + '</ul>')
    else:
        body.append('<p>No matching published ChangeSet operation was found.</p>')
    body.append('</section>')
    body.append(
        f'<p class="meta"><a href="/knowledge/{_e(entity["entity_id"])}.json">JSON</a> · '
        'Canonical data is historical evidence, not a guarantee of current conditions. '
        'Recheck volatile facts before travel.</p>'
    )
    return _page(
        f'{entity["name"]} — Wayproof',
        f'Canonical claims, sources, gaps, and history for {entity["name"]}.',
        f'{site_url}/knowledge/{entity["entity_id"]}/',
        "\n".join(body),
    )


def render_search_html(entities: Iterable[dict], site_url: str,
                       preferred_paths: dict[str, str] | None = None) -> str:
    entities = list(entities)
    preferred_paths = preferred_paths or {}
    kinds = sorted({item["kind"] for item in entities})
    rows = "".join(
        f'<li data-search="{_e((item["name"] + " " + item["entity_id"]).casefold())}" '
        f'data-kind="{_e(item["kind"])}">'
        f'<a href="{_e(preferred_paths.get(item["entity_id"], "/knowledge/" + item["entity_id"] + "/"))}">'
        f'{_e(item["name"])}</a> '
        f'<span class="pill">{_e(item["kind"])}</span></li>'
        for item in entities
    )
    options = ''.join(f'<option value="{_e(kind)}">{_e(kind)}</option>' for kind in kinds)
    body = f"""
{render_primary_nav()}
<h1>Canonical search</h1>
<p class="subtitle">Search {len(entities)} published entities. Results link to the
same canonical read service used for provenance and history.</p>
<p><label>Search <input id="entity-search" type="search" placeholder="Del Valle or Ohlone"></label>
<label>Type <select id="entity-kind"><option value="">All types</option>{options}</select></label></p>
<p id="result-count" class="meta">{len(entities)} results</p>
<ul id="entity-results" class="plain">{rows}</ul>
<noscript><p>All entities are listed above; browser filtering requires JavaScript.</p></noscript>
<script>
const query = document.getElementById('entity-search');
const kind = document.getElementById('entity-kind');
const rows = [...document.querySelectorAll('#entity-results li')];
function filterEntities() {{
  const needle = query.value.trim().toLocaleLowerCase();
  let visible = 0;
  for (const row of rows) {{
    const show = (!needle || row.dataset.search.includes(needle)) &&
                 (!kind.value || row.dataset.kind === kind.value);
    row.hidden = !show;
    if (show) visible += 1;
  }}
  document.getElementById('result-count').textContent = `${{visible}} results`;
}}
query.addEventListener('input', filterEntities);
kind.addEventListener('change', filterEntities);
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
    groups: dict[str, list[dict]] = {}
    for entity in entities:
        groups.setdefault(entity["kind"], []).append(entity)
    sections = []
    for kind, items in sorted(groups.items()):
        rows = "".join(
            '<li class="card">'
            f'<a href="{_e(preferred_paths.get(item["entity_id"], "/knowledge/" + item["entity_id"] + "/"))}">'
            f'<strong>{_e(item["name"])}</strong></a>'
            f'<div class="meta">{_e(_human_label(item["kind"]))}</div></li>'
            for item in items
        )
        sections.append(
            f'<section><h2>{_e(_human_label(kind))} ({len(items)})</h2>'
            f'<ul class="plain">{rows}</ul></section>'
        )
    body = (
        render_primary_nav()
        + f'<header class="page-header"><h1>{_e(spec["title"])}</h1>'
        + f'<p class="tagline">{_e(spec["description"])}</p>'
        + f'<p class="meta">{len(entities)} published records</p></header>'
        + "".join(sections)
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
            '<article class="card">'
            f'<h2><code>{_e(change_set_id)}</code></h2>'
            f'<p>{_e(group["summary"])}</p>'
            f'<details><summary>{len(operations)} published operations</summary>'
            f'<ul>{rows}</ul></details></article>'
        )
    body = (
        render_primary_nav()
        + '<header class="page-header"><h1>Published changes</h1>'
        + '<p class="tagline">See when canonical knowledge was added, replaced, or removed. '
          'Current snapshots stay concise while ChangeSets preserve the public history.</p>'
        + f'<p class="meta">{len(grouped)} published ChangeSets</p></header>'
        + "".join(articles)
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
    known_ids = {item["entity_id"] for item in entities}
    preferred_paths = {DEL_VALLE_ID: DEL_VALLE_PATH, OHLONE_ID: OHLONE_PATH}
    search_dir = output_dir / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    (search_dir / "index.html").write_text(render_search_html(
        entities, site_url, preferred_paths),
        encoding="utf-8")
    (search_dir / "index.json").write_text(_json({
        "type": "canonical_entity_index", "count": len(entities), "entities": entities,
    }), encoding="utf-8")

    directory_urls = []
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
        payload = entity_payload(reads, entity["entity_id"])
        page_dir = knowledge_dir / entity["entity_id"]
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(
            render_entity_html(payload, site_url, known_ids), encoding="utf-8")
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
