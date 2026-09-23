"""Lassen destinations expose sourced route choices without invented segments."""

from datetime import date
import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.intent import IntentResolutionState
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.schema import ChangeSetStatus, PlanningContext, TripIntent, TripStage


ROOT = Path(__file__).resolve().parents[1]


def by_id(records, collection, field):
    return {getattr(item, field): item for item in getattr(records, collection)}


def test_major_destinations_routes_and_trailheads_are_durable_entities():
    records = load_canonical(ROOT)
    entities = by_id(records, "entities", "entity_id")

    assert entities["peak-lassen-peak"].kind == "peak"
    assert entities["peak-cinder-cone"].kind == "peak"
    assert entities["hydrothermal-area-bumpass-hell"].kind == "hydrothermal_area"
    assert entities["waterbody-boiling-springs-lake"].kind == "waterbody"
    assert entities["route-terminal-geyser-trail"].kind == "route"
    assert entities["trailhead-warner-valley"].kind == "trailhead"


def test_every_published_route_has_an_evidenced_objective_and_start():
    records = load_canonical(ROOT)
    relationships = records.relationships
    route_ids = {
        "route-lassen-peak-trail", "route-brokeoff-mountain-trail",
        "route-cinder-cone-trail", "route-bumpass-hell-trail",
        "route-devils-kitchen-trail", "route-boiling-springs-lake-trail",
        "route-terminal-geyser-trail",
    }

    for route_id in route_ids:
        approaches = [item for item in relationships
                      if item.object_id == route_id
                      and item.predicate == "approached_via"]
        starts = [item for item in relationships
                  if item.subject_id == route_id and item.predicate == "starts_at"]
        assert len(approaches) == 1
        assert len(starts) == 1
        assert approaches[0].evidence_ids
        assert starts[0].evidence_ids


def test_profiles_preserve_round_trip_precision_while_topology_gap_narrows():
    records = load_canonical(ROOT)
    claims = by_id(records, "claims", "claim_id")
    gaps = by_id(records, "gaps", "gap_id")

    assert claims["claim-lassen-peak-trail-profile"].value["round_trip_miles"] == 5
    assert claims["claim-cinder-cone-trail-profile"].value["elevation_change_ft"] == 846
    assert claims["claim-bumpass-hell-trail-profile"].value["typical_season"] == (
        "approximately late July through October"
    )
    assert claims["claim-terminal-geyser-trail-profile"].value["round_trip_time_hours"] == (
        "2.5 to 3"
    )
    reason = gaps["gap-lassen-specific-route-topology"].reason
    assert "Lassen Peak and Brokeoff Mountain" in reason
    assert "branched-route reconciliation" not in reason
    assert "Bumpass Hell, Cinder Cone" in reason


def test_peak_and_non_peak_objectives_resolve_their_sourced_route_and_entry():
    reads = CanonicalReadService(ROOT)
    peak = reads.resolve_intent(TripIntent(("Lassen Peak",), date(2027, 8, 12)))
    hydrothermal = reads.resolve_intent(TripIntent(("Bumpass Hell",), date(2027, 8, 12)))

    assert peak.state is IntentResolutionState.PARTIAL
    assert peak.route.entity_id == "route-lassen-peak-trail"
    assert peak.entry.entity_id == "trailhead-lassen-peak"
    assert {item.code for item in peak.issues} == {"exit_unknown"}
    assert hydrothermal.state is IntentResolutionState.PARTIAL
    assert hydrothermal.route.entity_id == "route-bumpass-hell-trail"
    assert hydrothermal.entry.entity_id == "trailhead-bumpass-hell"
    assert hydrothermal.context.objectives[0].kind == "visit"


def test_route_conditions_are_discoverable_through_pretrip_recheck():
    context = PlanningContext(
        date(2027, 8, 12), (),
        (TripStage("bumpass", 1, "traverse", ("scope-route-bumpass-hell-trail",)),),
    )
    result = CanonicalReadService(ROOT).pretrip_recheck(
        context, "result-lassen-pretrip-recheck"
    )
    items = {item.input_id: item for item in result.items}

    assert result.state is RecheckState.REQUIRED
    assert items["claim-lassen-trail-conditions-recheck"].answerability is (
        RecheckAnswerability.NEEDS_CURRENT_CHECK
    )
    assert items["claim-lassen-trail-conditions-recheck"].source_ids == (
        "source-nps-lassen-trail-conditions",
    )
    assert items["gap-lassen-specific-route-topology"].answerability is (
        RecheckAnswerability.UNKNOWN
    )


def test_generated_site_discovers_lassen_peaks_routes_and_destination_pages(tmp_path):
    from scripts import build_site

    build_site.build(tmp_path)
    peaks = json.loads((tmp_path / "peaks" / "index.json").read_text())
    trails = json.loads((tmp_path / "trails" / "index.json").read_text())

    assert "peak-lassen-peak" in {item["entity_id"] for item in peaks["entities"]}
    assert "route-bumpass-hell-trail" in {
        item["entity_id"] for item in trails["entities"]
    }
    for entity_id in (
        "peak-lassen-peak", "route-lassen-peak-trail",
        "hydrothermal-area-bumpass-hell", "waterbody-boiling-springs-lake",
    ):
        assert (tmp_path / "knowledge" / entity_id / "index.html").exists()
        assert (tmp_path / "knowledge" / f"{entity_id}.json").exists()


def test_lassen_route_depth_changeset_is_one_validated_batch():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260923-lassen-destinations-route-depth.json"
    )

    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD", "REPLACE"}
    assert all(item.path.startswith("canonical/v0/") for item in change.operations)
