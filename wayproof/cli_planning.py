"""Thin terminal rendering for the canonical composed planner."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .planning import PlanningOutcomeState, TripPlan
from .read_service import CanonicalReadService
from .schema import (ActivityContext, EquipmentContext, PartyContext,
                     TripIntent)


def plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return {key: plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def _section(lines: list[str], title: str, values: Iterable[str]) -> None:
    values = tuple(values)
    if values:
        lines.extend(("", title, *(f"  {item}" for item in values)))


def format_canonical_plan(plan: TripPlan) -> str:
    resolution = plan.resolution
    lines = [
        f"Trip plan: {plan.state.value}",
        f"Resolution: {resolution.state.value}",
    ]
    _section(lines, "Objectives:", (
        f"{item.name} [{item.entity_id}]" for item in resolution.objectives
    ))
    if resolution.route:
        lines.append(f"Route: {resolution.route.name} [{resolution.route.entity_id}]")
    if resolution.entry:
        lines.append(f"Entry: {resolution.entry.name} [{resolution.entry.entity_id}]")
    if resolution.exit:
        lines.append(f"Exit: {resolution.exit.name} [{resolution.exit.entity_id}]")
    if resolution.traversal:
        traversal = resolution.traversal
        distance = f"{traversal.total_known_distance_miles:.2f} known mi"
        if not traversal.distance_complete:
            distance += "; total incomplete"
        lines.append(
            f"Traversal: {traversal.state.value}; {len(traversal.legs)} legs; {distance}"
        )
        if traversal.alternate_segment_ids:
            lines.append(
                "Alternates: " + ", ".join(traversal.alternate_segment_ids)
            )
    _section(lines, "Resolution issues:", (
        f"{item.code}: {item.message}" for item in resolution.issues
    ))

    if plan.readiness:
        lines.append(f"Readiness: {plan.readiness.state.value}")
        _section(lines, "Requirements:", (
            f"{item.status.value}: {item.requirement.description} "
            f"[{item.requirement.requirement_id}]"
            for item in plan.readiness.evaluation.requirements
        ))
        _section(lines, "Readiness explanations:", plan.readiness.explanations)

    if plan.operational:
        operational = plan.operational
        lines.append(f"Operational inputs: {operational.state.value}")
        cost = operational.costs
        if cost.total_usd is not None:
            lines.append(f"Cost total: ${cost.total_usd:.2f}")
        elif cost.components:
            lines.append("Cost total: partial; component selection required")
        _section(lines, "Cost components:", (
            f"${item.amount_usd:.2f} {item.label} [{item.input_id}]"
            for item in cost.components
        ))
        _section(lines, "Deadlines:", (
            f"{item.status.value}: {item.input_id}"
            + (f"; opens {item.opens_on.isoformat()}" if item.opens_on else "")
            + (f"; closes {item.closes_on.isoformat()}" if item.closes_on else "")
            for item in operational.deadlines
        ))
        _section(lines, "Inventory checks:", (
            f"{item.state.value}: {item.input_id}"
            + (f"; capacity {item.capacity}; "
               f"{'fits party' if item.fits_party else 'does not fit party'}"
               if item.fits_party is not None else "")
            for item in operational.inventory
        ))
        _section(lines, "Closure checks:", (
            f"{item.state.value}: {item.input_id}" for item in operational.closures
        ))
        _section(lines, "Conflicts:", (
            f"{item.input_id}: {item.explanation}" for item in operational.conflicts
        ))

    _section(lines, "Pre-trip rechecks:", (
        f"{item.state.value}: {item.result_id}" for item in plan.rechecks
    ))
    return "\n".join(lines)


def run_canonical_plan(args) -> tuple[TripPlan, str]:
    intent = TripIntent(
        tuple(args.objectives), date.fromisoformat(args.date),
        route_query=args.route or "", entry_query=args.entry or "",
        exit_query=args.exit_trailhead or "",
        party=PartyContext(tuple(args.participant or ())),
        activities=ActivityContext(
            tuple(args.activity or ()), {"overnight": bool(args.overnight)},
        ),
        equipment=EquipmentContext(tuple(args.equipment or ())),
    )
    reads = CanonicalReadService(Path(args.repository))
    plan = reads.plan(
        intent, recheck_result_ids=tuple(args.recheck_result or ()),
        as_of_date=date.fromisoformat(args.as_of) if args.as_of else None,
    )
    return plan, format_canonical_plan(plan)


def write_plan_json(path: str, plan: TripPlan) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(plain(plan), handle, indent=2, sort_keys=True)
        handle.write("\n")


def canonical_exit_code(plan: TripPlan) -> int:
    return 1 if plan.state in {
        PlanningOutcomeState.AMBIGUOUS, PlanningOutcomeState.UNKNOWN,
    } else 0
