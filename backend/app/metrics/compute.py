"""Statistics that SQL cannot express cleanly.

Everything that is a plain aggregation lives in the .sql files next door. What stays here
needs the full ranked array in memory: AUC, precision@k, threshold sweeps, and the
distribution comparisons used by the quality gate.

These are hand-written rather than pulled from scikit-learn so the tie handling and the
small-sample guards are visible and testable. test_compute.py cross-checks the AUC against
sklearn on random data.
"""

from __future__ import annotations

from math import log, sqrt
from typing import Sequence

import numpy as np

# Below this many decided applications a segment metric is too noisy to report as fact.
MIN_SEGMENT_SIZE = 30


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Rank values from 1..n, giving tied values their shared mean rank."""
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]

    start = 0
    for i in range(1, len(values) + 1):
        if i == len(values) or sorted_values[i] != sorted_values[start]:
            ranks[order[start:i]] = (start + i + 1) / 2
            start = i
    return ranks


def roc_auc(labels: Sequence[int], scores: Sequence[float]) -> float | None:
    """Probability that a random positive outranks a random negative.

    Computed through the Mann-Whitney U identity, which handles tied scores correctly by
    splitting the credit. Returns None when the segment has only one class, because AUC is
    undefined there rather than zero.
    """
    y = np.asarray(labels, dtype=float)
    x = np.asarray(scores, dtype=float)
    if len(y) != len(x):
        raise ValueError("labels and scores must be the same length")

    positives = int(y.sum())
    negatives = len(y) - positives
    if positives == 0 or negatives == 0:
        return None

    ranks = _average_ranks(x)
    rank_sum = float(ranks[y == 1].sum())
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% confidence interval for a proportion.

    Wilson rather than the normal approximation because segments here get small and the
    naive interval misbehaves near 0 and 1.
    """
    if total <= 0:
        return None

    p = successes / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    margin = z * sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def precision_at_k(labels: Sequence[int], scores: Sequence[float], k: int) -> float | None:
    """Share of positives among the k highest-scoring applications.

    This is the metric that matches how the product is actually used: a recruiter works
    down a ranked queue, so what matters is the top of the list, not the whole curve.
    """
    if k <= 0:
        return None

    y = np.asarray(labels, dtype=float)
    x = np.asarray(scores, dtype=float)
    k = min(k, len(y))
    if k == 0:
        return None

    top = np.argsort(-x, kind="mergesort")[:k]
    return float(y[top].mean())


def precision_recall_at_threshold(
    labels: Sequence[int], scores: Sequence[float], threshold: float
) -> dict[str, float | int | None]:
    """How a fixed cut-off behaves: what it flags, how much of it is right, what it misses."""
    y = np.asarray(labels, dtype=float)
    x = np.asarray(scores, dtype=float)

    flagged = x >= threshold
    n_flagged = int(flagged.sum())
    n_positive = int(y.sum())

    return {
        "threshold": threshold,
        "flagged": n_flagged,
        "flagged_rate": float(flagged.mean()) if len(y) else None,
        "precision": float(y[flagged].mean()) if n_flagged else None,
        "recall": float(y[flagged].sum() / n_positive) if n_positive else None,
    }


def population_stability_index(
    baseline: Sequence[float], current: Sequence[float], edges: Sequence[float]
) -> float | None:
    """Standard drift measure between two score distributions.

    Convention in the industry is below 0.10 stable, 0.10 to 0.25 moderate shift, above
    0.25 major shift. Empty bins are floored so a single missing bucket cannot send the
    result to infinity.
    """
    base = np.asarray(baseline, dtype=float)
    curr = np.asarray(current, dtype=float)
    if len(base) == 0 or len(curr) == 0:
        return None

    base_share = np.clip(np.histogram(base, bins=edges)[0] / len(base), 1e-6, None)
    curr_share = np.clip(np.histogram(curr, bins=edges)[0] / len(curr), 1e-6, None)

    return float(sum((c - b) * log(c / b) for b, c in zip(base_share, curr_share)))
