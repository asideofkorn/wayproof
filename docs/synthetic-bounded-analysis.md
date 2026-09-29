# Synthetic bounded processing and immutable analysis

This implements the synthetic gate after [reference-only activation](reference-only-activation.md).
`SyntheticAnalysisService` is an isolated domain rehearsal. It is not registered
with the production CLI, MCP server, canonical write service or Pages build.
The accepted `AnalysisRun`, `AnalysisFinding`, `ReviewedSelection`, and provenance
record definitions remain unchanged. Schema v0 and canonical knowledge are untouched.

## Inputs and processing boundary

The service accepts typed synthetic metadata whose source URLs use the reserved
`.invalid` domain. It takes a closed `SyntheticReply` fixture, not media bytes,
a file path, a network client, a callable processor, or a provider configuration.
There is no downloading, OCR engine, transcription engine, model request, tool
execution, EXIF extraction, location inference, upload, or private-custody path.
The scripted processor identifies itself as a simulation; it must never be
presented as real visual inspection. `.invalid` is an enforceable test-only URL
boundary, not an assertion that arbitrary submitted text is safe for publication.
The existing fingerprint-bound content review still screens retained text.

The service bounds input metadata to 100 records/100 KB, each attempt to four
inspection targets, image inspection to known areas of at most 16 million pixels,
a timed segment to 60 seconds, and an explicit frame selection to 32 frames.
Output is limited to eight findings/20 KB, each with bounded text and explicit
limitations. One session accepts at most 128 attempts. These are fixture/workload
bounds, not claims about real processor timeouts or sandboxing.

Every attempt gets a new opaque ID. Successful attempts create new frozen,
accepted run/finding records. Failed attempts retain only their ID and explicit
status (`failed`, `unavailable`, `changed`, or `invalid_output`); they do not
invent an inspection or reuse an earlier result. Reprocessing never mutates an
older run, selects a finding, creates an Observation/Evidence/Claim, resolves a
gap, adds a relationship or changes planning.

Input versions and attachment associations are pinned. Findings cannot exceed
inspected regions, frames or time ranges. Changed or unavailable input blocks
support for that version; a later successful attempt does not clear that block
or substitute new content. Capture and location remain explicitly unknown in
this simulation, independently of publication, retrieval and analysis times.
Version identity basis and reproducibility limitations remain visible. Repeated
analyses of the same version are not independent field corroboration.

## Human review and shared projections

`proposal_records(run_ids)` returns detached input/run/finding records for a
human-authored ChangeSet. It generates no selections, observations, evidence or
claims. A reviewer must explicitly choose finding IDs, author the ordinary
`Observation -> Evidence -> Claim` chain, and provide the corresponding research
text packet and workflow receipt.

`admit(change, packet, receipt)` validates the exact proposal against the service's
owned records and resolves the fingerprint-bound receipt through the configured
maintainer/PR workflow. A serialized `reviewer_role` or selection ID grants no
authority. Every admitted finding needs an explicit reviewed selection; changed,
foreign, withdrawn, or failed results are rejected. Prior selection/provenance
records cannot be overwritten. A different selection needs new records and a
separately reviewed ChangeSet.

Admission enables only the synthetic rehearsal projection, with
`publication: disabled`. Production `prepare_reference` still rejects analysis
records; generic v1 preparation also stays disabled. All consumers use the same
shared evidence traversal and the existing HTML/JSON/MCP exporters. They expose
the selected run, finding, version, inspected target, separate time roles,
uncertainty and limitations. Original-author excerpts, Wayproof paraphrases and
Wayproof analysis findings retain their existing distinct types; this processor
cannot emit author statements. Unselected outcomes remain operational research,
not consumer evidence. Continuing review failures produce unsupported output
without choosing another finding or Evidence.

## Withdrawal and owned outputs

`withdraw(source_ids)` follows typed dependencies through all attempts, runs,
findings, selections, observations, Evidence and Claims. Known origin/repost asset links propagate removal to their source associations;
duplicate source URLs cannot enter as separate inputs. It erases owned affected
payloads and request metadata and retains only non-sensitive withdrawn IDs.
Append-only history is subject to this removal exception. It also withdraws an
affected reviewed packet as a unit, rather than editing its reviewed content in
place. Unrelated outcomes and independent reviewed packets remain unchanged.

Live handles immediately return unsupported projections. Withdrawal does not
resolve approval and remains available after review revocation. It purges and
regenerates every registered owned output directory: HTML, JSON, MCP snapshots,
search index, invalidated planning cache, and replacement offline manifest.
Cleanup failures remain explicit and can be retried; live support cannot return
while cleanup is pending. Export refuses preexisting unowned, overlapping or
symlinked directories and withholds files if content/review eligibility changes
during generation. Exported output is a rehearsal artifact, not public deployment.

The ledger is process-local; there is no new persistent operational journal or
restart/recovery contract in this PR. Reviewed record/export snapshots exercise
the accepted schema, but restarting this service does not reload a ledger.
Retained outputs are explicitly owned by the session; they are not automatically
discovered after restart. Callers' copied values, Git history, remote artifacts,
and downloaded copies cannot be erased by the service. This scope must not be
mistaken for permission to run a live processor.

## Acceptance and next gates

Synthetic tests prove:

- New IDs and append-only outcomes across repeated/conflicting runs; no automatic
  canonical writes, selection or planning changes.
- Exact workflow review and typed Evidence lineage; rejection of every tested
  direct Claim-to-run/finding link and forged/modified records.
- Explicit failure, unavailable, changed and invalid-output states without
  substituted results; bounded partial video inspection and inert malicious OCR.
- Selective withdrawal after approval revocation, preserving unrelated history,
  with actual regenerated HTML/JSON/MCP/index/cache/offline artifacts.

Next is a separate activation review for **any live acquisition or external-model
processor**. That review must choose and enforce the execution environment,
provider permissions, timeouts/cancellation, operational retention and durable
history/recovery needed for real work, without weakening the accepted provenance
and deletion constraints. Only afterward should the shared ingestion skill target
stable commands: public-reference mode and textual field-observation mode with
an offline notes template. Personal photos/uploads and private custody remain
deferred.
