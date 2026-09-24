"""Official Rock Creek facility profiles remain useful and source-bounded."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def index(records, collection, key):
    return {getattr(item, key): item for item in getattr(records, collection)}


def test_group_and_backpacker_campgrounds_have_distinct_operating_models():
    records = load_canonical(ROOT)
    claims = index(records, "claims", "claim_id")
    aspen = claims["claim-campground-aspen-group-rock-creek-usfs-profile"].value
    backpacker = claims["claim-campground-mosquito-flat-backpacker-usfs-profile"].value
    group = claims["claim-campground-rock-creek-lake-group-usfs-profile"].value
    assert aspen["maximum_group_size"] == 25
    assert aspen["booking_facility_id"] == "233101"
    assert backpacker["maximum_stay_nights"] == 1
    assert "wilderness permit" in backpacker["eligibility"]
    assert group["site_type"] == "walk-in group campground"
    assert group["booking_facility_id"] == "232239"


def test_boating_profile_preserves_water_and_speed_constraints():
    records = load_canonical(ROOT)
    claims = index(records, "claims", "claim_id")
    boating = claims["claim-facility-rock-creek-boating-site-usfs-profile"].value
    assert boating["lake_speed_limit_mph"] == 5
    assert boating["facilities"] == {"flush_toilets": True, "potable_water": False}
    assert boating["fish_cleaning_in_lake"] is False


def test_generated_facility_pages_expose_planning_details(tmp_path):
    from scripts import build_site
    build_site.build(tmp_path)
    backpacker = (tmp_path / "knowledge" / "campground-mosquito-flat-backpacker" / "index.html").read_text()
    boating = (tmp_path / "knowledge" / "facility-rock-creek-boating-site" / "index.html").read_text()
    assert "valid wilderness permit" in backpacker
    assert "Lake speed limit mph</dt><dd>5" in boating


def test_one_validated_changeset_accounts_for_facility_layer():
    change = load_changeset(ROOT / "changesets/v0/wp-20260923-rock-creek-facility-layer.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({operation.path for operation in change.operations})
    assert {operation.action for operation in change.operations} == {ChangeAction.ADD}
