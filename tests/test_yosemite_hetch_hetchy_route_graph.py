from datetime import date
import json
from pathlib import Path
import pytest
from wayproof.canonical_storage import load_canonical,load_changeset
from wayproof.read_service import CanonicalReadService
from wayproof.schema import ChangeAction,ChangeSetStatus
from wayproof.traversal import TraversalState,resolve_traversal
ROOT=Path(__file__).resolve().parents[1]
ROUTES=(("route-wapama-falls","trailhead-wapama-rancheria","waterfall-wapama",11),("route-poopenaut-valley","trailhead-poopenaut-valley","valley-poopenaut",1))
@pytest.mark.parametrize("route,start,end,count",ROUTES)
def test_routes_resolve_both_directions(route,start,end,count):
 r=CanonicalReadService(ROOT);f=resolve_traversal(r,r.entity(route),r.entity(start),r.entity(end),date(2026,9,30));b=resolve_traversal(r,r.entity(route),r.entity(end),r.entity(start),date(2026,9,30));assert f.state is b.state is TraversalState.COMPLETE;assert len(f.legs)==len(b.legs)==count;assert [x.segment_id for x in b.legs]==[x.segment_id for x in reversed(f.legs)]
def test_snapshot_and_pages_publish(generated_site):
 p=json.loads((ROOT/"geometry/v0/snapshots/nps-yose-hetch-hetchy-route-features-20260926.geojson").read_text());assert len(p["features"])==12;site,_=generated_site
 for route,*_ in ROUTES:assert "Interactive map" in (site/"knowledge"/route/"index.html").read_text()
def test_remaining_gap_is_explicit():
 r=load_canonical(ROOT);g=next(x for x in r.gaps if x.gap_id=="gap-yosemite-hetch-hetchy-route-topology");assert "unnamed or nearby lines are not joined" in g.reason;assert "route-rancheria-falls" in g.related_ids
def test_one_changeset():
 c=load_changeset(ROOT/"changesets/v0/wp-20260926-yosemite-hetch-hetchy-route-graph.json");assert c.status is ChangeSetStatus.VALIDATED;assert {x.action for x in c.operations}=={ChangeAction.ADD,ChangeAction.REPLACE}
