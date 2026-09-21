# Canonical planning parity audit

This audit compares the canonical composed planner with the retained user
stories and planning scorecard. It does **not** require the canonical model to
reproduce CSV-era implementation details. The target is the user outcome: a
supported answer, or an explicit partial, conflicting, unknown, or
needs-current-check result.

The executable assertions are in `tests/test_canonical_planning_parity.py`.
They keep the classifications below tied to the published fixtures.

## Decision

Keep canonical planning opt-in for now. It is the correct architecture and is
already the stronger path for the fixtures it covers, but making it the default
would still silently remove useful Sierra coverage.

The default can switch when:

1. known closed Ohlone facilities are projected into the trip context;
2. the retained Sierra objectives either have canonical route/access knowledge
   or are explicitly declared outside the supported canonical corpus; and
3. canonical discovery replaces the useful `cli.py` inspection commands before
   the CSV data is retired.

## Retained Ohlone story

| Story | Canonical status | Evidence and remaining work |
|---|---|---|
| S1 — a traverse has two ends | Canonical | `TripIntent` accepts distinct entry and exit and canonical topology produces ordered legs, scoped access, alternates, and a deliberately incomplete distance in both directions. Stored `starts_at`/`ends_at` map orientation no longer implies that an ordinary official mainline is one-way; explicitly one-way spurs remain directional. |
| S2 — all-in cost | Partial | Del Valle fee alternatives are projected and the evaluator refuses a false total. The actual campground, reservation, change, and western-end parking components are not all selected for this trip, so the known $97 historical total is not reproduced. |
| S3 — the scarce thing is not necessarily a permit | Canonical | An overnight Ohlone intent activates the campsite-reservation requirement and its actionable deadline even though the trail permit is not required. |
| S4 — one booking enables another | Canonical | Stanford overnight parking is a requirement obtained through the camping reservation; Ohlone College is explicitly rejected for overnight parking. Both retain the source access-policy claim as provenance. |
| S5 — capacity constrains the party | Canonical | Route-accessible site profiles are evaluated against the supplied party size. Suitable and unsuitable sites remain distinct from live availability, which still requires a current check. |
| S6 — closed differs from absent | Partial | Dated closure inputs and current rechecks exist and distinguish an asserted closure from silence. The historical Sunol facility lifecycle facts are not yet canonical. |
| S7 — water plus last confirmation | Canonical | Dated claims and evidence preserve observations without overwriting history; route access and recheck services expose provenance and freshness. Exact route projection still depends on completing S1 directionality. |
| S8 — the objective is a route | Canonical | `TripObjective` and `TripIntent` resolve the Ohlone trail directly; no summit proxy is required. |
| S9 — campground release calendar | Canonical for the known lead time | The structured Ohlone reservation input computes the last actionable date from the published two-day minimum. Block-release calendar details remain visible source knowledge but are not yet reduced to an exact opening date when the source has not published one. |

## Scorecard outcome map

The legacy scorecard's question catalog remains useful; its mechanical proxies
do not. They inspect CSV columns and therefore cannot grade the canonical
service. The outcome-level mapping is:

| Questions | Status |
|---|---|
| Q2 route-specific permit; Q5 other end; Q6 carry/requirements; Q20 provenance; Q21 unknowns | Canonical semantics implemented, with corpus gaps surfaced rather than guessed. |
| Q7 cost; Q8 change/cancel cutoff; Q10 missed release; Q16 water; Q17 closure | Canonical operational inputs exist; completeness varies by fixture and remains explicit. |
| Q3 scarce thing; Q4 acquisition channel; Q9 party/capacity; Q15 interagency coverage | Model primitives exist in part, but adapters or canonical relationships still need work. |
| Q11 reachability; Q18 current hazards | Not yet a bounded canonical planning capability. |
| Q12 fire; Q13 pets; Q14 camping | Rules are representable and evaluated when context and scoped knowledge exist; corpus coverage is incomplete. |
| Q19 correction loop | Constrained proposals and ChangeSets replace the legacy CSV report queue; contribution UX remains M3 work. |

## Inspection and discovery disposition

Do not migrate the legacy scorecard as a second planner. Retain it only while
CSV mode remains supported. The canonical service and website already provide
entity search, typed records, provenance, ChangeSet history, and knowledge-gap
inspection.

Before the default switch, add thin CLI commands over those same canonical read
services for:

- entity search and typed lookup;
- evidence and published ChangeSet history;
- scoped knowledge gaps; and
- facility/campsite discovery once canonical capacity and access filters exist.

The legacy `report.py` mutation queue should not migrate. New contributions use
the constrained proposal service and the ChangeSet review boundary.
