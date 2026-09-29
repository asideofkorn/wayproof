"""Synthetic-only processing, review admission, and immutable provenance boundaries."""
from copy import deepcopy
from dataclasses import replace, FrozenInstanceError
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

import pytest

from test_media_contract_boundaries import draft, make_change
from test_public_research_policy import reviewed
from wayproof.analysis_service import SyntheticAnalysisService, SyntheticReply, SyntheticFinding
from wayproof.media_schema import (MediaRecords, Target, WholeImage, FrameSelector, TimeSelector,
    ReviewedSelection, Origin, InstantTime, UnknownTime, Basis, Location,
    ObservationProvenance, MediaObservation)
from wayproof.media_contract import wire
from wayproof.schema import Evidence, Claim, CanonicalRecords
from wayproof.public_research import FindingText, Quotation, ResearchPacket, fingerprint
from wayproof.research_workflow import ReviewReceipt
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository, PreparationRejected
from wayproof.media_migration import ReferencePublication
from wayproof.mcp_server import WayproofReadTools


class Reviews:
    def __init__(self):
        self.values = {}
        self.revoked = set()

    def resolve(self, receipt, fp):
        if fp in self.revoked or receipt.review_path != f'research-reviews/{fp}.json':
            raise ValueError('review unavailable')
        return self.values[fp]


@pytest.fixture
def analysis_seed(draft):
    r = draft.records
    version = replace(r.media_versions[0], identity_basis='unverifiable', reproducibility='unavailable')
    other_asset = replace(r.media_assets[0], id='10000000-0000-0000-0000-000000000001')
    other_version = replace(version, id='10000000-0000-0000-0000-000000000002', asset_id=other_asset.id)
    other_source = replace(r.sources[0], source_id='source-other', locator='https://example.invalid/other')
    other_attachment = replace(r.source_attachments[0], id='10000000-0000-0000-0000-000000000004',
        source_id=other_source.source_id, asset_id=other_asset.id, media_version_id=other_version.id,
        publication_time=replace(r.source_attachments[0].publication_time, basis=Basis('source', other_source.source_id)))
    return MediaRecords(entities=r.entities, sources=[r.sources[0], r.sources[2], other_source],
        media_assets=[r.media_assets[0], other_asset], media_versions=[version, other_version],
        source_attachments=[r.source_attachments[0], other_attachment])


@pytest.fixture
def session(analysis_seed):
    reviews = Reviews()
    service = SyntheticAnalysisService(analysis_seed, reviews,
        clock=lambda: datetime(2030, 4, 4, 12, tzinfo=timezone.utc))
    targets = tuple(Target(a.media_version_id, a.id, WholeImage('whole')) for a in analysis_seed.source_attachments)
    return service, reviews, targets


def reply(target, content='Synthetic water is visible.', modality='visual', **changes):
    return replace(SyntheticReply('available', (target.media_version_id,), 'succeeded',
        (SyntheticFinding(target, modality, content, 'unresolved', ('No real media was inspected.',)),)), **changes)


def proposal(service, result, change_id='analysis-review-a'):
    records = service.proposal_records((result.id,))
    texts = [Quotation('quotation', 'attributed_statement', s.id, s.source_id, (s.text,), False, False)
             for s in records.attributed_statements]
    for n, finding in enumerate(result.findings):
        selection = ReviewedSelection(str(uuid4()), 'active', Origin('finding', finding.id), None,
            (finding.target.media_version_id,), 'maintainer',
            InstantTime('instant', '2030-04-05T12:00:00Z', 'exact', Basis('clock', None)), change_id)
        oid, eid, cid = f'{change_id}-observation-{n}', f'{change_id}-evidence-{n}', f'{change_id}-claim-{n}'
        provenance = ObservationProvenance(str(uuid4()), 'active', oid, selection.id,
            (UnknownTime('unknown', 'unknown', Basis('unknown', None)),),
            (Location('unresolved', None, None, 'unknown', 'unassessed', Basis('unknown', None),
                      ('Capture place unknown.',)),))
        observation = MediaObservation(oid, result.run.source_id, finding.content,
            observer=result.run.analyst.label, origin_kind='media_analysis', provenance_id=provenance.id)
        records.reviewed_selections.append(selection)
        records.observation_provenance.append(provenance)
        records.observations.append(observation)
        records.evidence.append(Evidence(eid, oid, cid, 'supports'))
        records.claims.append(Claim(cid, 'synthetic-subject', 'synthetic_visible_condition',
                                    'Synthetic bounded report', evidence_ids=(eid,)))
        texts.extend((FindingText('analysis_finding', 'analysis_finding', finding.id, finding.id, finding.content),
                      FindingText('analysis_finding', 'observation', oid, finding.id, observation.content)))
    return make_change(records, change_id), ResearchPacket(tuple(texts))


def admit(service, reviews, result, change_id='analysis-review-a'):
    change, packet = proposal(service, result, change_id)
    review = replace(reviewed(change, packet), extraction_scope='necessary_excerpts')
    reviews.values[review.fingerprint] = review
    receipt = ReviewReceipt(17, 'a' * 40, f'research-reviews/{review.fingerprint}.json')
    service.admit(change, packet, receipt)
    return change, packet, receipt


def test_reprocessing_is_append_only_and_cannot_select_publish_or_change_plans(session, tmp_path):
    service, _, targets = session
    first = service.process('source-analysis', (targets[0],), reply(targets[0]))
    before = wire(first)
    second = service.process('source-analysis', (targets[0],), reply(targets[0], 'Conflicting synthetic dry view.'))
    assert first.id != second.id
    assert first.findings[0].id != second.findings[0].id
    assert wire(service.outcomes()[0]) == before
    assert first.run.inputs == second.run.inputs
    records = service.proposal_records((first.id, second.id))
    assert not records.reviewed_selections and not records.observations
    assert not records.evidence and not records.claims and not records.gaps and not records.relationships
    assert len(records.analysis_runs) == 2
    assert service.read().keys() == ()
    with pytest.raises(KeyError, match='not admitted'):
        service.read().get('analysis_finding', first.findings[0].id)
    with pytest.raises(FrozenInstanceError):
        records.analysis_runs[0].method = None
    with pytest.raises(Exception, match='planning activation is disabled'):
        service.read().plan()
    assert list(tmp_path.iterdir()) == []


def test_only_exact_workflow_review_admits_selected_lineage(session):
    service, reviews, targets = session
    result = service.process('source-analysis', (targets[0],), reply(targets[0]))
    change, packet = proposal(service, result)
    receipt = ReviewReceipt(17, 'a' * 40, 'research-reviews/unapproved.json')
    with pytest.raises(ValueError):
        service.admit(change, packet, receipt)
    assert not service.read().keys()
    change, packet, receipt = admit(service, reviews, result)
    rid = change.records.claims[0].claim_id
    reads = service.read()
    model = reads.explain_claim(rid)
    assert model['support'] == 'traceable' and model['publication'] == 'disabled'
    assert model['analysis_scope'] == 'synthetic_only'
    assert WayproofReadTools(reads).get_evidence_detail('claim', rid) == model
    lineage = {(row['record_type'], row['record_id']) for row in model['lineage']}
    assert {('analysis_run', result.id), ('analysis_finding', result.findings[0].id),
            ('evidence', change.records.evidence[0].evidence_id),
            ('media_version', targets[0].media_version_id)} <= lineage
    assert all(t['kind'] == 'analysis_finding' for t in model['texts'])
    context = model['context'][0]
    assert context['analysis_time']['value'] == '2030-04-04T12:00:00+00:00'
    assert context['retrieval_times'][0]['time']['value'] == '2030-04-03T12:00:00Z'
    assert context['attachment_publication_times'][0]['time']['value'] == '2030-04-02'
    assert context['statement_publication_time']['kind'] == 'unknown'
    assert context['event_capture_times'][0]['kind'] == 'unknown'
    assert context['locations'][0]['value'] is None
    assert context['versions'][0]['reproducibility'] == 'unavailable'
    assert context['analysis_run_id'] == result.id
    reviews.revoked.add(fingerprint(change, packet, CanonicalRecords()))
    assert reads.explain_claim(rid)['support'] == 'unsupported'
    assert reads.explain_claim(rid)['texts'] == []


@pytest.mark.parametrize('state,processor,versions,status', [
    ('unavailable','succeeded',None,'unavailable'), ('changed','succeeded',None,'changed'),
    ('available','failed',None,'failed'), ('available','succeeded',('different-version',),'changed')])
def test_failed_or_changed_attempt_has_explicit_status_and_no_substitute(session, state, processor, versions, status):
    service, reviews, targets = session
    first = service.process('source-analysis', (targets[0],), reply(targets[0]))
    change, _, _ = admit(service, reviews, first)
    before = wire(first)
    result = service.process('source-analysis', (targets[0],), reply(targets[0],
        'This output must never be substituted.', source_state=state, processor_state=processor,
        observed_version_ids=versions or (targets[0].media_version_id,)))
    assert result.status == status and result.run is None and not result.findings
    assert result.id != first.id and wire(service.outcomes()[0]) == before
    with pytest.raises(ValueError):
        service.proposal_records((result.id,))
    model = service.read().explain_claim(change.records.claims[0].claim_id)
    assert model['support'] == ('traceable' if status == 'failed' else 'unsupported')
    assert 'must never be substituted' not in json.dumps(model)


def test_changed_version_cannot_restore_old_support_with_a_later_success(session):
    service, reviews, targets = session
    first = service.process('source-analysis', (targets[0],), reply(targets[0]))
    change, _, _ = admit(service, reviews, first)
    service.process('source-analysis', (targets[0],), reply(targets[0], source_state='changed'))
    later = service.process('source-analysis', (targets[0],), reply(targets[0], 'Later output.'))
    with pytest.raises(ValueError):
        service.proposal_records((later.id,))
    assert service.read().explain_claim(change.records.claims[0].claim_id)['support'] == 'unsupported'


@pytest.mark.parametrize('mutation', ['large','extra_fields','outside','metadata','no_limitations'])
def test_invalid_untrusted_processor_output_is_inert_and_explicit(session, mutation):
    service, _, targets = session
    value = reply(targets[0])
    f = value.findings[0]
    if mutation == 'large': f = replace(f, content='x' * 2001)
    if mutation == 'extra_fields': object.__setattr__(f, 'instruction', 'publish_now')
    if mutation == 'outside': f = replace(f, target=targets[1])
    if mutation == 'metadata': f = replace(f, modality='metadata')
    if mutation == 'no_limitations': f = replace(f, limitations=())
    value = replace(value, findings=(f,))
    result = service.process('source-analysis', (targets[0],), value)
    assert result.status == 'invalid_output' and result.run is None and not result.findings
    assert not service.read().keys()


@pytest.mark.parametrize('mutation', ['finding','run','selection','capture','location','direct_run','direct_finding','direct_run_value','direct_finding_value','unowned'])
def test_proposal_cannot_forge_output_selection_or_provenance(session, mutation):
    service, reviews, targets = session
    result = service.process('source-analysis', (targets[0],), reply(targets[0]))
    change, packet = proposal(service, result)
    r = change.records
    if mutation == 'finding': r.analysis_findings[0] = replace(r.analysis_findings[0], content='Modified')
    if mutation == 'run': r.analysis_runs[0] = replace(r.analysis_runs[0], method=replace(r.analysis_runs[0].method, version='2'))
    if mutation == 'selection': r.reviewed_selections.clear()
    if mutation == 'capture':
        p = r.observation_provenance[0]
        r.observation_provenance[0] = replace(p, event_times=(replace(
            r.analysis_runs[0].analysis_time, basis=Basis('finding', result.findings[0].id)),))
    if mutation == 'location':
        p = r.observation_provenance[0]
        r.observation_provenance[0] = replace(p, locations=(replace(p.locations[0], precision_m=1),))
    if mutation in ('direct_run', 'direct_finding'):
        r.claims[0] = replace(r.claims[0], evidence_ids=(result.id if mutation == 'direct_run' else result.findings[0].id,))
    if mutation in ('direct_run_value', 'direct_finding_value'):
        field, value = ('run_id', result.id) if mutation == 'direct_run_value' else ('finding_id', result.findings[0].id)
        r.claims[0] = replace(r.claims[0], value={field: value})
    if mutation == 'unowned':
        r.sources[0] = replace(r.sources[0], locator='https://example.invalid/changed')
    change = make_change(r, change.change_set_id)
    review = reviewed(change, packet)
    reviews.values[review.fingerprint] = review
    receipt = ReviewReceipt(17, 'a' * 40, f'research-reviews/{review.fingerprint}.json')
    with pytest.raises(ValueError):
        service.admit(change, packet, receipt)
    assert not service.read().keys()


def test_partial_video_frames_remain_bounded_and_never_mean_whole_video(analysis_seed):
    seed = deepcopy(analysis_seed)
    seed.media_versions[0] = replace(seed.media_versions[0], media_type='video', duration_ms=120_000)
    service = SyntheticAnalysisService(seed, Reviews())
    attachment = seed.source_attachments[0]
    target = Target(attachment.media_version_id, attachment.id, FrameSelector('frames', (1000, 2000)))
    result = service.process('source-analysis', (target,), reply(target, modality='ocr'))
    assert result.status == 'succeeded'
    assert result.run.inputs[0].selector.timestamps_ms == (1000, 2000)
    outside = replace(reply(target).findings[0], target=replace(target, selector=FrameSelector('frames', (3000,))))
    assert service.process('source-analysis', (target,), replace(reply(target), findings=(outside,))).status == 'invalid_output'
    with pytest.raises(ValueError, match='duration budget'):
        service.process('source-analysis', (replace(target, selector=TimeSelector('time_range', 0, 120_000)),), reply(target))


def test_real_sources_and_processor_callbacks_cannot_be_enabled(analysis_seed, session):
    seed = deepcopy(analysis_seed)
    seed.sources[0] = replace(seed.sources[0], locator='https://www.nps.gov/example')
    with pytest.raises(ValueError, match='.invalid'):
        SyntheticAnalysisService(seed, Reviews())
    service, _, targets = session
    called = []
    with pytest.raises(ValueError, match='scripted synthetic'):
        service.process('source-analysis', (targets[0],), lambda: called.append(True))
    assert not called


def test_production_preparation_remains_closed_after_synthetic_review(session, tmp_path):
    service, reviews, targets = session
    result = service.process('source-analysis', (targets[0],), reply(targets[0]))
    change, packet, receipt = admit(service, reviews, result)
    writes = ChangeSetWriteService(InMemoryCanonicalRepository())
    writes.propose(change, 'synthetic researcher')
    assert not writes.validate(change.change_set_id, 'validator')
    with pytest.raises(PreparationRejected):
        writes.prepare(change.change_set_id, 'builder')
    with pytest.raises(ValueError):
        ReferencePublication.prepare(tmp_path, change, packet, receipt, reviews)
    assert not list(tmp_path.iterdir())


def test_conflicting_reprocessing_leaves_reviewed_selection_and_history_unchanged(session):
    service, reviews, targets = session
    first = service.process('source-analysis', (targets[0],), reply(targets[0]))
    change, _, _ = admit(service, reviews, first)
    model = service.read().explain_claim(change.records.claims[0].claim_id)
    second = service.process('source-analysis', (targets[0],), reply(targets[0], 'Conflicting dry view.'))
    assert service.read().explain_claim(change.records.claims[0].claim_id) == model
    with pytest.raises(KeyError):
        service.read().get('analysis_finding', second.findings[0].id)
    second_change, _, _ = admit(service, reviews, second, 'second-selection')
    second_model = service.read().explain_claim(second_change.records.claims[0].claim_id)
    assert second_model['context'][0]['analysis_run_id'] == second.id
    assert model == service.read().explain_claim(change.records.claims[0].claim_id)


def test_withdrawal_invalidates_all_dependent_attempts_without_approval(session):
    service, reviews, targets = session
    first = service.process('source-analysis', (targets[0],), reply(targets[0]))
    failed = service.process('source-analysis', (targets[0],), reply(targets[0], processor_state='failed'))
    unrelated = service.process('source-analysis', (targets[1],), reply(targets[1], 'Unrelated synthetic view.'))
    change, _, receipt = admit(service, reviews, first)
    other, _, _ = admit(service, reviews, unrelated, 'unrelated-review')
    before = wire(unrelated)
    other_model = service.read().explain_claim(other.records.claims[0].claim_id)
    reviews.revoked.add(receipt.review_path.split('/')[-1].removesuffix('.json'))
    impact = service.withdraw(('source-post',))
    assert ('analysis_run', first.id) in impact['records']
    assert ('analysis_run', failed.id) in impact['records']
    assert service.outcomes()[0].status == service.outcomes()[1].status == 'withdrawn'
    assert wire(service.outcomes()[2]) == before
    assert service.read().explain_claim(change.records.claims[0].claim_id)['support'] == 'unsupported'
    assert service.read().explain_claim(other.records.claims[0].claim_id) == other_model
    assert first.findings[0].content not in json.dumps(wire(service.outcomes()))
    service.withdraw(('source-post',))  # Retry remains safe and does not resurrect results.
    with pytest.raises(ValueError):
        service.process('source-analysis', (targets[0],), reply(targets[0]))


def test_export_withholds_files_if_review_is_revoked_during_generation(session, tmp_path, monkeypatch):
    service, reviews, targets = session
    result = service.process('source-analysis', (targets[0],), reply(targets[0]))
    change, packet, _ = admit(service, reviews, result)
    import wayproof.canonical_site as renderer
    original = renderer.render_evidence_html
    def revoke(model, url):
        reviews.revoked.add(fingerprint(change, packet, CanonicalRecords()))
        return original(model, url)
    monkeypatch.setattr(renderer, 'render_evidence_html', revoke)
    with pytest.raises(ValueError, match='changed during export'):
        service.export(tmp_path / 'owned')
    assert not (tmp_path / 'owned').exists()


def test_withdrawal_retry_finishes_failed_output_cleanup_without_authority(session, tmp_path, monkeypatch):
    service, reviews, targets = session
    result = service.process('source-analysis', (targets[0],), reply(targets[0]))
    change, packet, _ = admit(service, reviews, result)
    output = service.export(tmp_path / 'owned')
    import shutil
    original = shutil.rmtree
    def fail(*args, **kwargs):
        raise OSError('synthetic cleanup failure')
    monkeypatch.setattr(shutil, 'rmtree', fail)
    with pytest.raises(OSError):
        service.withdraw(('source-post',))
    reviews.revoked.add(fingerprint(change, packet, CanonicalRecords()))
    assert service.read().explain_claim(change.records.claims[0].claim_id)['support'] == 'unsupported'
    monkeypatch.setattr(shutil, 'rmtree', original)
    assert service.withdraw(('source-post',))['outputs'] == 'regenerated'
    assert output.exists()


def test_analysis_ids_are_not_reused_after_withdrawal(session, monkeypatch):
    service, _, targets = session
    result = service.process('source-analysis', (targets[0],), reply(targets[0]))
    service.withdraw(('source-post',))
    monkeypatch.setattr('wayproof.analysis_service.uuid4', lambda: result.id)
    with pytest.raises(ValueError, match='identity collision'):
        service.process('source-analysis', (targets[1],), reply(targets[1]))


@pytest.mark.parametrize('unknown', [False, True])
def test_image_area_requires_known_bounded_inspection(analysis_seed, unknown):
    from wayproof.media_schema import Dimensions
    seed = deepcopy(analysis_seed)
    seed.media_versions[0] = replace(seed.media_versions[0], dimensions=None if unknown else Dimensions(100_000, 100_000))
    service = SyntheticAnalysisService(seed, Reviews())
    a = seed.source_attachments[0]
    target = Target(a.media_version_id, a.id, WholeImage('whole'))
    with pytest.raises(ValueError, match='image-area budget'):
        service.process('source-analysis', (target,), reply(target))


def test_unavailable_material_is_not_made_available_by_a_fixture_flag(analysis_seed, draft):
    seed = deepcopy(analysis_seed)
    seed.availability_reports = [replace(draft.records.availability_reports[0], availability='unavailable')]
    service = SyntheticAnalysisService(seed, Reviews())
    a = seed.source_attachments[0]
    target = Target(a.media_version_id, a.id, WholeImage('whole'))
    result = service.process('source-analysis', (target,), reply(target))
    assert result.status == 'unavailable' and result.run is None


def test_cannot_register_overlapping_output_ownership(session, tmp_path):
    service, _, _ = session
    service.export(tmp_path / 'owned')
    with pytest.raises(ValueError, match='overlap'):
        service.export(tmp_path / 'owned' / 'nested')


def test_processor_cannot_transcribe_a_still_image(session):
    service, _, targets = session
    result = service.process('source-analysis', (targets[0],), reply(targets[0], modality='transcription'))
    assert result.status == 'invalid_output' and not result.findings


def test_source_aliases_cannot_escape_withdrawal(analysis_seed):
    seed = deepcopy(analysis_seed)
    seed.sources[2] = replace(seed.sources[2], locator=seed.sources[0].locator)
    with pytest.raises(ValueError, match='aliases'):
        SyntheticAnalysisService(seed, Reviews())


def test_known_repost_cannot_survive_original_source_withdrawal(analysis_seed):
    seed = deepcopy(analysis_seed)
    from wayproof.media_schema import AttributedStatement, Speaker
    statement = AttributedStatement(str(uuid4()), 'active', 'source-other', 'caption',
        Speaker('author', 'Synthetic reposter'), 'This synthetic item repeats the original attachment.',
        seed.source_attachments[1].publication_time, None)
    seed.attributed_statements = [statement]
    seed.media_assets[1] = replace(seed.media_assets[1], origin_asset_id=seed.media_assets[0].id,
                                    origin_statement_id=statement.id)
    service, reviews, targets = session.__wrapped__(seed)
    result = service.process('source-analysis', (targets[1],), reply(targets[1]))
    change, _, _ = admit(service, reviews, result)
    model = service.read().explain_claim(change.records.claims[0].claim_id)
    assert {row['kind'] for row in model['texts']} == {'quotation', 'analysis_finding'}
    impact = service.withdraw(('source-post',))
    assert ('source', 'source-other') in impact['records']
    assert ('analysis_run', result.id) in impact['records']
    assert service.outcomes()[0].status == 'withdrawn'
    assert service.read().explain_claim(change.records.claims[0].claim_id)['support'] == 'unsupported'
