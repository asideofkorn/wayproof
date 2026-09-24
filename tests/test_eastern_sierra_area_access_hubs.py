"""Eastern Sierra area pages act as canonical route and access hubs."""

from pathlib import Path

from wayproof.canonical_storage import load_canonical


ROOT = Path(__file__).resolve().parents[1]


def test_area_hubs_have_routes_and_access_points():
    records = load_canonical(ROOT)
    relationships = records.relationships

    expected = {
        "place-rock-creek-canyon": {"route-little-lakes-valley", "trailhead-mosquito-flat"},
        "place-convict-lake": {"route-convict-lake-loop", "trailhead-convict-lake"},
        "place-lundy-canyon": {"route-lundy-canyon", "trailhead-lundy-canyon"},
        "place-mammoth-lakes-basin": {"route-heart-lake-mammoth", "trailhead-coldwater"},
        "place-bishop-creek-canyon": {"route-sabrina-blue-lake", "trailhead-sabrina-basin"},
    }
    for area_id, related_ids in expected.items():
        actual = {
            relationship.subject_id for relationship in relationships
            if relationship.object_id == area_id
        }
        assert related_ids <= actual


def test_area_hubs_render_related_routes_and_trailheads(generated_site):
    site_root, _ = generated_site
    expected = {
        "place-rock-creek-canyon": ("Little Lakes Valley Trail", "Mosquito Flat Trailhead"),
        "place-lundy-canyon": ("Lundy Canyon Trail", "Lundy Canyon Trailhead"),
        "place-mammoth-lakes-basin": ("Heart Lake Trail", "Coldwater Trailhead"),
        "place-bishop-creek-canyon": ("Sabrina Basin Trail to Blue Lake", "Sabrina Basin Trailhead"),
    }
    for area_id, names in expected.items():
        page = (site_root / "knowledge" / area_id / "index.html").read_text()
        for name in names:
            assert name in page
