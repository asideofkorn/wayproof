from pathlib import Path

from wayproof.read_service import CanonicalReadService


def test_batch_04_group_camps_are_queryable() -> None:
    reads = CanonicalReadService(Path(__file__).resolve().parents[1])

    assert reads.entity("group-camp-briones-homestead-valley").name == "Homestead Valley Group Camp"
    briones = reads.get("claim", "claim-briones-group-camps-reserveamerica").value
    assert [p["maximum_people"] for p in briones["products"]] == [300, 75, 50]
    pinole = reads.get("claim", "claim-point-pinole-group-camp-reserveamerica").value
    assert pinole["facility_id"] == "110457"
    assert pinole["products"][0]["product_id"] == "1157"
    assert pinole["products"][0]["maximum_people"] == 35
