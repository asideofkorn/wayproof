"""Contracts for volatile EBRPD conditions promoted on 2026-09-22."""

from pathlib import Path

from wayproof.read_service import CanonicalReadService


ROOT = Path(__file__).resolve().parents[1]


def _batch_claims(reads):
    observation_id = "observation-ebrpd-alerts-closures-20260922"
    evidence_ids = {
        evidence.evidence_id for evidence in reads._records.evidence
        if evidence.observation_id == observation_id
    }
    return [
        claim for claim in reads._records.claims
        if set(claim.evidence_ids) & evidence_ids
    ]


def test_each_promoted_alert_is_atomic_and_traces_to_the_live_alert_page():
    reads = CanonicalReadService(ROOT)
    claims = _batch_claims(reads)

    assert len(claims) == 19
    for claim in claims:
        provenance = reads.explain_claim(claim.claim_id)
        assert [source.locator for source in provenance.sources] == [
            "https://www.ebparks.org/alerts-closures"
        ]


def test_unknown_condition_start_dates_are_not_invented():
    reads = CanonicalReadService(ROOT)
    unknown_start = {
        "claim-deer-valley-no-public-access",
        "claim-round-valley-backpack-camp-no-water-20260922",
        "claim-point-pinole-bay-trail-sinkhole-closure-2026",
        "claim-eckley-pier-water-unavailable-20260922",
    }
    claims = {claim.claim_id: claim for claim in _batch_claims(reads)}

    for claim_id in unknown_start:
        assert claims[claim_id].temporal_scope.starts_on is None


def test_critical_access_and_water_outcomes_are_directly_queryable():
    reads = CanonicalReadService(ROOT)
    deer = {
        claim.claim_id: claim
        for claim in reads.claims_for("park-deer-valley-regional-park")
    }
    round_valley = {
        claim.claim_id: claim
        for claim in reads.claims_for("backpack-camp-round-valley")
    }

    assert deer["claim-deer-valley-no-public-access"].value["status"] == "not_open_to_public"
    assert round_valley["claim-round-valley-backpack-camp-no-water-20260922"].value["status"] == "unavailable"
