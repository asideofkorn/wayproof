"""Deterministic, isolated v1 migration rehearsals. Production remains v0-only.

A workspace owns only its copied baseline, staged additions and generated views.
It cannot update the source repository or authorize publication. GitHub review
receipts are resolved by an independently configured workflow adapter on reads.
"""
from copy import deepcopy
from dataclasses import fields
from hashlib import sha256
import json
from pathlib import Path
import shutil
from urllib.parse import quote

from .canonical_storage import (RECORD_SPECS, _decode, _document, _json_value,
                                load_canonical, UnsupportedSchemaError)
from .media_contract import SPECS, decode_record as media_decode, wire, _typed
from .media_schema import MEDIA_SPECS, MediaRecords
from .media_validation import dependencies
from .public_research import (ReviewedResearch, assess, decode_packet, fingerprint,
                              projection, preview_json)
from .research_workflow import ReviewReceipt
from .schema import ChangeOperation, ChangeSet

ALL_SPECS = {**RECORD_SPECS, **MEDIA_SPECS}
FORMAT = 'wayproof-v1-migration-rehearsal-1'


def digest(data):
    return sha256(data).hexdigest()


def encoded(value):
    return _document(_json_value(value)).encode('utf-8')


def _files(root):
    result = {}
    if root.is_symlink():
        raise ValueError('migration refuses symlinks')
    if not root.exists():
        return result
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('migration refuses symlinks')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def _hashes(files):
    return {path: digest(content) for path, content in sorted(files.items())}


def _baseline(root):
    load_canonical(root)  # Full v0 capability/validation gate before copying.
    return {str(Path(namespace) / path): data
            for namespace in ('canonical', 'changesets')
            for path, data in _files(root / namespace).items()}


def _record_files(change):
    result = {}
    for kind, (collection, attr, _) in ALL_SPECS.items():
        for record in getattr(change.records, collection):
            rid = getattr(record, attr)
            path = f'canonical/v1/{collection}/{rid}.json'
            result[path] = encoded({'artifact_format_version': 1, 'schema_version': 1,
                                   'record_type': kind, 'record': wire(record)})
    return result


def _change_document(change):
    return {'artifact_format_version': 1, 'schema_version': 1,
            'change_set_id': change.change_set_id, 'summary': change.summary,
            'status': 'validated', 'operations': _json_value(change.operations)}


def _decode_change(document, files, order):
    if (set(document) != {'artifact_format_version', 'schema_version', 'change_set_id',
                          'summary', 'status', 'operations'} or type(document['schema_version']) is not int or document['schema_version'] != 1
            or document['artifact_format_version'] != 1 or document['status'] != 'validated'):
        raise UnsupportedSchemaError('unsupported staged ChangeSet')
    values = {f.name: [] for f in fields(MediaRecords)}
    if set(order) != set(files) or len(order) != len(files):
        raise ValueError("record order inventory mismatch")
    for path in order:
        raw = files[path]
        payload = json.loads(raw)
        if (set(payload) != {'artifact_format_version', 'schema_version', 'record_type', 'record'}
                or payload['artifact_format_version'] != 1 or payload['schema_version'] != 1):
            raise UnsupportedSchemaError('unsupported staged record envelope')
        kind, data = payload['record_type'], payload['record']
        collection, attr, cls = ALL_SPECS[kind]
        record = media_decode(kind, data) if kind in SPECS else _decode(cls, data)
        if path != f'canonical/v1/{collection}/{getattr(record, attr)}.json':
            raise ValueError('staged identity/path mismatch')
        values[collection].append(record)
    return ChangeSet(document['change_set_id'], MediaRecords(**values),
                     summary=document['summary'], schema_version=1,
                     operations=tuple(_decode(ChangeOperation, v) for v in document['operations']))


class MigrationWorkspace:
    """Owned rehearsal directory, never a production repository write adapter."""
    def __init__(self, root: Path, workflow):
        self.root, self.workflow = Path(root), workflow

    @classmethod
    def stage(cls, source: Path, destination: Path, change, packet, receipt, workflow):
        source, destination = Path(source).resolve(), Path(destination).resolve()
        if destination == source or source in destination.parents or destination in source.parents:
            raise ValueError('rehearsal must be outside the source repository')
        base_files = _baseline(source)
        base = load_canonical(source)
        change = deepcopy(change)
        if change.validate(existing=base):
            raise ValueError('invalid migration draft')
        fp = fingerprint(change, packet, base)
        review = workflow.resolve(receipt, fp)
        if assess(change, packet, ReviewedResearch((review,)), base):
            raise ValueError('migration policy rejected')
        additions = _record_files(change)
        record_order = list(additions)
        change_path = f'changesets/v1/{change.change_set_id}.json'
        additions[change_path] = encoded(_change_document(change))
        manifest = {
            'format': FORMAT, 'source_version': 0, 'target_version': 1,
            'state': 'staged', 'baseline': _hashes(base_files),
            'additions': _hashes(additions), 'record_order': record_order, 'fingerprint': fp,
            'receipt': wire(receipt), 'change_path': change_path,
            'packet': wire(packet),
            'identity_map': [[op.record_type, op.record_id, op.record_id] for op in change.operations],
            'counts': {col: len(getattr(change.records, col)) for col, _, _ in ALL_SPECS.values()},
            'output_digest': digest(encoded(_hashes(additions))),
            'rollback': 'remove v1 routing; retain baseline and withdrawal marker',
        }
        workspace = cls(destination, workflow)
        # Repeating a dry run is byte-identical; no overwrite of edited/withdrawn work.
        if destination.exists():
            if workspace._manifest() != manifest:
                raise ValueError('destination is not the identical staged migration')
            workspace._verify_files(manifest)
            return workspace
        destination.mkdir(parents=True)
        for path, data in {**base_files, **additions}.items():
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        workspace._save(manifest)
        return workspace

    def _manifest(self):
        if self.root.is_symlink():
            raise ValueError('migration refuses symlinks')
        path = self.root / 'migration.json'
        if path.is_symlink():
            raise ValueError('migration refuses symlinks')
        value = json.loads(path.read_bytes())
        if value.get('format') != FORMAT or value.get('source_version') != 0 or value.get('target_version') != 1:
            raise UnsupportedSchemaError('unsupported migration manifest')
        return value

    def _save(self, manifest):
        path = self.root / 'migration.json'
        if path.is_symlink():
            raise ValueError('migration refuses symlinks')
        path.write_bytes(encoded(manifest))

    def _verify_files(self, manifest, *, removing=False):
        expected = manifest['baseline'] | manifest['additions']
        actual = {str(Path(ns) / path): digest(data)
                  for ns in ('canonical', 'changesets')
                  for path, data in _files(self.root / ns).items()}
        if removing:
            valid = (all(actual.get(k) == v for k, v in manifest['baseline'].items())
                     and all(expected.get(k) == v for k, v in actual.items()))
        else:
            valid = actual == expected
        if not valid:
            raise ValueError('migration artifact inventory/content changed')
        if manifest['output_digest'] != digest(encoded(manifest['additions'])):
            raise ValueError('migration output digest mismatch')

    def _base(self, manifest):
        # Read the untouched v0 copy without relaxing the production root gate.
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in manifest['baseline']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((self.root / name).read_bytes())
            return load_canonical(root)

    def read(self):
        # A retained service handle refreshes on every request, including withdrawal.
        return LiveMigrationReadService(self)

    def _snapshot(self):
        manifest = self._manifest()
        self._verify_files(manifest)
        if manifest['state'] == 'staged' and manifest.get('change_path') not in manifest['additions']:
            raise ValueError('ChangeSet outside staged inventory')
        base = self._base(manifest)
        if manifest['state'] == 'rolled_back':
            raise UnsupportedSchemaError('v1 rehearsal rolled back; select the v0 baseline')
        if manifest['state'] == 'withdrawn':
            return MigrationReadService(base, {}, manifest['withdrawn_ids'], None, ())
        if manifest['state'] != 'staged':
            raise UnsupportedSchemaError('unknown migration state')
        change = _decode_change(json.loads((self.root / manifest['change_path']).read_bytes()), {
            path: (self.root / path).read_bytes() for path in manifest['additions']
            if path.startswith('canonical/v1/')}, manifest['record_order'])
        expected_ids = [[op.record_type, op.record_id, op.record_id] for op in change.operations]
        expected_counts = {col: len(getattr(change.records, col)) for col, _, _ in ALL_SPECS.values()}
        if manifest['identity_map'] != expected_ids or manifest['counts'] != expected_counts:
            raise ValueError('migration counts/identity mapping mismatch')
        packet = decode_packet(manifest['packet'])
        if change.validate(existing=base):
            raise ValueError('invalid persisted migration draft')
        fp = fingerprint(change, packet, base)
        if fp != manifest['fingerprint']:
            raise ValueError('persisted draft no longer matches reviewed snapshot')
        receipt = _typed(ReviewReceipt, manifest['receipt'])
        review = self.workflow.resolve(receipt, fp)
        eligible = not assess(change, packet, ReviewedResearch((review,)), base)
        records = {(kind, getattr(r, attr)): wire(r)
                   for kind, (col, attr, _) in ALL_SPECS.items()
                   for r in getattr(change.records, col)}
        unavailable = tuple(s.source_id for s in review.sources if s.current_state != 'available')
        return MigrationReadService(base, records, (), packet if eligible else None, unavailable)

    def withdraw(self):
        """Withdraw this whole additive batch, erase retained payloads, rebuild owned views.

        Baseline corrections must use a separate v0 ChangeSet; this operation
        cannot remove or restore baseline bytes. No old v1 payload backup is kept.
        """
        manifest = self._manifest()
        self._verify_files(manifest, removing=manifest['state'] == 'removal_hold')
        if manifest['state'] == 'withdrawn':
            return self.export()
        if manifest['state'] == 'staged':
            reads = self._snapshot()  # Revalidate workflow authority before changing custody.
            manifest['withdrawn_ids'] = [list(key) for key in sorted(reads.additions)]
            # Deny reads before touching files; interruption leaves an explicit hold.
            manifest['state'] = 'removal_hold'
            self._save(manifest)
        elif manifest['state'] != 'removal_hold':
            raise ValueError('only staged research can be withdrawn')
        output = self.root / 'outputs'
        if output.exists():
            _files(output)
            shutil.rmtree(output)
        for name in manifest['additions']:
            (self.root / name).unlink(missing_ok=True)
        manifest['additions'] = {}
        manifest['output_digest'] = digest(encoded({}))
        manifest.pop('packet')
        manifest.pop('change_path')
        manifest['state'] = 'withdrawn'
        self._save(manifest)
        self.export()

    def rollback(self):
        manifest = self._manifest()
        self._verify_files(manifest)
        if manifest['state'] == 'staged':
            # Purge retained payloads first, so rollback cannot resurrect them.
            self.withdraw()
            manifest = self._manifest()
        if manifest['state'] != 'withdrawn':
            raise ValueError('rollback requires a completed withdrawal')
        for namespace in ('canonical', 'changesets'):
            v1 = self.root / namespace / 'v1'
            if v1.exists():
                _files(v1)
                shutil.rmtree(v1)
        manifest['state'] = 'rolled_back'
        self._save(manifest)
        # The withdrawal outputs remain, while the original baseline is v0-readable.
        load_canonical(self.root)

    def export(self):
        """Replace the complete owned output set; never incrementally retain stale pages."""
        output = self.root / 'outputs'
        if output.exists():
            _files(output)
            shutil.rmtree(output)
        reads = self._snapshot()
        generation = digest((self.root / "migration.json").read_bytes())
        output.mkdir()
        from .canonical_site import render_evidence_html
        from .mcp_server import WayproofReadTools
        tools = WayproofReadTools(reads)
        index = []
        for kind, rid in reads.keys():
            model = reads.evidence_detail(kind, rid)
            prefix = f'evidence/{quote(kind, safe="")}/{quote(rid, safe="")}'
            directory = output / prefix
            directory.mkdir(parents=True)
            (directory / 'index.json').write_text(preview_json(model))
            (directory / 'index.html').write_text(render_evidence_html(model, ''))
            (directory / 'mcp.json').write_bytes(encoded(tools.get_evidence_detail(kind, rid)))
            index.append({'record_type': kind, 'record_id': rid, 'support': model['support'],
                          'url': '/' + prefix + '/'})
        (output / 'search-index.json').write_bytes(encoded(index))
        (output / 'cache.json').write_bytes(encoded({'generation': digest(encoded(index)),
                                                  'plans': 'invalidated', 'records': index}))
        inventory = _hashes(_files(output))
        (output / 'offline-manifest.json').write_bytes(encoded({
            'generation': digest(encoded(inventory)), 'replace_previous': True, 'files': inventory}))
        if generation != digest((self.root / 'migration.json').read_bytes()):
            shutil.rmtree(output)
            raise ValueError('migration changed during export; outputs withheld')
        return output


class LiveMigrationReadService:
    """No retained data cache; each request revalidates the current staged snapshot."""
    def __init__(self, workspace):
        self._workspace = workspace

    def evidence_detail(self, kind, rid):
        return self._workspace._snapshot().evidence_detail(kind, rid)

    def keys(self):
        return self._workspace._snapshot().keys()

    def explain_claim(self, rid):
        return self.evidence_detail('claim', rid)

    def get(self, kind, rid):
        return self.evidence_detail(kind, rid)

    def plan(self, *args, **kwargs):
        raise UnsupportedSchemaError('v1 planning activation is disabled')


class MigrationReadService:
    """One staged projection; adapters never traverse media records themselves."""
    def __init__(self, base, additions, withdrawn, packet, unavailable):
        self.additions = deepcopy(additions)
        self._records = {(kind, getattr(r, attr)): _json_value(r)
                         for kind, (col, attr, _) in RECORD_SPECS.items()
                         for r in getattr(base, col)} | self.additions
        self._withdrawn = {tuple(key) for key in withdrawn}
        self._packet = packet
        self._unavailable = {('source', sid) for sid in unavailable}

    def keys(self):
        return tuple(sorted(self._records.keys() | self._withdrawn))

    def evidence_detail(self, record_type, record_id):
        key = (record_type, record_id)
        if key not in self.keys():
            raise KeyError('unknown migration record')
        reached, pending = set(), [key]
        unsupported = False
        while pending:
            item = pending.pop()
            if item in reached:
                continue
            reached.add(item)
            record = self._records.get(item)
            if (item in self._withdrawn or item in self._unavailable or record is None
                    or record.get('state', 'active') != 'active'):
                unsupported = True
                continue
            if item in self.additions and self._packet is None:
                unsupported = True
            if item[0] == 'claim' and not record.get('evidence_ids'):
                unsupported = True
            deps = dependencies(item, record, self._records) if item[0] in SPECS else set()
            pending.extend(deps - reached)
            # Every dated unavailable report is explicit; never pick a mutable latest.
            if item[0] == 'media_version':
                for other, report in self._records.items():
                    if (other[0] == 'availability_report' and
                            report.get('media_version_id') == item[1] and
                            report.get('availability') != 'available'):
                        unsupported = True
                        reached.add(other)
        # No fallback to another Evidence when any pinned support is unavailable.
        model = {'projection': 'media-v1-rehearsal', 'record_type': record_type,
                 'record_id': record_id, 'support': 'unsupported' if unsupported else 'traceable',
                 'publication': 'disabled', 'lineage': [], 'texts': []}
        if unsupported:
            model['reason'] = 'Pinned support is withdrawn, unavailable, or not eligible; no substitute selected.'
            model['lineage'] = [{'record_type': kind, 'record_id': rid} for kind, rid in sorted(reached)]
        else:
            model['lineage'] = [{'record_type': kind, 'record_id': rid,
                                 'record': deepcopy(self._records[(kind, rid)])}
                                for kind, rid in sorted(reached)]
            if self._packet:
                model['texts'] = [row for row in projection(self._packet)['texts']
                                  if (row['target_kind'], row['target_id']) in reached]
        return model

    def explain_claim(self, claim_id):
        return self.evidence_detail('claim', claim_id)

    def get(self, record_type, record_id):
        return self.evidence_detail(record_type, record_id)

    def plan(self, *args, **kwargs):
        raise UnsupportedSchemaError('v1 planning activation is disabled')
