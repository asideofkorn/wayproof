"""Completion contract for the autonomous EBRPD park-depth pass."""

import json
from pathlib import Path

from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


def _official_park_claims(reads, entity_id):
    claims = []
    for claim in reads.claims_for(entity_id):
        provenance = reads.explain_claim(claim.claim_id)
        if any("ebparks.org/parks/" in source.locator for source in provenance.sources):
            claims.append(claim)
    return claims


def test_every_published_park_has_official_page_provenance():
    reads = CanonicalReadService(ROOT)
    parks = reads.search_entities(kinds=("park",))

    assert len(parks) == 64
    uncovered = [
        park.name for park in parks
        if not _official_park_claims(reads, park.entity_id)
    ]
    assert uncovered == []


def test_every_official_park_source_is_observed():
    reads = CanonicalReadService(ROOT)
    official_sources = {
        source.source_id for source in reads._records.sources
        if "ebparks.org/parks/" in source.locator
    }
    observed_sources = {
        observation.source_id for observation in reads._records.observations
    }
    assert official_sources <= observed_sources


def test_every_published_park_has_a_generated_human_page(tmp_path):
    from scripts import build_site

    build_site.build(tmp_path)
    directory = json.loads((tmp_path / "parks" / "index.json").read_text())
    published_ids = {item["entity_id"] for item in directory["entities"]}
    reads = CanonicalReadService(ROOT)

    for park in reads.search_entities(kinds=("park",)):
        assert park.entity_id in published_ids
        assert (tmp_path / "knowledge" / park.entity_id / "index.html").exists()


def test_all_camping_entities_have_canonical_context():
    reads = CanonicalReadService(ROOT)
    camping_kinds = {
        "campground", "campsite", "family_campsite", "group_campsite",
        "cabin_campsite", "backcountry_camp", "equestrian_campsite",
        "equestrian_campsite_area", "equestrian_group_campsite",
    }
    camps = reads.search_entities(kinds=camping_kinds)
    orphaned = []
    for camp in camps:
        if not (
            reads.relationships_for(camp.entity_id)
            or reads.claims_for(camp.entity_id)
            or reads.spatial_scopes_for(camp.entity_id)
        ):
            orphaned.append(camp.name)
    assert orphaned == []
