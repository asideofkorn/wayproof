from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def claims_by_id():
    return {claim.claim_id: claim for claim in load_canonical(ROOT).claims}


def test_arrival_and_parking_rules_preserve_operational_exceptions():
    claims = claims_by_id()
    arrival = claims["claim-yosemite-campground-arrival-departure-policy"].value
    assert arrival["check_in"] == arrival["checkout"] == "12:00"
    assert arrival["reservation_check_in_deadline_after_first_night"] == "10:00"
    assert arrival["missed_deadline_consequence"] == "reservation cancelled"

    parking = claims["claim-yosemite-campground-parking-policy"].value
    assert parking["maximum_motor_vehicles_per_campsite"] == 2
    assert parking["site_specific_one_vehicle_limits_possible"] is True
    assert parking["additional_parking_can_be_very_limited"] is True


def test_wastewater_utility_and_line_rules_stay_distinct():
    claims = claims_by_id()
    utilities = claims["claim-yosemite-campground-wastewater-and-utilities"].value
    assert utilities["camp_wastewater"] == "designated utility drains"
    assert utilities["utility_connections_prohibited"] is True
    assert utilities["campsite_hookups_available"] is False

    lines = claims["claim-yosemite-campground-lines-and-hammocks"].value
    assert lines["tree_padding_required"] is True
    assert lines["slacklines_at_camp_4"] == (
        "within 200 feet for registered Camp 4 campers"
    )
    assert lines["slacklines_at_other_campgrounds"] is False


def test_all_shared_rules_resolve_to_the_official_regulations_page():
    reads = CanonicalReadService(ROOT)
    for claim_id in (
        "claim-yosemite-campground-arrival-departure-policy",
        "claim-yosemite-campground-parking-policy",
        "claim-yosemite-campground-wastewater-and-utilities",
        "claim-yosemite-campground-lines-and-hammocks",
    ):
        explanation = reads.explain_claim(claim_id)
        assert explanation.sources[0].locator.endswith("/campregs.htm")


def test_shared_operations_publish_on_the_campground_collection_page(generated_site):
    site, _ = generated_site
    page = (
        site / "knowledge" / "campgrounds-yosemite-developed" / "index.html"
    ).read_text()
    assert "Arrival departure policy" in page
    assert "Wastewater and utility policy" in page
    assert "Line and hammock policy" in page


def test_batch_is_one_validated_add_only_changeset():
    changeset = load_changeset(
        ROOT
        / "changesets/v0/wp-20260926-yosemite-campground-shared-operations.json"
    )
    assert changeset.status is ChangeSetStatus.VALIDATED
    assert {operation.action for operation in changeset.operations} == {
        ChangeAction.ADD
    }
    assert len(changeset.operations) == len(
        {operation.path for operation in changeset.operations}
    )
