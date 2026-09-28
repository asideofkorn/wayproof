"""Production output acceptance using the shared generated-site fixture."""
import json
import re

from wayproof.media_migration import _files


def test_production_html_json_mcp_keep_identical_qualified_context(generated_reference_site):
    _, _, _, _, _, active = generated_reference_site
    model = json.loads(active['index.json'])
    assert model == active['model'] == json.loads(active['mcp.json'])
    assert json.loads(re.search(r'id="evidence-projection">(.*?)</script>', active['index.html']).group(1)) == model
    for label in ('Event / capture time', 'Statement publication time', 'Retrieval time',
                  'Analysis time (not performed)', 'precision, sensitivity and uncertainty'):
        assert label in active['index.html']
    assert json.loads(active['entity'])['reference_evidence'] == [model]
    assert 'href="https://example.invalid/comment"' in active['index.html']
    assert 'href="#context"' in active['index.html']


def test_withdrawal_regenerates_every_production_output_without_authority(generated_reference_site):
    publication, reads, tools, change, _, active = generated_reference_site
    output = publication.root / '_site'
    rid = change.records.claims[0].claim_id
    model = tools.explain_claim(rid)
    assert model == reads.get('claim', rid) == tools.get_record('claim', rid)['record']
    assert model['support'] == 'unsupported'
    assert model['texts'] == model['context'] == []
    directory = output / 'evidence/claim' / rid
    for name in ('index.json', 'mcp.json'):
        assert json.loads((directory / name).read_text()) == model
    html = (directory / 'index.html').read_text()
    assert json.loads(re.search(r'id="evidence-projection">(.*?)</script>', html).group(1)) == model
    assert 'unsupported' in html
    for row in json.loads((output / 'reference-index.json').read_text()):
        assert row['support'] == 'unsupported'
    assert json.loads((output / 'cache.json').read_text())['plans'] == 'invalidated'
    offline = json.loads((output / 'offline-manifest.json').read_text())
    assert offline != json.loads(active['offline'])
    assert offline['replace_previous']
    assert set(offline['files']) == set(_files(output)) - {'offline-manifest.json'}
    retained = b''.join(_files(publication.root).values())
    assert b'SYNTHETIC STALE REFERENCE TEXT' not in retained
    for source in change.records.sources:
        assert source.locator.encode() not in retained
    for statement in change.records.attributed_statements:
        assert statement.text.encode() not in retained
    assert not reads.changes(rid, 'claim')[0].evidence_refs
