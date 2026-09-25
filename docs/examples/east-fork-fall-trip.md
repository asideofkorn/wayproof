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
The current comparison deliberately sorts only by sourced distance fit. It now
includes the route-depth batches added after the original trip bundle: Upper
Rock Creek Canyon, the Yost and Fern branches, and the Sabrina/North Lake
options. This makes the example an audit of the currently published trip corpus
rather than a frozen list from the first planning pass.

At the ten-mile round-trip threshold, the published corpus currently yields:

- thirteen routes with a sourced distance that fits;
- one route whose distance remains unknown; and
- three longer routes retained for comparison because the traveler may hike
  farther alone.

`Fits` describes distance only. It does not erase a route's topology gap,
source disagreement, seasonal-access uncertainty, or current-condition check.
In particular, the short Lundy option remains distance-unknown, while the McGee
beaver-pond option and Convict Lake Loop retain explicit topology gaps. Those
are honest partial answers rather than reasons to omit the choices.

The public example uses anonymous participant IDs and contains no reservation
number or private confirmation evidence. The runtime fulfillment records that
the campsite reservation requirement is covered for the two travelers and the
full stay. It is not canonical knowledge and is never promoted into
`canonical/v0`.

Pre-trip rechecks are explicitly deferred in this snapshot. A consumer should
request the relevant current-condition rechecks closer to departure rather than
interpreting their omission as confirmation that roads, fire restrictions,
weather, trail access, or facilities are current.
