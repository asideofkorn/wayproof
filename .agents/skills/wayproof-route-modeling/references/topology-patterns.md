# Route-topology patterns

## Access to a route

```text
parking/staging/access point -> evidenced approach -> route endpoint or junction
```

Do not connect parking directly to a route because coordinates are close. Use an
official map, directions, trail description, or dated field evidence.

## Mainline with a spur

```text
junction A -> mainline segment -> junction B
                  |
                  +-> spur -> water/camp/restroom
```

Keep spur distance separate from mainline distance. A nearby facility may still
require a diversion.

## Parallel alternatives

```text
junction A -> official mainline --------> junction B
          \-> alternate via facility --->/
```

Retain both paths and their distances. The alternate may be longer but preferable
because it reaches water, sanitation, shelter, or another requirement.

## Named route over physical segments

A named trail can traverse many physical segments and jurisdictions. Model its
identity once, then attach ordered sourced membership. Mile markers or map labels
do not prove that every pair is connected by one leg; add supported intervening
legs.

## Directionality

Segment storage order is not a travel restriction. When travel is supported in
both directions, the resolver should traverse the graph both ways. Record
one-way travel only from explicit evidence.

## Partial graph

When a junction, connector, or distance is unclear, preserve known segments and
expose a gap. A partial graph that explains its limit is preferable to an
invented complete-looking route.
