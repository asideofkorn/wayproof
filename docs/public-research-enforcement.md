# Reference-only research enforcement — draft boundary

This implements the next bounded part of the
[public-source plan](public-source-research-plan.md). It does not activate v1,
fetch posts, inspect media, run models, add public endpoints, or change the
published v0 corpus.

## Enforced service boundary

`ChangeSetWriteService.assess_public_research(change_set_id, packet)` first runs
the existing structural v1 validator against the v0 baseline, then the narrow
policy in `wayproof/public_research.py`. Only a successful policy assessment
retains the detached text packet for the shared draft preview. Structural
`validate()` / `VALIDATED` continues to mean structurally representable intent,
not source eligibility, media permission, or approval to publish. `prepare`,
storage and publication still reject v1, including policy-assessed drafts.

The default service has no reviewed access/content facts and denies eligibility.
A trusted application may configure `ReviewedResearch` with maintainer-reviewed
facts about an exact proposal and baseline. This is application composition,
not an input accepted by `propose` or the closed research-packet decoder. The
fingerprint binds every proposed record, operation, summary, text rendition and
baseline; changing any of them invalidates the review. It hashes proposal
metadata, not media bytes, and is not a public media identity.

The review snapshot is the explicit trust root. This PR does **not** implement
GitHub authentication or discover whether a live social site is public. A human
must establish full public/no-login visibility and screen the entire bounded
content, source links, attribution and quotations; HTTP success or a proposal's
`public`/`approved` flag is insufficient. Unknown, login-required, private,
unavailable or changed inputs fail eligibility. Unknown publisher classification
fails; official/institutional classification is exposed in the preview so
research can prefer it without equating it with unrestricted reuse.

Trusted facts include acquisition class, access inspection time, publisher
classification, source state, and content-review exclusions. Any upload/private
acquisition, pending/rejected/revoked review, or retained-media, derivative, EXIF,
personal-identification, sensitive-location, profile-harvesting, unsafe-link or
misquotation exclusion rejects the proposal. Semantic screening is human review,
not a claim that a regex can recognize every name or sensitive place. The default
denial prevents unreviewed text from masquerading as screened content.

OCR/transcription additionally requires an explicit `ContentReview.extraction_scope`
attestation of `necessary_excerpts` covering every extraction in the exact reviewed
proposal. The default `unreviewed`, `complete`, and `unnecessary` states reject
proposals containing OCR/transcription runs or findings. A complete extraction is
prohibited even when it is only a few characters long. The reviewer must establish
that retained text is both an excerpt and necessary for the bounded factual purpose;
character limits alone cannot establish minimization. This fact belongs to trusted
review configuration, never the submitted text packet. Synthetic image/video cases
exercise complete-but-short rejection and necessary-excerpt acceptance without
performing OCR or transcription.

Intrinsic checks apply even to an accepted review: bounded records/strings,
clean HTTPS references (no credentials, query/fragment, IP-literal/local host or
control-character URLs), no artifact-reference shortcut, no retained-copy/digest
identity mode, no metadata extraction, location-inference modality or point
location, and explicit version limitations. An unresolved location may remain
unknown with no value. Unverifiable versions require unavailable reproducibility.
A provider-version basis is reviewed context, not proof supplied by an opaque ID.
The code performs no URL fetch, DNS lookup, command execution or media IO.

## Text representations and preview consistency

These are closed **draft-review representations**, not new persisted canonical
fields or a migration format:

- `Quotation`: one to three verbatim passages (at most 600 characters each),
  source/target IDs, and explicit omitted-start/end flags. Internal omissions
  render with an ellipsis. The rendered excerpt must exactly match the domain
  statement text; the reviewer establishes fidelity to the visible source.
- `Paraphrase`: Wayproof-authored Observation text with a pinned statement ID.
  It cannot occupy an attributed-statement field or be labeled as a quotation.
- `FindingText`: a distinct analysis-finding rendition with a pinned finding ID,
  including when used to describe a media-analysis Observation.

Every new statement, finding and Observation needs exactly one matching rendition.
The limits are 1,600 characters per rendition, 2,048 per other nonempty string,
and 100,000 characters for the encoded proposed records. These conservative
initial budgets are implementation choices, not a permission to quote that much
from any source; source terms and minimum-necessary review still apply.

`public_research_preview()` is the shared detached read model. JSON serialization
and escaped HTML preview render that same model, preserving labels, omissions,
source links/states and version limitations. Text, embedded URLs and instructions
remain inert; text URLs are not automatically fetched or turned into links.
Synthetic tests compare the service model, JSON and HTML's embedded model.
This is **preview consistency**, not completed live HTML/JSON/MCP v1 integration.
MCP and production readers remain v0-only until the next migration review.

If the trusted review is missing/stale/revoked, or a source is now changed or
unavailable, preview support becomes unavailable and retained text is withheld.
The selected version and underlying proposed records are not silently replaced.
A refreshed application-owned review snapshot is needed to assess new facts;
there is no request-level permission or source-state override.

## Removal and dependent support

`remove_public_research(source_ids, actor)` removes whole affected owned v1
drafts, all their text packets and their reviewed source references. It also
withdraws other owned drafts that reuse the same source URL, and handles drafts
that refer to a legacy Source without modifying that baseline Source. A withdrawn
ChangeSet ID cannot be reused. The service retains only an opaque withdrawn-ID
marker and its existing workflow event; previews expose no removed URL/text.
Externally held copies returned before withdrawal are outside service custody.

`removal_impact()` computes a conservative typed dependency closure through
versions, attachment associations, runs/findings, selections/provenance,
Observations, Evidence, Claims, relationships, rules, requirements, fulfillments,
gaps and derived results. All planning caches are invalidated conservatively,
since a plan can depend on missing information as well as explicit input IDs.
The result identifies HTML, JSON, MCP/read projections, indexes, caches and offline
manifests as outputs requiring regeneration/purge. It never picks alternative
Evidence or another analysis run automatically.

Owned draft deletion is executed. Published-output invalidations are a returned
impact plan, **not a claim that published files, Git history or third-party copies
have been purged**. There are no published v1 records to remove today. Requests
outside owned research drafts are rejected; existing canonical corrections still
use reviewed ChangeSets. Wiring removal/unsupported support into persisted v1,
production consumers and export regeneration remains a mandatory part of the
next migration/consumer-compatibility stage before activation.

## Remaining review gates

The next PR must review persistence of the text distinction, trusted review
acquisition from the existing maintainer/PR workflow, v1 migration and compatibility,
removal propagation to owned published outputs, and shared consumer behavior.
It must not equate a structural validation result or a caller-created review object
with GitHub publication authority. Activation and actual bounded media processing
remain separate later reviews. Private storage, accounts, uploads and retained-media
infrastructure remain deferred rather than becoming implicit prerequisites.
