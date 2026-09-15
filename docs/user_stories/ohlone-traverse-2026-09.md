# User stories: Ohlone Wilderness traverse, 5–6 September 2026

Drawn from a **completed** trip, so every expected answer below is known rather
than imagined. That is the point: a story without a verified answer is a wish,
and a schema can only be judged against answers somebody can check.

## Ground truth

| | |
|---|---|
| Route | Ohlone Wilderness Regional Trail, **east to west** |
| Entry | Del Valle (Lichen Bark), Del Valle Regional Park |
| Exit | Stanford Ave Staging Area, Mission Peak Regional Preserve |
| Distance | 28.92 mi, 7,867 ft ascent, over two days |
| Nights | Fri car camp at Del Valle site 083; Sat at Sunol Backpack Camp, Eagles Aerie |
| Actual cost | **$97.00** ($46 backpack camp, $8 change fee, $43 car campsite) |
| Land manager | East Bay Regional Park District |

Mission Peak sits on the route and **the summit was skipped**. The objective was
the traverse.

---

## The stories

### S1 — A traverse has two ends
**As** someone walking the Ohlone Trail east to west, **I want** to know what
governs my trip, **so that** I can book both ends.

**True answer.** Entry is Del Valle, exit is Stanford Ave, ~29 miles apart, in
two different park units. Both need arrangements, and they are different
arrangements.

**Today.** `plan.py "Mission Peak"` names one trailhead, Stanford Ave. There is
no way to express an entry and an exit. `Cluster.trailhead` is a single field.

**Exposes.** The schema assumes out-and-back. A point-to-point traverse is a
normal objective, not an edge case.

**Fixed 2026-09-15 — the two ends, not the middle.** `plan.py "Mission Peak"
--exit "Del Valle"` now resolves both ends:

```
Access
  Entry: Stanford Ave Staging Area  (west side)
  Exit: Del Valle (Lichen Bark)  (east side)
  ENDS ONLY, NOT THE ROUTE BETWEEN THEM: ...

Cost
  Park entrance (Del Valle Regional Park (at the exit)): $10 (weekends & holidays,
    April through Labor Day)
```

That `$10` was in `park_access.csv` from the start and reachable from nothing,
which is the same held-and-hidden shape as S2's campsite fee. Route shape is
derived from whether a plan names one end or two rather than stored: which end
you finish at is a choice, not a fact about the terrain. Scorecard Q5 moved
`no-model` → `declined` — declining is not answering, and a default plan still
names no exit.

**What is still open**, and why this story is not deleted: the route *between* the
ends. Two endpoints do not determine the path, so an agency boundary crossed in
the middle is unresolved, and the `29 miles apart` part of the true answer is not
computed. That needs the route entity S8 describes. The party's own $46 backpack
camp and $43 Del Valle campground were already handled by S2.

---

### S2 — The fee answer is wrong, not merely incomplete
**As** someone planning this trip, **I want** to know what it will cost, **so
that** I can budget and book.

**True answer.** $15/night per backpack site plus an $8 non-refundable
reservation fee; $10 flat entry at Del Valle on weekends and holidays, April
through Labor Day; $5 parking at Sunol on weekends and holidays. Actual total
$97.

**Today.** The permit block says **"Fee: Free"** and "Day hikers to
non-wilderness peaks generally need nothing else." The campsite fee does appear,
but under Facilities, several lines below a headline saying the trip is free.

**Exposes.** Fees live on the permit. When the permit is free and the cost is
elsewhere, the headline is false. This trip cost $97 and the tool says free.

**Fixed 2026-09-15.** `plan` now leads with a `Cost` section naming every
component that charges, and the permit's own line reads `Permit fee:` rather
than `Fee:`. A fee field is three-valued -- charges, free, or *unknown* -- so
Del Valle Family Campground's blank fee, which took $43 of the $97, renders as
"NO FEE ON FILE -- absent is not free" instead of vanishing. No total is
computed: the figures are prose from three operators in three shapes. The
entry-end charges are still missing, because S1 is still open.

---

### S3 — What gates the trip is not a permit
**As** a backpacker, **I want** to know what I must obtain before going, **so
that** I do not arrive without it.

**True answer.** There is **no backpacking permit** for the Ohlone Wilderness.
What gates the trip is a campsite reservation, and it must be made **by phone**:
1-888-327-2757 option 2, 9am–4pm Pacific, closed weekends and holidays. Backpack
sites cannot be booked online.

**Today.** "No wilderness permit required" is technically true and practically
misleading. The phone-only channel appears as a campground attribute, not as the
thing standing between you and the trip.

**Exposes.** `permit_group` is the spine of the model, and here the binding
constraint is a campground booking. The model has no concept of "the scarce
thing you must secure", only of "the permit".

---

### S4 — One booking is a precondition for another
**As** someone leaving a car at the western end, **I want** to know whether I
can park there overnight, **so that** my shuttle works.

**True answer.** Overnight parking at Stanford Ave is not allowed **without a
permit obtained while making the camping reservation**. You cannot get it
separately. Overnight parking at Ohlone College is not allowed at all. The
parking pass covers the reservation's check-in and check-out dates, so the
reservation dates must match the days each car is parked.

**Today.** Nothing models this. The tool reports Stanford Ave as a trailhead
needing no permit.

**Exposes.** A dependency between two bookings, where one is only obtainable
during the other. Nothing in the schema can express "B is a byproduct of A".

---

### S5 — Capacity constrains the party, before quota does
**As** a group of four, **I want** to know which sites can hold us, **so that**
I book one that fits.

**True answer.** Sunol Backpack Camp sites vary: Sky Camp 3, Cathedral 5, Hawks
Nest 5, Oak View 5, Sycamore 5, Eagles Aerie 10, Stars Rest 30.

**Today.** `campsites.csv` holds capacity for three Sunol sites. `plan.py` names
a campground but not which sites fit a given party.

**Exposes.** Party size is modelled as a *regulation* (group size limits) but not
as a *booking constraint*. They are different questions.

---

### S6 — Closed is not the same as absent
**As** someone planning water and shelter, **I want** to know what is shut,
**so that** I do not plan around it.

**True answer.** The Sunol Visitor Center and the family, school and group
campsites are closed. They washed out roughly fifteen years ago and have no
running water.

**Today.** Not represented. A closed facility and one that never existed are
indistinguishable.

**Exposes.** No lifecycle on facilities. This is the same class of gap as a
regulation that reads as permission through silence.

---

### S7 — Water is the plan, and the schema handles it
**As** someone on an exposed ridge, **I want** to know where water is and when
it was last checked, **so that** I can size my carry.

**True answer.** All water is non-potable; filter, treat or boil. Seven sources
were confirmed available in an EBRPD update dated 2 September 2026: Stromer
Springs, Boyd Camp, Stewart's Camp, Maggie's Half Acre, Doe Camp, Sunol Backpack
Camp, Eagle Springs. All spigots checked on the trip were working, lever-operated
and gravity-fed.

**Today.** `water_sources.csv` plus the dated `water_source_log` model this
correctly, and the trip confirms the design: a later check never overwrites an
earlier one.

**Exposes.** Nothing. **This part of the schema is right** and this story is here
to keep it that way.

---

### S8 — The objective is not a peak
**As** someone hiking the Ohlone Trail, **I want** to plan the trail, **so
that** I do not have to name a summit I am not climbing.

**True answer.** The objective was the traverse. The party skipped the Mission
Peak summit deliberately.

**Today.** `plan.py` takes peak names only. The Ohlone Trail cannot be named.
The only way in is to ask about a summit you may not visit.

**Exposes.** The atom of the data model is a peak. The atom of this trip is a
route. Every other finding in this document follows from that.

---

### S9 — Booking opens months ahead, on its own calendar
**As** someone wanting a wildflower-season trip, **I want** to know when to
book, **so that** I do not miss the window.

**True answer.** For late April through May, reservations open in December for
the January–June period. The exact date is published late in the preceding
October.

**Today.** `release_policies.csv` models release windows for wilderness permits.
Campgrounds have `reservation_method` as prose.

**Exposes.** The release-phase model is the right shape and is wired to the
wrong entity. A campground booking has a release calendar too.

---

## What this trip says about the schema

Two things, and they point opposite ways.

**The evidence, water and regulation machinery is sound.** S7 passes outright.
Dated checks, non-overwriting history, scoped rules: the shapes match reality.

**The access and objective machinery does not match the domain.** S1, S3, S4 and
S8 are all the same error seen from different sides. The model is
*peak → one trailhead → one permit*. This trip is *route → two entry points → a
campground booking that emits a parking permit*. No amount of data entry fixes
that; the shape is wrong.

**And one answer is not merely incomplete but false.** S2. The tool says a $97
trip is free. That is the only finding here that harms someone today.
