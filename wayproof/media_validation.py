"""Media contract graph checks, used by the production draft validator.

This checks lineage and bounded assertions, not permissions, consent or safety.
Selections are proposed within a ChangeSet, not caller-asserted review grants.
V1 preparation/publication remains disabled until the remaining gates exist.
"""
from datetime import date, datetime

from .media_contract import CHECK, COLLECTIONS

LEGACY_IDS = {'source': 'source_id', 'observation': 'observation_id',
              'evidence': 'evidence_id', 'claim': 'claim_id'}
PRIVATE_KEYS = {'content_hash', 'storage_locator', 'raw_exif', 'filename',
                'requester_reference', 'access_roles', 'retention_deadline'}
ANALYSIS_KEYS = {'run_id', 'finding_id', 'analysis_run_id', 'analysis_finding_id',
                 'selection_id', 'analysis_refs', 'latest_run', 'latest_finding'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identifier(kind, record):
    return record.get(LEGACY_IDS.get(kind, 'id'))


def active(record):
    return record.get('state', 'active') == 'active'


def values(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from values(child)
    elif isinstance(value, list):
        for child in value:
            yield from values(child)


def index(bundle):
    result = {}
    for collection, kind in COLLECTIONS.items():
        for record in bundle['records'][collection]:
            key = kind, identifier(kind, record)
            require(key not in result, 'duplicate record identity')
            result[key] = record
    return result


def basis_refs(record):
    for value in values(record):
        if isinstance(value, dict) and set(value) == {'kind', 'ref'}:
            kind, target = value['kind'], value['ref']
            if kind in ('clock', 'unknown'):
                require(target is None, 'clock/unknown cannot carry a foreign reference')
            else:
                require(target is not None, 'qualified value needs its basis')
                yield {'statement': 'attributed_statement', 'finding': 'analysis_finding',
                       'source': 'source'}[kind], target


def dependencies(key, record, records):
    """Support dependencies, not every owner/backlink (which can be cyclic)."""
    if not active(record):
        return set()
    kind, rid = key
    # Claim.value is opaque domain data, not a second provenance language.
    deps = set() if kind == 'claim' else set(basis_refs(record))
    single = {
        'media_version': [('asset_id', 'media_asset')],
        'availability_report': [('media_version_id', 'media_version')],
        'source_attachment': [('source_id', 'source'), ('asset_id', 'media_asset'),
                              ('media_version_id', 'media_version')],
        'attributed_statement': [('source_id', 'source')],
        'statement_mapping': [('statement_id', 'attributed_statement')],
        'analysis_run': [('source_id', 'source')],
        'analysis_finding': [('run_id', 'analysis_run')],
        'observation_provenance': [('selection_id', 'reviewed_selection')],
        'observation': [('source_id', 'source')],
        'evidence': [('observation_id', 'observation')],
        'legacy_artifact_mapping': [('observation_id', 'observation'), ('asset_id', 'media_asset'),
                                    ('media_version_id', 'media_version'),
                                    ('reviewed_selection_id', 'reviewed_selection')],
    }
    deps.update((target_kind, record[field]) for field, target_kind in single.get(kind, ()))
    if kind == 'media_asset' and record['origin_asset_id']:
        deps.add(('media_asset', record['origin_asset_id']))
        deps.add(('attributed_statement', record['origin_statement_id']))
    if kind == 'statement_mapping':
        deps.update(('source_attachment', item) for item in record['attachment_ids'])
    if kind == 'analysis_run':
        deps.update(('media_version', item['media_version_id']) for item in record['inputs'])
        deps.update(('source_attachment', item['source_attachment_id']) for item in record['inputs'])
    if kind == 'analysis_finding':
        deps.add(('media_version', record['target']['media_version_id']))
        deps.add(('source_attachment', record['target']['source_attachment_id']))
        deps.update(('evidence', item) for item in record['corroborating_evidence_ids'])
    if kind == 'reviewed_selection':
        deps.add(({'statement': 'attributed_statement', 'finding': 'analysis_finding'}[
            record['origin']['kind']], record['origin']['id']))
        deps.update(('media_version', item) for item in record['media_version_ids'])
        if record['mapping_id']:
            deps.add(('statement_mapping', record['mapping_id']))
    if kind == 'claim':
        deps.update(('evidence', item) for item in record['evidence_ids'])
    if kind == 'observation' and record.get('origin_kind') in ('media_statement', 'media_analysis'):
        # The declared edge survives removal of its target's payload/backlink.
        deps.add(('observation_provenance', record['provenance_id']))
    return deps


def validate_time(value):
    kind = value['kind']
    if kind == 'unknown':
        require(value['basis']['kind'] == 'unknown', 'unknown time must stay unknown')
    elif kind == 'range':
        parse = date.fromisoformat if value['precision'] == 'date' else datetime.fromisoformat
        start, end = parse(value['start']), parse(value['end'])
        require(start <= end, 'reversed time range')
        if value['precision'] == 'instant':
            require(start.tzinfo is not None and end.tzinfo is not None, 'instant needs timezone')


def validate_selector(selector, version):
    kind = selector['kind']
    if kind == 'whole':
        require(version['media_type'] == 'image', 'video/audio inspection must name bounded time')
    elif kind == 'image_region':
        size = version['dimensions']
        require(version['media_type'] == 'image' and size is not None, 'region needs image dimensions')
        require(selector['x'] + selector['width'] <= size['width'] and
                selector['y'] + selector['height'] <= size['height'], 'region out of bounds')
    else:
        duration = version['duration_ms']
        require(version['media_type'] in ('video', 'audio') and duration is not None,
                'timed inspection needs duration')
        if kind == 'time_range':
            require(selector['start_ms'] < selector['end_ms'] <= duration, 'time range out of bounds')
        else:
            require(version['media_type'] == 'video' and
                    max(selector['timestamps_ms']) < duration, 'frame out of bounds')


def covered(finding, inspected):
    if finding == inspected:
        return True
    if inspected['kind'] == 'whole':
        return finding['kind'] == 'image_region'
    if finding['kind'] == inspected['kind'] == 'time_range':
        return inspected['start_ms'] <= finding['start_ms'] < finding['end_ms'] <= inspected['end_ms']
    if finding['kind'] == inspected['kind'] == 'image_region':
        return (inspected['x'] <= finding['x'] and inspected['y'] <= finding['y'] and
                finding['x'] + finding['width'] <= inspected['x'] + inspected['width'] and
                finding['y'] + finding['height'] <= inspected['y'] + inspected['height'])
    if finding['kind'] == inspected['kind'] == 'frames':
        return set(finding['timestamps_ms']) <= set(inspected['timestamps_ms'])
    return False


def validate_graph(public, change_set_id, legacy_observation_ids=()):
    """Validate proposed selection intent, never attest to reviewer approval."""
    CHECK.validate(public)
    require(public['visibility'] == 'public', 'public draft required')
    records = index(public)
    for node in values(public):
        if isinstance(node, dict):
            require(not PRIVATE_KEYS.intersection(node), 'private fields cannot enter public records')
    analysis_ids = {rid for kind, rid in records if kind in ('analysis_run', 'analysis_finding')}
    graph = {key: dependencies(key, item, records) for key, item in records.items()}
    for key, deps in graph.items():
        require(deps <= records.keys(), f'missing typed reference: {key} -> {deps - records.keys()}')
    visiting, visited = set(), set()
    def visit(key):
        require(key not in visiting, 'cyclic support/origin graph')
        if key not in visited:
            visiting.add(key)
            for dep in graph[key]:
                visit(dep)
            visiting.remove(key)
            visited.add(key)
    for key in graph:
        visit(key)
    def get(kind, rid):
        require((kind, rid) in records, f'missing {kind} reference')
        return records[kind, rid]
    for (kind, rid), item in records.items():
        if not active(item):
            continue
        for value in (() if kind == 'claim' else values(item)):
            if isinstance(value, dict) and 'certainty' in value and 'kind' in value:
                validate_time(value)
        if kind == 'observation':
            if rid not in legacy_observation_ids:
                require('origin_kind' in item, 'new observation must declare origin kind')
            if 'origin_kind' in item:
                if item['origin_kind'] == 'source_text':
                    require(item['provenance_id'] is None, 'source-text observation cannot disguise media provenance')
                else:
                    provenance = get('observation_provenance', item['provenance_id'])
                    if active(provenance):
                        require(provenance['observation_id'] == rid, 'observation provenance backlink mismatch')
        if kind == 'media_asset':
            require(bool(item['origin_asset_id']) == bool(item['origin_statement_id']), 'repost needs basis')
        if kind == 'source_attachment':
            source = get('source', item['source_id'])
            if active(source):
                require(source.get('source_role') != 'analysis_report', 'attachment needs original source')
            version = get('media_version', item['media_version_id'])
            if active(version):
                require(version['asset_id'] == item['asset_id'], 'attachment asset/version mismatch')
            require((item['ordinal'] is None) == (item['ordinal_basis'] == 'unknown'), 'unknown attachment order')
        if kind == 'attributed_statement':
            source = get('source', item['source_id'])
            if active(source):
                require(source.get('source_role') != 'analysis_report', 'statement needs original/comment source')
            require((item['speaker']['role'] == 'unknown') == (item['speaker']['attribution'] is None),
                    'speaker identity must be explicit or unknown')
            if item['corrects_statement_id']:
                get('attributed_statement', item['corrects_statement_id'])
        if kind == 'statement_mapping':
            n = len(item['attachment_ids'])
            require(item['mapping_kind'] != 'single' or n == 1, 'single mapping cardinality')
            require(item['mapping_kind'] != 'multiple' or n > 1, 'multiple mapping cardinality')
            require((item['list_item'] is not None) == (item['mapping_kind'] == 'ordered_item'), 'ordered item basis')
            require((item['mapping_kind'] == 'ambiguous') == (item['certainty'] != 'explicit'), 'mapping uncertainty')
        if kind == 'analysis_run':
            source = get('source', item['source_id'])
            if active(source):
                require(source.get('source_role') == 'analysis_report', 'run needs typed analysis-report source')
            for target in item['inputs']:
                version = get('media_version', target['media_version_id'])
                attachment = get('source_attachment', target['source_attachment_id'])
                if active(attachment):
                    require(attachment['media_version_id'] == target['media_version_id'], 'run attachment/version mismatch')
                if active(version):
                    validate_selector(target['selector'], version)
        if kind == 'analysis_finding':
            run = get('analysis_run', item['run_id'])
            if active(run):
                require(item['modality'] in run['modalities'], 'modality outside run')
                require(any(t['media_version_id'] == item['target']['media_version_id'] and
                            t['source_attachment_id'] == item['target']['source_attachment_id'] and
                            covered(item['target']['selector'], t['selector']) for t in run['inputs']),
                        'finding exceeds inspected input')
            version = get('media_version', item['target']['media_version_id'])
            if active(version):
                validate_selector(item['target']['selector'], version)
            require(item['modality'] == 'metadata' or not item['metadata_fields'], 'metadata modality mismatch')
        if kind == 'reviewed_selection':
            require(item['change_set_id'] == change_set_id, 'selection must belong to this proposed ChangeSet')
            if item['origin']['kind'] == 'finding':
                require(item['mapping_id'] is None, 'finding selection cannot use author mapping')
                finding = get('analysis_finding', item['origin']['id'])
                if active(finding):
                    require(item['media_version_ids'] == [finding['target']['media_version_id']], 'selection version mismatch')
            else:
                mapping = get('statement_mapping', item['mapping_id'])
                if active(mapping):
                    require(mapping['statement_id'] == item['origin']['id'], 'selection speaker statement mismatch')
                    require(mapping['certainty'] == 'explicit', 'ambiguous mapping cannot be selected')
                    attachments = [get('source_attachment', aid) for aid in mapping['attachment_ids']]
                    if all(active(a) for a in attachments):
                        require(set(item['media_version_ids']) == {a['media_version_id'] for a in attachments},
                                'selection version mismatch')
        if kind == 'observation_provenance':
            observation = get('observation', item['observation_id'])
            selection = get('reviewed_selection', item['selection_id'])
            require(sum(active(r) and r['observation_id'] == item['observation_id'] for (k, _), r in records.items()
                        if k == 'observation_provenance') == 1, 'observation cannot have a moving selection')
            if active(observation) and active(selection):
                require(observation.get('provenance_id') == rid, 'provenance must be pinned on observation')
                require(observation.get('origin_kind') == {'statement':'media_statement', 'finding':'media_analysis'}[selection['origin']['kind']], 'observation origin mismatch')
                origin_kind = 'attributed_statement' if selection['origin']['kind'] == 'statement' else 'analysis_finding'
                origin = get(origin_kind, selection['origin']['id'])
                if active(origin):
                    owner = origin if origin_kind == 'attributed_statement' else get('analysis_run', origin['run_id'])
                    if active(owner):
                        require(observation['source_id'] == owner['source_id'], 'observation source attribution mismatch')
                        speaker = (owner['speaker']['attribution'] or '') if origin_kind == 'attributed_statement' else owner['analyst']['label']
                        require(observation['observer'] == speaker, 'observation speaker attribution mismatch')
                for assertion in item['event_times'] + item['locations']:
                    basis = assertion['basis']
                    require(basis['kind'] == 'unknown' or (basis['kind'] == selection['origin']['kind'] and
                            basis['ref'] == selection['origin']['id']), 'assertion bypasses reviewed selection')
                if observation['observed_at'] is not None:
                    require(len(item['event_times']) == 1 and item['event_times'][0].get('kind') == 'instant'
                            and item['event_times'][0]['certainty'] == 'exact'
                            and datetime.fromisoformat(item['event_times'][0]['value']) ==
                            datetime.fromisoformat(observation['observed_at']), 'capture time substitution')
            for time in item['event_times']:
                require(time['basis']['kind'] in ('statement', 'finding', 'unknown'), 'event time requires event basis')
            for location in item['locations']:
                if location['basis_kind'] == 'unresolved':
                    require(location['value'] is None and location['generalization'] in ('unknown', 'withheld'), 'unresolved location')
                if location['sensitivity'] != 'nonsensitive':
                    require(location['value'] is None or (location['value']['kind'] == 'region' and
                            location['generalization'] == 'generalized'), 'sensitive location must be withheld/generalized')
                required = {'author_labeled': 'statement', 'visible_sign': 'finding', 'corroborated': 'finding',
                            'exif_permitted': 'finding', 'inferred': 'finding', 'unresolved': 'unknown'}
                require(location['basis']['kind'] == required[location['basis_kind']], 'location basis mismatch')
                if location['basis_kind'] == 'exif_permitted':
                    finding = get('analysis_finding', location['basis']['ref'])
                    if active(finding):
                        require('gps' in finding['metadata_fields'], 'location requires permitted GPS finding')
                if location['basis_kind'] in ('corroborated', 'visible_sign'):
                    finding = get('analysis_finding', location['basis']['ref'])
                    if active(finding):
                        if location['basis_kind'] == 'corroborated':
                            require(bool(finding['corroborating_evidence_ids']), 'corroborated location needs Evidence')
                        else:
                            require(finding['modality'] in ('visual', 'ocr'), 'sign location needs visual/OCR finding')
        if kind == 'evidence':
            claim = get('claim', item['claim_id'])
            if active(claim):
                require(rid in claim['evidence_ids'], 'evidence not cited by named claim')
        if kind == 'claim':
            for eid in item['evidence_ids']:
                evidence = get('evidence', eid)
                if active(evidence):
                    require(evidence['claim_id'] == rid, 'evidence belongs to another claim')
            for value in values(item):
                require(not (isinstance(value, str) and value in analysis_ids), 'direct analysis reference in claim value')
                if isinstance(value, dict):
                    require(not ANALYSIS_KEYS.intersection(value), 'direct analysis key in claim value')
                    require(not (value.get('kind') in ('run', 'finding', 'analysis_run', 'analysis_finding')
                                 and ('ref' in value or 'id' in value)), 'direct analysis reference in claim value')
        if kind == 'legacy_artifact_mapping':
            observation = get('observation', item['observation_id'])
            version = get('media_version', item['media_version_id'])
            selection = get('reviewed_selection', item['reviewed_selection_id'])
            require(item['migration_id'] == change_set_id, 'legacy mapping must belong to this proposed ChangeSet')
            if active(observation):
                require(item['artifact_ref_index'] < len(observation['artifact_refs']), 'missing legacy reference')
            if active(version) and active(selection):
                require(version['asset_id'] == item['asset_id'] and item['media_version_id'] in selection['media_version_ids'],
                        'legacy mapping version mismatch')
    return records



def validate_media_change(change, existing):
    """Validate a detached additive v1 draft against a trusted v0 baseline.

    A selection's ChangeSet ID expresses proposed intent only. There is no
    caller-supplied list of reviewed IDs. V1 prepare/write/publish stay disabled.
    """
    from dataclasses import fields
    from jsonschema import ValidationError
    from .schema import CanonicalRecords, Source, Observation, ChangeAction
    from .media_schema import MediaRecords, MEDIA_SPECS, MediaSource, MediaObservation
    from .media_contract import public_bundle, decode_record, wire
    from .record_contract import shape_errors
    from .validation import validate_records
    from .write_service import _RECORD_TYPES

    errors = shape_errors(change.records, media=True) + shape_errors(existing)
    if errors:
        return tuple(sorted(set(errors)))
    specs = {**_RECORD_TYPES, **{k: (v[0], v[1]) for k, v in MEDIA_SPECS.items()}}
    targets = {(kind, getattr(r, attr)) for kind, (col, attr) in specs.items()
               for r in getattr(change.records, col)}
    operations = [(o.record_type, o.record_id) for o in change.operations]
    if len(operations) != len(set(operations)) or set(operations) != targets:
        errors.append('v1 ChangeSet must account for every record exactly once')
    if not change.summary.strip():
        errors.append('ChangeSet summary must not be blank')
    for op in change.operations:
        if op.action is not ChangeAction.ADD:
            errors.append('v1 replacement/removal requires the later lifecycle workflow')
        if op.record_type not in specs:
            errors.append('unknown v1 operation record type')
            continue
        col, _ = specs[op.record_type]
        if op.path != f'canonical/v1/{col}/{op.record_id}.json':
            errors.append('v1 operation must use its derived canonical/v1 path')
        if '/' in op.record_id or '\\' in op.record_id or op.record_id in ('.', '..'):
            errors.append('record ID must be a single path component')
        evidence_ids = {e.evidence_id for e in existing.evidence + change.records.evidence}
        gap_ids = {g.gap_id for g in existing.gaps + change.records.gaps}
        if set(op.evidence_refs) - evidence_ids or set(op.knowledge_gap_refs) - gap_ids:
            errors.append('v1 operation references unknown evidence/gap')

    # Ordinary canonical referential, scope and rule checks still apply. This
    # internal projection is never a read/export surface or a storage downgrade.
    core = CanonicalRecords(**{f.name: list(getattr(change.records, f.name))
                               for f in fields(CanonicalRecords)})
    core.sources = [Source(r.source_id, r.locator, r.publisher) if type(r) is MediaSource else r
                    for r in core.sources]
    core.observations = [Observation(r.observation_id, r.source_id, r.content,
                                    r.observed_at, r.retrieved_at, r.observer, r.artifact_refs)
                         if type(r) is MediaObservation else r for r in core.observations]
    errors.extend(validate_records(core, existing=existing))
    combined = MediaRecords(**{f.name: list(getattr(existing, f.name, ())) +
                              list(getattr(change.records, f.name)) for f in fields(MediaRecords)})
    try:
        for kind, (col, _) in specs.items():
            if kind in MEDIA_SPECS or kind in ('source', 'observation', 'evidence', 'claim'):
                for record in getattr(combined, col):
                    require(decode_record(kind, wire(record)) == record,
                            'media values must use their exact domain types')
        validate_graph(public_bundle(combined), change.change_set_id,
                       {r.observation_id for r in existing.observations})
        # Qualified entity locations still use the ordinary entity registry.
        entity_ids = {r.entity_id for r in combined.entities}
        for provenance in combined.observation_provenance:
            if active(wire(provenance)):
                for location in provenance.locations:
                    if getattr(location.value, 'kind', None) == 'entity':
                        require(location.value.entity_id in entity_ids, 'unknown location entity')
    except (ValueError, TypeError, ValidationError) as exc:
        # No raw media or submitted text in error messages.
        errors.append('invalid media contract: ' + ('closed public wire shape rejected'
                      if isinstance(exc, ValidationError) else str(exc)))
    return tuple(sorted(set(errors)))
