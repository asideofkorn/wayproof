"""Pre-trip recheck behavior over Del Valle and Ohlone volatile claims."""

from datetime import date
from pathlib import Path

from wayproof.canonical_storage import load_canonical
from wayproof.recheck import (RecheckAnswerability, RecheckState,
                              evaluate_pretrip_recheck)
from wayproof.schema import PlanningContext, TripObjective, TripStage


ROOT = Path(__file__).resolve().parents[1]


def context(trip_date, *scopes):
    return PlanningContext(
        trip_date=trip_date,
        objectives=(TripObjective("visit", "park-del-valle-regional-park", "visit"),),
        stages=(TripStage("visit", 1, "visit", scopes),),
    )


def items_by_id(result):
    return {item.input_id: item for item in result.items}


def test_same_day_algae_claim_is_answered_but_live_alert_still_needs_check():
    result = evaluate_pretrip_recheck(
        load_canonical(ROOT),
        context(date(2026, 9, 20), "scope-del-valle-park", "scope-del-valle-east-beach"),
    )
    items = items_by_id(result)
    assert items["claim-del-valle-ebrpd-east-beach-algae"].answerability is (
        RecheckAnswerability.ANSWERED
    )
    assert items["claim-del-valle-volatile-alerts"].answerability is (
        RecheckAnswerability.NEEDS_CURRENT_CHECK
    )
    assert result.state is RecheckState.REQUIRED


def test_dated_condition_does_not_answer_a_future_trip():
    result = evaluate_pretrip_recheck(
        load_canonical(ROOT),
        context(date(2026, 9, 21), "scope-del-valle-park", "scope-del-valle-east-beach"),
    )
    item = items_by_id(result)["claim-del-valle-ebrpd-east-beach-algae"]
    assert item.answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    assert "does not establish" in item.explanation


def test_ohlone_water_report_is_history_not_a_permanent_current_fact():
    records = load_canonical(ROOT)
    same_day = evaluate_pretrip_recheck(
        records, context(date(2026, 9, 19), "scope-ohlone-wilderness-trail")
    )
    future = evaluate_pretrip_recheck(
        records, context(date(2026, 9, 25), "scope-ohlone-wilderness-trail")
    )
    assert items_by_id(same_day)[
        "claim-ohlone-water-availability-20260919"
    ].answerability is RecheckAnswerability.ANSWERED
    assert items_by_id(future)[
        "claim-ohlone-water-availability-20260919"
    ].answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK


def test_recheck_item_exposes_the_sources_to_check():
    result = evaluate_pretrip_recheck(
        load_canonical(ROOT),
        context(date(2026, 9, 21), "scope-del-valle-park"),
    )
    item = items_by_id(result)["claim-del-valle-volatile-alerts"]
    assert item.evidence_ids == ("evidence-del-valle-volatile-alerts",)
    assert item.source_ids == ("source-reserveamerica-del-valle-overview-110003",)


def test_linked_gap_stays_unknown_instead_of_becoming_a_negative_answer():
    result = evaluate_pretrip_recheck(
        load_canonical(ROOT),
        context(date(2026, 9, 21), "scope-del-valle-park"),
    )
    item = items_by_id(result)["gap-del-valle-current-algae-status"]
    assert item.answerability is RecheckAnswerability.UNKNOWN


def test_unrelated_trip_has_no_recheck_items():
    result = evaluate_pretrip_recheck(
        load_canonical(ROOT),
        context(date(2026, 9, 21), "scope-somewhere-else"),
    )
    assert result.state is RecheckState.NOT_APPLICABLE
    assert result.items == ()
