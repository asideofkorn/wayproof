"""Geometry, loading, and approach tests.

Was the clustering pipeline's test file. The clustering, TSP, itinerary and
diagnostics tests went with the feature they covered; what remains is the
part `plan.py` and the site actually depend on -- haversine and Naismith
distance, peak and trailhead loading, collection merging, and trailhead
choice.

Originally: tests for the Sierra Peaks clustering toolkit.

Run with:  python -m pytest tests/  (or)  python tests/test_pipeline.py
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.model import Peak, Trailhead
from wayproof.data_loader import load_peaks, load_trailheads
from wayproof.distances import (
    haversine_miles,
    naismith_effective_miles,
    leg_metrics,
    build_distance_matrix,
)
from wayproof.approach import choose_trailhead, approach_metrics

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "sps_sample.csv")
TRAILHEADS = os.path.join(os.path.dirname(__file__), "..", "data", "trailheads.csv")


def test_haversine_known_distance():
    # Whitney to North Palisade is roughly 36 miles great-circle.
    d = haversine_miles(36.5785, -118.2923, 37.0945, -118.5147)
    assert 34 < d < 38, d

def test_haversine_zero():
    assert haversine_miles(37.0, -118.0, 37.0, -118.0) == 0.0

def test_naismith_adds_ascent():
    # 2000 ft ascent == 3 equivalent flat miles.
    assert math.isclose(naismith_effective_miles(0.0, 2000.0), 3.0, rel_tol=1e-6)
    # Descent adds nothing.
    assert naismith_effective_miles(5.0, 0.0) == 5.0

def test_leg_metrics_directional_ascent():
    low = Peak("low", 37.0, -118.0, 10000)
    high = Peak("high", 37.0, -118.0, 12000)
    _, asc_up, _ = leg_metrics(low, high)
    _, asc_down, _ = leg_metrics(high, low)
    assert asc_up == 2000
    assert asc_down == 0

def test_distance_matrix_symmetric():
    peaks = load_peaks(DATA)[:6]
    mat = build_distance_matrix(peaks, metric="effective")
    assert mat.shape == (6, 6)
    assert (mat == mat.T).all()
    assert (mat.diagonal() == 0).all()

def _synthetic_passes():
    from wayproof.passes import Pass
    # A north-south crest near longitude -118.4.
    return [
        Pass("South Pass", 36.7, -118.40, 11000, tier=1, kind="pass"),
        Pass("Mid Pass", 37.0, -118.42, 11500, tier=1, kind="pass"),
        Pass("North Pass", 37.3, -118.45, 11200, tier=1, kind="pass"),
    ]


def test_pass_classify_tiers_and_kinds():
    from wayproof.passes import classify
    assert classify("Forester Pass") == (1, "pass")
    assert classify("Lamarck Col") == (1, "col")
    assert classify("Echo Summit") == (1, "pass")        # road summit
    assert classify("Some Saddle") == (2, "saddle")
    assert classify("Random Notch") == (2, "notch")
    # Curated seed rows are tier 1 regardless of trailing noun.
    assert classify("Weird Saddle", coord_source="seed") == (1, "saddle")

def test_crest_model_assigns_sides():
    from wayproof.passes import CrestModel
    crest = CrestModel(_synthetic_passes(), crest_tier=1)
    assert crest.usable
    # East of the crest (less-negative longitude) vs west of it.
    assert crest.side(37.0, -118.0) == "east"
    assert crest.side(37.0, -118.9) == "west"

def test_router_same_side_is_direct():
    from wayproof.passes import PassRouter
    router = PassRouter(_synthetic_passes(), candidate_tier=1)
    a = Peak("a", 37.0, -118.0, 12000)
    b = Peak("b", 37.1, -118.1, 12000)   # both east of the crest
    leg = router.leg(a, b)
    assert leg.via_pass is None
    assert math.isclose(leg.horizontal_mi,
                        haversine_miles(37.0, -118.0, 37.1, -118.1), rel_tol=1e-9)

def test_router_cross_crest_routes_through_pass():
    from wayproof.passes import PassRouter
    router = PassRouter(_synthetic_passes(), candidate_tier=1)
    east = Peak("east", 37.0, -118.0, 12000)
    west = Peak("west", 37.0, -118.9, 12000)
    leg = router.leg(east, west)
    assert leg.via_pass is not None                    # forced over a pass
    direct = haversine_miles(37.0, -118.0, 37.0, -118.9)
    assert leg.horizontal_mi >= direct - 1e-9          # detour is never shorter

def test_build_router_from_dataset():
    from wayproof.passes import build_router
    passes_csv = os.path.join(os.path.dirname(__file__), "..", "data", "passes.csv")
    router = build_router(passes_csv, candidate_tier=1)
    assert router.crest.usable
    assert len(router.waypoints) >= 10

def test_load_trailheads():
    ths = load_trailheads(TRAILHEADS)
    assert len(ths) > 30
    assert all(th.name and th.side for th in ths)
    assert any(th.name.startswith("Whitney Portal") for th in ths)
    # Blank wilderness_area/land_agency cells (e.g. non-wilderness northern
    # Sierra trailheads) must load as "", not the literal string "nan" --
    # pandas NaN is truthy, so a naive `x or ""` check silently fails this.
    sierra_buttes = next(th for th in ths if th.name == "Sierra Buttes")
    assert sierra_buttes.wilderness_area == ""
    assert sierra_buttes.land_agency == "Tahoe NF"
    assert "nan" not in sierra_buttes.wilderness_area.lower()
    # `park` (the specific park/preserve unit, distinct from wilderness_area)
    # is blank for Sierra trailheads and only populated for the two EBRPD
    # ones added alongside Rose Peak/Mission Peak.
    assert sierra_buttes.park == ""
    lichen_bark = next(th for th in ths if th.name == "Del Valle (Lichen Bark)")
    assert lichen_bark.park == "Del Valle Regional Park"
    assert lichen_bark.wilderness_area == "Ohlone Wilderness"

def test_choose_trailhead_modal():
    ths = [
        Trailhead("A", 37.0, -118.0, 8000),
        Trailhead("B", 37.5, -118.5, 9000),
    ]
    peaks = [
        Peak("p1", 37.0, -118.0, 13000, meta={"nearest_trailhead": "A"}),
        Peak("p2", 37.0, -118.0, 13000, meta={"nearest_trailhead": "A"}),
        Peak("p3", 37.5, -118.5, 13000, meta={"nearest_trailhead": "B"}),
    ]
    assert choose_trailhead(peaks, ths).name == "A"

def test_choose_trailhead_centroid_fallback():
    # No usable nearest_trailhead names -> nearest trailhead to the centroid.
    ths = [Trailhead("Far", 40.0, -120.0, 7000), Trailhead("Near", 37.0, -118.0, 8000)]
    peaks = [Peak("p", 37.01, -118.01, 13000)]
    assert choose_trailhead(peaks, ths).name == "Near"

def test_approach_single_peak_equals_round_trip():
    # In + out for one peak reduces to the official round trip plus one-way gain.
    th = Trailhead("TH", 37.0, -118.0, 8000)
    p = Peak("P", 37.05, -118.05, 13000,
             meta={"mileage_rt": 10.0, "gain_ft": 5000, "nearest_trailhead": "TH"})
    m = approach_metrics(th, p, p)
    assert math.isclose(m["horizontal_mi"], 10.0)
    assert math.isclose(m["effective_mi"], 10.0 + naismith_effective_miles(0, 5000))
    assert m["elevation_gain_ft"] == 5000

def test_load_peaks_json(tmp_path):
    import json
    peaks = load_peaks(DATA)[:3]
    payload = {"peaks": [p.to_dict() for p in peaks]}
    fp = tmp_path / "p.json"
    fp.write_text(json.dumps(payload))
    loaded = load_peaks(str(fp))
    assert [p.name for p in loaded] == [p.name for p in peaks]

def test_load_peaks_core_only_has_no_collection_metadata(tmp_path):
    core = tmp_path / "core.csv"
    core.write_text("name,latitude,longitude,elevation_ft\n"
                     "Test Peak,37.0,-118.0,10000\n")
    peaks = load_peaks(str(core))
    assert len(peaks) == 1
    assert peaks[0].meta == {}
    assert peaks[0].collection == ""

def test_load_peaks_merges_collection_by_name(tmp_path):
    core = tmp_path / "core.csv"
    core.write_text("name,latitude,longitude,elevation_ft\n"
                     "Test Peak,37.0,-118.0,10000\n"
                     "Other Peak,37.1,-118.1,11000\n")
    collection = tmp_path / "collection.csv"
    collection.write_text("name,list,section\n"
                           "Test Peak,SPS,1.1\n")
    peaks = load_peaks(str(core), collections_path=str(collection))
    by_name = {p.name: p for p in peaks}
    assert by_name["Test Peak"].meta == {"list": "SPS", "section": 1.1}
    assert by_name["Test Peak"].collection == "SPS"
    # "Other Peak" has no collection row -- present, but with no metadata,
    # not silently dropped.
    assert by_name["Other Peak"].meta == {}
    assert by_name["Other Peak"].collection == ""

def test_load_peaks_collection_filter_after_merge(tmp_path):
    core = tmp_path / "core.csv"
    core.write_text("name,latitude,longitude,elevation_ft\n"
                     "Test Peak,37.0,-118.0,10000\n"
                     "Other Peak,37.1,-118.1,11000\n")
    collection = tmp_path / "collection.csv"
    collection.write_text("name,list\nTest Peak,SPS\nOther Peak,non-SPS\n")
    sps_only = load_peaks(str(core), list_filter="SPS", collections_path=str(collection))
    assert [p.name for p in sps_only] == ["Test Peak"]

def test_load_peaks_missing_collections_file_is_ignored(tmp_path):
    core = tmp_path / "core.csv"
    core.write_text("name,latitude,longitude,elevation_ft\n"
                     "Test Peak,37.0,-118.0,10000\n")
    peaks = load_peaks(str(core), collections_path=str(tmp_path / "does_not_exist.csv"))
    assert len(peaks) == 1
    assert peaks[0].meta == {}

def test_load_peaks_collection_cannot_redefine_core_column(tmp_path):
    import pytest
    core = tmp_path / "core.csv"
    core.write_text("name,latitude,longitude,elevation_ft\n"
                     "Test Peak,37.0,-118.0,10000\n")
    collection = tmp_path / "collection.csv"
    collection.write_text("name,elevation_ft\nTest Peak,9999\n")
    with pytest.raises(ValueError, match="redefines core column"):
        load_peaks(str(core), collections_path=str(collection))


if __name__ == "__main__":
    # The contributing checklist runs this file directly; keep that working by
    # delegating to pytest rather than maintaining a hand-rolled runner.
    import pytest as _pytest

    raise SystemExit(_pytest.main([__file__, "-q"]))
