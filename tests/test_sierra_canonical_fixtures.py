"""Canonical Williamson/Tyndall and Whitney reference-fixture regressions."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeSetStatus


ROOT = Path(__file__).resolve().parents[1]


def indexed(items, attr):
    return {getattr(item, attr): item for item in items}


def test_fixture_changeset_is_validated_and_exact():
    change = load_changeset(
        ROOT / "changesets/v0/wp-20260920-sierra-reference-fixtures.json"
    )
    assert change.status is ChangeSetStatus.VALIDATED
    assert len(change.operations) == 78
    assert len({item.path for item in change.operations}) == 78


def test_williamson_and_tyndall_share_shepherd_pass_access():
    snapshot = load_canonical(ROOT)
    relationships = indexed(snapshot.relationships, "relationship_id")
    assert relationships["relationship-williamson-approached-shepherd"].object_id == (
        "route-shepherd-pass"
    )
    assert relationships["relationship-tyndall-approached-shepherd"].object_id == (
        "route-shepherd-pass"
    )
    result = indexed(snapshot.derived_results, "result_id")[
        "result-williamson-tyndall-shared-access"
    ]
    assert result.value == {
        "shared_route": "route-shepherd-pass",
        "shared_trailhead": "trailhead-shepherd-pass-hiker",
        "overnight_permit": "permit-inyo-overnight-wilderness",
    }


def test_shepherd_profile_and_quota_are_atomic_source_facts():
    claims = indexed(load_canonical(ROOT).claims, "claim_id")
    assert claims["claim-shepherd-pass-route-profile"].value["shepherd_pass_miles"] == 12.25
    assert claims["claim-shepherd-pass-route-profile"].value["john_muir_trail_miles"] == 15.25
    assert claims["claim-shepherd-pass-quota"].value == {
        "trail_code": "JM32",
        "total": 15,
        "six_month_release": 9,
        "two_week_release": 6,
    }


def test_whitney_permit_selection_depends_on_route_and_trip_shape():
    snapshot = load_canonical(ROOT)
    result = indexed(snapshot.derived_results, "result_id")[
        "result-whitney-route-permit-split"
    ]
    assert result.value == {
        "day_use_any_whitney_zone_route": "permit-whitney-zone-day-use",
        "overnight_classic": "permit-whitney-trail-overnight",
        "overnight_north_fork": "permit-inyo-overnight-wilderness",
    }

    rels = indexed(snapshot.relationships, "relationship_id")
    assert rels["relationship-whitney-day-zone-permit"].object_id == (
        "permit-whitney-zone-day-use"
    )
    assert rels["relationship-north-fork-day-zone-permit"].object_id == (
        "permit-whitney-zone-day-use"
    )
    assert rels["relationship-north-fork-overnight-inyo-permit"].object_id == (
        "permit-inyo-overnight-wilderness"
    )


def test_north_fork_has_its_own_quota_and_is_not_silently_called_classic_trail():
    claims = indexed(load_canonical(ROOT).claims, "claim_id")
    assert claims["claim-north-fork-quota"].value == {
        "trail_code": "JM34",
        "total": 10,
        "six_month_release": 6,
        "two_week_release": 4,
    }
    overnight = claims["claim-whitney-overnight-scope"].value
    assert overnight["included_route"] == "classic Mount Whitney Trail"
    assert overnight["excluded_route"] == "North Fork of Lone Pine Creek"


def test_inyo_origin_permit_preserves_continuous_travel_into_seki():
    claim = indexed(load_canonical(ROOT).claims, "claim_id")[
        "claim-inyo-continuous-travel"
    ]
    assert claim.value == {"valid_into_seki": True, "overnight_exit_ends_trip": True}
