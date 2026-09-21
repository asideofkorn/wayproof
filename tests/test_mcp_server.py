"""Contract tests for the read-only MCP adapter."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from mcp import Client

from wayproof.mcp_server import (WayproofReadTools, create_server,
                                 planning_context_from_dict,
                                 trip_intent_from_dict)
from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def tools():
    return WayproofReadTools(CanonicalReadService(ROOT))


def whitney_context():
    return {
        "trip_date": "2027-08-12",
        "objectives": [{
            "objective_id": "summit", "entity_id": "peak-mount-whitney",
            "kind": "summit",
        }],
        "stages": [{
            "stage_id": "route", "sequence": 1, "kind": "traverse",
            "spatial_scope_ids": ["scope-route-whitney-classic", "scope-whitney-zone"],
        }],
        "party": {"participant_ids": ["alice", "bob"]},
        "activities": {"activities": ["hiking"], "attributes": {"overnight": True}},
    }


def del_valle_context():
    return {
        "trip_date": "2026-09-21",
        "objectives": [{
            "objective_id": "visit", "entity_id": "park-del-valle-regional-park",
            "kind": "visit",
        }],
        "stages": [{
            "stage_id": "visit", "sequence": 1, "kind": "visit",
            "spatial_scope_ids": ["scope-del-valle-park"],
        }],
    }


def test_tools_search_lookup_provenance_and_history(tools):
    search = tools.search_entities("Whitney", ["peak"])
    assert search == {"count": 1, "entities": [{
        "entity_id": "peak-mount-whitney", "kind": "peak", "name": "Mount Whitney",
    }]}
    entity = tools.get_entity("peak-mount-whitney")
    assert entity["entity"]["name"] == "Mount Whitney"
    provenance = tools.explain_claim("claim-whitney-overnight-scope")
    assert provenance["sources"][0]["source_id"] == "source-recreationgov-mount-whitney"
    history = tools.get_changes("claim-whitney-overnight-scope", "claim")
    assert history["count"] == 1


def test_tools_expose_explicit_gaps_and_contextual_rechecks(tools):
    assert tools.list_knowledge_gaps()["count"] > 0
    recheck = tools.pretrip_recheck(del_valle_context())
    assert recheck["state"] == "required"
    assert any(item["answerability"] == "needs_current_check" for item in recheck["items"])


def test_requirements_and_readiness_use_the_canonical_service(tools):
    requirements = tools.evaluate_requirements(whitney_context())
    requirement = requirements["requirements"][0]["requirement"]
    fulfillment = {
        "fulfillment_id": "group-permit",
        "requirement_id": requirement["requirement_id"],
        "kind": "permit",
        "evidence_ids": ["evidence-whitney-overnight-scope"],
        "coverage": {
            "participant_ids": ["alice", "bob"], "stage_ids": ["route"],
            "starts_on": "2027-08-12", "ends_on": "2027-08-12",
        },
    }
    readiness = tools.evaluate_readiness(whitney_context(), [fulfillment])
    assert readiness["state"] == "ready"


def test_context_parser_rejects_unresolved_or_malformed_inputs():
    with pytest.raises(ValueError, match="trip_date is required"):
        planning_context_from_dict({})
    with pytest.raises(ValueError, match="at least one objective"):
        planning_context_from_dict({
            "trip_date": "2027-01-01",
            "stages": [{"stage_id": "visit", "sequence": 1, "kind": "visit"}],
        })
    with pytest.raises(ValueError, match="ISO date"):
        planning_context_from_dict({"trip_date": "tomorrow"})


def test_intent_parser_and_tool_preserve_ambiguity(tools):
    payload = {
        "trip_date": "2027-08-12",
        "objective_queries": ["Mount Whitney"],
        "activities": {"activities": ["hiking"]},
    }
    assert trip_intent_from_dict(payload).activities.activities == ("hiking",)
    result = tools.resolve_trip_intent(payload)
    assert result["state"] == "ambiguous"
    assert result["context"] is None
    assert result["issues"][0]["candidates"] == [
        "route-mount-whitney-classic", "route-north-fork-lone-pine",
    ]


def test_intent_tool_returns_ordered_traversal_when_canonical_topology_exists(tools):
    result = tools.resolve_trip_intent({
        "trip_date": "2027-09-05",
        "objective_queries": ["Ohlone Wilderness Trail"],
        "entry_query": "Mission Peak Stanford Avenue Staging Area",
        "exit_query": "Lichen Bark Ohlone Trailhead",
    })

    assert result["state"] == "resolved"
    assert result["traversal"]["state"] == "complete"
    assert len(result["traversal"]["legs"]) == 52
    assert result["traversal"]["total_known_distance_miles"] == 26.9
    assert result["traversal"]["distance_complete"] is False


def test_mcp_protocol_discovers_only_read_tools_and_calls_them():
    async def exercise():
        async with Client(create_server(ROOT)) as client:
            discovered = await client.list_tools()
            names = {item.name for item in discovered.tools}
            assert names == {
                "search_entities", "get_record", "get_entity", "explain_claim",
                "get_changes", "list_knowledge_gaps", "evaluate_requirements",
                "evaluate_readiness", "pretrip_recheck", "resolve_trip_intent",
            }
            assert not names.intersection({"propose", "approve", "promote", "publish"})
            assert all(item.description for item in discovered.tools)
            result = await client.call_tool(
                "search_entities", {"query": "Whitney", "kinds": ["peak"]}
            )
            assert not result.is_error
            payload = json.loads(result.content[0].text)
            assert payload["entities"][0]["entity_id"] == "peak-mount-whitney"

    asyncio.run(exercise())
