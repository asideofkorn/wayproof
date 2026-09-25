"""Tests for scripts/build_site.py's static site generation.

scripts/ isn't a package, so the module is loaded by file path rather than
imported normally (same pattern as tests/test_split_collections.py).

Run with:  python -m pytest tests/test_build_site.py
"""

from __future__ import annotations

import json
import os

import pytest
from scripts import build_site

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def site(generated_site):
    return generated_site


def test_build_writes_index_and_cname(site):
    tmp_path, stats = site

    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "CNAME").read_text().strip() == "wayproof.dev"
    assert (tmp_path / "style.css").exists()
    assert stats["knowledge_gaps"] > 0

    index_html = (tmp_path / "index.html").read_text()
    assert f"<strong>{stats['knowledge_gaps']}</strong> explicit open questions" in index_html
    assert "Questions that remain open" in index_html
    assert 'href="/destinations/del-valle/"' in index_html
    assert "Know what applies before you go." in index_html
    assert "Browse the planning graph" in index_html
    assert "A fact is useful only when its limits are visible." in index_html
    assert 'href="/how-it-works/"' in index_html


def test_how_wayproof_works_explains_the_model_and_comparison(site):
    tmp_path, _ = site
    page = (tmp_path / "how-it-works" / "index.html").read_text()

    for text in (
        "From sources to decisions",
        "Source",
        "Observation",
        "Evidence",
        "Claim",
        "Proximity is not access.",
        "Traditional wiki",
        "Basic knowledge graph",
        "Wayproof claims model",
        "Two kinds of history",
        "Agents can propose knowledge. They cannot publish it directly.",
    ):
        assert text in page
    assert 'href="/knowledge/campsite-east-fork-126/"' in page
    assert 'class="comparison-table"' in page
    assert 'class="model-flow' in page
    assert "https://wayproof.dev/how-it-works/" in (
        tmp_path / "sitemap.xml"
    ).read_text()


def test_build_publishes_no_legacy_trailhead_pages(site):
    tmp_path, _ = site
    assert not (tmp_path / "trailheads").exists()


def test_build_writes_sitemap_and_robots(site):
    tmp_path, stats = site
    sitemap = (tmp_path / "sitemap.xml").read_text()

    assert sitemap.count("<loc>") == stats["indexed_urls"]
    assert "/trailheads/" not in sitemap
    assert "Sitemap: https://wayproof.dev/sitemap.xml" in (tmp_path / "robots.txt").read_text()


def test_build_writes_canonical_search_from_read_service(site):
    tmp_path, stats = site
    search = json.loads((tmp_path / "search" / "index.json").read_text())

    assert stats["canonical_entities"] == search["count"]
    assert stats["canonical_entities"] > 0
    assert any(item["entity_id"] == "park-del-valle-regional-park"
               for item in search["entities"])

    page = (tmp_path / "search" / "index.html").read_text()
    assert "Canonical search" in page
    assert "Del Valle Regional Park" in page
    assert 'id="entity-search"' in page


def test_del_valle_canonical_page_exposes_claims_sources_gaps_and_history(site):
    tmp_path, _ = site
    knowledge = tmp_path / "knowledge"
    payload = json.loads(
        (knowledge / "park-del-valle-regional-park.json").read_text()
    )
    page = (knowledge / "park-del-valle-regional-park" / "index.html").read_text()

    assert payload["answerability"] == "evidence_backed_claims_available"
    assert payload["claims"]
    assert any(bundle["sources"] for bundle in payload["claims"])
    assert payload["history"]
    assert "Plan a visit" in page
    assert "Explore related places" in page
    assert "Before you go" in page
    assert "Sources, evidence, and history" in page
    assert "Published ChangeSet history" in page


def test_generic_entity_pages_use_the_human_planning_hierarchy(site):
    tmp_path, _ = site
    representatives = {
        "peak-mount-whitney": ("Mount Whitney", "Routes and geography"),
        "park-lassen-volcanic-national-park": ("Lassen Volcanic National Park", "Getting there"),
        "park-yosemite-national-park": ("Yosemite National Park", "Requirements and current conditions"),
        "campground-yosemite-upper-pines": ("Upper Pines Campground", "Facilities and services"),
    }
    for entity_id, (name, expected_group) in representatives.items():
        page = (tmp_path / "knowledge" / entity_id / "index.html").read_text()
        assert name in page
        assert "Plan a visit" in page
        assert "Explore related places" in page
        assert "Before you go" in page
        assert "Sources, evidence, and history" in page
        assert expected_group in page


def test_cinder_cone_route_publishes_a_reproducible_human_map(site):
    tmp_path, _ = site
    entity_id = "route-cinder-cone-trail"
    page = (tmp_path / "knowledge" / entity_id / "index.html").read_text()
    payload = json.loads((tmp_path / "knowledge" / f"{entity_id}.json").read_text())
    geometry_path = tmp_path / "geometry" / "routes" / f"{entity_id}.geojson"
    geometry = json.loads(geometry_path.read_text())

    assert "Route map" in page
    assert "Simplified route diagram" not in page
    assert "<svg" not in page
    assert "planning evidence, not navigation-grade mapping" in page
    assert f'/geometry/routes/{entity_id}.geojson' in page
    assert payload["route_geometry_url"] == f"/geometry/routes/{entity_id}.geojson"
    assert payload["route_geometry"] == geometry
    assert len(geometry["features"]) == 3
    assert geometry["wayproof"]["navigation_grade"] is False


def test_route_geometry_adds_the_interactive_map(site):
    tmp_path, _ = site
    page = (
        tmp_path / "knowledge" / "route-cinder-cone-trail" / "index.html"
    ).read_text()

    assert 'data-interactive-route-map' in page
    assert 'data-geometry-url="/geometry/routes/route-cinder-cone-trail.geojson"' in page
    assert 'data-basemap="topo" aria-pressed="true"' in page
    assert 'data-basemap="aerial" aria-pressed="false"' in page
    assert 'data-basemap="aerial-labels" aria-pressed="false"' in page
    assert "Interactive map loads when scrolled into view." in page
    assert 'src="/assets/route-map.js?v=20260925-1"' in page
    assert 'href="/assets/vendor/maplibre/maplibre-gl.css"' in page

    for asset in (
        "route-map.js",
        "vendor/maplibre/maplibre-gl.css",
        "vendor/maplibre/maplibre-gl.mjs",
        "vendor/maplibre/maplibre-gl-shared.mjs",
        "vendor/maplibre/maplibre-gl-worker.mjs",
        "vendor/maplibre/LICENSE.txt",
    ):
        assert (tmp_path / "assets" / asset).is_file()


def test_interactive_map_is_available_for_every_route_with_geometry(site):
    tmp_path, _ = site
    for geometry_path in (tmp_path / "geometry" / "routes").glob("*.geojson"):
        route_id = geometry_path.stem
        page = (tmp_path / "knowledge" / route_id / "index.html").read_text()
        assert 'data-interactive-route-map' in page
        assert f'data-geometry-url="/geometry/routes/{route_id}.geojson"' in page
        assert 'src="/assets/route-map.js?v=20260925-1"' in page
        assert 'href="/assets/vendor/maplibre/maplibre-gl.css"' in page


def test_route_without_geometry_does_not_load_map_assets(site):
    tmp_path, _ = site
    page = (
        tmp_path / "knowledge" / "route-brokeoff-mountain-trail" / "index.html"
    ).read_text()

    assert "data-interactive-route-map" not in page
    assert 'src="/assets/route-map.js' not in page
    assert 'href="/assets/vendor/maplibre/maplibre-gl.css"' not in page


def test_interactive_map_asset_is_lazy_and_links_canonical_segments(site):
    tmp_path, _ = site
    script = (tmp_path / "assets" / "route-map.js").read_text()

    assert "IntersectionObserver" in script
    assert "await import(" in script
    assert "{ default: maplibregl }" not in script
    assert "maplibregl.supported" not in script
    assert "Downloadable route GeoJSON remains available below." in script
    assert "encodeURIComponent(segmentId)" in script
    assert 'map.on("click", "wayproof-route"' in script


def test_explore_map_is_generated_from_canonical_geometry(site):
    tmp_path, _ = site
    page = (tmp_path / "map" / "index.html").read_text()
    payload = json.loads((tmp_path / "map" / "features.geojson").read_text())

    assert 'data-explore-map' in page
    assert 'data-map-layer="routes"' in page
    assert 'data-map-layer="camping"' in page
    assert 'data-map-layer="camping"  >' in page
    assert 'data-map-layer="boundaries" checked' in page
    assert 'data-map-expand aria-expanded="false"' in page
    assert 'href="/map/features.geojson"' in page
    assert 'src="/assets/explore-map.js?v=20260925-2"' in page
    assert payload["wayproof"]["generated_from"] == "CanonicalReadService"
    assert payload["wayproof"]["navigation_grade"] is False
    assert any(item["properties"]["entity_id"] == "route-cinder-cone-trail"
               and item["properties"]["layer"] == "routes"
               for item in payload["features"])
    assert any(item["properties"]["entity_id"] == "campground-east-fork-inyo"
               and item["geometry"]["type"] == "Point"
               for item in payload["features"])
    assert all(item["geometry"]["type"] in {"Polygon", "MultiPolygon"}
               for item in payload["features"]
               if item["properties"]["layer"] == "boundaries")
    boundaries = [item for item in payload["features"]
                  if item["properties"]["layer"] == "boundaries"]
    assert len(boundaries) == 73
    assert any(item["properties"]["entity_id"] == "park-del-valle-regional-park"
               for item in boundaries)


def test_explore_map_assets_support_layers_selection_and_mobile_expansion(site):
    tmp_path, _ = site
    script = (tmp_path / "assets" / "explore-map.js").read_text()
    stylesheet = (tmp_path / "style.css").read_text()

    assert "queryRenderedFeatures" in script
    assert "data-map-layer" in script
    assert '"geometry-type"' in script
    assert 'id: "wp-routes-casing"' in script
    assert '"line-cap": "round"' in script
    assert '"line-join": "round"' in script
    assert "is-expanded" in script
    assert "Close full screen" in script
    assert ".explore-map-shell.is-expanded" in stylesheet
    assert "env(safe-area-inset-top)" in stylesheet


def test_primary_navigation_links_the_explore_map(site):
    tmp_path, _ = site
    for path in (tmp_path / "index.html", tmp_path / "search" / "index.html",
                 tmp_path / "knowledge" / "peak-mount-whitney" / "index.html"):
        assert '<a href="/map/">Map</a>' in path.read_text()


def test_relationships_show_human_names_instead_of_only_record_ids(site):
    tmp_path, _ = site
    page = (tmp_path / "knowledge" / "peak-mount-whitney" / "index.html").read_text()

    assert "Sequoia National Park" in page
    assert "High Sierra Trail" in page
    assert "Access and approaches" in page
    assert "Land and management" in page


def test_claim_linked_gaps_surface_on_the_entity_page(site):
    tmp_path, _ = site
    payload = json.loads(
        (tmp_path / "knowledge" / "peak-mount-whitney.json").read_text()
    )
    page = (tmp_path / "knowledge" / "peak-mount-whitney" / "index.html").read_text()

    gap_ids = {item["gap_id"] for item in payload["knowledge_gaps"]}
    assert "gap-whitney-published-elevation-conflict" in gap_ids
    assert "gap-whitney-current-conditions" in gap_ids
    assert "Which published Mount Whitney elevation should a consumer display?" in page


def test_large_related_inventories_are_progressively_disclosed(site):
    tmp_path, _ = site
    page = (tmp_path / "knowledge" / "campground-yosemite-upper-pines" /
            "index.html").read_text()

    assert 'class="related-more"' in page
    assert "Show 227 more" in page


def test_ohlone_search_opens_trail_page_with_canonical_detail_link(site):
    tmp_path, _ = site
    page = (tmp_path / "search" / "index.html").read_text()
    assert "/trails/ohlone-wilderness/" in page
    assert (tmp_path / "knowledge" / "trail-ohlone-wilderness" / "index.html").exists()
    trail = (tmp_path / "trails" / "ohlone-wilderness" / "index.html").read_text()
    assert "/knowledge/trail-ohlone-wilderness/" in trail


def test_del_valle_search_opens_the_outcome_focused_destination(site):
    tmp_path, _ = site
    search = (tmp_path / "search" / "index.html").read_text()
    assert ('href="/destinations/del-valle/">Del Valle Regional Park</a>'
            in search)

    page = (tmp_path / "destinations" / "del-valle" / "index.html").read_text()
    for heading in (
        "Check before you go",
        "Getting there and entering",
        "Camping",
        "Swimming, boating, and lake conditions",
        "Ohlone Wilderness Trail",
    ):
        assert heading in page
    assert "Sources and details" in page
    assert "At a glance" in page
    assert 'class="summary-grid"' in page
    assert "Canonical record" in page


def test_del_valle_destination_projects_recheck_and_readable_claims(site):
    tmp_path, _ = site
    payload = json.loads(
        (tmp_path / "destinations" / "del-valle" / "index.json").read_text()
    )
    assert payload["entity"]["entity_id"] == "park-del-valle-regional-park"
    assert payload["recheck"]["state"] == "required"
    answerability = {item["result"]["answerability"]
                     for item in payload["recheck"]["items"]}
    assert {"answered", "needs_current_check", "unknown"} <= answerability
    assert any(item["entity"]["entity_id"] == "trail-ohlone-wilderness"
               for item in payload["related"])

    page = (tmp_path / "destinations" / "del-valle" / "index.html").read_text()
    assert "Recheck required" in page
    assert "questions Wayproof cannot currently answer" in page
    assert "What fire restrictions apply for the planned trip date?" in page
    assert "Book a campsite" in page
    assert "Ohlone Wilderness Trail" in page
    assert "complete Ohlone Trail guide" in page
    assert "ordered backpack camp inventory" not in page.lower()


def test_del_valle_destination_is_in_the_sitemap(site):
    tmp_path, _ = site
    sitemap = (tmp_path / "sitemap.xml").read_text()
    assert "https://wayproof.dev/destinations/del-valle/" in sitemap


def test_ohlone_trail_page_uses_canonical_route_evidence(site):
    tmp_path, _ = site
    payload = json.loads((tmp_path / "trails" / "ohlone-wilderness" /
                          "index.json").read_text())
    assert payload["entity"]["entity_id"] == "trail-ohlone-wilderness"
    assert len(payload["route_results"]) == 3
    page = (tmp_path / "trails" / "ohlone-wilderness" / "index.html").read_text()
    for heading in ("Permits, reservations, and parking", "Western access at Mission Peak",
                    "Route, access, and distance", "Camps and water",
                    "Route choices and detours"):
        assert heading in page
    for place in ("Mission Peak Regional Preserve", "Mission Peak Stanford Avenue Staging Area",
                  "Mission Peak Ohlone College Entrance",
                  "Mission Peak Anza–Pine Walk-In Entrance"):
        assert place in page
    assert "Parking and access choices" in page
    assert "Choose your endpoint" in page
    assert "Sources and details" in page
    assert "https://wayproof.dev/trails/ohlone-wilderness/" in (
        tmp_path / "sitemap.xml").read_text()


def test_primary_navigation_connects_every_public_page_type(site):
    tmp_path, _ = site
    pages = (
        tmp_path / "index.html",
        tmp_path / "search" / "index.html",
        tmp_path / "destinations" / "del-valle" / "index.html",
        tmp_path / "knowledge" / "trail-ohlone-wilderness" / "index.html",
        tmp_path / "trails" / "ohlone-wilderness" / "index.html",
        tmp_path / "parks" / "index.html",
        tmp_path / "trails" / "index.html",
        tmp_path / "camping" / "index.html",
        tmp_path / "peaks" / "index.html",
        tmp_path / "changes" / "index.html",
        tmp_path / "how-it-works" / "index.html",
    )
    expected_links = {
        'href="/"',
        'href="/search/"',
        'href="/parks/"',
        'href="/trails/"',
        'href="/camping/"',
        'href="/peaks/"',
        'href="/changes/"',
        'href="/how-it-works/"',
    }

    for page in pages:
        html = page.read_text()
        missing = expected_links.difference(
            link for link in expected_links if link in html
        )
        assert not missing, f"{page.relative_to(tmp_path)} lacks {sorted(missing)}"


def test_every_canonical_page_uses_the_shared_site_shell(site):
    tmp_path, _ = site
    for page in (
        tmp_path / "search" / "index.html",
        tmp_path / "parks" / "index.html",
        tmp_path / "changes" / "index.html",
        tmp_path / "how-it-works" / "index.html",
        tmp_path / "knowledge" / "peak-mount-whitney" / "index.html",
    ):
        html = page.read_text()
        assert 'class="site-nav"' in html
        assert 'class="site-brand"' in html
        assert 'class="site-footer"' in html


def test_search_and_directories_have_task_focused_filters(site):
    tmp_path, _ = site
    search = (tmp_path / "search" / "index.html").read_text()
    parks = (tmp_path / "parks" / "index.html").read_text()

    assert "Find a place, route, or campsite" in search
    assert 'class="search-controls"' in search
    assert 'id="entity-search-form"' in search
    assert 'type="submit">Search</button>' in search
    assert 'aria-live="polite"' in search
    assert 'id="no-results"' in search
    assert "const hasCriteria = Boolean(needle || kind.value)" in search
    assert "const show = hasCriteria" in search
    assert "Enter a name or choose a type to search." in search
    assert "event.key === 'Enter'" in search
    assert "form.requestSubmit()" in search
    assert "form.addEventListener('submit'" in search
    assert 'class="result-grid"' in search
    assert "[hidden] { display:none !important; }" in (tmp_path / "style.css").read_text()
    assert 'id="directory-search"' in parks
    assert 'id="directory-kind"' in parks
    assert 'class="directory-grid"' in parks


def test_changes_page_uses_readable_history_cards(site):
    tmp_path, _ = site
    page = (tmp_path / "changes" / "index.html").read_text()

    assert "What changed, and why" in page
    assert 'class="change-list"' in page
    assert 'class="change-card"' in page


def test_directories_are_automatically_populated_from_canonical_kinds(site):
    tmp_path, _ = site
    expectations = {
        "parks": ("park", "Del Valle Regional Park"),
        "trails": ("trail", "Ohlone Wilderness Trail"),
        "camping": ("family_campsite", "001"),
        "peaks": ("peak", "Rose Peak"),
    }
    for directory, (kind, name) in expectations.items():
        payload = json.loads((tmp_path / directory / "index.json").read_text())
        assert payload["count"] > 0
        assert any(item["kind"] == kind and item["name"] == name
                   for item in payload["entities"])
        assert name in (tmp_path / directory / "index.html").read_text()


def test_deep_campground_records_publish_without_handwritten_pages(site):
    tmp_path, _ = site
    payload = json.loads((tmp_path / "camping" / "index.json").read_text())
    names = {item["name"] for item in payload["entities"]}

    assert "Anthony Chabot Family Campground" in names
    assert "Dumbarton Quarry Campground" in names
    assert (
        tmp_path / "knowledge" / "campground-anthony-chabot-family" / "index.html"
    ).exists()
    assert (
        tmp_path / "knowledge" / "campground-dumbarton-quarry" / "index.html"
    ).exists()


def test_group_camps_automatically_join_camping_navigation(site):
    tmp_path, _ = site
    payload = json.loads((tmp_path / "camping" / "index.json").read_text())
    names = {item["name"] for item in payload["entities"]}

    assert "Arroyo Flats Group Camp" in names
    assert "Las Trampas Corral Area Group Camp" in names
    assert (
        tmp_path / "knowledge" / "group-camp-garin-arroyo-flats" / "index.html"
    ).exists()
    assert (
        tmp_path / "knowledge" / "group-camp-las-trampas-corral" / "index.html"
    ).exists()


def test_more_group_camps_publish_without_handwritten_routes(site):
    tmp_path, _ = site
    payload = json.loads((tmp_path / "camping" / "index.json").read_text())
    names = {item["name"] for item in payload["entities"]}

    expected = {
        "Dairy Glen Group Camp",
        "Trails End Group Camp",
        "Fern Dell Group Camp",
        "Girls Camp Group Camp",
    }
    assert expected <= names
    for entity_id in (
        "group-camp-coyote-hills-dairy-glen",
        "group-camp-reinhardt-redwood-trails-end",
        "group-camp-reinhardt-redwood-fern-dell",
        "group-camp-reinhardt-redwood-girls-camp",
    ):
        assert (tmp_path / "knowledge" / entity_id / "index.html").exists()


def test_briones_and_point_pinole_group_camps_publish_automatically(site):
    tmp_path, _ = site
    payload = json.loads((tmp_path / "camping" / "index.json").read_text())
    names = {item["name"] for item in payload["entities"]}

    expected = {
        "Homestead Valley Group Camp",
        "Maud Whalen Group Camp",
        "Wee-Ta-Chi Group Camp",
        "Point Pinole Group Camp",
    }
    assert expected <= names
    for entity_id in (
        "group-camp-briones-homestead-valley",
        "group-camp-briones-maud-whalen",
        "group-camp-briones-wee-ta-chi",
        "group-camp-point-pinole-overnight",
    ):
        assert (tmp_path / "knowledge" / entity_id / "index.html").exists()


def test_tilden_and_sibley_camps_publish_automatically(site):
    tmp_path, _ = site
    payload = json.loads((tmp_path / "camping" / "index.json").read_text())
    names = {item["name"] for item in payload["entities"]}
    expected = {
        "New Woodland Group Camp",
        "Wildcat View Group Camp",
        "Gillespie Group Camp",
        "ES Anderson Equestrian Camp",
        "Sibley Backpack Camp",
    }
    assert expected <= names
    for entity_id in (
        "group-camp-tilden-new-woodland",
        "group-camp-tilden-wildcat-view",
        "group-camp-tilden-gillespie",
        "equestrian-camp-tilden-es-anderson",
        "backpack-camp-sibley",
    ):
        assert (tmp_path / "knowledge" / entity_id / "index.html").exists()


def test_remaining_reservable_park_camps_publish_automatically(site):
    tmp_path, _ = site
    payload = json.loads((tmp_path / "camping" / "index.json").read_text())
    names = {item["name"] for item in payload["entities"]}
    expected = {"Star Mine Group Camp", "Stewartville Backpack Camp", "Morgan Territory Backpack Camp", "Round Valley Backpack Camp"}
    assert expected <= names


def test_changes_page_exposes_public_changeset_history(site):
    tmp_path, _ = site
    payload = json.loads((tmp_path / "changes" / "index.json").read_text())
    page = (tmp_path / "changes" / "index.html").read_text()
    assert payload["operations"]
    assert "Published changes" in page
    assert "wp-20260921-ebrpd-parks-batch-15" in page


def test_directory_pages_are_in_the_sitemap(site):
    tmp_path, _ = site
    sitemap = (tmp_path / "sitemap.xml").read_text()
    for path in ("parks", "trails", "camping", "peaks", "changes"):
        assert f"https://wayproof.dev/{path}/" in sitemap


def test_no_canonical_gaps_renders_a_friendly_placeholder():
    assert "No canonical knowledge gaps" in build_site._render_gaps_html([])
