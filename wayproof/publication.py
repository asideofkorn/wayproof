"""Checks that a Git diff is authorized by one validated ChangeSet."""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

from .schema import ChangeAction, ChangeSet, ChangeSetStatus


_GIT_ACTIONS = {"A": ChangeAction.ADD, "M": ChangeAction.REPLACE,
                "D": ChangeAction.REMOVE}
_COLLECTIONS = {
    "entity": "entities", "spatial_scope": "spatial_scopes",
    "source": "sources", "observation": "observations",
    "evidence": "evidence", "claim": "claims",
    "relationship": "relationships", "rule": "rules",
    "requirement": "requirements", "fulfillment": "fulfillments",
    "gap": "gaps", "derived_result": "derived_results",
}


def verify_publication(changed_paths: Iterable[Tuple[str, str]],
                       changes: Iterable[ChangeSet]) -> Tuple[str, ...]:
    changed_paths = tuple(changed_paths)
    unsupported = []
    for status, path in changed_paths:
        parts = path.split('/')
        if parts[0] not in ('canonical', 'changesets'):
            continue
        supported = (len(parts) == 4 and parts[:2] == ['canonical', 'v0']
                     and parts[2] in _COLLECTIONS.values() and parts[3].endswith('.json'))
        if parts[0] == 'changesets':
            supported = (len(parts) == 3 and parts[1] == 'v0' and parts[2].endswith('.json'))
            if supported and status != 'A':
                unsupported.append('published ChangeSet cannot be modified or removed: ' + path)
        if not supported:
            unsupported.append('unsupported schema version/collection in publication: ' + path)
    if unsupported:
        return tuple(sorted(unsupported))
    canonical = {path: status for status, path in changed_paths
                 if path.startswith("canonical/v0/")}
    changes = tuple(changes)
    errors = []
    if not canonical:
        if changes:
            errors.append("a ChangeSet was added without a canonical diff")
        return tuple(errors)
    if len(changes) != 1:
        return ("a canonical diff requires exactly one new ChangeSet",)
    change = changes[0]
    if (type(change.schema_version) is not int or change.schema_version != 0 or
            type(change.artifact_format_version) is not int or change.artifact_format_version != 1):
        errors.append('unsupported ChangeSet schema version/format for publication')
    if change.status is not ChangeSetStatus.VALIDATED:
        errors.append("publication ChangeSet must be VALIDATED")
    if not change.summary.strip():
        errors.append("publication ChangeSet summary must not be blank")
    declared: Dict[str, ChangeAction] = {}
    for operation in change.operations:
        collection = _COLLECTIONS.get(operation.record_type)
        expected_path = (f"canonical/v0/{collection}/{operation.record_id}.json"
                         if collection else None)
        if expected_path is None:
            errors.append(f"unknown operation record type: {operation.record_type}")
        elif operation.path != expected_path:
            errors.append(f"operation path must be {expected_path}")
        if operation.path in declared:
            errors.append(f"ChangeSet repeats path: {operation.path}")
        declared[operation.path] = operation.action
    for path, status in canonical.items():
        expected = _GIT_ACTIONS.get(status)
        if expected is None:
            errors.append(f"unsupported Git change status {status}: {path}")
        elif path not in declared:
            errors.append(f"canonical diff has no ChangeSet operation: {path}")
        elif declared[path] is not expected:
            errors.append(
                f"{path} is {status} in Git but {declared[path].value} in ChangeSet")
    for path in sorted(set(declared) - set(canonical)):
        errors.append(f"ChangeSet operation has no canonical diff: {path}")
    return tuple(sorted(set(errors)))


def verify_reference_publication(changed_paths, root, previous_manifest=None, *, workflow=None):
    """One exact batch transition per reviewed diff; the index grants no authority."""
    from pathlib import Path
    from .media_migration import ReferencePublication, REFERENCE_MANIFEST, ALL_SPECS, digest, encoded
    from .media_contract import _typed
    from .research_workflow import ReviewReceipt
    try:
        publication = ReferencePublication(Path(root), workflow)
        manifest = publication._manifest()
        before = previous_manifest['batches'] if previous_manifest else {}
        after = manifest['batches']
        changed = {cid for cid in before.keys() | after.keys() if before.get(cid) != after.get(cid)}
        if len(changed) != 1 or set(before) - set(after):
            raise ValueError('publication requires one explicit batch transition')
        cid = changed.pop()
        new, old = after[cid], before.get(cid)
        marker_status = 'M' if previous_manifest else 'A'
        expected = {REFERENCE_MANIFEST: marker_status}
        if old is None:
            if new['state'] != 'staged':
                raise ValueError('first batch publication must be additive')
            snapshot = publication.batch(cid)._snapshot()
            if snapshot._packet is None:
                raise ValueError('batch lacks eligible reviewed support')
            expected.update({path: 'A' for path in new['additions']})
        elif old['state'] == 'staged' and new['state'] == 'staged':
            if new != dict(old, receipt=new['receipt']) or new['receipt'] == old['receipt']:
                raise ValueError('only a separately reviewed receipt may change')
            publication.workflow.resolve(_typed(ReviewReceipt, new['receipt']), new['fingerprint'])
        else:
            if old['state'] != 'staged' or new['state'] != 'withdrawn':
                raise ValueError('only whole-batch withdrawal is supported')
            from .media_migration import reference_tombstones, _hashes
            tombstones = reference_tombstones(old)
            expected.update({path: ('M' if path in tombstones else 'D') for path in old['additions']})
            expected_batch = dict(old)
            kinds = {col: kind for kind, (col, _, _) in ALL_SPECS.items()}
            expected_batch['withdrawn_ids'] = sorted(
                [kinds[Path(path).parts[2]], Path(path).stem] for path in old['record_order'])
            expected_batch['state'] = 'withdrawn'
            expected_batch['additions'] = _hashes(tombstones)
            expected_batch['output_digest'] = digest(encoded(expected_batch['additions']))
            expected_batch.pop('packet')
            expected_batch.pop('change_path')
            if new != expected_batch:
                raise ValueError('withdrawal differs from the prior owned inventory')
        publication._snapshot()  # Unavailable review produces unsupported output, never fallback.
        paths = {path: status for status, path in changed_paths
                 if path == REFERENCE_MANIFEST or path.split('/')[0] in ('canonical', 'changesets')}
        if paths != expected:
            raise ValueError('reference publication diff differs from the complete owned inventory')
        return ()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return ('reference publication rejected: ' + str(exc),)
