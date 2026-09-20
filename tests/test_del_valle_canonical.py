"""Regression checks for the first published Schema v0 knowledge slice."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def records():
    return load_canonical(ROOT)


def test_del_valle_publication_has_complete_source_lineage():
    snapshot = records()
    source = next(item for item in snapshot.sources
                  if item.source_id == "source-reserveamerica-del-valle-overview-110003")
    assert source.locator == (
        "https://www.reserveamerica.com/explore/del-valle/EB/110003/overview")
    assert all(item.source_id == source.source_id for item in snapshot.observations)
    assert all(item.evidence_ids for item in snapshot.claims)


def test_del_valle_inventory_disagreement_remains_visible():
    snapshot = records()
    inventory = next(item for item in snapshot.claims
                     if item.claim_id == "claim-del-valle-campground-inventory")
    assert inventory.value == {
        "cabins": 5,
        "drive_up_tent": 124,
        "rv_full_hookup": 21,
        "total": 150,
    }
    gap = next(item for item in snapshot.gaps
               if item.gap_id == "gap-del-valle-inventory-count")
    assert "150 or 155" in gap.question


def test_uncorroborated_ohlone_statement_is_not_a_current_rule():
    snapshot = records()
    statement = "claim-del-valle-ohlone-permit-page-statement"
    assert any(item.claim_id == statement for item in snapshot.claims)
    assert not any(item.claim_id == statement for item in snapshot.rules)
    assert any(statement in item.related_ids for item in snapshot.gaps)


def test_volatile_conditions_require_pretrip_recheck():
    result = next(item for item in records().derived_results
                  if item.result_id == "result-del-valle-pretrip-recheck")
    assert result.value["required"] is True
    assert set(result.value["topics"]) == {
        "fire_danger", "blue_green_algae", "flood_closure",
        "boat_inspection_procedure",
    }


def test_del_valle_changeset_is_a_validated_public_manifest():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-del-valle-reserveamerica-foundation.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 105
    assert len({item.path for item in change.operations}) == 105
