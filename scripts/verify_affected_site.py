#!/usr/bin/env python3
"""Validate affected static-site outputs for a pull-request diff.

The production renderer remains the single renderer.  It is inexpensive enough
to run once; the large saving comes from avoiding every destination-specific
site assertion when only a bounded canonical area changed.  Shared renderer,
schema, workflow, and uncertain changes are routed to the full site shard by
``select_test_groups.py`` instead of this command.
"""

from __future__ import annotations

import argparse
from collections import deque
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PREFIX = "canonical/v0/"
PRIMARY_KEYS = {
    "entities": "entity_id",
    "sources": "source_id",
    "observations": "observation_id",
    "evidence": "evidence_id",
    "claims": "claim_id",
    "relationships": "relationship_id",
    "rules": "rule_id",
    "requirements": "requirement_id",
    "gaps": "gap_id",
    "spatial_scopes": "scope_id",
    "derived_results": "result_id",
}


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _record(path: Path) -> tuple[str, str, dict[str, Any]] | None:
    relative = path.relative_to(ROOT).as_posix()
    if not relative.startswith(CANONICAL_PREFIX) or path.suffix != ".json":
        return None
    folder = relative.split("/")[2]
    key = PRIMARY_KEYS.get(folder)
    if not key:
        return None
    artifact = json.loads(path.read_text(encoding="utf-8"))
    payload = artifact.get("record", artifact)
    identifier = payload.get(key)
    if not isinstance(identifier, str):
        raise ValueError(f"{relative} has no {key}")
    return folder, identifier, payload


def _base_record(base: str, relative: str) -> tuple[str, str, dict[str, Any]] | None:
    result = subprocess.run(
        ["git", "show", f"{base}:{relative}"], cwd=ROOT,
        capture_output=True, text=True,
    )
    if result.returncode:
        return None
    folder = relative.split("/")[2]
    key = PRIMARY_KEYS.get(folder)
    if not key:
        return None
    artifact = json.loads(result.stdout)
    payload = artifact.get("record", artifact)
    identifier = payload.get(key)
    return (folder, identifier, payload) if isinstance(identifier, str) else None


def changed_paths(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"], cwd=ROOT,
        check=True, capture_output=True, text=True,
    )
    return [item for item in result.stdout.splitlines() if item]


def affected_records(base: str, paths: list[str]) -> tuple[set[str], set[str], set[tuple[str, str]]]:
    """Return current entity IDs, removed entity IDs, and affected records.

    Reference expansion is deliberately bounded to two hops in both directions.
    That captures entity/claim/evidence/source and rule/requirement joins without
    turning a common source or broad spatial scope into a whole-corpus test.
    """

    current: dict[str, tuple[str, dict[str, Any]]] = {}
    for path in (ROOT / "canonical/v0").glob("*/*.json"):
        item = _record(path)
        if item:
            folder, identifier, payload = item
            current[identifier] = (folder, payload)

    seeds: set[str] = set()
    removed_entities: set[str] = set()
    for relative in paths:
        if not relative.startswith(CANONICAL_PREFIX) or not relative.endswith(".json"):
            continue
        path = ROOT / relative
        item = _record(path) if path.exists() else None
        old = _base_record(base, relative)
        for candidate in (item, old):
            if candidate:
                folder, identifier, _ = candidate
                seeds.add(identifier)
                if folder == "entities" and item is None:
                    removed_entities.add(identifier)

    known = set(current)
    references = {
        identifier: set(_strings(payload)) & known
        for identifier, (_, payload) in current.items()
    }
    reverse: dict[str, set[str]] = {identifier: set() for identifier in known}
    for owner, targets in references.items():
        for target in targets:
            reverse[target].add(owner)

    affected = set(seeds)
    queue = deque((identifier, 0) for identifier in seeds if identifier in known)
    while queue:
        identifier, depth = queue.popleft()
        if depth >= 2:
            continue
        for neighbor in references.get(identifier, set()) | reverse.get(identifier, set()):
            if neighbor not in affected:
                affected.add(neighbor)
                queue.append((neighbor, depth + 1))

    entities = {
        identifier for identifier in affected
        if current.get(identifier, (None,))[0] == "entities"
    }
    records = {
        (current[identifier][0], identifier)
        for identifier in affected if identifier in current
    }
    return entities, removed_entities, records


def _assert_outputs(output: Path, entities: set[str], removed: set[str],
                    records: set[tuple[str, str]]) -> None:
    search = json.loads((output / "search/index.json").read_text(encoding="utf-8"))
    indexed = {item["entity_id"] for item in search["entities"]}
    missing = entities - indexed
    if missing:
        raise AssertionError(f"affected entities missing from search: {sorted(missing)}")

    for identifier in sorted(entities):
        html = output / "knowledge" / identifier / "index.html"
        payload_path = output / "knowledge" / f"{identifier}.json"
        if not html.is_file() or not payload_path.is_file():
            raise AssertionError(f"missing affected entity output: {identifier}")
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        if payload.get("entity", {}).get("entity_id", payload.get("entity_id")) != identifier:
            raise AssertionError(f"wrong entity payload at {payload_path}")
        geometry_url = payload.get("route_geometry_url")
        if geometry_url and not (output / geometry_url.lstrip("/")).is_file():
            raise AssertionError(f"missing affected route geometry: {geometry_url}")

    for identifier in sorted(removed):
        if (output / "knowledge" / identifier).exists() or (
            output / "knowledge" / f"{identifier}.json"
        ).exists():
            raise AssertionError(f"removed entity still published: {identifier}")

    # Evidence record types exposed by the read service use singular URL names.
    singular = {
        "sources": "source", "observations": "observation", "evidence": "evidence",
        "claims": "claim", "gaps": "gap", "rules": "rule",
        "requirements": "requirement", "relationships": "relationship",
        "spatial_scopes": "spatial_scope", "derived_results": "derived_result",
    }
    published_evidence = {"source", "observation", "evidence", "claim", "gap"}
    for folder, identifier in sorted(records):
        kind = singular.get(folder)
        if not kind:
            continue
        directory = output / "evidence" / kind / identifier
        if kind in published_evidence and not directory.exists():
            raise AssertionError(f"missing affected evidence output: {kind}/{identifier}")
        # Other canonical record kinds are intentionally not public evidence pages.
        if directory.exists() and not all(
            (directory / name).is_file() for name in ("index.html", "index.json")
        ):
            raise AssertionError(f"incomplete affected evidence output: {kind}/{identifier}")

    for required in (
        "index.html", "map/index.html", "map/features.geojson",
        "search/index.html", "changes/index.json", "sitemap.xml", "robots.txt",
    ):
        if not (output / required).is_file():
            raise AssertionError(f"missing shared site output: {required}")


def run(base: str, head: str, output: Path, site_tests: tuple[str, ...]) -> None:
    from scripts import build_site

    paths = changed_paths(base, head)
    entities, removed, records = affected_records(base, paths)
    started = time.monotonic()
    build_site.build(output, root=ROOT)
    rendered = time.monotonic() - started
    _assert_outputs(output, entities, removed, records)
    verified = time.monotonic() - started
    print(
        f"affected-site: rendered production site in {rendered:.1f}s; "
        f"verified {len(entities)} entity pages and {len(records)} linked records "
        f"in {verified:.1f}s"
    )

    tests = tuple(path for path in site_tests if (ROOT / path).is_file())
    if tests:
        env = os.environ.copy()
        env["WAYPROOF_PREBUILT_SITE"] = str(output)
        command = [sys.executable, "-m", "pytest", *tests, "-v"]
        print("affected-site: running changed site modules: " + ", ".join(tests))
        subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site-tests", default="[]", help="JSON array from test selection")
    args = parser.parse_args()
    tests = tuple(json.loads(args.site_tests))
    run(args.base, args.head, args.output, tests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
