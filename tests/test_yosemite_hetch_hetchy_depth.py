"""Hetch Hetchy depth preserves gate, reservoir, and topology limits."""
import json
from pathlib import Path
from wayproof.canonical_storage import load_canonical, load_changeset
from wayproof.schema import ChangeAction, ChangeSetStatus

ROOT=Path(__file__).resolve().parents[1]
ROUTES={"route-hetch-hetchy-lookout-point","route-wapama-falls","route-rancheria-falls","route-smith-peak-main","route-smith-peak-entrance","route-poopenaut-valley","route-laurel-lake","route-lake-vernon-rancheria-loop"}
def index(records,collection,attr):return {getattr(x,attr):x for x in getattr(records,collection)}

def test_routes_have_profiles_starts_objectives_and_topology_gap():
 r=load_canonical(ROOT);entities=index(r,"entities","entity_id");claims=index(r,"claims","claim_id");rels=index(r,"relationships","relationship_id");gaps=index(r,"gaps","gap_id")
 assert ROUTES<=entities.keys()
 for route in ROUTES:
  assert claims[f"claim-{route.removeprefix('route-')}-published-profile"].evidence_ids
  assert any(x.subject_id==route and x.predicate=="starts_at" for x in rels.values())
  assert any(x.subject_id==route and x.predicate=="reaches" for x in rels.values())
 assert set(gaps["gap-yosemite-hetch-hetchy-route-topology"].related_ids)==ROUTES

def test_access_rules_and_dated_status_are_explicit():
 claims=index(load_canonical(ROOT),"claims","claim_id")
 access=claims["claim-hetch-hetchy-access-profile"].value
 assert access["road_hours"]=="sunrise to sunset" and access["road_closed_to_all_vehicles"]=="sunset to sunrise"
 rules=claims["claim-hetch-hetchy-reservoir-use-rules"].value
 assert rules["swimming"] is False and rules["boating"] is False
 status=claims["claim-hetch-hetchy-observed-status-20260925"].value
 assert status["as_of"]=="2026-09-25" and status["recheck_required"] is True
 assert claims["claim-rancheria-falls-published-profile"].value["distance_conflict_preserved"] is True

def test_map_points_and_pages_publish(generated_site):
 site,_=generated_site;payload=json.loads((site/"map"/"features.geojson").read_text());ids={x["properties"]["entity_id"] for x in payload["features"]}
 assert {"entrance-yosemite-hetch-hetchy","access-hetch-hetchy-parking","trailhead-wapama-rancheria","trailhead-poopenaut-valley","facility-hetch-hetchy-restroom"}<=ids
 for eid in ROUTES|{"place-hetch-hetchy"}:
  page=site/"knowledge"/eid/"index.html";assert page.exists();assert "National Park Service" in page.read_text()

def test_batch_is_one_validated_add_only_changeset():
 change=load_changeset(ROOT/"changesets/v0/wp-20260925-yosemite-hetch-hetchy-depth.json")
 assert change.status is ChangeSetStatus.VALIDATED
 assert {x.action for x in change.operations}=={ChangeAction.ADD}
 assert len(change.operations)==len({x.path for x in change.operations})
