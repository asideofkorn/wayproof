# Wayproof Product Direction

## Purpose

Wayproof is open-source, source-backed logistics for outdoor trips. It turns a
specific objective and date into an executable plan: how the trip is accessed,
which constraints apply, what must be obtained or done, when action is needed,
and what evidence supports every answer.

The repository remains Sierra Nevada- and public-lands focused and provides a
working legacy planning CLI, a research corpus, and the first implemented
canonical planning services. Canonical Schema v0, controlled publication,
requirement coverage, bounded Trip Readiness, Pre-trip Recheck, published
ChangeSet history, and constrained additive proposals are implemented. The
website now reads exclusively through the canonical service layer and publishes
automatic discovery pages plus focused Del Valle and Ohlone views. The legacy
CLI has not yet fully migrated. The initial MCP adapter is implemented as a
read-only surface over the same canonical service layer, including bounded
intent-to-context resolution.

## Product promise

For a proposed trip, Wayproof should answer:

- what route, access points, traversals, land units, facilities, and resources
  are relevant;
- which rules apply to the date, route, activity, party, and equipment;
- which requirements gate the trip and what can fulfill each requirement;
- when scarce inventory or an application window becomes actionable;
- which facts are supported, stale, disputed, route-dependent, or unknown; and
- what must be rechecked shortly before departure.

A clear refusal or `UNKNOWN` result is better than a confident unsupported
answer. Absence of data is never evidence that a restriction, fee, closure, or
requirement does not exist.

## Product model

A `Trip` is evaluated from an expressed `TripIntent` and a resolved
`PlanningContext`. An intent may name a summit, trail, traverse, campground,
waterbody, facility, or another legitimate objective; a peak is one objective
type, not the ontology of the product.

The planning context includes:

- `TripObjective` values and ordered `TripStage` values;
- route, access, and traversal choices, including distinct entry and exit;
- date and time;
- `PartyContext`, including characteristics that materially affect a rule or
  booking constraint;
- `ActivityContext`; and
- `EquipmentContext`, including bounded equipment history when a rule depends
  on it.

Wayproof projects knowledge onto that context. It must distinguish legal access
from physical condition and user/equipment capability. It must also distinguish
facility existence from operational availability, and inventory that is
confirmed unavailable from inventory that simply cannot be checked.

## Core user outcomes

### Trip readiness

`Trip Readiness` is the consolidated, evidence-backed view of whether the
currently described trip can proceed. It includes applicable requirements,
coverage by proposed fulfillments, unresolved gaps, conflicts, deadlines,
closures, cost components, and route-dependent uncertainty. Readiness is not a
generic safety score or a booking guarantee.

Coverage is explicit: a reservation, credential, completed action, or verified
condition may cover only certain people, vehicles, dates, stages, places, or
activities. A partially covered requirement remains incomplete.

### Pre-trip recheck

`Pre-trip Recheck` reevaluates facts likely to change after initial planning:
roads, closures, water, fire restrictions, weather-sensitive operations,
facility status, inventory, and other time-sensitive claims. The result explains
what changed, what remains unresolved, and which sources should be checked.

### Explainability and answerability

Every material conclusion should expose its supporting claims and evidence.
Results use explicit answerability states such as answered, partial, conflicting,
unknown, not applicable, and needs-current-check. Exact enum spellings are an
implementation decision; the semantic distinctions are not.

## Contributor and research workflow

Evidence may arrive as an official page, PDF, screenshot, GPX trace, field
report, social post, GitHub issue, or structured authoritative dataset. Agents
may help identify entities, preserve observations, extract candidate claims, and
explain proposals. They must not directly author canonical knowledge.

The reviewer sees a `ChangeSet` containing the proposed changes, provenance,
uncertainties, conflicts, and knowledge gaps. A proposal can be valid while its
underlying fact remains uncertain: validation means the uncertainty is
represented correctly, not that the world is fully known.

Candidate preparation follows a controlled domain workflow:

```text
DRAFT -> VALIDATED -> PREPARED CANDIDATE
                         -> Git commit and PR
                         -> maintainer approval
                         -> merge to main = PROMOTED/PUBLISHED
```

Git and GitHub are the revision, concurrency, review, and publication system;
Wayproof does not reproduce them inside its domain model. Human approval is
required. CI proves that the typed ChangeSet accounts for the canonical diff,
and `main` represents published canonical knowledge.

Promoted ChangeSets are public provenance. Consumers can inspect which
published edit created, replaced, or removed a record and follow it to the Git
commit and PR. Rejected drafts and private research are not published
automatically.

Wayproof should feel like a trustworthy current wiki page: the primary view is
the currently applicable, cited answer, while every published revision and its
domain rationale remains available for inspection. ChangeSet history records
when Wayproof knowledge changed; dated Observations and Claims record when the
real-world condition changed.

## MVP contract

The MVP is complete when Wayproof can take a bounded real trip and:

1. represent objectives, stages, access, route/traversal, relevant context, and
   temporal scope without destination-specific schema exceptions;
2. trace `Source -> Observation -> Evidence -> Claim -> Rule/DerivedResult`;
3. derive applicable requirements and evaluate explicit fulfillment coverage;
4. produce Trip Readiness and Pre-trip Recheck outputs with answerability and
   provenance;
5. decline or surface gaps instead of inferring permission, availability, or
   correctness from silence;
6. accept new knowledge only through a validated, approved ChangeSet; and
7. expose the same behavior through the domain/service layer used by CLI and,
   later, MCP adapters.

MVP does not require nationwide coverage, exact route navigation, a database,
automated booking, or autonomous publication by an AI agent.

### Current implementation status

The executable lifecycle currently demonstrates the core contract end to end:

```text
constrained DRAFT proposal
  -> validation
  -> separate candidate preparation
  -> exact publication-diff verification
  -> Git-backed canonical files and ChangeSet history
  -> read service
  -> requirement coverage
  -> Trip Readiness
  -> Pre-trip Recheck
```

This proves the trust boundary and the central Whitney/Del Valle/Ohlone
semantics. Named objectives now resolve conservatively through sourced
route/access relationships into a planning context, preserving ambiguous
routes, unknown exits, and unsupported choices as explicit outcomes. It does
not yet complete the whole product contract. Remaining MVP work includes richer
traversal and constraint resolution, complete cost/deadline/conflict
aggregation, and completion of the legacy CLI migration onto the canonical read
service.

The deployed website is the first complete canonical read adapter. It publishes
entity search and evidence/history details; automatic Parks, Trails, Camping,
Peaks, and Changes indexes; JSON representations and sitemap discovery; and
focused Del Valle destination and Ohlone corridor pages. Directory membership
is derived from canonical entity kinds at build time, so newly promoted records
appear without a hand-maintained website catalog. Conditions and Pre-trip
Recheck remain contextual parts of a trip, destination, or route rather than a
standalone navigation category.

Coverage has expanded through the same controlled lifecycle to every current
top-level parkland page in the official East Bay Regional Park District
directory. This demonstrates geographic growth without a schema fork; it does
not by itself complete intent resolution, operational freshness, or the future
constrained MCP contribution workflow.

## Reference and regression fixtures

The product contract is grounded in real journeys and adversarial cases:

- the completed Ohlone traverse: two ends, campsite scarcity, phone booking,
  parking dependency, full cost, facility closure, and dated water evidence;
- Williamson plus Tyndall: shared objectives, Shepherd Pass access, effort, and
  continuous-travel/permit reasoning;
- Whitney-area routes: the same portal serving approaches governed by different
  permit products;
- facility and concessioner cases: operator, land manager, booking facility,
  booking channel, and governed place must remain separate;
- fishing: activity-, participant-, credential-, season-, method-, and species-
  dependent rules;
- boating and invasive-species controls: equipment identity and prior history,
  inspection, quarantine/dry-out, decontamination, and vessel-specific
  credentials;
- the eight adversarial schema cases covering legal versus physical access,
  water evidence, partial route resolution, coverage mismatch, supersession,
  unknown versus unavailable, compound scope, and evidence disagreement.

Canonical Schema v0 passed all eight adversarial cases without needing a
special-purpose primitive and is frozen for initial implementation. Frozen means
stable enough to implement and migrate against, not immune to evidence-driven
future change.

## Deliberate non-goals and open implementation choices

Wayproof complements rather than replaces navigation products such as CalTopo,
Gaia GPS, and similar tools. It does not manufacture an exact route from nearby
geometry.

The initial Python service boundaries and wire spellings now exist and may
evolve compatibly as adapters exercise them. Whether or when a generated SQLite
read index is useful remains intentionally unresolved. Canonical storage uses
versioned, deterministic, one-record-per-file JSON; ChangeSets are small public
domain-intent manifests alongside Git history rather than a second
version-control system.
