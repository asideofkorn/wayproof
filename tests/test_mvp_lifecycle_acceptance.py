"""End-to-end MVP acceptance test across publication and consumer boundaries."""

from datetime import date

from wayproof.canonical_storage import load_canonical, write_candidate
from wayproof.proposal_service import (ConstrainedProposalService,
                                       ProposalRequest)
from wayproof.publication import verify_publication
from wayproof.read_service import CanonicalReadService
from wayproof.readiness import ReadinessState
from wayproof.recheck import RecheckAnswerability
from wayproof.schema import (ActivityContext, CanonicalRecords, ChangeAction,
                             ChangeOperation, ChangeSet, Claim, Condition,
                             Coverage, DerivedResult, Entity, Evidence,
                             Fulfillment, Observation, PartyContext,
                             PlanningContext, Rule, Source, SpatialScope,
                             TemporalScope, TripObjective, TripStage)
from wayproof.write_service import (ChangeSetWriteService,
                                    InMemoryCanonicalRepository)


COLLECTIONS = {
    "entity": "entities",
    "spatial_scope": "spatial_scopes",
    "source": "sources",
    "observation": "observations",
    "evidence": "evidence",
    "claim": "claims",
    "rule": "rules",
    "derived_result": "derived_results",
}


def operation(record_type, record_id, evidence_refs=()):
    return ChangeOperation(
        ChangeAction.ADD,
        record_type,
        record_id,
        f"canonical/v0/{COLLECTIONS[record_type]}/{record_id}.json",
        "Seed the acceptance-test planning contract.",
        evidence_refs,
    )


def publish(root, writes, change_set_id):
    """Simulate reviewed Git publication after a separate builder prepares it."""
    prepared = writes.prepare(change_set_id, "candidate-builder")
    validated = writes.get(change_set_id)
    changed_paths = [
        ("A", item.path) for item in prepared.operations
    ] + [("A", f"changesets/v0/{change_set_id}.json")]
    assert verify_publication(changed_paths, (validated,)) == ()
    write_candidate(root, prepared, validated)


def seed_planning_contract(root):
    records = CanonicalRecords(
        entities=[Entity("park-test", "park", "Lifecycle Test Park")],
        spatial_scopes=[SpatialScope(
            "scope-test-park", "park", "park-test", "Lifecycle test boundary"
        )],
        sources=[
            Source("source-test-policy", "https://example.test/policy", "Test Park"),
            Source("source-test-status", "https://example.test/status", "Test Park"),
        ],
        observations=[
            Observation(
                "observation-test-policy", "source-test-policy",
                "An overnight permit is required."
            ),
            Observation(
                "observation-test-status", "source-test-status",
                "Water was available on September 20, 2026."
            ),
        ],
        evidence=[
            Evidence(
                "evidence-test-policy", "observation-test-policy", "claim-test-policy"
            ),
            Evidence(
                "evidence-test-status", "observation-test-status", "claim-test-status"
            ),
        ],
        claims=[
            Claim(
                "claim-test-policy", "park-test", "overnight_permit_required", True,
                ("evidence-test-policy",), spatial_scope_ids=("scope-test-park",),
            ),
            Claim(
                "claim-test-status", "park-test", "water_availability", "available",
                ("evidence-test-status",),
                TemporalScope(date(2026, 9, 20), date(2026, 9, 20)),
                ("scope-test-park",),
            ),
        ],
        rules=[Rule(
            "rule-test-overnight-permit",
            "claim-test-policy",
            "Obtain an overnight permit.",
            (Condition("activity.overnight", "equals", True),),
            ("scope-test-park",),
        )],
        derived_results=[DerivedResult(
            "result-test-pretrip-recheck",
            "pretrip_recheck",
            {"required": True, "topics": ["water_availability"]},
            ("claim-test-status",),
            "Water availability must be checked for the trip date.",
        )],
    )
    ids = (
        ("entity", "park-test", ()),
        ("spatial_scope", "scope-test-park", ()),
        ("source", "source-test-policy", ()),
        ("source", "source-test-status", ()),
        ("observation", "observation-test-policy", ()),
        ("observation", "observation-test-status", ()),
        ("evidence", "evidence-test-policy", ()),
        ("evidence", "evidence-test-status", ()),
        ("claim", "claim-test-policy", ("evidence-test-policy",)),
        ("claim", "claim-test-status", ("evidence-test-status",)),
        ("rule", "rule-test-overnight-permit", ()),
        ("derived_result", "result-test-pretrip-recheck", ()),
    )
    change = ChangeSet(
        "seed-planning-contract",
        records,
        "Seed a reviewed planning and recheck contract",
        tuple(operation(*item) for item in ids),
    )
    writes = ChangeSetWriteService(InMemoryCanonicalRepository())
    writes.propose(change, "maintainer")
    assert writes.validate(change.change_set_id, "schema-validator") == ()
    publish(root, writes, change.change_set_id)


def trip(trip_date=date(2026, 9, 20)):
    return PlanningContext(
        trip_date=trip_date,
        objectives=(TripObjective("visit-test", "park-test", "overnight"),),
        stages=(TripStage("camp", 1, "overnight", ("scope-test-park",)),),
        party=PartyContext(participant_ids=("traveler",)),
        activities=ActivityContext(
            activities=("camping",), attributes={"overnight": True}
        ),
    )


def test_mvp_lifecycle_from_constrained_proposal_to_consumer_history(tmp_path):
    seed_planning_contract(tmp_path)
    base = load_canonical(tmp_path)
    writes = ChangeSetWriteService(InMemoryCanonicalRepository(base))
    proposals = ConstrainedProposalService(writes, "mcp:research-agent")
    request = ProposalRequest(
        "add-test-spring-report",
        "Add a sourced spring report for review",
        "Preserve the bounded report without treating it as a permanent condition.",
        CanonicalRecords(
            entities=[Entity("water-test-spring", "water_source", "Test Spring")],
            sources=[Source(
                "source-test-spring-report", "https://example.test/spring", "Reporter"
            )],
            observations=[Observation(
                "observation-test-spring-report", "source-test-spring-report",
                "The spring was flowing during the visit."
            )],
            evidence=[Evidence(
                "evidence-test-spring-report", "observation-test-spring-report",
                "claim-test-spring-report"
            )],
            claims=[Claim(
                "claim-test-spring-report", "water-test-spring",
                "reported_water_availability", "flowing",
                ("evidence-test-spring-report",),
                TemporalScope(date(2026, 9, 20), date(2026, 9, 20)),
            )],
        ),
    )

    draft = proposals.submit(request)
    assert draft.status.value == "DRAFT"
    validated = proposals.validate(draft.change_set_id)
    assert validated.status.value == "VALIDATED"
    publish(tmp_path, writes, validated.change_set_id)

    reads = CanonicalReadService(tmp_path)
    assert reads.search_entities("test spring")[0].entity_id == "water-test-spring"
    provenance = reads.explain_claim("claim-test-spring-report")
    assert provenance.sources[0].locator == "https://example.test/spring"
    history = reads.changes(record_id="claim-test-spring-report")
    assert history[0].change_set_id == "add-test-spring-report"
    assert history[0].reason == request.reason

    context = trip()
    requirements = reads.requirements(context)
    assert requirements.requirements[0].status.value == "missing"
    assert reads.readiness(context).state is ReadinessState.BLOCKED

    permit = Fulfillment(
        "fulfillment-test-permit",
        "requirement-test-overnight-permit",
        "permit",
        ("evidence-test-policy",),
        Coverage(
            participant_ids=("traveler",),
            stage_ids=("camp",),
            starts_on=context.trip_date,
            ends_on=context.trip_date,
        ),
    )
    assert reads.readiness(context, (permit,)).state is ReadinessState.READY

    same_day = reads.pretrip_recheck(context, "result-test-pretrip-recheck")
    future = reads.pretrip_recheck(
        trip(date(2026, 9, 21)), "result-test-pretrip-recheck"
    )
    assert same_day.items[0].answerability is RecheckAnswerability.ANSWERED
    assert future.items[0].answerability is RecheckAnswerability.NEEDS_CURRENT_CHECK

    assert [item.action for item in proposals.workflow_log(validated.change_set_id)] == [
        "proposed", "validated", "prepared"
    ]
