"""TripIntent resolution remains bounded by canonical identity and topology."""

from datetime import date
from pathlib import Path

import pytest

from wayproof.intent import IntentResolutionState
from wayproof.read_service import CanonicalReadService
from wayproof.schema import TripIntent


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def reads():
    return CanonicalReadService(ROOT)


def intent(*objectives, **choices):
    return TripIntent(objectives, date(2027, 9, 5), **choices)


def issue_codes(result):
    return {item.code for item in result.issues}


def test_whitney_requires_a_route_choice_when_multiple_are_sourced(reads):
    result = reads.resolve_intent(intent("Mount Whitney"))

    assert result.state is IntentResolutionState.AMBIGUOUS
    assert result.context is None
    assert result.issues[0].code == "route_ambiguous"
    assert set(result.issues[0].candidates) == {
        "route-high-sierra-trail",
        "route-mount-whitney-classic",
        "route-mount-whitney-east-buttress",
        "route-mount-whitney-east-face",
        "route-mount-whitney-mountaineers",
        "route-north-fork-lone-pine",
    }


def test_explicit_whitney_route_resolves_but_does_not_infer_an_exit(reads):
    result = reads.resolve_intent(intent(
        "Mount Whitney", route_query="Mount Whitney Trail",
    ))

    assert result.state is IntentResolutionState.PARTIAL
    assert result.route.entity_id == "route-mount-whitney-classic"
    assert result.entry.entity_id == "trailhead-whitney-portal"
    assert result.exit is None
    assert issue_codes(result) == {"exit_unknown"}
    assert result.context.objectives[0].entity_id == "peak-mount-whitney"


def test_an_explicit_return_to_the_start_is_not_confused_with_an_inferred_loop(reads):
    result = reads.resolve_intent(intent(
        "Mount Whitney", route_query="Mount Whitney Trail",
        entry_query="Whitney Portal",
        exit_query="Whitney Portal",
    ))

    assert result.state is IntentResolutionState.PARTIAL
    assert result.entry == result.exit
    assert result.traversal.state.value == "unavailable"
    assert issue_codes(result) == {"traversal_unavailable"}
    assert [stage.kind for stage in result.context.stages] == [
        "entry", "traverse", "summit", "exit",
    ]


def test_shared_route_is_selected_for_williamson_and_tyndall(reads):
    result = reads.resolve_intent(intent("Mount Williamson", "Mount Tyndall"))

    assert result.state is IntentResolutionState.PARTIAL
    assert result.route.entity_id == "route-shepherd-pass"
    assert result.entry.entity_id == "trailhead-shepherd-pass-hiker"
    assert [item.entity_id for item in result.context.objectives] == [
        "peak-mount-williamson", "peak-mount-tyndall",
    ]
    assert issue_codes(result) == {"exit_unknown"}


def test_ohlone_endpoints_resolve_through_member_route_legs(reads):
    result = reads.resolve_intent(intent(
        "Ohlone Wilderness Trail",
        entry_query="Mission Peak Stanford Avenue Staging Area",
        exit_query="Lichen Bark Ohlone Trailhead",
    ))

    assert result.state is IntentResolutionState.RESOLVED
    assert result.route.entity_id == "trail-ohlone-wilderness"
    assert result.entry.entity_id == "staging-mission-peak-stanford-avenue"
    assert result.exit.entity_id == "trailhead-ohlone-lichen-bark"
    assert result.traversal.state.value == "complete"
    assert len(result.traversal.legs) == 52
    assert len(result.context.stages) == 55
    assert result.context.stages[1].stage_id == "route-leg-ohlone-mainline-001"


def test_a_route_not_sourced_for_the_objective_is_rejected(reads):
    result = reads.resolve_intent(intent(
        "Mount Whitney", route_query="Shepherd Pass Trail",
    ))

    assert result.state is IntentResolutionState.AMBIGUOUS
    assert result.context is None
    assert issue_codes(result) == {"route_not_supported"}


def test_unknown_and_ambiguous_names_are_visible_instead_of_guessed(reads):
    unknown = reads.resolve_intent(intent("Imaginary Summit"))
    ambiguous = reads.resolve_intent(intent("Camp"))

    assert unknown.state is IntentResolutionState.UNKNOWN
    assert issue_codes(unknown) == {"objective_unknown"}
    assert ambiguous.state is IntentResolutionState.AMBIGUOUS
    assert issue_codes(ambiguous) == {"objective_ambiguous"}
