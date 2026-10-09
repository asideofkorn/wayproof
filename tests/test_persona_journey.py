"""First-time discovery starts with names and follows generated links, not IDs."""
import json
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from wayproof.canonical_site import entity_payload, journey_summary
from wayproof.read_service import CanonicalReadService
from wayproof.schema import Claim, Entity, Relationship, SpatialScope

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href'), '']

    def handle_data(self, text):
        if self.current is not None:
            self.current[1] += text

    def handle_endtag(self, tag):
        if tag == 'a' and self.current:
            self.links.append(tuple(self.current))
            self.current = None

    def href(self, name):
        return next(href for href, label in self.links if label == name)


def page_at(site, href):
    path = href.split('#')[0].lstrip('/')
    return (site / path / 'index.html').read_text()


def search_matches(rows, query):
    node = shutil.which('node')
    assert node, 'Node is required to exercise the shipped search matcher'
    script = '''const fs = require('fs');
const search = require('./web_assets/planning-search.js');
const {rows, query} = JSON.parse(fs.readFileSync(0, 'utf8'));
console.log(JSON.stringify(rows.filter(r => search.matches(r.search_text, query))));'''
    result = subprocess.run([node, '-e', script], cwd=ROOT,
                            input=json.dumps({'rows': rows, 'query': query}),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def decisions(html):
    return html.split('id="trip-decisions"', 1)[1].split('</section>', 1)[0]


def test_first_time_dog_and_vehicle_journey(generated_site):
    site, _ = generated_site
    home = (site / 'index.html').read_text()
    search = page_at(site, Links(home).href('Search Wayproof'))
    rows = json.loads((site / 'search/index.json').read_text())['entities']
    matches = search_matches(rows, 'Taboose Pass dog')
    names = {r['name'] for r in matches}
    assert {'Taboose Pass', 'Taboose Pass Trail',
            'Taboose Pass western continuation in Kings Canyon'} <= names
    assert 'does not establish permission or current conditions' in search
    # Select by the visible name, then follow actual published links.
    lookup = json.loads((site / 'search/lookup.json').read_text())
    pass_page = page_at(site, next(r['url'] for r in lookup if r['name'] == 'Taboose Pass'))
    route_page = page_at(site, Links(pass_page).href('Taboose Pass Trail'))
    for page in (pass_page, route_page):
        overview = decisions(page)
        assert 'Jurisdiction transition' in overview
        assert 'John Muir Wilderness' in overview
        assert 'Sequoia and Kings Canyon National Parks' in overview
        assert 'Pets prohibited in this area' in overview
        assert 'Do not continue into this area with a dog' in overview
        assert 'rough, bumpy dirt road' in overview
        assert 'Current passability' in overview and 'unknown' in overview
        assert 'low-clearance fallback' in overview and 'added walking distance' in overview
        assert 'dog-compliant alternative or an exact turnaround point' in overview
        assert 'Retrieved: 2026-10-06' in overview
        assert 'National Park Service' in overview
        assert page.index('Pets prohibited in this area') < page.index('allowed under leash')
        assert page.index('Pets prohibited in this area') < page.index('id="plan"')
        assert 'National forest' in overview
        if 'id="route-map"' in page:
            assert page.index('Pets prohibited in this area') < page.index('id="route-map"')
    west = page_at(site, Links(route_page).href('Taboose Pass western continuation in Kings Canyon'))
    assert 'Pets prohibited in this area' in decisions(west)
    trailhead = page_at(site, Links(route_page).href('Taboose Pass Trailhead'))
    road = page_at(site, Links(trailhead).href('US 395 to Taboose Pass Trailhead'))
    assert 'Plan with 0 source-backed facts' not in road
    assert 'Vehicle clearance requirement' in decisions(road)
    assert 'current rules and conditions' in decisions(road)
    # Every first-step evidence link resolves to an actual built page.
    for href, _ in Links(decisions(pass_page)).links:
        if href.startswith(('/evidence/', '/knowledge/')):
            assert page_at(site, href)


def test_map_discovery_and_scoped_warning(generated_site):
    site, _ = generated_site
    map_page = page_at(site, Links((site / 'index.html').read_text()).href('Map'))
    assert 'Find a mapped place or planning need' in map_page
    assert 'Peaks and passes' in map_page
    assert '<ul data-map-results hidden></ul>' in map_page
    index = json.loads((site / 'map/search.json').read_text())
    matches = search_matches([{'name': name, 'search_text': f'{name} {topics}'}
                              for _, name, topics in index], 'Taboose dog')
    assert {row['name'] for row in matches} == {'Taboose Pass', 'Taboose Pass Trail'}
    assert 'Search all places and open questions' in map_page
    features = json.loads((site / 'map/features.geojson').read_text())['features']
    by_name = {f['properties']['name']: f for f in features}
    for name in ('Taboose Pass', 'Taboose Pass Trail'):
        props = by_name[name]['properties']
        assert 'western continuation in Kings Canyon: pets prohibited' in props['decision_summary']
        assert 'vehicle suitability' in props['decision_summary']
        assert 'Pets prohibited' in decisions(page_at(site, props['url']))
    # No inferred western branch, road polyline, or fallback appears on the map.
    assert 'US 395 to Taboose Pass Trailhead' not in by_name
    assert 'Taboose Pass western continuation in Kings Canyon' not in by_name


def test_search_token_order_synonyms_and_no_result_recovery(generated_site):
    site, _ = generated_site
    rows = json.loads((site / 'search/index.json').read_text())['entities']
    assert search_matches(rows, 'dogs Taboose Pass') == search_matches(rows, 'Taboose Pass pet')
    assert search_matches(rows, 'Taboose vehicle clearance')
    assert search_matches(rows, 'Taboose low-clearance vehicle')
    assert not search_matches(rows, 'Taboose nonexistentword')
    assert search_matches(rows, 'Taboose')
    assert search_matches(rows, 'Taboose Pass dog')[0]['kind'] in {'pass', 'route', 'trailhead'}
    assert not search_matches([{'search_text': 'petroleum stove fuel'}], 'dog')


def test_consumer_projection_keeps_direct_and_connected_rules_distinct():
    reads = CanonicalReadService(ROOT)
    route = next(e for e in reads.search_entities('Taboose Pass Trail') if e.kind == 'route')
    payload = entity_payload(reads, route.entity_id)
    assert not any(b['claim']['value'] == {'pets_allowed': False} for b in payload['claims'])
    west = next(c for c in payload['journey'] if 'Adjacent jurisdiction' in c['role'])
    assert len(west['relationships']) == 2
    assert [r['predicate'] for r in west['relationships']] == ['ends_at', 'adjacent_to']
    assert next(b for b in west['claims'] if b['claim']['predicate'] == 'pet_policy')['claim']['value'] == {'pets_allowed': False}
    claims = [b['claim']['claim_id'] for c in payload['journey'] for b in c['claims']]
    assert len(claims) == len(set(claims))
    assert 'pets prohibited' in journey_summary(payload['journey'])


def test_generic_context_uses_only_explicit_edges_and_scopes():
    reads = object.__new__(CanonicalReadService)
    reads._reference_keys = set()
    entities = [Entity('objective', 'pass', 'Example Divide'), Entity('route', 'route', 'Example Trail'),
                Entity('entry', 'trailhead', 'Example Entry'), Entity('west', 'zone', 'Other Jurisdiction'),
                Entity('nearby', 'zone', 'Nearby Unconnected'), Entity('road', 'road', 'Example Road')]
    reads._indexes = {'entity': {e.entity_id: e for e in entities}}
    relations = [Relationship('approach', 'objective', 'approached_via', 'route', ('proof',)),
                 Relationship('end', 'route', 'ends_at', 'objective', ('proof',)),
                 Relationship('start', 'route', 'starts_at', 'entry', ('proof',)),
                 Relationship('boundary', 'objective', 'adjacent_to', 'west', ('proof',)),
                 Relationship('neighbor', 'objective', 'adjacent_to', 'nearby', ('proof',))]
    road_claim = Claim('road-fact', 'road', 'road_access_description', {'current_passability': 'unknown'},
                       ('proof',), spatial_scope_ids=('entry-scope',))
    west_claim = Claim('west-fact', 'west', 'pet_policy', {'pets_allowed': False}, ('proof',))
    reads._records = SimpleNamespace(
        relationships=relations,
        spatial_scopes=[SpatialScope('entry-scope', 'place', 'entry')],
        claims=[road_claim, west_claim, Claim('transition', 'west', 'jurisdiction_transition', {}, ('proof',))])
    context = {c.entity_id: c for c in reads.journey_context('objective')}
    assert set(context) == {'objective', 'route', 'entry', 'west'}
    assert context['west'].relationship_ids == ('boundary',)
    assert reads.scoped_claims_for('entry') == (road_claim,)
    assert reads.scoped_claims_for('route') == ()
    assert reads.scoped_claims_for('objective') == ()
    assert reads.scoped_claims_for('west')[1] == west_claim


@pytest.mark.parametrize('fail_map,fail_search', [(False, False), (True, False), (False, True)])
def test_map_controls_wait_for_readiness(generated_site, fail_map, fail_search):
    site, _ = generated_site

    class Controls(HTMLParser):
        def __init__(self, html):
            super().__init__()
            self.elements = []
            self.feed(html)

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if (attrs.get('id') == 'map-search'
                    or any(key.startswith(('data-map-', 'data-basemap')) for key in attrs)):
                self.elements.append((tag, attrs))

    node = shutil.which('node')
    assert node, 'Node is required to exercise delayed map readiness'
    subprocess.run([node, '--experimental-vm-modules', 'tests/map_loading_harness.cjs'],
                   cwd=ROOT, text=True, capture_output=True, check=True, timeout=30,
                   input=json.dumps({
                       'controls': Controls((site / 'map/index.html').read_text()).elements,
                       'script': (site / 'assets/explore-map.js').read_text(),
                       'index': json.loads((site / 'map/search.json').read_text()),
                       'geometry': json.loads((site / 'map/features.geojson').read_text()),
                       'failMap': fail_map, 'failSearch': fail_search,
                   }))


def test_map_discovery_payload_budget(generated_site):
    import gzip

    site, _ = generated_site
    page = (site / 'map/index.html').read_bytes()
    index = (site / 'map/search.json').read_bytes()
    # Initial HTML must remain independent of inventory size. The geometry-free
    # index is lazy, and the browser caps rendered rows at 20.
    assert len(page) < 12_000
    assert len(gzip.compress(page)) < 4_000
    assert len(index) < 350_000
    assert len(gzip.compress(index)) < 50_000
