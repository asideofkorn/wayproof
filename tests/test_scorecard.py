"""Tests for the scorecard.

``scripts/scorecard.py`` owns its question list. It was previously parsed out
of the README, which made a five-line edit there fail four tests here and made
the README expensive to change -- the README now carries a few examples and the
spec lives in one place.

These guard the arithmetic and the honesty: a verdict vocabulary that silently
grows, a proxy that returns None, a structural row that quietly starts varying,
a report that hides its own weak proxies.

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
    OMITTED,
    PARTIAL,
    NO_MODEL,
    NOT_SCORED,
    QUESTIONS,
    VERDICT_MEANING,
    VERDICTS,
    build,
    format_report,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRIP = datetime.date(2027, 7, 15)


def _built():
    if not hasattr(_built, "cache"):
        _built.cache = build(TRIP)
    return _built.cache


# -- the guard that keeps this honest ---------------------------------------


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


# -- how the report presents a bad row --------------------------------------

def test_tier_one_rows_are_listed_worst_first_and_never_averaged():
    # A mean would hide the binding row. When Q6 answered 0 of 462, Q2's 309 and
    # Q3's 286 would have averaged it into looking like two thirds coverage.
    built = _built()
    report = format_report(built)
    tier1 = [q for q in QUESTIONS if q.tier == 1 and not q.structural]
    block = report.split("tier 1 -- ")[1]
    listed = [q.qid for q in tier1 if f"{q.qid} answered" in block]
    assert set(listed) == {q.qid for q in tier1}, "every tier-1 row must be listed"
    order = [block.index(f"{q.qid} answered") for q in
             sorted(tier1, key=lambda q: built["scores"][q.qid][ANSWERED])]
    assert order == sorted(order), "tier-1 rows must read worst first"
    worst = min(built["scores"][q.qid][ANSWERED] for q in tier1)
    assert f"At most {worst} objectives can have all" in report


def test_the_bound_is_the_weakest_row_not_the_mean():
    built = _built()
    tier1 = [q for q in QUESTIONS if q.tier == 1 and not q.structural]
    counts = [built["scores"][q.qid][ANSWERED] for q in tier1]
    worst = min(counts)
    assert worst < sum(counts) / len(counts), (
        "this test is vacuous unless the rows differ -- pick a different assertion"
    )
    assert f"At most {worst} objectives" in format_report(built)


# -- Q6 needs both halves ----------------------------------------------------

def test_q6_is_only_answered_when_both_halves_reach_the_reader():
    # The README's falsification criterion is about the DOCUMENT -- "wrong if it
    # says 'required' without saying that a digital reservation confirmation is
    # not a permit" -- not about equipment. A proxy that scored only the
    # food-storage rule would have gone green on half the question.
    built = _built()
    q6 = built["scores"]["Q6"]
    assert q6[ANSWERED], "some objectives should have both halves"
    assert q6[PARTIAL], "some should have exactly one, and must not read as answered"
    q = next(x for x in QUESTIONS if x.qid == "Q6")
    assert "both halves" in q.limit


def test_nothing_is_held_and_hidden_any_more():
    # OMITTED means the project holds a fact and no surface shows it. The
    # regulations subsystem was the only instance: 193 cells across Q6, Q12, Q13
    # and Q14, resolved for the website and absent from plan.py.
    built = _built()
    still_hidden = {q.qid: built["scores"][q.qid][OMITTED]
                    for q in QUESTIONS if built["scores"][q.qid][OMITTED]}
    assert still_hidden == {}, f"data held but not surfaced: {still_hidden}"


def test_each_tier_is_represented():
    # A scorecard that only measured tier 3 would look busy and say nothing
    # about whether a trip can happen.
    tiers = {q.tier for q in QUESTIONS}
    assert {1, 2, 3} <= tiers, f"tiers covered: {tiers}"


def test_no_model_reports_whole_questions_and_only_the_real_gaps():
    # Two ways this line has been wrong. First it printed the CELL count, which
    # was 0 because structural rows are counted once -- "no-model 0" directly
    # beneath a list of five questions the schema cannot express. The fix counted
    # structural questions instead, which was right only while every structural
    # row happened to score no-model.
    #
    # Q5 broke that: it is still constant for every objective, but it now scores
    # `declined` because `--exit` gave the other end somewhere to live. Counting
    # structural rows would overstate the schema gap by one, so the line counts
    # rows whose single constant verdict IS no-model.
    built = _built()
    report = format_report(built)
    tail = report.split("what each verdict asks of you:")[1]
    line = next(l for l in tail.splitlines() if l.strip().startswith("no-model"))

    structural = [q for q in QUESTIONS if q.structural]
    gaps = [q for q in structural
            if [v for v in VERDICTS if built["scores"][q.qid][v]] == [NO_MODEL]]
    assert gaps, "this test assumes at least one genuine schema gap"
    assert len(gaps) < len(structural), (
        "vacuous unless the two counts differ -- if every structural row is a "
        "schema gap again, this test no longer distinguishes them"
    )
    assert f"{len(gaps):5d}" in line, f"no-model line misstates the gap: {line!r}"
    assert f"{len(structural):5d}" not in line, (
        f"no-model line counts constant rows, not schema gaps: {line!r}"
    )
    assert "whole questions" in line


def test_the_structural_block_labels_each_rows_verdict():
    # A constant `declined` and a constant `no-model` ask for different work, so
    # listing them together unlabelled reads as five schema gaps.
    built = _built()
    report = format_report(built)
    block = report.split("same verdict for every objective")[1]
    for q in (q for q in QUESTIONS if q.structural):
        seen = [v for v in VERDICTS if built["scores"][q.qid][v]]
        assert f"{q.qid} tier {q.tier}  [{seen[0]}]" in block, (
            f"{q.qid} is listed without its verdict"
        )
