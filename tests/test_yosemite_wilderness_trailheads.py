"""Yosemite wilderness permit entries remain complete and source-bounded."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]
CHANGESET = "wp-20260925-yosemite-wilderness-trailheads"


def index(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def permit_entries(records):
    return {
        entity.entity_id: entity
        for entity in records.entities
        if entity.entity_id.startswith("permit-yosemite-entry-")
    }


def test_complete_2026_entry_matrix_preserves_quota_categories():
    records = load_canonical(ROOT)
    entries = permit_entries(records)
    claims = index(records, "claims", "claim_id")
    assert len(entries) == 66

    happy = claims[
        "claim-yosemite-entry-happy-isles-to-past-lyv-donohue-pass-eligible-quota-2026"
    ]
    assert happy.value == {"advance_lottery": 9, "week_ahead": 6, "total": 15}

    white_wolf = claims[
        "claim-yosemite-entry-white-wolf-to-pate-valley-quota-2026"
    ]
    assert white_wolf.value["total"] == 30

    winter = claims["claim-yosemite-entry-badger-pass-quota-2026"]
    assert winter.value == {"advance_lottery": 0, "week_ahead": 30, "total": 30}


def test_permit_scope_keeps_eligibility_first_night_and_cross_country_distinct():
    records = load_canonical(ROOT)
    claims = index(records, "claims", "claim_id")

    donohue = claims[
        "claim-yosemite-entry-lyell-canyon-donohue-pass-eligible-scope-2026"
    ].value
    assert donohue["donohue_pass_eligible"] is True

    lyv = claims[
        "claim-yosemite-entry-happy-isles-to-little-yosemite-valley-no-donohue-pass-scope-2026"
    ].value
    assert lyv["half_dome_eligible"] is True
    assert "first night required" in lyv["notes"]

    rockslides = claims[
        "claim-yosemite-entry-rockslides-cross-country-only-scope-2026"
    ].value
    assert rockslides["cross_country"] is True
    assert rockslides["travel_mode"] == "cross-country travel"


def test_facility_implications_and_explicit_physical_joins_do_not_use_proximity():
    records = load_canonical(ROOT)
    claims = index(records, "claims", "claim_id")
    relationships = records.relationships

    may_lake = claims["claim-yosemite-entry-may-lake-operations-2026"].value
    assert may_lake["toilet"] == "vault"
    assert may_lake["drinking_water"] == "not available at the vault toilet"
    assert may_lake["food_lockers"] is True

    cottonwood = claims[
        "claim-yosemite-entry-cottonwood-creek-operations-2026"
    ].value
    assert cottonwood["food_lockers"] is False

    assert any(
        relation.subject_id == "permit-yosemite-entry-may-lake"
        and relation.predicate == "applies_at"
        and relation.object_id == "trailhead-may-lake"
        for relation in relationships
    )
    assert not any(
        relation.subject_id == "permit-yosemite-entry-cottonwood-creek"
        and relation.predicate == "applies_at"
        for relation in relationships
    )


def test_process_future_recheck_and_topology_gaps_are_public():
    records = load_canonical(ROOT)
    claims = index(records, "claims", "claim_id")
    gaps = index(records, "gaps", "gap_id")

    process = claims["claim-yosemite-wilderness-permit-process-2026"].value
    assert process["advance_lottery_share_percent"] == 60
    assert process["week_ahead_share_percent"] == 40
    assert process["after_hours_summer_pickup"] is False

    assert "gap-yosemite-wilderness-entry-future-quotas" in gaps
    assert "gap-yosemite-wilderness-entry-minimum-camping-boundaries" in gaps
    assert "gap-yosemite-wilderness-entry-physical-starts" in gaps


def test_permit_entries_publish_to_canonical_detail_pages(generated_site):
    site, _ = generated_site
    for entity_id in (
        "permit-yosemite-overnight-wilderness",
        "permit-yosemite-entry-happy-isles-to-past-lyv-donohue-pass-eligible",
        "permit-yosemite-entry-white-wolf-to-pate-valley",
        "permit-yosemite-entry-budd-creek-cross-country-only",
        "permit-yosemite-entry-badger-pass",
    ):
        page = site / "knowledge" / entity_id / "index.html"
        assert page.exists()
        html = page.read_text()
        assert "National Park Service" in html


def test_batch_is_one_validated_add_only_changeset():
    change_set = load_changeset(ROOT / "changesets/v0" / f"{CHANGESET}.json")
    assert change_set.status is ChangeSetStatus.VALIDATED
    assert {operation.action for operation in change_set.operations} == {
        ChangeAction.ADD
    }
    assert len(change_set.operations) == len(
        {operation.path for operation in change_set.operations}
    )
