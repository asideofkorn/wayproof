# Public-source, reference-only media research

Status: implementation plan approved in principle by the maintainer on
2026-09-27. [Draft-boundary enforcement](public-research-enforcement.md) is now
implemented. [Reference-only activation](reference-only-activation.md) supplies the
production storage, shared consumers and owned-output removal path. Broader v1
processing, private media, uploads and retained media remain disabled.
This narrows the first delivery scope of [ADR 0004](adr/0004-repeatable-media-analysis.md)
and the [accepted media contract](proposals/media-provenance-v1/README.md).
The broader contract remains available for later scopes; private-media
infrastructure is not a prerequisite for this restricted launch.

## Scope and retained information

Wayproof links to public posts and records bounded, reviewed factual summaries.
It does not mirror social-media content. Prefer official agency, park,
campground, and institutional accounts initially; an official-looking account
is not by itself verified authority. Apply [DATA_LICENSE](../DATA_LICENSE.md)
and preserve each source's actual authority and uncertainty.

Only posts accessible without login, group membership, private credentials, or
access-control bypass qualify. A public preview is evidence only for what is
actually visible; it does not establish access to the full post, video, or
comments. Unsupported or inaccessible material remains unavailable/deferred.
Do not harvest profiles or comment threads. A specifically relevant public
clarification may be considered with its own attribution and mapping.

Allowed retained content is limited to safe source links, opaque record IDs,
necessary organizational attribution, qualified times/locations, original
attachment order where observed, availability/version limitations, bounded
factual statements and findings, method/inspection metadata, and review history.
Author statements and Wayproof findings remain separate. Do not infer a
commenter's identity from the parent post or store personal names/profile data
to fill an attribution gap. If required attribution cannot be represented safely
and accurately, defer the source rather than misattribute it.

Retained text must distinguish these forms in records and consumer output:

- **Bounded quotation/excerpt:** the smallest relevant verbatim passage from a
  specific caption/comment, explicitly labeled as an excerpt and linked to its
  source and actual speaker. Preserve the author's wording and uncertainty;
  do not silently correct, rewrite, translate, or combine passages as a quote.
- **Truncation:** disclose omitted beginnings/endings and mark internal omissions
  with an ellipsis. Never omit a qualification or exception that changes the
  meaning. Keep separate passages separate; do not imply an excerpt is the full
  statement. If the bounded excerpt cannot preserve necessary context, defer it
  or provide a separately labeled paraphrase.
- **Wayproof paraphrase/summary:** Wayproof-authored wording, explicitly labeled
  as such and linked to the source statement it summarizes. Do not put it in
  quotation marks or present it as the author's own text. Preserve qualifications
  and uncertainty; keep any Wayproof visual finding separately labeled too.

These distinctions must survive serialization and HTML/JSON/MCP/read projections.
Do not place a paraphrase in an author-text field merely because it cites the
source. If the accepted representation cannot express the distinction, review
any necessary representation change before activation; this plan adds no fields.

No raw images/video/audio, downloaded copies, screenshots, thumbnails, crops,
embeddings, full OCR/transcripts, EXIF, personal names or identifiers, face/plate
recognition results, or sensitive-location inferences may be collected as
retained research records or committed artifacts. Existing public place names
and necessary organizational labels are distinct from personal identification.
Do not extract EXIF, identify people, or infer sensitive locations even when the
result would not be retained. Reject or skip content that cannot be examined
within these constraints; image redaction infrastructure is outside this scope.
Review source links too: a link can disclose excluded information.

“No retention” means **no retained source media or media derivative files**,
not no stored data. Summaries, attributed statements, findings, provenance,
review records, and public projections are retained and need removal support.
Future bounded processing must demonstrate that transient inspection does not
leave payloads in files, caches, logs, crash captures, or provider storage under
Wayproof's control. Do not claim control over the source platform's retention.
If a tool/provider cannot meet the reviewed mode, do not use it in this scope.
No complex provider authorization service is required, but public availability
alone never authorizes arbitrary transfer or reuse.

## Minimal safeguards required before activation

- Enforce source eligibility, bounded field/content budgets, and prohibited
  data handling at the shared domain/publication boundary. A caller-supplied
  `public` or `no_retention` flag is not proof of eligibility or permission.
- Treat captions, comments, OCR, imagery, embedded links, and model output as
  inert untrusted data. They cannot invoke tools, change policy, read secrets,
  or write canonical records. Safely render retained text and URLs.
- Preserve Source → Observation → Evidence → Claim. Claims reference only
  Evidence IDs; analysis never supplies an alternate claim-support route.
  Keep author statements distinct from visual findings, capture dates distinct
  from publication dates, and location attribution distinct from date resolution.
- Keep human review through validated ChangeSets and GitHub PR merge. No new
  contributor login/account system is needed. Submitted reviewer labels or
  permission flags are not substitutes for the existing review authority.
- Support removal of a source reference and any retained summaries/findings
  that must be withdrawn. Compute affected provenance, Observations, Evidence,
  Claims, and planning answers; mark unsupported results and regenerate/purge
  owned HTML, JSON, MCP/read projections, indexes, caches, and exports. Include
  offline manifests where present. Removal must not silently choose replacement
  evidence. Provide a maintainer-owned removal route without collecting a new
  public identity dossier. Sensitive Git exposure still requires remediation;
  do not promise erasure of third-party copies or already downloaded exports.
- Record dated unavailability or material changes. A URL is not immutable input
  identity: changed content requires a new version/association and review, never
  an overwrite of the selected input. With no retained original or reliable
  provider version, preserve opaque identity with explicit unverifiable or
  unavailable reproducibility limits. Do not promise exact replay, changed-byte
  detection, or current support from an unchanged URL alone.

## Reviewable implementation sequence

1. **Narrow public-source/no-retention policy (draft boundary implemented).** Implement the shared
   admission/publication checks and removal/dependency behavior for retained
   references and text, using synthetic fixtures. Keep v1 preparation,
   persistence, and publication blocked. Any necessary extension of the existing
   correction/removal boundary must be reviewed explicitly; simply documenting
   a removal procedure does not pass this gate.
2. **V1 migration and consumer compatibility.** Review serializer/storage
   routing, migration manifests/dry runs, baseline preservation, stable IDs,
   reviewed selections, and unsupported-schema errors. HTML, JSON, MCP, and read
   services must agree on lineage, unavailable inputs, and removed/unsupported
   Evidence/Claims. Legacy artifact strings remain unchanged and unverified.
   Keep activation disabled until these checks and the narrow policy pass.
3. **Reviewed reference-only activation.** Separately review activation for
   eligible links and bounded attributed statements/provenance. Prove that the
   broader schema cannot admit uploads, private custody, EXIF processing, or
   retained-media workflows through this policy. This is not permission to run
   an automated media processor or weaken the Evidence boundary.
4. **Bounded processing and immutable runs.** Add explicitly limited inspection
   modalities/ranges and independent author/analysis attribution after proving
   transient-input handling and untrusted-input isolation. Every run records its
   identified/observed version, its identity basis and reproducibility
   limitations, retrieval/inspection context and bounds, method, and uncertainty. An opaque
   version ID pins the reviewed record; without retained media, a permitted
   digest, or a stable provider version, it cannot prove exact content later.
   Reprocessing cannot publish, select its own result, resolve gaps, create
   relationships, or change
   planning results without a separately reviewed ChangeSet.
5. **Deferred expanded scope.** Private custody storage, user accounts, uploads
   and consent workflows, private-media access controls, complex provider
   authorization, raw-media retention/deletion, and comprehensive derivative-file
   cleanup require a later scope decision when Wayproof actually retains media
   or accepts private/user-contributed inputs. They are not hidden prerequisites
   for steps 1–4 and cannot be enabled by relabeling material as public.

## Acceptance evidence

Synthetic tests must cover accessible/inaccessible posts, personal-data and
sensitive-location rejection, relevant comments without inherited authorship,
forged eligibility/review flags, malicious captions/OCR and unsafe links,
unknown capture time, ambiguous attachment mappings, partial inspection,
changed/unavailable originals, conflicting runs and unchanged prior selections,
removal of retained text/references with dependent answers reevaluated across
consumers, and rejection of every direct Claim-to-analysis path. Processing tests
must also demonstrate that no payload/derivative files or raw logs survive a run.
Acceptance cases must distinguish verbatim excerpts, disclosed truncation, and
Wayproof-labeled paraphrases across records and consumers, without losing source
qualifications or presenting Wayproof wording as an author's quote. A version
identified only at retrieval must expose its identity basis and reproducibility
limits; its opaque ID must not be presented as proof of exact historical content.

The broader private-custody and retained-media examples remain design fixtures,
not proof that this smaller policy is enforced. No schema definitions, active
canonical data, or current runtime gates change merely by adopting this plan.
