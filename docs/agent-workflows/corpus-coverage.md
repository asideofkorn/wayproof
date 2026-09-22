# Assessing canonical corpus coverage

This document describes how to assess coverage; it is not a hand-maintained list
of every published entity. Canonical records, validated ChangeSets, regression
tests, and generated website directories are authoritative.

## Coverage levels

Use these outcome-oriented levels when selecting a batch:

1. **Identity baseline** — durable identity, provenance, geographic scope, and
   operator or containment relationships.
2. **Visitor profile** — important activities, facilities, access policy, and
   stable operational facts.
3. **Planning depth** — evidenced entrances, route connections, reservations,
   rules, water and sanitation, and relevant alternatives answer a concrete
   planning question.
4. **Operational depth** — volatile conditions retain dates, history,
   answerability, and contextual pre-trip rechecks.
5. **Consumer verification** — read service, planner or MCP where relevant,
   tests, website, evidence history, and JSON agree.

A visitor profile is not complete planning depth. Detailed camping inventory
does not establish trail topology or live availability.

## Discover current coverage

Before adding data:

- Search `canonical/v0/entities/` for identity and aliases.
- Search claims and relationships by durable entity ID, not only display name.
- Search `changesets/v0/` for the intent and provenance of prior work.
- Search focused tests for consumer behavior already guaranteed.
- Inspect generated directories and entity pages through site tests or the
  deployed website.
- Consult `docs/canonical-planning-parity.md` for cross-surface planning gaps.

Useful high-depth fixtures include Del Valle, the Ohlone Wilderness Trail and
its access and booking context, Mission Peak access, and the source-backed East
Bay Regional Park batches. Treat these as patterns, not special schema branches.

## Select the next batch

Prioritize missing outcomes over record volume:

- access point -> evidenced route connection;
- route -> traversable ordered topology in supported directions;
- reservable facility -> capacity, booking channel, lead time, and current-check
  boundary;
- water or restroom -> identity, route relationship, dated status, and
  reliability limits;
- recreation -> activity- or equipment-specific rules and fees;
- volatile condition -> affected entity, temporal scope, retrieval context, and
  recheck;
- conflicting sources -> preserved claims plus an explicit conflict or gap.

Do not make every park equally deep by default. Deepen places needed by a real
planning scenario and add general tests that prevent destination-specific logic.

## Completion evidence

A batch is complete when:

- it answers the planning question or explains why the answer remains partial;
- material facts have a Source -> Observation -> Evidence -> Claim lineage;
- identities and relationships are not duplicated or proximity-derived;
- a validated ChangeSet exactly accounts for the canonical diff;
- focused and full tests pass; and
- relevant read, planning, MCP, and website surfaces agree.
