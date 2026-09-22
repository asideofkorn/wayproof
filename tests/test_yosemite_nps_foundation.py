"""Official NPS evidence establishes a usable Yosemite planning foundation."""

from datetime import date
import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.requirements import (Applicability, CoverageStatus,
                                   evaluate_requirements)
from wayproof.schema import (ActivityContext, ChangeSetStatus, PartyContext,
                             PlanningContext, TripStage)


ROOT = Path(__file__).resolve().parents[1]


def records_by_id(records, collection, identifier):
    return {getattr(item, identifier): item for item in getattr(records, collection)}


def yosemite_overnight_context():
    return PlanningContext(
        trip_date=date(2026, 9, 30),
        objectives=(),
        stages=(TripStage(
            "yosemite-wilderness-stage", 1, "overnight",
            ("scope-yosemite-national-park", "scope-yosemite-wilderness"),
        ),),
        party=PartyContext(("alice", "bob")),
        activities=ActivityContext(("hiking",), {"overnight": True}),
    )


def test_yosemite_park_identity_and_official_sources_load():
    records = load_canonical(ROOT)
    entities = records_by_id(records, "entities", "entity_id")
    sources = records_by_id(records, "sources", "source_id")

    assert entities["park-yosemite-national-park"].kind == "national_park"
    assert entities["land-yosemite-wilderness"].kind == "wilderness"
    assert sources["source-nps-yosemite-plan"].locator == (
        "https://www.nps.gov/yose/planyourvisit/index.htm"
    )
    assert all(source.publisher == "National Park Service"
               for source_id, source in sources.items()
               if source_id.startswith("source-nps-yosemite-"))


def test_2026_entry_policy_is_temporally_bounded_and_cited():
    records = load_canonical(ROOT)
    claims = records_by_id(records, "claims", "claim_id")
    claim = claims["claim-yosemite-entry-reservation-2026"]

    assert claim.value is False
    assert claim.temporal_scope.starts_on.isoformat() == "2026-01-01"
    assert claim.temporal_scope.ends_on.isoformat() == "2026-12-31"
    assert claim.evidence_ids == ("evidence-yosemite-entry-reservation-2026",)


def test_2026_fees_preserve_the_party_dependent_nonresident_charge():
    claims = records_by_id(load_canonical(ROOT), "claims", "claim_id")
    claim = claims["claim-yosemite-nonresident-entrance-fee-2026"]

    assert claim.value == {
        "additional_per_person_usd": 100,
        "applies_to": "non-US residents age 16 and older",
        "exceptions": ["Annual Pass", "America the Beautiful Pass"],
    }
    assert claim.temporal_scope.starts_on == date(2026, 1, 1)
    assert claim.temporal_scope.ends_on == date(2026, 12, 31)


def test_approximate_park_area_does_not_become_exact():
    claims = records_by_id(load_canonical(ROOT), "claims", "claim_id")
    assert claims["claim-yosemite-park-area"].value == {
        "approximate": True,
        "square_miles": 1200,
    }


def test_wilderness_requirements_remain_distinct_and_actionable():
    records = load_canonical(ROOT)
    claims = records_by_id(records, "claims", "claim_id")
    rules = records_by_id(records, "rules", "rule_id")
    requirements = records_by_id(records, "requirements", "requirement_id")

    assert claims["claim-yosemite-wilderness-permit"].value is True
    assert claims["claim-yosemite-wilderness-group-limit"].value == {
        "on_trail": 15,
        "cross_country_over_quarter_mile": 8,
    }
    assert rules["rule-yosemite-wilderness-bear-canister"].claim_id == (
        "claim-yosemite-wilderness-food-storage"
    )
    assert requirements["requirement-yosemite-overnight-wilderness-permit"].rule_id == (
        "rule-yosemite-overnight-wilderness-permit"
    )
    assert requirements["requirement-yosemite-wilderness-bear-canister"].rule_id == (
        "rule-yosemite-wilderness-bear-canister"
    )
    assert claims["claim-yosemite-wilderness-permit-identity-constraints"].value == {
        "limited_to": ["trip leader", "entry trailhead", "dates", "number of people"]
    }


def test_normal_overnight_hiking_context_activates_wilderness_requirements():
    records = load_canonical(ROOT)
    selected = {
        "rule-yosemite-overnight-wilderness-permit",
        "rule-yosemite-wilderness-bear-canister",
    }
    result = evaluate_requirements(
        tuple(rule for rule in records.rules if rule.rule_id in selected),
        yosemite_overnight_context(),
    )

    assert {
        item.rule_id for item in result.rule_assessments
        if item.applicability is Applicability.APPLIES
    } == selected
    assert {
        item.requirement.requirement_id for item in result.requirements
        if item.status is CoverageStatus.MISSING
    } == {
        "requirement-yosemite-overnight-wilderness-permit",
        "requirement-yosemite-wilderness-bear-canister",
    }


def test_access_relationships_are_explicitly_evidenced():
    records = load_canonical(ROOT)
    relationships = records_by_id(records, "relationships", "relationship_id")
    entrance_ids = {
        "entrance-yosemite-south",
        "entrance-yosemite-arch-rock",
        "entrance-yosemite-big-oak-flat",
        "entrance-yosemite-hetch-hetchy",
        "entrance-yosemite-tioga-pass",
    }

    access = [item for item in relationships.values()
              if item.object_id == "park-yosemite-national-park"
              and item.predicate == "accesses"]
    assert {item.subject_id for item in access} == entrance_ids
    assert all(item.evidence_ids for item in access)


def test_dynamic_status_and_unmodeled_routes_stay_unknown():
    records = load_canonical(ROOT)
    gaps = records_by_id(records, "gaps", "gap_id")

    assert "dynamic" in gaps["gap-yosemite-current-conditions"].reason.lower()
    assert "does not infer" in gaps["gap-yosemite-specific-route-topology"].reason.lower()
    assert "live inventory" in gaps["gap-yosemite-campground-availability"].reason.lower()


def test_dynamic_status_projects_through_the_consumer_recheck_service():
    result = CanonicalReadService(ROOT).pretrip_recheck(
        yosemite_overnight_context(), "result-yosemite-pretrip-recheck"
    )
    items = {item.input_id: item for item in result.items}

    assert result.state is RecheckState.REQUIRED
    assert items["claim-yosemite-current-conditions-recheck"].answerability is (
        RecheckAnswerability.NEEDS_CURRENT_CHECK
    )
    assert items["claim-yosemite-current-conditions-recheck"].source_ids == (
        "source-nps-yosemite-conditions",
    )
    assert items["gap-yosemite-current-conditions"].answerability is (
        RecheckAnswerability.UNKNOWN
    )


def test_yosemite_park_and_camping_collection_are_generated(tmp_path):
    from scripts import build_site

    build_site.build(tmp_path)
    parks = json.loads((tmp_path / "parks" / "index.json").read_text())
    camping = json.loads((tmp_path / "camping" / "index.json").read_text())

    assert "park-yosemite-national-park" in {
        item["entity_id"] for item in parks["entities"]
    }
    assert "campgrounds-yosemite-developed" in {
        item["entity_id"] for item in camping["entities"]
    }
    assert (tmp_path / "knowledge" / "park-yosemite-national-park" /
            "index.html").exists()


def test_yosemite_changeset_is_validated_and_bounded():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260922-yosemite-nps-foundation.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 87
    assert all(operation.path.startswith("canonical/v0/")
               for operation in change.operations)
