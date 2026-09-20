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
    source_ids = {item.source_id for item in snapshot.sources}
    assert all(item.source_id in source_ids for item in snapshot.observations)
    assert all(item.evidence_ids for item in snapshot.claims)


def test_del_valle_inventory_is_corroborated_and_old_gap_is_historical():
    snapshot = records()
    inventory = next(item for item in snapshot.claims
                     if item.claim_id == "claim-del-valle-campground-inventory")
    assert inventory.value == {
        "cabins": 5,
        "drive_up_tent": 124,
        "rv_full_hookup": 21,
        "total": 150,
    }
    assert len(inventory.evidence_ids) >= 2
    assert not any(item.gap_id == "gap-del-valle-inventory-count"
                   for item in snapshot.gaps)
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-del-valle-ebrpd-park-page.json")
    removed = [item for item in change.operations if item.action.value == "REMOVE"]
    assert [item.record_id for item in removed] == ["gap-del-valle-inventory-count"]


def test_uncorroborated_ohlone_statement_is_not_a_current_rule():
    snapshot = records()
    statement = "claim-del-valle-ohlone-permit-page-statement"
    claim = next(item for item in snapshot.claims if item.claim_id == statement)
    assert str(claim.temporal_scope.ends_on) == "2025-12-31"
    assert not any(item.claim_id == statement for item in snapshot.rules)
    assert not any(statement in item.related_ids for item in snapshot.gaps)


def test_volatile_conditions_require_pretrip_recheck():
    result = next(item for item in records().derived_results
                  if item.result_id == "result-del-valle-pretrip-recheck")
    assert result.value["required"] is True
    assert set(result.value["topics"]).issuperset({
        "fire_danger", "blue_green_algae", "flood_closure",
        "boat_inspection_procedure",
    })


def test_del_valle_changeset_is_a_validated_public_manifest():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-del-valle-reserveamerica-foundation.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 105
    assert len({item.path for item in change.operations}) == 105


def test_ebrpd_update_exercises_add_replace_and_remove():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-del-valle-ebrpd-park-page.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 95, "REPLACE": 8, "REMOVE": 1}


def test_dated_water_conditions_do_not_become_permanent_facts():
    snapshot = records()
    for claim_id in (
        "claim-del-valle-ebrpd-east-beach-algae",
        "claim-del-valle-ebrpd-west-beach-water",
    ):
        item = next(value for value in snapshot.claims if value.claim_id == claim_id)
        assert item.temporal_scope.starts_on == item.temporal_scope.ends_on


def test_conflicting_published_park_areas_remain_visible():
    snapshot = records()
    areas = {item.value for item in snapshot.claims
             if item.subject_id == "park-del-valle-regional-park"
             and item.predicate == "published_area_acres"}
    assert areas == {4316, 4395}
    assert any(item.gap_id == "gap-del-valle-park-area-conflict"
               for item in snapshot.gaps)


def test_mussel_inspection_applies_to_motorized_and_nonmotorized_equipment():
    snapshot = records()
    item = next(value for value in snapshot.claims
                if value.claim_id == "claim-ebrpd-mussels-inspection-scope")
    assert set(item.value["equipment"]) == {
        "boat", "kayak", "canoe", "sailboat", "inflatable_craft", "floating_board"
    }
    rule = next(value for value in snapshot.rules
                if value.rule_id == "rule-ebrpd-mussels-inspection-required")
    assert rule.conditions[0].dimension == "equipment_type"


def test_mussel_history_rule_uses_bounded_prior_events():
    snapshot = records()
    rule = next(value for value in snapshot.rules
                if value.rule_id == "rule-ebrpd-mussels-history-survey")
    assert rule.conditions[0].dimension == "equipment_prior_waterbody_events"
    assert rule.conditions[0].value == 30
    assert any(item.gap_id == "gap-ebrpd-mussels-current-flagged-waters"
               for item in snapshot.gaps)


def test_band_effective_date_and_failed_nonmotorized_gap_are_explicit():
    snapshot = records()
    band = next(value for value in snapshot.claims
                if value.claim_id == "claim-ebrpd-mussels-lake-specific-bands")
    assert str(band.temporal_scope.starts_on) == "2025-05-07"
    assert any(item.gap_id == "gap-ebrpd-mussels-nonmotorized-failure-quarantine"
               for item in snapshot.gaps)


def test_mussel_changeset_exercises_corroborating_replacements():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ebrpd-invasive-mussel-program.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 44, "REPLACE": 4, "REMOVE": 0}
    boat_inspection = next(item for item in records().claims
                           if item.claim_id == "claim-del-valle-boat-inspection")
    assert len(boat_inspection.evidence_ids) == 3


def test_algae_guidance_separates_stable_health_rules_from_current_conditions():
    snapshot = records()
    human = next(item for item in snapshot.claims
                 if item.claim_id == "claim-ebrpd-algae-human-exposure")
    assert set(human.value["routes"]) == {"ingestion", "inhalation", "skin_contact"}
    current = next(item for item in snapshot.claims
                   if item.claim_id == "claim-del-valle-ebrpd-east-beach-algae")
    assert current.temporal_scope.starts_on == current.temporal_scope.ends_on
    assert len(current.evidence_ids) >= 2


def test_algae_advisory_level_boundary_remains_an_explicit_gap():
    snapshot = records()
    gap = next(item for item in snapshot.gaps
               if item.gap_id == "gap-ebrpd-algae-advisory-level-actions")
    assert "Caution versus Danger" in gap.reason
    assert any(item.rule_id == "rule-ebrpd-algae-dog-water-access"
               for item in snapshot.rules)


def test_algae_changeset_adds_guidance_and_replaces_corroborated_state():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ebrpd-blue-green-algae.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 28, "REPLACE": 3, "REMOVE": 0}


def test_swimming_registration_is_not_misapplied_to_del_valle():
    snapshot = records()
    registration = next(item for item in snapshot.claims
                        if item.claim_id == "claim-ebrpd-swimming-registration-applicability")
    assert "Del Valle" not in registration.value["named_facilities"]
    assert registration.value["price_usd"] == 6


def test_del_valle_swimming_safety_and_fee_ambiguity_are_explicit():
    snapshot = records()
    safety = next(item for item in snapshot.claims
                  if item.claim_id == "claim-ebrpd-swimming-del-valle-safety")
    assert safety.value["days_to_avoid_after_rain"] == 3
    assert any(item.gap_id == "gap-del-valle-swimming-parking-fee"
               for item in snapshot.gaps)
    assert any(item.gap_id == "gap-del-valle-stoplight-meanings"
               for item in snapshot.gaps)


def test_swimming_changeset_combines_two_sources_with_bounded_replacements():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ebrpd-del-valle-swimming.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 35, "REPLACE": 3, "REMOVE": 0}


def test_bacterial_stoplight_is_defined_without_erasing_algae_gap():
    snapshot = records()
    item = next(value for value in snapshot.claims
                if value.claim_id == "claim-ebrpd-water-quality-traffic-light")
    assert item.value["red"] == "beach_closed_for_water_quality_issue"
    gap = next(value for value in snapshot.gaps
               if value.gap_id == "gap-del-valle-stoplight-meanings")
    assert "algae" in gap.question.lower()
    assert any(value.rule_id == "rule-ebrpd-water-quality-red-closure"
               for value in snapshot.rules)


def test_water_quality_changeset_narrows_existing_gap():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ebrpd-water-quality-stoplight.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 12, "REPLACE": 4, "REMOVE": 0}


def test_campground_corpus_keeps_current_and_dated_conflicting_counts():
    snapshot = records()
    current = next(item for item in snapshot.claims
                   if item.claim_id == "claim-del-valle-campground-inventory")
    dated = next(item for item in snapshot.claims
                 if item.claim_id == "claim-del-valle-camp-map-inventory-2025")
    assert current.value["total"] == 150
    assert dated.value == 145
    assert str(dated.temporal_scope.starts_on) == "2025-11-01"
    assert any(item.gap_id == "gap-del-valle-camp-map-currentness"
               for item in snapshot.gaps)


def test_cabin_faq_refines_booking_and_site_use_without_flattening_rules():
    snapshot = records()
    cabins = next(item for item in snapshot.claims
                  if item.claim_id == "claim-del-valle-ebrpd-cabins")
    use = next(item for item in snapshot.claims
               if item.claim_id == "claim-del-valle-cabin-site-use")
    assert cabins.value["reservation_channel"] == "phone_only"
    assert cabins.value["maximum_advance_weeks"] == 12
    assert use.value["max_consecutive_nights"] == 10
    assert use.value["required_nights_away"] == 5
    assert any(item.rule_id == "rule-del-valle-cabin-booking"
               for item in snapshot.rules)


def test_named_group_camps_and_2026_closures_remain_recheckable():
    snapshot = records()
    details = next(item for item in snapshot.claims
                   if item.claim_id == "claim-del-valle-group-camp-details")
    closures = next(item for item in snapshot.claims
                    if item.claim_id == "claim-del-valle-seasonal-closures-2026")
    assert details.value["Hetch Hetchy"]["capacity"] == [50, 100]
    assert closures.value["Cedar Camp"] == "until_further_notice"
    assert closures.value["subject_to_change_without_notice"] is True
    recheck = next(item for item in snapshot.derived_results
                   if item.result_id == "result-del-valle-pretrip-recheck")
    assert "campground_and_site_closures" in recheck.value["topics"]
    assert "claim-ebrpd-alerts-closures-live" in recheck.input_ids


def test_campground_corpus_manifest_covers_eight_sources_and_replacements():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ebrpd-del-valle-campground-corpus.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 67, "REPLACE": 4, "REMOVE": 0}
    assert sum(item.record_type == "source" for item in change.operations) == 8


def test_ordinance_38_corroborates_core_campground_limits():
    snapshot = records()
    for claim_id in (
        "claim-del-valle-family-capacity",
        "claim-del-valle-family-stay-limit",
        "claim-del-valle-family-vehicles",
        "claim-del-valle-smoking-prohibited",
    ):
        item = next(value for value in snapshot.claims if value.claim_id == claim_id)
        assert any("ordinance38" in evidence_id for evidence_id in item.evidence_ids)


def test_ordinance_38_keeps_district_and_del_valle_boating_rules_distinct():
    snapshot = records()
    launch = next(item for item in snapshot.claims
                  if item.claim_id == "claim-del-valle-ordinance-boat-launch")
    operating = next(item for item in snapshot.claims
                     if item.claim_id == "claim-del-valle-ordinance-boat-operating-rules")
    assert launch.value["size_restriction"] is None
    assert operating.value["maximum_speed_mph"] == 10
    assert operating.value["towed_persons_allowed"] is False
    assert str(operating.temporal_scope.starts_on) == "2023-09-01"


def test_ordinance_38_records_dog_zone_and_generator_rule_layering():
    snapshot = records()
    dog_zone = next(item for item in snapshot.claims
                    if item.claim_id == "claim-del-valle-dog-swimming-prohibited-zone")
    assert dog_zone.value == "Oak Point north to East Marina"
    gap = next(item for item in snapshot.gaps
               if item.gap_id == "gap-del-valle-generator-rule-layering")
    assert "stricter" in gap.reason
    assert any(item.rule_id == "rule-ebrpd-campground-disturbing-devices"
               for item in snapshot.rules)


def test_ordinance_38_manifest_is_complete():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ebrpd-ordinance-38-del-valle.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 40, "REPLACE": 7, "REMOVE": 0}
    assert sum(item.record_type == "source" for item in change.operations) == 2


def test_ohlone_page_resolves_old_permit_ambiguity_by_date():
    snapshot = records()
    current = next(item for item in snapshot.claims
                   if item.claim_id == "claim-ohlone-trail-permit-not-required-2026")
    historical = next(item for item in snapshot.claims
                      if item.claim_id == "claim-del-valle-ohlone-permit-page-statement")
    assert current.value is False
    assert str(current.temporal_scope.starts_on) == "2026-01-01"
    assert str(historical.temporal_scope.ends_on) == "2025-12-31"
    assert not any(item.gap_id == "gap-del-valle-ohlone-permit-current"
                   for item in snapshot.gaps)


def test_ohlone_overnight_reservation_remains_separate_from_trail_permit():
    snapshot = records()
    overnight = next(item for item in snapshot.claims
                     if item.claim_id == "claim-ohlone-overnight-reservation")
    assert overnight.value == {
        "channel": "phone",
        "designated_sites_only": True,
        "minimum_advance_days": 2,
        "required": True,
    }
    assert any(item.rule_id == "rule-ohlone-overnight-reservation"
               for item in snapshot.rules)


def test_ohlone_water_status_is_dated_and_requires_recheck():
    snapshot = records()
    water = next(item for item in snapshot.claims
                 if item.claim_id == "claim-ohlone-water-availability-20260919")
    assert water.temporal_scope.starts_on == water.temporal_scope.ends_on
    assert water.value["potable"] is False
    assert len(water.value["available"]) == 7
    recheck = next(item for item in snapshot.derived_results
                   if item.result_id == "result-del-valle-pretrip-recheck")
    assert "ohlone_backcountry_water" in recheck.value["topics"]


def test_ohlone_page_manifest_exercises_resolution_lifecycle():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ebrpd-ohlone-park-page.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 49, "REPLACE": 3, "REMOVE": 1}


def test_ohlone_map_preserves_spatial_evidence_without_reviving_permit():
    snapshot = records()
    title = next(item for item in snapshot.claims
                 if item.claim_id == "claim-ohlone-map-permit-title-historical")
    current = next(item for item in snapshot.claims
                   if item.claim_id == "claim-ohlone-trail-permit-not-required-2026")
    assert str(title.temporal_scope.ends_on) == "2025-12-31"
    assert current.value is False
    assert str(current.temporal_scope.starts_on) == "2026-01-01"


def test_ohlone_map_records_corridor_distances_and_access_boundaries():
    snapshot = records()
    distances = next(item for item in snapshot.claims
                     if item.claim_id == "claim-ohlone-map-corridor-distances")
    restrictions = next(item for item in snapshot.claims
                        if item.claim_id == "claim-ohlone-map-access-restrictions")
    assert distances.value["sunol_boundary_to_del_valle_boundary"] == 13.9
    assert distances.value["sunol_boundary_to_del_valle_west_beach_services"] == 15.6
    assert restrictions.value["sfwd_land_stay_on_trail"] is True
    assert restrictions.value["land_bank_entry"] is False


def test_ohlone_map_manifest_is_additive_with_bounded_corroboration():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-ebrpd-ohlone-map-2025-08.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 30, "REPLACE": 2, "REMOVE": 0}


def test_del_valle_picnic_inventory_captures_all_named_capacities():
    snapshot = records()
    item = next(value for value in snapshot.claims
                if value.claim_id == "claim-del-valle-picnic-inventory")
    assert len(item.value) == 12
    assert item.value["Fiesta Grande"]["capacity"] == 500
    assert item.value["Vista Del Lago"]["capacity"] == 35


def test_del_valle_fishing_credentials_are_age_and_place_specific():
    snapshot = records()
    item = next(value for value in snapshot.claims
                if value.claim_id == "claim-del-valle-fishing-license-requirements")
    assert item.value == {
        "california_license_required": True,
        "district_permit_required": True,
        "minimum_age": 16,
    }
    rule = next(value for value in snapshot.rules
                if value.rule_id == "rule-del-valle-fishing-credentials")
    assert rule.conditions[0].dimension == "participant_age"


def test_del_valle_map_and_horse_capacity_uncertainties_remain_visible():
    snapshot = records()
    gaps = {item.gap_id for item in snapshot.gaps}
    assert "gap-del-valle-map-no-fishing-segment" in gaps
    assert "gap-del-valle-little-chaparral-horse-capacity" in gaps
    map_claim = next(value for value in snapshot.claims
                     if value.claim_id == "claim-del-valle-map-use-restrictions")
    assert str(map_claim.temporal_scope.starts_on) == "2026-04-01"


def test_del_valle_map_picnic_fishing_manifest_is_additive():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-del-valle-map-picnic-fishing.json")
    counts = {action: sum(item.action.value == action for item in change.operations)
              for action in ("ADD", "REPLACE", "REMOVE")}
    assert counts == {"ADD": 50, "REPLACE": 0, "REMOVE": 0}
    assert sum(item.record_type == "source" for item in change.operations) == 3
