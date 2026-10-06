#!/usr/bin/env python3
"""Select the smallest safe CI test-group set for a proposed diff.

Unknown or shared implementation changes deliberately select every group. The
selector only narrows well-understood documentation, regional canonical-data,
test-only, and static-site changes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

try:
    from scripts.test_groups import GROUPS, group_for
except ModuleNotFoundError:  # Direct `python scripts/select_test_groups.py` use.
    from test_groups import GROUPS, group_for


ROOT = Path(__file__).resolve().parents[1]

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


def _regional_groups(path: str) -> set[str]:
    normalized = path.lower()
    groups: set[str] = set()
    if any(token in normalized for token in EBRPD_TOKENS):
        groups.add("regional-ebrpd")
    if any(token in normalized for token in SIERRA_TOKENS):
        groups.add("regional-sierra")
    return groups


def select_groups(paths: list[str], *, full: bool = False) -> list[str]:
    """Return CI groups in the repository's stable display order."""

    if full or not paths:
        return list(GROUPS)

    normalized = [path.strip().removeprefix("./") for path in paths if path.strip()]
    if any(
        path in FULL_SUITE_PATHS or path.startswith(FULL_SUITE_PREFIXES)
        for path in normalized
    ):
        return list(GROUPS)

    groups: set[str] = set()
    canonical_paths: list[str] = []
    unclassified_implementation = False

    for path in normalized:
        if path.startswith("tests/test_") and path.endswith(".py"):
            groups.add(group_for(Path(path).name))
        elif path.startswith("scripts/ingest_") and path.endswith(".py"):
            regional = _regional_groups(path)
            if not regional:
                unclassified_implementation = True
            groups.add("core")
            groups.update(regional)
        elif path in SITE_IMPLEMENTATION_PATHS or path.startswith(SITE_IMPLEMENTATION_PREFIXES):
            groups.update(("core", "planning", "site"))
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
        return list(GROUPS)

    if canonical_paths:
        regional = set().union(*(_regional_groups(path) for path in canonical_paths))
        if not regional:
            return list(GROUPS)
        groups.update(("core", "planning", "site"))
        groups.update(regional)

    # Documentation-only PRs still exercise the inexpensive core contract and
    # partition check, keeping the final required check stable.
    if not groups:
        groups.add("core")

    return [group for group in GROUPS if group in groups]


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
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()

    if args.full:
        paths: list[str] = []
    elif args.paths:
        paths = args.paths
    elif args.base:
        paths = changed_paths(args.base, args.head)
    else:
        parser.error("provide --full, --base, or explicit paths")

    groups = select_groups(paths, full=args.full)
    payload = json.dumps(groups, separators=(",", ":"))
    print(payload)
    if args.github_output:
        with args.github_output.open("a") as output:
            output.write(f"groups={payload}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
