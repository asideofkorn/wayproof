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
