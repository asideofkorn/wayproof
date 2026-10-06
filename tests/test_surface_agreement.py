"""Canonical HTML and JSON must expose the same published claims."""

from __future__ import annotations

import json

import pytest


@pytest.mark.parametrize("relative", (
    "destinations/del-valle",
    "trails/ohlone-wilderness",
))
def test_focused_pages_publish_every_json_claim_id_in_html(generated_site, relative):
    site_root, _ = generated_site
    root = site_root / relative
    payload = json.loads((root / "index.json").read_text())
    html = (root / "index.html").read_text()
    claims = [bundle["claim"] for section in payload["sections"]
              for bundle in section["claims"]]
    assert claims
    assert all(claim["claim_id"] in html for claim in claims)


def test_legacy_trailhead_surfaces_are_not_published(generated_site):
    site_root, _ = generated_site
    assert not (site_root / "trailheads").exists()
