"""Remaining western Yosemite and Tioga Road foundations stay source-bounded."""
import json
from pathlib import Path
from wayproof.canonical_storage import load_canonical,load_changeset
from wayproof.schema import ChangeAction,ChangeSetStatus
ROOT=Path(__file__).resolve().parents[1]
ROUTES={"route-tuolumne-grove-nature-trail","route-merced-grove","route-may-lake-day-hike","route-lukens-lake-tioga","route-lukens-lake-white-wolf","route-harden-lake","route-north-dome-porcupine-creek","route-ten-lakes-day-hike","route-ten-lakes-to-tenaya-lake","route-grand-canyon-tuolumne-white-wolf"}
def idx(r,c,a):return {getattr(x,a):x for x in getattr(r,c)}
def test_routes_have_profiles_starts_objectives_and_topology_gap():
 r=load_canonical(ROOT);claims=idx(r,"claims","claim_id");rels=idx(r,"relationships","relationship_id");gaps=idx(r,"gaps","gap_id")
 for route in ROUTES:
  assert claims[f"claim-{route.removeprefix('route-')}-published-profile"].evidence_ids
  assert any(x.subject_id==route and x.predicate=="starts_at" for x in rels.values())
  assert any(x.subject_id==route and x.predicate=="reaches" for x in rels.values())
 assert ROUTES <= set(gaps["gap-yosemite-west-tioga-route-topology"].related_ids)
def test_access_and_tenaya_facilities_are_explicit():
 claims=idx(load_canonical(ROOT),"claims","claim_id")
 assert claims["claim-crane-flat-white-wolf-access-profile"].value["grove_parking"]=="very limited"
 tioga=claims["claim-tioga-road-corridor-access-profile"].value;assert tioga["scenic_drive_miles"]==46 and tioga["operational_status_requires_current_check"] is True
 lake=claims["claim-tenaya-lake-facility-profile"].value;assert lake["parking_areas"]=="several" and lake["vault_toilets"]=="at some parking areas"
def test_points_and_pages_publish(generated_site):
 site,_=generated_site;data=json.loads((site/"map"/"features.geojson").read_text());ids={x["properties"]["entity_id"] for x in data["features"]}
 assert {"trailhead-tuolumne-grove","trailhead-merced-grove","trailhead-may-lake","trailhead-porcupine-creek","access-tenaya-east-beach-parking","facility-ten-lakes-vault-toilet"}<=ids
 for eid in ROUTES|{"place-crane-flat-white-wolf","place-tioga-road-corridor"}:
  p=site/"knowledge"/eid/"index.html";assert p.exists();assert "National Park Service" in p.read_text()
def test_batch_is_one_validated_add_only_changeset():
 c=load_changeset(ROOT/"changesets/v0/wp-20260925-yosemite-remaining-corridors.json");assert c.status is ChangeSetStatus.VALIDATED;assert {x.action for x in c.operations}=={ChangeAction.ADD};assert len(c.operations)==len({x.path for x in c.operations})
