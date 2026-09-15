#!/usr/bin/env python3
"""Inspection commands for the source-verification ledger and the open-gap list.

Trip planning itself lives in ``plan.py``. This file holds the two read-only
views into how the data got here:

    python cli.py --permit-sources desolation   # why we believe what we believe
    python cli.py --open-questions              # what is still unconfirmed

The experimental geographic clustering pipeline that used to dominate this file
was removed. It grouped SPS peaks by DBSCAN and ordered them with a TSP solver,
was never wired into ``plan`` or the published site, and cost more attention in
the README than the product did. It is in git history if it is ever wanted back.
"""

from __future__ import annotations

import argparse
import sys

from wayproof.data_loader import load_peaks, load_trailheads


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Inspect Wayproof's source ledger and its open questions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--permit-sources", nargs="?", const="__all__", default=None,
                   metavar="PERMIT_GROUP",
                   help="Print the verification history for one permit group, "
                        "or all groups when given no value.")
    p.add_argument("--open-questions", action="store_true",
                   help="Print every unconfirmed or conflicting fact currently derivable.")

    p.add_argument("--input", default="data/peaks.csv")
    p.add_argument("--collections-file", default="data/collections/sps.csv")
    p.add_argument("--trailheads", default="data/trailheads.csv")
    p.add_argument("--permits-file", default="data/permits.csv")
    p.add_argument("--release-policies-file", default="data/release_policies.csv")
    p.add_argument("--approaches-file", default="data/approaches.csv")
    p.add_argument("--permit-source-log-file", default="data/permit_source_log.csv")
    p.add_argument("--water-sources-file", default="data/water_sources.csv")
    p.add_argument("--water-source-log-file", default="data/water_source_log.csv")
    p.add_argument("--campgrounds-file", default="data/campgrounds.csv")
    p.add_argument("--campsites-file", default="data/campsites.csv")
    p.add_argument("--timed-entry-file", default="data/timed_entry.csv")
    p.add_argument("--pending-reports-file", default="data/pending_reports.csv")
    p.add_argument("--park-access-file", default="data/park_access.csv")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)

    if args.permit_sources is not None:
        from wayproof.permits import format_source_log, load_source_log
        group = None if args.permit_sources == "__all__" else args.permit_sources
        print(format_source_log(load_source_log(args.permit_source_log_file),
                                permit_group=group))
        return 0

    if args.open_questions:
        from wayproof.access import load_approaches
        from wayproof.camping import load_campgrounds, load_campsites
        from wayproof.park_access import load_park_access
        from wayproof.permits import load_permits, load_source_log
        from wayproof.provenance import load_deferrals, load_sources
        from wayproof.regulations import load_regulations
        from wayproof.reports import (
            format_open_questions, format_pending_reports, open_questions,
            pending_reports,
        )
        from wayproof.timed_entry import load_timed_entry
        from wayproof.water import load_water_source_log, load_water_sources

        by_park = load_timed_entry(args.timed_entry_file)
        questions = open_questions(
            peaks=load_peaks(args.input, collections_path=args.collections_file or None),
            approaches=load_approaches(args.approaches_file),
            water_sources=load_water_sources(args.water_sources_file),
            water_source_log=load_water_source_log(args.water_source_log_file),
            campgrounds=load_campgrounds(args.campgrounds_file),
            campsites=load_campsites(args.campsites_file),
            timed_entry=[p for policies in by_park.values() for p in policies],
            trailheads=load_trailheads(args.trailheads),
            park_access=list(load_park_access(args.park_access_file).values()),
            permits=list(load_permits(args.permits_file,
                                      args.release_policies_file).values()),
            regulations=load_regulations(),
            permit_source_log=load_source_log(args.permit_source_log_file),
            sources=load_sources(), deferrals=load_deferrals(),
            peak_names=None,
        )
        print(format_open_questions(questions))
        print()
        print(format_pending_reports(pending_reports(args.pending_reports_file)))
        return 0

    print("Nothing to do. Use --permit-sources or --open-questions, "
          "or see plan.py for trip planning.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
