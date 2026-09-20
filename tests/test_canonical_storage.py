"""Tests for deterministic canonical artifacts and publication enforcement."""

import json

import pytest

from wayproof.canonical_storage import (
    CanonicalStorageError,
    changeset_document,
    load_canonical,
    load_changeset,
    record_document,
    write_candidate,
)
from wayproof.publication import verify_publication
from wayproof.schema import (
    CanonicalRecords,
    ChangeAction,
    ChangeOperation,
    ChangeSet,
    Entity,
)
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository


def operation(action, record_id):
    return ChangeOperation(
        action, "entity", record_id,
        f"canonical/v0/entities/{record_id}.json", "Test publication")


def prepare(change, initial=None):
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(initial))
    writes.propose(change, "researcher")
    assert writes.validate(change.change_set_id, "validator") == ()
    return writes.prepare(change.change_set_id, "builder"), writes.get(change.change_set_id)


def test_record_json_is_deterministic_and_versioned():
    first = record_document("entity", Entity("place-1", "place", "Café"))
    second = record_document("entity", Entity("place-1", "place", "Café"))
    assert first == second
    assert first.endswith("\n")
    payload = json.loads(first)
    assert payload["artifact_format_version"] == 1
    assert payload["schema_version"] == 0
    assert payload["record"]["name"] == "Café"


def test_write_and_load_add_replace_remove_candidate(tmp_path):
    add = ChangeSet(
        "add-place", CanonicalRecords(entities=[Entity("place-1", "place", "Old")]),
        summary="Add place", operations=(operation(ChangeAction.ADD, "place-1"),))
    prepared, validated = prepare(add)
    paths = write_candidate(tmp_path, prepared, validated)
    assert len(paths) == 2
    assert load_canonical(tmp_path) == prepared.result
    persisted = load_changeset(tmp_path / "changesets/v0/add-place.json")
    assert persisted.operations == validated.operations

    edit = ChangeSet(
        "edit-place", CanonicalRecords(entities=[Entity("place-1", "place", "New")]),
        summary="Edit place", operations=(operation(ChangeAction.REPLACE, "place-1"),))
    prepared, validated = prepare(edit, load_canonical(tmp_path))
    write_candidate(tmp_path, prepared, validated)
    assert load_canonical(tmp_path).entities[0].name == "New"

    remove = ChangeSet(
        "remove-place", CanonicalRecords(), summary="Remove place",
        operations=(operation(ChangeAction.REMOVE, "place-1"),))
    prepared, validated = prepare(remove, load_canonical(tmp_path))
    write_candidate(tmp_path, prepared, validated)
    assert load_canonical(tmp_path) == CanonicalRecords()


def test_storage_rejects_unvalidated_changeset():
    change = ChangeSet("draft", CanonicalRecords(), summary="Still a draft")
    with pytest.raises(CanonicalStorageError, match="validated"):
        changeset_document(change)


def test_loader_rejects_filename_identity_mismatch(tmp_path):
    path = tmp_path / "canonical/v0/entities/wrong.json"
    path.parent.mkdir(parents=True)
    path.write_text(record_document("entity", Entity("right", "place", "Right")))
    with pytest.raises(CanonicalStorageError, match="filename"):
        load_canonical(tmp_path)


def test_publication_requires_exact_path_and_action_accounting():
    change = ChangeSet(
        "publish-1", CanonicalRecords(), summary="Publish",
        operations=(operation(ChangeAction.ADD, "place-1"),))
    change.status = change.status.VALIDATED
    clean = [("A", "canonical/v0/entities/place-1.json"),
             ("A", "changesets/v0/publish-1.json")]
    assert verify_publication(clean, [change]) == ()

    assert "exactly one" in verify_publication(clean, [])[0]
    mismatch = [("M", "canonical/v0/entities/place-1.json")]
    assert any("but ADD" in error for error in verify_publication(mismatch, [change]))
    extra = [("A", "canonical/v0/entities/place-1.json"),
             ("A", "canonical/v0/entities/place-2.json")]
    assert any("no ChangeSet operation" in error
               for error in verify_publication(extra, [change]))


def test_changeset_without_canonical_diff_is_rejected():
    change = ChangeSet("orphan", CanonicalRecords(), summary="Orphan")
    assert verify_publication([("A", "changesets/v0/orphan.json")], [change]) == (
        "a ChangeSet was added without a canonical diff",)
