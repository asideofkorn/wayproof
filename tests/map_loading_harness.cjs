// Exercise the shipped module with deterministic network/map delays. No browser
// dependency is needed in CI; disabled click behavior and event bubbling follow DOM semantics.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {controls, script, index, geometry, failMap, failSearch} = JSON.parse(fs.readFileSync(0, 'utf8'));
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => {resolve = a; reject = b;}); return {promise, resolve, reject}; };
const settle = () => new Promise(resolve => setImmediate(resolve));
class Element {
  constructor(tag, attrs = {}) {
    this.tag = tag; this.attrs = attrs; this.dataset = {}; this.children = []; this.listeners = {};
    this.disabled = 'disabled' in attrs; this.checked = 'checked' in attrs; this.value = '';
    this.classList = {add() {}, toggle() { return true; }};
    for (const [key, value] of Object.entries(attrs)) if (key.startsWith('data-')) {
      this.dataset[key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = value;
    }
  }
  matches(selector) {
    if (selector.startsWith('#')) return this.attrs.id === selector.slice(1);
    const [, attr, value] = selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/) || [];
    const actual = attr?.startsWith('data-') ? this.dataset[attr.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] : this.attrs[attr];
    return actual !== undefined && (value === undefined || value === actual);
  }
  querySelectorAll(selector) {
    return this.children.filter(child => child instanceof Element).flatMap(child => [
      ...(selector.split(', ').some(s => child.matches(s)) ? [child] : []), ...child.querySelectorAll(selector)]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0]; }
  closest(selector) { return this.matches(selector) ? this : this.parent?.closest(selector); }
  append(...children) { for (const child of children) { if (child instanceof Element) child.parent = this; this.children.push(child); } }
  replaceChildren(...children) { this.children = []; this.append(...children); }
  setAttribute(key, value) { this.attrs[key] = value; }
  addEventListener(type, callback) { (this.listeners[type] ||= []).push(callback); }
  dispatchEvent(event) {
    if (!event.target) event.target = this;
    for (const callback of this.listeners[event.type] || []) callback(event);
    if (event.bubbles) this.parent?.dispatchEvent(event);
  }
  click() {
    if (this.disabled) return;
    this.dispatchEvent({type: 'click', target: this, bubbles: true});
  }
  toggleChecked() { if (!this.disabled) { this.checked = !this.checked; this.dispatchEvent({type: 'change'}); } }
}
const container = new Element('main', {'data-explore-map': '', 'data-geometry-url': '/geometry', 'data-search-url': '/search'});
for (const [tag, attrs] of controls) container.append(new Element(tag, attrs));
const document = {querySelector: () => container, createElement: tag => new Element(tag), body: new Element('body')};
const moduleGate = deferred(), geometryGate = deferred(), indexGate = deferred();
let map, searchRequests = 0;
class MapStub {
  constructor(options) {
    map = this; this.handlers = {}; this.layers = new Map(options.style.layers.map(layer => [layer.id, layer])); this.fits = [];
    this.touchZoomRotate = {disableRotation() {}};
  }
  addControl() {}
  on(type, callback) { this.handlers[type] = callback; }
  addSource() {}
  addLayer(layer) { this.layers.set(layer.id, layer); }
  getLayer(id) { return this.layers.get(id); }
  setLayoutProperty(id, property, value) {
    assert(this.layers.has(id), `Layer ${id} used before it exists`);
    this.layers.get(id).layout[property] = value;
  }
  getLayoutProperty(id, property) { return this.layers.get(id).layout[property]; }
  fitBounds(bounds) { this.fits.push(bounds); }
  resize() {}
}
class Bounds { constructor(point) { this.points = [point]; } extend(point) { this.points.push(point); return this; } }
const location = {href: 'https://example.test/map/', search: ''};
const context = vm.createContext({document, location, URL, URLSearchParams,
  history: {replaceState(_, __, url) { location.href = String(url); location.search = url.search; }},
  window: {setTimeout}, Event: class {constructor(type) {this.type = type;}},
  WayproofSearch: require('../web_assets/planning-search.js'),
  fetch(url) {
    if (url === '/search') {searchRequests++; return indexGate.promise;}
    assert.equal(url, '/geometry'); return geometryGate.promise;
  },
});
const vendor = new vm.SyntheticModule(['Map', 'LngLatBounds', 'NavigationControl', 'AttributionControl'], function () {
  this.setExport('Map', MapStub); this.setExport('LngLatBounds', Bounds);
  this.setExport('NavigationControl', class {}); this.setExport('AttributionControl', class {});
}, {context});
const source = new vm.SourceTextModule(script, {context, importModuleDynamically: async () => {
  await moduleGate.promise;
  await vendor.link(() => {}); await vendor.evaluate(); return vendor;
}});
(async () => {
  await source.link(() => {}); await source.evaluate();
  const search = container.querySelector('#map-search');
  const results = container.querySelector('[data-map-results]');
  const status = container.querySelector('[data-map-status]');
  const layers = container.querySelectorAll('[data-map-layer]');
  const basemaps = container.querySelectorAll('[data-basemap]');
  const searchStatus = container.querySelector('[data-map-search-status]');
  assert.equal(searchRequests, 0, 'Blank search must not fetch the inventory');
  for (const control of [...layers, ...basemaps, container.querySelector('[data-map-expand]')]) assert(control.disabled);
  const checked = layers[0].checked;
  layers[0].toggleChecked(); basemaps[1].click();
  assert.equal(layers[0].checked, checked);
  search.value = 'Taboose dog'; search.dispatchEvent({type: 'input'});
  assert.equal(searchRequests, 1);
  indexGate.resolve({ok: !failSearch, json: async () => index}); await settle();
  if (failSearch) {
    assert.match(searchStatus.textContent, /unavailable.*all-place search/);
    assert.equal(results.children.length, 0);
  } else {
    assert.equal(results.children.length, 2);
    const button = results.querySelector('[data-map-focus]');
    assert(button.disabled); button.click(); assert.equal(map, undefined);
    assert(results.children[0].children.some(c => c.tag === 'a' && c.href.startsWith('/knowledge/')));
  }
  moduleGate.resolve(); await settle();
  assert.equal(map, undefined, 'Map must still wait for geometry');
  geometryGate.resolve({ok: !failMap, json: async () => geometry}); await settle();
  if (failMap) {
    assert.match(status.textContent, /unavailable.*disabled/);
    for (const control of [...layers, ...basemaps, ...results.querySelectorAll('[data-map-focus]')]) assert(control.disabled);
    return;
  }
  assert(map); assert.equal(map.fits.length, 0);
  layers[0].toggleChecked(); basemaps[1].click();
  if (!failSearch) { const button = results.querySelector('[data-map-focus]'); assert(button.disabled); button.click(); }
  assert.equal(map.fits.length, 0, 'No control runs while map load is delayed');
  map.handlers.load();
  assert.match(status.textContent, /ready/);
  for (const layer of layers) assert.equal(layer.disabled, layer.dataset.mapCount === '0');
  assert(!basemaps[1].disabled); basemaps[1].click();
  assert.equal(map.getLayoutProperty('basemap-aerial', 'visibility'), 'visible');
  const activeLayer = layers.find(l => !l.disabled); activeLayer.toggleChecked();
  assert.equal(map.getLayoutProperty(`wp-${activeLayer.dataset.mapLayer}-line`, 'visibility'), activeLayer.checked ? 'visible' : 'none');
  if (failSearch) return;
  const button = results.querySelector('[data-map-focus]');
  assert(!button.disabled); button.click();
  assert.equal(new URL(location.href).searchParams.get('entity'), button.dataset.mapFocus);
  assert.equal(map.fits.length, 2);
  const selected = geometry.features.filter(f => f.properties.entity_id === button.dataset.mapFocus);
  assert.deepEqual(map.fits.at(-1).points[0], selected[0].geometry.coordinates);
  assert(container.querySelector('[data-map-selection]').children.length);
  // Results created after load must work, too, without rebinding handlers.
  search.value = 'Taboose'; search.dispatchEvent({type: 'input'}); await settle();
  assert(!results.querySelector('[data-map-focus]').disabled);
  results.querySelector('[data-map-focus]').click(); assert.equal(map.fits.length, 3);
  search.value = 'a'; search.dispatchEvent({type: 'input'}); await settle();
  assert.equal(results.children.length, 20); assert.match(searchStatus.textContent, /first 20/);
  search.value = ''; search.dispatchEvent({type: 'input'}); await settle();
  assert.equal(results.children.length, 0); assert.equal(searchRequests, 1);
})().catch(error => { console.error(error); process.exitCode = 1; });
