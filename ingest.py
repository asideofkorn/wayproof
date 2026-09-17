#!/usr/bin/env python3
"""Turn a source you have read into a validated row plus its ledger entry.

    python ingest.py check campgrounds --set name="Foo Camp" pets_marker=allowed
    python ingest.py add campgrounds \\
        --source https://example.org/foo --summary "what the page said" \\
        --set name="Foo Camp" park="Bar Park" agency_id=ebrpd

`check` writes nothing. `add` refuses without a source and a summary, and
writes the row and the ledger entry together or neither.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from wayproof import ingest, schema
from wayproof.permits import _VALID_VERDICTS


def _parse_set(pairs):
    values = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--set wants column=value, got {pair!r}")
        column, value = pair.split("=", 1)
        values[column.strip()] = value
    return values


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Write a row and the ledger entry that justifies it.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--data-dir", default="data", type=pathlib.Path)
    sub = p.add_subparsers(dest="command", required=True)

    for name, help_text in (("check", "Validate a row without writing it"),
                            ("add", "Write the row and its ledger entry")):
        s = sub.add_parser(name, help=help_text)
        s.add_argument("table", help="e.g. campgrounds.csv, or campgrounds")
        s.add_argument("--set", nargs="+", default=[], metavar="COL=VALUE",
                       help="Column values for the row.")
        if name == "add":
            s.add_argument("--source", required=True,
                           help="URL of the page you read. Required: a row with "
                                "no source is a guess.")
            s.add_argument("--summary", required=True,
                           help="What the source actually said.")
            s.add_argument("--method", default="page read")
            s.add_argument("--verdict", default="new-group", choices=sorted(_VALID_VERDICTS))
            s.add_argument("--permit-group", default=ingest.NO_GROUP)
            s.add_argument("--source-last-updated", default="")
            s.add_argument("--conflict-id", default="")
            s.add_argument("--conflict-kind", default="")
            s.add_argument("--date", default=None, help="YYYY-MM-DD; defaults to today.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    table = args.table if args.table.endswith(".csv") else f"{args.table}.csv"
    values = _parse_set(args.set)

    if not (args.data_dir / table).exists():
        print(f"no such table: {args.data_dir / table}", file=sys.stderr)
        return 2

    if args.command == "check":
        problems = schema.validate_row(table, values, args.data_dir)
        if problems:
            print(f"NOT WRITABLE ({len(problems)}):", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 1
        print(f"writable: {table} <- {values}")
        return 0

    entry = ingest.build_entry(
        source_url=args.source, summary=args.summary, method=args.method,
        verdict=args.verdict, permit_group=args.permit_group, on=args.date,
        source_last_updated=args.source_last_updated,
        conflict_id=args.conflict_id, conflict_kind=args.conflict_kind,
        data_dir=args.data_dir)
    try:
        ingest.add_row(table, values, entry, args.data_dir)
    except ValueError as e:
        print("REFUSED, nothing written:", file=sys.stderr)
        for p in str(e).split("; "):
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"{table} <- {values.get(schema.header(table, args.data_dir)[0])}")
    print(f"{ingest.LOG} <- {entry.entry_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
