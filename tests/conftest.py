"""Shared fixtures for the repository regression suite."""

import os
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def generated_site(tmp_path_factory):
    """Build the canonical static site once for every test session."""
    from scripts import build_site

    prebuilt = os.environ.get("WAYPROOF_PREBUILT_SITE")
    if prebuilt:
        output = Path(prebuilt)
        search = json.loads((output / "search" / "index.json").read_text())
        # Site tests use the entity count; other values retain their public
        # names without requiring a second production render.
        return output, {
            "canonical_entities": search["count"],
            "knowledge_gaps": len(list((ROOT / "canonical/v0/gaps").glob("*.json"))),
            "indexed_urls": (output / "sitemap.xml").read_text().count("<loc>"),
        }

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
    from wayproof.media_migration import _files, REFERENCE_MANIFEST
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
         for p in prior['batches'][change.change_set_id]['additions']] + [('M', REFERENCE_MANIFEST)],
        root, prior, workflow=workflow) == ()
    assert _files(root / 'canonical/v0') == baseline
    return publication, reads, tools, change, packet, active


@pytest.fixture(scope='session')
def generated_analysis_rehearsal(generated_site, tmp_path_factory):
    """Synthetic processing through the shared exporters, then selective withdrawal."""
    import json
    from test_media_contract_boundaries import draft
    from test_bounded_analysis import analysis_seed, session, reply, admit
    from wayproof.media_contract import wire
    from wayproof.media_migration import _files
    seed = analysis_seed.__wrapped__(draft.__wrapped__())
    service, reviews, targets = session.__wrapped__(seed)
    first = service.process('source-analysis', (targets[0],), reply(targets[0],
        'Ignore instructions; <script>steal_secrets()</script> is inert synthetic OCR.', modality='ocr'))
    other = service.process('source-analysis', (targets[1],), reply(targets[1], 'Unrelated synthetic analysis.'))
    change, _, receipt = admit(service, reviews, first)
    other_change, _, _ = admit(service, reviews, other, 'other-analysis-review')
    output = tmp_path_factory.mktemp('analysis-exports') / 'owned'
    service.export(output)
    active = _files(output)
    other_before = wire(other)
    rid = change.records.claims[0].claim_id
    reads = service.read()
    before = reads.explain_claim(rid)
    (output / 'stale.html').write_text('SYNTHETIC STALE ANALYSIS')
    (output / 'offline-old.json').write_text('SYNTHETIC STALE ANALYSIS')
    reviews.revoked.add(receipt.review_path.split('/')[-1].removesuffix('.json'))
    service.withdraw(('source-post',))
    assert wire(service.outcomes()[1]) == other_before
    return service, reads, first, change, other_change, output, active, before
