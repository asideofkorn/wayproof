from __future__ import annotations

import json

import pytest

from scripts.verify_affected_site import _assert_outputs, _strings


def _write(path, value=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) if not isinstance(value, str) else value)


def _site(tmp_path):
    entity_id = "route-example"
    _write(tmp_path / "search/index.json", {
        "entities": [{"entity_id": entity_id}], "count": 1,
    })
    _write(tmp_path / f"knowledge/{entity_id}/index.html", entity_id)
    _write(tmp_path / f"knowledge/{entity_id}.json", {
        "entity_id": entity_id,
        "route_geometry_url": f"/geometry/routes/{entity_id}.geojson",
    })
    _write(tmp_path / f"geometry/routes/{entity_id}.geojson", {"type": "FeatureCollection"})
    for path in (
        "index.html", "map/index.html", "map/features.geojson",
        "search/index.html", "changes/index.json", "sitemap.xml", "robots.txt",
    ):
        _write(tmp_path / path)
    return entity_id


def test_affected_output_contract_checks_entity_geometry_and_shared_indexes(tmp_path):
    entity_id = _site(tmp_path)
    _assert_outputs(tmp_path, {entity_id}, {"removed-entity"}, {("entities", entity_id)})


def test_affected_output_contract_rejects_missing_geometry(tmp_path):
    entity_id = _site(tmp_path)
    (tmp_path / f"geometry/routes/{entity_id}.geojson").unlink()
    with pytest.raises(AssertionError, match="missing affected route geometry"):
        _assert_outputs(tmp_path, {entity_id}, set(), set())


def test_reference_extraction_handles_nested_artifact_values():
    assert set(_strings({"ids": ["entity-a", {"claim": "claim-b"}], "n": 2})) == {
        "entity-a", "claim-b",
    }
