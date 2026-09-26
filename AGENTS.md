# Wayproof agent instructions

These instructions apply to the entire repository.

## Start here

Before changing product semantics, canonical knowledge, or publication behavior,
read `PRODUCT.md`, `ARCHITECTURE.md`, and the relevant milestone in `ROADMAP.md`.
Read `README.md` for current commands and implemented surfaces. Preserve unrelated
worktree changes and never assume an untracked file is disposable.

Use the repository workflow matching the task:

- Source-backed additions or corrections:
  `.agents/skills/wayproof-source-ingestion/SKILL.md`
- Access points, routes, segments, alternatives, or traversals:
  `.agents/skills/wayproof-route-modeling/SKILL.md`
- Branch, test, PR, merge, and deployment work:
  `.agents/skills/wayproof-release-batch/SKILL.md`

When a task spans these areas, follow the skills in that order. Read only the
referenced supporting material relevant to the task.

## Non-negotiable boundaries

- Canonical Schema v0 remains the implementation contract until a separately
  reviewed schema migration changes it.
- Canonical JSON is serializer-owned. Do not hand-edit files under
  `canonical/v0/` or `changesets/v0/`.
- Create knowledge through the domain write boundary and a validated ChangeSet.
  Storage is not the write API.
- The lifecycle is DRAFT -> VALIDATED -> prepared candidate -> GitHub review ->
  merge to `main` as PROMOTED/PUBLISHED. An agent must not bypass validation or
  directly promote knowledge.
- GitHub supplies approval and publication. MCP, CLI, website, and importers are
  adapters over domain services and must not introduce another mutation path.
- Never infer route access, membership, or traversal from proximity alone.
- Missing evidence is `unknown`, not evidence of permission, availability,
  absence, closure, or safety.
- Preserve conflict, uncertainty, provenance, temporal scope, geospatial scope,
  and superseded historical evidence. Do not replace an unknown event date with
  a retrieval date.
- Check summaries, tables, FAQs, expandable sections, and linked detail pages
  for internal disagreement. If one authoritative source conflicts with itself,
  preserve both statements and expose the conflict as a consumer-visible gap or
  recheck; never silently select one statement.
- Decompose composite prose into atomic observations and claims. Keep source
  statements distinct from derived results and normative rules.
- Dynamic conditions require retrieval context and an appropriate pre-trip
  recheck; do not make volatile status timeless.
- Preserve source precision. Approximate, bounded, qualified, and seasonal
  values must remain approximate, bounded, qualified, and seasonal in canonical
  records and consumer output.
- Reuse the vocabulary and identifiers exercised by domain services. A
  schema-valid rule that cannot fire for normal `TripIntent` input, or whose
  generated requirement identifier differs from its persisted requirement, is
  not complete.
- Do not invent unresolved representation or infrastructure decisions, including
  new serialization formats, module layouts, enum spellings, or database timing.
- Apply the source and licensing policy in `DATA_LICENSE.md`. Do not commit
  copyrighted source artifacts merely because they were available for review.

## Change and verification rules

- Keep each PR bounded to one coherent outcome.
- A canonical-data PR introduces exactly one new ChangeSet. Corrections made
  before merge belong in that original ChangeSet; create a follow-up ChangeSet
  only after the earlier one has been published on `main`.
- Add focused regression tests for changed behavior or new canonical coverage.
- Verify consumer behavior, not only record existence: exercise rule evaluation,
  answerability/rechecks, generated directories, detail pages, and identifier
  joins affected by the batch.
- Extend generic publication logic for a generally supported entity kind. Do not
  add destination-specific navigation exceptions, and do not weaken an existing
  invariant merely to admit new data.
- Run `python -m pytest -q` with the repository's supported Python 3.14 runtime.
- During iteration, run the affected CI module with
  `python scripts/test_groups.py --group <group>`. The five exhaustive groups
  are `core`, `planning`, `regional-ebrpd`, `regional-sierra`, and `site`;
  `python scripts/test_groups.py --check` verifies that every test module is
  assigned exactly once. A new planning, regional, or site-building test module
  must be classified in `scripts/test_groups.py`; otherwise it deliberately
  defaults to `core` so CI cannot omit it. Tests that inspect generated website
  output must use the session-scoped `generated_site` fixture instead of
  rebuilding the site themselves.
- For canonical knowledge changes, also run:
  `python scripts/verify_canonical_diff.py --base origin/main`.
  Run it on the final committed candidate after refreshing from current `main`,
  and inspect `git diff --name-status origin/main...HEAD`; relevant uncommitted
  canonical changes are not covered by a `HEAD` comparison.
- Documentation, tests, and rendering changes do not require a ChangeSet when
  canonical knowledge is untouched.
- Merge only after required checks pass. After a knowledge or publishing change,
  verify the main-branch tests, Pages deployment, and representative live HTML
  and JSON output.
- Generated directories and destination pages must derive from canonical read
  services. Do not create a hand-maintained parallel website catalog.

## Working with uncertainty

Continue when uncertainty can be represented safely as a dated observation,
explicit gap, conflict, alias, partial topology, or value requiring recheck.
Stop for maintainer direction only when proceeding would change product
semantics, require new authority, conceal a material conflict, or perform an
unsafe/destructive action.
