#!/usr/bin/env python3
"""Optional offline snapshot rebuild; requires pyshp and pyproj (not runtime dependencies)."""
import shapefile,pyproj,json,hashlib
from pathlib import Path
import argparse
p=argparse.ArgumentParser(description='Rebuild reviewed public-domain NPS western Taboose display geometry.')
p.add_argument('--shapefile',type=Path,required=True)
p.add_argument('--archive',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
src=a.shapefile
assert hashlib.sha256(a.archive.read_bytes()).hexdigest() == 'eb8fe80714e056fa947d2d7274e8af451a28ba7bf63ce4116844894656112925', 'Unreviewed NPS archive; review new edition before rebuilding'
from zipfile import ZipFile
with ZipFile(a.archive) as archive:
 for extension in ('.shp','.dbf','.prj'):
  member=next(n for n in archive.namelist() if Path(n).name=='seki_maintained_trails'+extension)
  assert src.with_suffix(extension).read_bytes()==archive.read(member), 'Shapefile does not match reviewed archive'
r=shapefile.Reader(str(src)); transform=pyproj.Transformer.from_crs(26911,4326,always_xy=True)
chains={'pass-jmt':[(188,True)],'jmt-bench-junction':[(186,False)],'bench-lake':[(187,False),(509,False),(508,False)],'pinchot-pass':[(185,True)],'mather-pass':[(189,True),(722,True),(190,False)]}
features=[]
for key,parts in chains.items():
 coords=[];lineage=[]
 for index,reverse in parts:
  s=r.shapeRecord(index);raw=list(s.shape.points);pts=raw[::-1] if reverse else raw
  if coords: assert coords[-1]==pts[0],(key,index)
  coords.extend(pts if not coords else pts[1:])
  attrs={k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in s.record.as_dict().items()}
  lineage.append({'shapefile_record_index_zero_based':index,'attributes':attrs,'source_vertex_range_inclusive':[0,len(raw)-1],'reversed':reverse,'source_geometry_sha256':hashlib.sha256(json.dumps(raw).encode()).hexdigest()})
 features.append({'type':'Feature','properties':{'feature_id':'nps-taboose-'+key,'source_features':lineage},'geometry':{'type':'LineString','coordinates':[list(transform.transform(*p)) for p in coords]}})
result={'type':'FeatureCollection','wayproof':{'source':'https://irma.nps.gov/DataStore/DownloadFile/601800?Reference=2253434','publisher':'National Park Service','classification':'public_domain','retrieved_at':'2026-10-07T01:21:00+00:00','source_coordinate_reference_system':'EPSG:26911','normalized_coordinate_reference_system':'EPSG:4326','source_artifact_sha256':hashlib.sha256(a.archive.read_bytes()).hexdigest(),'navigation_grade':False,'processing':'Complete shapefile features reoriented and joined only at exactly identical source endpoints. Reprojected using pyproj from NAD83 UTM 11N to WGS84; no snapping, rounding, simplification or calculated trail mileage. Record indices are local to the hashed artifact, not durable NPS identifiers.','review_basis':'NPS 2026 Kings Canyon Stock Use and Grazing Regulations map and stock guide, page 14; historical atlas panels 7 and 11. Maps and From_Junc/To_Junc attributes establish connections, geometry is display evidence.','limitations':'Published 2018 dataset with older edits, source accuracy varies 5-14m/unknown. Pinchot Pass South record 186 has inconsistent name/endpoints; exact junction connectors and 2026 map establish its role; original attributes retained. USFS and NPS Taboose Pass endpoints remain unmodified and are not forcibly snapped.'},'features':features}
out=a.output;out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print([(f['properties']['feature_id'],len(f['geometry']['coordinates'])) for f in features])
