"""Fail-closed, reference-only research review; no acquisition or persistence.

Review facts enter through trusted application composition, never proposal flags.
This draft boundary does not authenticate GitHub, fetch posts, or process media.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from html import escape
from ipaddress import ip_address
import json
import re
from typing import Literal
from urllib.parse import unquote, urlsplit

from .media_contract import _typed, wire
from .media_validation import dependencies, index
from .media_contract import public_bundle


@dataclass(frozen=True)
class Quotation:
    kind: Literal['quotation']
    target_kind: Literal['attributed_statement', 'observation']
    target_id: str
    source_id: str
    passages: tuple[str, ...]
    omitted_start: bool
    omitted_end: bool


@dataclass(frozen=True)
class Paraphrase:
    kind: Literal['paraphrase']
    target_kind: Literal['observation']
    target_id: str
    statement_id: str
    text: str


@dataclass(frozen=True)
class FindingText:
    kind: Literal['analysis_finding']
    target_kind: Literal['analysis_finding', 'observation']
    target_id: str
    finding_id: str
    text: str


@dataclass(frozen=True)
class ResearchPacket:
    texts: tuple[Quotation | Paraphrase | FindingText, ...]


@dataclass(frozen=True)
class SourceReview:
    source_id: str
    locator: str
    inspected_at: datetime
    access: Literal['public_no_login', 'login_required', 'private', 'unavailable', 'unknown']
    current_state: Literal['available', 'unavailable', 'changed']
    publisher_kind: Literal['official', 'institutional', 'other', 'unknown']


@dataclass(frozen=True)
class ContentReview:
    """Trusted reviewer findings about the exact submitted snapshot, not grants."""
    fingerprint: str
    sources: tuple[SourceReview, ...]
    acquisition: Literal['public_reference', 'upload', 'private']
    # Empty only after review: includes semantic hazards a regex cannot prove absent.
    exclusions: tuple[Literal['retained_media', 'derivatives', 'exif', 'personal_identification',
        'sensitive_location', 'profile_harvesting', 'unsafe_link', 'misquotation'], ...]
    disposition: Literal['accepted', 'rejected', 'pending', 'revoked']
    # Applies to all OCR/transcription in this fingerprint-bound proposal.
    extraction_scope: Literal['unreviewed', 'necessary_excerpts', 'complete', 'unnecessary'] = 'unreviewed'


class ReviewedResearch:
    """Application-owned reviewed snapshot. Do not construct from request JSON.

    There is deliberately no default approval or public mutation/approve method.
    Production review acquisition/authentication is NOT supplied by this class.
    The caller configuring the service is the trust root, like its v0 repository.
    """
    def __init__(self, reviews: tuple[ContentReview, ...] = ()):
        self._reviews = {}
        for review in reviews:
            clean = _typed(ContentReview, wire(review))
            if clean != review or clean.fingerprint in self._reviews:
                raise ValueError('invalid or duplicate trusted review')
            self._reviews[clean.fingerprint] = deepcopy(clean)

    def lookup(self, fingerprint):
        return deepcopy(self._reviews.get(fingerprint))

    def forget_sources(self, source_ids):
        # Withdrawal can remove authority, never create it. No URL/text tombstone.
        for key, review in tuple(self._reviews.items()):
            if any(s.source_id in source_ids for s in review.sources):
                del self._reviews[key]


def decode_packet(value):
    """Closed input shape: eligibility/reviewer flags are not proposal fields."""
    return _typed(ResearchPacket, value)


def fingerprint(change, packet, existing=None):
    # Hash bounded proposal metadata, never media bytes; not a public media ID.
    payload = {'id': change.change_set_id, 'schema': change.schema_version,
               'records': wire(change.records), 'operations': wire(change.operations),
               'summary': change.summary, 'packet': wire(packet),
               'baseline': wire(existing) if existing is not None else None}
    return sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _need(condition, reason):
    if not condition:
        raise ValueError(reason)


def safe_url(value):
    _need(type(value) is str and 0 < len(value) <= 2048, 'URL length/type rejected')
    decoded = unquote(value)
    _need(not any(ord(c) < 33 or ord(c) == 127 for c in decoded)
          and not any(c in decoded for c in '\\<>"\''), 'unsafe URL characters')
    parsed = urlsplit(value)
    _need(parsed.scheme == 'https' and parsed.hostname and not parsed.username
          and not parsed.password and parsed.port in (None, 443)
          and not parsed.query and not parsed.fragment, 'URL must be a clean HTTPS reference')
    host = parsed.hostname.lower()
    _need(host.isascii() and '.' in host and not host.endswith(('.local', '.localhost', '.internal'))
          and re.fullmatch(r'[a-z0-9.-]+', host) and not host.endswith('.'), 'non-public URL host')
    try:
        address = ip_address(host)
    except ValueError:
        address = None
    _need(address is None, 'IP-literal reference rejected')
    return value


def bounded_text(value, limit=1600):
    _need(type(value) is str and 0 < len(value) <= limit, 'text budget exceeded')
    _need(not any((ord(c) < 32 and c not in '\n\t') or ord(c) == 127
                  or c in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069'
                  for c in value), 'text controls rejected')
    _need('data:' not in value.lower() and 'base64,' not in value.lower(), 'embedded payload rejected')
    return value


def text_value(item):
    if type(item) is Quotation:
        _need(0 < len(item.passages) <= 3, 'excerpt passage budget exceeded')
        for part in item.passages:
            bounded_text(part, 600)
        return bounded_text(('… ' if item.omitted_start else '') +
                            ' … '.join(item.passages) + (' …' if item.omitted_end else ''))
    return bounded_text(item.text)


def assess(change, packet, reviewed: ReviewedResearch, existing=None):
    """Return stable reasons only; never echo submitted content in errors."""
    try:
        _need(change.schema_version == 1, 'public research requires a v1 draft')
        _need(type(packet) is ResearchPacket and decode_packet(wire(packet)) == packet,
              'typed research packet required')
        encoded = json.dumps(wire(change.records), allow_nan=False)
        _need(len(encoded) <= 100_000, 'research draft budget exceeded')
        # Bound every string, including metadata, nested Claim values and operation reasons.
        def walk(value):
            if isinstance(value, Enum):
                walk(value.value)
            elif isinstance(value, str):
                if value:
                    bounded_text(value, 2048)
            elif isinstance(value, dict):
                for key, item in value.items():
                    bounded_text(key, 100)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(wire(change.records)); walk(wire(change.operations)); bounded_text(change.summary)
        review = reviewed.lookup(fingerprint(change, packet, existing))
        _need(review is not None and review.disposition == 'accepted', 'review missing, stale, or not accepted')
        _need(review.acquisition == 'public_reference' and not review.exclusions,
              'review rejects public reference-only scope')
        r = change.records
        referenced = {s.source_id for s in r.sources}
        for collection in (r.observations, r.source_attachments, r.attributed_statements, r.analysis_runs):
            referenced.update(s.source_id for s in collection)
        sources = {s.source_id: s for s in (list(getattr(existing, 'sources', ())) + r.sources)
                   if s.source_id in referenced}
        _need(sources.keys() == referenced, 'source unavailable for review')
        checks = {s.source_id: s for s in review.sources}
        _need(len(checks) == len(review.sources) and checks.keys() == sources.keys(), 'source review coverage mismatch')
        for sid, source in sources.items():
            safe_url(source.locator)
            check = checks[sid]
            _need(check.locator == source.locator and check.inspected_at.tzinfo is not None,
                  'source review locator/time mismatch')
            _need(check.access == 'public_no_login' and check.current_state == 'available',
                  'source inaccessible, unavailable, or changed')
            _need(check.publisher_kind != 'unknown', 'publisher classification unresolved')
        r = change.records
        _need(not any(o.artifact_refs for o in r.observations), 'artifact retention/reference bypass rejected')
        for version in r.media_versions:
            _need(getattr(version, 'identity_basis', '') in ('unverifiable', 'provider_version')
                  and version.limitations, 'reference-only version identity/limitations required')
            _need(version.identity_basis != 'unverifiable' or version.reproducibility == 'unavailable',
                  'unverifiable input cannot promise reproducibility')
        extraction_modalities = {'ocr', 'transcription'}
        has_extraction = (any(extraction_modalities.intersection(run.modalities) for run in r.analysis_runs)
                          or any(f.modality in extraction_modalities for f in r.analysis_findings))
        _need(not has_extraction or review.extraction_scope == 'necessary_excerpts',
              'OCR/transcription requires reviewed minimum-necessary excerpts, never complete extraction')
        for run in r.analysis_runs:
            _need(set(run.modalities) <= {'visual', 'ocr', 'transcription'}, 'prohibited processing modality')
        for finding in r.analysis_findings:
            _need(not finding.metadata_fields and finding.modality in ('visual', 'ocr', 'transcription'),
                  'EXIF/location inference rejected')
        for provenance in r.observation_provenance:
            for location in provenance.locations:
                _need(location.basis_kind not in ('exif_permitted', 'inferred')
                      and (location.sensitivity == 'nonsensitive' or
                           (location.value is None and location.basis_kind == 'unresolved'))
                      and getattr(location.value, 'kind', None) != 'point', 'restricted location rejected')
        targets = {('attributed_statement', x.id): x.text for x in r.attributed_statements}
        targets.update({('analysis_finding', x.id): x.content for x in r.analysis_findings})
        targets.update({('observation', x.observation_id): x.content for x in r.observations})
        texts = {(t.target_kind, t.target_id): t for t in packet.texts}
        _need(len(texts) == len(packet.texts) and texts.keys() == targets.keys(), 'text representation coverage mismatch')
        statements = {x.id: x for x in r.attributed_statements}
        observations = {x.observation_id: x for x in r.observations}
        provenances = {x.id: x for x in r.observation_provenance}
        selections = {x.id: x for x in r.reviewed_selections}
        for key, item in texts.items():
            _need(text_value(item) == targets[key], 'represented text differs from domain record')
            if key[0] == 'attributed_statement':
                _need(type(item) is Quotation and item.source_id == statements[key[1]].source_id,
                      'author text requires a source quotation')
            elif key[0] == 'analysis_finding':
                _need(type(item) is FindingText and item.finding_id == key[1], 'finding label mismatch')
            else:
                observation = observations[key[1]]
                if observation.origin_kind == 'source_text':
                    _need(type(item) is Quotation and item.source_id == observation.source_id,
                          'source text requires an attributed excerpt')
                else:
                    selection = selections[provenances[observation.provenance_id].selection_id]
                    if selection.origin.kind == 'finding':
                        _need(type(item) is FindingText and item.finding_id == selection.origin.id,
                              'analysis observation label mismatch')
                    else:
                        statement = statements[selection.origin.id]
                        if type(item) is Paraphrase:
                            _need(item.statement_id == statement.id, 'paraphrase source mismatch')
                        else:
                            _need(type(item) is Quotation and item.source_id == statement.source_id
                                  and text_value(item) == statement.text, 'quotation provenance mismatch')
        return ()
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        # Deliberately avoid reflecting arbitrary submitted fields in logs/errors.
        return ('public research policy rejected: missing review or invalid/out-of-scope content',)


def removal_impact(records, source_ids):
    """Conservative typed dependency closure, including planning and output invalidation."""
    from .write_service import _RECORD_TYPES
    from .media_schema import MEDIA_SPECS
    media = index(public_bundle(records))
    graph = {key: dependencies(key, record, media) for key, record in media.items()}
    specs = {**_RECORD_TYPES, **{k: (col, attr) for k, (col, attr, _) in MEDIA_SPECS.items()}}
    all_records = {(kind, getattr(r, attr)): r for kind, (col, attr) in specs.items()
                   for r in getattr(records, col, ())}
    by_id = {}
    for key in all_records:
        by_id.setdefault(key[1], set()).add(key)
    for key, r in all_records.items():
        refs = set()
        for name in ('evidence_ids', 'related_ids', 'input_ids'):
            for rid in getattr(r, name, ()):
                refs.update(by_id.get(rid, ()))
        for name, kind in (('claim_id', 'claim'), ('rule_id', 'rule'), ('requirement_id', 'requirement')):
            if getattr(r, name, None):
                refs.add((kind, getattr(r, name)))
        # Source owners/backlinks also carry retained text and must be withdrawn.
        if getattr(r, 'source_id', None) and key[0] != 'source':
            refs.add(('source', r.source_id))
        graph.setdefault(key, set()).update(refs)
    for attachment in getattr(records, 'source_attachments', ()):
        if getattr(attachment, 'state', None) == 'active':
            graph.setdefault(('media_version', attachment.media_version_id), set()).add(
                ('source', attachment.source_id))
    affected = {('source', sid) for sid in source_ids}
    referenced_keys = set().union(*graph.values()) if graph else set()
    _need(affected <= all_records.keys() | referenced_keys, 'unknown removal source')
    unresolved = sorted(sid for kind, sid in affected if (kind, sid) not in all_records)
    while True:
        expanded = affected | {key for key, deps in graph.items() if deps & affected}
        if expanded == affected:
            break
        affected = expanded
    # A plan can depend on policy/rules or absence of data, not just recorded IDs.
    # Invalidate all planning/output caches conservatively, never auto-repair support.
    return {'records': sorted(affected), 'unresolved_sources': unresolved, 'plans': 'invalidate_all',
            'outputs': ['html', 'json', 'mcp', 'read_service', 'indexes', 'caches', 'offline_manifests'],
            'published_outputs': 'requires_reviewed_regeneration_or_purge'}


def projection(packet, states=()):
    """Single inert preview model; no public endpoint or active v1 reader."""
    result = []
    for item in packet.texts:
        label = {'quotation': 'Source excerpt', 'paraphrase': 'Wayproof paraphrase',
                 'analysis_finding': 'Wayproof analysis finding'}[item.kind]
        result.append({'kind': item.kind, 'target_kind': item.target_kind, 'target_id': item.target_id,
                       'label': label, 'text': text_value(item), 'provenance': wire(item)})
    return {'texts': result, 'source_states': list(states), 'publication': 'disabled'}


def preview_json(model):
    return json.dumps(model, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def preview_html(model):
    rows = ''.join('<p><strong>' + escape(row['label']) + '</strong> ' +
                   escape(row['text']) + '</p>' for row in model['texts'])
    context = '<p>Support: ' + escape(model.get('support', 'draft')) + '</p>'
    for source in model.get('source_states', ()):
        context += '<p>' + escape(source['source_id']) + ': ' + escape(source['state'])
        if source.get('locator'):
            context += ' <a rel="noreferrer" href="' + escape(safe_url(source['locator']), quote=True) + '">Source</a>'
        context += '</p>'
    for version in model.get('versions', ()):
        context += '<p>' + escape(version['identity_basis'] + ': ' + version['reproducibility']) + ' ' + escape('; '.join(version['limitations'])) + '</p>'
    return '<section>' + rows + context + '<script type="application/json">' + preview_json(model) + '</script></section>'
