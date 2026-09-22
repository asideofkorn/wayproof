"""Official NPS evidence establishes a bounded Yosemite planning foundation."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def records_by_id(records, collection, identifier):
    return {getattr(item, identifier): item for item in getattr(records, collection)}


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
    assert rules["rule-yosemite-wilderness-food-storage"].claim_id == (
        "claim-yosemite-wilderness-food-storage"
    )
    assert requirements["requirement-yosemite-overnight-wilderness-permit"].rule_id == (
        "rule-yosemite-overnight-wilderness-permit"
    )
    assert requirements["requirement-yosemite-wilderness-bear-canister"].rule_id == (
        "rule-yosemite-wilderness-food-storage"
    )


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


def test_yosemite_changeset_is_validated_and_bounded():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260922-yosemite-nps-foundation.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 76
    assert all(operation.path.startswith("canonical/v0/")
               for operation in change.operations)
