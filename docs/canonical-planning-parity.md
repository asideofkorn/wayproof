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
would silently remove useful Sierra coverage and would present only one
direction of the completed Ohlone traverse as connected.

The default can switch when:

1. both evidenced directions of the Ohlone mainline are representable, without
   assuming that every route segment is bidirectional;
2. the Ohlone campsite reservation, dependent overnight-parking permission,
   booking calendar, site capacity, and known closed facilities are projected
   into the trip context;
3. the retained Sierra objectives either have canonical route/access knowledge
   or are explicitly declared outside the supported canonical corpus; and
4. canonical discovery replaces the useful `cli.py` inspection commands before
   the CSV data is retired.

## Retained Ohlone story

| Story | Canonical status | Evidence and remaining work |
|---|---|---|
| S1 — a traverse has two ends | Partial | `TripIntent` accepts distinct entry and exit and canonical topology produces ordered legs, scoped access, alternates, and a deliberately incomplete distance. The published graph currently connects Stanford Avenue to Lichen Bark only; the completed trip's Lichen Bark to Stanford direction fails closed. Add evidence-backed directionality instead of globally reversing edges. |
| S2 — all-in cost | Partial | Del Valle fee alternatives are projected and the evaluator refuses a false total. The actual campground, reservation, change, and western-end parking components are not all selected for this trip, so the known $97 historical total is not reproduced. |
| S3 — the scarce thing is not necessarily a permit | Partial | Camping and reservation rules can become requirements, but the Sunol backpack campsite reservation is not yet projected as the controlling fulfillment for this traverse. |
| S4 — one booking enables another | Missing canonical knowledge | Requirement/Fulfillment coverage can represent the result, but no canonical relationship says the camping reservation produces the Stanford overnight-parking permission or forbids overnight parking at Ohlone College. |
| S5 — capacity constrains the party | Partial | Party participants are first-class and Del Valle capacity rules resolve. Sunol site inventory/capacity is not yet evaluated to return sites that fit the party. |
| S6 — closed differs from absent | Partial | Dated closure inputs and current rechecks exist and distinguish an asserted closure from silence. The historical Sunol facility lifecycle facts are not yet canonical. |
| S7 — water plus last confirmation | Canonical | Dated claims and evidence preserve observations without overwriting history; route access and recheck services expose provenance and freshness. Exact route projection still depends on completing S1 directionality. |
| S8 — the objective is a route | Canonical | `TripObjective` and `TripIntent` resolve the Ohlone trail directly; no summit proxy is required. |
| S9 — campground release calendar | Partial | Deadline inputs and operational evaluation support structured booking windows. The relevant Sunol booking calendar still needs canonical knowledge and scope. |

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
