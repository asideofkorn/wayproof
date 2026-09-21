# Wayproof

Wayproof is open-source, source-backed logistics for outdoor trips. It helps
answer what access applies, which rules and requirements matter, what evidence
supports an answer, and what must be checked again before departure.

The project is Sierra Nevada- and California public-lands focused today. Its
domain model is designed to expand without treating geographic proximity as a
route, silence as permission, or old observations as current conditions.

Wayproof complements navigation tools such as CalTopo and Gaia GPS. It does not
draw or navigate an exact route and it is not a booking system.

## Project status

Wayproof is currently a hybrid application:

- the established CSV-backed CLI remains operational but is not published on the website;
- Canonical Schema v0 knowledge is stored as deterministic, versioned JSON;
- published knowledge changes are authorized by validated ChangeSets and GitHub
  review;
- rule applicability, requirement generation, fulfillment coverage, Trip
  Readiness, and Pre-trip Recheck are implemented as domain services;
- a shared read service exposes search, provenance, published history,
  requirements, readiness, and rechecks; and
- a read-only MCP server exposes that same canonical service boundary to agents;
  and
- a constrained additive proposal service lets identified consumers prepare and
  validate evidence drafts without gaining publication authority.

M0, the trusted canonical foundation, is complete. M1–M3 are in progress. The
legacy CLI has not yet fully migrated to the canonical services, and the MCP
surface is currently read-only. See [PRODUCT.md](PRODUCT.md),
[ARCHITECTURE.md](ARCHITECTURE.md), and [ROADMAP.md](ROADMAP.md) for the product
contract and exact milestone status.

## Why this exists

A destination name and coordinates are not an executable trip plan. Real trips
depend on questions such as:

- Which approach and entry point actually serve this objective?
- Does the selected route change the required permit?
- Are the entry and exit different, and what is required at each end?
- Which rules apply to this date, activity, party, or equipment?
- Does one reservation or credential cover everyone and every stage?
- Is a reported road, beach, campsite, or water source currently available?
- Which source supports the answer, and when was it observed?
- What is unknown, conflicting, unavailable, closed, or due for rechecking?

Wayproof prefers an explicit `UNKNOWN` or `NEEDS_CURRENT_CHECK` result to a
confident unsupported answer.

## What someone actually asks

Wayproof is meant to answer practical questions such as:

- What do I need to do for this trip, and how do I get it?
- Does my route, date, party, activity, or equipment change the answer?
- What will it cost, what is available, and what must I carry?
- What is closed or hazardous, and what needs a current recheck?
- Where are water and facilities, and when were they last confirmed?
- How do you know—and what do you still not know?

These examples explain the product; they are not an exhaustive or
machine-readable contract. The planning scorecard owns its more detailed,
stable question catalog independently. A question Wayproof cannot answer should
say so plainly: declining is a usable answer; being wrong is not.

## `plan`: Objective + Date

The established `plan.py` command remains the current end-user planner while
its behavior is migrated behind the canonical read service. Its quick-start
commands appear below.

## Trust model

Canonical evidence follows this lineage:

```text
Source -> Observation -> Evidence -> Claim -> Rule / DerivedResult
```

Planning applies that knowledge through:

```text
Rule -> Requirement -> Fulfillment
```

Publication follows a separate controlled lifecycle:

```text
DRAFT ChangeSet
  -> VALIDATED
  -> separately prepared candidate
  -> Git commit / pull request / CI
  -> maintainer approval
  -> merge to main = published
```

`VALIDATED` means a proposal is structurally and semantically representable. It
does not mean every claim is certain, reviewed, approved, or published. Agents
and consumer adapters cannot directly author canonical files or promote their
own proposals.

Published ChangeSets provide wiki-like revision history: consumers can inspect
why a canonical record was added, replaced, or removed while dated observations
preserve changes in the outside world.

## Implemented canonical capabilities

The canonical service layer currently supports:

- durable entities, spatial scopes, relationships, and temporal claims;
- `Source -> Observation -> Evidence -> Claim` provenance traversal;
- route-, activity-, and trip-context-specific rule applicability;
- explicit `APPLIES`, `DOES_NOT_APPLY`, and `UNKNOWN` outcomes;
- runtime requirements with participant, equipment, stage, and date coverage;
- `MISSING`, `PARTIAL`, and `COMPLETE` fulfillment coverage, including several
  fulfillments jointly satisfying one requirement;
- Trip Readiness states: `READY`, `BLOCKED`, `PARTIAL`, `UNKNOWN`, and
  `NOT_APPLICABLE`;
- Pre-trip Recheck answerability: `ANSWERED`, `NEEDS_CURRENT_CHECK`, and
  `UNKNOWN`;
- deterministic canonical serialization and exact ChangeSet-to-diff checking;
- entity search, typed lookup, evidence explanations, and per-record published
  ChangeSet history; and
- additive evidence proposals with derived paths and operations, but no direct
  preparation, approval, promotion, replacement, or removal capability.

The end-to-end acceptance test exercises:

```text
proposal -> validation -> candidate preparation -> publication verification
         -> Git-backed persistence -> read service -> provenance/history
         -> requirements -> readiness -> recheck
```

See [tests/test_mvp_lifecycle_acceptance.py](tests/test_mvp_lifecycle_acceptance.py).

## Reference coverage

The canonical regression corpus includes:

- Del Valle Regional Park and campground facilities, rules, boating controls,
  swimming conditions, closures, and water-quality rechecks;
- the Ohlone Wilderness Trail route graph, parallel and access segments,
  campsites, parking, water, restrooms, and dated field observations;
- Mount Williamson and Mount Tyndall shared Shepherd Pass access;
- Mount Whitney classic-trail versus North Fork route and permit semantics;
- facility, concessioner, fishing, boating, and invasive-species cases; and
- eight adversarial schema cases covering access, water evidence, partial route
  resolution, coverage mismatch, supersession, unknown versus unavailable,
  compound scope, and evidence disagreement.

Coverage is intentionally selective. Legacy data is classified as `KEEP`,
`REVERIFY`, `RECONSTRUCT`, or `DISCARD`; it is not bulk-migrated into canonical
truth.

## Installation

Wayproof supports Python 3.14.

```bash
git clone https://github.com/asideofkorn/wayproof.git
cd wayproof
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the complete test suite:

```bash
python -m pytest -q
```

## Legacy CLI quick start

These commands use the established CSV-backed application while adapter
migration is in progress.

Resolve access and permit logistics for named objectives:

```bash
python plan.py "Mount Williamson" "Mount Tyndall" --date 2027-07-15
```

Model a distinct exit explicitly:

```bash
python plan.py "Rose Peak" --date 2027-06-01 --exit "Ohlone College"
```

Write the resolved plan as JSON:

```bash
python plan.py "Mount Whitney" --date 2027-07-01 --output plan.json
```

Inspect source history and open research questions:

```bash
python cli.py --permit-sources whitney_zone
python cli.py --open-questions
```

Search legacy campground data while keeping unlocated matches visible:

```bash
python cli.py --campgrounds --access drive_in --near 37.8044,-122.2712
```

Use `python plan.py --help`, `python cli.py --help`, or
`python report.py --help` for complete options.

The legacy report queue remains available for CSV-era corrections:

```bash
python report.py submit data/water_sources.csv "Boyd Camp" \
  "Observed water flowing" --confidence firsthand
python report.py list
```

A report changes only the queue. It does not directly modify domain data.

## Canonical read service

`CanonicalReadService` is the common read-only boundary used by the website and
MCP adapter and intended for the remaining CLI migration.

```python
from pathlib import Path

from wayproof.read_service import CanonicalReadService

reads = CanonicalReadService(Path("."))

whitney = reads.search_entities("whitney", kinds=("peak",))
claim = reads.explain_claim("claim-whitney-overnight-scope")
history = reads.changes(record_id="claim-whitney-overnight-scope")

print(whitney[0].name)
print(claim.sources[0].locator)
print(history[0].change_set_id)
```

The same object exposes:

- `get(record_type, record_id)` and `entity(entity_id)`;
- `resolve_intent(intent)` for conservative `TripIntent` resolution;
- `plan(intent, fulfillments=(), recheck_result_ids=())` for integrated
  resolution, constraint evaluation, readiness, and named rechecks;
- `requirements(context, fulfillments=())`;
- `readiness(context, fulfillments=())`; and
- `pretrip_recheck(context, result_id=...)`.

Planning calls take a typed `PlanningContext`. Real examples are in
[tests/test_requirement_evaluation.py](tests/test_requirement_evaluation.py),
[tests/test_trip_readiness.py](tests/test_trip_readiness.py), and
[tests/test_pretrip_recheck.py](tests/test_pretrip_recheck.py).

The read service deliberately has no proposal, approval, promotion, or raw
storage mutation methods.

## MCP read server

The initial MCP adapter exposes eleven read-only tools over
`CanonicalReadService`:

- `search_entities`, `get_record`, and `get_entity`;
- `explain_claim`, `get_changes`, and `list_knowledge_gaps`; and
- `resolve_trip_intent`, `plan_trip`, `evaluate_requirements`,
  `evaluate_readiness`, and `pretrip_recheck`.

Install the project, then start its standard-input/output server from the
repository root:

```bash
pip install -e .
wayproof-mcp
```

If a host launches the command from another directory, set
`WAYPROOF_REPOSITORY` to the checkout containing `canonical/v0` and
`changesets/v0`. `resolve_trip_intent` accepts an ISO `trip_date`, one or more
objective names or IDs, and optional route, entry, and exit choices. It returns
`resolved`, `partial`, `ambiguous`, or `unknown` plus a typed planning context
when one can be built. It never guesses among multiple routes, silently assumes
an exit, or treats missing topology as fact. Where canonical segment topology
exists, the result includes ordered legs, known distance, distance completeness,
accessible entities, and separately identified alternate segments. Those leg
scopes become ordered planning stages used by requirement and readiness
evaluation. The evaluation tools also accept an already-resolved context with
objectives and ordered stages.

`plan_trip` is the composed operation for consumers: it accepts the same intent,
optional fulfillments, and explicitly named recheck manifests. Ambiguous or
unknown intent stops before readiness; a partial resolution can still expose a
separately blocked or ready requirement slice. This prevents a satisfied permit
from hiding missing route topology, and prevents an unresolved route from being
treated as permit-free.

The MCP server intentionally exposes no proposal, approval, promotion,
publication, filesystem, or raw canonical CRUD tools.

## Constrained proposals

`ConstrainedProposalService` is the domain boundary for a future contribution
adapter. An identified actor can submit additive, typed evidence records and ask
for validation and explanation.

The initial surface allows:

- entities and spatial scopes;
- sources and observations;
- evidence and claims;
- sourced relationships; and
- knowledge gaps.

It does not allow consumer-authored rules, derived results, runtime requirements
or fulfillments, `REPLACE`, `REMOVE`, candidate preparation, approval,
promotion, or publication. A separate trusted builder and the GitHub review
workflow retain those responsibilities.

See [tests/test_proposal_service.py](tests/test_proposal_service.py) for a small
source-to-claim proposal and its validation behavior.

## Canonical repository layout

```text
canonical/v0/<collection>/<record-id>.json
changesets/v0/<change-set-id>.json
```

Important implementation modules:

```text
wayproof/schema.py             Schema v0 records and ChangeSet values
wayproof/validation.py         canonical invariants
wayproof/write_service.py      validate and prepare detached candidates
wayproof/canonical_storage.py  deterministic Git-backed serialization
wayproof/publication.py        exact canonical-diff authorization
wayproof/requirements.py       rule applicability and fulfillment coverage
wayproof/readiness.py          bounded Trip Readiness aggregation
wayproof/recheck.py            volatile-condition projection and freshness
wayproof/read_service.py       shared consumer read facade
wayproof/mcp_server.py         read-only MCP adapter
wayproof/proposal_service.py   constrained additive draft proposals
```

Canonical JSON files are serializer-owned. Normal contributors and agents
should not hand-edit them. Canonical changes require one validated ChangeSet
whose operations exactly account for the Git diff. Ordinary code,
documentation, tests, and rendering changes do not require a ChangeSet when
canonical knowledge is untouched.

## Current limitations and next work

The following remain incomplete:

- richer `TripIntent` resolution beyond named objectives, sourced endpoints,
  and published segment topology, including aliases and constraint matching;
- complete Trip Readiness aggregation for costs, deadlines, inventory,
  closures, and conflicts;
- completion of the legacy CLI migration to `CanonicalReadService`;
- constrained MCP proposal adapter;
- automated URL/artifact ingestion and stronger duplicate/entity resolution;
- operational freshness scheduling beyond explicit canonical recheck manifests;
  and
- exceptional repair/redaction policy for already-published artifacts.

A generated SQLite index is not currently required. Git-backed structured files
remain canonical unless measured performance or concurrency needs justify an
additional read index or transactional service.

## Website

[wayproof.dev](https://wayproof.dev) is generated from this repository and
deployed through GitHub Pages. Canonical search and entity-detail pages consume
the shared read service and present claims, source evidence, knowledge gaps,
relationships, and published ChangeSet history. The Del Valle destination view
adds visitor-oriented access, camping, lake, Ohlone Trail, and Pre-trip Recheck
sections over those same services. The deployed website is canonical-only;
legacy CSV-backed planning tools remain available in the repository but do not
publish web pages.

## Development

Useful checks:

```bash
python -m pytest -q
python scripts/verify_canonical_diff.py --base origin/main --head HEAD
```

The canonical-diff verifier is required only when a branch changes canonical
records or ChangeSets.

Pull requests run the suite on Python 3.14. Existing unrelated worktree changes
should be preserved.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), cite sources for knowledge changes,
and preserve uncertainty rather than converting it into a confident value.

For data licensing and source-policy constraints, see
[DATA_LICENSE.md](DATA_LICENSE.md).

## License

Source code is licensed under the [MIT License](LICENSE). Data and source
artifacts may carry separate terms described in [DATA_LICENSE.md](DATA_LICENSE.md).
