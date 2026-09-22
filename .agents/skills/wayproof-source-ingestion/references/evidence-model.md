# Evidence-model reminders

Read `ARCHITECTURE.md` for the authoritative design. Use this checklist while
authoring a batch.

```text
Source -> Observation -> Evidence -> Claim -> Rule/DerivedResult
```

- A `Source` identifies the publisher and artifact; it is not a universal
  authority ranking.
- An `Observation` preserves what a source or reporter stated or encountered,
  including its date and context.
- `Evidence` links an assertion to the material that supports it.
- A `Claim` is atomic and explicitly scoped in space, time, activity, party, or
  equipment where applicable.
- A `Rule` expresses normative or evaluative behavior with applicability and
  requirement semantics.
- A `DerivedResult` records domain-owned computation or resolution. Do not
  silently promote it into source fact.

Required distinctions:

- unknown != unavailable != closed != absent != not applicable;
- current real-world evidence != Git publication history;
- source disagreement != textual variation;
- a missing value != a negative assertion;
- facility inventory != live availability;
- location proximity != route access;
- source retrieval date != condition start date.
- approximate value != exact value;
- a recorded current-condition gap != a consumer-visible pre-trip recheck;
- a persisted rule != a rule proven to apply to normal trip input;
- a similarly named runtime requirement != the same canonical requirement.

Preserve history through dated claims and observations. Preserve publication
intent through permanent ChangeSets. Never rewrite an older observation merely
because a newer condition is available.

Examples:

- Model Shadow Cliffs Lake and Shadow Cliffs Arroyo separately when the source
  publishes different water-quality statuses.
- Keep `Eyrie` and `Aerie` as aliases when evidence shows they identify the same
  camp.
- A personal report that water flowed on a particular day is dated evidence,
  not a timeless guarantee.
- A Google Maps pin can support approximate identity or geometry while an
  official operating rule remains sourced to its publisher.
- "Nearly 1,200 square miles" should retain an approximation marker; storing
  exact `1200` silently adds certainty not present in the source.
- A current-conditions page should normally support a recheck topic and source
  pointer rather than a timeless assertion of whatever it said at ingestion.
