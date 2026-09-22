"""Planning outcomes for the Lake Chabot–Reinhardt Redwood deep dive."""

from pathlib import Path

from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


def _accesses(reads, park_id):
    return [
        edge for edge in reads.relationships_for(park_id)
        if edge.predicate == "accesses" and edge.object_id == park_id
    ]


def test_official_access_points_are_explicit_and_geospatially_usable():
    reads = CanonicalReadService(ROOT)
    expected = {
        "park-lake-chabot-regional-park": 10,
        "park-dr-aurelia-reinhardt-redwood-regional-park": 13,
    }
    for park_id, count in expected.items():
        edges = _accesses(reads, park_id)
        assert len(edges) == count
        for edge in edges:
            profile = next(
                claim for claim in reads.claims_for(edge.subject_id)
                if claim.predicate == "access_profile"
            )
            assert 37 < profile.value["latitude"] < 38
            assert -123 < profile.value["longitude"] < -122


def test_regional_route_connections_are_queryable():
    reads = CanonicalReadService(ROOT)
    edges = reads.relationships_for("route-east-bay-skyline-national-recreation-trail")
    assert any(
        edge.predicate == "accessible_from"
        and edge.object_id == "park-lake-chabot-regional-park"
        for edge in edges
    )
    assert any(
        edge.predicate == "traverses"
        and edge.object_id == "park-dr-aurelia-reinhardt-redwood-regional-park"
        for edge in edges
    )


def test_water_sanitation_rules_and_disruptions_remain_distinct():
    reads = CanonicalReadService(ROOT)
    chabot_claims = {
        claim.claim_id for claim in reads.claims_for("park-lake-chabot-regional-park")
    }
    redwood_claims = {
        claim.claim_id
        for claim in reads.claims_for("park-dr-aurelia-reinhardt-redwood-regional-park")
    }
    assert {
        "claim-lake-chabot-marina-accessible-water-sanitation",
        "claim-lake-chabot-water-contact-rules",
        "claim-lake-chabot-fishing-rules",
        "claim-lake-chabot-blue-green-algae-caution-20260922",
    } <= chabot_claims
    assert {
        "claim-reinhardt-redwood-piedmont-stables-boil-water-20260922",
        "claim-reinhardt-redwood-stream-trail-closures-2026",
        "claim-reinhardt-redwood-golden-spike-closure-2026",
        "claim-reinhardt-redwood-fishing-prohibited",
    } <= redwood_claims
