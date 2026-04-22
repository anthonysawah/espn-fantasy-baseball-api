"""Tests for the small utility helpers."""

from __future__ import annotations

from espn_fantasy_baseball.utils import (
    chunked,
    coerce_float,
    coerce_int,
    decode_positions,
    decode_pro_team,
    decode_stats,
)


def test_decode_stats_translates_numeric_keys() -> None:
    out = decode_stats({"5": 30, "20": 80})
    assert out == {"HR": 30, "R": 80}


def test_decode_stats_handles_none_and_junk() -> None:
    assert decode_stats(None) == {}
    assert decode_stats({"not-a-number": 1}) == {}


def test_decode_stats_preserves_unknown_ids() -> None:
    out = decode_stats({"999": 1.23})
    assert out == {"STAT_999": 1.23}


def test_decode_positions_maps_slot_ids() -> None:
    assert decode_positions([0, 4, 14]) == ["C", "SS", "SP"]


def test_decode_positions_handles_empty_and_unknown() -> None:
    assert decode_positions(None) == []
    assert decode_positions([999]) == ["SLOT_999"]


def test_decode_pro_team_known_and_unknown() -> None:
    assert decode_pro_team(10) == "NYY"
    assert decode_pro_team(None) == "FA"
    assert decode_pro_team(0) == "FA"
    assert decode_pro_team(999) == "TEAM_999"


def test_chunked() -> None:
    assert list(chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert list(chunked([], 3)) == []


def test_coerce_helpers_are_defensive() -> None:
    assert coerce_int("7") == 7
    assert coerce_int(None, default=-1) == -1
    assert coerce_float("3.14") == 3.14
    assert coerce_float("nope", default=0.0) == 0.0
