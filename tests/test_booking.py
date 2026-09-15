"""Tests for agency-scoped booking mechanics.

Run with:  python -m pytest tests/test_booking.py
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wayproof.booking import (
    ALL, BACKPACK, FAMILY, GROUP, BookingChannel, channels_for,
    load_booking_channels,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS = os.path.join(ROOT, "data", "booking_channels.csv")


def _ch(cid, applies_to, scope_value="ebrpd"):
    return BookingChannel(channel_id=cid, scope_type="agency",
                          scope_value=scope_value, applies_to=applies_to)


def test_missing_file_is_not_an_error(tmp_path):
    assert load_booking_channels(tmp_path / "nope.csv") == []


def test_invalid_applies_to_is_rejected_loudly(tmp_path):
    path = tmp_path / "booking_channels.csv"
    path.write_text("channel_id,scope_type,scope_value,applies_to\nx,agency,ebrpd,cabin\n")
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
