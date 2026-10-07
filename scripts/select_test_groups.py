#!/usr/bin/env python3
"""Select the smallest safe CI test-group set for a proposed diff.

Unknown or shared implementation changes deliberately select every group. The
selector only narrows well-understood documentation, regional canonical-data,
test-only, and static-site changes.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

try:
    from scripts.test_groups import GROUPS, group_for
except ModuleNotFoundError:  # Direct `python scripts/select_test_groups.py` use.
    from test_groups import GROUPS, group_for


ROOT = Path(__file__).resolve().parents[1]
MAIN_SMOKE_GROUPS = ("core", "planning")

EBRPD_TOKENS = (
    "chabot", "del-valle", "del_valle", "ebrpd", "ohlone",
    "redwood-regional", "sunol", "tilden",
)
SIERRA_TOKENS = (
    "bishop", "east-fork", "east_fork", "eastern-sierra", "emigrant",
    "inyo", "kings-canyon", "lassen", "rock-creek", "rock_creek",
    "sierra", "taboose", "whitney", "yosemite",
)

FULL_SUITE_PATHS = {
    "pyproject.toml",
    "requirements.txt",
    "scripts/select_test_groups.py",
    "scripts/test_groups.py",
    "tests/conftest.py",
}
FULL_SUITE_PREFIXES = (".github/workflows/", "schema/", "schemas/")
SITE_IMPLEMENTATION_PATHS = {"scripts/build_site.py", "wayproof/canonical_site.py"}
SITE_IMPLEMENTATION_PREFIXES = ("site_assets/", "static/", "templates/")
CANONICAL_PREFIXES = ("canonical/", "changesets/", "geometry/")
DOC_PREFIXES = (".agents/", "docs/", "sources/")


@dataclass(frozen=True)
class TestScope:
    """CI work selected for one diff.

    ``affected`` site validation uses the production renderer once and limits
    assertions to changed records, their dependants, and explicitly changed
    site-test modules. ``full`` retains the exhaustive site shard.
    """

    groups: tuple[str, ...]
    site_mode: str
    site_tests: tuple[str, ...] = ()


def main_smoke_scope() -> TestScope:
    """Fast post-merge integration coverage; exhaustive checks belong on PRs."""

    return TestScope(MAIN_SMOKE_GROUPS, "none")


def _regional_groups(path: str) -> set[str]:
    normalized = path.lower()
    groups: set[str] = set()
    if any(token in normalized for token in EBRPD_TOKENS):
        groups.add("regional-ebrpd")
    if any(token in normalized for token in SIERRA_TOKENS):
        groups.add("regional-sierra")
    return groups


def _regional_site_tests(paths: list[str]) -> set[str]:
    """Select established destination-site modules named by changed paths."""

    tokens = {
        token.replace("-", "_")
        for path in paths
        for token in (*EBRPD_TOKENS, *SIERRA_TOKENS)
        if token in path.lower()
    }
    selected: set[str] = set()
    tests_dir = ROOT / "tests"
    for path in tests_dir.glob("test_*.py"):
        name = path.name.lower().replace("-", "_")
        if group_for(path.name) == "site" and any(token in name for token in tokens):
            selected.add(path.relative_to(ROOT).as_posix())
    return selected


def select_scope(paths: list[str], *, full: bool = False) -> TestScope:
    """Return the smallest safe test scope for the supplied paths."""

    if full or not paths:
        return TestScope(tuple(GROUPS), "full")

    normalized = [path.strip().removeprefix("./") for path in paths if path.strip()]
    if any(
        path in FULL_SUITE_PATHS or path.startswith(FULL_SUITE_PREFIXES)
        for path in normalized
    ):
        return TestScope(tuple(GROUPS), "full")

    groups: set[str] = set()
    site_tests: set[str] = set()
    canonical_paths: list[str] = []
    unclassified_implementation = False
    site_mode = "none"

    for path in normalized:
        if path.startswith("tests/test_") and path.endswith(".py"):
            group = group_for(Path(path).name)
            if group == "site":
                site_tests.add(path)
                site_mode = "affected"
            else:
                groups.add(group)
        elif path.startswith("scripts/ingest_") and path.endswith(".py"):
            regional = _regional_groups(path)
            if not regional:
                unclassified_implementation = True
            groups.add("core")
            groups.update(regional)
        elif path in SITE_IMPLEMENTATION_PATHS or path.startswith(SITE_IMPLEMENTATION_PREFIXES):
            groups.update(("core", "planning", "site"))
            site_mode = "full"
        elif path.startswith(CANONICAL_PREFIXES):
            canonical_paths.append(path)
        elif path.endswith(".md") or path.startswith(DOC_PREFIXES):
            continue
        elif path.startswith(("wayproof/", "scripts/")) or path in {
            "cli.py", "plan.py", "report.py"
        }:
            unclassified_implementation = True
        else:
            # A new top-level format or unfamiliar file may affect packaging or
            # runtime behavior. Prefer excess testing to a false narrow run.
            unclassified_implementation = True

    if unclassified_implementation:
        return TestScope(tuple(GROUPS), "full")

    if canonical_paths:
        regional = set().union(*(_regional_groups(path) for path in canonical_paths))
        if not regional:
            return TestScope(tuple(GROUPS), "full")
        groups.update(("core", "planning"))
        groups.update(regional)
        site_mode = "affected"
        site_tests.update(_regional_site_tests(canonical_paths))

    # Documentation-only PRs still exercise the inexpensive core contract and
    # partition check, keeping the final required check stable.
    if not groups:
        groups.add("core")

    if "site" in groups:
        site_mode = "full"
        site_tests.clear()
    return TestScope(
        tuple(group for group in GROUPS if group in groups),
        site_mode,
        tuple(sorted(site_tests)),
    )


def select_groups(paths: list[str], *, full: bool = False) -> list[str]:
    """Compatibility wrapper returning groups in stable display order."""

    return list(select_scope(paths, full=full).groups)


def changed_paths(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--main-smoke", action="store_true")
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()

    if args.main_smoke:
        if args.base or args.paths:
            parser.error("--main-smoke cannot be combined with --base or explicit paths")
        scope = main_smoke_scope()
    elif args.full:
        paths: list[str] = []
        scope = select_scope(paths, full=True)
    elif args.paths:
        paths = args.paths
        scope = select_scope(paths)
    elif args.base:
        paths = changed_paths(args.base, args.head)
        scope = select_scope(paths)
    else:
        parser.error("provide --full, --main-smoke, --base, or explicit paths")

    payload = json.dumps(scope.groups, separators=(",", ":"))
    print(payload)
    if args.github_output:
        with args.github_output.open("a") as output:
            output.write(f"groups={payload}\n")
            output.write(f"site_mode={scope.site_mode}\n")
            output.write(
                "site_tests="
                + json.dumps(scope.site_tests, separators=(",", ":"))
                + "\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
