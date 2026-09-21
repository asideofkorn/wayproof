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


def entity_payload(reads: CanonicalReadService, entity_id: str) -> dict:
    """Build one transport-neutral entity view exclusively through read APIs."""
    entity = reads.entity(entity_id)
    claims = []
    history = list(reads.changes(record_id=entity_id))
    for claim in reads.claims_for(entity_id):
        provenance = reads.explain_claim(claim.claim_id)
        claims.append({
            "claim": claim,
            "evidence": provenance.evidence,
            "observations": provenance.observations,
            "sources": provenance.sources,
        })
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
        '<nav class="crumbs"><a href="/">Wayproof</a> / '
        '<a href="/search/">Canonical search</a></nav>',
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


def render_search_html(entities: Iterable[dict], site_url: str) -> str:
    entities = list(entities)
    kinds = sorted({item["kind"] for item in entities})
    rows = "".join(
        f'<li data-search="{_e((item["name"] + " " + item["entity_id"]).casefold())}" '
        f'data-kind="{_e(item["kind"])}">'
        f'<a href="/knowledge/{_e(item["entity_id"])}">{_e(item["name"])}</a> '
        f'<span class="pill">{_e(item["kind"])}</span></li>'
        for item in entities
    )
    options = ''.join(f'<option value="{_e(kind)}">{_e(kind)}</option>' for kind in kinds)
    body = f"""
<nav class="crumbs"><a href="/">Wayproof</a></nav>
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


def build_canonical_site(reads: CanonicalReadService, output_dir: Path,
                         site_url: str) -> dict:
    """Write canonical search and detail pages into an existing site artifact."""
    entities = tuple(_plain(item) for item in reads.search_entities())
    known_ids = {item["entity_id"] for item in entities}
    search_dir = output_dir / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    (search_dir / "index.html").write_text(render_search_html(entities, site_url), encoding="utf-8")
    (search_dir / "index.json").write_text(_json({
        "type": "canonical_entity_index", "count": len(entities), "entities": entities,
    }), encoding="utf-8")

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
    return {"canonical_entities": len(entities)}
