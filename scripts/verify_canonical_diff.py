#!/usr/bin/env python3
"""Fail CI when canonical changes escape the ChangeSet boundary."""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.publication import verify_publication


def changed_paths(base: str, head: str):
    output = subprocess.check_output(
        ["git", "diff", "--no-renames", "--name-status", f"{base}...{head}"],
        text=True,
    )
    result = []
    for line in output.splitlines():
        status, path = line.split("\t", 1)
        result.append((status[0], path))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()
    paths = changed_paths(args.base, args.head)
    change_paths = [Path(path) for status, path in paths
                    if status == "A" and path.startswith("changesets/v0/")]
    changes = [load_changeset(path) for path in change_paths]
    load_canonical(Path("."))
    errors = verify_publication(paths, changes)
    if errors:
        for error in errors:
            print(f"error: {error}")
        return 1
    print("Canonical diff is fully accounted for." if changes
          else "No canonical publication in this diff.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
