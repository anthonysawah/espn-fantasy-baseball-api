"""Shared utility helpers."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .constants import POSITION_MAP, PRO_TEAM_MAP, STAT_ID_MAP


def decode_stats(raw_stats: Mapping[str, Any] | None) -> dict[str, float]:
    """Translate ESPN's numeric-keyed stats dict into human-readable keys.

    ESPN returns stats as ``{"0": 450, "1": 120, ...}`` where the keys are the
    numeric stat ids documented in :data:`espn_fantasy_baseball.constants.STAT_ID_MAP`.
    """
    if not raw_stats:
        return {}
    out: dict[str, float] = {}
    for key, value in raw_stats.items():
        try:
            stat_id = int(key)
        except (TypeError, ValueError):
            continue
        name = STAT_ID_MAP.get(stat_id, f"STAT_{stat_id}")
        out[name] = value
    return out


def decode_positions(eligible_slots: Iterable[int] | None) -> list[str]:
    """Map a list of slot-ids to their human-readable position abbreviations."""
    if not eligible_slots:
        return []
    return [POSITION_MAP.get(slot, f"SLOT_{slot}") for slot in eligible_slots]


def decode_pro_team(pro_team_id: int | None) -> str:
    """Translate ESPN's proTeamId to a team abbreviation (``"FA"`` if unknown)."""
    if pro_team_id is None:
        return "FA"
    return PRO_TEAM_MAP.get(pro_team_id, f"TEAM_{pro_team_id}")


def chunked(seq: list[Any], size: int) -> Iterable[list[Any]]:
    """Yield successive ``size``-sized chunks from ``seq``."""
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
