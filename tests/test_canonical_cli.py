"""The terminal adapter delegates canonical planning to the shared service."""

import json
from pathlib import Path

from plan import main


ROOT = Path(__file__).resolve().parents[1]


def test_ambiguous_canonical_request_is_visible_and_nonzero(capsys):
    code = main([
        "Mount Whitney", "--date", "2027-08-12", "--canonical",
        "--repository", str(ROOT),
    ])

    output = capsys.readouterr().out
    assert code == 1
    assert "Trip plan: ambiguous" in output
    assert "route_ambiguous" in output
    assert "Readiness:" not in output


def test_ohlone_canonical_summary_uses_shared_traversal(capsys):
    code = main([
        "Ohlone Wilderness Trail", "--date", "2027-09-05", "--canonical",
        "--repository", str(ROOT),
        "--entry", "Mission Peak Stanford Avenue Staging Area",
        "--exit", "Lichen Bark Ohlone Trailhead",
        "--activity", "hiking", "--as-of", "2027-08-01",
    ])

    output = capsys.readouterr().out
    assert code == 0
    assert "Resolution: resolved" in output
    assert "Traversal: complete; 52 legs; 26.90 known mi; total incomplete" in output
    assert "Alternates:" in output
    assert "Operational inputs:" in output


def test_canonical_json_is_the_complete_composed_result(tmp_path, capsys):
    destination = tmp_path / "plan.json"
    code = main([
        "Mount Whitney", "--date", "2027-08-12", "--canonical",
        "--repository", str(ROOT), "--route", "Mount Whitney Trail",
        "--entry", "Whitney Portal", "--exit", "Whitney Portal",
        "--activity", "hiking", "--overnight",
        "--participant", "alice", "--participant", "bob",
        "--output", str(destination),
    ])

    assert code == 0
    payload = json.loads(destination.read_text())
    assert payload["state"] == "partial"
    assert payload["resolution"]["issues"][0]["code"] == "traversal_unavailable"
    assert payload["readiness"]["state"] == "blocked"
    assert payload["operational"]["state"] == "not_applicable"
    assert "Wrote plan" in capsys.readouterr().out


def test_invalid_dates_return_usage_error_without_a_traceback(capsys):
    code = main([
        "Mount Whitney", "--date", "next Tuesday", "--canonical",
        "--repository", str(ROOT),
    ])

    assert code == 2
    assert "must use YYYY-MM-DD" in capsys.readouterr().err
