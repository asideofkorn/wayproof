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

## Remaining gates before activation

1. Implement separate private custody, authenticated review/policy, acquisition
   classification, consent and permitted-use/provider controls. Enforce content
   minimization, EXIF and sensitive-location/person protections, and isolate
   untrusted media/OCR from tools and secrets. Structural location checks alone
   do not perform privacy screening.
2. Implement retention, redaction/removal and dependent-answer reevaluation
   across retained inputs, findings, Evidence/Claims, indexes, caches, exports
   and offline manifests. Core-record tombstones and non-additive v1 operations
   remain disabled until that workflow exists; draft media tombstones describe
   unavailable dependencies, not an implemented takedown operation.
3. Separately review serializer/storage routing, migration dry runs, authenticated
   selection of previously published v1 records, exact publication-diff
   verification, and shared consumer projections. Remove the hard activation
   rejection only with evidence that all required gates work together.

Only then can bounded ingestion and immutable reprocessing begin. Reprocessing
must never publish, resolve gaps, add relationships, change plans, or select its
own findings without the separate reviewed ChangeSet/publication workflow.
