"""Evidence-bounded comparison of explicitly selected hiking routes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from .schema import CanonicalRecords, Claim, KnowledgeGap


class DistanceFit(str, Enum):
    FITS = "fits"
    EXCEEDS = "exceeds"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HikeCandidateComparison:
    route_id: str
    name: str
    round_trip_miles: Optional[float]
    distance_fit: DistanceFit
    distance_claim_ids: Tuple[str, ...] = ()
    knowledge_gap_ids: Tuple[str, ...] = ()
    needs_current_check: bool = False


@dataclass(frozen=True)
class HikeComparison:
    maximum_round_trip_miles: float
    candidates: Tuple[HikeCandidateComparison, ...]


def _distance(claims: Tuple[Claim, ...]) -> tuple[Optional[float], Tuple[str, ...]]:
    candidates = []
    for claim in claims:
        value = claim.value
        if not isinstance(value, dict):
            continue
        if isinstance(value.get("round_trip_miles"), (int, float)):
            candidates.append((0, float(value["round_trip_miles"]), claim.claim_id))
        elif isinstance(value.get("one_way_miles"), (int, float)):
            candidates.append((1, float(value["one_way_miles"]) * 2, claim.claim_id))
        elif isinstance(value.get("one_way_distance_miles"), (int, float)):
            candidates.append((2, float(value["one_way_distance_miles"]) * 2, claim.claim_id))
        elif isinstance(value.get("one_way_distance_miles_from_source_features"), (int, float)):
            candidates.append((
                2,
                float(value["one_way_distance_miles_from_source_features"]) * 2,
                claim.claim_id,
            ))
    if not candidates:
        return None, ()
    priority = min(item[0] for item in candidates)
    preferred = tuple(item for item in candidates if item[0] == priority)
    distance = preferred[0][1]
    # Preserve competing equally preferred source values instead of averaging them.
    matching = tuple(item[2] for item in preferred if abs(item[1] - distance) < 0.000001)
    return round(distance, 8), matching


def _current_check(gaps: Tuple[KnowledgeGap, ...]) -> bool:
    volatile_terms = ("current", "conditions", "open", "seasonal", "weather", "fire", "road")
    return any(
        any(term in f"{gap.question} {gap.reason}".casefold() for term in volatile_terms)
        for gap in gaps
    )


def compare_hikes(
    records: CanonicalRecords,
    route_ids: Tuple[str, ...],
    maximum_round_trip_miles: float,
) -> HikeComparison:
    """Compare caller-selected routes without inferring a candidate set or duration."""
    if maximum_round_trip_miles <= 0:
        raise ValueError("maximum_round_trip_miles must be greater than zero")
    entities = {item.entity_id: item for item in records.entities}
    output = []
    for route_id in dict.fromkeys(route_ids):
        entity = entities.get(route_id)
        if entity is None or entity.kind != "route":
            raise KeyError(f"unknown route: {route_id}")
        claims = tuple(item for item in records.claims if item.subject_id == route_id)
        gaps = tuple(item for item in records.gaps if route_id in item.related_ids)
        distance, claim_ids = _distance(claims)
        if distance is None:
            fit = DistanceFit.UNKNOWN
        elif distance <= maximum_round_trip_miles:
            fit = DistanceFit.FITS
        else:
            fit = DistanceFit.EXCEEDS
        output.append(HikeCandidateComparison(
            route_id=route_id,
            name=entity.name,
            round_trip_miles=distance,
            distance_fit=fit,
            distance_claim_ids=claim_ids,
            knowledge_gap_ids=tuple(sorted(item.gap_id for item in gaps)),
            needs_current_check=_current_check(gaps),
        ))
    rank = {DistanceFit.FITS: 0, DistanceFit.UNKNOWN: 1, DistanceFit.EXCEEDS: 2}
    ordered = tuple(sorted(
        output,
        key=lambda item: (
            rank[item.distance_fit],
            item.round_trip_miles if item.round_trip_miles is not None else float("inf"),
            item.name.casefold(),
        ),
    ))
    return HikeComparison(float(maximum_round_trip_miles), ordered)
