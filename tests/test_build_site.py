"""Tests for scripts/build_site.py's static site generation.

scripts/ isn't a package, so the module is loaded by file path rather than
imported normally (same pattern as tests/test_split_collections.py).

Run with:  python -m pytest tests/test_build_site.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_spec = importlib.util.spec_from_file_location(
    "build_site", os.path.join(ROOT, "scripts", "build_site.py")
)
build_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_site)


def _build(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        return build_site.build(tmp_path)
    finally:
        os.chdir(original_cwd)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    output = tmp_path_factory.mktemp("site")
    return output, _build(output)


def test_build_writes_index_and_cname(site):
    tmp_path, stats = site

    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "CNAME").read_text().strip() == "wayproof.dev"
    assert (tmp_path / "style.css").exists()
    # The real dataset has known unconfirmed items (see wayproof/reports.py's
    # open_questions()); a build against it should surface at least one.
    assert stats["open_questions"] > 0

    index_html = (tmp_path / "index.html").read_text()
    assert f"({stats['open_questions']} open)" in index_html
    assert "github.com/asideofkorn/wayproof/issues/new" in index_html
    assert 'href="/destinations/del-valle/"' in index_html


def test_build_writes_three_representations_per_trailhead(site):
    tmp_path, stats = site
    trailheads = tmp_path / "trailheads"

    assert stats["trailheads"] > 0
    assert (trailheads / "index.html").exists()
    assert (trailheads / "index.json").exists()

    # Whitney Portal is the richest real example: a lottery permit plus a
    # sourced route-level exception (Mount Russell) that doesn't inherit it.
    assert (trailheads / "whitney-portal" / "index.html").exists()
    markdown = (trailheads / "whitney-portal.md").read_text()
    structured = json.loads((trailheads / "whitney-portal.json").read_text())

    assert "Mount Russell" in markdown
    assert structured["permit"]["permit_group"] == "whitney_zone"
    assert structured["peaks_nearby"]["verified"] is False

    pages = list(trailheads.glob("*/index.html"))
    assert len(pages) == stats["trailheads"]


def test_build_writes_sitemap_and_robots(site):
    tmp_path, stats = site
    sitemap = (tmp_path / "sitemap.xml").read_text()

    assert sitemap.count("<loc>") == stats["indexed_urls"]
    assert "https://wayproof.dev/trailheads/whitney-portal/" in sitemap
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
    assert "Published claims" in page
    assert "Evidence and sources" in page
    assert "Published history" in page
    assert "Known gaps" in page


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
    assert "Why Wayproof says this" in page
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
    assert "Recheck state: required" in page
    assert "What fire restrictions apply for the planned trip date?" in page
    assert "Reservation window" in page
    assert "Ohlone Wilderness Trail" in page


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
    for heading in ("Permits, reservations, and parking", "Route, access, and distance",
                    "Camps and water", "Route choices and detours"):
        assert heading in page
    assert "Why Wayproof says this" in page
    assert "https://wayproof.dev/trails/ohlone-wilderness/" in (
        tmp_path / "sitemap.xml").read_text()


def test_primary_navigation_connects_every_public_page_type(site):
    tmp_path, _ = site
    pages = (
        tmp_path / "index.html",
        tmp_path / "search" / "index.html",
        tmp_path / "destinations" / "del-valle" / "index.html",
        tmp_path / "knowledge" / "trail-ohlone-wilderness" / "index.html",
        tmp_path / "trailheads" / "index.html",
        tmp_path / "trailheads" / "whitney-portal" / "index.html",
    )
    expected_links = {
        'href="/"',
        'href="/search/"',
        'href="/destinations/del-valle/"',
        'href="/trailheads/"',
    }

    for page in pages:
        html = page.read_text()
        missing = expected_links.difference(
            link for link in expected_links if link in html
        )
        assert not missing, f"{page.relative_to(tmp_path)} lacks {sorted(missing)}"


def test_issue_url_is_prefilled_and_escaped():
    url = build_site._issue_url(
        "data/peaks.csv", "Mount Carillon", "Isn't in the dataset at all",
    )
    assert url.startswith("https://github.com/asideofkorn/wayproof/issues/new?")
    assert "title=%5Bdata%5D%20Mount%20Carillon" in url
    assert "labels=data" in url
    # The apostrophe in the question must be percent-encoded, not raw --
    # otherwise it isn't a valid URL query value.
    assert "Isn't" not in url
    assert "Isn%27t" in url


def test_no_open_questions_renders_a_friendly_placeholder():
    html_out = build_site._render_questions_html([])
    assert "No open questions on file" in html_out
