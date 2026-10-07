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
CLI has not yet fully migrated, but `plan.py --canonical` now exposes the
composed planner for named objectives while preserving the CSV mode during
transition. The initial MCP adapter is implemented as a
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

## Product personas

Personas are behavior-based product hypotheses, not demographic profiles or
claims that one person represents every user. They preserve the practical
failure modes that Wayproof should prevent and provide scenarios against which
future data, planning, and interface work can be evaluated. Revise them as
broader research produces stronger or conflicting evidence.

### The conscientious cross-jurisdiction adventurer

This experienced backpacker or outdoor guide plans ambitious multi-day trips,
often with a partner and dog. They are prepared and compliance-minded: they
obtain permits, inspect multiple maps and layers, carry required equipment,
read trailhead signs, and prefer abandoning an objective to knowingly violating
a land-management rule. Experience does not protect them when individually
accurate planning systems fail to compose the complete trip.

Their goals are to complete a memorable route, include their dog where it is
legal, understand the entire journey rather than only its starting trailhead,
confirm that their vehicle can reach the intended access point, and retain
usable alternatives when one constraint invalidates the original plan.

A representative failure combines two disconnected planning problems. A
low-clearance vehicle cannot reach the intended trailhead, adding substantial
distance and elevation. Later, an apparently continuous trail crosses from
National Forest wilderness into National Park wilderness where a different pet
rule applies. The maps, permit interaction, and starting signage did not make
the route-specific jurisdiction change operationally visible. The restriction
is discovered only after significant effort, without a prepared compliant
alternative.

Wayproof should support this persona by:

- projecting every evidenced jurisdiction and rule onto the relevant route
  segment instead of flattening a regional rule across the entire trip;
- warning before a route crosses into an incompatible jurisdiction and showing
  the supported boundary, turnaround point, or unresolved connection;
- resolving pet, party, activity, and equipment constraints against complete
  route alternatives;
- connecting road condition, vehicle suitability, parking, and overflow facts
  to the resulting approach distance and elevation rather than treating the
  trailhead as automatically reachable;
- offering source-backed alternatives from usable access points when the
  preferred plan fails;
- distinguishing official facts, dated observations, uncertainty, and items
  that still require a ranger or current-source recheck; and
- retaining the relevant route, evidence, and warnings for offline field use.

**Acceptance scenario:** a traveler plans a multi-day Taboose-area trip with a
dog and a low-clearance vehicle. Before departure, Wayproof identifies uncertain
road access and its possible approach consequences, highlights the route segment
that enters Kings Canyon National Park, explains the segment-scoped pet
restriction, and presents supported compliant alternatives. Each conclusion is
traceable to evidence; missing geometry or current access status remains
explicitly unresolved.

**Research basis:** this provisional persona was drafted from a bounded review
of the public [Wilder Magic backpacking account](https://www.instagram.com/wilder.magic/)
and its visible public discussion on October 6, 2026. Example:
[Eastern Sierra cross-jurisdiction backpacking failure reel](https://www.instagram.com/reel/DeH-n6VS6Ur/).
The source demonstrates a behavior and planning failure; it does not justify
inference about unreported personal attributes or the prevalence of this
persona.

### The permit holder without a route

This traveler has successfully obtained a wilderness permit but still lacks an
executable itinerary. A permit name, entry trailhead, or first-night zone does
not tell them which connected segments reach an objective, where camping is
allowed, whether a proposed return or crossover ends the permitted trip, or
which direction and exit remain valid.

Wayproof should connect the permit product to its governed entry, eligible
routes, ordered stages, first-night and continuous-travel constraints, legal
camping context, and supported exits. It should show why a proposed itinerary
is valid, partial, or incompatible rather than treating possession of a permit
as trip readiness.

**Acceptance scenario:** a traveler selects a Glen Aulin or High Sierra Camp
entry permit and a three-day objective. Wayproof builds only evidenced route
options from that entry, identifies unresolved nightly stops, rejects an
itinerary that exits and improperly re-enters wilderness, and explains which
permit or route change would resolve the problem.

**Research examples:** [Glen Aulin permit without a route](https://www.reddit.com/r/Yosemite/comments/140g06p/glen_aulin_backpacking_permit_route/),
[High Sierra Camp Loop permit confusion](https://www.reddit.com/r/Yosemite/comments/1q9wiyv/high_sierra_camp_loop_confusion/),
and a [five-day itinerary with invalid wilderness re-entry](https://www.reddit.com/r/Yosemite/comments/1r1fsla/5_day_backpacking_plan_questions/).

### The fixed-window visiting planner

This traveler has fixed dates, long-distance transportation, and limited local
knowledge. They must combine driving, lodging or camping, seasonal transit,
route choice, elevation, acclimatization, weather-sensitive access, and current
conditions into a small number of usable days. Individually useful destination
lists increase rather than reduce their planning burden when they are not
evaluated together.

Wayproof should compare feasible objectives within the stated dates and party
constraints; connect each to current access, parking, campground, and seasonal
transport facts; and expose alternatives when a road, shuttle, weather window,
or acclimatization constraint breaks the preferred plan. Recommendations must
remain separate from supported operational facts.

**Acceptance scenario:** a visitor arriving from sea level has four Eastern
Sierra days during fall color season. Wayproof identifies usable campground
bases and trailheads, preserves uncertain foliage and weather as rechecks,
surfaces route elevations and seasonal transport limits, and produces a small
set of plans whose driving and hiking stages fit the fixed window.

**Research examples:** a [last-minute Eastern Sierra trip with intertwined
camping, altitude, foliage, and route questions](https://www.reddit.com/r/SierraNevada/comments/1wz9oi8/help_planning_a_last_minute_eastern_sierra_trip/)
and an [October Rafferty Creek trip whose seasonal transportation may have
ended](https://www.reddit.com/r/Yosemite/comments/1sreuq7/wilderness_permit_questions_rafferty_creek_entry/).

### The conditions-dependent water planner

This traveler can identify trails and camps, but route feasibility depends on
water whose status changes by source, season, trailhead, and observation date.
Community reports may appear to conflict because they refer to different ponds,
springs, tanks, faucets, or dates. A mapped water symbol is not evidence that
water is presently available or safe to drink.

Wayproof should attach each water observation to a precise source and route
stage, distinguish built infrastructure from natural water, retain observation
and retrieval dates, preserve genuine disagreement, and calculate no unsupported
availability. The plan should identify dry stretches, water-dependent camps,
and sources requiring a current check.

**Acceptance scenario:** a two-night Henry Coe plan selects an entry and camps
that depend on particular water sources. Wayproof distinguishes historically
reliable facilities from dated natural-source reports, shows which planned legs
depend on each source, and produces a pre-trip water recheck rather than a
timeless assurance.

**Research examples:** a [Henry Coe discussion containing differing current
water reports and trailhead-specific alternatives](https://www.reddit.com/r/norcalhiking/comments/17k66ke/two_night_backpacking_trip_nearby_menlo_park/)
and a [short family trip request centered on reachable water](https://www.reddit.com/r/norcalhiking/comments/1v1wxh3/backpacking_options_for_sacramento_area/).

### The inventory-constrained objective seeker

This traveler has a desired objective and dates constrained by work, travel, or
companions, but scarce permits or campsites are allocated through lotteries,
release windows, cancellations, and walk-up inventory. They may repeatedly pay
application fees without learning which alternate entry reaches the same goal
or whether a different date, permit product, or route is a genuine substitute.

Wayproof should begin with the objective, enumerate only evidenced route and
access alternatives, associate each with the correct permit or reservation
product, and explain release timing, costs, and unresolved live availability.
Published inventory must never be presented as current availability, and an
alternative is useful only when its topology and constraints still satisfy the
trip intent.

**Acceptance scenario:** a traveler cannot obtain the preferred Yosemite
trailhead for fixed dates. Wayproof identifies other supported approaches to
the objective, shows their distinct permit products and release mechanisms,
and explains the route or effort tradeoffs without claiming that inventory is
available until it is actually checked.

**Research example:** a [planner describing repeated lottery failures, fixed
schedule constraints, fees, and conflicting referrals](https://www.reddit.com/r/Yosemite/comments/1jdqu6b/backcountry_permit_frustrations/).

### The constraint-heavy family planner

This planner is responsible for a party member whose range, carried weight,
water needs, comfort, or facility requirements materially narrow the trip.
Generic difficulty labels are inadequate: a short distance may still be steep,
water may be unavailable, toilets may be absent, and an apparently simple
destination may introduce permits, food-storage, or campsite requirements.

Wayproof should project party context onto distance, elevation, access, water,
facilities, campsite and permit requirements without turning those facts into a
generic safety score. It should keep reported capability distinct from route
facts, expose fallback and early-exit options, and explain every newly relevant
requirement.

**Acceptance scenario:** a caregiver requests a one-night trip with a short
approach, dependable water, and minimal permitting. Wayproof returns only
routes whose published distance, topology, access, and facilities can answer
those constraints; identifies requirements such as food storage; and leaves
subjective party capability for the planner to decide.

**Research examples:** the [short water-centered family trip request](https://www.reddit.com/r/norcalhiking/comments/1v1wxh3/backpacking_options_for_sacramento_area/)
and a [beginner request explicitly seeking easy access, bathrooms, and water](https://www.reddit.com/r/norcalhiking/comments/1ialcj1/short_backpacking_trip_recs/).

### The community trip-planning explainer

This ranger, guide, trip leader, outdoor educator, local expert, or experienced
community member repeatedly helps other people interpret routes, permits,
conditions, and regulations. They may already know how to answer a question,
but the answer is scattered across maps, agency pages, personal experience, and
earlier discussions. Rewriting it for every traveler is inefficient, while an
uncited summary is difficult for others to verify or reuse.

Their goals are to share a durable, source-backed explanation; direct people to
the relevant route, rule, or facility rather than a generic home page; correct
misleading advice without erasing legitimate uncertainty; and contribute local
knowledge without becoming responsible for maintaining a parallel database.
They can be an important distribution path because one trusted explainer may
introduce Wayproof to many planners.

Wayproof should support this persona by:

- providing permanent, readable links to entities, routes, claims,
  observations, evidence, and unresolved gaps;
- generating compact explanations that preserve dates, scope, attribution,
  disagreement, and items requiring a current check;
- accepting a dated textual field observation with its reported location,
  conditions, precision, and uncertainty as a reviewable contribution;
- accepting a public trip-report URL as a research reference, preserving the
  author and publication context while allowing an agent to extract candidate
  observations and evidence;
- distinguishing quotations, contributor statements, Wayproof paraphrases,
  and derived findings rather than collapsing them into one account;
- allowing contributors and maintainers to inspect, correct, reject, replace,
  or withdraw retained material through the established review workflow; and
- ensuring that neither a field report nor an extracted trip report directly
  creates a canonical claim, route relationship, or planning conclusion.

**Acceptance scenario:** an experienced hiker answers a recurring question
about a route restriction and links to a public trip report containing a dated
water observation. Wayproof preserves the report as a source, proposes the
bounded observation with its time and location qualifications, and routes it
through `Source -> Observation -> Evidence -> Claim` review. Once approved,
the explainer can share a stable Wayproof page that shows the supported answer,
the dated observation, any conflicting evidence, and what still requires a
current check.

**Research basis:** this provisional persona synthesizes behavior visible in
the public forum discussions cited by the planning personas above, where
experienced participants repeatedly interpret permit rules, recommend viable
alternatives, and report field conditions. Those discussions demonstrate a
contribution and explanation role; they do not establish contributor identity,
expert status, or the accuracy of any unreviewed statement.

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
route/access relationships into a planning context. Published segment topology
expands into ordered traversal stages with bounded distance completeness and
visible alternates, while ambiguous routes, unknown exits, and unsupported
choices remain explicit outcomes. It does not yet complete the whole product
contract. Remaining MVP work includes richer constraint resolution and
complete cost/deadline/conflict
aggregation, and completion of the legacy CLI migration onto the canonical read
service.

The read service and MCP now also expose one composed planning operation. It
resolves the intent, evaluates party/activity/equipment-dependent rules and
fulfillment coverage when a context exists, and can project explicitly selected
recheck manifests. Resolution and readiness remain distinct: for example, a
Whitney permit may be fully covered while the plan remains partial because its
segment topology is not published.

The composed plan also exposes source-backed cost, deadline, inventory,
closure, and conflict inputs through explicit semantic registration. Activity,
scope, date, and sourced relationships determine relevance. Volatile or
conflicting inputs remain visibly unresolved, and an activity-dependent fee is
not presented as owed when activity context is absent. Computing a final total,
selecting live inventory, and deciding operational deadlines remain later
readiness work.

Operational evaluation now computes a total only for unambiguous applicable
amounts, calculates structured reservation-window dates from an explicit
planning date, distinguishes published inventory from live availability, and
propagates closures and conflicts into overall planning answerability. It does
not choose vehicle/site/party fee alternatives or invent live booking status.

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
