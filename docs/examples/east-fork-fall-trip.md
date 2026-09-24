# East Fork fall trip input bundle

[`examples/trips/east-fork-fall-2026.json`](../../examples/trips/east-fork-fall-2026.json)
is a noncanonical consumer example for a real, bounded trip. It composes two
existing read operations instead of creating a second planning model:

1. `plan_trip` evaluates the booked campsite, party coverage, camping context,
   and canonical operational inputs.
2. `compare_hikes` evaluates an explicitly selected set of route IDs against
   the traveler's ten-mile round-trip limit while preserving source claim IDs,
   knowledge gaps, and current-check flags.

The bundle retains user-supplied travel context for presentation but does not
claim that Wayproof has computed or sourced the Oakland–Tioga Pass drive. The
fall-foliage goal is likewise a preference, not a canonical foliage ranking.
The current comparison deliberately sorts only by sourced distance fit.

The public example uses anonymous participant IDs and contains no reservation
number or private confirmation evidence. The runtime fulfillment records that
the campsite reservation requirement is covered for the two travelers and the
full stay. It is not canonical knowledge and is never promoted into
`canonical/v0`.

Pre-trip rechecks are explicitly deferred in this snapshot. A consumer should
request the relevant current-condition rechecks closer to departure rather than
interpreting their omission as confirmation that roads, fire restrictions,
weather, trail access, or facilities are current.
