#!/usr/bin/env python3
"""Resolve trip logistics for specific, named objectives.

Unlike ``cli.py``'s experimental geographic clustering, this does not
discover or group objectives -- it assumes you already know what you want to
do and answers: what access applies, what permit governs it, when do you
need to act, and what evidence backs the answer?

To report something you confirmed or found wrong (including a peak missing
from the dataset entirely), use ``report.py`` instead -- a report isn't
tied to a trip date and doesn't need its target to already exist, so it
doesn't belong on this objective/date-resolution flow.

Examples
--------
Access and permit logistics for a single objective::

    python plan.py "Mount Whitney" --date 2027-07-15

A mixed trip from a shared trailhead, including a peak-specific approach
override::

    python plan.py "Mount Whitney" "Mount Russell" --date 2027-07-01

Write the resolved plan as structured JSON::

    python plan.py "Mount Williamson" "Mount Tyndall" --date 2027-07-15 \\
        --output plan.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys

from wayproof.access import load_approaches
from wayproof.advisories import load_advisories
from wayproof.booking import load_booking_channels, load_booking_facilities
from wayproof.camping import load_campgrounds, load_campsites
from wayproof.data_loader import load_peaks, load_trailheads
from wayproof.park_access import load_park_access
from wayproof.regulations import load_regulations
from wayproof.permits import load_permits
from wayproof.plan import resolve_plan, format_plan_summary
from wayproof.water import load_water_sources, load_water_source_log


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=("Resolve access, permit, and evidence logistics for specific, "
                     "named objectives on a given trip date."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("objectives", nargs="+",
                   help="One or more objective names -- a peak, or a campground "
                        "for a trip that is a night at a campsite")
    p.add_argument("--date", required=True, help="Planned trip date (YYYY-MM-DD)")
    p.add_argument("--canonical", action="store_true",
                   help="Plan from canonical Git-backed knowledge through the shared "
                        "service used by MCP. Legacy CSV planning remains the default "
                        "during migration.")
    p.add_argument("--repository", default=".",
                   help="Repository containing canonical/v0 (canonical mode only).")
    p.add_argument("--route", default="",
                   help="Explicit route name or ID; ambiguity is never guessed.")
    p.add_argument("--entry", default="",
                   help="Explicit entry name or ID (canonical mode only).")
    p.add_argument("--activity", action="append", default=[],
                   help="Trip activity such as hiking, backpacking, camping, boating, "
                        "or swimming; repeat for multiple activities.")
    p.add_argument("--overnight", action="store_true",
                   help="Set the canonical overnight activity constraint.")
    p.add_argument("--participant", action="append", default=[],
                   help="Participant ID for fulfillment coverage; repeat as needed.")
    p.add_argument("--equipment", action="append", default=[],
                   help="Equipment ID for rule context; repeat as needed.")
    p.add_argument("--as-of", default="", metavar="YYYY-MM-DD",
                   help="Explicit planning date for deadline status; no wall-clock default.")
    p.add_argument("--recheck-result", action="append", default=[],
                   help="Canonical pre-trip recheck manifest ID; repeat as needed.")
    p.add_argument("--peaks-file", default="data/peaks.csv",
                   help="Core peak dataset: name, coordinates, elevation -- "
                        "collection-agnostic (default data/peaks.csv)")
    p.add_argument("--collections-file", default="data/collections/sps.csv",
                   help="Collection metadata (list, section, official mileage, etc.) "
                        "joined onto --peaks-file by name (default data/collections/sps.csv). "
                        "Pass '' to resolve objectives from core geography alone, "
                        "with no collection metadata.")
    p.add_argument("--list", default="all",
                   help="If the collection data has a 'list' column, keep only this "
                        "list (default 'all', so both SPS and non-SPS-tracked "
                        "objectives resolve; pass 'SPS' to restrict to the 247-peak list)")
    p.add_argument("--trailheads-file", default="data/trailheads.csv",
                   help="Trailhead dataset (default data/trailheads.csv)")
    p.add_argument("--permits-file", default="data/permits.csv",
                   help="Permit rules dataset (default data/permits.csv)")
    p.add_argument("--release-policies-file", default="data/release_policies.csv",
                   help="Structured permit release-phase dataset "
                        "(default data/release_policies.csv)")
    p.add_argument("--approaches-file", default="data/approaches.csv",
                   help="Peak-specific approach/permit relationships "
                        "(default data/approaches.csv)")
    p.add_argument("--water-sources-file", default="data/water_sources.csv",
                   help="Named backcountry water sources (default data/water_sources.csv)")
    p.add_argument("--water-source-log-file", default="data/water_source_log.csv",
                   help="Append-only water-availability check ledger "
                        "(default data/water_source_log.csv)")
    p.add_argument("--campgrounds-file", default="data/campgrounds.csv",
                   help="Backpack campgrounds (default data/campgrounds.csv)")
    p.add_argument("--campsites-file", default="data/campsites.csv",
                   help="Individually-bookable campsites (default data/campsites.csv)")
    p.add_argument("--booking-facilities-file",
                   default="data/booking_facilities.csv",
                   help="CSV of booking-system facilities "
                        "(default data/booking_facilities.csv)")
    p.add_argument("--booking-channels-file", default="data/booking_channels.csv",
                   help="How to book a campsite, scoped by agency "
                        "(default data/booking_channels.csv)")
    p.add_argument("--park-access-file", default="data/park_access.csv",
                   help="Park-level entrance fee/hours dataset (default data/park_access.csv)")
    p.add_argument("--advisories-file", default="data/advisories.csv",
                   help="Conditions with an end -- closures, outages, water quality "
                        "(default data/advisories.csv)")
    p.add_argument("--regulations-file", default="data/regulations.csv",
                   help="Rules in force once you hold the permit "
                        "(default data/regulations.csv)")
    p.add_argument("--exit", dest="exit_trailhead", metavar="TRAILHEAD",
                   help="Trailhead you finish at, if the trip does not end where it "
                        "started. Give the same name as the entry for an explicit "
                        "out-and-back or loop. Omitted means UNKNOWN, not "
                        "returns-to-start -- absence is never read as a route shape.")
    p.add_argument("--output", "-o", help="Write the resolved plan to this JSON file")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    try:
        trip_date = datetime.date.fromisoformat(args.date)
        if args.as_of:
            datetime.date.fromisoformat(args.as_of)
    except ValueError:
        print("--date and --as-of must use YYYY-MM-DD", file=sys.stderr)
        return 2

    if args.canonical:
        from wayproof.cli_planning import (canonical_exit_code,
                                           run_canonical_plan,
                                           write_plan_json)
        result, summary = run_canonical_plan(args)
        print(summary)
        if args.output:
            write_plan_json(args.output, result)
            print(f"\nWrote plan to {args.output}")
        return canonical_exit_code(result)

    list_filter = None if args.list.lower() == "all" else args.list
    peaks = load_peaks(args.peaks_file, list_filter=list_filter,
                        collections_path=args.collections_file or None)
    trailheads = load_trailheads(args.trailheads_file)
    permits = load_permits(args.permits_file, args.release_policies_file)
    approaches = load_approaches(args.approaches_file)
    water_sources = load_water_sources(args.water_sources_file)
    water_source_log = load_water_source_log(args.water_source_log_file)
    campgrounds = load_campgrounds(args.campgrounds_file)
    campsites = load_campsites(args.campsites_file)
    booking_channels = load_booking_channels(args.booking_channels_file)
    booking_facilities = load_booking_facilities(args.booking_facilities_file)
    park_access = list(load_park_access(args.park_access_file).values())
    regulations = load_regulations(args.regulations_file)
    advisories = load_advisories(args.advisories_file)

    result = resolve_plan(args.objectives, trip_date, peaks, trailheads, permits,
                           approaches=approaches, water_sources=water_sources,
                           water_source_log=water_source_log, campgrounds=campgrounds,
                           campsites=campsites,
                           booking_channels=booking_channels,
                           booking_facilities=booking_facilities,
                           park_access=park_access,
                           regulations=regulations, advisories=advisories,
                           exit_trailhead=args.exit_trailhead)

    print(format_plan_summary(result))

    if args.output:
        with open(args.output, "w") as fh:
            json.dump(result.to_dict(), fh, indent=2)
        print(f"\nWrote plan to {args.output}")

    # A campground is an objective too; exiting non-zero on a resolved
    # campsite plan would tell a script the trip could not be planned.
    return 0 if result.has_objectives else 1


if __name__ == "__main__":
    sys.exit(main())
