"""Canonical HTML and JSON must expose the same published claims."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("canonical-site")
    subprocess.run([sys.executable, "scripts/build_site.py", "--output", str(out)],
                   cwd=ROOT, check=True, capture_output=True)
    return out


@pytest.mark.parametrize("relative", (
    "destinations/del-valle",
    "trails/ohlone-wilderness",
))
def test_focused_pages_publish_every_json_claim_id_in_html(site, relative):
    root = site / relative
    payload = json.loads((root / "index.json").read_text())
    html = (root / "index.html").read_text()
    claims = [bundle["claim"] for section in payload["sections"]
              for bundle in section["claims"]]
    assert claims
    assert all(claim["claim_id"] in html for claim in claims)


def test_legacy_trailhead_surfaces_are_not_published(site):
    assert not (site / "trailheads").exists()
