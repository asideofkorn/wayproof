"""Step 4 design oracle, NOT a production validator or privacy enforcement layer.

Only tests import this file. It validates synthetic JSON, traces references, and
calculates a removal impact set. No networking, media processing, storage writes,
canonical service calls, authentication, or real deletion happens here.
"""
from datetime import date, datetime
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

HERE = Path(__file__).parent
SCHEMA = json.loads((HERE / 'schema.json').read_text())
COLLECTIONS = json.loads((HERE / 'collections.json').read_text())
CHECK = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
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
    deps = set(basis_refs(record))
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


def validate(public, private, reviewed_changesets=(), legacy_observation_ids=()):
    """Synthetic review tokens are test inputs, not authenticated approvals."""
    CHECK.validate(public)
    CHECK.validate(private)
    require(public['visibility'] == 'public' and private['visibility'] == 'private', 'store separation')
    records = index(public)
    custody = {item['media_version_id']: item for item in private['custody']}
    require(len(custody) == len(private['custody']), 'duplicate custody for a version')
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
        for value in values(item):
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
        if kind == 'media_version':
            require(rid in custody, 'version needs a separate operational review')
            policy = custody[rid]
            require(policy['release_review'] == 'approved', 'public release review absent')
            require('public_display' in policy['permitted_uses'], 'public metadata release not permitted')
            if policy['acquisition'] == 'contributed':
                require(set(policy['permitted_uses']) <= set(policy['contribution_scope']), 'contribution scope')
            if item['identity_basis'] == 'permitted_digest':
                require(policy['content_hash'] is not None, 'digest identity basis requires permitted private hash')
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
                    require('analysis' in custody[target['media_version_id']]['permitted_uses'], 'analysis permission')
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
                require(set(item['metadata_fields']) <= set(custody[item['target']['media_version_id']][
                    'permitted_exif_fields']), 'EXIF permission absent')
            require(item['modality'] == 'metadata' or not item['metadata_fields'], 'metadata modality mismatch')
        if kind == 'reviewed_selection':
            require(item['change_set_id'] in reviewed_changesets, 'selection needs separate reviewed ChangeSet')
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
                            and item['event_times'][0]['value'] == observation['observed_at'], 'capture time substitution')
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
        if kind == 'legacy_artifact_mapping':
            observation = get('observation', item['observation_id'])
            version = get('media_version', item['media_version_id'])
            selection = get('reviewed_selection', item['reviewed_selection_id'])
            require(item['migration_id'] in reviewed_changesets, 'legacy mapping needs reviewed migration')
            if active(observation):
                require(item['artifact_ref_index'] < len(observation['artifact_refs']), 'missing legacy reference')
            if active(version) and active(selection):
                require(version['asset_id'] == item['asset_id'] and item['media_version_id'] in selection['media_version_ids'],
                        'legacy mapping version mismatch')
    return records


def validate_transition(before, after, reviewed_changeset=None):
    """Pure proposal diff check; neither argument is mutated or persisted."""
    old, new = index(before), index(after)
    require(before == after or reviewed_changeset is not None, 'canonical change requires separate review')
    for key, value in old.items():
        require(key in new, 'removal needs a non-sensitive tombstone in this synthetic contract')
        if key[0] == 'source' and not active(value):
            require(not active(new[key]), 'removed source identity cannot be reused')
        if key[0] == 'source' and active(value) and active(new[key]):
            require(value.get('source_role') == new[key].get('source_role'),
                    'source role cannot be reclassified; allocate a distinct source')
        if (key[0] not in LEGACY_IDS or key[0] == 'observation') and new[key] != value:
            require(not active(new[key]), 'immutable media record cannot be overwritten')


def validate_custody_transition(before, after, reviewed_removal=None):
    """Private identity bindings cannot be replaced, even under another custody ID.

    A synthetic removal token permits erasure, never replacement of a digest.
    This function does not authenticate the token or erase stored bytes.
    """
    old = {item['media_version_id']: item for item in before['custody']}
    new = {item['media_version_id']: item for item in after['custody']}
    require(len(old) == len(before['custody']) and len(new) == len(after['custody']),
            'duplicate custody for a version')
    for vid, prior in old.items():
        if vid not in new:
            require(reviewed_removal is not None, 'custody erasure needs reviewed removal')
            continue
        current = new[vid]
        require(current['id'] == prior['id'], 'immutable custody/version binding')
        if current['content_hash'] != prior['content_hash']:
            require(current['content_hash'] is None and reviewed_removal is not None,
                    'changed digest requires new media version')


def removal_impact(bundle, target):
    """Conservative dependency plan ONLY. No data or cache is deleted."""
    records = index(bundle)
    require(target in records, 'unknown removal target')
    affected = {target}
    while True:
        added = {key for key, item in records.items() if dependencies(key, item, records) & affected}
        if added <= affected:
            return affected
        affected |= added


def explain_media_claim(bundle, claim_id):
    """Synthetic read-model example; explicit unavailable/unsupported projection."""
    records = index(bundle)
    start = ('claim', claim_id)
    require(start in records, 'unknown claim')
    seen, pending = set(), [start]
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        if key in records:
            pending.extend(dependencies(key, records[key], records))
    missing = [key for key in seen if key not in records or not active(records[key])]
    version_ids = {rid for kind, rid in seen if kind == 'media_version'}
    availability = [r for (kind, _), r in records.items() if kind == 'availability_report'
                    and active(r) and r['media_version_id'] in version_ids]
    return {'claim_id': claim_id, 'availability_reports': availability, 'support': ('unavailable' if missing else 'traceable' if any(k == 'observation_provenance' for k, _ in seen) else 'legacy_source_only'),
            'records': sorted(seen), 'unavailable_records': sorted(missing)}


def origin_groups(bundle, version_ids):
    """Shared-origin grouping, never an assertion of independent corroboration."""
    records = index(bundle)
    groups = set()
    for vid in version_ids:
        asset_id = records['media_version', vid]['asset_id']
        seen = set()
        while True:
            require(asset_id not in seen, 'cyclic origin')
            seen.add(asset_id)
            asset = records['media_asset', asset_id]
            if not active(asset) or asset['origin_asset_id'] is None:
                break
            asset_id = asset['origin_asset_id']
        groups.add(asset_id)
    return {'shared_origin_groups': sorted(groups), 'independence': 'not_established'}
