"""Tests for agency-scoped booking mechanics.

Run with:  python -m pytest tests/test_booking.py
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.booking import (
    ALL, BACKPACK, CABIN, FAMILY, GROUP, UNKNOWN_FACILITY_LABEL, BookingChannel,
    channels_for, dangling_facility_ids, facilities_by_park,
    facilities_without_campgrounds, facility_for, facility_label,
    load_booking_channels, load_booking_facilities, parks_by_facility,
)
from wayproof.camping import load_campgrounds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS = os.path.join(ROOT, "data", "booking_channels.csv")
FACILITIES = os.path.join(ROOT, "data", "booking_facilities.csv")
CAMPGROUNDS = os.path.join(ROOT, "data", "campgrounds.csv")


def _ch(cid, applies_to, scope_value="ebrpd"):
    return BookingChannel(channel_id=cid, scope_type="agency",
                          scope_value=scope_value, applies_to=applies_to)


def test_missing_file_is_not_an_error(tmp_path):
    assert load_booking_channels(tmp_path / "nope.csv") == []


def test_invalid_applies_to_is_rejected_loudly(tmp_path):
    # This test used "cabin" as its nonsense value until Del Valle's facility
    # turned out to sell five of them, which is a small lesson in picking
    # placeholders: the vocabulary was incomplete, not the value absurd.
    path = tmp_path / "booking_channels.csv"
    path.write_text("channel_id,scope_type,scope_value,applies_to\nx,agency,ebrpd,yurt\n")
    with pytest.raises(ValueError, match="applies_to"):
        load_booking_channels(path)


def test_a_class_resolves_its_own_channel_plus_the_agency_wide_one():
    # Specific-plus-general, the same layering regulations_for does: the
    # District-wide contact is stored once and read alongside the per-class
    # method, rather than being copied into each class.
    chans = [_ch("all", ALL), _ch("fam", FAMILY), _ch("bp", BACKPACK)]
    got = channels_for(chans, FAMILY, agency="ebrpd")
    assert [c.channel_id for c in got] == ["all", "fam"]


def test_the_agency_wide_channel_reads_first():
    chans = [_ch("zzz-family", FAMILY), _ch("aaa-all", ALL)]
    assert [c.channel_id for c in channels_for(chans, FAMILY, agency="ebrpd")] \
        == ["aaa-all", "zzz-family"]


def test_an_unknown_campsite_type_gets_no_class_specific_channel():
    # Guessing "family" here would tell a backpacker to book online, which
    # EBRPD does not allow. Silence about the class beats the wrong queue.
    chans = [_ch("all", ALL), _ch("fam", FAMILY)]
    assert [c.channel_id for c in channels_for(chans, "", agency="ebrpd")] == ["all"]


def test_channels_do_not_leak_to_another_agency():
    chans = [_ch("all", ALL), _ch("fam", FAMILY)]
    assert channels_for(chans, FAMILY, agency="inyo_nf") == []


# -- the committed data ------------------------------------------------------

def test_backpack_sites_are_not_sold_online_and_family_ones_are():
    chans = load_booking_channels(CHANNELS)
    backpack = channels_for(chans, BACKPACK, agency="ebrpd")
    method = " ".join(c.method for c in backpack)
    assert "Phone only" in method
    assert "NOT bookable online" in method

    family = channels_for(chans, FAMILY, agency="ebrpd")
    assert "reserveamerica.com" in " ".join(c.method for c in family)


def test_the_email_that_books_nothing_is_stated_as_not_a_channel():
    # EBRPD publishes a reservations email address that accepts no
    # reservations. It has its own field because finding out otherwise happens
    # when the site is already gone.
    chans = channels_for(load_booking_channels(CHANNELS), FAMILY, agency="ebrpd")
    not_accepted = " ".join(c.not_accepted for c in chans)
    assert "reservations@ebparks.org" in not_accepted
    assert "NO reservations" in not_accepted


def test_group_sites_need_a_longer_lead_time_than_family_ones():
    # Three business days against two. Reading one off the other books nothing.
    chans = load_booking_channels(CHANNELS)
    lead = {t: " ".join(c.lead_time for c in channels_for(chans, t, agency="ebrpd"))
            for t in (FAMILY, GROUP)}
    assert "2 business days" in lead[FAMILY]
    assert "3 business days" in lead[GROUP]


def test_a_booking_horizon_is_never_stored_without_the_date_it_was_read():
    # A rolling window expires. Shown undated, it silently becomes wrong.
    for c in load_booking_channels(CHANNELS):
        if c.horizon:
            assert c.horizon_as_of, f"{c.channel_id} states a horizon with no as-of date"


def test_every_committed_channel_cites_a_source():
    for c in load_booking_channels(CHANNELS):
        assert c.source_url, c.channel_id
        assert c.log_entry_ids, c.channel_id


# -- park scope --------------------------------------------------------------

def test_a_park_scoped_channel_needs_the_park_to_resolve():
    # Booking mechanics were agency-wide until Coyote Hills stated a group
    # deadline of its own, so a park-scoped row used to load and reach nothing.
    chans = [_ch("all", ALL),
             BookingChannel(channel_id="park-group", scope_type="park",
                            scope_value="Coyote Hills Regional Park",
                            applies_to=GROUP)]
    assert [c.channel_id for c in channels_for(chans, GROUP, agency="ebrpd")] == ["all"]
    got = channels_for(chans, GROUP, agency="ebrpd", park="Coyote Hills Regional Park")
    assert [c.channel_id for c in got] == ["all", "park-group"]


def test_a_parks_deadline_reads_after_the_districts_not_instead_of_it():
    # The narrower row is a tightening of the agency's, not a free-standing
    # claim -- shown in that order so it cannot be read as the only rule.
    chans = [_ch("aaa-agency-group", GROUP),
             BookingChannel(channel_id="zzz-park-group", scope_type="park",
                            scope_value="P", applies_to=GROUP)]
    got = channels_for(chans, GROUP, agency="ebrpd", park="P")
    assert [c.channel_id for c in got] == ["aaa-agency-group", "zzz-park-group"]


def test_a_park_scoped_channel_does_not_leak_to_another_park():
    chans = [BookingChannel(channel_id="park-group", scope_type="park",
                            scope_value="Coyote Hills Regional Park",
                            applies_to=GROUP)]
    assert channels_for(chans, GROUP, agency="ebrpd", park="Briones Regional Park") == []


def test_coyote_hills_asks_for_five_working_days_where_the_district_asks_three():
    # Both are true and they are not the same deadline. A party reading only
    # the District row plans to call three days out and is two days late.
    chans = load_booking_channels(CHANNELS)
    district = " ".join(c.lead_time for c in channels_for(chans, GROUP, agency="ebrpd"))
    assert "5 working days" not in district

    park = " ".join(c.lead_time for c in channels_for(
        chans, GROUP, agency="ebrpd", park="Coyote Hills Regional Park"))
    assert "5 working days" in park
    assert "paid in full" in park


def test_the_park_scoped_row_says_how_far_its_scope_is_a_judgement():
    # It was read on one campsite's page. Stored at park scope because four
    # other EBRPD listings do not carry it -- which is an inference, not a
    # quote, and the row has to say so.
    chans = channels_for(load_booking_channels(CHANNELS), GROUP,
                         agency="ebrpd", park="Coyote Hills Regional Park")
    row = next(c for c in chans if c.scope_type == "park")
    assert "JUDGEMENT" in row.lead_time
    assert "site scope" in row.lead_time


def test_a_cabin_borrows_one_rule_from_each_neighbour():
    # Booked on the family calendar's far end -- twelve weeks -- and on the
    # group clock at the near end, 72 hours rather than 48, then cancelled on
    # the group tiers. A class that fits neither is why applies_to is a
    # vocabulary rather than a flag for "is this a group site".
    chans = load_booking_channels(CHANNELS)
    cabin = next(c for c in channels_for(chans, CABIN, agency="ebrpd")
                 if c.applies_to == CABIN)
    assert "72 hours and 12 weeks" in cabin.lead_time
    assert "PHONE ONLY" in cabin.method
    assert "90% of site use fees refundable" in cabin.change_cancel
    assert "COUNT TOWARD THE HOUSEHOLD'S TWO-SITE LIMIT" in cabin.change_cancel


def test_family_refunds_are_prorated_by_night_and_group_ones_are_not():
    # A different SHAPE, not a different number: group bookings refund a
    # percentage of the whole, family bookings lose only the nights inside 48
    # hours. Cancelling a four-night family stay the day before returns three.
    chans = load_booking_channels(CHANNELS)
    family = " ".join(c.change_cancel for c in channels_for(chans, FAMILY, agency="ebrpd"))
    group = " ".join(c.change_cancel for c in channels_for(chans, GROUP, agency="ebrpd"))
    assert "within 48 hours of the cancellation request are non-refundable" in family
    assert "PRORATED BY NIGHT" in family
    assert "90% of site use fees refundable" in group
    assert "PRORATED BY NIGHT" not in group


# --- booking facilities: the level above a campground --------------------

# The one campground with no facility key. Named on the Ohlone Wilderness
# permit map and absent from the Del Valle listing that was read; its pair
# Caballo Loco IS on that listing, which is what gives that row a key.
FACILITY_UNRECORDED = {"Lil Chaparral Horse Camp"}


def test_missing_facility_file_is_not_an_error(tmp_path):
    assert load_booking_facilities(tmp_path / "nope.csv") == []


def test_every_campground_facility_key_resolves_to_a_facility():
    cgs = load_campgrounds(CAMPGROUNDS)
    assert dangling_facility_ids(cgs, load_booking_facilities(FACILITIES)) == []


def test_no_facility_sits_in_the_table_unused():
    # The other end of the join. A facility nobody books through is either a
    # row that should not be here or a campground that has not been keyed.
    cgs = load_campgrounds(CAMPGROUNDS)
    orphans = facilities_without_campgrounds(cgs, load_booking_facilities(FACILITIES))
    assert [f.facility_id for f in orphans] == []


def test_the_sunol_facility_sells_sites_in_exactly_three_parks():
    """The count this project has now got wrong once and must not again.

    A commit message, a docstring and a log entry all read "four different
    parks" while two earlier log entries said three. Four is the number of Del
    Valle camps on that facility, not the number of parks it reaches. This is
    the guard, and it fails if the number moves in either direction.
    """
    parks = parks_by_facility(load_campgrounds(CAMPGROUNDS))["EB/110028"]
    assert parks == {
        "Del Valle Regional Park",
        "Mission Peak Regional Preserve",
        "Sunol Regional Wilderness",
    }


def test_two_parks_are_sold_through_more_than_one_facility():
    # The other direction of the same asymmetry, and the reason facility_id is
    # a stored column rather than something a park could supply.
    by_park = facilities_by_park(load_campgrounds(CAMPGROUNDS))
    several = {p: sorted(f) for p, f in by_park.items() if len(f) > 1}
    assert several == {
        "Coyote Hills Regional Park": ["EB/110453", "EB/110750"],
        "Del Valle Regional Park": ["EB/110003", "EB/110028"],
    }


def test_park_does_not_determine_facility_in_either_direction():
    """Stated as an assertion because the tempting shortcut is to derive it.

    If park determined facility, this table could be dropped and the key read
    off the campground's park. It does not, in both directions at once.
    """
    cgs = load_campgrounds(CAMPGROUNDS)
    assert any(len(p) > 1 for p in parks_by_facility(cgs).values())
    assert any(len(f) > 1 for f in facilities_by_park(cgs).values())


def test_only_the_named_campground_has_no_facility():
    blank = {c.name for c in load_campgrounds(CAMPGROUNDS) if not c.facility_id}
    assert blank == FACILITY_UNRECORDED


def test_a_slug_is_never_presented_as_a_name():
    """The habit that produced two fabricated citations, guarded at the label.

    EB/110028's slug is 'sunol' and its published title is 'Sunol', while its
    park is Sunol Regional Wilderness -- so the two coincide there and nowhere
    else. Where no title has been read the label says "slug '...'" in words,
    because a bare slug rendered as a name is one step from a slug constructed
    from a name, which is how 'del-valle-regional-park' became a citation.
    """
    facs = {f.facility_id: f for f in load_booking_facilities(FACILITIES)}
    named = facility_label(facs["EB/110028"])
    assert named == "Sunol (EB/110028)"
    unnamed = facility_label(facs["EB/110453"])
    assert unnamed == "EB/110453, slug 'coyote-hills-regional-park'"
    assert "slug" in unnamed


def test_an_unrecorded_facility_is_labelled_rather_than_guessed_from_the_park():
    cg = {c.name: c for c in load_campgrounds(CAMPGROUNDS)}["Lil Chaparral Horse Camp"]
    facs = load_booking_facilities(FACILITIES)
    assert facility_for(cg, facs) is None
    assert facility_label(None) == UNKNOWN_FACILITY_LABEL
    # Its park HAS facilities. Falling back on one would be a coin toss.
    assert len(facilities_by_park(load_campgrounds(CAMPGROUNDS))[cg.park]) == 2


def test_a_repeated_facility_id_is_rejected_at_load(tmp_path):
    # The exact shape of the fabrication: 110455 under two slugs.
    path = tmp_path / "f.csv"
    path.write_text("facility_id,slug\nEB/110455,las-trampas-regional-wilderness\n"
                    "EB/110455,del-valle-regional-park\n")
    with pytest.raises(ValueError, match="appears twice"):
        load_booking_facilities(path)


def test_a_repeated_slug_is_rejected_at_load(tmp_path):
    path = tmp_path / "f.csv"
    path.write_text("facility_id,slug\nEB/110003,del-valle\nEB/110999,del-valle\n")
    with pytest.raises(ValueError, match="two facility ids"):
        load_booking_facilities(path)


def test_the_fabricated_facility_id_is_not_in_the_table():
    # EB/110448 was invented for Anthony Chabot, whose real facility is
    # EB/110004. It exists only in prose recording the mistake.
    ids = {f.facility_id for f in load_booking_facilities(FACILITIES)}
    assert "EB/110448" not in ids
    assert "EB/110004" in ids and "EB/110003" in ids
