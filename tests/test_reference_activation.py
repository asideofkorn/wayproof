"""Synthetic production activation tests; no source acquisition or processing."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from test_media_contract_boundaries import draft, make_change
from test_public_research_policy import research, reviewed
from test_media_migration import Workflow
from wayproof.canonical_storage import load_canonical, record_document, UnsupportedSchemaError
from wayproof.media_migration import ReferencePublication, REFERENCE_MANIFEST, _files
from wayproof.media_contract import wire
from wayproof.media_schema import UnknownTime, Basis
from wayproof.public_research import ResearchPacket
from wayproof.research_workflow import ReviewReceipt
from wayproof.read_service import CanonicalReadService
from wayproof.mcp_server import WayproofReadTools
from wayproof.schema import Entity
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository
from wayproof.publication import verify_reference_publication


def statement_research(research, subject='legacy-place'):
    change, packet = deepcopy(research)
    r = change.records
    r.entities.clear()
    r.sources[:] = [s for s in r.sources if s.source_role != 'analysis_report']
    r.observations[:] = [o for o in r.observations if o.origin_kind == 'media_statement']
    r.analysis_runs.clear()
    r.analysis_findings.clear()
    r.reviewed_selections[:] = [s for s in r.reviewed_selections if s.origin.kind == 'statement']
    r.observation_provenance[:] = [p for p in r.observation_provenance
                                 if p.observation_id == r.observations[0].observation_id]
    r.evidence[:] = [replace(r.evidence[0], observation_id=r.observations[0].observation_id)]
    r.claims[:] = [replace(r.claims[0], subject_id=subject, predicate='reported_capture_context',
                          value='Author reports an approximate date; location remains unknown.')]
    packet = ResearchPacket(tuple(t for t in packet.texts if t.kind != 'analysis_finding'))
    return make_change(r), packet


def prepare(root, change, packet):
    from wayproof.canonical_storage import load_v0_baseline
    base = load_v0_baseline(root)
    review = reviewed(change, packet, base)
    workflow = Workflow(review)
    receipt = ReviewReceipt(7, 'a' * 40, f'research-reviews/{review.fingerprint}.json')
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(base))
    writes.propose(change, 'synthetic researcher')
    assert not writes.validate(change.change_set_id, 'synthetic validator')
    return writes.prepare_reference(change.change_set_id, 'synthetic builder', root,
                                    packet, receipt, workflow), workflow


@pytest.fixture
def reference(research, tmp_path):
    root = tmp_path / 'repository'
    path = root / 'canonical/v0/entities/legacy-place.json'
    path.parent.mkdir(parents=True)
    path.write_text('  ' + record_document('entity', Entity('legacy-place', 'park', 'Legacy park')))
    change, packet = statement_research(research)
    before = _files(root)
    publication, workflow = prepare(root, change, packet)
    return publication, workflow, change, packet, before


def test_real_read_storage_mcp_and_publication_entrypoints(reference):
    publication, workflow, change, _, before = reference
    root = publication.root
    records = load_canonical(root, research_workflow=workflow)
    assert records.claims == change.records.claims
    reads = CanonicalReadService(root, research_workflow=workflow)
    model = reads.explain_claim(change.records.claims[0].claim_id)
    assert model['projection'] == 'media-v1-reference'
    assert model['support'] == 'traceable'
    tools = WayproofReadTools(reads)
    assert tools.explain_claim(model['record_id']) == model
    assert tools.get_record('claim', model['record_id'])['record'] == model
    assert tools.get_entity('legacy-place')['reference_evidence'] == [model]
    assert reads.claims_for('legacy-place') == ()  # No implicit planning registration.
    for name, content in before.items():
        assert (root / name).read_bytes() == content
    paths = [('A', p) for p in publication.batch()._manifest()['additions']] + [('A', REFERENCE_MANIFEST)]
    assert verify_reference_publication(paths, root, workflow=workflow) == ()
    assert verify_reference_publication(paths[:-1], root, workflow=workflow)
    assert verify_reference_publication(paths + [('M', next(iter(before)))], root, workflow=workflow)


def test_context_preserves_roles_unknown_location_and_reproducibility(reference):
    publication, _, change, *_ = reference
    model = publication.read().explain_claim(change.records.claims[0].claim_id)
    context = model['context'][0]
    assert context['event_capture_times'][0]['value'] == '2030-04-01'
    assert context['event_capture_times'][0]['certainty'] == 'approximate'
    assert context['statement_publication_time']['value'] == '2030-04-03'
    assert context['attachment_publication_times'][0]['time']['value'] == '2030-04-02'
    assert context['retrieval_times'][0]['time']['value'] == '2030-04-03T12:00:00Z'
    assert context['analysis_time']['kind'] == 'unknown'
    assert context['analysis_status'] == 'not_performed'
    assert context['locations'][0]['value'] is None
    assert context['locations'][0]['precision_m'] is None
    assert context['locations'][0]['sensitivity'] == 'unassessed'
    assert context['versions'][0]['identity_basis'] == 'unverifiable'
    assert context['versions'][0]['reproducibility'] == 'unavailable'


def test_known_publication_never_fills_unknown_capture(reference, tmp_path):
    publication, _, change, packet, before = reference
    r = deepcopy(change.records)
    r.observation_provenance[0] = replace(r.observation_provenance[0],
        event_times=(UnknownTime('unknown', 'unknown', Basis('unknown', None)),))
    root = tmp_path / 'unknown'
    for path, content in before.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    candidate, _ = prepare(root, make_change(r), packet)
    context = candidate.read().explain_claim(r.claims[0].claim_id)['context'][0]
    assert context['event_capture_times'] == [wire(r.observation_provenance[0].event_times[0])]
    assert context['statement_publication_time']['kind'] == 'date'
    assert context['locations'][0]['value'] is None


@pytest.mark.parametrize('mutation', ['processing', 'upload', 'private', 'retained_media',
    'exif', 'personal_identification', 'sensitive_location', 'login_required', 'inferred_location',
    'unknown_precision', 'publication_as_capture'])
def test_activation_rejects_broader_paths_before_writes(research, tmp_path, mutation):
    root = tmp_path / 'root'
    p = root / 'canonical/v0/entities/legacy-place.json'
    p.parent.mkdir(parents=True)
    p.write_text(record_document('entity', Entity('legacy-place', 'park', 'Legacy park')))
    before = _files(root)
    change, packet = statement_research(research)
    if mutation == 'processing':
        change, packet = research
    if mutation == 'inferred_location':
        p = change.records.observation_provenance[0]
        change.records.observation_provenance[0] = replace(p, locations=(replace(p.locations[0], basis_kind='inferred'),))
    if mutation == 'unknown_precision':
        p = change.records.observation_provenance[0]
        change.records.observation_provenance[0] = replace(p, locations=(replace(p.locations[0], precision_m=5),))
    if mutation == 'publication_as_capture':
        p = change.records.observation_provenance[0]
        change.records.observation_provenance[0] = replace(p, event_times=(change.records.attributed_statements[0].publication_time,))
    change = make_change(change.records)
    from wayproof.canonical_storage import load_v0_baseline
    base = load_v0_baseline(root)
    review = reviewed(change, packet, base)
    if mutation in ('upload', 'private'):
        review = replace(review, acquisition=mutation)
    if mutation == 'login_required':
        review = replace(review, sources=tuple(replace(s, access='login_required') for s in review.sources))
    if mutation in ('retained_media', 'exif', 'personal_identification', 'sensitive_location'):
        review = replace(review, exclusions=(mutation,))
    receipt = ReviewReceipt(7, 'a'*40, f'research-reviews/{review.fingerprint}.json')
    with pytest.raises(ValueError):
        ReferencePublication.prepare(root, change, packet, receipt, Workflow(review))
    assert _files(root) == before


@pytest.mark.parametrize('state', ['changed', 'unavailable'])
def test_changed_or_unavailable_input_never_substitutes_content(reference, state):
    publication, workflow, change, *_ = reference
    reads = CanonicalReadService(publication.root, research_workflow=workflow)
    workflow.review = replace(workflow.review, sources=tuple(replace(s, current_state=state)
                              for s in workflow.review.sources))
    model = reads.explain_claim(change.records.claims[0].claim_id)
    assert model['support'] == 'unsupported'
    assert model['texts'] == model['context'] == []
    assert all('record' not in row for row in model['lineage'])
    with pytest.raises(UnsupportedSchemaError):
        load_canonical(publication.root, research_workflow=workflow)


def test_unknown_layout_and_forged_receipt_cannot_activate(reference):
    publication, *_ = reference
    (publication.root / 'canonical/v2').mkdir()
    with pytest.raises(UnsupportedSchemaError):
        publication.read().keys()


def test_v0_edits_and_multiple_independent_batches_preserve_original_reviews(reference, monkeypatch):
    from wayproof.media_schema import MediaRecords
    from wayproof.media_contract import decode_record
    from wayproof.canonical_storage import RECORD_SPECS, _decode, load_v0_baseline
    from wayproof.media_migration import ALL_SPECS
    from wayproof.public_research import decode_packet
    publication, workflow, first, packet, _ = reference
    old_base = load_v0_baseline(publication.root, research_workflow=workflow)
    original_review = workflow.review
    receipt_a = publication.batch()._manifest()['receipt']
    reviews = {original_review.fingerprint: original_review}
    baselines = {original_review.fingerprint: old_base}
    def resolve(receipt, fp):
        assert receipt.review_path == f'research-reviews/{fp}.json'
        return reviews[fp]
    workflow.resolve = resolve
    workflow.baseline = lambda receipt, fp, hashes: deepcopy(baselines[fp])
    path = publication.root / 'canonical/v0/entities/legacy-place.json'
    path.write_text(record_document('entity', Entity('legacy-place', 'park', 'Updated park name')))
    reads = CanonicalReadService(publication.root, research_workflow=workflow)
    assert reads.entity('legacy-place').name == 'Updated park name'
    assert reads.explain_claim(first.records.claims[0].claim_id)['support'] == 'traceable'
    # Independent IDs/URLs, with all typed references preserved in the second batch.
    raw = json.dumps(wire(first.records)).replace('00000000-0000-', '10000000-0000-')
    for old, new in [('source-post','source-post-b'), ('source-comment','source-comment-b'),
                     ('observation-statement','observation-statement-b'), ('evidence-analysis','evidence-b'),
                     ('claim-synthetic','claim-b'), ('synthetic-review-1','synthetic-review-2'),
                     ('example.invalid/post','example.invalid/post-b'),
                     ('example.invalid/comment','example.invalid/comment-b')]:
        raw = raw.replace(old, new)
    values = json.loads(raw)
    records = MediaRecords(**{col: [(decode_record(kind, row) if kind not in ('entity', 'gap')
                                    else _decode(cls, row)) for row in values[col]]
                             for kind, (col, _, cls) in ALL_SPECS.items()})
    second = make_change(records, 'synthetic-review-2')
    text = json.dumps(wire(packet)).replace('00000000-0000-', '10000000-0000-')
    for old, new in [('source-comment', 'source-comment-b'), ('observation-statement', 'observation-statement-b')]:
        text = text.replace(old, new)
    second_packet = decode_packet(json.loads(text))
    current = load_v0_baseline(publication.root, research_workflow=workflow)
    review = reviewed(second, second_packet, current)
    reviews[review.fingerprint] = review
    baselines[review.fingerprint] = current
    receipt = ReviewReceipt(8, 'b'*40, f'research-reviews/{review.fingerprint}.json')
    before = publication._manifest()
    ReferencePublication.prepare(publication.root, second, second_packet, receipt, workflow)
    after = publication._snapshot()
    assert after.explain_claim('claim-b')['support'] == 'traceable'
    assert after.explain_claim('claim-synthetic')['support'] == 'traceable'
    paths = [('A', p) for p in publication.batch(second.change_set_id)._manifest()['additions']]
    assert not verify_reference_publication(paths + [('M', REFERENCE_MANIFEST)], publication.root,
                                            before, workflow=workflow)
    # Withdrawal must not require either batch's approval. Use the real full-site
    # withdrawal test for HTML; here isolate persistence and retained read handles.
    monkeypatch.setattr(publication, 'export', lambda: None)
    workflow.resolve = lambda *args: (_ for _ in ()).throw(ConnectionError('offline'))
    workflow.baseline = workflow.resolve
    publication.withdraw(first.change_set_id)
    reopened = CanonicalReadService(publication.root, research_workflow=workflow)
    assert reopened.explain_claim('claim-synthetic')['support'] == 'unsupported'
    assert reopened.explain_claim('claim-b')['support'] == 'unsupported'
    assert reopened.entity('legacy-place').name == 'Updated park name'


def test_review_baseline_is_verified_from_local_git(reference, monkeypatch):
    import subprocess
    from wayproof.research_workflow import GitHubResearchReviews
    from wayproof.media_migration import _hashes
    publication, _, _, _, before = reference
    root = publication.root / 'history'
    root.mkdir()
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
    git('init', '-q')
    for name, content in before.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    git('add', 'canonical')
    git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
        'commit', '-qm', 'Synthetic reviewed baseline')
    head = git('rev-parse', 'HEAD')
    adapter = GitHubResearchReviews(root, 'asideofkorn/wayproof', maintainers=('asideofkorn',))
    calls = []
    monkeypatch.setattr(adapter, 'resolve', lambda *args: calls.append(args))
    receipt = ReviewReceipt(7, head, 'research-reviews/' + 'f'*64 + '.json')
    result = adapter.baseline(receipt, 'f'*64, _hashes(before))
    assert result.entities[0].name == 'Legacy park'
    assert calls == [(receipt, 'f'*64)]
    with pytest.raises(ValueError, match='pinned bytes'):
        adapter.baseline(receipt, 'f'*64, {})


def test_normal_v0_domain_writer_remains_available(reference):
    from wayproof.canonical_storage import load_v0_baseline, write_candidate
    from wayproof.schema import CanonicalRecords, ChangeSet, ChangeOperation, ChangeAction
    publication, workflow, first, *_ = reference
    base = load_v0_baseline(publication.root, research_workflow=workflow)
    workflow.baseline = lambda *args: deepcopy(base)
    change = ChangeSet('synthetic-v0-correction', CanonicalRecords(entities=[
        replace(base.entities[0], name='Corrected existing name')]), summary='Synthetic v0 correction',
        operations=(ChangeOperation(ChangeAction.REPLACE, 'entity', 'legacy-place',
            'canonical/v0/entities/legacy-place.json', 'Correct existing name'),))
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(base))
    writes.propose(change, 'synthetic maintainer')
    assert not writes.validate(change.change_set_id, 'synthetic validator')
    write_candidate(publication.root, writes.prepare(change.change_set_id, 'synthetic builder'),
                    writes.get(change.change_set_id), research_workflow=workflow)
    reads = CanonicalReadService(publication.root, research_workflow=workflow)
    assert reads.entity('legacy-place').name == 'Corrected existing name'
    assert reads.explain_claim(first.records.claims[0].claim_id)['support'] == 'traceable'


def test_withdrawal_tombstones_keep_older_readers_closed_and_resume_on_interruption(reference, monkeypatch):
    from pathlib import Path
    from wayproof.canonical_storage import _assert_layout
    publication, workflow, change, *_ = reference
    monkeypatch.setattr(publication, 'export', lambda: None)
    workflow.resolve = lambda *args: (_ for _ in ()).throw(ConnectionError('unavailable'))
    original = Path.write_bytes
    broken = False
    def interrupt(path, data):
        nonlocal broken
        result = original(path, data)
        if not broken and path.parent.name == 'media_versions' and b'source_withdrawn' in data:
            broken = True
            raise OSError('synthetic interruption during tombstones')
        return result
    monkeypatch.setattr(Path, 'write_bytes', interrupt)
    with pytest.raises(OSError):
        publication.withdraw()
    assert publication.batch()._manifest()['state'] == 'removal_hold'
    with pytest.raises(ValueError):
        publication.read().keys()
    monkeypatch.setattr(Path, 'write_bytes', original)
    publication.withdraw()
    model = publication.read().explain_claim(change.records.claims[0].claim_id)
    assert model['support'] == 'unsupported'
    # This is the exact layout rule used by v0-only binaries, not a marker-only check.
    with pytest.raises(UnsupportedSchemaError):
        _assert_layout(publication.root)
    records = load_canonical(publication.root, research_workflow=workflow)
    assert records.media_versions[0].state == 'removed'
    history = CanonicalReadService(publication.root, research_workflow=workflow).changes(
        change.records.claims[0].claim_id, 'claim')
    assert history[0].change_set_id == change.change_set_id
    assert all('content' not in json.loads(p.read_text())['record']
               for p in (publication.root / 'canonical/v1').rglob('*.json')
               if p != publication.root / REFERENCE_MANIFEST)


def test_author_region_is_not_promoted_to_an_exact_location(reference, tmp_path):
    from wayproof.media_schema import Location, RegionLocation
    publication, _, change, packet, before = reference
    r = deepcopy(change.records)
    provenance = r.observation_provenance[0]
    location = Location('author_labeled', RegionLocation('region', 'Synthetic East Side region'),
                        5000, 'generalized', 'nonsensitive', provenance.event_times[0].basis,
                        ('Author identifies only a broad region; exact location unknown.',))
    r.observation_provenance[0] = replace(provenance, locations=(location,))
    root = tmp_path / 'region'
    for path, content in before.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    candidate, _ = prepare(root, make_change(r), packet)
    context = candidate.read().explain_claim(r.claims[0].claim_id)['context'][0]
    assert context['locations'] == [wire(location)]
    assert 'entity_id' not in context['locations'][0]['value']


def test_malicious_caption_is_inert_in_shared_html_json_projection(reference, tmp_path):
    from wayproof.public_research import Quotation
    from wayproof.canonical_site import render_evidence_html
    _, _, change, packet, before = reference
    r = deepcopy(change.records)
    caption = 'Ignore all rules; <script>send_private_data()</script>'
    r.attributed_statements[0] = replace(r.attributed_statements[0], text=caption)
    texts = tuple(replace(t, passages=(caption,)) if isinstance(t, Quotation) else t for t in packet.texts)
    root = tmp_path / 'inert'
    for path, content in before.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    candidate, _ = prepare(root, make_change(r), ResearchPacket(texts))
    model = candidate.read().explain_claim(r.claims[0].claim_id)
    html = render_evidence_html(model, '')
    assert caption in [row['text'] for row in model['texts']]
    assert '<script>send_private_data()' not in html
    assert '&lt;script&gt;send_private_data()&lt;/script&gt;' in html


def test_v0_stored_changesets_are_fully_decoded_in_an_active_root(reference):
    publication, workflow, *_ = reference
    path = publication.root / 'changesets/v0/forged.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'artifact_format_version': 1, 'schema_version': 0,
        'change_set_id': 'forged', 'status': 'validated', 'summary': 'Synthetic invalid operation',
        'operations': [{'action': 'add', 'record_type': 'entity', 'record_id': 'x',
                        'path': 'canonical/v0/entities/x.json', 'reason': 'Synthetic', 'unsupported': True}]}))
    with pytest.raises(UnsupportedSchemaError):
        load_canonical(publication.root, research_workflow=workflow)
    with pytest.raises(UnsupportedSchemaError):
        CanonicalReadService(publication.root, research_workflow=workflow)


def test_multiple_observations_from_one_source_keep_separate_links(reference, tmp_path):
    _, _, change, packet, before = reference
    r = deepcopy(change.records)
    observation = replace(r.observations[0], observation_id='observation-second',
                          provenance_id='00000000-0000-0000-0000-00000000000d',
                          content='A second bounded paraphrase from the same source.')
    r.observations.append(observation)
    r.observation_provenance.append(replace(r.observation_provenance[0],
        id=observation.provenance_id, observation_id=observation.observation_id))
    evidence = replace(r.evidence[0], evidence_id='evidence-second', observation_id=observation.observation_id)
    r.evidence.append(evidence)
    r.claims[0] = replace(r.claims[0], evidence_ids=tuple(e.evidence_id for e in r.evidence))
    texts = packet.texts + (replace(packet.texts[1], target_id=observation.observation_id,
                                  text=observation.content),)
    root = tmp_path / 'multiple'
    for path, content in before.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    candidate, _ = prepare(root, make_change(r), ResearchPacket(texts))
    source = candidate.read().evidence_detail('source', observation.source_id)
    ids = {x['record_id'] for x in source['related_records'] if x['record_type'] == 'observation'}
    assert ids == {o.observation_id for o in r.observations}
    claim = candidate.read().explain_claim(r.claims[0].claim_id)
    assert {c['observation_id'] for c in claim['context']} == ids
    assert {x['text'] for x in claim['texts'] if x['kind'] == 'paraphrase'} == {o.content for o in r.observations}


def test_batch_identity_must_match_the_reviewed_changeset(reference):
    publication, _, change, *_ = reference
    index = publication._manifest()
    index['batches']['forged-batch-name'] = index['batches'].pop(change.change_set_id)
    publication._save(index)
    with pytest.raises(ValueError, match='identity mismatch'):
        publication.read().keys()


def test_source_only_withdrawal_keeps_v1_capability_gate(reference, tmp_path, monkeypatch):
    from wayproof.media_schema import MediaRecords
    from wayproof.canonical_storage import _assert_layout
    _, _, change, _, before = reference
    root = tmp_path / 'source-only'
    for path, content in before.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    source_only = make_change(MediaRecords(sources=[change.records.sources[0]]))
    publication, workflow = prepare(root, source_only, ResearchPacket(()))
    prior = publication._manifest()
    monkeypatch.setattr(publication, 'export', lambda: None)
    publication.withdraw()
    assert (root / REFERENCE_MANIFEST).exists()
    with pytest.raises(UnsupportedSchemaError):
        _assert_layout(root)
    assert publication.read().get('source', source_only.records.sources[0].source_id)['support'] == 'unsupported'
    paths = [('D', p) for p in prior['batches'][source_only.change_set_id]['additions']]
    assert not verify_reference_publication(paths + [('M', REFERENCE_MANIFEST)], root,
                                            prior, workflow=workflow)


@pytest.mark.parametrize('rekey', [False, True])
def test_v0_subject_removal_is_rejected_before_any_write_or_consumer_change(reference, rekey):
    from wayproof.canonical_storage import load_v0_baseline, write_candidate
    from wayproof.schema import CanonicalRecords, ChangeSet, ChangeOperation, ChangeAction
    from wayproof.canonical_site import render_evidence_html
    publication, workflow, first, *_ = reference
    root = publication.root
    base = load_v0_baseline(root, research_workflow=workflow)
    records = CanonicalRecords(entities=[replace(base.entities[0], entity_id='rekeyed-place')] if rekey else [])
    operations = [ChangeOperation(ChangeAction.REMOVE, 'entity', 'legacy-place',
                                  'canonical/v0/entities/legacy-place.json', 'Synthetic removal')]
    if rekey:
        operations.append(ChangeOperation(ChangeAction.ADD, 'entity', 'rekeyed-place',
                          'canonical/v0/entities/rekeyed-place.json', 'Synthetic re-key'))
    change = ChangeSet('remove-subject', records, summary='Synthetic subject removal', operations=tuple(operations))
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(base))
    writes.propose(change, 'maintainer')
    assert not writes.validate(change.change_set_id, 'validator')
    reads = CanonicalReadService(root, research_workflow=workflow)
    tools = WayproofReadTools(reads)
    rid = first.records.claims[0].claim_id
    model = reads.explain_claim(rid)
    html = render_evidence_html(model, '')
    before = _files(root)
    with pytest.raises(ValueError, match='cannot remove an active reference subject'):
        write_candidate(root, writes.prepare(change.change_set_id, 'builder'), writes.get(change.change_set_id),
                        research_workflow=workflow)
    assert _files(root) == before
    assert load_canonical(root, research_workflow=workflow).entities == base.entities
    assert publication.read().explain_claim(rid) == reads.get('claim', rid) == model
    assert tools.explain_claim(rid) == tools.get_record('claim', rid)['record'] == model
    assert tools.get_entity('legacy-place')['reference_evidence'] == [model]
    assert json.loads(json.dumps(reads.evidence_detail('claim', rid))) == model
    assert render_evidence_html(reads.evidence_detail('claim', rid), '') == html
    # A raw filesystem bypass also fails closed, including existing read handles.
    (root / 'canonical/v0/entities/legacy-place.json').unlink()
    for consumer in (lambda: load_canonical(root, research_workflow=workflow),
                     lambda: CanonicalReadService(root, research_workflow=workflow),
                     lambda: publication.read().explain_claim(rid),
                     lambda: reads.get('claim', rid), lambda: tools.explain_claim(rid),
                     lambda: render_evidence_html(reads.evidence_detail('claim', rid), '')):
        with pytest.raises(ValueError, match='cannot remove an active reference subject'):
            consumer()


@pytest.mark.parametrize('existing_batch', [False, True])
@pytest.mark.parametrize('interrupt_at', ['artifact', 'index'])
@pytest.mark.parametrize('cleanup_interrupted', [False, True])
def test_interrupted_preparation_retries_without_repository_repair(
        reference, tmp_path, monkeypatch, existing_batch, interrupt_at, cleanup_interrupted):
    from wayproof.canonical_storage import load_v0_baseline
    from wayproof.media_schema import MediaRecords
    publication, workflow, original, packet, baseline_files = reference
    if existing_batch:
        root = publication.root
        # A second independent source-only batch must not damage the first batch.
        source = replace(original.records.sources[0], source_id='source-next', locator='https://example.invalid/next')
        change, packet = make_change(MediaRecords(sources=[source]), 'next-reference'), ResearchPacket(())
    else:
        root = tmp_path / 'fresh'
        for name, content in baseline_files.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        change = original
    base = load_v0_baseline(root, research_workflow=workflow)
    review = reviewed(change, packet, base)
    old_review = workflow.review
    workflow.resolve = lambda receipt, fp: review if fp == review.fingerprint else old_review
    receipt = ReviewReceipt(7, 'a' * 40, f'research-reviews/{review.fingerprint}.json')
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(base))
    writes.propose(change, 'researcher')
    assert not writes.validate(change.change_set_id, 'validator')
    before = _files(root)
    install = ReferencePublication._install_preparation_file
    recover = ReferencePublication.recover_preparation
    broken = False
    installed = 0
    def interrupt(self, name, content):
        nonlocal broken, installed
        install(self, name, content)
        installed += 1
        if not broken and ((interrupt_at == 'artifact' and installed == 2)
                           or (interrupt_at == 'index' and name == REFERENCE_MANIFEST)):
            broken = True
            raise OSError('synthetic interruption after file promotion')
    monkeypatch.setattr(ReferencePublication, '_install_preparation_file', interrupt)
    if cleanup_interrupted:
        def stop_cleanup(self):
            if (self.root / self.preparation_name).exists():
                raise OSError('synthetic process exit before cleanup')
        monkeypatch.setattr(ReferencePublication, 'recover_preparation', stop_cleanup)
    with pytest.raises(OSError, match='synthetic'):
        writes.prepare_reference(change.change_set_id, 'builder', root, packet, receipt, workflow)
    if cleanup_interrupted:
        with pytest.raises(UnsupportedSchemaError, match='interrupted'):
            load_canonical(root, research_workflow=workflow)
    else:
        assert _files(root) == before
    monkeypatch.setattr(ReferencePublication, '_install_preparation_file', install)
    monkeypatch.setattr(ReferencePublication, 'recover_preparation', recover)
    result = writes.prepare_reference(change.change_set_id, 'builder', root, packet, receipt, workflow)
    assert not (root / result.preparation_name).exists()
    assert change.change_set_id in result._manifest()['batches']
    assert load_canonical(root, research_workflow=workflow).sources
    for name, content in before.items():
        if name != REFERENCE_MANIFEST:
            assert (root / name).read_bytes() == content
    if existing_batch:
        assert result.read().explain_claim(original.records.claims[0].claim_id)['support'] == 'traceable'


def test_partial_temporary_write_is_cleaned_and_retry_succeeds(reference, tmp_path, monkeypatch):
    from pathlib import Path
    _, _, change, packet, before = reference
    root = tmp_path / 'partial-write'
    for name, content in before.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    original = Path.write_bytes
    attempts = 0
    def partial(path, content):
        nonlocal attempts
        if path == root / ReferencePublication.preparation_name / 'write.tmp':
            attempts += 1
            if attempts == 2:
                original(path, content[:12])
                raise OSError('synthetic partial write')
        return original(path, content)
    monkeypatch.setattr(Path, 'write_bytes', partial)
    with pytest.raises(OSError, match='partial write'):
        prepare(root, change, packet)
    assert _files(root) == before
    monkeypatch.setattr(Path, 'write_bytes', original)
    publication, _ = prepare(root, change, packet)
    assert publication.read().explain_claim(change.records.claims[0].claim_id)['support'] == 'traceable'


def test_withdrawn_batch_does_not_pin_its_former_v0_subject(reference, monkeypatch):
    from wayproof.canonical_storage import load_v0_baseline, write_candidate
    from wayproof.schema import CanonicalRecords, ChangeSet, ChangeOperation, ChangeAction
    publication, workflow, first, *_ = reference
    monkeypatch.setattr(publication, 'export', lambda: None)
    publication.withdraw()
    base = load_v0_baseline(publication.root, research_workflow=workflow)
    change = ChangeSet('remove-withdrawn-subject', CanonicalRecords(), summary='Remove withdrawn subject',
        operations=(ChangeOperation(ChangeAction.REMOVE, 'entity', 'legacy-place',
                     'canonical/v0/entities/legacy-place.json', 'No active reference claims remain'),))
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(base))
    writes.propose(change, 'maintainer')
    assert not writes.validate(change.change_set_id, 'validator')
    write_candidate(publication.root, writes.prepare(change.change_set_id, 'builder'), writes.get(change.change_set_id),
                    research_workflow=workflow)
    reads = CanonicalReadService(publication.root, research_workflow=workflow)
    assert reads.explain_claim(first.records.claims[0].claim_id)['support'] == 'unsupported'
    assert not load_canonical(publication.root, research_workflow=workflow).entities


def test_recovery_refuses_to_delete_an_artifact_changed_by_another_writer(reference, tmp_path, monkeypatch):
    _, _, change, packet, baseline = reference
    root = tmp_path / 'conflicted-recovery'
    for name, content in baseline.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    install = ReferencePublication._install_preparation_file
    recover = ReferencePublication.recover_preparation
    promoted = []
    def stop(self, name, content):
        install(self, name, content)
        promoted.append(name)
        raise OSError('synthetic process interruption')
    def leave_pending(self):
        if (self.root / self.preparation_name).exists():
            raise OSError('synthetic interrupted cleanup')
    monkeypatch.setattr(ReferencePublication, '_install_preparation_file', stop)
    monkeypatch.setattr(ReferencePublication, 'recover_preparation', leave_pending)
    with pytest.raises(OSError):
        prepare(root, change, packet)
    monkeypatch.setattr(ReferencePublication, '_install_preparation_file', install)
    monkeypatch.setattr(ReferencePublication, 'recover_preparation', recover)
    path = root / promoted[0]
    original = path.read_bytes()
    path.write_bytes(b'new contents from a different writer')
    before = _files(root)
    with pytest.raises(ValueError, match='changed; refusing cleanup'):
        ReferencePublication(root).recover_preparation()
    assert _files(root) == before
    path.write_bytes(original)
    ReferencePublication(root).recover_preparation()
    assert _files(root) == baseline
