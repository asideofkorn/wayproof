"""`plan` surfaces the rules that apply once you hold the permit.

README Q6, "What must I carry?" -- *wrong if it says "required" without saying
that a digital reservation confirmation is not a permit*. Before this, the
scorecard read:

    Q6   answered 0   omitted 49   no-data 413

`omitted` means the project holds the fact and no surface shows it.
`regulations_for()` resolved 18 rules for Desolation, including a bear canister
required on pain of a $5,000 fine, the website rendered all 18, and
`resolve_plan()` took no `regulations` argument at all -- so `plan.py`, the
flagship command, printed none of them for any objective.

Two halves, because the question has two. Equipment comes from the food-storage
rule; the *document* comes from `permits.carry`, a new column and a sibling of
`excludes` for the same reason: being wrong about it is discovered at the
trailhead and cannot be fixed there.

Run with:  python -m pytest tests/test_rules_in_force.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.access import load_approaches
from wayproof.data_loader import load_peaks, load_trailheads
from wayproof.permits import load_permits
from wayproof.plan import format_plan_summary, resolve_plan
from wayproof.regulations import load_regulations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", *p)  # noqa: E731
TRIP = date(2027, 7, 15)


def _inputs(with_regulations=True):
    return dict(
        peaks=load_peaks(D("peaks.csv"), collections_path=D("collections", "sps.csv")),
        trailheads=load_trailheads(D("trailheads.csv")),
        permits=load_permits(D("permits.csv"), D("release_policies.csv")),
        approaches=load_approaches(D("approaches.csv")),
        regulations=load_regulations(D("regulations.csv")) if with_regulations else None,
    )


def _plan(name, **kw):
    return resolve_plan([name], TRIP, **{**_inputs(), **kw})


# -- the equipment half ------------------------------------------------------

def test_the_bear_canister_requirement_reaches_the_flagship_command():
    # $5,000 under 36 CFR 261.58(cc). It was in the dataset and on the website
    # and absent from plan.py for every objective.
    text = format_plan_summary(_plan("Mount Tallac"))
    assert "Rules in force" in text
    assert "hard-sided, bear-proof food storage container is REQUIRED" in text
    assert "36 CFR 261.58(cc)" in text, "the citation is the part that carries the fine"


def test_all_eighteen_desolation_rules_resolve_into_the_plan():
    result = _plan("Mount Tallac")
    assert len(result.regulations) == 18


def test_an_inherited_rule_says_where_it_came_from():
    # State law read as one wilderness's local quirk is the failure the scope
    # labels exist to prevent.
    text = format_plan_summary(_plan("Mount Tallac"))
    assert "[CA state law]" in text
    assert "[Eldorado National Forest]" in text


def test_every_objective_resolves_at_least_the_statewide_rule():
    # Every permit group declares jurisdiction CA, so the California Campfire
    # Permit reaches all of them -- which is the point of storing it once. There
    # is therefore no real objective with an empty rulebook.
    for name in ("Mount Whitney", "Mount Tallac", "Rose Peak", "Smith Mountain"):
        assert _plan(name).regulations, f"{name} resolved no rules at all"


def test_a_group_matching_no_rule_prints_no_section():
    # The empty branch still has to be right: an out-of-state group inherits
    # nothing, and an empty heading would read as "no rules apply".
    from wayproof.model import Trailhead
    from wayproof.permits import PermitRule
    rule = PermitRule(permit_group="nevada_x", agency="Humboldt-Toiyabe NF",
                      permit_type="X", quota_required=False, jurisdiction="NV")
    result = resolve_plan(
        ["Mount Whitney"], TRIP,
        peaks=_inputs()["peaks"],
        trailheads=[Trailhead(name="Whitney Portal", latitude=36.5861,
                              longitude=-118.2414, permit_group="nevada_x")],
        permits={"nevada_x": rule},
        regulations=load_regulations(D("regulations.csv")),
    )
    assert result.regulations == []
    assert "Rules in force" not in format_plan_summary(result)


def test_omitting_the_regulations_argument_still_works():
    # Optional, like every other dataset resolve_plan takes.
    result = _plan("Mount Tallac", regulations=None)
    assert result.regulations == []
    assert "Rules in force" not in format_plan_summary(result)


# -- the document half, which is what the question's "wrong if" names --------

def test_the_permit_says_a_confirmation_is_not_a_permit():
    text = format_plan_summary(_plan("Mount Tallac"))
    assert "MUST CARRY" in text
    assert "CONFIRMATION is NOT a valid permit" in text


def test_must_carry_reads_above_the_notes_it_was_buried_in():
    # It spent its life as one clause among cancellation policy and fire-scar
    # hazards. A party that reads it late is a party turned back.
    text = format_plan_summary(_plan("Mount Tallac"))
    assert text.index("MUST CARRY") < text.index("  Note:")


def test_the_carry_fact_is_no_longer_also_in_the_prose():
    # A fact asserted in two places is a fact maintained in neither -- the
    # discipline test_notes_split.py already enforces for rules and excludes.
    permits = load_permits(D("permits.csv"), D("release_policies.csv"))
    for group, rule in permits.items():
        if not rule.carry:
            continue
        prose = f"{rule.notes} {rule.reservation_method}".lower()
        for phrase in ("not a valid permit", "carried by the group leader",
                       "carried on your person", "carry a signed physical"):
            assert phrase not in prose, f"{group}: {phrase!r} is in both carry and prose"


def test_every_carry_value_names_what_does_not_count():
    # The field exists for the trap, not for a restatement of "bring the permit".
    permits = load_permits(D("permits.csv"), D("release_policies.csv"))
    stated = {g: r.carry for g, r in permits.items() if r.carry}
    assert stated, "no permit states a carry requirement"
    for group, carry in stated.items():
        low = carry.lower()
        assert any(w in low for w in ("not ", "printed", "physical", "signed", "in person")), (
            f"{group}'s carry value does not say what is required or what fails: {carry!r}"
        )


# -- all surfaces, and the machine one --------------------------------------

def test_the_website_states_the_carry_requirement_too():
    # Three surfaces that cannot disagree is the site's whole claim; a field the
    # CLI shows and the pages do not would break it.
    from wayproof.model import Trailhead
    from wayproof.render import render_trailhead_html, render_trailhead_markdown
    from wayproof.views import trailhead_view
    permits = load_permits(D("permits.csv"), D("release_policies.csv"))
    view = trailhead_view(Trailhead(name="Mount Tallac", latitude=38.9, longitude=-120.1,
                                    permit_group="desolation"),
                          permits["desolation"])
    assert "CONFIRMATION is NOT a valid permit" in view["permit"]["carry"]
    for text in (render_trailhead_html(view), render_trailhead_markdown(view)):
        assert "What you must carry" in text
        assert "CONFIRMATION is NOT a valid permit" in text


def test_the_json_surface_carries_the_rules_with_their_scope():
    payload = json.loads(json.dumps(_plan("Mount Tallac").to_dict()))
    rules = {r["id"]: r for group in payload["regulations"] for r in group["rules"]}
    canister = rules["desolation-bear-canister"]
    assert canister["citation"] == "36 CFR 261.58(cc)"
    assert canister["inherited"] is False and canister["scope"] == "this permit"
    statewide = rules["ca-campfire-permit"]
    assert statewide["inherited"] is True and "state law" in statewide["scope"]


def test_the_rules_are_ordered_consequence_first():
    # regulations.CATEGORY_ORDER puts the ones that carry a fine or end a trip
    # first. The plan must not re-sort them alphabetically.
    labels = [line.strip() for line in
              format_plan_summary(_plan("Mount Tallac")).splitlines()
              if line.startswith("  ") and not line.startswith("    ")
              and line.strip() in ("Fire", "Food storage", "Group size", "Camping")]
    assert labels == ["Fire", "Food storage", "Group size", "Camping"]


def test_the_stay_limit_says_it_is_counted_per_household_not_per_person():
    # A family reading "30 total days per year" as a per-person allowance plans
    # roughly twice the camping it may book, and cannot fix it by reserving in
    # another member's name. Ordinance 38 does not say how the limit is
    # counted; the booking system does, and the rule has to carry it.
    from wayproof.regulations import load_regulations
    rule = next(r for r in load_regulations(D("regulations.csv"))
                if r.regulation_id == "ebrpd-camping-stay-limit")
    blob = f"{rule.summary} {rule.detail}".lower()
    assert "per household address" in blob
    assert "not per person" in blob
    assert "walk-in" in blob, "nights taken without a reservation count toward the tally"
