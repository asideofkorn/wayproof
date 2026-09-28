# V1 migration and consumer compatibility — staged review

This implements an isolated migration rehearsal using synthetic acceptance data.
Production readers, writers, CLI/MCP entry points, publication CI and the site
builder still reject v1. No production repository is migrated by this PR, and
no media is acquired, processed, retained, or rendered. Approval of this change
is not approval of a media source or authorization to activate processing.

## Storage and rollback

`MigrationWorkspace.stage` validates an additive v1 ChangeSet against a fully
validated v0 repository, rechecks the narrow public-research policy, and writes
to a separate owned directory outside that repository. Existing v0 files and
ChangeSets are copied **byte for byte**, including their original whitespace.
IDs and legacy `artifact_refs` are not interpreted or rewritten.

New records use the existing artifact envelope with `schema_version: 1` under
`canonical/v1/<collection>/<id>.json`; the staged ChangeSet uses
`changesets/v1/<id>.json`. Production `write_candidate` remains disabled for v1.
The separate `migration.json` is a rehearsal/control manifest, not a new
canonical record or an approval grant. It records source/target versions,
baseline path/digests, permitted collection counts, identity mappings, original
record order, output path/digests, the text packet, review receipt, and rollback
behavior. Digests identify repository metadata, never media content.

Repeated staging of identical input is byte-identical and idempotent. Existing
nonidentical directories are not overwritten. Reload verifies the complete file
inventory and digests, version envelopes, identities, counts, structural graph,
exact research fingerprint and independently resolved workflow authority before
returning content. Rehashing tampered records cannot bypass the review binding.

Rollback removes v1 routing after withdrawing its retained payloads and returns
the unchanged v0 baseline. The minimal withdrawal marker remains, and the same
workspace cannot restage an old receipt and resurrect the withdrawn batch.
Rollback does not restore research payloads. Workspaces are serialized operator
jobs, not a concurrent database or an archive of historical media snapshots.

## Review authority

`ReviewReceipt` contains only a PR number, exact head commit and review-blob path.
The source repository, checkout, base branch and workflow adapter are trusted
application configuration, not fields accepted from research submissions.

`GitHubResearchReviews.resolve` checks the configured GitHub repository and base,
merged PR identity, current-head approval by a non-author with the `admin` or
`maintain` role, subsequent dismissal/change requests, and merge ancestry in the
locally fetched `origin/main`. It then reads the exact reviewed Git blob at
`research-reviews/<fingerprint>.json` and decodes the closed `ContentReview` shape.
That document supplies reviewed facts; **its mere existence, or its `accepted`
field, supplies no authority**. API errors, missing Git objects, stale approvals,
unknown roles, or mismatching fingerprints deny the read. There is no automatic
fetch of the checkout and no source/media fetch. Tests replace the GitHub/Git
transport with synthetic responses; they do not call GitHub or media providers.

GitHub's `role_name` is used because the legacy `permission` field maps maintain
to write; see the [GitHub collaborator-permission API](https://docs.github.com/en/rest/collaborators/collaborators#get-repository-permissions-for-a-user).
Maintainer identities are used only for authorization and are not copied into
public evidence projections. Serialized proposal flags cannot become review
receipts or trusted facts. Review artifacts themselves remain subject to the
same removal obligations as any retained source references; this rehearsal does
not claim to rewrite remote Git history or erase third-party copies.

## One projection, explicit unsupported answers

`MigrationReadService.evidence_detail` follows typed dependencies from a durable
record ID. An Observation's selected statement/finding, version, attachment,
qualified dates/locations, analysis bounds, uncertainty and rendition labels are
preserved in the returned lineage. Multiple observations and runs remain distinct;
the projection never chooses a newer run or substitutes publication for capture.

A missing/tombstoned dependency, an unavailable version report, failed eligibility,
or withdrawal makes the dependent claim **unsupported**, even if another cited
Evidence remains available. Unsupported results retain IDs and an explanation,
but expose no old payload or claim value. They do not choose replacement support.
Dated availability reports remain assertions, not guarantees of current state.

The existing HTML evidence renderer and MCP `get_evidence_detail`/`explain_claim`
adapters consume this same model. JSON is its serialization. Staged read handles
reload on every request so a handle opened before withdrawal cannot return a stale
supported answer. V1 planning fails with a named unsupported-schema error; it does
not fall back to a partial v0 plan. Production entry points remain disabled until
the separate activation review selects the supported reference-only route.

## Executed removal and generated outputs

Withdrawal conservatively removes the **whole additive research batch**, including
its sources, statements, analysis text, text packet and ChangeSet prose. It leaves
only IDs, non-sensitive migration digests and receipt pointers. This intentionally
withdraws more than the minimum dependency closure; choosing surviving support is
a later reviewed ChangeSet. Existing v0 content requires its own reviewed v0
correction/removal and is never modified by migration rollback.

The workspace owns an `outputs/` directory. Export replaces it in full, removing
obsolete files, and generates evidence HTML, JSON, MCP response snapshots, a
search index, a cache with all plans invalidated, and a replacement offline
manifest with content digests. Actual MCP requests use the same refreshed service;
MCP snapshots are acceptance artifacts, not a second server implementation.
The manifest identifies replacement of the preceding offline generation; it
cannot delete a copy already downloaded to someone else's device.

A removal hold denies reads during deletion. No original-payload backup is kept.
An interrupted hold can be resumed by calling withdrawal again; reads remain
blocked until deletion finishes. Tests inspect
the regenerated files and retained read handles, inject stale output/cache/index
files, and search all owned artifacts for removed links/text. This is executed
custody removal for the workspace, not merely an impact-plan return value.

## Compatibility and activation boundary

The minimum supported older reader is the root-capability-gate release introduced
in PR #197. It rejects the staged v1 directory before loading v0. Pre-gate binaries
cannot be retroactively repaired; they must be upgraded or pinned to the original
v0 snapshot, and must never be pointed at an activated mixed-version repository.

This PR supplies a staged storage/projection/removal path for review. The activation
PR must explicitly wire only that reviewed reference-only path into production
routing and publication, keep broader schema capabilities inaccessible, and retain
the full consumer and removal acceptance cases. It must not introduce downloads,
processors, new review authority, or automatic claim/selection/planning changes.
