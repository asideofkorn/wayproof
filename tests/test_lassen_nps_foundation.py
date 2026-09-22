"""Official first-party evidence establishes a bounded Lassen planning foundation."""

from datetime import date
import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.requirements import Applicability, CoverageStatus, evaluate_requirements
from wayproof.schema import (
    ActivityContext, ChangeSetStatus, PartyContext, PlanningContext, TripIntent,
    TripStage,
)


ROOT = Path(__file__).resolve().parents[1]


def records_by_id(records, collection, identifier):
    return {getattr(item, identifier): item for item in getattr(records, collection)}


def lassen_overnight_context():
    return PlanningContext(
        trip_date=date(2026, 9, 30),
        objectives=(),
        stages=(TripStage(
            "lassen-wilderness-overnight", 1, "overnight",
            ("scope-lassen-national-park", "scope-lassen-wilderness"),
        ),),
        party=PartyContext(("alice", "bob")),
        activities=ActivityContext(("hiking", "camping"), {"overnight": True}),
    )


def lassen_campground_context():
    return PlanningContext(
        trip_date=date(2026, 9, 30),
        objectives=(),
        stages=(TripStage(
            "lassen-developed-campground", 1, "overnight",
            ("scope-lassen-national-park", "scope-lassen-developed-campgrounds"),
        ),),
        party=PartyContext(("alice", "bob")),
        activities=ActivityContext(("camping",), {"overnight": True}),
    )


def test_lassen_identity_and_first_party_sources_load():
    records = load_canonical(ROOT)
    entities = records_by_id(records, "entities", "entity_id")
    sources = records_by_id(records, "sources", "source_id")

    assert entities["park-lassen-volcanic-national-park"].kind == "national_park"
    assert entities["land-lassen-volcanic-wilderness"].kind == "wilderness"
    assert entities["campgrounds-lassen-developed"].kind == "campground_collection"
    assert sources["source-nps-lassen-directions"].locator.endswith("/directions.htm")
    assert sources["source-recreationgov-lassen-wilderness"].publisher == "Recreation.gov"


def test_access_edges_are_explicit_and_evidenced_without_invented_traversal():
    records = load_canonical(ROOT)
    relationships = records_by_id(records, "relationships", "relationship_id")
    gaps = records_by_id(records, "gaps", "gap_id")
    access = [item for item in relationships.values()
              if item.object_id == "park-lassen-volcanic-national-park"
              and item.predicate == "accesses"]

    assert {item.subject_id for item in access} == {
        "entrance-lassen-northwest", "entrance-lassen-southwest",
        "access-lassen-butte-lake", "access-lassen-juniper-lake",
        "access-lassen-warner-valley",
    }
    assert all(item.evidence_ids for item in access)
    assert "does not infer route membership" in (
        gaps["gap-lassen-specific-route-topology"].reason
    )


def test_campground_collection_preserves_membership_and_dynamic_limits():
    records = load_canonical(ROOT)
    claims = records_by_id(records, "claims", "claim_id")
    gaps = records_by_id(records, "gaps", "gap_id")
    published = claims["claim-lassen-campground-collection"].value

    assert len(published) == 11
    assert {item["name"] for item in published} >= {
        "Manzanita Lake Campground", "Southwest Walk-In Campground",
        "Butte Lake Campground", "Juniper Lake Campground",
        "Warner Valley Campground",
    }
    assert "live inventory" in gaps["gap-lassen-campground-live-operations"].reason
    assert "intentionally deferred" in gaps["gap-lassen-campground-site-details"].reason


def test_campground_reservation_conflict_preserves_warner_valley_uncertainty():
    records = load_canonical(ROOT)
    claims = records_by_id(records, "claims", "claim_id")
    gaps = records_by_id(records, "gaps", "gap_id")
    policy = claims["claim-lassen-campground-reservations"].value

    assert policy["required_except"] == [
        "Juniper Lake", "Southwest Walk-In", "Warner Valley",
    ]
    assert "summary omits Warner Valley" in policy["source_page_conflict"]
    assert "conflicts internally" in (
        gaps["gap-lassen-campground-reservation-policy-conflict"].reason
    )


def test_wilderness_permit_fees_and_food_storage_are_distinct_claims():
    claims = records_by_id(load_canonical(ROOT), "claims", "claim_id")

    assert claims["claim-lassen-wilderness-permit"].value is True
    assert claims["claim-lassen-wilderness-permit-process"].value == {
        "channel": "Recreation.gov only",
        "maximum_advance_days": 90,
        "quota": False,
        "physical_pickup_required": False,
        "confirmation_email_is_permit": True,
    }
    assert claims["claim-lassen-wilderness-permit-fees"].value == {
        "administration_usd_per_permit": 6,
        "trip_usd_per_person_age_16_plus": 5,
        "entrance_fee_separate": True,
    }
    food = claims["claim-lassen-wilderness-food-storage"]
    assert food.value["hanging_permitted"] is False
    assert food.temporal_scope.starts_on == date(2026, 4, 16)
    assert food.temporal_scope.ends_on == date(2026, 11, 30)


def test_representative_overnight_intent_rules_join_exact_requirements():
    records = load_canonical(ROOT)
    selected = {
        "rule-lassen-overnight-wilderness-permit",
        "rule-lassen-wilderness-bear-canister",
    }
    result = evaluate_requirements(
        tuple(rule for rule in records.rules if rule.rule_id in selected),
        lassen_overnight_context(),
    )

    assert {item.rule_id for item in result.rule_assessments
            if item.applicability is Applicability.APPLIES} == selected
    assert {item.requirement.requirement_id for item in result.requirements
            if item.status is CoverageStatus.MISSING} == {
        "requirement-lassen-overnight-wilderness-permit",
        "requirement-lassen-wilderness-bear-canister",
    }


def test_representative_named_intents_resolve_without_destination_special_cases():
    reads = CanonicalReadService(ROOT)
    visit = reads.resolve_intent(TripIntent(
        ("Lassen Volcanic National Park",), date(2026, 9, 30),
        activities=ActivityContext(("hiking",), {}),
    ))
    camp = reads.resolve_intent(TripIntent(
        ("Manzanita Lake Campground",), date(2026, 9, 30),
        activities=ActivityContext(("camping",), {"overnight": True}),
    ))

    assert visit.objectives[0].entity_id == "park-lassen-volcanic-national-park"
    assert camp.objectives[0].entity_id == "campground-lassen-manzanita-lake"


def test_dynamic_operating_topics_project_through_recheck_consumer():
    result = CanonicalReadService(ROOT).pretrip_recheck(
        lassen_overnight_context(), "result-lassen-pretrip-recheck"
    )
    items = {item.input_id: item for item in result.items}

    assert result.state is RecheckState.REQUIRED
    assert items["claim-lassen-current-conditions-recheck"].answerability is (
        RecheckAnswerability.NEEDS_CURRENT_CHECK
    )
    assert items["claim-lassen-current-conditions-recheck"].source_ids == (
        "source-nps-lassen-conditions",
    )
    assert items["gap-lassen-current-conditions"].answerability is (
        RecheckAnswerability.UNKNOWN
    )


def test_reservation_conflict_projects_for_campground_recheck_consumer():
    result = CanonicalReadService(ROOT).pretrip_recheck(
        lassen_campground_context(), "result-lassen-pretrip-recheck"
    )
    items = {item.input_id: item for item in result.items}

    assert items["claim-lassen-campground-reservations"].answerability is (
        RecheckAnswerability.NEEDS_CURRENT_CHECK
    )
    assert items["claim-lassen-campground-reservations"].source_ids == (
        "source-nps-lassen-camping",
    )
    assert items["gap-lassen-campground-reservation-policy-conflict"].answerability is (
        RecheckAnswerability.UNKNOWN
    )


def test_lassen_generated_navigation_and_detail_pages(tmp_path):
    from scripts import build_site

    build_site.build(tmp_path)
    parks = json.loads((tmp_path / "parks" / "index.json").read_text())
    camping = json.loads((tmp_path / "camping" / "index.json").read_text())

    assert "park-lassen-volcanic-national-park" in {
        item["entity_id"] for item in parks["entities"]
    }
    camping_ids = {item["entity_id"] for item in camping["entities"]}
    assert "campgrounds-lassen-developed" in camping_ids
    assert "campground-lassen-manzanita-lake" in camping_ids
    for entity_id in (
        "park-lassen-volcanic-national-park",
        "land-lassen-volcanic-wilderness",
        "campgrounds-lassen-developed",
        "campground-lassen-manzanita-lake",
    ):
        assert (tmp_path / "knowledge" / entity_id / "index.html").exists()
        assert (tmp_path / "knowledge" / f"{entity_id}.json").exists()


def test_lassen_changeset_is_validated_and_bounded():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260922-lassen-nps-foundation.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 103
    assert all(operation.path.startswith("canonical/v0/")
               for operation in change.operations)
