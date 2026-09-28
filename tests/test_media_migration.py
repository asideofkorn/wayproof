"""Synthetic staged migration/withdrawal acceptance; no media/network/model IO."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import re

import pytest

from test_public_research_policy import research, reviewed
from test_media_contract_boundaries import draft
from wayproof.canonical_storage import load_canonical, record_document, UnsupportedSchemaError
from wayproof.media_migration import MigrationWorkspace, _files
from wayproof.public_research import fingerprint
from wayproof.research_workflow import GitHubResearchReviews, ReviewReceipt
from wayproof.schema import CanonicalRecords, Entity, Source, Observation, Evidence, Claim
from wayproof.media_contract import wire
from wayproof.mcp_server import WayproofReadTools


class Workflow:
    """Test-only authenticated workflow seam; production uses GitHubResearchReviews."""
    def __init__(self, review):
        self.review = review

    def resolve(self, receipt, fp):
        assert receipt.head_commit == 'a' * 40
        assert receipt.review_path == f'research-reviews/{fp}.json'
        assert fp == self.review.fingerprint
        return self.review


@pytest.fixture
def migration(research, tmp_path):
    change, packet = research
    source = tmp_path / 'source'
    path = source / 'canonical/v0/entities/legacy-place.json'
    path.parent.mkdir(parents=True)
    # Deliberately noncanonical whitespace: migration must preserve bytes, not reserialize.
    path.write_text('  ' + record_document('entity', Entity('legacy-place', 'park', 'Legacy park')))
    for kind, collection, rid, record in (
        ('source', 'sources', 'legacy-source', Source('legacy-source', 'https://example.invalid/legacy')),
        ('observation', 'observations', 'legacy-observation', Observation(
            'legacy-observation', 'legacy-source', 'Synthetic legacy report', artifact_refs=('unverified-image.jpg',))),
        ('evidence', 'evidence', 'legacy-cited', Evidence('legacy-cited', 'legacy-observation', 'legacy-claim', 'supports')),
        ('evidence', 'evidence', 'legacy-uncited', Evidence('legacy-uncited', 'legacy-observation', 'legacy-claim', 'contradicts')),
        ('claim', 'claims', 'legacy-claim', Claim('legacy-claim', 'legacy-place', 'reported_status', 'open', ('legacy-cited',))),
    ):
        target = source / f'canonical/v0/{collection}/{rid}.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(record_document(kind, record))
    base = load_canonical(source)
    review = reviewed(change, packet, base)
    receipt = ReviewReceipt(7, 'a' * 40, f'research-reviews/{review.fingerprint}.json')
    workflow = Workflow(review)
    workspace = MigrationWorkspace.stage(source, tmp_path / 'stage', change, packet, receipt, workflow)
    return workspace, source, change, packet, receipt, workflow


def test_deterministic_reload_and_rollback_preserve_v0_bytes(migration):
    workspace, source, change, packet, receipt, workflow = migration
    before = _files(source)
    first = _files(workspace.root)
    MigrationWorkspace.stage(source, workspace.root, change, packet, receipt, workflow)
    assert _files(workspace.root) == first
    for path, content in before.items():
        assert (workspace.root / path).read_bytes() == content
    with pytest.raises(UnsupportedSchemaError, match='unsupported schema'):
        load_canonical(workspace.root)  # Existing production/older supported reader fails closed.
    reads = MigrationWorkspace(workspace.root, workflow).read()
    for claim in change.records.claims:
        detail = reads.evidence_detail('claim', claim.claim_id)
        assert detail['support'] == 'traceable'
        assert any(row['record_type'] == 'evidence' for row in detail['lineage'])
    workspace.rollback()
    assert load_canonical(workspace.root) == load_canonical(source)
    assert _files(source) == before
    with pytest.raises(ValueError, match='identical staged migration'):
        MigrationWorkspace.stage(source, workspace.root, change, packet, receipt, workflow)


def test_removal_erases_content_and_regenerates_every_owned_consumer(migration):
    workspace, source, change, packet, _, workflow = migration
    baseline = _files(source)
    output = workspace.export()
    old_offline = json.loads((output / 'offline-manifest.json').read_text())
    # Simulate stale output/index/cache files; a rebuild must remove them too.
    for name in ('old.html', 'old.json', 'old-mcp.json', 'old-index.json', 'old-cache.json', 'old-offline.json'):
        (output / name).write_text('STALE RETAINED TEXT')
    workspace.withdraw()
    reopened = MigrationWorkspace(workspace.root, workflow)
    reads = reopened.read()
    tools = WayproofReadTools(reads)
    for claim in change.records.claims:
        model = tools.get_evidence_detail('claim', claim.claim_id)
        assert model['support'] == 'unsupported'
        assert model['texts'] == []
        directory = output / 'evidence/claim' / claim.claim_id
        assert json.loads((directory / 'index.json').read_text()) == model
        assert json.loads((directory / 'mcp.json').read_text()) == model
        html = (directory / 'index.html').read_text()
        assert json.loads(re.search(r'id="evidence-projection">(.*?)</script>', html).group(1)) == model
        assert 'unsupported' in html
    all_bytes = b''.join(_files(workspace.root).values())
    for statement in change.records.attributed_statements:
        assert statement.text.encode() not in all_bytes
    for source_record in change.records.sources:
        assert source_record.locator.encode() not in all_bytes
    assert b'STALE RETAINED TEXT' not in all_bytes
    index = json.loads((output / 'search-index.json').read_text())
    assert all(row['support'] == 'unsupported' for row in index
               if row['record_type'] == 'claim' and row['record_id'] != 'legacy-claim')
    assert json.loads((output / 'cache.json').read_text())['plans'] == 'invalidated'
    offline = json.loads((output / 'offline-manifest.json').read_text())
    assert offline['generation'] != old_offline['generation']
    assert offline['replace_previous'] is True
    assert _files(source) == baseline
    workspace.rollback()
    assert all(s.locator.encode() not in b''.join(_files(workspace.root).values())
               for s in change.records.sources)


def test_unavailable_review_hides_claims_without_substituting_evidence(migration):
    workspace, _, change, _, _, workflow = migration
    workflow.review = replace(workflow.review, sources=tuple(
        replace(source, current_state='unavailable') for source in workflow.review.sources))
    reads = workspace.read()
    for claim in change.records.claims:
        model = reads.explain_claim(claim.claim_id)
        assert model['support'] == 'unsupported'
        assert all('record' not in row for row in model['lineage'])
        assert not model['texts']
    workspace.export()


def test_tampering_rejected_before_export(migration):
    workspace, *_ = migration
    path = next((workspace.root / 'canonical/v1/claims').glob('*.json'))
    path.write_text(path.read_text().replace('claim', 'forged', 1))
    with pytest.raises(ValueError, match='inventory/content changed'):
        workspace.export()
    assert not (workspace.root / 'outputs').exists()


def test_workflow_requires_merged_head_approval_not_receipt_flags(research, tmp_path, monkeypatch):
    change, packet = research
    review = reviewed(change, packet)
    receipt = ReviewReceipt(7, 'a' * 40, f'research-reviews/{review.fingerprint}.json')
    authority = GitHubResearchReviews(tmp_path, 'owner/repo')
    pr = {'merged': True, 'base': {'ref': 'main', 'repo': {'full_name': 'owner/repo'}},
          'head': {'sha': 'a' * 40}, 'merge_commit_sha': 'b' * 40, 'user': {'login': 'contributor'}}
    reviews = [{'id': 1, 'state': 'APPROVED', 'commit_id': 'a' * 40, 'user': {'login': 'maintainer'}}]
    permission = {'permission': 'write', 'role_name': 'maintain'}
    calls = []
    def api(path):
        calls.append(path)
        return deepcopy(reviews if '/reviews?' in path else permission if '/permission' in path else pr)
    monkeypatch.setattr(authority, '_api', api)
    git_calls = []
    def git(*args):
        git_calls.append(args)
        return json.dumps(wire(review)) if args[0] == 'show' else ''
    monkeypatch.setattr(authority, '_git', git)
    assert authority.resolve(receipt, review.fingerprint) == review
    assert ('merge-base', '--is-ancestor', 'b' * 40, 'refs/remotes/origin/main') in git_calls
    for key, value in [('merged', False), ('head', {'sha': 'c' * 40})]:
        old = pr[key]
        pr[key] = value
        with pytest.raises(ValueError):
            authority.resolve(receipt, review.fingerprint)
        pr[key] = old
    for state in ('CHANGES_REQUESTED', 'DISMISSED'):
        reviews.append({'id': 2, 'state': state, 'commit_id': 'a' * 40, 'user': {'login': 'maintainer'}})
        with pytest.raises(ValueError):
            authority.resolve(receipt, review.fingerprint)
        reviews.pop()
    permission['role_name'] = 'read'
    with pytest.raises(ValueError, match='approval'):
        authority.resolve(receipt, review.fingerprint)


def test_existing_read_and_mcp_handles_refresh_after_withdrawal(migration):
    workspace, _, change, *_ = migration
    reads = workspace.read()
    tools = WayproofReadTools(reads)
    rid = change.records.claims[0].claim_id
    assert tools.get_evidence_detail('claim', rid)['support'] == 'traceable'
    workspace.withdraw()
    assert reads.explain_claim(rid)['support'] == 'unsupported'
    assert tools.get_evidence_detail('claim', rid)['support'] == 'unsupported'
    assert tools.get_record('claim', rid)['record']['support'] == 'unsupported'


@pytest.mark.parametrize('kind', ['baseline', 'content', 'receipt'])
def test_rehashed_tampering_still_cannot_change_reviewed_snapshot(migration, kind):
    from wayproof.media_migration import digest, encoded
    workspace, *_ = migration
    manifest = workspace._manifest()
    if kind == 'receipt':
        manifest['receipt']['approved'] = True
    else:
        inventory = manifest['baseline' if kind == 'baseline' else 'additions']
        name = next(p for p in inventory if ('entities/' if kind == 'baseline' else 'claims/') in p)
        path = workspace.root / name
        value = json.loads(path.read_bytes())
        if kind == 'baseline':
            value['record']['name'] = 'Forged legacy name'
        else:
            value['record']['value'] = 'Forged claim value'
        path.write_bytes(encoded(value))
        inventory[name] = digest(path.read_bytes())
        manifest['output_digest'] = digest(encoded(manifest['additions']))
    workspace._save(manifest)
    with pytest.raises(ValueError):
        workspace.read().keys()


def test_unavailable_version_does_not_fall_back_to_other_evidence(migration, tmp_path):
    workspace, source, change, packet, _, workflow = migration
    # A claim pins two Evidence records; loss of one cannot silently select the other.
    from test_media_contract_boundaries import make_change
    r = deepcopy(change.records)
    claim = r.claims[0]
    r.claims[0] = replace(claim, evidence_ids=tuple(e.evidence_id for e in r.evidence))
    # Keep reciprocal Evidence -> Claim identities consistent.
    r.evidence[:] = [replace(e, claim_id=claim.claim_id) for e in r.evidence]
    r.claims[:] = r.claims[:1]
    r.availability_reports[0] = replace(r.availability_reports[0], availability='unavailable')
    change = make_change(r)
    review = reviewed(change, packet, load_canonical(source))
    receipt = ReviewReceipt(7, 'a' * 40, f'research-reviews/{review.fingerprint}.json')
    staged = MigrationWorkspace.stage(source, tmp_path / 'unavailable', change, packet, receipt, Workflow(review))
    model = staged.read().explain_claim(claim.claim_id)
    assert model['support'] == 'unsupported'
    assert model['texts'] == []
    assert {e.evidence_id for e in r.evidence} <= {row['record_id'] for row in model['lineage']}


def test_production_consumers_and_writer_remain_disabled(migration):
    from wayproof.read_service import CanonicalReadService
    from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository, PreparationRejected
    workspace, source, change, *_ = migration
    with pytest.raises(UnsupportedSchemaError):
        CanonicalReadService(workspace.root)
    with pytest.raises(UnsupportedSchemaError):
        workspace.read().plan(None)
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(load_canonical(source)))
    writes.propose(change, 'synthetic')
    assert writes.validate(change.change_set_id, 'synthetic') == ()
    with pytest.raises(PreparationRejected, match='activation is disabled'):
        writes.prepare(change.change_set_id, 'synthetic')


def test_namespace_symlink_is_rejected(migration, tmp_path):
    workspace, *_ = migration
    target = tmp_path / 'moved-canonical'
    (workspace.root / 'canonical').rename(target)
    (workspace.root / 'canonical').symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        workspace.read().keys()


def test_interrupted_removal_holds_reads_and_can_resume(migration, monkeypatch):
    workspace, _, change, *_ = migration
    workspace.export()
    original = Path.unlink
    broken = False
    def interrupt(path, *args, **kwargs):
        nonlocal broken
        if 'canonical/v1/observations' in path.as_posix() and not broken:
            broken = True
            raise OSError('synthetic disk interruption')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'unlink', interrupt)
    with pytest.raises(OSError):
        workspace.withdraw()
    assert workspace._manifest()['state'] == 'removal_hold'
    with pytest.raises((ValueError, UnsupportedSchemaError)):
        workspace.read().keys()
    assert not (workspace.root / 'outputs').exists()
    monkeypatch.setattr(Path, 'unlink', original)
    workspace.withdraw()
    assert workspace.read().explain_claim(change.records.claims[0].claim_id)['support'] == 'unsupported'
    assert (workspace.root / 'outputs/offline-manifest.json').exists()


def test_legacy_uncited_evidence_is_preserved_without_relaxing_new_evidence(migration):
    from test_media_contract_boundaries import make_change
    workspace, source, change, *_ = migration
    model = workspace.read().explain_claim('legacy-claim')
    assert model['support'] == 'traceable'
    assert 'legacy-uncited' not in {row['record_id'] for row in model['lineage']}
    observation = next(row['record'] for row in model['lineage'] if row['record_type'] == 'observation')
    assert observation['artifact_refs'] == ['unverified-image.jpg']
    records = deepcopy(change.records)
    records.evidence.append(replace(records.evidence[0], evidence_id='new-uncited'))
    errors = make_change(records).validate(existing=load_canonical(source))
    assert any('evidence not cited by named claim' in error for error in errors)
