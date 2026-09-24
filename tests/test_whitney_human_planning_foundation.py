"""Mount Whitney publishes direct human-planning facts without hiding conflict."""

from datetime import date
import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.schema import ActivityContext, ChangeSetStatus, PlanningContext, TripStage


ROOT = Path(__file__).resolve().parents[1]


def by_id(records, collection, identifier):
    return {getattr(item, identifier): item for item in getattr(records, collection)}


def test_whitney_peak_has_direct_identity_and_preserved_elevation_conflict():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")
    gaps = by_id(records, "gaps", "gap_id")

    identity = claims["claim-whitney-geographic-identity"].value
    assert "contiguous United States" in identity["highest_point_of"]
    assert identity["county_boundary"] == ["Inyo County", "Tulare County"]
    assert claims["claim-whitney-nps-elevation"].value["feet"] == 14505
    assert claims["claim-whitney-usgs-elevation"].value["feet"] == 14494
    assert claims["claim-whitney-peakbagger-measurement"].value["feet"] == 14500.7
    assert "different elevations" in gaps["gap-whitney-published-elevation-conflict"].reason


def test_whitney_approaches_and_community_source_limits_are_explicit():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")
    relationships = by_id(records, "relationships", "relationship_id")

    assert claims["claim-whitney-east-approach"].value["one_way_miles"] == 10.7
    assert claims["claim-whitney-west-approach"].value["approximate_one_way_miles"] == 60
    catalog = claims["claim-whitney-community-route-catalog"].value
    assert catalog["planning_use"] == "route discovery only"
    assert catalog["operational_guidance_authoritative"] is False
    assert relationships["relationship-mountaineers-uses-north-fork"].object_id == "route-north-fork-lone-pine"


def test_whitney_conditions_project_to_peak_context():
    context = PlanningContext(
        trip_date=date(2026, 10, 1), objectives=(),
        stages=(TripStage("whitney", 1, "summit", ("scope-peak-mount-whitney",)),),
        activities=ActivityContext(("hiking",), {}),
    )
    result = CanonicalReadService(ROOT).pretrip_recheck(context, "result-whitney-pretrip-recheck")
    items = {item.input_id: item for item in result.items}
    assert result.state is RecheckState.REQUIRED
    assert items["claim-whitney-current-conditions-recheck"].answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    assert items["claim-whitney-current-conditions-recheck"].source_ids == ("source-nps-seki-trail-conditions",)
    assert items["gap-whitney-current-conditions"].answerability is RecheckAnswerability.UNKNOWN


def test_whitney_entities_publish_to_generic_directories_and_details(generated_site):
    tmp_path, _ = generated_site
    peaks = json.loads((tmp_path / "peaks" / "index.json").read_text())
    parks = json.loads((tmp_path / "parks" / "index.json").read_text())
    trails = json.loads((tmp_path / "trails" / "index.json").read_text())
    assert "peak-mount-whitney" in {item["entity_id"] for item in peaks["entities"]}
    assert "park-sequoia-national-park" in {item["entity_id"] for item in parks["entities"]}
    assert "route-high-sierra-trail" in {item["entity_id"] for item in trails["entities"]}
    assert (tmp_path / "knowledge" / "peak-mount-whitney" / "index.html").exists()


def test_whitney_enrichment_changeset_is_single_validated_batch():
    change = load_changeset(ROOT / "changesets/v0/wp-20260923-whitney-human-planning-foundation.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert all(operation.path.startswith("canonical/v0/") for operation in change.operations)
