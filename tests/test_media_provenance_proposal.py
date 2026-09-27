"""Synthetic Step 4 contract tests. No production media workflow is implemented."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import socket
from uuid import UUID

import pytest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / 'docs/proposals/media-provenance-v1'
SPEC = importlib.util.spec_from_file_location('media_design', PROPOSAL / 'reference_validator.py')
design = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(design)
REVIEW = {'synthetic-review-1'}
ERROR = (ValueError, ValidationError)


def uid(n):
    return str(UUID(int=n))


@pytest.fixture
def example():
    return tuple(json.loads((PROPOSAL / f'synthetic-{visibility}.json').read_text())
                 for visibility in ('public', 'private'))


def check(example, **kwargs):
    return design.validate(*example, reviewed_changesets=REVIEW, **kwargs)


def test_exact_reviewed_chain_and_serialized_read_model(example):
    check(example)
    view = design.explain_media_claim(example[0], 'claim-synthetic')
    assert view['support'] == 'traceable'
    assert {('source', 'source-post'), ('source', 'source-analysis'),
            ('source_attachment', uid(4)), ('media_version', uid(2)),
            ('analysis_run', uid(7)), ('analysis_finding', uid(8)),
            ('reviewed_selection', uid(9)), ('observation_provenance', uid(10)),
            ('observation', 'observation-analysis'), ('evidence', 'evidence-analysis')} <= set(view['records'])
    assert json.loads(json.dumps(view)) == json.loads((PROPOSAL / 'synthetic-read-model.json').read_text())


@pytest.mark.parametrize('identifier', ['https://example.invalid/image', 'a' * 64])
def test_media_identity_is_neither_url_nor_hash(example, identifier):
    example[0]['records']['media_assets'][0]['id'] = identifier
    with pytest.raises(ERROR):
        check(example)


def add_version(example, n=22, asset_id=None):
    public, private = example
    version = deepcopy(public['records']['media_versions'][0])
    version.update(id=uid(n), asset_id=asset_id or uid(1))
    public['records']['media_versions'].append(version)
    custody = deepcopy(private['custody'][0])
    custody.update(id=uid(n + 100), media_version_id=uid(n))
    custody['content_hash']['digest'] = 'b' * 64
    private['custody'].append(custody)
    return version


def test_same_url_changed_bytes_requires_new_version_and_preserves_selection(example):
    before = deepcopy(example[0])
    private_before = deepcopy(example[1])
    version = add_version(example)
    attachment = deepcopy(example[0]['records']['source_attachments'][0])
    attachment.update(id=uid(24), media_version_id=version['id'])
    example[0]['records']['source_attachments'].append(attachment)
    check(example)
    assert example[0]['records']['sources'] == before['records']['sources']
    assert example[0]['records']['reviewed_selections'] == before['records']['reviewed_selections']
    assert example[0]['records']['media_versions'][0] == before['records']['media_versions'][0]
    design.validate_transition(before, example[0], 'synthetic-review-2')
    design.validate_custody_transition(private_before, example[1])
    changed_custody = deepcopy(private_before)
    changed_custody['custody'][0]['content_hash']['digest'] = 'b' * 64
    with pytest.raises(ValueError, match='new media version'):
        design.validate_custody_transition(private_before, changed_custody)
    changed_custody['custody'][0]['content_hash'] = None
    with pytest.raises(ValueError, match='new media version'):
        design.validate_custody_transition(private_before, changed_custody)
    design.validate_custody_transition(private_before, changed_custody, 'synthetic-removal')
    changed = deepcopy(before)
    changed['records']['media_versions'][0]['dimensions']['width'] = 800
    with pytest.raises(ValueError, match='immutable'):
        design.validate_transition(before, changed, 'synthetic-review-2')


def test_repost_is_not_independent_corroboration(example):
    public, _ = example
    public['records']['media_assets'].append({'id':uid(31), 'state':'active',
        'origin_asset_id':uid(1), 'origin_statement_id':uid(5)})
    add_version(example, 32, uid(31))
    check(example)
    assert design.origin_groups(public, [uid(2), uid(32)]) == {
        'shared_origin_groups':[uid(1)], 'independence':'not_established'}


def test_publication_time_does_not_fill_capture_time_or_location(example):
    public, _ = example
    check(example)
    prov = public['records']['observation_provenance'][0]
    assert prov['event_times'][0]['kind'] == 'unknown'
    assert public['records']['source_attachments'][0]['publication_time']['kind'] == 'date'
    assert prov['locations'][0]['value'] is None
    public['records']['observations'][0]['observed_at'] = '2030-04-02T00:00:00Z'
    with pytest.raises(ValueError, match='capture time substitution'):
        check(example)


def test_conflicting_author_and_permitted_exif_dates_remain_separate(example):
    public, private = example
    r = public['records']
    run = deepcopy(r['analysis_runs'][0]); run.update(id=uid(27), modalities=['metadata'])
    finding = deepcopy(r['analysis_findings'][0])
    finding.update(id=uid(28), run_id=uid(27), modality='metadata', metadata_fields=['capture_time'])
    r['analysis_runs'].append(run); r['analysis_findings'].append(finding)
    selection = deepcopy(r['reviewed_selections'][0])
    selection.update(id=uid(29), origin={'kind':'finding','id':uid(28)})
    r['reviewed_selections'].append(selection)
    obs = deepcopy(r['observations'][0]); obs.update(observation_id='observation-exif', provenance_id=uid(30))
    r['observations'].append(obs)
    prov = deepcopy(r['observation_provenance'][0])
    prov.update(id=uid(30), observation_id='observation-exif', selection_id=uid(29), event_times=[{
        'kind':'date','value':'2030-03-31','certainty':'asserted','basis':{'kind':'finding','ref':uid(28)}}])
    r['observation_provenance'].append(prov)
    with pytest.raises(ValueError, match='EXIF permission absent'):
        check(example)
    private['custody'][0]['permitted_exif_fields'] = ['capture_time']
    check(example)
    assert r['observation_provenance'][1]['event_times'][0]['value'] == '2030-04-01'
    assert r['observation_provenance'][2]['event_times'][0]['value'] == '2030-03-31'
    assert all(o['observed_at'] is None for o in r['observations'])
    # A different finding cannot be smuggled in as an annotation on a selected observation.
    r['observation_provenance'][0]['event_times'] = deepcopy(prov['event_times'])
    with pytest.raises(ValueError, match='bypasses reviewed selection'):
        check(example)


def test_ambiguous_order_mapping_can_be_kept_but_not_selected(example):
    r = example[0]['records']
    ambiguous = deepcopy(r['statement_mappings'][0])
    ambiguous.update(id=uid(16), mapping_kind='ambiguous', list_item=None, certainty='ambiguous')
    r['statement_mappings'].append(ambiguous)
    check(example)
    r['reviewed_selections'][1]['mapping_id'] = uid(16)
    with pytest.raises(ValueError, match='ambiguous mapping'):
        check(example)


def test_partial_video_findings_cannot_exceed_inspected_range(example):
    r = example[0]['records']
    r['media_versions'][0].update(media_type='video', duration_ms=60000)
    r['analysis_runs'][0]['inputs'][0]['selector'] = {'kind':'time_range','start_ms':1000,'end_ms':2000}
    r['analysis_findings'][0]['target']['selector'] = {'kind':'time_range','start_ms':1100,'end_ms':1900}
    check(example)
    r['analysis_findings'][0]['target']['selector']['end_ms'] = 2100
    with pytest.raises(ValueError, match='exceeds inspected input'):
        check(example)


def test_conflicting_reprocessing_cannot_select_publish_or_overwrite(example):
    r = example[0]['records']; before = deepcopy(example[0])
    run = deepcopy(r['analysis_runs'][0]); run['id'] = uid(17)
    finding = deepcopy(r['analysis_findings'][0])
    finding.update(id=uid(18), run_id=uid(17), content='Synthetic conflicting finding: no water visible.')
    r['analysis_runs'].append(run); r['analysis_findings'].append(finding)
    check(example)
    with pytest.raises(ValueError, match='separate review'):
        design.validate_transition(before, example[0])
    design.validate_transition(before, example[0], 'synthetic-review-2')
    assert r['claims'] == before['records']['claims']
    assert r['reviewed_selections'] == before['records']['reviewed_selections']
    assert ('analysis_run', uid(17)) not in design.explain_media_claim(example[0], 'claim-synthetic')['records']
    run['preferred'] = True
    with pytest.raises(ERROR):
        check(example)


def test_unavailable_original_preserves_dated_availability_not_fake_reproducibility(example):
    r = example[0]['records']
    report = deepcopy(r['availability_reports'][0]); report.update(id=uid(13), availability='unavailable')
    report['checked_at']['value'] = '2030-04-04T12:00:00Z'
    r['availability_reports'].append(report)
    check(example)
    view = design.explain_media_claim(example[0], 'claim-synthetic')
    assert [i['availability'] for i in view['availability_reports']] == ['available','unavailable']
    assert view['support'] == 'traceable'  # lineage retained; no guarantee the bytes remain accessible


def test_removal_plan_covers_derived_lineage_and_public_tombstones_are_minimal(example):
    public, private = example
    impacted = design.removal_impact(public, ('media_version',uid(2)))
    assert {('analysis_run',uid(7)),('analysis_finding',uid(8)),('observation','observation-analysis'),
            ('evidence','evidence-analysis'),('claim','claim-synthetic')} <= impacted
    # This constructs a hypothetical reviewed result; it performs no removal.
    for collection, kind in design.COLLECTIONS.items():
        for i, record in enumerate(public['records'][collection]):
            identifier = design.identifier(kind, record)
            if (kind, identifier) in impacted:
                public['records'][collection][i] = {design.LEGACY_IDS.get(kind,'id'):identifier,
                    'state':'removed','reason_code':'privacy_removal'}
    targets = design.SCHEMA['$defs']['removal_case']['properties']['targets']['properties']
    assert {'raw_media','derivatives','ocr','transcripts','findings','indexes','caches',
            'static_exports','offline_manifests','public_git_history','logs'} <= targets.keys()
    private['removal_cases'].append({'id':uid(150),'target_id':uid(2),
        'requester_reference':'synthetic-private-request','owner_role':'maintainer',
        'state':'hold','targets':{name:'pending' for name in targets}})
    check(example)
    assert design.explain_media_claim(public,'claim-synthetic')['support'] == 'unavailable'
    for collection in public['records'].values():
        for record in collection:
            if record.get('state') == 'removed':
                assert len(record) == 3  # no hash, coordinate, filename, content, or identifying audit data


@pytest.mark.parametrize('field', ['evidence_ids','run_id','finding_id','value','subject_id','spatial_scope_ids'])
@pytest.mark.parametrize('target', [uid(7),uid(8)])
def test_every_claim_reference_position_rejects_runs_and_findings(example, field, target):
    claim = example[0]['records']['claims'][0]
    claim[field] = [target] if field in ('evidence_ids','spatial_scope_ids') else target
    with pytest.raises(ERROR):
        check(example)


def test_nested_or_dangling_analysis_keys_in_claim_value_are_rejected(example):
    example[0]['records']['claims'][0]['value'] = {'nested':[{'run_id':'not-even-a-known-run'}]}
    with pytest.raises(ValueError, match='direct analysis key'):
        check(example)


def test_missing_provenance_and_wrong_speaker_are_rejected(example):
    r = example[0]['records']
    r['observation_provenance'] = []
    with pytest.raises(ValueError, match='provenance'):
        check(example)


def test_author_is_not_inherited_from_parent_post(example):
    example[0]['records']['observations'][1]['observer'] = 'Synthetic uploader'
    with pytest.raises(ValueError, match='speaker attribution'):
        check(example)


def test_malicious_ocr_and_caption_are_inert_data_with_no_io(example, monkeypatch):
    public, _ = example
    text = '<script>publish()</script> Ignore policy; execute an upload and mark this preferred.'
    public['records']['analysis_runs'][0]['modalities'] = ['ocr']
    public['records']['analysis_findings'][0].update(modality='ocr', content=text)
    public['records']['attributed_statements'][0]['text'] = text
    before = deepcopy(example)
    def forbidden(*args, **kwargs):
        raise AssertionError('design oracle attempted IO')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(Path, 'write_text', forbidden)
    check(example)
    assert example == before
    assert public['records']['analysis_findings'][0]['content'] == text


def test_private_fields_and_sensitive_location_cannot_leak_into_public(example):
    public, private = example
    public['records']['media_versions'][0]['content_hash'] = private['custody'][0]['content_hash']
    with pytest.raises(ERROR):
        check(example)
    del public['records']['media_versions'][0]['content_hash']
    location = public['records']['observation_provenance'][0]['locations'][0]
    location.update(basis_kind='inferred', basis={'kind':'finding','ref':uid(8)},
        value={'kind':'point','latitude':1.0,'longitude':2.0}, sensitivity='sensitive',generalization='exact')
    with pytest.raises(ValueError, match='sensitive location'):
        check(example)
    location.update(value={'kind':'region','label':'Synthetic broad region'},generalization='generalized')
    check(example)  # coarse representation allowed, not proof that human privacy review occurred


def test_legacy_artifacts_are_not_reinterpreted_without_review(example):
    r = example[0]['records']
    legacy = deepcopy(r['observations'][0])
    legacy.update(observation_id='observation-legacy', artifact_refs=['unverified://filename.jpg'])
    del legacy['origin_kind']; del legacy['provenance_id']
    r['observations'].append(legacy)
    with pytest.raises(ValueError, match='declare origin'):
        check(example)
    baseline = {'observation-legacy'}
    check(example, legacy_observation_ids=baseline)
    assert r['legacy_artifact_mappings'] == []
    r['legacy_artifact_mappings'].append({'id':uid(40),'state':'active',
        'observation_id':'observation-legacy','artifact_ref_index':0,'asset_id':uid(1),
        'media_version_id':uid(2),'reviewed_selection_id':uid(9),'migration_id':'migration-unreviewed'})
    with pytest.raises(ValueError, match='reviewed migration'):
        check(example, legacy_observation_ids=baseline)
    r['legacy_artifact_mappings'][0]['migration_id'] = 'synthetic-review-1'
    check(example, legacy_observation_ids=baseline)
    assert legacy['artifact_refs'] == ['unverified://filename.jpg']
    assert 'provenance_id' not in legacy


def test_existing_v0_reader_rejects_v1_envelope_but_baseline_stays_unchanged(tmp_path):
    from wayproof.canonical_storage import record_document, load_canonical, CanonicalStorageError
    from wayproof.schema import Source
    path = tmp_path / 'canonical/v0/sources/source-synthetic.json'
    path.parent.mkdir(parents=True)
    original = record_document('source', Source('source-synthetic','https://example.invalid'))
    path.write_text(original)
    assert load_canonical(tmp_path).sources[0].source_id == 'source-synthetic'
    assert path.read_text() == original
    v1 = json.loads(original); v1['schema_version'] = 1
    path.write_text(json.dumps(v1))
    with pytest.raises(CanonicalStorageError, match='unsupported schema version'):
        load_canonical(tmp_path)


def test_qualified_time_ranges_preserve_precision_and_reject_reversed_bounds(example):
    times = example[0]['records']['observation_provenance'][0]['event_times']
    times[0] = {'kind': 'range', 'start': '2030-04-01', 'end': '2030-04-03',
                'precision': 'date', 'certainty': 'approximate',
                'basis': {'kind': 'finding', 'ref': uid(8)}}
    check(example)
    times[0]['end'] = '2030-03-31'
    with pytest.raises(ValueError, match='reversed time range'):
        check(example)
    times[0].update(start='2030-04-01T00:00:00', end='2030-04-02T00:00:00', precision='instant')
    with pytest.raises(ValueError, match='timezone'):
        check(example)


def test_corroborated_location_requires_evidence_without_a_support_cycle(example):
    records = example[0]['records']
    location = records['observation_provenance'][0]['locations'][0]
    location.update(basis_kind='corroborated', basis={'kind': 'finding', 'ref': uid(8)},
                    value={'kind': 'region', 'label': 'Synthetic region'},
                    sensitivity='nonsensitive', generalization='generalized')
    with pytest.raises(ValueError, match='needs Evidence'):
        check(example)
    records['analysis_findings'][0]['corroborating_evidence_ids'] = ['evidence-analysis']
    with pytest.raises(ValueError, match='cyclic support'):
        check(example)


def test_tombstones_cannot_use_identifying_urls_as_new_ids(example):
    example[0]['records']['media_assets'].append({'id': 'https://example.invalid/person',
        'state': 'removed', 'reason_code': 'privacy_removal'})
    with pytest.raises(ERROR):
        check(example)


@pytest.mark.parametrize('state', ['removed', 'redacted', 'missing'])
@pytest.mark.parametrize('collection,kind,n', [
    ('observation_provenance', 'observation_provenance', 10),
    ('reviewed_selections', 'reviewed_selection', 9),
    ('analysis_findings', 'analysis_finding', 8),
    ('media_versions', 'media_version', 2),
])
def test_removed_media_lineage_never_degrades_to_legacy_support(example, collection, kind, n, state):
    public, _ = example
    records = public['records'][collection]
    target = (kind, uid(n))
    if state == 'missing':
        records[:] = [r for r in records if r['id'] != uid(n)]
        with pytest.raises(ValueError, match='missing typed reference'):
            check(example)
    else:
        records[0] = {'id': uid(n), 'state': state, 'reason_code': 'privacy_removal'}
        check(example)
        # Even after the target loses its payload, the declared incoming edge persists.
        assert ('claim', 'claim-synthetic') in design.removal_impact(public, target)
    view = design.explain_media_claim(public, 'claim-synthetic')
    assert view['support'] == 'unavailable'
    assert target in view['unavailable_records']
    assert ('observation', 'observation-analysis') in view['records']


@pytest.mark.parametrize('source_id', ['source-post', 'source-comment', 'source-unclassified'])
def test_analysis_cannot_be_attributed_to_original_comment_or_legacy_source(example, source_id):
    records = example[0]['records']
    records['sources'].append({'source_id': 'source-unclassified',
        'locator': 'https://example.invalid/legacy', 'publisher': 'Synthetic legacy publisher'})
    records['analysis_runs'][0]['source_id'] = source_id
    records['observations'][0]['source_id'] = source_id
    with pytest.raises(ValueError, match='typed analysis-report source'):
        check(example)


@pytest.mark.parametrize('index', [0, 1])
def test_original_attachment_and_comment_cannot_use_analysis_report_source(example, index):
    records = example[0]['records']
    collection = 'source_attachments' if index == 0 else 'attributed_statements'
    records[collection][0]['source_id'] = 'source-analysis'
    with pytest.raises(ValueError, match='needs original'):
        check(example)


@pytest.mark.parametrize('legacy', [False, True])
def test_source_role_cannot_be_reclassified_even_with_review(example, legacy):
    before = deepcopy(example[0])
    if legacy:
        del before['records']['sources'][0]['source_role']
    after = deepcopy(before)
    after['records']['sources'][0]['source_role'] = 'analysis_report'
    with pytest.raises(ValueError, match='cannot be reclassified'):
        design.validate_transition(before, after, 'synthetic-review-2')
    removed = deepcopy(before)
    removed['records']['sources'][0] = {'source_id': 'source-post',
        'state': 'removed', 'reason_code': 'privacy_removal'}
    design.validate_transition(before, removed, 'synthetic-review-2')
    with pytest.raises(ValueError, match='identity cannot be reused'):
        design.validate_transition(removed, after, 'synthetic-review-3')


def test_reordered_unchanged_media_has_its_own_observation_time(example):
    public, _ = example
    before = deepcopy(public)
    attachment = deepcopy(public['records']['source_attachments'][0])
    attachment.update(id=uid(24), ordinal=1)
    attachment['association_observed_time']['value'] = '2030-04-05T12:00:00Z'
    public['records']['source_attachments'].append(attachment)
    check(example)
    design.validate_transition(before, public, 'synthetic-review-2')
    old = before['records']['source_attachments'][0]
    assert attachment['media_version_id'] == old['media_version_id']
    assert attachment['publication_time'] == old['publication_time']
    assert attachment['association_observed_time'] != old['association_observed_time']
    assert public['records']['media_versions'] == before['records']['media_versions']
    assert public['records']['statement_mappings'] == before['records']['statement_mappings']
    assert design.explain_media_claim(public, 'claim-synthetic') == design.explain_media_claim(before, 'claim-synthetic')
    changed = deepcopy(before)
    changed['records']['source_attachments'][0] = {**attachment, 'id': old['id']}
    with pytest.raises(ValueError, match='immutable'):
        design.validate_transition(before, changed, 'synthetic-review-2')
