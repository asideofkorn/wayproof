"""Bounded operational evaluation never manufactures a definitive answer."""

from datetime import date

from wayproof.operational import (DeadlineStatus, OperationalState,
                                  evaluate_operational_inputs)
from wayproof.planning_inputs import (PlanningInput, PlanningInputAnswerability,
                                      PlanningInputCategory,
                                      PlanningInputProjection)


def item(identifier, category, value, *, predicate="test"):
    return PlanningInput(
        identifier, category, PlanningInputAnswerability.ANSWERED,
        "subject", predicate, value, ("evidence",),
    )


def projection(*items):
    return PlanningInputProjection(items, {})


def test_one_unambiguous_cost_can_be_totaled():
    result = evaluate_operational_inputs(projection(item(
        "parking", PlanningInputCategory.COST, 10,
        predicate="published_swimming_page_parking_fee_usd",
    )), date(2027, 8, 12))

    assert result.costs.state is OperationalState.ANSWERED
    assert result.costs.total_usd == 10


def test_alternative_fee_fields_expose_components_but_not_a_false_total():
    result = evaluate_operational_inputs(projection(item(
        "entry", PlanningInputCategory.COST,
        {"vehicle_parking_usd": 5, "bus_parking_usd": 25},
        predicate="published_entry_fees",
    )), date(2027, 8, 12))

    assert result.costs.state is OperationalState.PARTIAL
    assert {component.amount_usd for component in result.costs.components} == {5, 25}
    assert result.costs.total_usd is None
    assert result.costs.unresolved_input_ids == ("entry",)


def test_structured_reservation_window_has_deterministic_status():
    inputs = projection(item(
        "booking", PlanningInputCategory.DEADLINE,
        {"maximum_advance_weeks": 12, "minimum_advance_hours": 48},
        predicate="reservation_window",
    ))
    before = evaluate_operational_inputs(
        inputs, date(2027, 8, 12), date(2027, 5, 1),
    ).deadlines[0]
    open_now = evaluate_operational_inputs(
        inputs, date(2027, 8, 12), date(2027, 6, 1),
    ).deadlines[0]
    late = evaluate_operational_inputs(
        inputs, date(2027, 8, 12), date(2027, 8, 11),
    ).deadlines[0]

    assert before.status is DeadlineStatus.NOT_OPEN
    assert open_now.status is DeadlineStatus.ACTIONABLE
    assert late.status is DeadlineStatus.EXPIRED
    assert open_now.opens_on == date(2027, 5, 20)
    assert open_now.closes_on == date(2027, 8, 10)


def test_deadline_status_requires_explicit_as_of_date():
    result = evaluate_operational_inputs(projection(item(
        "booking", PlanningInputCategory.DEADLINE,
        {"minimum_advance_days": 2}, predicate="overnight_camping_reservation",
    )), date(2027, 8, 12))

    assert result.deadlines[0].status is DeadlineStatus.UNKNOWN
    assert result.deadlines[0].closes_on == date(2027, 8, 10)


def test_published_inventory_is_not_live_availability():
    result = evaluate_operational_inputs(projection(item(
        "sites", PlanningInputCategory.INVENTORY, {"total": 150},
        predicate="site_inventory",
    )), date(2027, 8, 12))

    assert result.inventory[0].state is OperationalState.NEEDS_CURRENT_CHECK


def test_effective_explicit_closed_status_blocks_but_open_ended_input_rechecks():
    closed = item(
        "trail", PlanningInputCategory.CLOSURE,
        {"status": "closed"}, predicate="trail_closure",
    )
    result = evaluate_operational_inputs(projection(closed), date(2027, 8, 12))
    assert result.closures[0].state is OperationalState.BLOCKED
    assert result.state is OperationalState.BLOCKED

    volatile = PlanningInput(
        "trail", PlanningInputCategory.CLOSURE,
        PlanningInputAnswerability.NEEDS_CURRENT_CHECK,
        "subject", "trail_closure", {"status": "closed"}, ("evidence",),
    )
    result = evaluate_operational_inputs(projection(volatile), date(2027, 8, 12))
    assert result.closures[0].state is OperationalState.NEEDS_CURRENT_CHECK
    assert result.state is OperationalState.NEEDS_CURRENT_CHECK
