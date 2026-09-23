---
name: wayproof-route-modeling
description: Model or correct Wayproof access points, routes, route segments, trail topology, mileage, endpoints, alternatives, spurs, directionality, traversals, or route-connected facilities. Use whenever a task asks how a traveler enters, moves through, diverts from, or completes a route; never infer those relationships from proximity.
---

# Wayproof route modeling

## Establish the planning question

Identify the endpoints and traveler outcome before adding geometry. Examples
include reaching a trail from parking, traversing a corridor in either direction,
choosing a water-bearing alternate, or detouring to a campsite.

Read `references/topology-patterns.md`, the route/access sections of
`ARCHITECTURE.md`, and existing traversal tests. Follow
`../wayproof-source-ingestion/SKILL.md` for provenance and ChangeSet creation.

## Audit existing topology

- Resolve existing places, access points, routes, segments, facilities, and
  aliases first.
- Before claiming route depth or completeness, inspect available official maps,
  map PDFs, trail guides, elevation profiles, and detailed route descriptions.
  Record a disposition when an applicable map or guide is deferred.
- Inspect source-backed endpoint, route-membership, `approached_via`, and
  traversal relationships.
- Exercise the read or traversal service from both requested endpoints. A list
  of individually valid segments may still be disconnected.
- Distinguish incomplete topology from an invalid route assertion.

## Match assertions to map evidence

- A printed mileage label or explicit route description can support distance;
  do not calculate canonical trail mileage from map scale or drawn geometry.
- A clearly drawn, labeled connection can support topology, but visual proximity
  alone cannot support access, membership, or traversal.
- A geospatial PDF, official coordinate, or inspected image metadata can support
  geometry at its stated precision; it does not prove a route connection.
- Treat a user-dropped or estimated pin as approximate evidence and preserve its
  reporter and observation context. Do not silently upgrade it to an official
  location.
- Record the map title, publisher, edition or effective date when available,
  page or panel, and retrieval context so later map revisions can be compared.
- Keep winter, summer, stock, bicycle, water, and other mode- or season-specific
  routes distinct unless evidence explicitly establishes shared segments.

## Model the graph

1. Represent parking, gates, walk-in entrances, staging areas, and transit
   access as explicit access entities when supported.
2. Represent the named route independently from the physical segments used to
   traverse it.
3. Give segments explicit endpoints, ordering or connectivity, directionality,
   and sourced distance when the evidence supplies them.
4. Model parallel routes and alternatives as distinct paths between evidenced
   junctions. Preserve their individual mileage and facility implications.
5. Model camps, water, toilets, peaks, and other resources as places connected
   by evidenced spurs or route relationships—not as implicit mainline points.
6. Keep partial endpoints, unknown distances, and uncertain junctions explicit.
   Do not add a synthetic segment merely to make a test pass.
7. Keep a route usable in both directions when evidence supports it. Encode
   one-way restrictions explicitly rather than relying on segment order.

## Validate consumer behavior

- Test complete ordered traversal, known-distance totals, alternatives, spur
  costs, and both directions where applicable.
- Test that a nearby but unconnected entity is not selected as an access point.
- Test partial answerability when a connection or mileage is genuinely missing.
- Verify planning output preserves source evidence and recheck needs for dynamic
  facilities along the route.
- Inspect generated route and related-place pages to ensure the graph is useful
  to consumers rather than merely schema-valid.

Before describing a promised route scope as route-complete, answer its relevant
planning questions: where travelers enter, how endpoints connect, whether each
supported direction traverses, which alternatives and spurs exist, what their
distance costs are, and how route-connected water, toilets, camps, parking, and
other requirements are reached. Preserve unanswered questions as explicit gaps.
