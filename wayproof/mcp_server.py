"""Read-only Model Context Protocol adapter for canonical Wayproof services."""

from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from .read_service import CanonicalReadService
from .schema import (
    ActivityContext,
    Coverage,
    EquipmentContext,
    Fulfillment,
    PartyContext,
    PlanningContext,
    TripIntent,
    TripObjective,
    TripStage,
)


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _date(value: Any, field: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD)") from exc


def _tuple(value: Any) -> tuple:
    return tuple(value or ())


def planning_context_from_dict(payload: dict[str, Any]) -> PlanningContext:
    """Parse an adapter payload without inventing unresolved trip choices."""
    if not isinstance(payload, dict):
        raise ValueError("context must be an object")
    trip_date = _date(payload.get("trip_date"), "trip_date")
    if trip_date is None:
        raise ValueError("trip_date is required")
    objectives = tuple(
        TripObjective(item["objective_id"], item["entity_id"], item["kind"])
        for item in payload.get("objectives", ())
    )
    stages = tuple(
        TripStage(item["stage_id"], int(item["sequence"]), item["kind"],
                  _tuple(item.get("spatial_scope_ids")))
        for item in payload.get("stages", ())
    )
    if not objectives:
        raise ValueError("at least one objective is required")
    if not stages:
        raise ValueError("at least one stage is required")
    party = payload.get("party") or {}
    activities = payload.get("activities") or {}
    equipment = payload.get("equipment") or {}
    return PlanningContext(
        trip_date=trip_date,
        objectives=objectives,
        stages=stages,
        party=PartyContext(_tuple(party.get("participant_ids")),
                           dict(party.get("attributes") or {})),
        activities=ActivityContext(_tuple(activities.get("activities")),
                                   dict(activities.get("attributes") or {})),
        equipment=EquipmentContext(
            _tuple(equipment.get("equipment_ids")),
            dict(equipment.get("attributes") or {}),
            _tuple(equipment.get("prior_events")),
        ),
    )


def trip_intent_from_dict(payload: dict[str, Any]) -> TripIntent:
    """Parse a user request while keeping route and access choices optional."""
    if not isinstance(payload, dict):
        raise ValueError("intent must be an object")
    trip_date = _date(payload.get("trip_date"), "trip_date")
    if trip_date is None:
        raise ValueError("trip_date is required")
    objectives = _tuple(payload.get("objective_queries"))
    if not objectives:
        raise ValueError("at least one objective query is required")
    party = payload.get("party") or {}
    activities = payload.get("activities") or {}
    equipment = payload.get("equipment") or {}
    return TripIntent(
        objective_queries=objectives,
        trip_date=trip_date,
        route_query=str(payload.get("route_query") or ""),
        entry_query=str(payload.get("entry_query") or ""),
        exit_query=str(payload.get("exit_query") or ""),
        party=PartyContext(_tuple(party.get("participant_ids")),
                           dict(party.get("attributes") or {})),
        activities=ActivityContext(_tuple(activities.get("activities")),
                                   dict(activities.get("attributes") or {})),
        equipment=EquipmentContext(
            _tuple(equipment.get("equipment_ids")),
            dict(equipment.get("attributes") or {}),
            _tuple(equipment.get("prior_events")),
        ),
    )
def _coverage(payload: dict[str, Any] | None) -> Coverage:
    payload = payload or {}
    return Coverage(
        participant_ids=_tuple(payload.get("participant_ids")),
        equipment_ids=_tuple(payload.get("equipment_ids")),
        stage_ids=_tuple(payload.get("stage_ids")),
        starts_on=_date(payload.get("starts_on"), "coverage.starts_on"),
        ends_on=_date(payload.get("ends_on"), "coverage.ends_on"),
    )


def fulfillments_from_list(payload: list[dict[str, Any]] | None) -> tuple[Fulfillment, ...]:
    return tuple(
        Fulfillment(
            item["fulfillment_id"], item["requirement_id"], item["kind"],
            _tuple(item.get("evidence_ids")), _coverage(item.get("coverage")),
        )
        for item in (payload or ())
    )


class WayproofReadTools:
    """Transport-neutral tool implementations used by MCP and direct tests."""

    def __init__(self, reads: CanonicalReadService):
        self.reads = reads

    def search_entities(self, query: str = "", kinds: list[str] | None = None) -> dict:
        """Search canonical entities by name or ID, optionally filtering exact kinds."""
        entities = self.reads.search_entities(query, kinds or ())
        return {"count": len(entities), "entities": _plain(entities)}

    def get_record(self, record_type: str, record_id: str) -> dict:
        """Get one canonical record by its collection type and durable record ID."""
        return {"record_type": record_type, "record": _plain(
            self.reads.get(record_type, record_id)
        )}

    def get_entity(self, entity_id: str) -> dict:
        """Get an entity with its claims, relationships, and explicit knowledge gaps."""
        return _plain({
            "entity": self.reads.entity(entity_id),
            "claims": self.reads.claims_for(entity_id),
            "relationships": self.reads.relationships_for(entity_id),
            "knowledge_gaps": self.reads.knowledge_gaps_for(entity_id),
        })

    def explain_claim(self, claim_id: str) -> dict:
        """Trace a claim through supporting evidence, observations, and sources."""
        return _plain(self.reads.explain_claim(claim_id))

    def get_changes(self, record_id: str = "", record_type: str = "") -> dict:
        """List published ChangeSet operations, optionally filtered by record."""
        entries = self.reads.changes(record_id or None, record_type or None)
        return {"count": len(entries), "changes": _plain(entries)}

    def list_knowledge_gaps(self, record_id: str = "") -> dict:
        """List all explicit knowledge gaps or only gaps related to one record."""
        gaps = (self.reads.knowledge_gaps_for(record_id)
                if record_id else self.reads.knowledge_gaps())
        return {"count": len(gaps), "knowledge_gaps": _plain(gaps)}

    def resolve_trip_intent(self, intent: dict[str, Any]) -> dict:
        """Resolve named objectives into a bounded canonical planning context."""
        return _plain(self.reads.resolve_intent(trip_intent_from_dict(intent)))

    def plan_trip(self, intent: dict[str, Any],
                  fulfillments: list[dict[str, Any]] | None = None,
                  recheck_result_ids: list[str] | None = None) -> dict:
        """Resolve a trip and evaluate readiness plus explicitly named rechecks."""
        return _plain(self.reads.plan(
            trip_intent_from_dict(intent),
            fulfillments_from_list(fulfillments),
            _tuple(recheck_result_ids),
        ))

    def evaluate_requirements(self, context: dict[str, Any]) -> dict:
        """Evaluate applicable canonical rules and requirements for a resolved context."""
        return _plain(self.reads.requirements(planning_context_from_dict(context)))

    def evaluate_readiness(self, context: dict[str, Any],
                           fulfillments: list[dict[str, Any]] | None = None) -> dict:
        """Evaluate bounded Trip Readiness and explicit fulfillment coverage."""
        parsed = planning_context_from_dict(context)
        return _plain(self.reads.readiness(parsed, fulfillments_from_list(fulfillments)))

    def pretrip_recheck(self, context: dict[str, Any]) -> dict:
        """Return contextual facts and gaps that must be rechecked before a trip."""
        return _plain(self.reads.pretrip_recheck(planning_context_from_dict(context)))


def create_server(root: Path | str = Path(".")) -> MCPServer:
    """Create a stdio/HTTP-capable read server rooted at a Wayproof checkout."""
    tools = WayproofReadTools(CanonicalReadService(Path(root)))
    server = MCPServer(
        "wayproof",
        title="Wayproof canonical outdoor planning reads",
        description=(
            "Read source-backed Wayproof entities, provenance, publication history, "
            "requirements, readiness, and contextual pre-trip rechecks."
        ),
        version="0.1.0",
        instructions=(
            "Treat unknown or needs-current-check results explicitly. Do not infer "
            "permission, availability, or safety from missing records. This server "
            "has no canonical write, approval, or promotion tools."
        ),
    )

    server.tool(name="search_entities")(tools.search_entities)
    server.tool(name="get_record")(tools.get_record)
    server.tool(name="get_entity")(tools.get_entity)
    server.tool(name="explain_claim")(tools.explain_claim)
    server.tool(name="get_changes")(tools.get_changes)
    server.tool(name="list_knowledge_gaps")(tools.list_knowledge_gaps)
    server.tool(name="resolve_trip_intent")(tools.resolve_trip_intent)
    server.tool(name="plan_trip")(tools.plan_trip)
    server.tool(name="evaluate_requirements")(tools.evaluate_requirements)
    server.tool(name="evaluate_readiness")(tools.evaluate_readiness)
    server.tool(name="pretrip_recheck")(tools.pretrip_recheck)
    return server


def main() -> None:
    root = Path(os.environ.get("WAYPROOF_REPOSITORY", ".")).resolve()
    create_server(root).run(transport="stdio")


if __name__ == "__main__":
    main()
