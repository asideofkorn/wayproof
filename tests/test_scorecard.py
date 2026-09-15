"""Tests for the README-question scorecard.

The scorecard's whole value is that it tracks the README's question list. If the
two drift, it measures a list nobody agreed to -- so the load-bearing test here
is :func:`test_every_readme_question_is_accounted_for`, which fails when a
question is added, reworded or removed without the scorecard following.

The rest guard the arithmetic: a verdict vocabulary that silently grows, a proxy
that returns None, a structural row that quietly starts varying.

Run with:  python -m pytest tests/test_scorecard.py
"""

from __future__ import annotations

import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "scripts"))

import scorecard
from scorecard import (
    ANSWERED,
    NOT_SCORED,
    QUESTIONS,
    VERDICT_MEANING,
    VERDICTS,
    build,
    format_report,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIP = datetime.date(2027, 7, 15)


def _readme_questions() -> list:
    """The bolded questions under "What Someone Actually Asks", verbatim."""
    text = open(os.path.join(ROOT, "README.md")).read()
    start = text.index("## What Someone Actually Asks")
    section = text[start:text.index("## `plan`: Objective + Date")]
    return [m.group(1) for m in re.finditer(r"^- \*\*(.+?)\*\*", section, re.M)]


def _built():
    if not hasattr(_built, "cache"):
        _built.cache = build(TRIP)
    return _built.cache


# -- the guard that keeps this honest ---------------------------------------

def test_every_readme_question_is_accounted_for():
    # Either scored, or listed in NOT_SCORED with a reason. A question that is
    # neither is one the scorecard silently ignores.
    readme = _readme_questions()
    scored = {q.text for q in QUESTIONS}
    excused = {k.split(" ", 1)[1] for k in NOT_SCORED}
    unaccounted = [q for q in readme if q not in scored and q not in excused]
    assert unaccounted == [], (
        "README questions the scorecard neither scores nor excuses: "
        f"{unaccounted}. Add a proxy, or add it to NOT_SCORED with a reason."
    )


def test_no_scorecard_question_has_been_dropped_from_the_readme():
    # The reverse drift: a question reworded in the README leaves the scorecard
    # measuring text that no longer exists.
    readme = set(_readme_questions())
    stale = [q.qid for q in QUESTIONS if q.text not in readme]
    assert stale == [], (
        f"scorecard questions no longer in the README verbatim: {stale}. "
        "Re-copy the text, or retire the row."
    )


def test_each_scorecard_question_quotes_the_readmes_wrong_if():
    # "wrong if" is the falsification criterion; a scorecard row without one is
    # measuring completeness, which is the thing the README rejects.
    for q in QUESTIONS:
        assert q.wrong_if.strip(), f"{q.qid} carries no 'wrong if'"


# -- arithmetic --------------------------------------------------------------

def test_every_question_scores_every_objective_exactly_once():
    built = _built()
    for q in QUESTIONS:
        total = sum(built["scores"][q.qid].values())
        assert total == built["n"], (
            f"{q.qid} scored {total} objectives, expected {built['n']} -- "
            "a proxy returned nothing, or returned twice"
        )


def test_no_proxy_invents_a_verdict():
    built = _built()
    for q in QUESTIONS:
        unknown = set(built["scores"][q.qid]) - set(VERDICTS)
        assert not unknown, f"{q.qid} produced verdict(s) outside the vocabulary: {unknown}"


def test_every_verdict_says_what_it_asks_of_you():
    assert set(VERDICTS) == set(VERDICT_MEANING), (
        "a verdict with no stated fix is a number nobody can act on"
    )


def test_a_structural_question_really_is_constant():
    # The flag exists so constant rows are counted once instead of 462 times.
    # If one starts varying, the flag is now a lie and the aggregate is wrong.
    built = _built()
    for q in QUESTIONS:
        if q.structural:
            seen = {v for v, count in built["scores"][q.qid].items() if count}
            assert len(seen) == 1, (
                f"{q.qid} is marked structural but produced {seen} -- "
                "it varies by objective now, so drop the flag"
            )


def test_detail_and_totals_agree():
    built = _built()
    for q in QUESTIONS:
        for verdict, names in built["detail"][q.qid].items():
            assert len(names) == built["scores"][q.qid][verdict]


# -- the report --------------------------------------------------------------

def test_the_report_states_what_it_does_not_measure():
    # A coverage number read as a correctness number is worse than no number.
    report = format_report(_built())
    assert "NOT whether the answer is right" in report


def test_the_report_names_every_weak_proxy():
    report = format_report(_built())
    for q in QUESTIONS:
        if q.limit:
            assert q.qid in report.split("where a proxy is weaker")[1], (
                f"{q.qid} has a stated limit that the report does not print"
            )


def test_the_report_excludes_structural_rows_from_the_aggregate():
    built = _built()
    report = format_report(built)
    varying = [q for q in QUESTIONS if not q.structural]
    assert f"{len(varying)} objective-varying questions" in report


def test_the_scorecard_does_not_assert_anything():
    # Deliberately not a test of the data: this measures, it does not gate. If
    # it ever exits non-zero on a bad number it becomes a target, and the
    # cheapest way to move most rows is to add unchecked data.
    assert scorecard.main(["--date", "2027-07-15"]) == 0


def test_by_question_rejects_an_unknown_id():
    assert scorecard.main(["--by-question", "Q999"]) == 2


# -- the finding this exists to make visible --------------------------------

def test_the_worst_tier_one_row_is_reported_not_averaged():
    # Q6 "What must I carry?" answers 0 of 462: the rules exist for 49 and
    # plan.py surfaces none of them. An average would hide that behind Q2's 309.
    built = _built()
    q6 = built["scores"]["Q6"]
    assert q6[ANSWERED] == 0
    assert "At most 0 objectives can have all" in format_report(built)


def test_question_ids_follow_readme_order():
    # The ids are how a story doc, a commit or a PR refers to a question. If
    # they stop matching the README's order they stop being a shared spine --
    # and I already numbered two rows wrong once, which this would have caught.
    readme = _readme_questions()
    position = {text: i + 1 for i, text in enumerate(readme)}
    wrong = []
    for q in QUESTIONS:
        expected = f"Q{position[q.text]}"
        if q.qid != expected:
            wrong.append(f"{q.qid} should be {expected} ({q.text!r})")
    for key in NOT_SCORED:
        qid, text = key.split(" ", 1)
        expected = f"Q{position[text]}"
        if qid != expected:
            wrong.append(f"NOT_SCORED {qid} should be {expected} ({text!r})")
    assert wrong == [], "ids out of step with README order: " + "; ".join(wrong)


def test_the_readme_question_count_is_stated_correctly():
    # Guards the number quoted in the scorecard's own output and in review notes.
    readme = _readme_questions()
    assert len(readme) == len(QUESTIONS) + len(NOT_SCORED)
    assert len(readme) == 21, (
        f"the README now lists {len(readme)} questions, not 21 -- update any "
        "count quoted elsewhere"
    )


def test_each_tier_is_represented():
    # A scorecard that only measured tier 3 would look busy and say nothing
    # about whether a trip can happen.
    tiers = {q.tier for q in QUESTIONS}
    assert {1, 2, 3} <= tiers, f"tiers covered: {tiers}"
