"""Outcome contract for the first EBRPD access-and-conditions deep dive."""

import json
from pathlib import Path

from scripts import build_site
from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


def test_tilden_access_points_are_explicit_and_geospatially_usable():
    reads = CanonicalReadService(ROOT)
    park_id = "park-charles-lee-tilden-regional-park"
    access_edges = [
        relationship for relationship in reads.relationships_for(park_id)
        if relationship.predicate == "accesses" and relationship.object_id == park_id
    ]

    assert len(access_edges) == 13
    for relationship in access_edges:
        profiles = [
            claim for claim in reads.claims_for(relationship.subject_id)
            if claim.predicate == "access_profile"
        ]
        assert len(profiles) == 1
        assert -123 < profiles[0].value["longitude"] < -122
        assert 37 < profiles[0].value["latitude"] < 38


def test_inspiration_point_hands_off_to_nimitz_and_skyline_routes():
    reads = CanonicalReadService(ROOT)
    inspiration_edges = reads.relationships_for("staging-tilden-inspiration-point")
    assert any(
        edge.predicate == "accesses" and edge.object_id == "route-tilden-nimitz-way"
        for edge in inspiration_edges
    )
    nimitz_edges = reads.relationships_for("route-tilden-nimitz-way")
    assert any(
        edge.predicate == "part_of"
        and edge.object_id == "route-east-bay-skyline-national-recreation-trail"
        for edge in nimitz_edges
    )


def test_tilden_live_disruptions_are_separate_recheckable_claims():
    reads = CanonicalReadService(ROOT)
    claims = {
        claim.claim_id: claim
        for claim in reads.claims_for("park-charles-lee-tilden-regional-park")
    }
    expected = {
        "claim-tilden-central-park-drive-weekday-closure-2026",
        "claim-tilden-laurel-canyon-trail-closure-2026",
        "claim-tilden-wildcat-gorge-trail-closure-2026",
        "claim-tilden-south-park-drive-newt-closure",
    }
    assert expected <= claims.keys()
    for claim_id in expected:
        provenance = reads.explain_claim(claim_id)
        assert provenance.sources[0].locator == "https://www.ebparks.org/parks/tilden"


def test_new_access_and_route_entities_publish_without_handwritten_pages(tmp_path):
    build_site.build(tmp_path)
    search = json.loads((tmp_path / "search" / "index.json").read_text())
    published = {entity["entity_id"] for entity in search["entities"]}

    assert "staging-tilden-inspiration-point" in published
    assert "route-tilden-nimitz-way" in published
    assert (tmp_path / "knowledge" / "staging-tilden-inspiration-point" / "index.html").exists()
    assert (tmp_path / "knowledge" / "route-tilden-nimitz-way" / "index.html").exists()
