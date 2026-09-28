# Reviewed reference-only v1 activation

This activates the accepted reference-only path in production storage, the shared
read service, HTML/JSON, MCP, publication checks, and owned-output removal. It
adds no real sources, media acquisition, processors, model calls, uploads, or
future ingestion skill. Existing v0 canonical bytes and stable IDs are unchanged.

## Admission and publication

`ChangeSetWriteService.prepare_reference` is the dedicated candidate boundary.
It revalidates the additive v1 ChangeSet, the narrow reference allowlist, the
public-source policy, the exact research fingerprint, and a workflow-resolved
`ReviewReceipt`. Generic `prepare`, `record_document`, and `write_candidate`
remain v0 APIs; they cannot serialize broad v1 drafts.

The first active scope permits owned public/no-login Source references, bounded
attributed statements and labeled paraphrases, attachment/version metadata,
explicit mappings, reviewed selections, qualified Observation provenance, typed
Evidence and explicitly proposed Claims about existing entities. It rejects
analysis sources, runs/findings, unqualified observations, legacy artifact
mappings, new planning entities/scopes/rules/relationships, uploads, private
custody, retained media/derivatives, EXIF, personal identification, and inferred
or sensitive locations. Admission is review-backed, not an assertion that a URL
or automated text check proves its own eligibility.

The research review must already be merged. The stored receipt pins its exact
head and reviewed blob. The adapter accepts an exact-head merged PR whose
`merged_by` actor is the configured Wayproof maintainer (`asideofkorn`), or the
existing independent admin/maintain approval path. A proposal cannot configure
maintainers, set approval flags, or mint a review. GitHub CLI authentication and
local Git history are needed; missing approval/history makes reference support
unavailable rather than exposing unverified content. Git/network access here is
administrative review resolution, never source/media acquisition.

The prepared canonical candidate requires its own PR and merge to main. The
publication checker verifies one exact batch transition: addition, a separately
reviewed receipt update for identical content, or withdrawal. It checks the
complete canonical diff and refuses extra files, undeclared edits, altered
payloads, combined v0 edits, or restoration of a withdrawn batch.

The existing v1 record and ChangeSet envelopes are reused. A serializer-owned
`reference-publication.json` index (`wayproof-reference-publication-1`) holds
independent batches, each using the reviewed migration manifest's codec,
inventory, identity map, fingerprint, packet, receipt, and lifecycle. This is a
storage/control index, not an additional approval or public domain record type.
Unmarked v1 directories remain unsupported.

## Independent batches and v0 compatibility

Each batch owns its Source references and cannot reuse another batch's record
IDs, including withdrawn IDs. Source URL aliases across batches or the v0 corpus
are rejected rather than counted as independent support; several statements and
observations from the same source may be represented within one reviewed batch.
Adding later statements to an already admitted source requires an explicit
shared-source migration; this activation does not silently mutate or alias an
existing batch. Reposts with different URLs still require source-origin review; URL uniqueness
alone does not establish independent corroboration.

The original v0 baseline is pinned for review validation, not frozen for future
editing. When current v0 bytes differ, the adapter verifies the baseline from the
receipt's exact local Git commit against the recorded hashes. It does not replace
the old review with a fingerprint of today's baseline or publish historical v0
payloads as current evidence. V0 entity edits and additional independent batches
continue through their own ChangeSets. Missing historical baseline/authority
leaves the affected batch unsupported.

For v0 editing in a mixed repository, `load_v0_baseline(root)` explicitly selects
the v0 write/planning baseline after checking the entire repository. The existing
v0 writer prevents identity or Source aliases into reference batches.
`load_canonical(root)` returns a fully checked typed mixed snapshot, including
typed removal tombstones. It refuses a raw snapshot when reference support is
unverified, instead of returning a misleading partial record set. Consumer
services can still render the explicit unsupported projection.

Example application composition (the inputs are already typed proposal values):

```python
from pathlib import Path
from wayproof.canonical_storage import load_v0_baseline
from wayproof.write_service import ChangeSetWriteService, InMemoryCanonicalRepository

root = Path('.')
writes = ChangeSetWriteService(InMemoryCanonicalRepository(load_v0_baseline(root)))
writes.propose(change, actor)
assert not writes.validate(change.change_set_id, actor)
publication = writes.prepare_reference(change.change_set_id, actor, root,
                                       packet, receipt)
# Commit the prepared files, open a PR, and wait for review/merge.
```

The deployment adapter's repository/base/maintainers are trusted application
configuration in `configured_research_workflow`; they never come from the packet.
Tests inject a synthetic workflow without external calls. Pages and publication
CI provide GitHub authentication and full Git history. If a squash merge left the
review head unavailable locally, an operator must fetch that reviewed PR head;
the reader does not silently use another commit.

## Time and location acceptance criteria

Every active media-statement Observation has explicitly qualified event/capture
times and locations. The shared projection separately exposes:

- Event/capture time: exact, date-only, range, approximate/asserted, or unknown,
  with its selected statement basis.
- Statement and attachment publication times, separately attributed.
- Retrieval time for each identified/observed version, with its own basis.
- Analysis time: explicitly unknown and `not_performed` in this activation.
- Location value, attribution basis, precision, generalization, sensitivity, and
  limitations/uncertainty. An unresolved location has no value or precision.

No field is filled from another. Publication/retrieval time cannot become
capture time. The Claim's subject or a nearby entity cannot fill a missing
location. V0 `observed_at`/`retrieved_at` shortcuts and planning time/spatial scopes
are rejected on these new records so they cannot bypass qualified provenance.
Human review remains responsible for whether a statement actually supports an
assertion; structural validation does not interpret arbitrary prose as truth.

Reference versions retain opaque IDs, identity basis, reproducibility status and
limitations. Without retained bytes, a permitted digest or a stable provider
version, they identify an observed version and cannot prove its content later.
No image or video is embedded, downloaded or analyzed.

## Shared consumers and removal

`CanonicalReadService`, the existing MCP tools, HTML, JSON and generated MCP
snapshots use one reference evidence projection. Relevant entity pages include
reference-evidence links; evidence pages expose quotations versus paraphrases,
source links, role-specific time/location context, durable lineage links, section
navigation and previous/next reference records. Multiple observations survive
separately. Reference claims are additional reported context, not automatically
registered operational/planning inputs; v0 plans and open gaps remain unchanged.

Unavailable/changed sources, revoked/unavailable approval, removed support and
missing pinned input produce visible unsupported claims without substituting
another Evidence, finding, version, or batch. A new source-state review is pinned
with `ReferencePublication(root).refresh_review(receipt, change_id)` and requires
its own merged research review and publication PR. Existing read/MCP handles
refresh support for each request. A site build freezes one checked projection,
then rechecks it and its inventory before accepting the output generation.

`ReferencePublication(root).withdraw(change_id)` deletes the whole owned batch's
retained records, packet, ChangeSet prose and current fingerprint-named research
review file. It requires no GitHub availability or continuing approval. Other
batches can remain present but become unsupported if their authority cannot be
verified. The operation first holds reads and purges the owned `_site`, and can
resume after interrupted deletion or tombstone writing.

Only IDs, hashes of bounded metadata, and non-sensitive control metadata remain.
Accepted `MediaTombstone` records replace media metadata; this also preserves a
real v1 artifact in a fresh Git checkout after withdrawal, so older capability-
gated binaries cannot silently load v0 while ignoring the removal state. Claim
and Evidence permalinks remain visibly unsupported. Withdrawn identities cannot
be reused, and a withdrawn batch cannot be restored by changing its receipt.

The complete production `_site` is regenerated, including HTML/JSON/MCP,
reference/search indexes, an invalidated planning-cache marker, and a replacement
offline manifest with a complete file inventory. Activated builds use the owned
`<root>/_site` directory to avoid untracked parallel exports surviving removal.
The offline manifest is a replacement contract, not an implemented offline client
or a claim that previously downloaded copies have already been erased.

The removal diff still requires normal GitHub review/merge for deployment. Local
withdrawal does not rewrite Git history, purge remote review history, invalidate
third-party caches, or erase other people's downloads. Those operational removal
steps remain necessary where applicable; no broader retained-media cleanup is
claimed implemented here.

## Next gate

Bounded processing and immutable analysis runs remain disabled. Review them in a
separate PR before building the shared public-reference/field-observation skill.
Personal photos, uploads and contributor-media custody require a later scope
review. This activation does not change either boundary.
