"""Rock Creek nonreservable campground depth stays source-bounded."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def indexed(records, collection, attribute):
    return {getattr(item, attribute): item for item in getattr(records, collection)}


def test_two_first_come_campgrounds_publish_official_profiles():
    records = load_canonical(ROOT)
    claims = indexed(records, "claims", "claim_id")

    pine = claims["claim-campground-pine-grove-rock-creek-usfs-profile"].value
    assert pine["site_count"] == 10
    assert pine["operating_model"] == "first come, first served; self-register at campground"
    assert pine["maximum_rv_length_ft"] == 15
    assert pine["facilities"]["potable_water"] is True
    assert "vault_toilets" not in pine["facilities"]

    upper = claims["claim-campground-upper-pine-grove-rock-creek-usfs-profile"].value
    assert upper["site_count"] == 9
    assert upper["published_elevation_ft"] == 9400
    assert upper["facilities"]["vault_toilets"] is True
    assert upper["accessibility_note"] == "some sites are flat for easier accessibility"


def test_tamarack_remains_an_explicit_identity_gap():
    records = load_canonical(ROOT)
    gaps = indexed(records, "gaps", "gap_id")
    claims = indexed(records, "claims", "claim_id")
    gap = gaps["gap-rock-creek-nonreservable-campground-depth"]

    assert gap.related_ids == ("campground-tamarack-rock-creek",)
    assert "feature type" in gap.reason
    assert "claim-campground-tamarack-rock-creek-usfs-profile" not in claims


def test_generated_pages_show_profiles_and_gap(tmp_path):
    from scripts import build_site

    build_site.build(tmp_path)
    pine_page = (tmp_path / "knowledge" / "campground-pine-grove-rock-creek" / "index.html").read_text()
    assert "first come, first served" in pine_page
    assert "Maximum rv length ft</dt><dd>15" in pine_page
    tamarack_page = (tmp_path / "knowledge" / "campground-tamarack-rock-creek" / "index.html").read_text()
    assert "insufficient to resolve the feature type" in tamarack_page


def test_one_validated_changeset_accounts_for_the_batch():
    change = load_changeset(ROOT / "changesets/v0/wp-20260923-rock-creek-nonreservable-depth.json")
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == len({item.path for item in change.operations})
    assert {item.action for item in change.operations} == {ChangeAction.ADD, ChangeAction.REPLACE}
