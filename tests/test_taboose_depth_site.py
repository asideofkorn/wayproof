"""One shared production-site build validates the new Taboose consumer pages."""
import json
from scripts.ingest_taboose_depth import ROUTES,CAMP,BENCH,MATHER,PINCHOT,site_id,CHANGE_ID

def test_taboose_depth_generated_discovery_and_evidence(generated_site):
 output,_=generated_site
 camping=json.loads((output/'camping/index.json').read_text())
 ids={x['entity_id'] for x in camping['entities']}
 assert {site_id(f'{i:03d}') for i in range(1,37)}<=ids
 peaks=json.loads((output/'peaks/index.json').read_text())
 assert {MATHER,PINCHOT}<={x['entity_id'] for x in peaks['entities']}
 trails=json.loads((output/'trails/index.json').read_text())
 assert {r[0] for r in ROUTES.values()}<={x['entity_id'] for x in trails['entities']}
 for rid,_,_,legs in ROUTES.values():
  html=(output/f'knowledge/{rid}/index.html').read_text()
  assert 'id="route-map"' in html
  geo=json.loads((output/f'geometry/routes/{rid}.geojson').read_text())
  assert len(geo['features'])==1+len(legs)
  assert geo['wayproof']['distance_complete'] is False
 for eid in (CAMP,BENCH,site_id('006'),site_id('016'),'camp-bench-lake-stock'):
  assert (output/f'knowledge/{eid}/index.html').exists()
  assert (output/f'knowledge/{eid}.json').exists()
 fit=(output/f'knowledge/{site_id("006")}.json').read_text()
 assert 'not stated' in fit and 'fit_confirmed' in fit
 assert 'gap-taboose-camp-depth' in fit and 'cancellation' in fit
 gap=(output/'evidence/gap/gap-taboose-camp-depth/index.json').read_text()
 assert 'cancellation' in gap and 'units' in gap
 assert CHANGE_ID in (output/'changes/index.html').read_text()
