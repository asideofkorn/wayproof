const BASEMAPS = {
  topo: {
    label: "Topo",
    tiles: [
      "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
    ],
    attribution: "USGS The National Map",
  },
  aerial: {
    label: "Aerial",
    tiles: [
      "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
    ],
    attribution: "USDA, USGS The National Map: Orthoimagery",
  },
  "aerial-labels": {
    label: "Aerial + labels",
    tiles: [
      "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile/{z}/{y}/{x}",
    ],
    attribution: "USGS The National Map: Orthoimagery and US Topo",
  },
};

function coordinates(geometry) {
  if (!geometry) return [];
  if (geometry.type === "Point") return [geometry.coordinates];
  if (geometry.type === "LineString" || geometry.type === "MultiPoint") {
    return geometry.coordinates;
  }
  if (geometry.type === "MultiLineString" || geometry.type === "Polygon") {
    return geometry.coordinates.flat();
  }
  if (geometry.type === "MultiPolygon") return geometry.coordinates.flat(2);
  if (geometry.type === "GeometryCollection") {
    return geometry.geometries.flatMap(coordinates);
  }
  return [];
}

function setStatus(container, message) {
  const status = container.querySelector("[data-map-status]");
  if (status) status.textContent = message;
}

const UNAVAILABLE_MESSAGE =
  "Interactive map unavailable. Downloadable route GeoJSON remains available below.";

async function enhanceRouteMap(container) {
  const mapElement = container.querySelector("[data-map-canvas]");
  const geometryUrl = container.dataset.geometryUrl;
  if (!mapElement || !geometryUrl) {
    setStatus(container, UNAVAILABLE_MESSAGE);
    return;
  }

  let maplibregl;
  try {
    maplibregl = await import("/assets/vendor/maplibre/maplibre-gl.mjs");
  } catch (error) {
    setStatus(container, UNAVAILABLE_MESSAGE);
    return;
  }

  let route;
  try {
    const response = await fetch(geometryUrl);
    if (!response.ok) throw new Error(`GeoJSON request failed: ${response.status}`);
    route = await response.json();
  } catch (error) {
    setStatus(container, UNAVAILABLE_MESSAGE);
    return;
  }

  const sourceDefinitions = Object.fromEntries(
    Object.entries(BASEMAPS).map(([id, definition]) => [
      `basemap-${id}`,
      {
        type: "raster",
        tiles: definition.tiles,
        tileSize: 256,
        minzoom: 0,
        maxzoom: 16,
        attribution: definition.attribution,
      },
    ]),
  );
  const basemapLayers = Object.keys(BASEMAPS).map((id) => ({
    id: `basemap-${id}`,
    type: "raster",
    source: `basemap-${id}`,
    layout: { visibility: id === "topo" ? "visible" : "none" },
  }));

  let map;
  try {
    map = new maplibregl.Map({
      container: mapElement,
      style: {
        version: 8,
        sources: sourceDefinitions,
        layers: basemapLayers,
      },
      center: [-119.5, 37.3],
      zoom: 5,
      attributionControl: false,
      dragRotate: false,
      pitchWithRotate: false,
    });
  } catch (error) {
    setStatus(container, UNAVAILABLE_MESSAGE);
    return;
  }
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

  map.on("load", () => {
    const points = route.features.flatMap((feature) => coordinates(feature.geometry));
    if (!points.length) {
      setStatus(container, UNAVAILABLE_MESSAGE);
      return;
    }

    map.addSource("wayproof-route", { type: "geojson", data: route });
    map.addLayer({
      id: "wayproof-route-casing",
      type: "line",
      source: "wayproof-route",
      paint: {
        "line-color": "#0b1b18",
        "line-width": 8,
        "line-opacity": 0.82,
      },
    });

    map.addLayer({
      id: "wayproof-route",
      type: "line",
      source: "wayproof-route",
      paint: {
        "line-color": "#27a78d",
        "line-width": 5,
      },
    });
    map.on("click", "wayproof-route", (event) => {
      const feature = event.features && event.features[0];
      const segmentId = feature && feature.properties.segment_id;
      if (!segmentId) return;

      const content = document.createElement("div");
      const heading = document.createElement("strong");
      heading.textContent = "Canonical route segment";
      const link = document.createElement("a");
      link.href = `/knowledge/${encodeURIComponent(segmentId)}/`;
      link.textContent = segmentId;
      content.append(heading, document.createElement("br"), link);
      new maplibregl.Popup()
        .setLngLat(event.lngLat)
        .setDOMContent(content)
        .addTo(map);
    });
    map.on("mouseenter", "wayproof-route", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "wayproof-route", () => {
      map.getCanvas().style.cursor = "";
    });
    map.addSource("wayproof-endpoints", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: [
          { type: "Feature", properties: { role: "start" }, geometry: { type: "Point", coordinates: points[0] } },
          { type: "Feature", properties: { role: "destination" }, geometry: { type: "Point", coordinates: points[points.length - 1] } },
        ],
      },
    });
    map.addLayer({
      id: "wayproof-endpoints",
      type: "circle",
      source: "wayproof-endpoints",
      paint: {
        "circle-radius": 7,
        "circle-color": ["match", ["get", "role"], "start", "#ffffff", "#b6462f"],
        "circle-stroke-color": ["match", ["get", "role"], "start", "#17806d", "#ffffff"],
        "circle-stroke-width": 3,
      },
    });

    const bounds = points.reduce(
      (current, point) => current.extend(point),
      new maplibregl.LngLatBounds(points[0], points[0]),
    );
    map.fitBounds(bounds, { padding: 44, maxZoom: 15, duration: 0 });
    container.classList.add("map-enhanced");
    setStatus(container, "Interactive map ready. Topo layer selected.");
  });

  map.on("error", () => {
    if (!container.classList.contains("map-enhanced")) {
      setStatus(container, UNAVAILABLE_MESSAGE);
    }
  });

  for (const button of container.querySelectorAll("[data-basemap]")) {
    button.addEventListener("click", () => {
      const selected = button.dataset.basemap;
      for (const id of Object.keys(BASEMAPS)) {
        map.setLayoutProperty(
          `basemap-${id}`,
          "visibility",
          id === selected ? "visible" : "none",
        );
      }
      for (const candidate of container.querySelectorAll("[data-basemap]")) {
        candidate.setAttribute("aria-pressed", String(candidate === button));
      }
      setStatus(container, `Interactive map ready. ${BASEMAPS[selected].label} layer selected.`);
    });
  }
}

const maps = document.querySelectorAll("[data-interactive-route-map]");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      observer.unobserve(entry.target);
      enhanceRouteMap(entry.target);
    }
  }, { rootMargin: "240px" });
  for (const container of maps) observer.observe(container);
} else {
  for (const container of maps) enhanceRouteMap(container);
}
