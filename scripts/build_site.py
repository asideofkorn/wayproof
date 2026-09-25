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
import shutil
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
  <div class="footer-links"><a href="/how-it-works/">How it works</a>
  <a href="/changes/">Published changes</a>
  <a href="https://github.com/{repo}/issues/new?template=data_report.md&amp;labels=data">Submit a report</a></div>
  <p class="meta footer-note">Planning aid, not a booking or safety guarantee. Verify volatile facts at the linked official source.</p>
</footer>
</body>
</html>
"""

HOW_IT_WORKS_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>How Wayproof Works &mdash; Sources, Claims, and Planning</title>
<meta name="description" content="How Wayproof turns sources into scoped claims,
preserves uncertainty, and produces traceable outdoor-planning answers.">
<link rel="canonical" href="{site}/how-it-works/">
<link rel="stylesheet" href="/style.css">
</head>
<body>
{primary_nav}

<header class="page-header model-hero">
  <span class="eyebrow">How Wayproof works</span>
  <h1>From sources to decisions&mdash;without hiding uncertainty.</h1>
  <p class="tagline">A useful outdoor-planning answer must show what is known,
  what applies to this trip, what conflicts, and what still needs checking.</p>
</header>

<nav class="section-nav" aria-label="On this page">
  <a href="#answer">Start with the answer</a>
  <a href="#evidence">Evidence model</a>
  <a href="#relationships">Planning graph</a>
  <a href="#comparison">Compare approaches</a>
  <a href="#history">History</a>
  <a href="#publishing">Publishing</a>
</nav>

<section id="answer">
  <span class="eyebrow">Start with the outcome</span>
  <h2>What can I rely on for this trip?</h2>
  <p>A Wayproof answer combines durable place and route knowledge with the date,
  activity, party, equipment, and stages of a trip. It does not turn a missing
  value into permission, availability, or safety.</p>
  <article class="answer-example">
    <span class="meta">Example planning answer</span>
    <h3>East Fork Campground Site 126</h3>
    <ul>
      <li>Reserved individual campsite with sourced coordinates and facilities.</li>
      <li>Published vehicle and checkout fields disagree.</li>
      <li>Campground operations and fire restrictions need a current check.</li>
    </ul>
    <div class="hero-actions"><a class="button primary" href="/knowledge/campsite-east-fork-126/">See the record</a>
    <a class="button" href="/changes/">View published history</a></div>
  </article>
</section>

<section id="evidence">
  <span class="eyebrow">Evidence model</span>
  <h2>Every answer can be traced backward.</h2>
  <div class="model-flow" role="img" aria-label="Source leads to observation, evidence, claim, then rule or derived result">
    <div><strong>Source</strong><span>Page, API, map, or field report</span></div><b aria-hidden="true">&rarr;</b>
    <div><strong>Observation</strong><span>What it said or showed</span></div><b aria-hidden="true">&rarr;</b>
    <div><strong>Evidence</strong><span>How it supports or challenges</span></div><b aria-hidden="true">&rarr;</b>
    <div><strong>Claim</strong><span>One scoped assertion</span></div><b aria-hidden="true">&rarr;</b>
    <div><strong>Rule or result</strong><span>What follows for planning</span></div>
  </div>
  <p class="model-note">A source is not automatically correct. An observation
  preserves what it published; evidence records how that observation bears on
  a claim. Competing claims can coexist without erasing one another.</p>
  <div class="principle-grid">
    <article><strong>Scoped</strong><p>Claims can be bounded by place, time, activity, party, and equipment.</p></article>
    <article><strong>Traceable</strong><p>Sources and supporting observations remain inspectable.</p></article>
    <article><strong>Honest</strong><p>Conflict and missing evidence remain visible to consumers.</p></article>
  </div>
</section>

<section id="relationships">
  <span class="eyebrow">Planning graph</span>
  <h2>Places connect only when evidence supports the edge.</h2>
  <div class="relationship-map" role="img" aria-label="A park contains a campground and has a trailhead; the campground contains campsites; the trailhead starts a route composed of segments that reach peaks and pass facilities">
    <div class="relationship-column"><strong>Park or preserve</strong><span>contains &darr;</span><strong>Campground</strong><span>contains &darr;</span><strong>Campsite</strong></div>
    <div class="relationship-bridge" aria-hidden="true"><span>has access</span><b>&rarr;</b></div>
    <div class="relationship-column"><strong>Trailhead</strong><span>starts &darr;</span><strong>Route</strong><span>composed of &darr;</span><strong>Segments</strong></div>
    <div class="relationship-branch"><span>reaches &rarr; <strong>Peak</strong></span><span>passes &rarr; <strong>Water or camp</strong></span></div>
  </div>
  <p class="model-note"><strong>Proximity is not access.</strong> Wayproof does
  not infer that a nearby road reaches a trail, or that a campsite belongs to a
  campground, without evidence for that relationship.</p>
</section>

<section id="comparison">
  <span class="eyebrow">Why this model</span>
  <h2>Wiki readability, graph connections, claim-level accountability.</h2>
  <p class="comparison-hint" aria-hidden="true">Swipe to compare all approaches &rarr;</p>
  <div class="comparison-table" tabindex="0" aria-label="Scrollable comparison table">
  <table>
    <thead><tr><th>Capability</th><th>Traditional wiki</th><th>Basic knowledge graph</th><th>Wayproof claims model</th></tr></thead>
    <tbody>
      <tr><th>Primary unit</th><td>Editable page</td><td>Entity and relationship</td><td>Scoped, evidenced claim</td></tr>
      <tr><th>Best at</th><td>Human-readable explanation</td><td>Connecting structured objects</td><td>Answering planning questions with provenance</td></tr>
      <tr><th>Sources</th><td>Citations attached to prose</td><td>Often attached to nodes or edges</td><td>Source &rarr; Observation &rarr; Evidence &rarr; Claim</td></tr>
      <tr><th>Disagreement</th><td>Editors commonly select one version</td><td>Can retain multiple unexplained values</td><td>Preserves claims, methods, dates, evidence, and conflict</td></tr>
      <tr><th>Unknowns</th><td>Absent or described in prose</td><td>Usually a missing property</td><td>Explicit knowledge gap with planning consequences</td></tr>
      <tr><th>Time</th><td>Page revision history</td><td>Optional temporal properties</td><td>Real-world time is separate from publication history</td></tr>
      <tr><th>Rules</th><td>Explained for a reader</td><td>Require custom application logic</td><td>Evaluated against trip context</td></tr>
      <tr><th>Changing conditions</th><td>The page is updated</td><td>The latest value may replace the old one</td><td>Dated evidence plus a pre-trip recheck</td></tr>
      <tr><th>Revision history</th><td>Page diffs</td><td>Implementation-dependent</td><td>Typed ChangeSets plus Git history</td></tr>
      <tr><th>Agent use</th><td>Agent interprets prose</td><td>Strong traversal, limited explanation</td><td>Structured answer with evidence and applicability</td></tr>
    </tbody>
  </table>
  </div>
  <p>Wayproof borrows the readable current view and public revision history of
  a wiki, plus the structured relationships of a knowledge graph. Its
  distinguishing unit is the claim: a bounded statement whose evidence,
  scope, uncertainty, and planning effect remain inspectable.</p>
</section>

<section id="history">
  <span class="eyebrow">Two kinds of history</span>
  <h2>The world changing is not the same as Wayproof changing.</h2>
  <div class="history-grid">
    <article><strong>Real-world history</strong><p>Dated observations and claims record when water flowed, a road opened, or a rule applied.</p></article>
    <article><strong>Publication history</strong><p>Validated ChangeSets and Git record when Wayproof added, replaced, or removed knowledge.</p></article>
  </div>
  <p>A later observation that a water source is dry does not erase an earlier
  field report that it flowed. Likewise, a publication date is never used as a
  substitute for an unknown real-world event date.</p>
</section>

<section>
  <span class="eyebrow">Answerability</span>
  <h2>Uncertainty is part of the answer.</h2>
  <dl class="state-list">
    <div><dt>Answered</dt><dd>Evidence supports a bounded answer.</dd></div>
    <div><dt>Conflicting</dt><dd>Published evidence disagrees, and no choice is silently made.</dd></div>
    <div><dt>Unknown</dt><dd>Evidence is insufficient.</dd></div>
    <div><dt>Needs current check</dt><dd>The fact is too volatile to freeze into a timeless answer.</dd></div>
    <div><dt>Not applicable</dt><dd>The question does not apply to this trip context.</dd></div>
  </dl>
</section>

<section id="publishing">
  <span class="eyebrow">Controlled publishing</span>
  <h2>Agents can propose knowledge. They cannot publish it directly.</h2>
  <div class="model-flow publication-flow" role="img" aria-label="Draft ChangeSet is validated, prepared, reviewed on GitHub, merged, and published">
    <div><strong>Draft</strong><span>Typed ChangeSet</span></div><b aria-hidden="true">&rarr;</b>
    <div><strong>Validate</strong><span>Schema and semantics</span></div><b aria-hidden="true">&rarr;</b>
    <div><strong>Prepare</strong><span>Detached candidate</span></div><b aria-hidden="true">&rarr;</b>
    <div><strong>Review</strong><span>GitHub PR and CI</span></div><b aria-hidden="true">&rarr;</b>
    <div><strong>Publish</strong><span>Merge to main</span></div>
  </div>
  <p>Git and GitHub handle review, concurrency, and publication. Wayproof adds
  the domain intent: what knowledge changed, which evidence supports it, and
  which gaps remain.</p>
  <div class="hero-actions"><a class="button primary" href="/search/">Explore Wayproof</a>
  <a class="button" href="/changes/">Browse published changes</a>
  <a class="button" href="https://github.com/{repo}">Inspect the repository</a></div>
</section>

<footer class="site-footer"><div><strong>Wayproof</strong>
  <p>Source-backed outdoor planning with uncertainty left visible.</p></div>
  <div class="footer-links"><a href="/search/">Search</a>
  <a href="/how-it-works/">How it works</a>
  <a href="/changes/">Published changes</a>
  <a href="https://github.com/{repo}">GitHub</a></div>
  <p class="meta footer-note">Planning aid, not a booking or safety guarantee. Confirm volatile conditions with the linked official source.</p>
</footer>
</body>
</html>
"""

def build(output_dir: Path, today: datetime.date | None = None) -> dict:
    today = today or datetime.date.today()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "style.css").write_text(STYLESHEET)
    shutil.copytree(Path("web_assets"), output_dir / "assets", dirs_exist_ok=True)
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
    how_dir = output_dir / "how-it-works"
    how_dir.mkdir(parents=True, exist_ok=True)
    (how_dir / "index.html").write_text(HOW_IT_WORKS_TEMPLATE.format(
        site=SITE_URL, repo=REPO, primary_nav=render_primary_nav(),
    ))

    canonical_entities = canonical_reads.search_entities()
    urls = [f"{SITE_URL}/", f"{SITE_URL}/search/", f"{SITE_URL}/how-it-works/"]
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
