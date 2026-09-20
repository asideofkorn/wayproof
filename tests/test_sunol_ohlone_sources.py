"""Regression checks for the Sunol and ReserveAmerica Ohlone sources."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus

ROOT = Path(__file__).resolve().parents[1]


def records():
    return load_canonical(ROOT)


def claim(claim_id):
    return next(item for item in records().claims if item.claim_id == claim_id)


def test_sunol_sources_corroborate_existing_ohlone_policy():
    permit = claim("claim-ohlone-trail-permit-not-required-2026")
    reservation = claim("claim-ohlone-overnight-reservation")
    assert len(permit.evidence_ids) == 2
    assert len(reservation.evidence_ids) == 3
    assert reservation.value["minimum_advance_days"] == 2


def test_sunol_current_conditions_remain_recheckable():
    closure = claim("claim-sunol-shady-glen-trail-closed-20260920")
    fire = claim("claim-sunol-fire-policy-20260920")
    assert closure.value["status"] == "closed"
    assert str(closure.temporal_scope.starts_on) == "2026-09-20"
    assert fire.value["open_fires"] is False
    result = next(item for item in records().derived_results
                  if item.result_id == "result-del-valle-pretrip-recheck")
    assert "sunol_trail_and_fire_status" in result.value["topics"]


def test_sunol_and_ohlone_trip_constraints_are_explicit():
    snapshot = records()
    rules = {item.rule_id for item in snapshot.rules}
    assert claim("claim-sunol-drinking-water-unavailable").value is False
    assert claim("claim-ohlone-trail-maximum-consecutive-nights").value == 3
    assert claim("claim-ohlone-overnight-dogs-prohibited").value is False
    assert claim("claim-ohlone-overnight-alcohol-prohibited").value is False
    assert {
        "rule-sunol-bring-drinking-water",
        "rule-ohlone-maximum-three-consecutive-nights",
        "rule-ohlone-no-overnight-dogs",
        "rule-ohlone-no-alcohol",
        "rule-ohlone-backpack-stoves-only",
    } <= rules


def test_reserveamerica_facility_identity_and_lead_time_are_preserved():
    profile = claim("claim-reserveamerica-sunol-backpack-facility")
    assert profile.value["facility_id"] == "EB/110028"
    assert profile.value["minimum_advance_hours"] == 48
    assert profile.value["inventory_description"] == "limited backpack sites"


def test_sunol_changeset_is_validated_and_complete():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-sunol-ohlone-sources.json")
    assert change.status is ChangeSetStatus.VALIDATED
    counts = {action: sum(item.action.value == action
                          for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 47, "REPLACE": 3, "REMOVE": 0}
