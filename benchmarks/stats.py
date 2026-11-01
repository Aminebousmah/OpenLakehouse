"""Pure statistics of the benchmark report."""

from __future__ import annotations

from collections.abc import Sequence


def percentile(values: Sequence[float], share: float) -> float:
    """Nearest-rank percentile, which stays an actually observed latency."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    rank = max(1, int(-(-share * len(ordered) // 1)))
    return ordered[rank - 1]


def median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2
