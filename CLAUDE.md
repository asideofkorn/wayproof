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

One exception, and it is why **Decisions** below exists: a rule that governs
future edits belongs *here*, not in a docstring. Where this file states a rule,
the docstring that used to carry the argument may shrink to a pointer.

## Decisions

The recurring calls, in the order you hit them. Each is already enforced
somewhere in code or tests; this is where to read it before you write.

**Where does a new fact go?**

| the fact | its home |
|---|---|
| varies per place, from the operator's own form/listing | a column on that place's table, named for the source |
| what a land manager says you may do | `regulations.csv`, scoped |
| true only within a window | `advisories.csv` |
| how you reserve it | `booking_channels.csv` |
| occurs once, fits nothing above | `notes` |

If you write the same *kind* of thing into `notes` twice, it needed a column.
An amenity ("two XL BBQs", "Campfire Allowed") is a description, not a
permission — it can never contradict a rule, so do not file one against the
other as a conflict.

**What scope for a new rule?** The narrowest level whose *whole extent* the
rule covers. A rule read off one park's page is `park`-scoped unless the source
says otherwise — seven current rules violate this and are listed under Known.
If the rule's own words narrow it further than any scope level can ("at a
BACKPACK site"), record it at the level that contains it and accept that it is
in force too widely; it may not then declare `supersedes`. Never scope to
`permit_group: none`.

**When may a rule declare `supersedes`?** All four, or not at all:

1. its scope is strictly narrower than the rule it displaces (loader enforces);
2. it *fully* displaces — answers everything the broader rule answers, more
   restrictively;
3. a source, or a reading already recorded, establishes it. Never derive it
   from scope: `point-pinole-dogs` is narrower and displaces nothing;
4. it is not partial. A dog-only override of an all-animal rule is not
   representable — leave it in `detail`.

**When do you open a `conflict_id`?** When two sources disagree about a value
that gates a decision. Not for differences that decide nothing (acreage, drive
time). One id per disagreement; a resolving entry closes only the id it names.
One publisher contradicting itself is `internal`.

**How do you change a value that already exists?** Append to
`permit_source_log.csv` first. If the new evidence disagrees, open a conflict
and leave the stored value alone. Change the stored value only once resolved,
with a `corrects-existing` entry saying why. Never overwrite silently; history
is not rewritten when the answer changes.

**When does a column need a third state?** When "the source has this field and
left it empty" is distinguishable from "nobody read the source" *and both
occur*. Give it a value (`PETS_NOT_MARKED`); never collapse it into blank.

**When does a vocabulary get a new value?** When a source produced a shape the
existing values cannot carry — never to anticipate one. It needs a line saying
what it means, loader validation, and a test.

**When you cannot reach the source:** do not fill the field, and do not fill it
from a search summary. Leave it blank and make the gap name the page that would
close it. If you read part of a page, fill what you read and leave
`verified_date` blank — see `Dumbarton Quarry`.

## Data invariants

Three, and the procedures above serve them.

- **Never write a value you did not read.** Web-search summaries are not a read.
- **Blank means nobody checked.** It never means "no".
- **Name a column for what the source said**, not for the answer, wherever a
  rule can override it: `pets_marker`, `coord_precision`, not `pets_allowed`.

Every row carries its source and the date it was checked. `permits.csv`'s
`notes` has a 1,400-character cap enforced by a test; nothing else does yet.

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
- Seven EBRPD rules are scoped `agency` but were read off one park's booking
  page (six off Garin's, one off Reinhardt's). Either they are District
  boilerplate or they are that park's; nobody has checked. Do not re-scope
  them without reading the pages.
- The website publishes trailhead reference only. Campgrounds, pets, costs,
  advisories and conditions are CLI-only.
- The scorecard scores peaks only; campground objectives score zero times.
- `equestrian` is a valid site class with no booking channel of its own, so
  Lil Chaparral and Caballo Loco resolve to the agency-wide contact only.
  Nobody has read how EBRPD sells an equestrian site; do not invent a channel.
- `permit_source_log.csv:verdict` has a vocabulary that no loader validates.
  `tests/test_schema_integrity.py` checks the data; the loader still does not.

## Open — do not build without asking

Under discussion, nothing decided:

1. **Place + subject as first-class**, with a resolver returning a verdict, the
   level that decided it, what tighter levels said, and provenance inline.
2. **Page generation off that resolver**, replacing the parallel thin
   trailhead view.
3. **Prose compression** — README to ~250 lines, package prose under 20%.

Ask before starting any of them, and before adding a new column, table or
module to work around one.
