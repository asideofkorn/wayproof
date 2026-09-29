"""Bounded synthetic analysis rehearsal, with no acquisition or processor plugins.

Run/finding records use the accepted media contract. Attempt outcomes are local
service state, not a new canonical envelope. Only explicit, workflow-reviewed
ChangeSets can admit findings to the rehearsal evidence projection. Production
reference publication continues to reject analysis records.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from .media_contract import _typed, wire
from .media_schema import (MediaRecords, AnalysisRun, AnalysisFinding, Target,
                           Analyst, Method, InstantTime, Basis)
from .media_validation import dependencies, validate_selector
from .media_migration import (ALL_SPECS, MigrationReadService, LiveMigrationReadService,
                              encoded, reference_context, export_projection)
from .public_research import (ResearchPacket, ReviewedResearch, assess, fingerprint,
                              bounded_text, safe_url, removal_impact)
from .schema import CanonicalRecords, ChangeSet, ChangeOperation, ChangeAction


@dataclass(frozen=True)
class SyntheticFinding:
    target: Target
    modality: Literal['visual', 'ocr', 'transcription']
    content: str
    certainty: Literal['observed', 'asserted', 'inferred', 'unresolved']
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class SyntheticReply:
    """Scripted fixture data, never a callback, model response adapter or URL loader."""
    source_state: Literal['available', 'unavailable', 'changed']
    observed_version_ids: tuple[str, ...]
    processor_state: Literal['succeeded', 'failed']
    findings: tuple[SyntheticFinding, ...]


@dataclass(frozen=True)
class ProcessingOutcome:
    id: str
    status: Literal['succeeded', 'failed', 'unavailable', 'changed', 'invalid_output', 'withdrawn']
    run: AnalysisRun | None
    findings: tuple[AnalysisFinding, ...]


def _records_index(records):
    return {(kind, getattr(row, attr)): row for kind, (col, attr, _) in ALL_SPECS.items()
            for row in getattr(records, col)}


def _records(index):
    return MediaRecords(**{col: [deepcopy(row) for (kind, _), row in index.items() if kind == k]
                           for k, (col, _, _) in ALL_SPECS.items()})


def _change(records):
    """Structural check for service-owned records, never a publication operation."""
    return ChangeSet('synthetic-analysis-validation', records, summary='Synthetic analysis validation',
        schema_version=1, operations=tuple(ChangeOperation(ChangeAction.ADD, kind, rid,
            f'canonical/v1/{ALL_SPECS[kind][0]}/{rid}.json', 'Synthetic analysis validation')
            for kind, rid in _records_index(records)))


class SyntheticAnalysisService:
    """One process-local synthetic session; not wired into production CLI/MCP.

    Trusted composition supplies a review workflow and a clock. There is no
    processor/provider registration point. Inputs are typed synthetic metadata
    and scripted output fixtures; media bytes and arbitrary URLs are not inputs.
    """
    seed_kinds = frozenset({'entity', 'source', 'media_asset', 'media_version',
                            'availability_report', 'source_attachment', 'attributed_statement'})
    review_kinds = seed_kinds | {'analysis_run', 'analysis_finding', 'reviewed_selection',
                                'observation_provenance', 'observation', 'evidence', 'claim'}

    def __init__(self, seed: MediaRecords, workflow, *, clock=None):
        candidate = deepcopy(seed)
        if type(seed) is not MediaRecords or _change(candidate).validate(existing=CanonicalRecords()):
            raise ValueError('invalid synthetic input graph')
        rows = _records_index(candidate)
        if any(kind not in self.seed_kinds for kind, _ in rows) or len(rows) > 100:
            raise ValueError('synthetic input scope exceeded')
        if len(encoded(wire(candidate))) > 100_000:
            raise ValueError('synthetic input budget exceeded')
        if len({s.locator for s in candidate.sources}) != len(candidate.sources):
            raise ValueError('source aliases cannot become independent processing inputs')
        for source in candidate.sources:
            safe_url(source.locator)
            if not urlsplit(source.locator).hostname.endswith('.invalid'):
                raise ValueError('only reserved .invalid fixture sources are admitted')
        for statement in candidate.attributed_statements:
            bounded_text(statement.text)
        for version in candidate.media_versions:
            if (version.identity_basis not in ('unverifiable', 'provider_version')
                    or not version.limitations or
                    (version.identity_basis == 'unverifiable' and version.reproducibility != 'unavailable')):
                raise ValueError('reference-only identity and reproducibility limitations required')
        self._seed = rows
        self._workflow = workflow
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._outcomes = {}
        self._requests = {}
        self._admissions = {}
        self._used_ids = {rid for _, rid in rows}
        self._withdrawn = set()
        self._withdrawn_sources = set()
        self._outputs = set()
        self._revision = 0
        self._blocked_versions = {}

    def _id(self):
        rid = str(uuid4())
        if rid in self._used_ids:
            raise ValueError('analysis identity collision')
        self._used_ids.add(rid)
        return rid

    def outcomes(self):
        """Detached operational history; these results are not Evidence."""
        return deepcopy(tuple(self._outcomes.values()))

    def process(self, source_id, inputs: tuple[Target, ...], reply: SyntheticReply):
        if len(self._outcomes) >= 128:
            raise ValueError('synthetic session attempt budget exceeded')
        source = self._seed.get(('source', source_id))
        if source is None or source.source_role != 'analysis_report':
            raise ValueError('analysis-report source required')
        if type(inputs) is not tuple or not 1 <= len(inputs) <= 4:
            raise ValueError('bounded typed inspection targets required')
        inputs = tuple(_typed(Target, wire(t)) for t in inputs)
        if len(set(inputs)) != len(inputs):
            raise ValueError('duplicate inspection target')
        for target in inputs:
            version = self._seed.get(('media_version', target.media_version_id))
            attachment = self._seed.get(('source_attachment', target.source_attachment_id))
            if version is None or attachment is None or attachment.media_version_id != version.id:
                raise ValueError('input version/attachment unavailable')
            selector = wire(target.selector)
            validate_selector(selector, wire(version))
            if selector['kind'] in ('whole', 'image_region'):
                width = selector.get('width', version.dimensions.width if version.dimensions else 0)
                height = selector.get('height', version.dimensions.height if version.dimensions else 0)
                if not width or not height or width * height > 16_000_000:
                    raise ValueError('inspection image-area budget unavailable or exceeded')
            if selector['kind'] == 'time_range' and selector['end_ms'] - selector['start_ms'] > 60_000:
                raise ValueError('inspection duration budget exceeded')
            if selector['kind'] == 'frames' and len(selector['timestamps_ms']) > 32:
                raise ValueError('inspection frame budget exceeded')
        # Only a closed data fixture is accepted. No callable/provider can execute.
        if type(reply) is not SyntheticReply:
            raise ValueError('only scripted synthetic replies are supported')
        ident = self._id()
        status, run, findings = 'invalid_output', None, ()
        try:
            if set(vars(reply)) != {f.name for f in fields(SyntheticReply)} or any(
                    type(finding) is not SyntheticFinding or
                    set(vars(finding)) != {f.name for f in fields(SyntheticFinding)}
                    for finding in reply.findings):
                raise ValueError('undeclared processor output fields')
            clean = _typed(SyntheticReply, wire(reply))
            if len(encoded(wire(clean))) > 20_000 or len(clean.findings) > 8:
                raise ValueError('processor output budget exceeded')
            versions = tuple(t.media_version_id for t in inputs)
            if clean.source_state == 'unavailable':
                status = 'unavailable'
            elif clean.source_state == 'changed' or clean.observed_version_ids != versions:
                status = 'changed'
            elif any(r.media_version_id in versions and r.availability != 'available'
                     for (kind, _), r in self._seed.items() if kind == 'availability_report'):
                status = 'unavailable'
            elif clean.processor_state == 'failed':
                status = 'failed'
            else:
                for finding in clean.findings:
                    version = self._seed.get(('media_version', finding.target.media_version_id))
                    if version is None or (finding.modality == 'transcription' and version.media_type == 'image') or (
                            finding.modality in ('visual', 'ocr') and version.media_type == 'audio'):
                        raise ValueError('finding modality does not match the inspected media')
                when = self._clock()
                if when.tzinfo is None:
                    raise ValueError('analysis clock must be timezone aware')
                run = AnalysisRun(ident, 'active', source_id, inputs,
                    Analyst('tool', 'Wayproof synthetic processor', '1'),
                    Method('scripted-synthetic-fixture', '1', 'No media was fetched or inspected; bounded fixture output only.'),
                    InstantTime('instant', when.isoformat(), 'exact', Basis('clock', None)),
                    tuple(sorted({f.modality for f in clean.findings})),
                    ('Synthetic simulation only; not a real-world observation.',
                     'Only the named regions, frames or time ranges are represented.'))
                findings = tuple(AnalysisFinding(self._id(), 'active', ident, f.target, f.modality, (),
                    bounded_text(f.content), f.certainty, (), tuple(bounded_text(s, 600) for s in f.limitations))
                    for f in clean.findings)
                if not findings or any(not f.limitations for f in findings):
                    raise ValueError('bounded findings require limitations')
                proposed = _records(self._seed | {('analysis_run', ident): run} |
                                    {('analysis_finding', f.id): f for f in findings})
                if _change(proposed).validate(existing=CanonicalRecords()):
                    raise ValueError('processor output violates provenance contract')
                status = 'succeeded'
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
            # Never echo malformed output, exceptions, prompts or supposed tool calls.
            status, run, findings = 'invalid_output', None, ()
        if status in ('changed', 'unavailable'):
            for target in inputs:
                self._blocked_versions[target.media_version_id] = (
                    'changed' if status == 'changed' or self._blocked_versions.get(target.media_version_id) == 'changed'
                    else 'unavailable')
        outcome = ProcessingOutcome(ident, status, run, findings)
        self._outcomes[ident] = outcome
        self._requests[ident] = (source_id, inputs)
        self._revision += 1
        return deepcopy(outcome)

    def proposal_records(self, run_ids):
        """Return only owned input/run/finding records; never select or author evidence."""
        rows = dict(self._seed)
        wanted = set()
        for rid in run_ids:
            result = self._outcomes[rid]
            if result.status != 'succeeded' or any(t.media_version_id in self._blocked_versions for t in result.run.inputs):
                raise ValueError('only successful, active results can be proposed')
            rows['analysis_run', rid] = result.run
            wanted.add(('analysis_run', rid))
            for finding in result.findings:
                rows['analysis_finding', finding.id] = finding
                wanted.add(('analysis_finding', finding.id))
        plain = {key: wire(row) for key, row in rows.items()}
        while True:
            reached = wanted | {ref for key in wanted for ref in dependencies(key, plain[key], plain)}
            if reached == wanted:
                break
            wanted = reached
        # Entities are context for a human-authored proposal, never inferred from media.
        wanted.update(key for key in rows if key[0] == 'entity')
        return _records({key: rows[key] for key in rows if key in wanted})

    def admit(self, change, packet: ResearchPacket, receipt):
        """Admit an exact reviewed synthetic proposal to rehearsal consumers only."""
        change, packet = deepcopy(change), deepcopy(packet)
        if change.change_set_id in self._admissions:
            raise ValueError('reviewed history cannot be overwritten')
        if change.validate(existing=CanonicalRecords()):
            raise ValueError('invalid analysis proposal')
        rows = _records_index(change.records)
        if set(kind for kind, _ in rows) - self.review_kinds:
            raise ValueError('analysis rehearsal cannot change planning or relationships')
        owned = dict(self._seed)
        for result in self._outcomes.values():
            if result.status == 'succeeded':
                owned['analysis_run', result.id] = result.run
                owned.update({('analysis_finding', f.id): f for f in result.findings})
        for key, row in rows.items():
            if key in self._withdrawn:
                raise ValueError('withdrawn identities cannot be reused')
            if key[0] in self.seed_kinds | {'analysis_run', 'analysis_finding'} and owned.get(key) != row:
                raise ValueError('proposal changes or imports unowned input/analysis records')
        if not change.records.analysis_findings or not change.records.reviewed_selections:
            raise ValueError('explicit reviewed finding selection required')
        selected = {s.origin.id for s in change.records.reviewed_selections if s.origin.kind == 'finding'}
        if selected != {f.id for f in change.records.analysis_findings}:
            raise ValueError('every admitted finding needs an explicit selection')
        for provenance in change.records.observation_provenance:
            if not provenance.event_times or not provenance.locations:
                raise ValueError('event time and location must preserve explicit unknowns')
            # This fixture processor does not inspect metadata or identify locations/dates.
            if (any(t.kind != 'unknown' for t in provenance.event_times) or
                    any(loc.value is not None or loc.precision_m is not None or loc.basis_kind != 'unresolved'
                        for loc in provenance.locations)):
                raise ValueError('synthetic finding cannot establish a capture date or location')
        if any(o.observed_at is not None or o.retrieved_at is not None for o in change.records.observations):
            raise ValueError('analysis observations require separate qualified time roles')
        if any(c.temporal_scope is not None or c.spatial_scope_ids for c in change.records.claims):
            raise ValueError('analysis rehearsal cannot establish planning scopes')
        for previous, _, _ in self._admissions.values():
            if previous is None:
                continue
            for key, row in _records_index(previous.records).items():
                if key in rows and (rows[key] != row or key[0] not in self.seed_kinds | {'analysis_run', 'analysis_finding'}):
                    raise ValueError('reviewed records cannot be overwritten or reselected in place')
        if any(v.id in self._blocked_versions for v in change.records.media_versions):
            raise ValueError('selected input is unavailable or changed')
        fp = fingerprint(change, packet, CanonicalRecords())
        review = self._workflow.resolve(receipt, fp)
        if assess(change, packet, ReviewedResearch((review,)), CanonicalRecords()):
            raise ValueError('review does not admit this exact analysis proposal')
        self._admissions[change.change_set_id] = (change, packet, deepcopy(receipt))
        self._revision += 1

    def _snapshot(self):
        snapshots = []
        for change, packet, receipt in self._admissions.values():
            if change is None:
                continue
            eligible = False
            try:
                review = self._workflow.resolve(receipt, fingerprint(change, packet, CanonicalRecords()))
                eligible = not assess(change, packet, ReviewedResearch((review,)), CanonicalRecords())
                eligible = eligible and not any(v.id in self._blocked_versions for v in change.records.media_versions)
            except Exception:
                pass  # No continuing review authority means unsupported, never fallback.
            projection = MigrationReadService(CanonicalRecords(),
                {key: wire(row) for key, row in _records_index(change.records).items()}, (),
                packet if eligible else None, ())
            snapshots.append(projection)
        return AnalysisReadProjection(snapshots, self._withdrawn, self._blocked_versions)

    def read(self):
        return LiveMigrationReadService(self)

    def export(self, destination):
        """Write only a newly-owned rehearsal directory, never production publication."""
        destination = Path(destination).absolute()
        if any(p.is_symlink() for p in (destination, *destination.parents)):
            raise ValueError('analysis export refuses symlinks')
        destination = destination.resolve()
        if destination not in self._outputs:
            if any(destination in output.parents or output in destination.parents for output in self._outputs):
                raise ValueError('owned analysis output directories cannot overlap')
            if destination.exists():
                raise ValueError('analysis export requires a new owned directory')
            self._outputs.add(destination)
        snapshot = self._snapshot()
        def generation(reads):
            return encoded({'revision': self._revision,
                            'models': [reads.evidence_detail(*key) for key in reads.keys()]})
        pinned = generation(snapshot)
        return export_projection(snapshot, destination, pinned,
                                 lambda: generation(self._snapshot()))

    def withdraw(self, source_ids):
        """Erase dependent retained content, preserve unrelated outcomes, rebuild outputs."""
        targets = set(source_ids)
        if not targets or not targets <= ({rid for kind, rid in self._seed if kind == 'source'} | self._withdrawn_sources):
            raise ValueError('unknown withdrawal source')
        rows = dict(self._seed)
        for result in self._outcomes.values():
            if result.status == 'succeeded':
                rows['analysis_run', result.id] = result.run
                rows.update({('analysis_finding', f.id): f for f in result.findings})
        for change, _, _ in self._admissions.values():
            if change is not None:
                rows.update(_records_index(change.records))
        fresh = targets - self._withdrawn_sources
        affected = set()
        # Known origin/repost assets carry removal obligations to their owning
        # source associations; they must not survive under a different URL.
        while fresh:
            affected = set(removal_impact(_records(rows), fresh)['records'])
            owners = {row.source_id for (kind, _), row in rows.items()
                      if kind == 'source_attachment' and ('media_version', row.media_version_id) in affected}
            if owners <= fresh:
                break
            fresh.update(owners)
        targets.update(fresh)
        for rid, (source_id, inputs) in tuple(self._requests.items()):
            if (('source', source_id) in affected or any(('media_version', t.media_version_id) in affected
                    or ('source_attachment', t.source_attachment_id) in affected for t in inputs)):
                result = self._outcomes[rid]
                affected.add(('analysis_run', rid))
                affected.update(('analysis_finding', f.id) for f in result.findings)
                self._outcomes[rid] = ProcessingOutcome(rid, 'withdrawn', None, ())
                del self._requests[rid]
        for cid, (change, _, _) in tuple(self._admissions.items()):
            if change is not None and set(_records_index(change.records)) & affected:
                # Withdraw the reviewed packet as one unit; do not silently revise a review.
                self._withdrawn.update(key for key in _records_index(change.records)
                                       if key[0] not in self.seed_kinds | {'analysis_run', 'analysis_finding'})
                self._admissions[cid] = (None, None, None)
        for key in affected:
            self._seed.pop(key, None)
            if key[0] == 'media_version':
                self._blocked_versions.pop(key[1], None)
        self._withdrawn.update(affected)
        self._withdrawn_sources.update(targets)
        self._revision += 1
        # Live reads are already invalidated even if IO cleanup fails; retry is safe.
        from .media_migration import _files
        import shutil
        for output in self._outputs:
            if output.exists():
                _files(output)
                shutil.rmtree(output)
        for output in self._outputs:
            self.export(output)
        return {'records': sorted(affected), 'plans': 'invalidated', 'outputs': 'regenerated',
                'publication': 'disabled'}


class AnalysisReadProjection:
    """Single shared read model used by rehearsal HTML/JSON/MCP exporters."""
    def __init__(self, snapshots, withdrawn, input_states):
        self._snapshots, self._withdrawn = snapshots, set(withdrawn)
        self._input_states = dict(input_states)

    def keys(self):
        return tuple(sorted(self._withdrawn | {key for s in self._snapshots for key in s.keys()}))

    def evidence_detail(self, kind, rid):
        key = (kind, rid)
        if key in self._withdrawn:
            snapshot = MigrationReadService(CanonicalRecords(), {}, self._withdrawn, None, ())
            model = snapshot.evidence_detail(kind, rid)
        else:
            models = [s.evidence_detail(kind, rid) for s in self._snapshots if key in s.keys()]
            if not models:
                raise KeyError('finding is not admitted to the evidence projection')
            model = next((m for m in models if m['support'] == 'unsupported'), models[0])
        model['context'] = reference_context(model['lineage']) if model['support'] == 'traceable' else []
        model['analysis_scope'] = 'synthetic_only'
        lineage = {(r['record_type'], r['record_id']) for r in model['lineage']}
        model['input_states'] = [{'media_version_id': rid, 'state': status}
                                 for rid, status in sorted(self._input_states.items())
                                 if ('media_version', rid) in lineage]
        return model

    def explain_claim(self, rid):
        return self.evidence_detail('claim', rid)

    def get(self, kind, rid):
        return self.evidence_detail(kind, rid)

    def plan(self, *args, **kwargs):
        raise ValueError('analysis cannot activate planning')
