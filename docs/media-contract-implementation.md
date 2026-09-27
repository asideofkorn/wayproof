# Media contract implementation — Step 5a

The media contract was accepted in [PR #196](https://github.com/asideofkorn/wayproof/pull/196).
This implements the first enforcement boundary using synthetic data. Schema v0
is still the only readable, preparable and publishable canonical version.

## Implemented boundary

- `wayproof/media_schema.py` supplies frozen public record and qualified
  time/location types. `media_contract.json` is the packaged public subset of
  the accepted contract. A test compares its shapes with the accepted proposal;
  runtime code does not import the documentation oracle or its private fixtures.
- `media_contract.decode_record()` converts closed JSON shapes into typed
  records. Its inverse produces detached values for validation, not persisted
  v1 artifacts. Source roles, original attachment order and association
  observation time, bounded inspected inputs, and exact selection/version IDs
  remain explicit.
- `ChangeSet(schema_version=1, records=MediaRecords(...))` goes through the
  existing `ChangeSetWriteService.propose/validate/explain` lifecycle. It is an
  additive draft only. Every record needs exactly one typed ADD operation at
  its derived `canonical/v1/<collection>/<id>.json` path. These paths express
  future intent; this release cannot write them.
- Ordinary v0 entity, scope, Evidence, Claim and rule validation also runs.
  The internal v0 projection is used only for those checks, never as a reader,
  export or persisted downgrade of media-derived knowledge.
- New media Observations require exact provenance and matching source/analyst
  attribution. Claims still cite only Evidence IDs. Unknown capture dates stay
  unknown, partial inspection stays bounded, and unselected findings cannot
  supply location/time assertions. Legacy baseline IDs come from the repository,
  not an input flag; artifact reference strings remain untouched.
- Proposed selections and legacy mappings must name their containing ChangeSet.
  There is **no caller-supplied list of approved ChangeSet IDs**. `VALIDATED`
  means structurally representable intent, not maintainer approval or permission
  to process/release media. The `reviewer_role` and `reviewed_at` fields in a
  draft are proposed metadata; they do not authorize anything.
- `prepare`, ChangeSet serialization, candidate storage, and publication checks
  reject v1 regardless of caller-provided status/metadata. Existing v0 consumer
  proposals reject extended containers/records rather than dropping fields.
  V0 candidate storage preflights the entire candidate before writing paths.

There is no media acquisition, model call, processor, public renderer or new
MCP tool. Constructing a typed draft does not run a media pipeline. The private
custody/permission example from Step 4 is deliberately **not** a runtime grant
or a newly implemented private store.

## Reader and publication capability gate

`load_canonical()` checks the existing versioned directory contract in both
`canonical/` and `changesets/` before loading data. Only the supported v0
collections and JSON artifact layout are allowed. Unknown version directories,
unknown collections, unsupported envelopes and extra record fields fail with
`UnsupportedSchemaError`; no new root manifest format is introduced.

The shared read service, canonical CLI (including JSON output), MCP startup and
site builder all use that gate. The site validates before writing export files.
The publication verifier also rejects unsupported paths, even if a diff has no
v0 canonical changes. A published ChangeSet cannot be modified or removed.
Ordinary code/docs paths and the separate legacy CSV planner are unaffected.

V0 serialization stays byte-compatible. Pre-gate binaries are not made safe by
this change: upgrade them before any future activation, or keep them on a pinned
legacy snapshot. Current code rejects all v1 repositories; it cannot claim a
partially loaded v1 dataset is a complete v0 answer.

## Revised delivery scope after Step 5a

The maintainer selected a [public-source, reference-only launch](public-source-research-plan.md).
Step 5a remains implemented and v1 activation remains disabled. The next gates are:

1. Enforce a narrow public-source/no-retention policy, including removal of
   retained links, summaries, findings, and dependent support. Prefer official
   accounts; reject private/login-only sources, personal-data harvesting, EXIF,
   sensitive-location inference, and retained source media or derivative files.
2. Complete separately reviewed v1 migration/storage routing and shared consumer
   compatibility, including changed/unavailable/removed inputs and unsupported
   answers. Legacy references remain unverified strings; no silent downgrade.
3. Activate v1 only for reviewed reference-only provenance after those gates pass.
4. Add bounded processing and immutable runs with demonstrated transient-input
   handling and untrusted-input isolation. Reprocessing never publishes or selects
   its own findings, resolves gaps, creates relationships, or changes plans.

Private custody storage, contributor accounts/uploads, private-media controls,
complex provider authorization, and raw-media/derivative-file deletion are
explicitly deferred until those inputs or retained artifacts are in scope.
No-retention does not remove the obligation to withdraw retained summaries and
findings, reevaluate Evidence/Claims, and update owned projections. The initial
policy must be enforced, not claimed from a caller's permission flag. Current
runtime v1 prepare/write/publish rejection stays in place until activation review.

## Public-research policy follow-up

The [reference-only enforcement boundary](public-research-enforcement.md) adds
policy assessment and removal of owned research drafts to the existing write
service. Structural validation remains distinct from policy/review authority.
V1 prepare/write/publish rejection remains unchanged; live removal/consumer
integration is still part of the next separately reviewed migration stage.
