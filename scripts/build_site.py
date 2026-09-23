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

from wayproof.canonical_site import build_canonical_site, render_primary_nav
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
    visible = "".join(items[:6])
    remaining = "".join(items[6:])
    more = (f'<details><summary>Show {len(items) - 6} more open questions</summary>'
            f'<ul class="gap-grid">{remaining}</ul></details>' if remaining else "")
    return f'<ul class="gap-grid">{visible}</ul>{more}'


LANDING_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wayproof &mdash; Source-Backed Outdoor Planning</title>
<meta name="description" content="Source-backed outdoor planning for permits, access,
routes, camps, facilities, and current-condition rechecks. Every answer traceable.">
<link rel="canonical" href="{site}/">
<link rel="stylesheet" href="/style.css">
</head>
<body>
{primary_nav}

<header class="home-hero">
  <span class="eyebrow">Plan from evidence, not folklore</span>
  <h1>Know what applies before you go.</h1>
  <p class="tagline">Wayproof connects outdoor objectives to permits, access,
  routes, camps, facilities, and current-condition rechecks&mdash;with every
  answer traceable to a source.</p>
  <div class="hero-actions"><a class="button primary" href="/search/">Search Wayproof</a>
  <a class="button" href="/parks/">Browse places</a></div>
  <div class="trust-strip"><span><strong>{canonical_entity_count}</strong> published records</span>
  <span><strong>{gap_count}</strong> explicit open questions</span>
  <span><strong>Public</strong> ChangeSet history</span></div>
</header>

<section>
  <span class="eyebrow">Start with your objective</span>
  <h2>Browse the planning graph</h2>
  <div class="browse-grid">
    <a class="browse-card" href="/parks/"><strong>Parks &amp; preserves</strong><span>Find access, rules, facilities, and connected routes.</span></a>
    <a class="browse-card" href="/trails/"><strong>Trails &amp; routes</strong><span>Compare corridors, trailheads, camps, and route choices.</span></a>
    <a class="browse-card" href="/camping/"><strong>Camping</strong><span>Explore campgrounds, group camps, cabins, and individual sites.</span></a>
    <a class="browse-card" href="/peaks/"><strong>Peaks</strong><span>Connect summits to approaches, permits, and current checks.</span></a>
  </div>
</section>

<section>
  <span class="eyebrow">How Wayproof answers</span>
  <h2>A fact is useful only when its limits are visible.</h2>
  <div class="principle-grid">
    <article><strong>1. Start with the source</strong><p>Official and attributed community sources remain distinct.</p></article>
    <article><strong>2. Preserve disagreement</strong><p>Conflicting values stay attached to their methods and provenance.</p></article>
    <article><strong>3. Recheck what changes</strong><p>Conditions, closures, water, and access are marked for confirmation.</p></article>
  </div>
</section>

<section>
  <span class="eyebrow">Planning guides</span>
  <h2>See the model in practice</h2>
  <div class="featured-grid">
    <a class="featured-card" href="/destinations/del-valle/"><span class="meta">Destination guide</span><strong>Del Valle Regional Park</strong><span>Camping, lake recreation, access, and current checks.</span></a>
    <a class="featured-card" href="/trails/ohlone-wilderness/"><span class="meta">Trail guide</span><strong>Ohlone Wilderness Trail</strong><span>Endpoints, parking, camps, water, and route alternatives.</span></a>
    <a class="featured-card" href="/knowledge/peak-mount-whitney/"><span class="meta">Peak record</span><strong>Mount Whitney</strong><span>Approaches, elevation evidence, route choices, and uncertainty.</span></a>
  </div>
</section>

<section>
  <span class="eyebrow">Research queue</span>
  <h2>Questions that remain open</h2>
  <p>These are explicit canonical gaps&mdash;not missing fields quietly treated as answers.</p>
  {gaps_html}
</section>

<footer class="site-footer"><div><strong>Wayproof</strong>
  <p>Built openly from <a href="https://github.com/{repo}">{repo}</a>.</p></div>
  <div class="footer-links"><a href="/changes/">Published changes</a>
  <a href="https://github.com/{repo}/issues/new?template=data_report.md&amp;labels=data">Submit a report</a></div>
  <p class="meta footer-note">Planning aid, not a booking or safety guarantee. Verify volatile facts at the linked official source.</p>
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
        primary_nav=render_primary_nav(),
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
