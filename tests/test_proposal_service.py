"""Constrained proposal boundary tests."""

import pytest

from wayproof.proposal_service import (ConstrainedProposalService,
                                       ProposalRejected, ProposalRequest)
from wayproof.schema import (CanonicalRecords, Claim, DerivedResult, Entity,
                             Evidence, Observation, Rule, Source,
                             ChangeSetStatus)
from wayproof.write_service import (ChangeSetWriteService,
                                    InMemoryCanonicalRepository)


def service(initial=None):
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(initial))
    return writes, ConstrainedProposalService(writes, "mcp:research-agent")


def evidence_request(change_set_id="proposal-water-status"):
    return ProposalRequest(
        change_set_id=change_set_id,
        summary="Propose a dated water-status observation",
        reason="Preserve the submitted source and bounded observation for review.",
        records=CanonicalRecords(
            entities=[Entity("water-test-spring", "water_source", "Test Spring")],
            sources=[Source("source-test-report", "https://example.test/report", "Reporter")],
            observations=[Observation(
                "observation-test-report", "source-test-report", "Water was flowing."
            )],
            evidence=[Evidence(
                "evidence-test-report", "observation-test-report", "claim-test-water"
            )],
            claims=[Claim(
                "claim-test-water", "water-test-spring", "reported_water_availability",
                "flowing", ("evidence-test-report",),
            )],
        ),
    )


def test_submit_creates_an_additive_draft_with_derived_operations():
    writes, proposals = service()
    receipt = proposals.submit(evidence_request())
    explanation = proposals.explain(receipt.change_set_id)

    assert receipt.status is ChangeSetStatus.DRAFT
    assert explanation.addition_count == 5
    assert {item.action.value for item in explanation.operations} == {"ADD"}
    assert all(item.path.startswith("canonical/v0/") for item in explanation.operations)
    claim = next(item for item in explanation.operations if item.record_type == "claim")
    assert claim.evidence_refs == ("evidence-test-report",)


def test_consumer_can_validate_but_cannot_prepare_or_publish():
    writes, proposals = service()
    proposals.submit(evidence_request())
    receipt = proposals.validate("proposal-water-status")

    assert receipt.status is ChangeSetStatus.VALIDATED
    assert receipt.validation_errors == ()
    assert [item.action for item in proposals.workflow_log(receipt.change_set_id)] == [
        "proposed", "validated"
    ]
    assert not hasattr(proposals, "prepare")
    assert not hasattr(proposals, "approve")
    assert not hasattr(proposals, "promote")
    assert writes.get(receipt.change_set_id).status is ChangeSetStatus.VALIDATED


def test_invalid_evidence_chain_remains_a_draft_with_explanations():
    _, proposals = service()
    request = ProposalRequest(
        "invalid-proposal",
        "Propose an incomplete claim",
        "Expose missing provenance during validation.",
        CanonicalRecords(claims=[Claim(
            "claim-orphan", "missing-entity", "status", "open", ()
        )]),
    )
    proposals.submit(request)
    receipt = proposals.validate(request.change_set_id)

    assert receipt.status is ChangeSetStatus.DRAFT
    assert any("requires evidence" in item for item in receipt.validation_errors)
    assert proposals.explain(request.change_set_id).validation_errors


def test_normative_rules_and_derived_results_are_not_consumer_proposable():
    _, proposals = service()
    for record in (
        CanonicalRecords(rules=[Rule("rule-test", "claim-test", "Do a thing")]),
        CanonicalRecords(derived_results=[DerivedResult(
            "result-test", "answerability", "answered", ("claim-test",)
        )]),
    ):
        with pytest.raises(ProposalRejected, match="cannot add"):
            proposals.submit(ProposalRequest(
                "privileged-proposal", "Try privileged record", "Boundary test", record
            ))


def test_empty_and_anonymous_proposals_are_rejected():
    writes = ChangeSetWriteService(InMemoryCanonicalRepository())
    with pytest.raises(ProposalRejected, match="identified actor"):
        ConstrainedProposalService(writes, " ")

    proposals = ConstrainedProposalService(writes, "consumer")
    with pytest.raises(ProposalRejected, match="at least one record"):
        proposals.submit(ProposalRequest(
            "empty", "Empty proposal", "Nothing to add", CanonicalRecords()
        ))
