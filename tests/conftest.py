"""Shared fixtures for the repository regression suite."""

import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def generated_site(tmp_path_factory):
    """Build the canonical static site once for every test session."""
    from scripts import build_site

    output = tmp_path_factory.mktemp("generated-site")
    original_cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        stats = build_site.build(output)
    finally:
        os.chdir(original_cwd)
    return output, stats


@pytest.fixture(scope='session')
def generated_reference_site(generated_site, tmp_path_factory):
    """One synthetic activation and removal through the full production site builder."""
    from copy import deepcopy
    import json
    import shutil
    from test_media_contract_boundaries import draft
    from test_public_research_policy import research
    from test_reference_activation import statement_research, prepare
    from wayproof.media_migration import _files
    from wayproof.read_service import CanonicalReadService
    from wayproof.mcp_server import WayproofReadTools
    from wayproof.publication import verify_reference_publication

    root = tmp_path_factory.mktemp('reference-production')
    for namespace in ('canonical', 'changesets', 'data', 'geometry'):
        shutil.copytree(ROOT / namespace, root / namespace)
    change, packet = statement_research(research.__wrapped__(draft.__wrapped__()),
                                        'park-del-valle-regional-park')
    publication, workflow = prepare(root, change, packet)
    from wayproof.media_contract import wire
    review_file = root / 'research-reviews' / (publication.batch()._manifest()['fingerprint'] + '.json')
    review_file.parent.mkdir()
    review_file.write_text(json.dumps(wire(workflow.review)))
    baseline = {k: v for k, v in _files(root / 'canonical/v0').items()}
    reads = CanonicalReadService(root, research_workflow=workflow)
    tools = WayproofReadTools(reads)
    output = publication.export()
    rid = change.records.claims[0].claim_id
    directory = output / 'evidence/claim' / rid
    active = {name: (directory / name).read_text() for name in ('index.html', 'index.json', 'mcp.json')}
    active['entity'] = (output / 'knowledge/park-del-valle-regional-park.json').read_text()
    active['offline'] = (output / 'offline-manifest.json').read_text()
    active['model'] = tools.explain_claim(rid)
    for name in ('obsolete.html', 'old-cache.json', 'old-index.json', 'old-offline.json'):
        (output / name).write_text('SYNTHETIC STALE REFERENCE TEXT')
    prior = deepcopy(publication._manifest())
    def no_authority(*args):
        raise ConnectionError('synthetic revoked approval / unavailable GitHub')
    workflow.resolve = no_authority
    publication.withdraw()
    assert verify_reference_publication(
        [('M' if p in publication.batch()._manifest()['additions'] else 'D', p)
         for p in prior['batches'][change.change_set_id]['additions']] + [('M', 'reference-publication.json')],
        root, prior, workflow=workflow) == ()
    assert _files(root / 'canonical/v0') == baseline
    return publication, reads, tools, change, packet, active
