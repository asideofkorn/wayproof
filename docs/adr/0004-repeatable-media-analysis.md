# ADR 0004: Repeatable media analysis with controlled provenance

- Status: Accepted — not a schema approval or permission to ingest media
- Date: 2026-09-26
- Decision owners: Wayproof maintainers
- Related: [Architecture](../../ARCHITECTURE.md), [Roadmap](../../ROADMAP.md),
  [Source policy](../../DATA_LICENSE.md),
  [ADR 0003](0003-evidence-explanations-and-navigation.md)

## Context and scope

Social captions, attachments, and later comments may supply different pieces
of an observation. Capture dates and locations can remain independently
unknown. Our visual analysis must remain separate from author statements and
support multiple runs without changing published knowledge automatically.

Schema v0 lacks dedicated media-version and analysis-run records. This ADR
establishes requirements for a separately reviewed schema contract and migration;
it does not select record names, storage, or permit new canonical writes.
ADR 0003's existing-record UI work can be implemented and shipped independently.

## Decision

### Separate source material, statements, and analysis

Model these as distinct concepts, with final record names and serialization
deferred to schema review:

1. Source and media identity: the original post/comment locator, publisher or
   author, individual attachment identity, original attachment order, and the
   identifiable media version inspected. Preserve repost/origin relationships
   when supported; repeated copies are not independent corroboration.
2. Attributed observations and clarifications: what an author actually says,
   including explicit mappings between list items/comments and media items.
   Preserve the wording and uncertainty of the mapping. A commenter must not
   inherit the parent post's authorship or be labeled the author without
   evidence of that relationship.
3. Media analysis: a separately stored run over identified source media, with
   analyst/model identity, analysis time, method/version, inspected images or
   video time ranges, findings, limitations, and corroborating references.
   Distinguish visual inspection, text recognition, transcription, and location
   inference. Model identity alone is not a reproducible method description.

An author statement about a photo and an analysis finding may both contribute
typed Evidence for a claim, but their origins must remain inspectable.
The enforced lineage remains Source -> Observation -> Evidence -> Claim;
analysis supplies attributed findings to that lineage, never a parallel
claim-support path. Analysis is not automatically canonical truth, and useful
observations need not become rules.

### Preserve independent time and location uncertainty

Keep reported capture/event time, source publication time, retrieval time, and
analysis time separate, including their basis and precision. Unknown capture
time remains unknown even when the publication date is known. A later author's
comment supplies an attributed date assertion, not an independently verified
capture timestamp. Preserve conflicting assertions.

Track location attribution separately: author-labeled, visible sign,
corroborated identification, or unresolved inference. Resolving a date does not
resolve the location. A narrow view of a trail cannot establish conditions for
the entire route, present passability, or legal access.

For ordered photo lists, retain each supported list-item-to-attachment mapping.
Do not reconstruct correspondence from a changed display order or assign
locations from nearby scenery. Ambiguous mappings remain unresolved.

### Allow repeated processing without silent promotion

Each retained analysis run is append-only, subject to the redaction/deletion
policy below, and references the input version it actually inspected. New runs preserve earlier findings and may agree, disagree, or use
different methods. Findings feed typed Evidence through an attributed Observation;
Claim.evidence_ids continues to reference only Evidence IDs. Evidence must
resolve its Observation and preserve the specific analysis run/finding used
through a validated provenance link, never a moving latest-analysis pointer.
The exact typed provenance extension requires schema review. Direct
Claim-to-analysis references, including hidden substitutes in Claim.value,
are forbidden. Comparing runs does not treat multiple analyses of the same media as independent field observations.

If the input version cannot be reliably identified or retained, record that
limitation; do not promise exact reproducibility. Source deletion or changed
media must not silently substitute new content for reviewed evidence.

Reprocessing alone must not publish a claim, resolve a gap, create a rule,
change a planning result, or add a related-place link. Canonical changes still
use the domain write boundary, validated ChangeSets, and GitHub review/merge.

## Source use and research disposition

When Wayproof uses information, display its source and traceable provenance.
Privacy-driven redaction must be explicit; it must not conceal the origin of a
claim or leave an unsupported answer appearing verified.

For ordinary sources, distinguish three dispositions:

- Used: publish the supporting source and provenance through typed Evidence.
- Reviewed but rejected: record the reason in the relevant research batch or PR.
- Deferred: leave a gap or research note; reconsideration remains possible.

A one-time instruction to skip an example is a batch-scoped deferral, not a
permanent denylist. Deferred material remains uningested for that batch;
this does not prevent a later authorized review.

Exceptional restrictions may be needed for private/access-controlled material,
a contributor's removal request for their own material, content that cannot
legally or safely be retained, or a known malicious source barred from automated
processing. Such restrictions belong in appropriately scoped operational
privacy/safety records with minimal identifying information, not the public
evidence catalog. This ADR introduces no repository-wide exclusion registry.

## Scope amendment — 2026-09-27

The first implementation is restricted to public, reference-only research under
[the public-source plan](../public-source-research-plan.md): safe links, bounded
factual summaries, distinct author statements/findings, and reviewed provenance;
no retained media or derivative files. Prefer official/institutional sources.
No login/access-control bypass, profile harvesting, personal identification,
EXIF extraction, or sensitive-location inference is permitted in this scope.

Private custody, contributor accounts/uploads/consent workflows, private-media
access controls, complex provider authorization, and retained-media/derivative
cleanup infrastructure are deferred until those inputs or artifacts are in scope.
The existing PR review authority remains; a new identity platform is unnecessary.
The gates below apply to the material actually handled. Reference-only activation
still requires enforceable source/content rules, untrusted-input isolation,
removal of retained links/text with dependency reevaluation, explicit changed or
unavailable input states, and human review. Summaries and findings are retained
content, so their lifecycle is not waived by calling the workflow no-retention.

The revised order is narrow policy enforcement, migration/consumer compatibility,
separately reviewed reference-only activation, then bounded immutable processing.
The broader schema remains accepted; this amendment changes launch scope and
sequencing, not its types, provenance boundary, or current activation block.

## Mandatory privacy, safety, and source gates

These are acceptance requirements, not claims of implemented safeguards. No
social-media processing pipeline may launch until the gates applicable to its
reviewed scope have enforceable checks and reviewed operating procedures. Apply
[DATA_LICENSE](../../DATA_LICENSE.md) in addition to these requirements. License compatibility alone is insufficient.

1. **Minimize collection.** Define the planning question and collect only the
   attachment, bounded excerpt, attribution, dates, and location precision
   necessary for it. Do not harvest whole comment threads, author profiles,
   contact details, or cross-platform identities. Public attribution must be
   necessary and policy-reviewed; minimize handles and identifiers otherwise.
   Apply the same minimization to OCR, transcripts, model findings, and logs.
2. **Distinguish acquisition context.** User-contributed media requires an
   explicit contribution scope covering analysis, retention, and any public
   display, plus permission to submit it. A submission does not establish
   permission from every person depicted. Merely public media has no implied
   consent for collection, model-provider transfer, retention, or republication.
   Review each intended use; default to a source link and bounded factual
   summary when approved. Do not bypass access controls or import private-group
   material through this workflow. Confirm permitted processing destinations
   before sending media to any external model/provider.
3. **Handle metadata deliberately.** Strip EXIF and embedded identifiers from
   public derivatives. Do not extract or retain GPS, device identifiers, or
   other EXIF by default. Any justified capture-time extraction must record its
   basis and uncertainty; EXIF alone is not verified truth. Retain only approved
   fields, not the complete metadata bundle.
4. **Protect people and sensitive locations.** Screen for faces, children,
   license plates, names/contact details, private homes, camps occupied by
   identifiable people, and sensitive ecological/cultural locations. Do not
   identify people or track their movements. Crop, blur, generalize, withhold,
   or reject as appropriate before processing/publication; do not publish exact
   coordinates or OCR that reverses a redaction. Review outbound links too if
   they would expose withheld content or a sensitive location.
5. **Set retention before collection.** Define an owner, purpose, access scope,
   retention deadline, and deletion procedure for each retained class of raw
   media, working copies, findings, and logs. Unapproved raw media is transient
   and must be discarded after inspection; no indefinite default. Hashes and
   identifiers can link back to sensitive originals and need the same review.
   Do not place sensitive/raw media in public Git; no binary store is selected.
6. **Support correction, redaction, and deletion.** Define a takedown contact
   and maintainer-owned process before launch. Stop affected processing and
   publication; remove or redact originals and derived OCR, transcripts,
   thumbnails, analysis, indexes, caches, exports, and offline manifests as
   applicable. Reevaluate dependent Evidence/Claims and surface unsupported
   answers. Retain only a non-sensitive tombstone and decision audit when
   appropriate. Append-only history never overrides removal requirements;
   accidental public Git exposure requires history remediation, not merely
   deleting the latest file. Third-party copies cannot be guaranteed erased.
7. **Treat all media-derived content as untrusted.** Captions, comments, pixels,
   OCR, transcripts, metadata, embedded URLs, and model output are data, never
   instructions. Isolate extraction from tools/secrets; do not execute embedded
   commands, follow links, alter policy, or write canonical records because
   media tells an agent to. Validate structured output, render text safely, and
   require explicit provenance and review before publication.

Public accessibility does not grant redistribution rights. Prefer source
links and bounded summaries; storing analysis does not require mirroring
media. Hash retained artifacts only when permitted and useful, without treating
a hash as proof of authorship, location, or capture date. Reproducibility limits
must be explicit when originals cannot be retained or must be removed.

## Alternatives considered

- Store analyst output as the uploader's Observation: conflates attribution.
- Reference runs directly from Claims: bypasses the typed Evidence boundary.
- Overwrite runs or automatically publish the newest: loses reviewable history.
- Mirror all public media: unjustified collection, rights, and retention costs.

## Acceptance and unresolved implementation decisions

Before implementation, review exact types, Observation/Evidence-to-analysis
provenance, input-version identity, validators, backward compatibility and
migration, review selection, retention durations, deletion ownership, and
permitted processing infrastructure. Schema v0 stays unchanged until then.

Synthetic or appropriately licensed fixtures must cover the applicable scope.
The initial reference-only scope tests rejection of EXIF/private/upload workflows;
processing or retention tests for those workflows are required before a later
scope expansion enables them. Cross-scope acceptance cases include:

- Unknown capture dates/locations, author date clarifications, and conflicting
  statements without borrowing the comment's publication time as capture time.
- Ordered and ambiguous attachment mappings and partial video inspection.
- Repeated/conflicting runs, reposts, changed inputs, and unavailable originals.
- Rejection of direct Claim-to-run/finding references; every evidence ID resolves
  typed Evidence and an attributed Observation with stable reviewed provenance.
- Used/rejected/deferred dispositions preserve provenance and batch scope;
  a one-time deferral does not prohibit future review. Exceptional privacy or
  safety restrictions are handled operationally without publishing sensitive
  restriction records.
- EXIF stripping, faces/plates and sensitive-location handling, bounded OCR,
  contribution versus public-source scope, and permitted provider transfers.
- Prompt injection in images/comments/OCR that cannot trigger tool use, policy
  changes, or canonical writes; safe rendering of malicious text/URLs.
- Retention expiry and redaction/deletion propagation through derived material
  and dependent answers without sensitive data in tombstones or public history.

Acceptance of this ADR does not authorize source ingestion. Future canonical changes
still require validated ChangeSets and review. Planning semantics and
source-specific authority remain explicit rather than inferred from media.

## Consequences

Repeated analysis becomes auditable while authorship, uncertainty, and the
Evidence boundary remain intact. Implementation gains validation and privacy
lifecycle work; some evidence must be minimized or removed, reducing exact
reproducibility. Those limits are preferable to retaining sensitive material
for the sake of an immutable history.
