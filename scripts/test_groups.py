#!/usr/bin/env python3
"""Run an exact, maintainable partition of the pytest module suite."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

SITE = {
    "test_build_site.py",
    "test_east_fork_campsite_inventory.py",
    "test_east_fork_trip_foundation.py",
    "test_ebrpd_depth_completion.py",
    "test_lassen_destination_routes.py",
    "test_lassen_nps_foundation.py",
    "test_rock_creek_corridor_routes.py",
    "test_rock_creek_facility_layer.py",
    "test_rock_creek_nonreservable_depth.py",
    "test_rock_creek_planning_depth.py",
    "test_rock_creek_route_and_summit_depth.py",
    "test_tilden_access_depth.py",
    "test_whitney_human_planning_foundation.py",
    "test_yosemite_campground_inventory.py",
    "test_yosemite_glacier_point_depth.py",
    "test_yosemite_hetch_hetchy_depth.py",
    "test_yosemite_remaining_corridors.py",
    "test_yosemite_nps_foundation.py",
    "test_yosemite_tuolumne_depth.py",
    "test_yosemite_tuolumne_route_depth.py",
    "test_yosemite_valley_depth.py",
    "test_yosemite_wawona_mariposa_depth.py",
}

PLANNING = {
    "test_canonical_cli.py", "test_canonical_planning_parity.py",
    "test_entry_point.py", "test_intent_resolution.py", "test_mcp_server.py",
    "test_planning.py", "test_planning_inputs.py", "test_pretrip_recheck.py",
    "test_requirement_evaluation.py", "test_route_geometry.py",
    "test_route_shape_disclosure.py", "test_surface_agreement.py",
    "test_traversal_resolution.py", "test_trip_cost.py",
    "test_trip_readiness.py", "test_views.py",
}

EBRPD_PREFIXES = (
    "test_chabot_", "test_del_valle_", "test_ebrpd_", "test_ohlone_",
    "test_park_deep_", "test_sunol_", "test_tilden_",
)
SIERRA_PREFIXES = (
    "test_east_fork_", "test_eastern_sierra_", "test_lassen_",
    "test_rock_creek_", "test_sierra_", "test_whitney_", "test_yosemite_",
)
GROUPS = ("core", "planning", "regional-ebrpd", "regional-sierra", "site")


def group_for(name: str) -> str:
    if name in SITE:
        return "site"
    if name in PLANNING:
        return "planning"
    if name.startswith(EBRPD_PREFIXES):
        return "regional-ebrpd"
    if name.startswith(SIERRA_PREFIXES):
        return "regional-sierra"
    return "core"


def partition() -> dict[str, list[Path]]:
    grouped = {name: [] for name in GROUPS}
    for path in sorted(TESTS.glob("test_*.py")):
        grouped[group_for(path.name)].append(path)
    discovered = {path for paths in grouped.values() for path in paths}
    expected = set(TESTS.glob("test_*.py"))
    if discovered != expected or sum(map(len, grouped.values())) != len(expected):
        raise SystemExit("test groups must cover every module exactly once")
    return grouped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", choices=GROUPS)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    grouped = partition()
    for name, paths in grouped.items():
        print(f"{name}: {len(paths)} modules")
    if args.check and not args.group:
        return 0
    if not args.group:
        parser.error("provide --group or --check")
    command = [sys.executable, "-m", "pytest", *map(str, grouped[args.group])]
    command.extend(args.pytest_args or ["-v"])
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
