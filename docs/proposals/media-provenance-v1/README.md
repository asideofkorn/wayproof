# Media provenance v1 — schema and migration review

**Status: Accepted for implementation; v1 activation is disabled.** The separate
schema-review gate required by [ADR 0004](../../adr/0004-repeatable-media-analysis.md)
was accepted with [PR #196](https://github.com/asideofkorn/wayproof/pull/196)
on 2026-09-27. Acceptance does not authorize media ingestion or certify privacy
and deletion controls. All examples are synthetic; `example.invalid` is not fetched.

Step 5a implements typed public records and structural ChangeSet draft validation
in `wayproof/`, plus a repository capability gate. V0 published bytes and record
shapes remain unchanged. V1 preparation, persistence and publication are disabled.
See [implementation boundaries](../../media-contract-implementation.md) for what
is implemented and what must pass review before activation.

The review question is: **Can each published media-derived claim be traced to
the exact reviewed statement/finding, exact inspected version and attachment,
through typed Observation and Evidence, without an alternate support path?**
An unavailable/redacted origin must instead produce an explicit limitation or
unsupported result. Traceability is not a finding that a claim is true, current,
independently corroborated, or safe for a trip.

## Review package and authority

- [schema.json](schema.json) defines closed JSON record shapes and wire spellings
  accepted for implementation. The public subset is packaged with the runtime;
  its public/private bundles are **test containers**, not a new persisted snapshot format.
- [collections.json](collections.json) maps these fixture collections to record
  types. The new types, v1 Source role, and two v1 Observation fields are the extension;
  the four existing types included in the fixture are not a replacement for
  the full v0 schema, domain validators, or predicate vocabulary.
- [synthetic-public.json](synthetic-public.json) contains one source attachment,
  a separately attributed clarification, and one visual-analysis lineage.
- [synthetic-private.json](synthetic-private.json) illustrates a **different
  operational store**. It is safe to commit only because it is wholly synthetic.
  Its shape is never an invitation to put real operational records in Git.
- [synthetic-read-model.json](synthetic-read-model.json) is the detached trace
  expected from the public example.
- [reference_validator.py](reference_validator.py) is a test-only design oracle.
  Production code never imports it. It validates JSON and references, checks
  hypothetical transitions, and computes a removal-impact set in memory.
  It does not download, process, publish, persist, delete, authenticate reviewers,
  enforce permissions, verify consent, or purge a cache.
- [Synthetic tests](../../../tests/test_media_provenance_proposal.py) exercise
  that oracle. They use the explicit `jsonschema` dependency, and make no media/network/model requests.

Record definitions below and the JSON schema must be reviewed together. Any
changed spelling or invariant requires updating examples and tests. Draft domain
integration is implemented in Step 5a. Schema activation, storage migration, real lifecycle enforcement, and source acquisition remain later
reviews with their own acceptance evidence.

## Initial implementation scope amendment — 2026-09-27

The [public-source, reference-only plan](../../public-source-research-plan.md)
narrows the first activation to publicly accessible links and bounded factual
summaries/provenance, with no retained media or derivative files. Private custody,
accounts/uploads, private-media controls, complex provider authorization, and
retained-media cleanup are deferred. This does not change the accepted record
shapes or activate v1. Policy must reject out-of-scope uses of the broader schema.

The private store and lifecycle below describe the broader future scope, not a
requirement to create custody records for every public reference. The initial
scope still needs enforceable source/content rules, human PR review, removal of
retained links/statements/findings and dependent support across owned outputs,
explicit changed/unavailable versions, and untrusted-input isolation. Synthetic
private fixtures and permission flags are not runtime authorization.

## Public and operational/private separation

This proposal selects a **public, minimized canonical corpus** and a physically
and logically separate **private operational workspace**. An access flag on a
record inside public Git is not separation. A combined dump is forbidden.
No private path, storage locator, consent/removal case ID, provider credential,
original filename, content hash, raw EXIF, precise sensitive coordinate, private
speaker identity, or private request detail enters public canonical records,
ChangeSet reasons, CI logs, read indexes, exports, or Git history.

| Public canonical record | Private operational counterpart |
|---|---|
| Opaque asset/version identity; approved dimensions/duration; identity limitations | Permitted digest and permission basis; private storage locator; restricted metadata |
| Approved source locator and minimum necessary speaker attribution | Acquisition context, actual contribution/permission evidence, access roles and review records |
| Bounded approved statement or finding; method/version without secrets | Raw inputs, full OCR/transcript if justified, prompts/configuration containing secrets, working copies and logs |
| Qualified, approved/generalized time and location | Approved EXIF fields and precise restricted location, only when necessary |
| Minimal removal/redaction tombstone and unsupported answer | Requester/contact, retention deadlines, deletion tasks, private decision evidence and verification receipts |

Public Source locators and free text can themselves identify people or expose a
sensitive place. A closed schema does **not** detect that. Step 5 must inspect
content and outbound links, authenticate release review, minimize attribution,
and block unsafe publication. Hashes stay private even when hashing is permitted;
public identity and lineage never depend on exposing a hash. No binary store,
provider, secret store, retention duration default, or database is selected here.

The private example's `custody` records require an owner, purpose, acquisition
class, explicitly permitted uses/destinations, contribution scope when applicable,
retention deadline, access roles, and release-review disposition. Public access
is not permission. `permitted_uses` and `release_review` in a fixture are test
assertions, **not authenticated grants**. Step 5 must derive them from actual
reviewed authority rather than trust a submitted boolean or enum.

## Record definitions

All new IDs are opaque Wayproof-allocated UUIDs. Fixture UUIDs are deliberately
predictable for readability; real IDs must not encode account names, filenames,
URLs, hashes, or coordinates. Existing v0 IDs are not rewritten. New records use
`id` and `state: active` plus the exact fields below. All fields are required;
`null` means the specific not-applicable/unknown case described, not an inferred
value. Arrays preserve uncertainty or multiplicity rather than selecting the
first element. Unknown fields are rejected.

Each new record also has a closed tombstone alternative: `id`,
`state: removed | redacted`, `reason_code: privacy_removal | retention_expired |
source_withdrawn`. No original payload, hash, private reference, coordinates,
filename, identifying reason text, or hidden metadata survives in that variant.
For the fixture's existing types, the equivalent tombstone uses their existing
ID field. A legacy ID that itself identifies someone must be withdrawn/re-keyed
with any linking map retained privately; preserving its URL for auditability
cannot override removal. That exceptional migration needs separate review.

| Accepted type | Exact active payload fields (besides `id`, `state`) |
|---|---|
| `media_asset` | `origin_asset_id: UUID|null`, `origin_statement_id: UUID|null` |
| `media_version` | `asset_id: UUID`, `media_type: image|video|audio`, `dimensions: {width,height}|null`, `duration_ms: positive integer|null`, `retrieval_time: Time`, `identity_basis: permitted_digest|provider_version|reviewed_copy|unverifiable`, `reproducibility: bounded|unavailable`, `limitations: string[]` |
| `availability_report` | `media_version_id: UUID`, `checked_at: Time`, `availability: available|unavailable|unknown`, `limitations: string[]` |
| `source_attachment` | `source_id: Source ID`, `asset_id: UUID`, `media_version_id: UUID`, `ordinal: positive integer|null`, `ordinal_basis: source_order|unknown`, `publication_time: Time`, `association_observed_time: Time` |
| `attributed_statement` | `source_id: Source ID`, `statement_kind: caption|comment|correction|clarification`, `speaker: {role: author|commenter|unknown, attribution: string|null}`, `text: bounded string`, `publication_time: Time`, `corrects_statement_id: UUID|null` |
| `statement_mapping` | `statement_id: UUID`, `mapping_kind: single|multiple|ordered_item|ambiguous`, `attachment_ids: UUID[]`, `list_item: positive integer|null`, `basis: string`, `certainty: explicit|ambiguous|unresolved` |
| `analysis_run` | `source_id: Source ID`, `inputs: Target[]`, `analyst: {kind: human|tool|model, label, version}`, `method: {name, version, configuration_summary}`, `analysis_time: Time`, `modalities: Modality[]`, `limitations: string[]` |
| `analysis_finding` | `run_id: UUID`, `target: Target`, `modality: Modality`, `metadata_fields: (capture_time|gps)[]`, `content: bounded string`, `certainty: observed|asserted|inferred|unresolved`, `corroborating_evidence_ids: Evidence ID[]`, `limitations: string[]` |
| `reviewed_selection` | `origin: {kind: statement|finding, id: UUID}`, `mapping_id: UUID|null`, `media_version_ids: UUID[]`, `reviewer_role: maintainer`, `reviewed_at: Time`, `change_set_id: reviewed ChangeSet ID` |
| `observation_provenance` | `observation_id: Observation ID`, `selection_id: UUID`, `event_times: Time[]`, `locations: Location[]` |
| `legacy_artifact_mapping` | `observation_id: Observation ID`, `artifact_ref_index: nonnegative integer`, `asset_id: UUID`, `media_version_id: UUID`, `reviewed_selection_id: UUID`, `migration_id: reviewed migration ID` |

`bounded string` is purpose-minimized text, not a universal character-count
privacy rule. Field content budgets must be specified per processing purpose
and enforced in Step 5. UUID arrays requiring at least one item and numeric
bounds are formalized in the schema. v0 Source/Observation/Evidence/Claim shapes
remain governed by the existing schema; their fixture definitions only exercise
the lineage, not all other v0 entity/scope validation.

### Asset, version, and attachment identity

An asset is a logical item, such as a reviewed identification of attachment 3.
Neither the same URL nor equal bytes proves logical identity. Changed bytes at
the same URL require a new version; if continuity of the logical attachment is
uncertain, use a separate asset pending review. Hash matching cannot establish
author, capture time, location, or independent corroboration.

The private custody record binds a permitted digest to exactly one version;
changing a digest under that version, even by replacing the custody ID, is
invalid. A separately reviewed removal can erase that binding, never replace
it with different bytes. A nullable private storage locator records that no
copy is retained. Relocating storage does not change the inspected identity.

An attachment is the immutable association of a Source, asset, inspected version,
and **original** ordinal. Order is absent from the reusable asset. A later
retrieval/reorder/replacement creates another association; old mappings stay
pinned to old association IDs. A known `ordinal` requires `source_order`; an
unknown ordinal stays null. A source without stable ordering must not acquire
an order from the current UI. Source URLs may be identical across versions.

`association_observed_time` records when this source-to-version association and
order were observed, with its own qualified basis. It is distinct from the
post's publication time, the version's retrieval time, and media capture time.
Reordering unchanged media appends another dated association without changing
the version, old order, or pinned mappings. Unknown observation times stay
unknown; consumers cannot infer an ordering chronology from publication time.

Versions carry retrieval context; availability is a separate **dated assertion**
so a remote disappearance does not mutate a version or retroactively erase an
inspection. Multiple availability reports are shown with their check times.
They are not a guarantee of current availability. `unverifiable` input identity
and inability to retain originals must be explicit reproducibility limitations.

A supported repost names an origin asset and the statement establishing that
relationship. The origin graph must be acyclic. Shared-origin grouping prevents
reposts or repeat analysis being counted as independent field reports. Separate
asset IDs with unknown origins still do **not** prove independence.

### Statements and mappings

Each comment has its own Source locator, not merely its parent's post URL.
The speaker is stated explicitly or remains unknown; it is never inherited
from Source.publisher or the parent uploader. Corrections append new statements
and refer to the earlier statement. No identity enrichment/profile harvesting
is authorized. Public attribution must pass the separate release review.

Single mappings name one attachment; multiple mappings name more than one.
Ordered-item mappings preserve the list item number and original attachment IDs.
Ambiguous/unresolved mappings can remain as research context, but cannot be
selected as exact media support for a published Observation. A later resolution
creates a new mapping and separately reviewed selection; it does not rewrite
which attachment an earlier reviewer inspected.

### Runs and findings

`Modality` is `visual | ocr | transcription | location_inference | metadata`.
A `Target` contains **both** `media_version_id` and `source_attachment_id`, plus
one selector. The attachment must resolve to the named version. This pins the
original source association used in the inspection, without expanding all
claims or attachments sharing a source/version. The inspector may not replace
that association with a different repost after review.

Selectors are closed variants:

- `whole`: one image; not shorthand for unknown-duration video/audio.
- `image_region`: nonnegative x/y and positive width/height in input-version pixels.
- `time_range`: integer `start_ms`, `end_ms`, a half-open interval within the known duration.
- `frames`: explicit video presentation timestamps in milliseconds, within duration.

A finding's selector must be contained by a corresponding inspected selector
on the same version **and attachment**. Sparse frames cannot become a continuous
range; two seconds cannot become the full clip. Coordinate orientation and
video timestamp interpretation must be part of the versioned method description.
No inferred scene-wide or route-wide condition follows from a bounded finding.

The accepted v1 Source adds `source_role: original|comment|analysis_report` to
the existing Source fields. Legacy Sources remain valid without a role, but
cannot serve as analysis-report Sources. A run's Source must carry
`source_role: analysis_report`; original attachments and attributed statements
cannot use that role. A removed Source remains an unavailable
dependency, never a way to recover attribution from another Source.

Roles cannot be changed on an existing Source, even with a reviewed transition;
a removed Source ID cannot be reused to evade that restriction.
Allocate a distinct analysis-report Source instead of relabeling an uploader,
commenter, or unclassified legacy Source. Step 5 must enforce role allocation
and acquisition classification at the domain write boundary; these synthetic
roles are not authenticated identities or implemented ingestion controls.

An analysis Observation uses the run's analysis-report Source and analyst
attribution; the trace also includes the original source through the pinned
attachment. Statements instead preserve their own speaker and source.

Runs record a method and configuration summary/version in addition to the model
name. Secrets and private prompts never enter the public summary. Missing
configuration/input retention limits reproducibility; no bit-for-bit claim is
made. Findings are bounded results, never Claims, and corroborating references
must resolve typed Evidence without a support cycle. Metadata extraction names
only permitted fields and requires a private purpose/permission review.

## Qualified time and location

`Time` is reused for publication, retrieval, analysis, review, and event/capture
roles. The **containing field determines the role**; no role is a fallback for
another. Its exact variants are:

| `kind` | Value fields | Qualification |
|---|---|---|
| `unknown` | No timestamp/value | `certainty: unknown` |
| `instant` | `value`: timezone-qualified ISO 8601 instant | `certainty: exact|asserted|approximate` |
| `date` | `value`: ISO date, no invented midnight or zone | same |
| `range` | `start`, `end`, `precision: date|instant`; ordered inclusive bounds | same |

Every value has `basis: {kind: statement|finding|source|clock|unknown, ref}`.
Only `clock` and `unknown` have null refs. Other basis refs must resolve to the
specified type. Qualification describes the reported value, not verified truth;
an EXIF value or author assertion must retain its source and uncertainty.
Approximate/asserted dates are not converted into exact timestamps. Conflicting
author and EXIF assertions are separate attributed Observations/selections.

Event/capture assertions and location assertions on an Observation must name
**its selected** statement or finding, or remain unknown. Attaching an unselected
finding as an annotation would bypass reviewed selection and is rejected.
Publication time cannot fill missing capture time. Date resolution cannot supply
location. New media observations do not populate v0's bare datetime fields by
fallback; the qualified representations are authoritative for v1 consumers.
The only allowed `observed_at` compatibility projection for a new media
Observation is one exactly matching its single, exact event instant. Date-only,
approximate, asserted, conflicting, or unknown event times leave it null.

`Location` includes all of:

- `basis_kind: author_labeled|visible_sign|corroborated|exif_permitted|inferred|unresolved`;
- `value`: null, `{kind: entity, entity_id}`, `{kind: region, label}`, or a bounded
  latitude/longitude point;
- `precision_m`: positive resolution/uncertainty distance when applicable, else null;
- `generalization: exact|generalized|withheld|unknown`;
- `sensitivity: nonsensitive|sensitive|unassessed`;
- typed `basis` and `limitations`.

Author labeling requires the selected statement; sign/corroboration/inference
requires the selected finding; EXIF location additionally requires the `gps`
metadata permission. Corroboration must name separately reviewed Evidence,
not the same finding's own derived claim; typed references and cycle checks
alone do not establish independent origins. A sign requires a visual/OCR
finding. Unresolved means no location value.
Sensitive/unassessed points or entity identifiers cannot be public; use null or
an approved generalized region. The private workspace may retain more precision
only when expressly permitted. A broad region label itself still needs review.
There is no automatic geocoding, EXIF extraction, or sensitive-location detector
in this proposal.

## Observation, Evidence, review, and reads

Accepted **new v1 Observations** add `origin_kind: source_text|media_statement|
media_analysis` and `provenance_id: UUID|null`. Existing v0 records remain
byte-for-byte unchanged and are recognized from the migration baseline, not
from a user-supplied `legacy=true` flag. Source-text observations have no media
provenance. New media observations require a reciprocal, unique
ObservationProvenance record and a matching selected origin kind.

Readers follow the Observation's declared `provenance_id` directly, including
when the target is a tombstone. They must not rediscover this edge by scanning
active provenance backlinks. A tombstoned provenance, selection, finding, or
version makes the trace explicitly unavailable. Missing targets invalidate the
bundle; a defensive read projection also reports them as unavailable. Neither
case can downgrade a media observation into `legacy_source_only` support.

Step 5 must prevent media processing outputs from falsely entering a source-text
writer path. Neither a string marker nor these tests can determine whether an
operator lied about how text was acquired. Acquisition classification, policy,
authority, and reviewed typed operations must all be enforced at the write
boundary. All ordinary v0 validators and predicate-specific value validators
continue to apply; media origin is not a way to avoid them.

The selected origin and version set must match exactly. A statement selection
requires an explicit mapping of that same statement. A finding selection names
its exact version and no author mapping. Selections are immutable and may only
be introduced with a separately reviewed ChangeSet. The oracle receives fake
review receipts as **test inputs**; it does not authenticate a maintainer or
replace GitHub review/publication.

```text
Original Source -> SourceAttachment -> exact MediaVersion
                                     <- AnalysisRun -> AnalysisFinding
Wayproof analysis Source -> Observation -> Evidence -> Claim
                                 |
                                 +-> ObservationProvenance -> ReviewedSelection
                                                               -> exact Finding
Author/comment Source -> AttributedStatement -> explicit Mapping -> attachment(s)
                      -> Observation -> Evidence -> Claim
                            +-> Provenance -> Selection -> exact Statement
```

A run appends new findings. It never selects itself. A new selection supporting
changed knowledge requires a **new Observation and Evidence**, with an explicit
reviewed Claim change if appropriate. Old observations remain pinned to their
original selections. There is no persisted or consumer-resolved `latest_run`,
`preferred_finding`, or moving analysis pointer.

Claim.evidence_ids continues to accept Evidence IDs only. Direct run/finding
fields are invalid, including hidden reference substitutes in Claim.value.
The example validator rejects known analysis IDs in any Claim position and
reserved analysis-reference keys in nested values. Arbitrary prose remains
inert, not a reference language. Step 5 must integrate typed predicate schemas
and prohibit adapters from interpreting arbitrary strings/URLs as alternative
support. Media data never supplies tools, policies, or canonical instructions.

The read example traces Source -> Observation -> Evidence -> Claim and expands
only its exact selection, finding/run, version, attachment and original source.
Availability reports are contextual and dated. Shared HTML, JSON, MCP, and read
services must eventually consume the same projection. This PR introduces no
production reader, public renderer, endpoint, or route.

## Additive migration and reader compatibility

**Accepted decision: fail closed on unsupported v1, not silently ignore media
collections while treating their claims as fully explained.** Record envelopes
retain the existing deterministic artifact format and separate schema-version
field. v1 activation and concrete storage routing are a later migration PR;
these fixture bundles are not a replacement storage format.

1. Freeze/review the baseline manifest of v0 IDs and content identities. Keep
   existing files and promoted ChangeSets unchanged. No bulk data reinterpretation.
   Legacy Sources keep their existing fields and unclassified status. New
   analysis-report Sources receive distinct IDs and the explicit v1 role;
   a migration cannot reclassify an existing uploader/comment Source.
2. **Before activation**, ship and test a root-level schema/capability gate in
   every supported reader, writer, CLI, MCP server, site build, and exporter.
   Unknown versions must produce a named unsupported-schema error before any
   partial read, index, planning answer, or export. Reader upgrade is a hard
   prerequisite, not optional advisory text.
3. Activate v1 only through a separately reviewed deterministic migration
   artifact with source/target versions, baseline digest, permitted collections,
   expected record counts, identity mappings, output digest and rollback plan.
   The v1 view references the unchanged baseline plus serializer-owned additive
   records. No new-media Claim may be exposed as a complete v0 projection.
4. Existing `Observation.artifact_refs` stay literal, readable, unverified
   strings. A URL, filename, or apparent digest is never silently promoted to an
   asset ID, version ID, hash, verified download, or capture/location assertion.
5. A later explicit migration may add `legacy_artifact_mapping` for a particular
   baseline observation and zero-based artifact-ref index. It must resolve the
   reviewed asset, version and selection and be covered by a reviewed migration.
   It does not alter the string or retroactively change the Observation's source,
   time, location, or support. New media support requires new typed observations.
6. Dry-run migration against synthetic and baseline snapshots; verify byte
   preservation, counts/references, idempotency, reversible routing, and all
   consumer/version errors. Rollback selects the preceding supported snapshot;
   it must not resurrect withdrawn data or silently downgrade v1 media claims.

**Implemented capability gate:** `load_canonical()` checks both canonical and
ChangeSet directory layouts before loading a snapshot. Unknown versions,
collections and envelope/record extensions raise `UnsupportedSchemaError`.
Read service, MCP, canonical CLI and site exports use this shared gate; site
validation precedes output writes. CI rejects unsupported publication paths too.
This supports **v0 only**, and does not activate v1 or migrate data. Old binaries
without this gate still require an upgrade or an explicitly pinned legacy
snapshot; they cannot be supported against an activated v1 dataset.

## Retention, redaction, deletion, and dependent answers

Append-only is an ordinary-history rule, subordinate to removal obligations.
A private removal case has a target, requester reference, owner and lifecycle
`hold -> reviewed -> propagating -> verified`. Every affected delivery surface
must have a recorded disposition: raw media, working copies, derivatives, OCR,
transcripts, findings, indexes, caches, static exports, offline manifests, logs,
and public Git history. `not_applicable` requires review, not a missing task.

The designed sequence is:

1. Place an immediate operational processing/publication hold, including affected
   public projections. Verify the request privately; do not publish the request
   or identifying evidence. Ordinary deferrals are still batch-scoped, not a
   global source blacklist.
2. Compute the conservative dependency closure: asset/version/attachment,
   inspected runs, findings, selected provenance, Observations, Evidence,
   Claims, and dependent rules/results/planning answers. Review shared source
   locators, captions, publisher labels, reposts, corroborating references and
   backlinks for disclosures beyond those formal dependencies. A source link
   is not automatically safe merely because Wayproof did not copy the media.
3. Delete or redact content as required. Pure redaction creates a new version
   with a new reviewed inspection if reused; it must not masquerade as the input
   originally inspected. Replace removed public payloads with approved minimal
   tombstones, or withdraw/re-key an identifying legacy ID. Clear identifying
   references, free text and hashes from every affected public artifact.
4. Reevaluate each dependent Evidence/Claim. Consumers show unavailable or
   unsupported evidence and withdraw unsupported planning answers; a missing
   original is not evidence that a place is closed, safe, or currently accessible.
   Alternative surviving evidence requires an explicit reviewed selection and
   domain change, never automatic substitution by a newer analysis.
5. Regenerate/purge all owned views and caches, supersede offline manifests, and
   remediate public Git history if sensitive material leaked. Keeping only the
   latest file clean is insufficient. Document inability to erase third-party
   copies; stale offline clients cannot be guaranteed purged. Fail closed while
   the owned publication state is inconsistent.
6. Retain a minimal non-sensitive audit and verify completion. New retention
   deadlines require a reviewed purpose; no unlimited default. Raw-media,
   findings, logs and private metadata can have distinct deadlines/permissions.

The oracle's removal function returns an **impact plan**. Its synthetic test
constructs a hypothetical tombstoned snapshot and proves the claim no longer
appears traceable. It does not demonstrate physical deletion, provider cleanup,
Git remediation, retention scheduling, takedown operations, cache purges, or
complete privacy screening. Implement and test the controls applicable to the
reviewed scope before processing. Reference-only scope still requires retained
text/reference removal and dependent-answer updates; raw-media/private-store
cleanup is deferred while those artifacts are excluded. The design oracle does
not change production answerability behavior.

## Synthetic acceptance and review gates

| Case | Required result |
|---|---|
| Same attachment URL, changed bytes | New opaque version and association; old selection unchanged |
| Unchanged media reordered later | New association observation time and ordinal; old mapping/version unchanged |
| Run attributed to uploader/comment/legacy Source | Rejected; distinct typed analysis-report Source required |
| Provenance, selection, finding, or version tombstoned/missing | Explicit unavailable support, never legacy fallback; missing target rejects validation |
| Supported repost / repeated analysis | Shared origin retained; never counted as independent field corroboration |
| Known publication, unknown capture | Capture stays unknown; location does not improve |
| Author and permitted EXIF dates disagree | Separate attributed qualified assertions, no automatic winner |
| Ambiguous ordered list | Retained as context; not selectable as exact media support |
| Partial video | Findings stay within inspected ranges/frames and exact version/attachment |
| Conflicting runs | Both retained; old Observation/selection unchanged; no preferred output flag |
| Unavailable original | Dated availability and reproducibility limits remain explicit |
| Removal request | Dependency plan includes derived lineage; tombstoned support is unavailable; delivery manifest includes all surfaces |
| Malicious OCR/caption | Inert text; no networking, writes, tool calls or policy changes in the design oracle |
| Claim points to run/finding, including nested value | Rejected; only typed Evidence can support the claim |
| Reprocessing without separate review | Hypothetical canonical transition rejected; no publication, gap resolution, relationship or planning change |
| Private hash / sensitive precise location | Rejected from public representation; private review never exported |
| Legacy artifact reference | Readable unchanged; only an explicit reviewed mapping can add identity |
| Unsupported envelope | Clear version error; Step 5a implements the v0-only root capability gate |

Before approving this schema proposal, review the new Observation origin fields,
separate availability assertions, selection cardinality, qualified location/time
semantics, public/private field budgets, opaque identities, migration gates,
tombstone restrictions, and unsupported-answer behavior. Acceptance here selects
a contract for implementation; it does not waive Step 5 enforcement review.
The initial delivery sequence is narrow public-source policy enforcement,
v1 migration/shared consumer compatibility, reviewed reference-only activation,
and bounded immutable processing. Each stage must prove the applicable checks
in the scope amendment above. Private custody and retained-media infrastructure
remain gates for later expanded scope; they are not initial launch prerequisites.
The existing ChangeSet/Evidence/publication boundary applies to every stage.
