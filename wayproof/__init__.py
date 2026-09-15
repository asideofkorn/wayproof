"""Source-backed trip logistics: what access applies, what permit governs it,
when you must act, and what evidence stands behind the answer.

The experimental geographic clustering and TSP ordering that used to live here
were removed. They grouped SPS peaks by proximity and sequenced them, were
never wired into ``plan`` or the published site, and drew more documentation
than the product. Recoverable from git history if wanted.
"""

from .approach import approach_leg, approach_metrics, choose_trailhead, entry_conflicts
from .data_loader import load_peaks, load_trailheads, resolve_peak_name
from .distances import (
    build_distance_matrix,
    haversine_miles,
    leg_metrics,
    naismith_effective_miles,
)
from .model import Cluster, Peak, Trailhead

__all__ = [
    "Peak",
    "Cluster",
    "Trailhead",
    "load_peaks",
    "load_trailheads",
    "resolve_peak_name",
    "haversine_miles",
    "naismith_effective_miles",
    "leg_metrics",
    "build_distance_matrix",
    "choose_trailhead",
    "entry_conflicts",
    "approach_leg",
    "approach_metrics",
]

__version__ = "0.1.0"
