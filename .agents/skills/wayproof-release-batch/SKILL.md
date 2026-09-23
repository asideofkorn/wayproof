---
name: wayproof-release-batch
description: Deliver a bounded Wayproof code, documentation, website, or canonical-data batch through branch creation, validation, focused and full tests, GitHub PR checks, merge, main-branch verification, and Pages verification. Use when preparing or completing a PR, processing repeated autonomous batches, or confirming that canonical changes reached consumer surfaces.
---

# Wayproof release batch

## Establish a clean boundary

1. Inspect branch and worktree state. Preserve unrelated and untracked files.
2. Update from `main` before creating a focused branch. If network access is
   temporarily unavailable, do not claim the branch is current; verify before
   pushing.
3. Define one coherent outcome and its acceptance evidence.
4. Use source-ingestion and route-modeling skills first when canonical knowledge
   is involved.

## Review before publication

- Inspect the complete diff, including generated canonical records and the typed
  ChangeSet manifest.
- Confirm canonical JSON was produced by the serializer rather than manually
  edited.
- Run focused tests while iterating, then `python -m pytest -q`.
- For canonical changes, run
  `python scripts/verify_canonical_diff.py --base origin/main` on the final
  committed candidate. First refresh from current `main`, then inspect
  `git diff --name-status origin/main...HEAD`. Do not treat a check against
  `HEAD` as covering relevant uncommitted files.
- Build or exercise the website when read models, canonical data, rendering, or
  navigation changed.
- For each newly introduced entity kind, confirm whether it belongs in an
  existing generated directory. Test the generic classification so later
  entities populate automatically; never patch a single destination into nav.
- Run at least one end-to-end consumer assertion for each changed rule or
  recheck. Confirm runtime and persisted identifiers join exactly.
- For destination and route batches, exercise the practical questions promised
  by the stated coverage level: entry and parking, route reachability and
  directionality, alternatives and spurs, route-connected facilities, booking
  or permit requirements, and applicable pre-trip rechecks.
- Treat source fidelity as behavior: check that approximations, ranges,
  exceptions, time bounds, and dynamic status remain visible after serialization
  and publication.
- Do not make an existing regression test less specific to obtain a green build.
  Determine whether the new data exposes a real implementation gap, then add the
  narrowest generic support and retain the original invariant.
- Confirm no unrelated files, browser captures, copyrighted downloads, secrets,
  or local environments are staged.

## Publish through GitHub

1. Commit a reviewable diff and push the branch.
2. Open a PR describing the outcome, evidence, tests, uncertainty, and any
   intentionally unresolved gaps.
3. Wait for every required check. A PR existing is not evidence that it passed.
4. If checks fail, repair them on the same branch; do not merge around failure.
5. Merge only when the user authorized merge or an autonomous series of passing
   batches.
6. If GitHub registers the new PR head SHA but does not enqueue a check, inspect
   the workflow and run queue before taking action. A no-content trigger commit
   is acceptable only after confirming that the corrected head has no run; do
   not rerun an obsolete failing SHA and call it current verification.

## Verify publication

- Confirm the merge commit is on `main` and the main-branch tests pass.
- For website-affecting changes, confirm Pages succeeds and sample representative
  live HTML and JSON URLs.
- When a batch adds, supersedes, or preserves time-varying knowledge, verify that
  consumers can discover the supporting evidence and historical ChangeSet
  without forcing current snapshots to duplicate the full change history.
- Verify new entity kinds populate generated navigation and directories without
  hand-maintained catalogs.
- Confirm no unintended open PRs and preserve pre-existing unrelated changes.
- Begin a subsequent autonomous batch only from refreshed `main`.

## Continue versus stop

Continue through uncertainty that Wayproof can preserve as a gap, conflict,
partial result, alias, or recheck. Stop when proceeding would change product
semantics, need new authority, hide a material conflict, publish without passing
checks, or destructively affect user work.
