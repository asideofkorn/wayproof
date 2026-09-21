#!/usr/bin/env python3
"""Build the static wayproof.dev site.

Generates, from the committed dataset on every build:

- a landing page whose research queue comes from canonical knowledge gaps;
- canonical entity search and evidence/history detail pages backed only by
  ``CanonicalReadService``;
- ``sitemap.xml`` and ``robots.txt``.

Usage
-----
    python scripts/build_site.py --output _site
"""

from __future__ import annotations

import argparse
import datetime
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wayproof.canonical_site import build_canonical_site
from wayproof.render import (
    STYLESHEET,
    render_robots,
    render_sitemap,
)
from wayproof.read_service import CanonicalReadService
from wayproof.views import SITE_URL

REPO = "asideofkorn/wayproof"

def _render_gaps_html(gaps) -> str:
    if not gaps:
        return "<p>No canonical knowledge gaps are published right now.</p>"
    items = []
    for gap in gaps:
        links = ", ".join(
            f'<a href="/knowledge/{html.escape(item)}/">{html.escape(item)}</a>'
            for item in gap.related_ids
        ) or "no related canonical record"
        items.append(
            '<li class="card">'
            f'<div>{html.escape(gap.question)}</div>'
            f'<div class="meta"><code>{html.escape(gap.gap_id)}</code> · {links}</div>'
            "</li>"
        )
    return f'<ul class="plain" style="list-style:none;padding:0">{"".join(items)}</ul>'


LANDING_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wayproof -- Source-Backed Permit &amp; Access Logistics for the Sierra Nevada</title>
<meta name="description" content="Which permit governs your objective, when reservations
open, what it costs, and what source says so. Sierra Nevada first, open source, every
fact dated.">
<link rel="canonical" href="{site}/">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<h1>Wayproof</h1>
<p class="tagline">Open-source, source-backed logistics for hiking, trail running,
backpacking, and mountaineering. Sierra Nevada first, designed to expand to
U.S. public lands.</p>

<p class="lede">Which permit governs your objective, when its reservations open,
what it costs, and which source says so &mdash; every fact dated, and the
uncertain ones labelled rather than guessed.</p>

<nav aria-label="Primary">
  <a href="/">Home</a>
  <a href="/search/">Canonical search</a>
  <a href="/destinations/del-valle/">Del Valle</a>
  <a href="/trails/ohlone-wilderness/">Ohlone Trail</a>
  <a href="https://github.com/{repo}">GitHub</a>
  <a href="https://github.com/{repo}#readme">Docs</a>
  <a href="https://github.com/{repo}/issues/new?template=data_report.md&labels=data">Submit a report</a>
</nav>

<section>
  <h2>Search canonical knowledge</h2>
  <p>Search {canonical_entity_count} published places, routes, campsites, water
  sources, and other entities. Each detail page distinguishes supported claims,
  known gaps, source evidence, and published ChangeSet history.</p>
  <p><a href="/search/">Search canonical knowledge &rarr;</a></p>
  <p><a href="/destinations/del-valle/">Plan Del Valle Regional Park &rarr;</a></p>
  <p><a href="/trails/ohlone-wilderness/">Plan the Ohlone Wilderness Trail &rarr;</a></p>
</section>

<section>
  <h2>Canonical knowledge gaps ({gap_count} open)</h2>
  <p>These questions are published canonical gaps, not inferred from missing
  fields or copied from the legacy research corpus.</p>
  {gaps_html}
</section>

<footer>
  <p>Built from <a href="https://github.com/{repo}">{repo}</a>'s own dataset.</p>
  <p class="meta">Planning aid, not a booking guarantee -- verify the current rule at
  the official source before acting on any date here.</p>
</footer>
</body>
</html>
"""

def build(output_dir: Path, today: datetime.date | None = None) -> dict:
    today = today or datetime.date.today()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "style.css").write_text(STYLESHEET)
    # Baked into the deployed artifact (not just set in repo Settings) so the
    # custom domain survives every GitHub Actions Pages deployment.
    (output_dir / "CNAME").write_text("wayproof.dev\n")

    canonical_reads = CanonicalReadService(Path("."))
    canonical_stats = build_canonical_site(canonical_reads, output_dir, SITE_URL, today)
    gaps = canonical_reads.knowledge_gaps()

    (output_dir / "index.html").write_text(LANDING_TEMPLATE.format(
        site=SITE_URL, repo=REPO, gap_count=len(gaps),
        gaps_html=_render_gaps_html(gaps),
        canonical_entity_count=canonical_stats["canonical_entities"],
    ))

    canonical_entities = canonical_reads.search_entities()
    urls = [f"{SITE_URL}/", f"{SITE_URL}/search/"]
    urls += [f"{SITE_URL}/knowledge/{item.entity_id}/" for item in canonical_entities]
    urls += list(canonical_stats["destination_urls"])
    (output_dir / "sitemap.xml").write_text(render_sitemap(urls))
    (output_dir / "robots.txt").write_text(render_robots())

    return {"knowledge_gaps": len(gaps), "indexed_urls": len(urls), "canonical_entities":
            canonical_stats["canonical_entities"]}


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--output", default="_site", help="Output directory (default _site)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    stats = build(Path(args.output))
    print(f"Built site into {args.output}/: "
          f"{stats['canonical_entities']} canonical entity pages, "
          f"{stats['knowledge_gaps']} canonical knowledge gaps, "
          f"{stats['indexed_urls']} URLs in sitemap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
