from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.recheck import RecheckAnswerability
from wayproof.schema import ChangeAction, ChangeSetStatus

from tests.test_yosemite_nps_foundation import yosemite_overnight_context


ROOT = Path(__file__).resolve().parents[1]


def indexed(records, collection, field):
    return {getattr(item, field): item for item in getattr(records, collection)}


def test_park_and_high_country_mobility_profiles_preserve_seasonality():
    claims = indexed(load_canonical(ROOT), "claims", "claim_id")
    park = claims["claim-yosemite-public-transportation"].value
    assert "Yosemite Valley-Tuolumne Meadows hikers bus" in park["internal"]
    assert park["no_service"] == ["Hetch Hetchy Valley"]
    assert park["seasonal_service_requires_current_check"] is True

    tioga = claims["claim-tioga-road-seasonal-transportation-2026"]
    assert tioga.value["yarts_highway_120_east"]["conditions_permitting"] is True
    assert "White Wolf" in tioga.value["yarts_highway_120_east"]["stops"]
    assert tioga.temporal_scope.starts_on.year == 2026
    assert tioga.temporal_scope.ends_on.year == 2026

    tuolumne = claims["claim-tuolumne-seasonal-transportation-2026"].value
    assert tuolumne["tuolumne_meadows_shuttle"]["not_available_every_year"] is True
    assert "Tenaya Lake" in tuolumne["tuolumne_meadows_shuttle"]["service_area"]


def test_transportation_remains_a_consumer_visible_current_check():
    result = CanonicalReadService(ROOT).pretrip_recheck(
        yosemite_overnight_context(), "result-yosemite-pretrip-recheck"
    )
    item = next(
        entry
        for entry in result.items
        if entry.input_id == "claim-yosemite-public-transportation"
    )
    assert item.answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK
    assert item.source_ids == ("source-nps-yosemite-transportation",)


def test_corridor_pages_publish_the_mobility_profiles(generated_site):
    site, _ = generated_site
    for entity_id in ("place-tioga-road-corridor", "place-tuolumne-meadows"):
        page = (site / "knowledge" / entity_id / "index.html").read_text()
        assert "Seasonal transportation profile" in page
        assert "current check" in page.lower()


def test_batch_is_one_validated_changeset():
    changeset = load_changeset(
        ROOT / "changesets/v0/wp-20260926-yosemite-seasonal-mobility.json"
    )
    assert changeset.status is ChangeSetStatus.VALIDATED
    assert {operation.action for operation in changeset.operations} == {
        ChangeAction.ADD,
        ChangeAction.REPLACE,
    }
