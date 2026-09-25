# ADR 0002: Interactive map rendering and basemap sources

- Status: Accepted
- Date: 2026-09-24
- Amended: 2026-09-25 — remove the contextless schematic fallback after
  production evaluation; retain textual route facts, status messaging, and the
  downloadable GeoJSON when the interactive map is unavailable.
- Decision owners: Wayproof maintainers
- Related: `PRODUCT.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `DATA_LICENSE.md`,
  `docs/adr/0001-versioned-source-geometry-for-route-maps.md`

## Context

ADR 0001 established that Wayproof publishes deterministic, route-specific
GeoJSON from reviewed and versioned source-geometry snapshots. The generated
website initially rendered that geometry as a dependency-free schematic. The
schematic is fast, accessible, printable, and resilient, but it does not show a
route in geographic context.

Visitors need to understand terrain, nearby roads and water, route shape, and
the relative locations of trailheads and facilities. The public site is static
and hosted on GitHub Pages, so the solution must run entirely in the browser.
It must not require a database or application server, weaken the evidence
boundary, or make a visually plausible alignment count as route evidence.

The initial public corpus is in the United States, primarily California public
lands. Wayproof also intends to support an installable offline PWA later. The
first map implementation should therefore avoid a renderer or data contract
that prevents future packaged basemaps, while avoiding premature offline tile
distribution now.

## Decision drivers

- Render Wayproof-generated GeoJSON on static GitHub Pages.
- Provide useful topographic and aerial context without an initial usage bill
  or visitor API key.
- Preserve geometry provenance, accuracy, review state, and fitness-for-use.
- Keep the canonical read projection independent of a particular basemap.
- Support mobile touch interaction and future foreground GPS positioning.
- Preserve accessible route facts and downloadable geometry for JavaScript
  failure, map-service outages, printing, and offline use without downloaded
  tiles.
- Avoid silently depending on commercial free-tier quotas or terms.
- Avoid bulk caching a public tile service as an offline-map strategy.

## Options considered

### 1. Keep only the generated schematic

Advantages:

- no runtime dependencies or third-party requests;
- deterministic and easy to test; and
- works offline and in print.

Disadvantages:

- no terrain, road, water, boundary, or aerial context;
- limited support for inspecting facility locations; and
- cannot naturally support map layers or device position later.

The schematic was initially retained as a fallback. Production evaluation found
that a contextless line did not provide enough planning value to justify its
page weight, so the amended decision removes it.

### 2. Leaflet with raster basemaps

Advantages:

- mature, small, and straightforward for raster tiles and GeoJSON; and
- broad plugin ecosystem.

Disadvantages:

- the planned vector-tile, PMTiles, styling, and GPS evolution would depend on
  additional plugins or a later renderer migration.

This is viable but not selected because MapLibre better fits the expected
offline and vector-map direction.

### 3. MapLibre GL JS with selected raster basemaps

Advantages:

- open-source browser renderer with native GeoJSON, raster, vector-tile, and
  style support;
- works on static pages;
- supports future PMTiles or other packaged vector sources; and
- provides a path to richer feature interaction and foreground GPS.

Disadvantages:

- a larger client dependency than the schematic;
- requires WebGL and JavaScript; and
- needs deliberate performance and accessibility fallbacks.

This is the selected renderer.

### 4. A commercial hosted map platform's free tier

Advantages:

- polished global styles, imagery, labels, and operational support; and
- simple hosted style configuration.

Disadvantages:

- quotas, account credentials, and terms can change;
- free usage may not remain appropriate as traffic grows; and
- offline redistribution rights and costs are separate concerns.

This is deferred. A commercial provider may be adopted later if international
coverage, reliability, imagery currency, or measured traffic justifies it.

### 5. Self-host all basemap and imagery data immediately

Advantages:

- maximum control over availability, styling, and offline packaging.

Disadvantages:

- significant generation, storage, bandwidth, update, and licensing work;
- aerial imagery is particularly large; and
- premature for current traffic and product maturity.

This is rejected for the initial implementation. Regional packaged maps remain
a later PWA decision.

## Decision

1. Wayproof will use MapLibre GL JS as its interactive browser map renderer.
2. MapLibre JavaScript and CSS will be hosted with the generated Wayproof site,
   not loaded from a runtime CDN.
3. The initial US basemap choices will be:
   - **Topo:** USGS The National Map `USGSTopo` raster service;
   - **Aerial:** USGS The National Map `USGSImageryOnly` raster service; and
   - **Aerial + labels:** USGS `USGSImageryTopo` raster service.
4. The interface will use the term **Aerial**, not **Satellite**, because the
   detailed contiguous-US imagery is primarily orthorectified aerial imagery,
   including NAIP, even though small-scale imagery may have satellite sources.
5. Wayproof will visibly attribute the active basemap and retain the geometry
   source, snapshot/version, accuracy, review state, and downloadable GeoJSON
   alongside the map.
6. Basemap pixels provide visual context only. Alignment with a road, trail, or
   image does not validate, promote, connect, or increase the confidence of a
   Wayproof geometry feature.
7. The interactive map will consume Wayproof's static generated GeoJSON. It
   will not query an upstream trail service in a visitor's browser.
8. Canonical identifiers will link selectable map features to the same detail
   pages and read projections used elsewhere. The map will not maintain a
   separate feature catalog.
9. Textual route information, explicit map-status messaging, and downloadable
   GeoJSON remain available for loading failure, map-service outage, printing,
   and use without a basemap. The contextless schematic is not retained.
10. Map code and aerial tiles will load lazily. Aerial imagery will not be
    requested until selected by the visitor.
11. The first implementation will use live USGS tiles. It will not bulk-cache
    those services for offline use. Future offline basemaps require a separate
    bounded regional-package and licensing decision; MapLibre should remain
    capable of rendering that later source.
12. A provider change does not require changing canonical knowledge or route
    GeoJSON. It requires review of attribution, licensing, availability,
    accuracy disclosure, privacy, cost, and offline rights.

## Initial implementation boundary

The first phase will:

- fix the mobile relationship diagram so labels remain horizontal;
- add self-hosted MapLibre assets;
- add Topo, Aerial, and Aerial + labels controls;
- overlay one existing generated route GeoJSON on the interactive map;
- fit the initial viewport to the route;
- preserve the existing accuracy warning and downloadable GeoJSON; and
- verify focused site-generation behavior plus desktop and mobile rendering.

It will not yet add selectable canonical facilities, maps to every entity type,
offline basemap packages, GPS positioning, or navigation claims.

## Consequences

Positive consequences:

- static route pages gain geographic context without a Wayproof server;
- no commercial account or per-view charge is required initially;
- the renderer can evolve toward vector tiles, PMTiles, and foreground GPS;
- published geometry remains deterministic and evidence-backed; and
- visitors retain useful route information during third-party tile outages.

Negative consequences:

- live maps depend on USGS service availability and browser WebGL support;
- imagery capture dates and resolution vary by location;
- the initial basemap choice is US-focused;
- self-hosted renderer assets add repository and site weight; and
- interactive behavior requires focused browser and accessibility testing.

USGS basemaps are not navigation guarantees. Wayproof maps remain planning and
evidence interfaces, and volatile access or closure information still requires
the appropriate recheck.

## Reconsideration triggers

Revisit this decision when one or more of the following is demonstrated:

- material coverage outside the United States;
- measured availability or performance problems with USGS services;
- a requirement for more current or differently licensed imagery;
- production traffic that justifies a supported commercial provider;
- proven offline regional-basemap requirements;
- privacy requirements that prohibit direct tile requests; or
- a different renderer materially improves accessibility, battery use, or
  supported-device coverage.
