"""Campground-first decisions and context without inferred containment."""
import json
from pathlib import Path
from types import SimpleNamespace

from wayproof.camping_projection import camping_hierarchy
from wayproof.schema import Entity, Relationship
from wayproof.read_service import CanonicalReadService

ROOT = Path(__file__).resolve().parents[1]


def test_hierarchy_preserves_multiple_parents_and_rejects_unsourced_or_nearby():
    entities = {e.entity_id: e for e in (
        Entity('site', 'campsite', '12'), Entity('one','campground','One'),
        Entity('two','campground','Two'), Entity('near','campground','Nearby'),
        Entity('unknown','campground','Unsourced'))}
    relations = [Relationship('r1','site','part_of','one',evidence_ids=('e1',)),
                 Relationship('r2','two','contains','site',evidence_ids=('e2',)),
                 Relationship('r3','site','near','near',evidence_ids=('e3',)),
                 Relationship('r4','site','part_of','unknown',evidence_ids=())]
    reads = SimpleNamespace(entity=entities.__getitem__, relationships_for=lambda _: relations)
    assert {p.entity_id for p in camping_hierarchy(reads,'site').parents} == {'one','two'}
    assert not camping_hierarchy(SimpleNamespace(entity=entities.__getitem__, relationships_for=lambda _: []),'site').parents


def test_campground_projection_does_not_promote_child_facts():
    reads = CanonicalReadService(ROOT)
    eid = 'campground-east-fork-inyo'
    assert len(reads.camping_hierarchy(eid).children) == 133
    assert any(c.subject_id == 'campsite-east-fork-125' for c in reads.scoped_claims_for(eid))
    assert not any(c.subject_id.startswith('campsite-') for c in reads.camping_claims(eid))
    assert any(c.predicate == 'fire_restrictions' for c in reads.camping_claims(eid))


def test_campground_first_static_journey(generated_site):
    root, _ = generated_site
    directory = (root/'camping/index.html').read_text()
    assert '/knowledge/campground-east-fork-inyo/' in directory
    assert '/knowledge/campsite-east-fork-126/' not in directory
    parent = root/'knowledge/campground-east-fork-inyo'
    page = (parent/'index.html').read_text()
    assert len(page.encode()) < 100_000
    assert 'Browse 133 campsites' in page
    assert page.index('Check opening') < page.index('Browse 133 campsites')
    assert '/knowledge/route-upper-rock-creek-canyon/' in page
    assert '2026-09-23' in page and 'weather dependent' in page
    assert 'campsite-east-fork-125' not in page
    assert '/facts/' in page
    pages = [parent/'campsites/index.html', *sorted((parent/'campsites').glob('page-*/index.html'))]
    assert len(pages) == 7
    html = ''.join(p.read_text() for p in pages)
    for n in range(1,134):
        assert f'/knowledge/campsite-east-fork-{n}/' in html
    assert all(p.read_text().count('class="camp-row"') <= 20 for p in pages)
    assert 'Campsite 126' in html
    assert 'Vehicle limits differ' in html
    site = (root/'knowledge/campsite-east-fork-126/index.html').read_text()
    assert site.index('Vehicle limits differ') < site.index('Check availability')
    assert site.index('Checkout times differ') < site.index('Check availability')
    assert '/evidence/claim/claim-east-fork-site-126-vehicle-fields/' in site
    assert '/knowledge/campground-east-fork-inyo/' in site
    assert '11:00' in site and '13:00' in site
    assert 'All details, sources and history' in site
    assert (root/'knowledge/campsite-east-fork-126/facts/index.html').exists()


def test_search_index_keeps_parent_context_and_preferred_destinations(generated_site):
    root, _ = generated_site
    rows = {r['id']:r for r in json.loads((root/'search/lookup.json').read_text())}
    assert rows['campsite-east-fork-126']['parents'][0]['name'] == 'East Fork Campground'
    assert 'East Fork Campground' in rows['campsite-east-fork-126']['text']
    assert rows['park-del-valle-regional-park']['url'] == '/destinations/del-valle/'
    assert rows['trail-ohlone-wilderness']['url'] == '/trails/ohlone-wilderness/'
    assert (root/'search/index.html').read_text().count('class="result-card"') <= 20


def test_camping_search_groups_parents_but_keeps_numbered_site_queries(generated_site):
    import shutil
    import subprocess
    root, _ = generated_site
    rows = json.loads((root/'search/lookup.json').read_text())
    script = '''const search = require('./web_assets/planning-search.js');
const rows=JSON.parse(require('fs').readFileSync(0,'utf8'));
const find=(q,k='')=>rows.filter(r=>search.discover(r,q,k)).map(r=>r.id);
console.log(JSON.stringify([find('East Fork'),find('East Fork 126'),find('East Fork','campsite'),find('Taboose Pass dog')]));'''
    result = subprocess.run([shutil.which('node'),'-e',script],cwd=ROOT,input=json.dumps(rows),text=True,capture_output=True,check=True)
    broad,numbered,explicit,dog=json.loads(result.stdout)
    assert 'campground-east-fork-inyo' in broad
    assert 'campsite-east-fork-126' not in broad
    assert 'campsite-east-fork-126' in numbered
    assert len([e for e in explicit if e.startswith('campsite-east-fork-')]) == 133
    assert 'place-taboose-pass' in dog


def test_return_context_rejects_external_and_script_urls():
    import shutil
    import subprocess
    script = r'''
const vm = require('vm'), fs = require('fs'), assert = require('assert');
const code = fs.readFileSync('web_assets/planning-context.js','utf8');
function run(from) {
  const back={hidden:true};
  const location={origin:'https://wayproof.dev',pathname:'/knowledge/example/',
    search:'?'+new URLSearchParams({from}),hash:'',href:'https://wayproof.dev/knowledge/example/'};
  vm.runInNewContext(code,{URL,URLSearchParams,location,
    document:{querySelector:s=>s==='[data-context-back]'?back:null,addEventListener(){}},history:{}});
  return back;
}
for(const value of ['https://evil.example/', '//evil.example/search/', '/\\evil.example/search/', 'javascript:alert(1)', '/assets/'])
  assert.equal(run(value).hidden,true,value);
const back=run('/search/?q=East+Fork&kind=campground');
assert.equal(back.hidden,false);
assert.equal(back.href,'/search/?q=East+Fork&kind=campground');
assert.equal(back.textContent,'← Back to search results');
'''
    subprocess.run([shutil.which('node'),'-e',script],cwd=ROOT,check=True,capture_output=True,text=True)
