const BASEMAPS = {
  topo: ["https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}", "USGS The National Map"],
  aerial: ["https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}", "USDA, USGS The National Map: Orthoimagery"],
  "aerial-labels": ["https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile/{z}/{y}/{x}", "USGS The National Map: Orthoimagery and US Topo"],
};
const COLORS = { boundaries: "#c78c3c", routes: "#1d9f89", peaks: "#d45f4c", access: "#508bd2", camping: "#9b78d0", facilities: "#e0b64c" };

function coordinates(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Point") return [geometry.coordinates];
  if (["LineString", "MultiPoint"].includes(geometry.type)) return geometry.coordinates;
  if (["MultiLineString", "Polygon"].includes(geometry.type)) return geometry.coordinates.flat();
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat(2);
  return [];
}

function showSelection(container, features) {
  const panel = container.querySelector("[data-map-selection]");
  const unique = [...new Map(features.map(feature => [`${feature.properties.entity_id}:${feature.properties.claim_id || feature.properties.segment_id || "geometry"}`, feature])).values()];
  panel.replaceChildren();
  const title = document.createElement("strong");
  if (!unique.length) {
    title.textContent = "Select a feature";
    const note = document.createElement("p");
    note.textContent = "Tap or click a route, place, or facility to inspect it.";
    panel.append(title, note);
    return;
  }
  title.textContent = unique.length === 1 ? "Selected feature" : `${unique.length} features here`;
  const list = document.createElement("ul");
  for (const feature of unique.slice(0, 12)) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = feature.properties.url;
    link.textContent = feature.properties.name;
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = `${feature.properties.kind.replaceAll("_", " ")} · ${feature.properties.evidence_status}`;
    item.append(link, meta);
    list.append(item);
  }
  panel.append(title, list);
}

async function loadExploreMap(container) {
  const canvas = container.querySelector("[data-map-canvas]");
  const status = container.querySelector("[data-map-status]");
  try {
    const [module, response] = await Promise.all([import("/assets/vendor/maplibre/maplibre-gl.mjs"), fetch(container.dataset.geometryUrl)]);
    if (!response.ok) throw new Error("Map data unavailable");
    const maplibregl = module;
    const data = await response.json();
    const sources = Object.fromEntries(Object.entries(BASEMAPS).map(([id, value]) => [`basemap-${id}`, { type: "raster", tiles: [value[0]], tileSize: 256, maxzoom: 16, attribution: value[1] }]));
    const layers = Object.keys(BASEMAPS).map(id => ({ id: `basemap-${id}`, type: "raster", source: `basemap-${id}`, layout: { visibility: id === "topo" ? "visible" : "none" } }));
    const map = new maplibregl.Map({ container: canvas, style: { version: 8, sources, layers }, center: [-119.2, 37.5], zoom: 5.2, attributionControl: false, dragRotate: false, pitchWithRotate: false });
    map.touchZoomRotate.disableRotation();
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.on("load", () => {
      map.addSource("wayproof", { type: "geojson", data });
      for (const layer of Object.keys(COLORS)) {
        const layerFilter = ["==", ["get", "layer"], layer];
        const polygonFilter = ["all", layerFilter, ["==", ["geometry-type"], "Polygon"]];
        const lineFilter = ["all", layerFilter, ["==", ["geometry-type"], "LineString"]];
        const pointFilter = ["all", layerFilter, ["==", ["geometry-type"], "Point"]];
        const checked = container.querySelector(`[data-map-layer="${layer}"]`).checked;
        const layout = { visibility: checked ? "visible" : "none" };
        map.addLayer({ id: `wp-${layer}-fill`, type: "fill", source: "wayproof", filter: polygonFilter, paint: { "fill-color": COLORS[layer], "fill-opacity": 0.2 }, layout });
        if (layer === "routes") {
          map.addLayer({ id: "wp-routes-casing", type: "line", source: "wayproof", filter: lineFilter,
            layout: { ...layout, "line-cap": "round", "line-join": "round" },
            paint: { "line-color": "#0b1b18", "line-width": 8, "line-opacity": 0.82 } });
        }
        map.addLayer({ id: `wp-${layer}-line`, type: "line", source: "wayproof", filter: lineFilter,
          layout: { ...layout, "line-cap": "round", "line-join": "round" },
          paint: { "line-color": COLORS[layer], "line-width": layer === "routes" ? 5 : 2 } });
        map.addLayer({ id: `wp-${layer}-point`, type: "circle", source: "wayproof", filter: pointFilter, paint: { "circle-color": COLORS[layer], "circle-radius": layer === "camping" ? 4 : 6, "circle-stroke-color": "#fff", "circle-stroke-width": 1.5 }, layout });
      }
      const points = data.features.flatMap(feature => coordinates(feature.geometry));
      if (points.length) {
        const bounds = points.reduce((result, point) => result.extend(point), new maplibregl.LngLatBounds(points[0], points[0]));
        map.fitBounds(bounds, { padding: 45, maxZoom: 12, duration: 0 });
      }
      status.textContent = "Interactive map ready. Select a feature to inspect it.";
      container.classList.add("map-enhanced");
    });
    map.on("click", event => {
      const layerIds = Object.keys(COLORS).flatMap(layer => [`wp-${layer}-fill`, `wp-${layer}-line`, `wp-${layer}-point`]).filter(id => map.getLayer(id) && map.getLayoutProperty(id, "visibility") !== "none");
      showSelection(container, map.queryRenderedFeatures(event.point, { layers: layerIds }));
    });
    for (const button of container.querySelectorAll("[data-basemap]")) button.addEventListener("click", () => {
      for (const id of Object.keys(BASEMAPS)) map.setLayoutProperty(`basemap-${id}`, "visibility", id === button.dataset.basemap ? "visible" : "none");
      for (const candidate of container.querySelectorAll("[data-basemap]")) candidate.setAttribute("aria-pressed", String(candidate === button));
    });
    for (const checkbox of container.querySelectorAll("[data-map-layer]")) checkbox.addEventListener("change", () => {
      for (const suffix of ["fill", "line", "point"]) map.setLayoutProperty(`wp-${checkbox.dataset.mapLayer}-${suffix}`, "visibility", checkbox.checked ? "visible" : "none");
      if (checkbox.dataset.mapLayer === "routes") map.setLayoutProperty("wp-routes-casing", "visibility", checkbox.checked ? "visible" : "none");
    });
    const expand = container.querySelector("[data-map-expand]");
    expand.addEventListener("click", () => {
      const expanded = container.classList.toggle("is-expanded");
      expand.setAttribute("aria-expanded", String(expanded));
      expand.textContent = expanded ? "Close full screen" : "Full screen";
      document.body.classList.toggle("map-open", expanded);
      window.setTimeout(() => map.resize(), 50);
    });
  } catch (error) {
    status.textContent = "Interactive map unavailable. Downloadable GeoJSON remains available.";
  }
}

const container = document.querySelector("[data-explore-map]");
if (container) loadExploreMap(container);
