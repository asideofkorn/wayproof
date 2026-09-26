# Source exclusion policy and registry

## Policy

An explicit maintainer or contributor exclusion blocks ingestion, analysis,
canonical proposals, and public evidence links for the identified source until
an explicit reviewed reversal. A URL supplied solely to discuss UI or posting
behavior is not permission to ingest it. Use synthetic examples for tests.

Before retrieving candidate content, compare its normalized platform identity
against this registry. Strip tracking parameters and normalize equivalent host
forms; check parent-post identity for attached media and comments. Propagate
an exclusion to known copies/aliases without fetching the excluded content to
discover more aliases. Repeat the check before processing and publication.
Record the exclusion ID in the review checklist/proposal disposition, never a
copy of excluded content. On a match, stop that candidate and retain only the
minimum exclusion audit. If identity cannot be resolved, defer the candidate.

Maintainers enforce this gate in review today. Automated social ingestion is
not implemented; ADR 0004 requires validator coverage before it launches.
Exclusion removal requires an explicit reviewed policy change, not an analysis
rerun or a newer source date. Private identifiers belong in a restricted
registry, not this public document.

## Registered exclusions

| ID | Normalized source identity | Scope | Reason | Recorded |
| --- | --- | --- | --- | --- |
| EX-0001 | Facebook post `27334602719548950` in group `easternsierrafallcolors` | Post, attachments, comments, known aliases; no public evidence links | Explicitly excluded by contributor; posting behavior only, unresolved photographed locations | 2026-09-26 |

The numeric identity is retained solely to enforce the exclusion. This registry
is not a source catalog and does not authorize retrieval or publication of the
post's content. No author identities, photos, or comment text are retained here.
