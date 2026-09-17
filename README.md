# Wayproof

Open-source, source-backed logistics for hiking, trail running, backpacking, and
mountaineering. Sierra Nevada first; designed to expand to U.S. public lands.

Turn an outdoor objective into a trip you can actually execute: approaches,
access, effort, permits, booking deadlines, and evidence.

This repository began as a tool for grouping the Sierra Peaks Section (SPS) list
into possible multi-peak trips. That experimental geographic-planning code is
still part of the project, but it exposed a more important problem: in the
mountains, proximity is not the same thing as feasibility.

Two summits can be close on a map and still be separated by technical ridges,
cliffs, difficult talus, snow or ice, creek crossings, private land, major
descents and reclimbs, or simply no sensible route connection.

The project is therefore evolving around a different question:

**I want to do this objective on this date. What do I need to know and do to make
the trip happen?**

Today the data and tooling are Sierra Nevada- and SPS-focused. The longer-term
architecture is intended to support other U.S. public lands without pretending
that nationwide coverage exists yet.

## The Planning Problem

Suppose you want to climb Mount Williamson and Mount Tyndall over three days in
July 2027.

Knowing that the summits are geographically near one another is useful, but it
is not enough to plan the trip.

That relationship between objective -> approach -> access -> permit -> timing ->
evidence is the direction of the project. The questions it has to answer, and
what makes an answer wrong, are below.

Wayproof is not intended to replace CalTopo, Gaia GPS,
AllTrails, Strava Routes, or other detailed mapping and navigation tools. Those
products are better suited to drawing, inspecting, and navigating exact routes.
This project is focused on the logistical knowledge around the trip: what access
applies, what rules matter, when you need to act, and what evidence supports the
answer.

## What Someone Actually Asks

These are the questions this project exists to answer. Every one comes from a
trip that happened, and each carries **what makes an answer wrong** rather than
what makes it complete.

That emphasis is deliberate. This project's failures have not been missing
features; they have been confident wrong answers. `plan.py` once returned a
Sequoia-Kings Canyon permit for a peak its own data routes over Shepherd Pass on
the Inyo side, and printed a verification date underneath. A tool that says
nothing is useless. A tool that says the wrong thing with a date attached is
worse, because it is trusted.

So: **a change that does not improve one of the answers below is probably not
worth making.** Worked examples with verified answers live in
`docs/user_stories/`.

### Getting these wrong costs you the trip

- **What do I need to do this trip?** Wrong if it names a permit but omits a
  fee, booking or pass that also gates entry. An Ohlone traverse was reported as
  free; it cost $97 and needed a phone call three weeks out.
- **Does my specific route change which permit I need?** Wrong if it answers per
  trailhead. Whitney Portal serves the main trail, the Mountaineers Route and
  the East Face, under two different permits.
- **What is the scarce thing, and when does it become available?** Wrong if it
  assumes the scarce thing is a permit. At Ohlone it is a campsite; at Whitney
  it is a lottery slot.
- **How do I actually get it?** Wrong if it implies online booking where the
  channel is phone-only in business hours, or in person only, as at Carson Pass.
- **What do I need at the other end?** Wrong if it treats exit parking as
  unrelated. At Stanford Ave the overnight pass is obtainable only while booking
  the campsite.
- **What must I carry?** Wrong if it says "required" without saying that a
  digital reservation confirmation is not a permit.

### Getting these wrong costs money or a day

- **What will it cost, all in?** Wrong if entrance, parking and reservation fees
  are reported away from the headline figure.
- **Can I change or cancel, and by when?** Wrong if it gives a refund rule
  without its cutoff.
- **How many of us can go?** Wrong if it gives one number. Mokelumne allows 8
  overnight and 12 on a day hike.
- **If I miss the release, what are my options?** Wrong if it reports "sold out"
  where a walk-up share, a cancellation window or an off-season route exists.
- **Is the trailhead reachable on my dates?** Wrong if it ignores seasonal road
  closure or snow.

### Getting these wrong is uncomfortable but recoverable

- **Can I have a fire?** Wrong if it reports the statewide permit requirement
  without the local ban sitting on top of it.
- **Can I bring a pet?** Wrong if it says "under control" where the forest
  requires a leash under six feet. Also wrong if it answers for a dog when the
  animal is not one: most pets rules in this dataset are written about dogs,
  because that is how the agencies write them, and a leash rule is not an
  answer to whether a cat, a rabbit or a bird may come. Say which animal the
  rule governs, or say there is no rule on file. It is also wrong to answer
  from the booking listing's pets marker alone: Round Valley Backpack Camp is
  marked pets-allowed and its preserve bans dogs outright.
- **Where can and cannot I camp?** Setbacks, designated sites, restoration
  closures.
- **Does my permit still cover me in the next wilderness?** Reciprocity, and
  where it stops.
- **Where is water, and when was it last confirmed?** Wrong if availability is
  reported without a date.
- **What is closed?** Wrong if closed and never-existed look the same.
- **What is hazardous right now?** Burn scars, snow windows, exposure.

### Afterwards

- **This is wrong, and here is what I found.** Wrong if the report is accepted
  without being checked against the data. This project's first community report
  claimed a peak was missing that was present under a misspelling.

### The two that run underneath all of them

- **How do you know, and when did you last check?** Wrong if a verification date
  is attached to a claim it does not cover.
- **What do you not know here?** Wrong if silence reads as confirmation.

A question this project cannot answer should say so plainly. **Declining is a
usable answer; being wrong is not.**

## `plan`: Objective + Date -> Logistics

`plan.py` is that answer. It takes specific, named objectives and resolves
access, permit, and evidence logistics for them directly.

```bash
python plan.py "Mount Williamson" "Mount Tyndall" --date 2027-07-15
```

```text
MOUNT WILLIAMSON + MOUNT TYNDALL
Trip date: 2027-07-15

Access
  Trailhead: Shepherd Pass  (east side)

Permit
  Wilderness: John Muir Wilderness  |  Agency: Inyo National Forest
  Permit: Inyo NF Wilderness Permit (John Muir / Ansel Adams / Golden Trout-Inyo / Hoover-Inyo entries)
  Status: Reservations open 2027-01-14 (07:00 America/Los_Angeles) -- mark your
  calendar. A further 40% release opens 2027-07-01 (07:00 America/Los_Angeles).
  Fee: $6/permit + $5/person ($15/person if the trip enters or exits via the Mt. Whitney Zone)
  Apply: https://www.recreation.gov/permits/233262
  Provenance: source last updated 2026-07-08; we last checked this against the
  source on 2026-07-23.

Known per-objective mileage (official round trip, from source data)
  MOUNT WILLIAMSON: 12.9 mi round trip, 8,990 ft gain
  Mount Tyndall: 11.1 mi round trip, 8,360 ft gain
  These are each objective's own official round-trip stats from its standard
  trailhead -- not a computed combined route. Whether they can reasonably be
  linked into one continuous trip is not modeled here; treat as reference
  points, not a verified itinerary.

Planning aid, not a booking guarantee -- verify the current rule at the
official source before acting on any date above.
```

A trailhead shared by objectives with different actual approaches -- e.g. Mount
Whitney and Mount Russell from Whitney Portal -- surfaces both permits it
actually needs, using the same approach-relationship data described below:

```bash
python plan.py "Mount Whitney" "Mount Russell" --date 2027-07-01
```

`--output plan.json` writes the same resolution as structured JSON (objectives,
trailhead, every permit entry, warnings) for downstream use.

**Current scope, deliberately:** `plan`'s objectives must share a single
trailhead, the same assumption made everywhere else access is modeled in this
project. Objectives that don't share one aren't rejected -- `plan` still
resolves its best guess and reports the mismatch as an explicit warning rather
than silently trusting it. A loop or point-to-point traverse with a genuinely
different entry and exit is a natural next step, not something this models yet.

```bash
python plan.py --help
```

## What The Project Can Do Today

The current implementation is centered on the Sierra Nevada and the Sierra Peaks
Section dataset.

It can:

- Resolve access, permit, and evidence logistics for a specific, named set of
  objectives and a trip date (`plan.py`).
- Load the SPS list with summit coordinates, elevation, class, section,
  emblem and mountaineers flags, mileage/gain fields, trailhead metadata, USGS
  quad, and source metadata.
- Work with a curated Sierra trailhead dataset containing location, side of the
  range, wilderness area, land agency, and permit-group relationships.
- Estimate approach effort when trailhead and peak-approach data are available.
- Report permit logistics for a planned trip date, including quota season,
  reservation window, application method, fees, official application URL, and
  provenance dates.
- Preserve an append-only history of permit-source verification, including
  conflicting evidence.
- Apply explicitly sourced, peak-specific approach relationships when a
  trailhead's default permit is not sufficient for a particular objective,
  including flagging suspected-but-unconfirmed cases rather than guessing.
- Answer whether a named animal may come to a campground, separating what the
  booking listing marked from what the land manager's rules actually say, and
  naming the rules that are written about a different animal instead of
  counting them as an answer.
- Say which of the rules in force a narrower one displaces, so a District-wide
  norm and the park rule that overrides it do not read as peer bullets.


The geographic grouping capability is useful for discovery. It is not an
authoritative mountain-routing engine.

## Current Coverage And Limitations

Current coverage is Sierra Nevada- and SPS-focused, plus a first step outside
it: Rose Peak and Mission Peak (Diablo Range, Alameda County), added to
`data/peaks.csv` with no SPS collection row, on East Bay Regional Park
District land with a genuinely different access model (no wilderness permit,
a campsite reservation instead, and a vehicle day-use fee with its own
exemptions) -- see the "Campgrounds And Facilities" section below.

The repository currently includes:

- `data/peaks.csv` - collection-agnostic summit identity: name, coordinates, elevation, region, nearest-trailhead access signal
- `data/collections/sps.csv` - the SPS collection layer: list membership, section, class, official mileage/gain, benchmark rating
- `data/trailheads.csv` - curated trailheads and access metadata, including the `agency_id` key that scopes agency-wide regulations to permit-free land (Sierra Nevada plus, as of Rose Peak/Mission Peak, the East Bay's Diablo Range)
- `data/permits.csv` - structured wilderness-entry permit rules
- `data/release_policies.csv` - structured, computable permit release phases
- `data/approaches.csv` - peak-specific approach/permit relationships, confirmed and unconfirmed
- `data/permit_source_log.csv` - append-only permit verification history
- `data/campgrounds.csv` / `data/campsites.csv` - campgrounds and their individually-bookable sites. Four independent axes on a campground, none predicting another: `access_mode` (how you physically reach it — `drive_in`/`hike_in`/`boat_in`, `;`-separated where the operator lists several), `campsite_type` (which queue the agency sells it in), `unit_level` (whether the row IS one bookable unit or holds several), and `facility_id` (which booking page sells it). Plus `pets_marker`/`pets_animals`, named after the booking listing's pets field rather than after the answer. Plus coordinates with a `coord_precision` saying whether they name the campground or only its park, `season_closed_start`/`season_closed_end`, the operator's own `loop` label, and `source_url`/`verified_date`
- `data/booking_facilities.csv` - the booking system's own pages, keyed by facility id. A level above a campground and *not* a park: one facility sells sites in three different parks, and two parks are each sold through two facilities, so `facility_id` is stored on a campground rather than inferred from where it is
- `data/booking_channels.csv` - how to book a campsite, scoped by agency and by class of site — the channel, what is *not* a channel, lead time, release-day mechanics and booking horizon
- `data/water_sources.csv` / `data/water_source_log.csv` - named backcountry water sources and an append-only ledger of dated availability checks (a source can go dry with no announcement, so a later check never overwrites an earlier one)
- `data/park_access.csv` - park-level vehicle entrance fees, gate hours, and fee exemptions (distinct from a wilderness permit or a campsite reservation)
- `data/passes.csv` - Sierra pass data used for optional coarse cross-crest
  distance estimates
- `data/permit_zones.csv` - bookable destination zones for permit groups
  whose quota attaches to a destination rather than an entry point
- `data/regulations.csv` - rules in force once you hold a permit (fire, food
  storage, waste, pets, stock), scoped by state, agency, or permit group

The project does not currently:

- provide comprehensive U.S. public-land coverage,
- check live Recreation.gov inventory,
- model complete trail topology,
- determine whether off-trail terrain is technically passable,
- evaluate current snow, ice, creek, avalanche, wildfire, or weather conditions,
- resolve `plan` objectives that don't share a single trailhead (a loop or
  point-to-point traverse with a distinct entry and exit isn't modeled yet),
- or certify that a generated peak sequence is a safe or feasible route.

Use the following terms deliberately:

- **Candidate grouping** - a set of objectives generated from geometry and
  planning heuristics.
- **Candidate sequence** - a suggested ordering of those objectives; not verified
  travel between them.
- **Known approach** - an approach relationship represented by actual project
  data rather than inferred only from geometric proximity.
- **Verified rule** - a logistical rule supported by authoritative source
  evidence.
- **Unresolved / uncertain** - the available evidence does not justify a
  confident conclusion.



## Installation

```bash
cd wayproof
pip install -r requirements.txt
```

Python 3.9+ is supported. Core dependencies are `pandas` and `numpy`.

## Quick Start

```bash
# Resolve access, permit, and evidence logistics for specific objectives.
python plan.py "Mount Williamson" "Mount Tyndall" --date 2027-07-15

# Inspect the source-verification log: why we believe what we believe.
python cli.py --permit-sources desolation

# List every unconfirmed or conflicting fact currently derivable.
python cli.py --open-questions

# Find a campground you cannot already name: the only command that answers
# "where could I go" rather than "why do we believe this".
python cli.py --campgrounds --access drive_in --near 37.8044,-122.2712

# ...and whether the animal you are bringing may come to them
python cli.py --campgrounds --access drive_in --pets allowed --animal cat \
    --near 37.8044,-122.2712
```

## CLI Usage

### `plan.py`

| Flag | Default | Description |
|------|---------|-------------|
| `objectives` | required | One or more objective (peak) names, positional |
| `--date` | required | Planned trip date (`YYYY-MM-DD`) |
| `--exit` | none | Trailhead you finish at, when the trip does not end where it started. Pass the same name as the entry for an explicit out-and-back or loop. **Omitted means unknown, not returns-to-start** — absence is never read as a route shape. Resolves the exit's permit group (and compares it against the entry's) and its park entrance fee, which lands in the cost roll-up. |
| `--peaks-file` | `data/peaks.csv` | Core peak dataset: name, coordinates, elevation |
| `--collections-file` | `data/collections/sps.csv` | Collection metadata (list, section, mileage, etc.) joined by name; pass `''` for core geography alone |
| `--list` | `all` | Keep only this `list` value; pass `SPS` to restrict to the SPS list |
| `--trailheads-file` | `data/trailheads.csv` | Trailhead dataset |
| `--permits-file` | `data/permits.csv` | Permit rules dataset |
| `--release-policies-file` | `data/release_policies.csv` | Structured permit release-phase dataset |
| `--approaches-file` | `data/approaches.csv` | Peak-specific approach/permit relationships |
| `--water-sources-file` | `data/water_sources.csv` | Named backcountry water sources |
| `--water-source-log-file` | `data/water_source_log.csv` | Append-only water-availability check ledger |
| `--campgrounds-file` | `data/campgrounds.csv` | Backpack campgrounds |
| `--campsites-file` | `data/campsites.csv` | Individually-bookable campsites |
| `--park-access-file` | `data/park_access.csv` | Park-level entrance fee/hours dataset |
| `--output, -o` | - | Write the resolved plan to this JSON file |

### `report.py`

Submit, list, and resolve data reports -- see "The Scavenger Hunt". Not
tied to a trip date or an existing dataset entry, so it's a separate tool
from `plan.py` rather than a flag on it.

| Command | Description |
|---------|-------------|
| `submit <target_file> <target_key> <claim>` | Submit a report (positional: which dataset, which item, the claim itself) |
| `list` | Print every report awaiting review |
| `resolve <report_id> <status>` | Mark a report `accepted` / `rejected` / `needs-more-evidence` (still a separate step from transcribing it into the domain CSV) |

| Flag | Default | Description |
|------|---------|-------------|
| `--evidence` | `""` | A link, photo description, who told you, a GPS track, etc. (`submit` only) |
| `--confidence` | `firsthand` | `firsthand` / `official_source` / `told_by_staff` / `secondhand` (`submit` only) |
| `--channel` | `cli` | Where this came from, e.g. `github_issue` when transcribing an issue (`submit` only) |
| `--notes` | `""` | Resolution notes, e.g. what CSV row or PR this became (`resolve` only) |
| `--pending-reports-file` | `data/pending_reports.csv` | The intake queue itself |

### `cli.py`

Two read-only views into the data's provenance, and one search. Trip planning
for a *named* objective is `plan.py`.

| Flag | Default | Description |
|------|---------|-------------|
| `--permit-sources [GROUP]` | all groups | Verification history for one permit group, or all |
| `--open-questions` | off | Every unconfirmed or conflicting fact currently derivable |
| `--campgrounds` | off | List campgrounds matching the filters below |
| `--access` | any | `drive_in` / `hike_in`. Campgrounds whose access nobody has recorded are excluded **and then listed** -- absent is not a value |
| `--type` | any | `family` / `group` / `backpack` |
| `--park` | any | Only campgrounds in this park |
| `--pets` | any | `allowed` / `not_marked`, matching the booking listing's own pets field. Both kinds of silence are excluded **and then listed separately**, because a listing left unmarked and a listing never read ask for different work |
| `--animal ANIMAL` | none | Which animal you are bringing. **Filters nothing** -- it asks each result the question and reports which rules govern that animal and which are written about another one |
| `--near LAT,LON` | none | Sort by straight-line distance from a point. Oakland City Hall is `37.8044,-122.2712` |
| `--within MILES` | none | With `--near`, drop matches beyond this distance |

All accept the same `--*-file` overrides as `plan.py` for pointing at
alternative datasets.

**Three things `--campgrounds` will not do**, all for the same reason the rest
of this project states its gaps rather than hiding them:

- **It does not drop what it cannot measure.** A campground with no
  coordinates is reported under `CANNOT BE PLACED`, not omitted. Omitting it
  would make "nothing is near you" and "nobody has looked" identical, which is
  the failure the scorecard already names for Q21. Every drive-in campground
  is placed; what is unplaced is backcountry.
- **It does not pretend a park centroid is a campsite.** Most coordinates here
  came off a ReserveAmerica *park* overview page, so `coord_precision` is
  `park` and the distance renders as "to the park, not the campground". Only
  Dumbarton Quarry has its own facility page, so only it reads "to the
  campground".
- **It does not give a park's point to every campground in that park.** A park
  coordinate is assigned when that point is a reasonable stand-in for where you
  arrive, and withheld when a source states a distance that makes it
  misleading, or when the campground has its own entrance. Anthony Chabot's
  point goes to all eight of its campgrounds; Del Valle's goes to one of five,
  because its four backpack camps sit 2 to 11.5 miles up the Ohlone Wilderness
  Trail. A blank that is a decision says so in `coord_source`, the same rule as
  an unsourced `access_mode`.

## Python Usage

The package exposes the loaders and geometry helpers `plan.py` is built on.

```python
from wayproof import load_peaks, ClusterConfig
from wayproof.pipeline import plan_trips
from wayproof.export import save_json

peaks = load_peaks("data/peaks.csv", list_filter="SPS",
                    collections_path="data/collections/sps.csv")
groups = plan_trips(peaks, ClusterConfig(eps_mi=6, miles_per_day=15, max_days=3))
save_json(groups, "out.json")
```

## Data

### Peak Data

Peak data is split into two files, per [`DATA_LICENSE.md`](DATA_LICENSE.md)'s
Source Policy: a public-domain-first **core** dataset, and an optional **SPS
collection** layered on top of it. This keeps a mountain's existence from
depending on a private compilation -- only its membership in the SPS
collection does -- and is the same architecture a future non-Sierra-Club
collection (a different range, a different list) would layer onto the same
core.

- **`data/peaks.csv`** (core, collection-agnostic): `name`, `latitude`,
  `longitude`, `elevation_ft`, `elev_estimated`, `coord_source`, `region`,
  the project-computed `nearest_trailhead`/`nearest_trailhead_side`/
  `nearest_trailhead_mi` access signal, and an optional `notes` field for a
  peak-specific data-quality flag (e.g. an unresolved SPS/non-SPS name
  conflict) -- scanned by `wayproof.reports.open_questions()`, see "The
  Scavenger Hunt". A peak's presence here depends only on having a name and
  a location.
- **`data/collections/sps.csv`** (the SPS collection): `list` (`SPS` or
  `non-SPS`), `section`, `class`, `emblem`, `mountaineers`, `mileage_rt`,
  `gain_ft`, `loss_ft`, `trailhead` (named route), `quad`, `benchmark`,
  `benchmark_rating` -- everything that comes specifically from the Sierra
  Club SPS program's own two source documents.

`wayproof.data_loader.load_peaks` joins the two by `name` when given a
`collections_path`; loading `data/peaks.csv` alone works too, just without
collection metadata. Both files are committed and ready to use; the
copyrighted Sierra Club source documents themselves are not redistributed
here. Download them yourself to rebuild; see
[`DATA_LICENSE.md`](DATA_LICENSE.md) and
[`data/source/README.md`](data/source/README.md).

| Source | Used for | Bundled? |
|--------|----------|----------|
| `sps_list_with_mileage.xls` (29th ed., 2025) | 247 SPS peaks: elevation, class, section, round-trip mileage, gain/loss, trailhead, USGS quad, emblem/mountaineers flags | No, Sierra Club copyright |
| `scrambler_ratings_non_sps_2025.pdf` | 354 non-SPS High Sierra peaks, labeled `non-SPS`, tracked but outside current SPS grouping defaults | No, Sierra Club copyright |
| USGS GNIS California + Nevada state files | Decimal lat/long for every peak, matched on name and USGS quad | Yes, public domain |

All 247 SPS peaks have coordinates: 240 from GNIS, including 14
spelling/wording aliases like *Foerster*/*Forester* and *Maclure*/*MacClure*,
and 7 unofficially named peaks (no GNIS entry) from peakbagger.com: Taylor
Dome, Spanish Needle, Rockhouse Peak, Cartago Peak, North Maggie Mountain,
Clyde Minaret, and Rogers Peak. Each row records its `coord_source`. The
peakbagger-sourced coordinates are a known third-party dependency tracked for
independent re-verification -- see [`DATA_LICENSE.md`](DATA_LICENSE.md).

Two peak names ("Mount Johnson", "Thunder Mountain") appear under both
`SPS` and `non-SPS` with conflicting data in the underlying source
documents; the SPS-list entry is kept for both files. See
[`DATA_LICENSE.md`](DATA_LICENSE.md) for that tie-break and the still-open
follow-up to independently resolve which value is correct.

#### Rebuilding The Dataset

Only needed to rebuild from scratch; requires the Sierra Club source documents
in `data/source/`, which are not bundled. The scripts print a download reminder
if they are missing.

```bash
# 1. Parse the Sierra Club sources -> data/sps_peaks.csv (staging, coords blank)
python scripts/build_dataset.py

# 2. Join GNIS coordinates (uses the committed Sierra subset)
python scripts/merge_gnis.py

# 3. Split the staging file into data/peaks.csv + data/collections/sps.csv
python scripts/split_collections.py
```

`scripts/merge_gnis.py` holds the curated alias map and the 7 manual
peakbagger coordinates. `data/source/gnis_sierra_summits.txt` is a trimmed
Sierra-box GNIS subset committed for reproducibility. `data/sps_peaks.csv` is
a git-ignored, rebuild-only staging file -- see
[`data/source/README.md`](data/source/README.md) for the full sequence,
including `scripts/assign_trailheads.py`.

### Trailheads

`data/trailheads.csv` is a curated list of major east-, west-, and crest-side
Sierra trailheads with lat/long coordinates, side of range, wilderness area,
land agency, `agency_id`, and `permit_group`. `land_agency` is a display string
(`Eldorado NF/LTBMU`); `agency_id` is the matching key (`eldorado_nf;ltbmu`,
semicolon-separated for co-managed land) that agency-scoped regulations resolve
against — see "Rules do not stop where permits do" above for why a trailhead
carries its own agency key rather than borrowing the permit's. Coordinates are to roughly 0.001 degrees and
spot-checked against public sources such as the PCTA and NPS.

Run:

```bash
python scripts/assign_trailheads.py
```

to add `nearest_trailhead`, `nearest_trailhead_side`, and
`nearest_trailhead_mi` (straight-line) columns to the `data/sps_peaks.csv`
build-staging file (see "Rebuilding The Dataset" above -- these end up in
the committed `data/peaks.csv` core dataset). The nearest-trailhead
assignment is an access signal and can be used for candidate grouping with
`--trailhead-field nearest_trailhead`; it is not proof of the actual approach
a user should take.

### Mountain Passes

`data/passes.csv` is the Sierra pass dataset, sourced from USGS GNIS feature
class `Gap`; see [`data/source/README.md`](data/source/README.md) to rebuild and
backfill elevations. Each pass carries a tier: tier 1 = named passes/cols
(default crossing set, and the points that define the crest line); tier 2 =
minor gaps/saddles.

Pass routing is opt-in and used only by `scripts/assign_trailheads.py`, which
regenerates the computed `nearest_trailhead` column. With `--use-passes`, a leg
between two points on opposite sides of the crest is evaluated through the
cheapest eligible pass rather than straight across the ridge.

```bash
python scripts/assign_trailheads.py --use-passes
```

The crest is approximated by a monotone longitude/latitude line fit over the
tier-1 passes, so peaks sitting almost on the crest can be assigned a side
coarsely; denser pass data (`merge_passes.py --add-all`) sharpens it.

Pass-aware routing is a coarse distance heuristic used by the experimental
grouping system. It does not turn the tool into a terrain-aware route planner.

### Input Schema

Minimum required columns are `name`, `latitude`, `longitude`, and
`elevation_ft`. Common aliases like `lat`, `lon`, and `elevation` are accepted.
The core file (`data/peaks.csv`) also optionally carries `elev_estimated`,
`coord_source`, and `nearest_trailhead`/`nearest_trailhead_side`/
`nearest_trailhead_mi`. Collection metadata comes from a separate file joined
by `name` via `load_peaks`'s `collections_path` argument (or
`--collections-file` on the CLI); the bundled SPS collection
(`data/collections/sps.csv`) carries `list`, `class`, `section`, `emblem`,
`mountaineers`, `mileage_rt`, `gain_ft`, `loss_ft`, `trailhead`, `quad`, and
`benchmark`/`benchmark_rating`. All of these flow through to the JSON export
as per-peak `attributes`. JSON input is also supported as a list of objects
or `{"peaks": [...]}` -- collection fields can simply be included inline in
that case, same as any other JSON peak record.

## Methodology, Rebuilding, And Development

### Project Layout

```text
wayproof/
├── plan.py                      # resolve logistics for named objectives (flagship)
├── report.py                    # submit/list/resolve data reports
├── cli.py                       # experimental candidate-grouping entry point
├── requirements.txt
├── data/
│   ├── sps_sample.csv            # 30-peak demo subset, used by tests
│   ├── peaks.csv                 # core: name, coordinates, elevation (collection-agnostic)
│   ├── collections/
│   │   └── sps.csv               # SPS collection: list, section, mileage, benchmark rating
│   ├── trailheads.csv            # trailheads incl. wilderness area / agency / permit_group
│   ├── permits.csv               # permit rules per permit_group
│   ├── release_policies.csv      # structured, computable permit release phases
│   ├── approaches.csv            # peak-specific approach/permit relationships
│   ├── permit_source_log.csv     # append-only source-verification audit trail
│   ├── campgrounds.csv           # backpack campgrounds (shared facilities)
│   ├── campsites.csv             # individually-bookable sites within a campground
│   ├── water_sources.csv         # named backcountry water sources
│   ├── water_source_log.csv      # append-only water-availability check ledger
│   ├── park_access.csv           # park-level entrance fees, gate hours, exemptions
│   ├── timed_entry.csv           # year-scoped vehicle timed-entry requirements
│   ├── permit_zones.csv          # bookable destination zones (quota by destination, not entry)
│   ├── regulations.csv           # rules in force, scoped by state / agency / permit group
│   ├── pending_reports.csv       # community/self submission intake queue (created on first use)
│   └── source/                   # official Sierra Club files + trimmed GNIS subset
├── scripts/
│   ├── build_dataset.py         # XLS + non-SPS PDF -> sps_peaks.csv (staging)
│   ├── merge_gnis.py            # join GNIS coordinates (name + quad)
│   ├── merge_coords.py          # generic GPX/KML/CSV/JSON coordinate joiner
│   ├── assign_trailheads.py     # nearest-trailhead access signals
│   ├── split_collections.py     # staging -> data/peaks.csv + data/collections/sps.csv
│   ├── build_gnis_gaps.py       # trimmed GNIS gap/pass source data
│   ├── merge_passes.py          # pass dataset assembly
│   ├── fill_pass_elevation.py   # pass elevation backfill helper
│   ├── parse_benchmarks.py      # benchmark route parser
│   └── build_site.py            # wayproof.dev static site (live open_questions())
├── wayproof/
│   ├── model.py
│   ├── data_loader.py
│   ├── distances.py
│   ├── approach.py
│   ├── passes.py
│   ├── permits.py
│   ├── access.py
│   ├── release_policy.py
│   ├── camping.py
│   ├── water.py
│   ├── park_access.py
│   ├── permit_zones.py
│   ├── regulations.py
│   ├── timed_entry.py
│   ├── reports.py
│   ├── plan.py
│   ├── views.py                  # page view models (one dict per published page)
│   ├── render.py                 # HTML / Markdown / JSON renderers over a view
│   └── visualize.py
└── tests/
    ├── test_pipeline.py
    ├── test_permits.py
    ├── test_plan.py
    ├── test_facilities.py
    ├── test_timed_entry.py
    ├── test_reports.py
    └── test_split_collections.py
```

Run the tests:

```bash
python -m pytest tests/
```

### Notes, Assumptions, And Extension Points

- **Straight-line distance.** Where distances are computed at all, they are
  great-circle, optionally through a pass. They do not model cliffs, technical
  terrain, or trail topology, and are not a substitute for a mapping tool.
- **Permits** are a planning aid, not a booking system. `data/permits.csv` is a
  manually curated snapshot of quota seasons, reservation windows, and lottery
  timing, which agencies change from year to year. It does not call
  recreation.gov or check live availability.

## License And Data

The source code is licensed under the [MIT License](LICENSE).

The data has separate provenance and terms; see
[`DATA_LICENSE.md`](DATA_LICENSE.md), including its Source Policy section
explaining the project's federal-data-first sourcing tiers and how every
data file is classified (`public_domain` / `open_license` / `project_created`
/ `third_party_reference_only`). Sierra Club source documents in
`data/source/` are copyrighted and are not redistributed here. Peak data derives
from the Sierra Club SPS list and USGS GNIS; map tiles are © OpenStreetMap
contributors / OpenTopoMap (CC-BY-SA) / Esri.

## Contributing

Contributions welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) and
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). Please run the tests and cite
sources for data corrections.
