# DRAFT — user stories: a Sierra overnight permit trip

> ## ⚠ NOT GROUND TRUTH YET
>
> The Ohlone story opens by setting the standard this file does not yet meet:
>
> > *Drawn from a **completed** trip, so every expected answer below is known
> > rather than imagined. That is the point: **a story without a verified answer
> > is a wish**, and a schema can only be judged against answers somebody can
> > check.*
>
> **Every `True answer` below is blank on purpose.** No firsthand Sierra trip
> exists in this repository. All 55 entries in `permit_source_log.csv` are desk
> research — screenshots, pasted page text, uploaded PDFs, web search, one
> maintainer decision — across 14 distinct `method` values, and **not one is a
> field observation**. The only firsthand evidence anywhere in `data/` is the
> Ohlone trip's water log.
>
> Filling these in from anything other than a trip you actually took would put
> invented ground truth into the one document whose entire value is that its
> answers are checkable.
>
> **What *is* verified here is the `Today` column.** Every one was captured by
> running `plan.py` against this commit. Those are facts about the tool, and they
> are what makes filling in the rest mechanical rather than open-ended.
>
> `Exposes` is stated only where the defect is provable from the code or data
> without knowing the trip's answer. Where it depends on the answer, it says so.

---

## Ground truth — TO BE FILLED FROM A COMPLETED TRIP

| | |
|---|---|
| Route | _TODO_ |
| Objective(s) | _TODO — and whether a summit was actually reached_ |
| Entry | _TODO_ |
| Exit | _TODO — same as entry, or not_ |
| Dates | _TODO — entry date, exit date, nights out_ |
| Party size | _TODO_ |
| Permit(s) actually carried | _TODO — product name, and how it was obtained_ |
| When it was booked | _TODO — and whether the window was nearly missed_ |
| Actual cost | _TODO — every line, including parking and any change fee_ |
| Land manager(s) | _TODO — all of them, if the route crossed a boundary_ |
| Anything that surprised you | _TODO — this is usually where the findings are_ |

**Suggested anchor if you have a choice.** A trip that crosses an agency
boundary on one continuous permit (Onion Valley → Kearsarge Pass → SEKI, or
Shepherd Pass) would exercise the most unvalidated machinery in the repo:
interagency reciprocity, the 60/40 rolling release, and a per-trail quota. A
Whitney Zone trip instead exercises the lottery and the
`whitney_zone` / `inyo_jmw_aaw` split. Desolation exercises destination zones.
None of the three has ever been checked against a trip.

---

## The stories

### S1 — Party size and nights are not inputs, but almost every Sierra fee depends on them
**As** a party of four out for three nights, **I want** to know what the permit
costs us, **so that** I can collect the money before we go.

**True answer.** _TODO_

**Today.** `plan.py` accepts objectives and a single `--date`. There is no flag
for party size and none for number of nights. Meanwhile the fees it prints are:

```
inyo_jmw_aaw   $6/permit + $5/person ($15/person if the trip enters or exits via the Mt. Whitney Zone)
hoover         $8/person ages 13+ (12 and under free) plus $6 non-refundable service fee per permit
desolation     $5 for the 1st night, $10 for 2-14 nights ... capped at $100 per permit
seki           $15/trip + $5/person within quota season
```

**Exposes.** *(provable; no ground truth needed)* The cost section added in #33
deliberately does not total its components, and the stated reason is that the
figures are prose. That is true but incomplete: even parsed perfectly, **the
inputs do not exist**. Three of the four fees above are per-person, two are
per-night, and one changes if the route touches the Whitney Zone. This is the
Sierra form of Ohlone S5 — party size modelled as a *regulation* (group-size
limits) but never as a *booking parameter*.

---

### S2 — The rules that get you fined are not in the answer
**As** someone entering Desolation Wilderness, **I want** to know what I must
carry, **so that** I do not arrive with the wrong food storage.

**True answer.** _TODO — did you carry a canister, and did anyone check?_

**Today.** `regulations_for()` resolves **18 regulations** for `desolation`,
including `desolation-bear-canister`: a hard-sided container is **required**,
with fines to $5,000 under 36 CFR 261.58(cc). The website renders all 18 on
every Desolation trailhead page.

`plan.py "Mount Tallac"` mentions the word *canister* **zero times**. It prints
no regulations at all — the count of `Rules in force` / campfire / canister
mentions in its output is 0 for every objective.

**Exposes.** *(provable)* The flagship command omits the highest-consequence
data the project holds. `resolve_plan()` takes no `regulations` argument, so the
subsystem is wired to the website and not to the tool. The same is true of
`permit_zones` — see S3.

**Fixed 2026-09-15.** `resolve_plan()` now takes `regulations` and `plan` prints
a `Rules in force` section: all 18 Desolation rules with their citations and
scope labels. The question has a second half the first fix missed — its own
"wrong if" is about the *document*, not the equipment — so `permits.csv` gained a
`carry` column, a sibling of `excludes` for the same reason, and the plan now
leads the permit block with `MUST CARRY: ... a digital or paper reservation
CONFIRMATION is NOT a valid permit`. Scorecard Q6 moved 0 → 35 answered, 42
partial; `omitted` across the whole board went to 0. `permit_zones` is still
unwired, so S3 stands.

---

### S3 — A Desolation permit is booked by destination, not by trailhead
**As** someone booking Desolation, **I want** to know which of the 45 zones to
select, **so that** I can complete the reservation at all.

**True answer.** _TODO_

**Today.** `plan.py "Mount Tallac"` names the permit, the fee, the season and
the release date, and never mentions a destination zone. `data/permit_zones.csv`
holds 46 rows; `resolve_plan()` does not load them. The quota season, the
first-night rule and the zone count are present in `permits.csv` prose but not
as an instruction to pick one.

**Exposes.** *(provable)* You cannot complete the booking from this output. The
README documents zones at length as a deliberately separate entity; the planner
does not see them.

---

### S4 — A lottery deadline is months before the trip and cannot be recovered
**As** someone who wants Whitney in July, **I want** to know the last date I can
act, **so that** I do not discover in June that it closed in March.

**True answer.** _TODO — when did you apply, and did you get it?_

**Today.** Verified output for `--date 2027-07-15`:

```
Status: Lottery for 2027 opens Feb 1; apply by Mar 1.
Note: One results date only: March 15. Daily quota is 100 people/day for Day Use
permits and 60 people/day for Overnight permits.
```

**Exposes.** *(contingent on the answer)* The dates are computed and stated, and
this may well be right. What a trip would settle is whether the *unclaimed*
release on Apr 22 and the day-of cancellation path — both in `notes`, neither
computed — are what someone actually uses when they miss the lottery, which is
the common case.

---

### S5 — One trailhead, two permits: both, or a choice?
**As** someone climbing Whitney and Russell from Whitney Portal, **I want** to
know which permits to buy, **so that** I am not turned back at a checkpoint.

**True answer.** _TODO_

**Today.** Verified output for `Mount Whitney` + `Mount Russell`:

```
Cost
  THIS TRIP IS NOT FREE -- 2 of 2 components carry a fee.
  Permit (Mount Whitney Zone Permit ...): $15/person lottery-claim/reservation fee ...
  Permit (Inyo NF Wilderness Permit ...): $6/permit + $5/person ($15/person if the
    trip enters or exits via the Mt. Whitney Zone)
```

**Exposes.** *(partly provable)* The two entries are listed without stating
whether they are **both required** or **alternatives** — the second is labelled
"for Mount Russell only", which reads either way. And the Inyo fee is
conditional on the Whitney Zone, an interaction between the two rows that
nothing resolves: the tool prints both prices and leaves the reader to work out
which applies. The cost roll-up counts them as two charges, which assumes
both-required.

---

### S6 — Does my permit cover the leg in the next agency's land?
**As** someone crossing Kearsarge Pass from Inyo NF into SEKI, **I want** a
yes/no on a second permit, **so that** I can stop worrying about it.

**True answer.** _TODO — did anyone ask to see a permit on the park side?_

**Today.** Verified output for an Onion Valley objective:

```
Crosses into other land: Honored for continuous travel into neighboring parks:
Yosemite NP (...) and Sequoia & Kings Canyon NP (Taboose, Sawmill, Baxter,
Shepherd Pass, Kearsarge Pass, Cottonwood Pass corridors) — no separate NPS
permit needed. Per the official page: this requires *continuous* wilderness
travel: a break ... requires a new permit ...
```

**Exposes.** *(provable)* The answer exists and is good, but it is a paragraph
of prose in `interagency_note`, not a resolved yes/no for *this* route. The
corridor list is a sentence, so nothing can check whether the route you named is
on it. `permits.py`'s module docstring reasons about reciprocity at length; none
of that reasoning is computable.

---

### S7 — Off season is a different product, not a discount
**As** someone going in December, **I want** to know how the permit works then,
**so that** I do not turn up expecting a self-issue kiosk.

**True answer.** _TODO_

**Today.** `--date 2027-12-15` for Whitney gives:

```
Status: Reservations open 2027-12-01 -- mark your calendar.
```

**Exposes.** *(contingent)* This is the off-season phase resolving correctly at
a 14-day offset, which is the behaviour `release_policies.csv` intends. Worth a
story because `open_questions()` currently reports five quota'd groups with **no
off-season phase on file**, where the tool falls back to asserting
"free/self-issue, no reservation" — an assumption the project has already found
wrong twice. A December trip on one of those five would settle it.

---

### S8 — Was the entry-point flag right?
**As** a user, **I want** the tool to be unsure only when it should be, **so
that** I do not learn to ignore the warning.

**True answer.** _TODO — which trailhead did you actually start from?_

**Today.** `entry_conflicts` flags **153 of 247** SPS objectives, relabelling the
permit "CANDIDATE ONLY". For the remaining 94, the answer is stated plainly.

**Exposes.** *(needs the answer)* This is the single most valuable thing a trip
could check, and it cannot be checked any other way. If your objective was
flagged and the geometry was in fact right, the flag is too loud at 62%. If it
was *not* flagged and the entry was wrong, `names_same_place` is too generous —
one such case is already known: **Lamont Peak** matches trailhead `Indian Wells
Canyon (Owens Peak)` on the shared token `peak`, because `_tokens`'
noise list omits `peak`, `mount` and `mountain`.

---

### S9 — Something that works, recorded so it stays working
**As** a maintainer, **I want** the parts that match reality pinned, **so that**
a refactor cannot quietly undo them.

**True answer.** _TODO_

**Today.** Inyo's split release computes both dates, not just the first:

```
Status: Reservations open 2026-12-31 (07:00 America/Los_Angeles) -- mark your
calendar. A further 40% release opens 2027-06-17 (07:00 America/Los_Angeles).
```

**Exposes.** *(contingent)* Ohlone S7 exists to protect the water model; this
slot is reserved for whichever Sierra machinery the trip confirms. The 60/40
release is the strongest candidate — it is the one piece of permit timing that
is fully structured rather than prose — but a trip has to confirm the second
date is real before this becomes a keep-it-this-way story.

---

## What to do with this file

1. Fill the ground-truth table from a trip you have taken.
2. Answer each `True answer`. Where you cannot, delete the story — an
   unanswerable story is the wish this document warns about.
3. Re-run each `Today` against the then-current commit; several will have moved.
4. Rename to `sierra-<route>-<yyyy-mm>.md`, matching
   `ohlone-traverse-2026-09.md`, and **delete this banner**.

Until step 4, this file is a question list, not evidence, and nothing in the
codebase should cite it.
