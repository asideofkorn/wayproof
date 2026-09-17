# CLAUDE.md

Source-backed trip logistics for public lands. `plan.py` is the product.
`cli.py` inspects provenance and searches campgrounds. `scripts/build_site.py`
publishes wayproof.dev.

**Read `CONTRIBUTING.md` first — it is 42 lines.** The README is ~1,700 lines of
design argument. It is history, not a style guide. Do not infer house voice
from it.

## The one rule

Declining is a usable answer; being wrong is not. A tool that says nothing is
useless; a tool that says the wrong thing with a date attached is worse,
because it is trusted.

## Before you write prose

This package is **38% docstring and comment** (`camping.py` 64%,
`regulations.py` 75%, `pets.py` 85%). That is a defect this repo is trying to
reverse, not a style to match.

The cause is duplication, not verbosity: the pets decision is currently argued
in full in six places. Each piece of writing gets **one** home.

| what you are writing | where it goes | budget |
|---|---|---|
| why a decision was made | the commit message | no limit |
| what a thing does | its docstring | 3–5 lines |
| the rule that came out of it | a **test name** | — |
| a worked trip | `docs/user_stories/` | — |
| what the project is | README | do not add to it |

Specifically: **do not add a README section for your change**, and do not
restate one argument in a docstring, a constant's docstring, a test docstring,
a data note and the README. Pick one and link the rest.

## Data

- **Never write a value you did not read from a source.** Web-search summaries
  are not a read. `Dumbarton Quarry`'s blank `verified_date` is the marker for
  this and a test holds it.
- **Blank means nobody checked.** It never means "no". If "checked, and the
  source was empty" is a real state, give it its own value — see
  `camping.PETS_NOT_MARKED`.
- **Name a column for what the source said**, not for the answer, wherever a
  rule can override it: `pets_marker`, `coord_precision`, not `pets_allowed`.
- **One fact, one table.** `notes` is miscellany, not a filing cabinet.
  `permits.csv`'s `notes` has a 1,400-character cap enforced by a test.
- Cite the source and date on the row. Append to `permit_source_log.csv`; never
  rewrite history when an answer changes.

## Tests

- `python -m pytest tests/` — CONTRIBUTING's single-file command is stale.
- **Test names are the spec.** `pytest --collect-only -q` should read as the
  rulebook. Keep module docstrings to a few lines.
- Pin the *failure*, not the feature: write the test that would have caught the
  wrong answer.
- A fixture helper defaults any field whose absence would trip an unrelated
  gap check — see `_ground()` in `tests/test_reports.py`.

## Commands

```bash
python plan.py "Mount Williamson" --date 2027-07-15   # the product
python cli.py --open-questions                        # what is unconfirmed
python cli.py --campgrounds --access drive_in --near 37.8044,-122.2712
python scripts/scorecard.py                           # coverage, never a target
python scripts/build_site.py                          # -> _site/
```

`scorecard.py` is a measurement and does not fail the build. Do not chase it —
the cheapest way to move most rows is to add unchecked data.

## Known, unfixed

Do not treat these as bugs to fix in passing; they are tracked design debt.

- A `Trailhead` has no facilities (no toilet, parking, or fee columns). Only
  campgrounds can be asked anything.
- Rules scope on one axis. ~53% carry a condition their scope cannot express
  ("at a BACKPACK site", "dogs") and it lives in the summary prose.
- The website publishes trailhead reference only. Campgrounds, pets, costs,
  advisories and conditions are CLI-only.
- The scorecard scores peaks only; campground objectives score zero times.

## Open — do not build without asking

Under discussion, nothing decided:

1. **Place + subject as first-class**, with a resolver returning a verdict, the
   level that decided it, what tighter levels said, and provenance inline.
2. **Page generation off that resolver**, replacing the parallel thin
   trailhead view.
3. **Prose compression** — README to ~250 lines, package prose under 20%.

Ask before starting any of them, and before adding a new column, table or
module to work around one.
