from __future__ import annotations

from scripts.select_test_groups import select_groups, select_scope
from scripts.test_groups import GROUPS, group_for


def test_taboose_canonical_batch_skips_unrelated_ebrpd_regressions():
    paths = [
        "canonical/v0/claims/claim-taboose-pets.json",
        "changesets/v0/changeset-taboose-pass.json",
        "geometry/v0/snapshots/inyo-taboose.geojson",
        "DATA_LICENSE.md",
    ]
    assert select_groups(paths) == ["core", "planning", "regional-sierra"]
    assert select_scope(paths).site_mode == "affected"


def test_ebrpd_canonical_batch_skips_unrelated_sierra_regressions():
    assert select_groups(["canonical/v0/entities/park-tilden.json"]) == [
        "core", "planning", "regional-ebrpd"
    ]


def test_generic_site_change_runs_shared_consumer_contracts_only():
    assert select_groups(["wayproof/canonical_site.py", "tests/test_build_site.py"]) == [
        "core", "planning", "site"
    ]


def test_shared_domain_and_ci_changes_fail_safe_to_full_suite():
    assert select_groups(["wayproof/read_service.py"]) == list(GROUPS)
    assert select_groups([".github/workflows/tests.yml"]) == list(GROUPS)


def test_documentation_only_change_uses_core_smoke_suite():
    assert select_groups(["docs/testing.md", "README.md"]) == ["core"]


def test_generated_site_consumers_share_the_site_shard():
    assert group_for("test_emigrant_foundation.py") == "site"
    assert group_for("test_eastern_sierra_area_access_hubs.py") == "site"


def test_changed_destination_site_module_uses_prebuilt_affected_site():
    scope = select_scope([
        "canonical/v0/entities/pass-taboose.json",
    ])
    assert list(scope.groups) == ["core", "planning", "regional-sierra"]
    assert scope.site_mode == "affected"
    assert scope.site_tests == ("tests/test_taboose_pass.py",)


def test_shared_renderer_and_full_runs_keep_exhaustive_site_shard():
    scope = select_scope(["wayproof/canonical_site.py"])
    assert list(scope.groups) == ["core", "planning", "site"]
    assert scope.site_mode == "full"
    assert not scope.site_tests
    assert select_scope([], full=True).site_mode == "full"


def test_regional_ingestion_script_does_not_force_unrelated_region():
    assert select_groups(["scripts/ingest_taboose_pass.py"]) == [
        "core", "regional-sierra"
    ]
