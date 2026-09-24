"""Rock Creek's principal routes are traversable, mapped, and permit-aware."""

from datetime import date
import hashlib
import json
from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability, RecheckState
from wayproof.requirements import Applicability, CoverageStatus
from wayproof.schema import (
    ActivityContext, ChangeSetStatus, Coverage, Fulfillment, PartyContext,
    PlanningContext, TripObjective, TripStage,
)
from wayproof.traversal import TraversalState, resolve_traversal


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = Path("geometry/v0/snapshots/usgs-rock-creek-principal-routes-20260923.geojson")
SNAPSHOT_HASH = "cbbaa853ee6d4ad8a8d995ab91270b7154a5fe3643ac1cb666d43f53c59b600a"
ROUTES = {
    "route-little-lakes-valley": ("trailhead-mosquito-flat", "route-node-little-lakes-south-junction", 3.60003589, 4),
    "route-mono-pass-rock-creek": ("trailhead-mosquito-flat", "pass-mono-rock-creek", 3.32465708, 5),
    "route-morgan-pass-rock-creek": ("trailhead-mosquito-flat", "pass-morgan-rock-creek", 5.48061415, 7),
    "route-tamarack-lakes-rock-creek": ("trailhead-tamarack-lakes-rock-creek", "waterbody-buck-lake-rock-creek", 5.19126423, 8),
    "route-hilton-lakes-rock-creek": ("trailhead-hilton-lakes-rock-creek", "waterbody-hilton-lakes-upper", 4.08534229, 8),
}


def context(overnight: bool = True):
    return PlanningContext(
        date(2026, 9, 30),
        (TripObjective("objective-1", "route-little-lakes-valley", "traverse"),),
        (TripStage("objective-1", 1, "traverse", (
            "scope-rock-creek-corridor", "scope-route-little-lakes-valley",
        )),),
        PartyContext(("traveler-1", "traveler-2")),
        ActivityContext(("hiking",), {"overnight": overnight}),
    )


def test_all_five_principal_routes_traverse_both_directions_with_known_distance():
    reads = CanonicalReadService(ROOT)
    for route_id, (entry_id, exit_id, distance, leg_count) in ROUTES.items():
        route = reads.entity(route_id)
        entry, exit_entity = reads.entity(entry_id), reads.entity(exit_id)
        outbound = resolve_traversal(reads, route, entry, exit_entity, date(2026, 9, 30))
        inbound = resolve_traversal(reads, route, exit_entity, entry, date(2026, 9, 30))

        assert outbound.state is TraversalState.COMPLETE
        assert outbound.distance_complete is True
        assert outbound.total_known_distance_miles == distance
        assert len(outbound.legs) == leg_count
        assert inbound.state is TraversalState.COMPLETE
        assert inbound.total_known_distance_miles == distance
        assert [item.segment_id for item in inbound.legs] == [
            item.segment_id for item in reversed(outbound.legs)
        ]


def test_reviewed_snapshot_is_bounded_and_every_route_projects_offline_geojson():
    content = (ROOT / SNAPSHOT).read_bytes()
    snapshot = json.loads(content)
    reads = CanonicalReadService(ROOT)

    assert hashlib.sha256(content).hexdigest() == SNAPSHOT_HASH
    assert len(snapshot["features"]) == 25
    assert {item["properties"]["source_originator"] for item in snapshot["features"]} == {
        "U.S. Forest Service"
    }
    for route_id, (entry_id, exit_id, distance, leg_count) in ROUTES.items():
        geometry = reads.route_geometry(route_id, date(2026, 9, 30))
        assert geometry["wayproof"]["entry_id"] == entry_id
        assert geometry["wayproof"]["exit_id"] == exit_id
        assert geometry["wayproof"]["distance_miles"] == distance
        assert geometry["wayproof"]["navigation_grade"] is False
        assert len(geometry["features"]) == leg_count


def test_little_lakes_context_is_visible_without_invented_lake_to_lake_cuts():
    records = load_canonical(ROOT)
    relationships = records.relationships
    gaps = {item.gap_id: item for item in records.gaps}
    accessible = {
        item.object_id for item in relationships
        if item.subject_id == "route-segment-rock-creek-little-lakes-main"
        and item.predicate == "provides_access_to"
    }

    assert accessible == {
        "waterbody-mack-lake-rock-creek", "waterbody-marsh-lake-rock-creek",
        "waterbody-heart-lake-rock-creek", "waterbody-box-lake-rock-creek",
        "waterbody-long-lake-rock-creek", "waterbody-chickenfoot-lake-rock-creek",
        "waterbody-gem-lakes-rock-creek",
    }
    assert "does not cut it at inferred positions" in gaps[
        "gap-rock-creek-little-lakes-intermediate-mileages"
    ].reason
    assert "do not share exact endpoints" in gaps[
        "gap-rock-creek-gem-chickenfoot-spur-connectors"
    ].reason


def test_overnight_permit_and_bear_container_apply_but_day_hike_does_not():
    reads = CanonicalReadService(ROOT)
    overnight = reads.requirements(context(True))
    applicable = {
        item.rule_id: item.applicability for item in overnight.rule_assessments
    }
    requirements = {
        item.requirement.requirement_id: item for item in overnight.requirements
    }

    assert applicable["rule-rock-creek-overnight-wilderness-permit"] is Applicability.APPLIES
    assert applicable["rule-little-lakes-bear-container"] is Applicability.APPLIES
    assert requirements["requirement-rock-creek-overnight-wilderness-permit"].status is CoverageStatus.MISSING
    assert requirements["requirement-little-lakes-bear-container"].status is CoverageStatus.MISSING

    day = reads.requirements(context(False))
    day_rules = {item.rule_id: item.applicability for item in day.rule_assessments}
    assert day_rules["rule-rock-creek-overnight-wilderness-permit"] is Applicability.DOES_NOT_APPLY
    assert day_rules["rule-little-lakes-bear-container"] is Applicability.DOES_NOT_APPLY


def test_private_fulfillments_join_exact_runtime_requirement_ids():
    reads = CanonicalReadService(ROOT)
    coverage = Coverage(
        participant_ids=("traveler-1", "traveler-2"), stage_ids=("objective-1",),
        starts_on=date(2026, 9, 30), ends_on=date(2026, 10, 4),
    )
    fulfilled = reads.requirements(context(True), (
        Fulfillment("private-inyo-permit", "requirement-rock-creek-overnight-wilderness-permit", "private_permit", (), coverage),
        Fulfillment("private-bear-container", "requirement-little-lakes-bear-container", "equipment_confirmation", (), coverage),
    ))
    assert all(item.status is CoverageStatus.COMPLETE for item in fulfilled.requirements
               if item.requirement.rule_id.startswith(("rule-rock-creek", "rule-little-lakes")))


def test_pretrip_recheck_returns_current_access_gap_and_official_sources():
    reads = CanonicalReadService(ROOT)
    result = reads.pretrip_recheck(context(True), "result-rock-creek-pretrip-recheck")
    items = {item.input_id: item for item in result.items}

    assert result.state is RecheckState.REQUIRED
    current = items["claim-rock-creek-routes-current-conditions-recheck"]
    assert current.answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    assert current.source_ids == ("source-usfs-inyo-alerts",)
    assert items["gap-rock-creek-live-access-and-trailhead-operations"].answerability is RecheckAnswerability.UNKNOWN


def test_generated_site_has_corridor_entities_and_route_maps(tmp_path):
    from scripts import build_site

    build_site.build(tmp_path)
    routes = json.loads((tmp_path / "trails" / "index.json").read_text())
    ids = {item["entity_id"] for item in routes["entities"]}
    assert ROUTES.keys() <= ids
    for route_id in ROUTES:
        assert (tmp_path / "knowledge" / route_id / "index.html").exists()
        assert (tmp_path / "geometry" / "routes" / f"{route_id}.geojson").exists()
    assert (tmp_path / "knowledge" / "trailhead-mosquito-flat" / "index.html").exists()


def test_one_validated_changeset_accounts_for_the_batch():
    change = load_changeset(
        ROOT / "changesets" / "v0" /
        "wp-20260923-rock-creek-corridor-principal-routes.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action.value for item in change.operations} == {"ADD"}
