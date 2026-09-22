# Contributing

Thanks for your interest in improving Wayproof. Contributions
of all kinds are welcome: bug reports, source-backed data corrections, and code.

## Getting started

```bash
git clone https://github.com/<owner>/wayproof.git
cd wayproof
python3.14 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
```

Wayproof supports Python 3.14. Agents should also read `AGENTS.md`; its linked
repository skills contain the source-ingestion, route-modeling, and release
workflows.

## Development guidelines

- **Tests must pass.** Run `python -m pytest -q` before opening a PR; add a
  focused test for new behavior, fixed bugs, or new planning coverage.
- **Match the surrounding style.** Type hints, module docstrings, and concise
  comments that explain *why*, as in the existing code.
- **Keep changes focused.** One logical change per PR with a clear description.
- **Canonical knowledge changes:** cite sources, preserve provenance and
  uncertainty, and use the domain write boundary to create a validated
  ChangeSet and detached candidate. Files under `canonical/v0/` and
  `changesets/v0/` are serializer-owned and must not be hand-edited. Run
  `python scripts/verify_canonical_diff.py --base origin/main --head HEAD`.
- **Source policy:** prefer official/public sources where available, but model
  only what each source supports. Do not commit copyrighted source documents;
  see `DATA_LICENSE.md`.
- **Legacy data:** salvage fields as `KEEP`, `REVERIFY`, `RECONSTRUCT`, or
  `DISCARD`; do not bulk-migrate the old corpus.

Documentation, tests, and rendering changes do not require a ChangeSet when
canonical knowledge is untouched. Schema migrations require a separately
reviewed deterministic migration artifact.

## Canonical contribution lifecycle

```text
source or field evidence
  -> observation and evidence
  -> atomic scoped claims and relationships
  -> DRAFT ChangeSet
  -> validation
  -> detached candidate
  -> GitHub PR and CI
  -> maintainer merge to main = PROMOTED/PUBLISHED
```

Validation means the proposal legally represents its evidence, uncertainty, and
gaps; it does not mean every claim is certain. GitHub review supplies approval.
Neither an agent nor an MCP client may directly promote canonical knowledge.

See `ARCHITECTURE.md` for the evidence model and storage boundary, and
`docs/agent-workflows/corpus-coverage.md` for selecting outcome-focused data
batches.

## Reporting bugs / requesting features

Open an issue using the templates in `.github/ISSUE_TEMPLATE/`. For a data
correction, confirmation, or something missing (a peak, trailhead, permit,
water source, campground, etc.), use the "Data report" template -- see the
README's "The Scavenger Hunt" section for how these get reviewed and
turned into the actual dataset via `report.py`.

## License

By contributing, you agree that your contributions will be licensed under the
project's MIT License.
