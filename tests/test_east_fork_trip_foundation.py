from datetime import date
import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.planning import PlanningOutcomeState
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.requirements import CoverageStatus
from wayproof.schema import (
    ActivityContext, ChangeSetStatus, Coverage, Fulfillment, PartyContext,
    TripIntent,
)


ROOT = Path(__file__).resolve().parents[1]


def east_fork_intent():
    return TripIntent(
        ("East Fork Campground Site 126",), date(2026, 9, 30),
        party=PartyContext(("traveler-1", "traveler-2")),
        activities=ActivityContext(("camping",), {"overnight": True}),
    )


def by_id(records, collection, identifier):
    return {getattr(item, identifier): item for item in getattr(records, collection)}


def test_complete_public_site_profile_and_private_reservation_boundary():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")
    profile = claims["claim-east-fork-site-126-profile"].value

    assert profile["campsite_id"] == "62213"
    assert profile["site"] == "126"
    assert profile["loop"] == "EAST"
    assert profile["listed_capacity"] == 6
    assert profile["latitude"] == 37.4890270000001
    assert profile["longitude"] == -118.719946
    assert profile["details"] == [
        "15 ft site will fit small RV or trailer",
        "Site is next to restroom and water spigot",
    ]
    canonical_text = "\n".join(
        path.read_text() for path in (ROOT / "canonical" / "v0").rglob("*.json")
    )
    assert "Jenna" not in canonical_text
    assert "reservation number" not in canonical_text.casefold()


def test_conflicting_public_fields_are_preserved_as_gaps():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")
    gaps = by_id(records, "gaps", "gap_id")

    times = claims["claim-east-fork-site-126-arrival-departure"].value
    assert times["checkout_site_details"] == "11:00"
    assert times["checkout_attribute"] == "13:00"
    vehicles = claims["claim-east-fork-site-126-vehicle-fields"].value
    assert vehicles["maximum_vehicles_site_details"] == 1
    assert vehicles["maximum_vehicles_attribute"] == 2
    assert "claim-east-fork-site-126-vehicle-fields" in gaps[
        "gap-east-fork-site-126-vehicle-conflict"
    ].related_ids
    assert claims["claim-east-fork-published-elevation-recreation"].value == 8900
    assert claims["claim-east-fork-published-elevation-usfs"].value == 9000


def test_private_runtime_fulfillment_satisfies_reservation_requirement():
    reads = CanonicalReadService(ROOT)
    intent = east_fork_intent()
    without = reads.plan(intent)
    assessment = next(
        item for item in without.readiness.evaluation.requirements
        if item.requirement.requirement_id == "requirement-east-fork-site-126-reservation"
    )
    assert assessment.status is CoverageStatus.MISSING

    fulfillment = Fulfillment(
        "private-east-fork-booking", "requirement-east-fork-site-126-reservation",
        "private_reservation_confirmation", (), Coverage(
            participant_ids=("traveler-1", "traveler-2"),
            stage_ids=("objective-1",),
            starts_on=date(2026, 9, 30), ends_on=date(2026, 10, 4),
        ),
    )
    planned = reads.plan(intent, (fulfillment,))
    assessment = next(
        item for item in planned.readiness.evaluation.requirements
        if item.requirement.requirement_id == "requirement-east-fork-site-126-reservation"
    )
    assert assessment.status is CoverageStatus.COMPLETE
    # Live inventory and current operations intentionally keep the overall plan partial.
    assert planned.state is PlanningOutcomeState.PARTIAL


def test_site_objective_projects_parent_campground_inputs():
    reads = CanonicalReadService(ROOT)
    plan = reads.plan(east_fork_intent(), as_of_date=date(2026, 9, 23))
    predicates = {item.predicate for item in plan.planning_inputs.inputs}

    assert "recreation_gov_site_profile" in predicates
    assert "site_inventory" in predicates
    assert "fees" in predicates
    assert "reservation_window" in predicates


def test_trip_recheck_exposes_dated_status_and_unknowns():
    reads = CanonicalReadService(ROOT)
    resolution = reads.resolve_intent(east_fork_intent())
    result = reads.pretrip_recheck(
        resolution.context, "result-east-fork-pretrip-recheck"
    )
    items = {item.input_id: item for item in result.items}

    assert result.state is RecheckState.REQUIRED
    assert items["claim-east-fork-operating-status-20260923"].answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    assert items["claim-east-fork-fire-restrictions-2026"].answerability is RecheckAnswerability.ANSWERED
    assert items["gap-east-fork-trip-date-operations"].answerability is RecheckAnswerability.UNKNOWN


def test_generated_site_contains_east_fork_campground_and_site(generated_site):
    tmp_path, _ = generated_site
    camping = json.loads((tmp_path / "camping" / "index.json").read_text())
    ids = {item["entity_id"] for item in camping["entities"]}
    assert "campground-east-fork-inyo" in ids
    assert "campsite-east-fork-126" in ids
    page = tmp_path / "knowledge" / "campsite-east-fork-126" / "index.html"
    assert page.exists()
    assert "Site is next to restroom and water spigot" in page.read_text()


def test_changeset_is_validated_and_exact():
    change = load_changeset(
        ROOT / "changesets" / "v0" / "wp-20260923-east-fork-trip-foundation.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 78
    assert len({item.path for item in change.operations}) == 78
