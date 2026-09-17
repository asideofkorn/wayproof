#!/usr/bin/env python3
"""Fail when rows were added to the data without a reading to justify them.

Checks the OUTCOME, not the path. Every convention in this repo has drifted --
CONTRIBUTING's test command, the README's counts, "concise comments" -- and
every mechanical check has held. So this does not care whether a row arrived
through `wayproof.ingest.add_row`, a heredoc or an editor; it cares that the ledger
gained an entry when the data gained rows.

    python scripts/check_provenance.py --base origin/main

A restructure legitimately adds no reading: splitting a column out of `notes`
moves facts that were already sourced. Say so with `[migration]` in the commit
message and this stands down.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from typing import Dict, List, Sequence

LEDGER = "data/permit_source_log.csv"
MIGRATION = "[migration]"


def _run(args: Sequence[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout


def row_counts(ref: str, data_dir: str = "data") -> Dict[str, int]:
    """``{path: data row count}`` for every CSV at *ref*. Missing file -> absent."""
    listing = _run(["git", "ls-tree", "-r", "--name-only", ref, data_dir]).split()
    counts = {}
    for path in listing:
        if not path.endswith(".csv"):
            continue
        blob = _run(["git", "show", f"{ref}:{path}"])
        if not blob:
            continue
        # -1 for the header. A trailing newline is not a row.
        counts[path] = max(len(blob.rstrip("\n").splitlines()) - 1, 0)
    return counts


def commit_messages(base: str, head: str) -> str:
    return _run(["git", "log", "--format=%B", f"{base}..{head}"])


def verdict(before: Dict[str, int], after: Dict[str, int],
            messages: str = "") -> List[str]:
    """Problems with this change. Empty means the data gained nothing unsourced.

    One ledger entry may justify many rows -- a single page read added seven
    Anthony Chabot group camps -- so this asks for *an* entry, not one per row.
    """
    grew = {}
    for path, count in after.items():
        if path == LEDGER:
            continue
        if count > before.get(path, 0):
            grew[path] = count - before.get(path, 0)
    if not grew:
        return []
    if MIGRATION in messages:
        return []
    if after.get(LEDGER, 0) > before.get(LEDGER, 0):
        return []
    total = sum(grew.values())
    detail = ", ".join(f"{p} +{n}" for p, n in sorted(grew.items()))
    return [
        f"{total} row(s) added with no new entry in {LEDGER}: {detail}. "
        f"A row with no reading behind it is a guess. Add the entry "
        f"(`wayproof.ingest.add_row` writes both), or say {MIGRATION} in the commit "
        f"message if this moves facts that were already sourced."
    ]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", default="origin/main", help="Ref to compare against.")
    p.add_argument("--head", default="HEAD")
    args = p.parse_args(argv)

    if not _run(["git", "rev-parse", "--verify", "--quiet", args.base]).strip():
        print(f"base ref {args.base!r} not found; nothing to compare", file=sys.stderr)
        return 0

    problems = verdict(row_counts(args.base), row_counts(args.head),
                       commit_messages(args.base, args.head))
    if problems:
        print("PROVENANCE CHECK FAILED", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("provenance: every added row has a reading behind it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
