"""Executed rehearsal consumer/removal assertions, not an impact-plan-only test."""
import json
import re

from wayproof.media_migration import _files
from wayproof.mcp_server import WayproofReadTools


def test_reviewed_analysis_html_json_mcp_share_exact_bounded_context(generated_analysis_rehearsal):
    _, _, first, change, _, _, active, before = generated_analysis_rehearsal
    prefix = f'evidence/claim/{change.records.claims[0].claim_id}/'
    html = active[prefix + 'index.html'].decode()
    model = json.loads(active[prefix + 'index.json'])
    assert model == before == json.loads(active[prefix + 'mcp.json'])
    assert model == json.loads(re.search(r'id="evidence-projection">(.*?)</script>', html).group(1))
    assert model['context'][0]['analysis_run_id'] == first.id
    assert model['context'][0]['event_capture_times'][0]['kind'] == 'unknown'
    assert model['publication'] == 'disabled' and model['analysis_scope'] == 'synthetic_only'
    assert '<script>steal_secrets()' not in html
    assert '&lt;script&gt;steal_secrets()&lt;/script&gt;' in html
    assert 'Wayproof analysis finding' in html
    assert 'Qualified provenance' in html


def test_withdrawal_regenerates_projections_and_preserves_unrelated_history(generated_analysis_rehearsal):
    service, reads, first, change, other_change, output, active, _ = generated_analysis_rehearsal
    current = _files(output)
    rid = change.records.claims[0].claim_id
    model = reads.explain_claim(rid)
    assert model['support'] == 'unsupported' and model['texts'] == model['context'] == []
    assert model == WayproofReadTools(reads).get_evidence_detail('claim', rid)
    for kind, record_id in [('analysis_run', first.id), ('analysis_finding', first.findings[0].id),
                            ('evidence', change.records.evidence[0].evidence_id), ('claim', rid)]:
        prefix = f'evidence/{kind}/{record_id}/'
        row = reads.get(kind, record_id)
        assert row['support'] == 'unsupported'
        assert json.loads(current[prefix + 'index.json']) == json.loads(current[prefix + 'mcp.json']) == row
        html = current[prefix + 'index.html'].decode()
        assert json.loads(re.search(r'id="evidence-projection">(.*?)</script>', html).group(1)) == row
    other_prefix = f'evidence/claim/{other_change.records.claims[0].claim_id}/'
    for name in ('index.html', 'index.json', 'mcp.json'):
        assert current[other_prefix + name] == active[other_prefix + name]
    retained = b''.join(current.values())
    assert b'steal_secrets' not in retained and b'SYNTHETIC STALE ANALYSIS' not in retained
    assert b'https://example.invalid/post' not in retained
    assert json.loads(current['cache.json'])['plans'] == 'invalidated'
    index = json.loads(current['search-index.json'])
    assert next(r for r in index if r['record_id'] == rid)['support'] == 'unsupported'
    offline = json.loads(current['offline-manifest.json'])
    assert offline['replace_previous'] and set(offline['files']) == set(current) - {'offline-manifest.json'}
    assert current['offline-manifest.json'] != active['offline-manifest.json']
    assert service.outcomes()[0].status == 'withdrawn'
