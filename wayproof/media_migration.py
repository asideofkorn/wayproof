"""Deterministic v1 rehearsal and narrowly reviewed reference publication.

The rehearsal owns an isolated copy. The production adapter reuses its codec,
review and projection boundaries for independent, removable reference batches.
Neither adapter grants publication authority or activates media processing.
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
            or type(document['artifact_format_version']) is not int
            or document['artifact_format_version'] != 1 or document['status'] != 'validated'):
        raise UnsupportedSchemaError('unsupported staged ChangeSet')
    values = {f.name: [] for f in fields(MediaRecords)}
    if set(order) != set(files) or len(order) != len(files):
        raise ValueError("record order inventory mismatch")
    for path in order:
        raw = files[path]
        payload = json.loads(raw)
        if (set(payload) != {'artifact_format_version', 'schema_version', 'record_type', 'record'}
                or type(payload['artifact_format_version']) is not int
                or type(payload['schema_version']) is not int
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
    manifest_name = 'migration.json'
    output_name = 'outputs'

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
        path = self.root / self.manifest_name
        if path.is_symlink():
            raise ValueError('migration refuses symlinks')
        value = json.loads(path.read_bytes())
        if value.get('format') != FORMAT or value.get('source_version') != 0 or value.get('target_version') != 1:
            raise UnsupportedSchemaError('unsupported migration manifest')
        return value

    def _save(self, manifest):
        path = self.root / self.manifest_name
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
        review = self._resolve_review(receipt, fp)
        eligible = not assess(change, packet, ReviewedResearch((review,)), base)
        records = {(kind, getattr(r, attr)): wire(r)
                   for kind, (col, attr, _) in ALL_SPECS.items()
                   for r in getattr(change.records, col)}
        unavailable = tuple(s.source_id for s in review.sources if s.current_state != 'available')
        result = MigrationReadService(base, records, (), packet if eligible else None, unavailable)
        result.change = change
        result.source_states = [{'source_id': s.source_id, 'state': s.current_state,
                                 'inspected_at': s.inspected_at.isoformat()} for s in review.sources]
        return result

    def _resolve_review(self, receipt, fingerprint):
        return self.workflow.resolve(receipt, fingerprint)

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
            # Custody/inventory checks above protect the deletion boundary.
            # Publication authority must never be a prerequisite for withdrawal.
            kinds = {collection: kind for kind, (collection, _, _) in ALL_SPECS.items()}
            owned = []
            for name in manifest['additions']:
                parts = Path(name).parts
                if len(parts) == 4 and parts[:2] == ('canonical', 'v1'):
                    owned.append([kinds[parts[2]], Path(parts[3]).stem])
            manifest['withdrawn_ids'] = sorted(owned)
            # Deny reads before touching files; interruption leaves an explicit hold.
            manifest['state'] = 'removal_hold'
            self._save(manifest)
        elif manifest['state'] != 'removal_hold':
            raise ValueError('only staged research can be withdrawn')
        output = self.root / self.output_name
        if output.exists():
            _files(output)
            shutil.rmtree(output)
        self._purge_extra(manifest)
        for name in manifest['additions']:
            (self.root / name).unlink(missing_ok=True)
        manifest['additions'] = self._tombstones(manifest)
        manifest['output_digest'] = digest(encoded(manifest['additions']))
        manifest.pop('packet')
        manifest.pop('change_path')
        manifest['state'] = 'withdrawn'
        self._save(manifest)
        self.export()

    def _tombstones(self, manifest):
        return {}

    def _purge_extra(self, manifest):
        """Adapter-owned retained metadata, removed while reads are on hold."""

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
        output = self.root / self.output_name
        if output.exists():
            _files(output)
            shutil.rmtree(output)
        reads = self._snapshot()
        generation = digest((self.root / self.manifest_name).read_bytes())
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
        if generation != digest((self.root / self.manifest_name).read_bytes()):
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
    projection_name = 'media-v1-rehearsal'
    publication = 'disabled'

    def __init__(self, base, additions, withdrawn, packet, unavailable):
        self.base = deepcopy(base)
        self.change = None
        self.source_states = []
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
        if key not in self._records and key not in self._withdrawn:
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
        model = {'projection': self.projection_name, 'record_type': record_type,
                 'record_id': record_id, 'support': 'unsupported' if unsupported else 'traceable',
                 'publication': self.publication, 'lineage': [], 'texts': []}
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
        if self.projection_name == 'media-v1-reference':
            model['context'] = reference_context(model['lineage']) if not unsupported else []
            model['source_states'] = deepcopy(self.source_states)
        return model

    def explain_claim(self, claim_id):
        return self.evidence_detail('claim', claim_id)

    def get(self, record_type, record_id):
        return self.evidence_detail(record_type, record_id)

    def plan(self, *args, **kwargs):
        raise UnsupportedSchemaError('v1 planning activation is disabled')


REFERENCE_MANIFEST = 'canonical/v1/reference-publication.json'
REFERENCE_COLLECTIONS = frozenset((
    'sources', 'observations', 'evidence', 'claims', 'media_assets', 'media_versions',
    'availability_reports', 'source_attachments', 'attributed_statements',
    'statement_mappings', 'reviewed_selections', 'observation_provenance',
))


def reference_scope(change):
    """Activation allowlist, narrower than the accepted draft/analysis schema."""
    for field in fields(MediaRecords):
        if field.name not in REFERENCE_COLLECTIONS and getattr(change.records, field.name):
            raise ValueError('reference activation excludes processing and planning records')
    r = change.records
    owned_sources = {s.source_id for s in r.sources}
    if any(item.source_id not in owned_sources for col in
           (r.observations, r.attributed_statements, r.source_attachments) for item in col):
        raise ValueError('reference batches must own their source references')
    if any(s.source_role not in ('original', 'comment') for s in r.sources):
        raise ValueError('reference activation excludes analysis sources')
    if any(o.origin_kind != 'media_statement' for o in r.observations):
        raise ValueError('reference activation requires qualified statement provenance')
    if any(s.origin.kind != 'statement' for s in r.reviewed_selections):
        raise ValueError('reference activation excludes findings')
    for p in r.observation_provenance:
        if not p.event_times or not p.locations:
            raise ValueError('event and location assertions must explicitly preserve unknowns')
        for loc in p.locations:
            if loc.basis_kind == 'unresolved' and (loc.precision_m is not None or loc.value is not None):
                raise ValueError('unresolved location cannot acquire precision or a value')
            if loc.value is not None and (loc.basis_kind != 'author_labeled' or not loc.limitations):
                raise ValueError('reference location requires author attribution and uncertainty')
    # V0 fields must not become a second, less-qualified event/location channel.
    if any(o.observed_at is not None or o.retrieved_at is not None for o in r.observations):
        raise ValueError('reference observations use qualified provenance and version retrieval times')
    if any(c.temporal_scope is not None or c.spatial_scope_ids for c in r.claims):
        raise ValueError('reference claims expose qualified provenance; planning scopes remain disabled')


def configured_research_workflow(root):
    """Wayproof deployment configuration, never loaded from proposal/receipt flags."""
    from .research_workflow import GitHubResearchReviews
    return GitHubResearchReviews(Path(root), 'asideofkorn/wayproof', maintainers=('asideofkorn',))


class ReferenceBatch(MigrationWorkspace):
    """Production adapter over the reviewed migration codec and removal boundary.

    Each batch pins its review baseline while the production v0 tree may evolve.
    It never changes v0 planning, accepts processors, or grants publication authority.
    Git review/merge remains required for prepared files to reach the deployed root.
    """
    manifest_name = REFERENCE_MANIFEST
    output_name = '_site'

    def __init__(self, publication, change_id):
        super().__init__(publication.root, publication.workflow)
        self.publication, self.change_id = publication, change_id

    def _manifest(self):
        value = self.publication._manifest()['batches'][self.change_id]
        if (value.get('format') != FORMAT or type(value.get('source_version')) is not int
                or value['source_version'] != 0 or type(value.get('target_version')) is not int
                or value['target_version'] != 1):
            raise UnsupportedSchemaError('unsupported reference batch format')
        allowed = {'format', 'source_version', 'target_version', 'state', 'baseline',
                   'additions', 'record_order', 'fingerprint', 'receipt', 'change_path',
                   'packet', 'identity_map', 'counts', 'output_digest', 'rollback', 'withdrawn_ids', 'subjects'}
        if set(value) - allowed:
            raise ValueError('unsupported reference manifest fields')
        import re
        if not re.fullmatch('[0-9a-f]{64}', value['fingerprint']):
            raise ValueError('invalid reference fingerprint')
        if value['state'] not in ('staged', 'withdrawn', 'removal_hold'):
            raise ValueError('invalid reference lifecycle state')
        identities = value['identity_map']
        expected_order = []
        for kind, rid, stable in identities:
            if (kind not in ALL_SPECS or not isinstance(rid, str) or rid != stable
                    or not re.fullmatch(r'[A-Za-z0-9_.-]+', rid) or rid in ('.', '..')):
                raise ValueError('invalid durable reference identity')
            expected_order.append(f'canonical/v1/{ALL_SPECS[kind][0]}/{rid}.json')
        if set(expected_order) != set(value['record_order']) or len(expected_order) != len(set(expected_order)):
            raise ValueError('reference identity/order mismatch')
        if value['state'] == 'withdrawn':
            if (value['additions'] != _hashes(reference_tombstones(value)) or 'packet' in value or 'change_path' in value
                    or value['withdrawn_ids'] != sorted([row[:2] for row in identities])):
                raise ValueError('invalid reference withdrawal tombstone')
        collections = {col for col, _, _ in ALL_SPECS.values()}
        for group, version in (('baseline', 'v0'), ('additions', 'v1')):
            for name, hash_value in value[group].items():
                parts = Path(name).parts
                valid = (len(parts) == 4 and parts[:2] == ('canonical', version)
                         and parts[2] in collections) or (
                         len(parts) == 3 and parts[:2] == ('changesets', version))
                if (not valid or name != '/'.join(parts) or '..' in parts
                        or not parts[-1].endswith('.json') or len(hash_value) != 64):
                    raise ValueError('invalid owned reference artifact path/digest')
        # Empty unknown namespaces/collections must fail just like populated ones.
        for ns in ('canonical', 'changesets'):
            parent = self.root / ns
            if parent.exists():
                for version in parent.iterdir():
                    if version.name not in ('v0', 'v1') or not version.is_dir() or version.is_symlink():
                        raise UnsupportedSchemaError('unsupported reference namespace')
                    if ns == 'canonical':
                        for collection in version.iterdir():
                            if collection == self.root / REFERENCE_MANIFEST and collection.is_file() and not collection.is_symlink():
                                continue
                            if collection.name not in collections or not collection.is_dir() or collection.is_symlink():
                                raise UnsupportedSchemaError('unsupported reference collection')
        return value

    def _save(self, value):
        manifest = self.publication._manifest()
        manifest['batches'][self.change_id] = value
        self.publication._save(manifest)

    def _verify_files(self, manifest, *, removing=False):
        self.publication._verify_inventory(removing=removing)

    def _base(self, manifest):
        current = self.publication.current_base()
        if manifest['state'] != 'staged':
            return current
        if self.publication.baseline_hashes() == manifest['baseline']:
            return current
        receipt = _typed(ReviewReceipt, manifest['receipt'])
        try:
            return self.workflow.baseline(receipt, manifest['fingerprint'], manifest['baseline'])
        except Exception as exc:
            raise ReviewUnavailable('reviewed baseline is unavailable') from exc

    def _snapshot(self):
        try:
            result = super()._snapshot()
        except ReviewUnavailable:
            manifest = self._manifest()
            self._verify_files(manifest)
            if manifest['state'] != 'staged':
                raise
            result = MigrationReadService(self.publication.current_base(), {},
                                          [row[:2] for row in manifest['identity_map']], None, ())
            result.source_states = [{'state': 'review_unavailable'}]
        current = self.publication.current_base()
        result.base = current
        result._records = {(kind, getattr(r, attr)): _json_value(r)
                           for kind, (col, attr, _) in RECORD_SPECS.items()
                           for r in getattr(current, col)} | result.additions
        result.change_id = self.change_id
        if result.change is not None:
            if (result.change.change_set_id != self.change_id or
                    self._manifest()['change_path'] != f'changesets/v1/{self.change_id}.json'):
                raise ValueError('reference batch/ChangeSet identity mismatch')
            reference_scope(result.change)
            if self._manifest()['subjects'] != {c.claim_id: c.subject_id for c in result.change.records.claims}:
                raise ValueError('reference subject map differs from reviewed claims')
        result.projection_name = 'media-v1-reference'
        result.publication = 'reviewed_reference'
        return result

    def refresh_review(self, receipt):
        """Pin a separately merged review of the identical content, including unavailability."""
        manifest = self._manifest()
        self._verify_files(manifest)
        if manifest['state'] != 'staged':
            raise ValueError('withdrawn reference content cannot be restored')
        self.workflow.resolve(receipt, manifest['fingerprint'])
        manifest['receipt'] = wire(receipt)
        self._save(manifest)
        return self.export()

    def _resolve_review(self, receipt, fingerprint):
        try:
            return self.workflow.resolve(receipt, fingerprint)
        except Exception as exc:
            raise ReviewUnavailable('research approval is unavailable or revoked') from exc

    def export(self):
        # The production output is a full site build, not the rehearsal renderer.
        return self.publication.export()

    def _tombstones(self, manifest):
        files = reference_tombstones(manifest)
        for name, data in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return _hashes(files)

    def _purge_extra(self, manifest):
        # Current review artifacts can contain source URLs. Historical Git/remote
        # copies require operational cleanup outside this working-tree adapter.
        reviews = self.root / 'research-reviews'
        if reviews.exists():
            _files(reviews)
            (reviews / (manifest['fingerprint'] + '.json')).unlink(missing_ok=True)

    def rollback(self):
        # Retain tombstone routing in production. Disabling it would erase the
        # visible unsupported status and could resurrect old downloaded pages.
        raise ValueError('production rollback uses withdrawal; tombstone routing must remain')


def reference_context(lineage):
    """No fallback between qualified time roles or from subject/proximity to location."""
    records = {(row['record_type'], row['record_id']): row['record'] for row in lineage}
    result = []
    unknown = {'kind': 'unknown', 'certainty': 'unknown', 'basis': {'kind': 'unknown', 'ref': None}}
    for (kind, rid), record in records.items():
        if kind != 'observation_provenance':
            continue
        selection = records[('reviewed_selection', record['selection_id'])]
        statement = records[('attributed_statement', selection['origin']['id'])]
        versions = [records[('media_version', vid)] for vid in selection['media_version_ids']]
        result.append({
            'observation_id': record['observation_id'],
            'event_capture_times': deepcopy(record['event_times']),
            'statement_publication_time': deepcopy(statement['publication_time']),
            'attachment_publication_times': [
                {'attachment_id': aid, 'time': deepcopy(a['publication_time'])}
                for (k, aid), a in records.items() if k == 'source_attachment'
                and a['media_version_id'] in selection['media_version_ids']],
            'retrieval_times': [{'media_version_id': v['id'], 'time': deepcopy(v['retrieval_time'])}
                                for v in versions],
            'analysis_time': deepcopy(unknown),
            'analysis_status': 'not_performed',
            'locations': deepcopy(record['locations']),
            'versions': [{key: deepcopy(v[key]) for key in
                          ('id', 'identity_basis', 'reproducibility', 'limitations')} for v in versions],
        })
    return result


class ReviewUnavailable(ValueError):
    pass


class ReferencePublication:
    """Production index of independently reviewed, independently removable batches."""
    manifest_name = REFERENCE_MANIFEST
    output_name = '_site'
    index_format = 'wayproof-reference-publication-1'

    def __init__(self, root, workflow=None):
        self.root = Path(root)
        self.workflow = workflow if workflow is not None else configured_research_workflow(root)

    def _manifest(self):
        import re
        path = self.root / self.manifest_name
        if self.root.is_symlink() or path.is_symlink():
            raise ValueError('reference publication refuses symlinks')
        value = json.loads(path.read_bytes())
        if (set(value) != {'format', 'batches'} or value['format'] != self.index_format
                or not isinstance(value['batches'], dict) or not value['batches']
                or any(not re.fullmatch(r'[A-Za-z0-9_.-]+', cid) or cid in ('.', '..')
                       for cid in value['batches'])):
            raise UnsupportedSchemaError('unsupported reference publication index')
        return value

    def _save(self, manifest):
        path = self.root / self.manifest_name
        if path.is_symlink():
            raise ValueError('reference publication refuses symlinks')
        path.write_bytes(encoded(manifest))

    def batch(self, change_id=None):
        ids = self._manifest()['batches']
        if change_id is None and len(ids) == 1:
            change_id = next(iter(ids))
        if change_id not in ids:
            raise ValueError('select an existing reference batch explicitly')
        return ReferenceBatch(self, change_id)

    def current_base(self):
        from .canonical_storage import _load_v0_records, _assert_layout
        _assert_layout(self.root, reference=True)
        return _load_v0_records(self.root)

    def baseline_files(self):
        return {f'{ns}/v0/{path}': content for ns in ('canonical', 'changesets')
                for path, content in _files(self.root / ns / 'v0').items()}

    def baseline_hashes(self):
        return _hashes(self.baseline_files())

    def _verify_inventory(self, *, removing=False):
        expected = {}
        optional = set()
        removing_tombstones = {}
        reserved = set()
        for cid in self._manifest()['batches']:
            batch = self.batch(cid)._manifest()
            if set(expected) & set(batch['additions']):
                raise ValueError('reference batches overlap')
            identities = {tuple(row[:2]) for row in batch['identity_map']}
            if reserved & identities:
                raise ValueError('reference identities cannot be reused')
            reserved.update(identities)
            expected.update(batch['additions'])
            if removing and batch['state'] == 'removal_hold':
                optional.update(batch['additions'])
                removing_tombstones.update(_hashes(reference_tombstones(batch)))
            if batch['output_digest'] != digest(encoded(batch['additions'])):
                raise ValueError('reference output digest mismatch')
        actual = {f'{ns}/v1/{path}': digest(content) for ns in ('canonical', 'changesets')
                  for path, content in _files(self.root / ns / 'v1').items()
                  if f'{ns}/v1/{path}' != REFERENCE_MANIFEST}
        if (set(actual) - set(expected) or set(expected) - set(actual) - optional
                or any(expected[path] != content and removing_tombstones.get(path) != content
                       for path, content in actual.items())):
            raise ValueError('reference inventory/content changed')
        self.check_v0_result(self.current_base())

    def check_v0_result(self, records):
        reserved = {tuple(row[:2]) for batch in self._manifest()['batches'].values()
                    for row in batch['identity_map']}
        current = {(kind, getattr(r, attr)) for kind, (col, attr, _) in RECORD_SPECS.items()
                   for r in getattr(records, col)}
        if reserved & current:
            raise ValueError('v0 cannot reuse a reference or withdrawal identity')
        for manifest in self._manifest()['batches'].values():
            for name in manifest['additions']:
                if name.startswith('canonical/v1/sources/') and (self.root / name).exists():
                    source = json.loads((self.root / name).read_bytes())['record']
                    if any(s.locator == source['locator'] for s in records.sources):
                        raise ValueError('v0 cannot alias an independently removable reference source')

    @classmethod
    def prepare(cls, root, change, packet, receipt, workflow=None):
        from tempfile import TemporaryDirectory
        root = Path(root).resolve()
        publication = cls(root, workflow)
        reference_scope(change)
        existing = (publication._manifest() if (root / REFERENCE_MANIFEST).exists()
                    else {'format': cls.index_format, 'batches': {}})
        if change.change_set_id in existing['batches']:
            raise ValueError('reference batch identity already exists')
        if existing['batches']:
            previous = publication._snapshot()
            reserved = set(previous.reference_keys)
            locators = {r.locator for r in previous.base.sources}
            for batch in previous.batches:
                if batch.change is None and batch._withdrawn and batch.source_states:
                    raise ValueError('existing reference review unavailable; cannot establish independence')
                if batch.change is not None:
                    locators.update(s.locator for s in batch.change.records.sources)
        else:
            # Normal v0 root capability gate, including unknown empty versions.
            base = load_canonical(root)
            reserved = set()
            locators = {s.locator for s in base.sources}
        if any(s.locator in locators for s in change.records.sources):
            raise ValueError('source alias requires updating its original batch, not independent corroboration')
        if any((op.record_type, op.record_id) in reserved for op in change.operations):
            raise ValueError('reference identities cannot be reused')
        files = publication.baseline_files()
        with TemporaryDirectory() as directory:
            source = Path(directory) / 'baseline'
            source.mkdir()
            for name, content in files.items():
                path = source / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            staged = MigrationWorkspace.stage(source, Path(directory) / 'candidate', change,
                                               packet, receipt, publication.workflow)
            manifest = staged._manifest()
            manifest['subjects'] = {c.claim_id: c.subject_id for c in change.records.claims}
            if publication.baseline_hashes() != manifest['baseline']:
                raise ValueError('v0 baseline changed during reference preparation')
            for name in manifest['additions']:
                path = root / name
                if path.exists():
                    raise ValueError('reference artifact already exists')
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((staged.root / name).read_bytes())
            existing['batches'][change.change_set_id] = manifest
            publication._save(existing)
        return publication

    def _snapshot(self):
        self._verify_inventory()
        snapshots = [self.batch(cid)._snapshot() for cid in self._manifest()['batches']]
        base = self.current_base()
        locators = {s.locator for s in base.sources}
        for batch in snapshots:
            if batch.change is not None:
                new = {s.locator for s in batch.change.records.sources}
                if locators & new:
                    raise ValueError('reference source aliases cannot become independent support')
                locators.update(new)
        return ReferenceReadService(base, snapshots)

    def subjects(self):
        return {cid: subject for batch in self._manifest()['batches'].values()
                for cid, subject in batch['subjects'].items()}

    def read(self):
        return LiveMigrationReadService(self)

    def records(self):
        snapshot = self._snapshot()
        if any(batch._packet is None and batch.change is not None or
               batch.source_states == [{'state': 'review_unavailable'}] for batch in snapshot.batches):
            raise UnsupportedSchemaError('reference support unavailable; use the evidence read projection')
        return MediaRecords(**{f.name: list(getattr(snapshot.base, f.name, ())) +
                               [r for batch in snapshot.batches if batch.change is not None
                                for r in getattr(batch.change.records, f.name)] +
                               [media_decode(kind, {'id': rid, 'state': 'removed', 'reason_code': 'source_withdrawn'})
                                for batch in snapshot.batches if batch.change is None
                                and not batch.source_states
                                for kind, rid in batch._withdrawn
                                if kind in MEDIA_SPECS and MEDIA_SPECS[kind][0] == f.name]
                               for f in fields(MediaRecords)})

    def withdraw(self, change_id=None):
        self.batch(change_id).withdraw()

    def refresh_review(self, receipt, change_id=None):
        return self.batch(change_id).refresh_review(receipt)

    def export(self):
        from scripts.build_site import build
        build(self.root / self.output_name, root=self.root, research_workflow=self.workflow)
        return self.root / self.output_name


class ReferenceReadService:
    """One combined read projection with no cross-batch substitution."""
    def __init__(self, base, batches):
        self.base, self.batches = base, batches
        self.additions = {key: record for b in batches for key, record in b.additions.items()}
        self._withdrawn = set().union(*(b._withdrawn for b in batches)) if batches else set()
        self.reference_keys = set(self.additions) | self._withdrawn
        self._owners = {key: b for b in batches for key in set(b.additions) | b._withdrawn}

    def keys(self):
        return tuple(sorted(self.reference_keys))

    def evidence_detail(self, kind, rid):
        model = self._owners[(kind, rid)].evidence_detail(kind, rid)
        ids = sorted(identifier for record_type, identifier in self.reference_keys if record_type == kind)
        position = ids.index(rid)
        owner = self._owners[(kind, rid)]
        model['related_records'] = [
            {'record_type': other[0], 'record_id': other[1]}
            for other, record in sorted(owner.additions.items())
            if other[0] in SPECS and (kind, rid) in dependencies(other, record, owner._records)]
        model['navigation'] = {'position': position + 1, 'total': len(ids),
            'previous_id': ids[position - 1] if position else None,
            'next_id': ids[position + 1] if position + 1 < len(ids) else None}
        return model

    def explain_claim(self, rid):
        return self.evidence_detail('claim', rid)

    def get(self, kind, rid):
        return self.evidence_detail(kind, rid)


def reference_tombstones(manifest):
    """Accepted typed tombstones also keep older v0 readers fail-closed after removal."""
    return {f'canonical/v1/{MEDIA_SPECS[kind][0]}/{rid}.json': encoded({
        'artifact_format_version': 1, 'schema_version': 1, 'record_type': kind,
        'record': {'id': rid, 'state': 'removed', 'reason_code': 'source_withdrawn'}})
        for kind, rid, _ in manifest['identity_map'] if kind in MEDIA_SPECS}
