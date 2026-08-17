"""Tests for the statistics in compute.py.

The expected values here are worked out by hand or come from a second, independent
implementation. The AUC tests also cross-check against scikit-learn on random data with
heavy ties, which is where a hand-written rank implementation usually goes wrong.
"""

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from app.metrics.compute import (
    population_stability_index,
    precision_at_k,
    precision_recall_at_threshold,
    roc_auc,
    wilson_interval,
)


class TestRocAuc:
    def test_perfect_ranking_scores_one(self):
        assert roc_auc([0, 0, 1, 1], [1, 2, 3, 4]) == 1.0

    def test_reversed_ranking_scores_zero(self):
        assert roc_auc([1, 1, 0, 0], [1, 2, 3, 4]) == 0.0

    def test_all_scores_tied_is_a_coin_flip(self):
        # Every pair is a tie, so each contributes half credit.
        assert roc_auc([0, 1, 0, 1], [5, 5, 5, 5]) == 0.5

    def test_partial_ties_split_credit(self):
        # One positive at 2, one negative at 2, one negative at 1.
        # Pairs: (pos 2 vs neg 1) wins, (pos 2 vs neg 2) ties -> (1 + 0.5) / 2.
        assert roc_auc([0, 0, 1], [1, 2, 2]) == pytest.approx(0.75)

    def test_returns_none_when_only_one_class_present(self):
        assert roc_auc([1, 1, 1], [1, 2, 3]) is None
        assert roc_auc([0, 0, 0], [1, 2, 3]) is None

    def test_rejects_mismatched_lengths(self):
        with pytest.raises(ValueError):
            roc_auc([0, 1], [1.0])

    @pytest.mark.parametrize("distinct_values", [2, 5, 50, 1000])
    def test_matches_sklearn_including_heavy_ties(self, distinct_values):
        rng = np.random.default_rng(distinct_values)
        for _ in range(25):
            size = int(rng.integers(20, 400))
            labels = rng.integers(0, 2, size)
            if labels.sum() in (0, size):
                continue
            scores = rng.integers(0, distinct_values, size).astype(float)
            assert roc_auc(labels, scores) == pytest.approx(roc_auc_score(labels, scores))


class TestWilsonInterval:
    def test_brackets_the_observed_rate(self):
        low, high = wilson_interval(50, 100)
        assert low < 0.5 < high

    def test_stays_inside_zero_and_one_at_the_extremes(self):
        # This is why Wilson is used instead of the normal approximation, which would
        # produce a negative lower bound here.
        assert wilson_interval(0, 10) == (0.0, pytest.approx(0.2775, abs=1e-4))
        assert wilson_interval(10, 10)[1] == 1.0

    def test_narrows_as_the_sample_grows(self):
        small_low, small_high = wilson_interval(5, 10)
        large_low, large_high = wilson_interval(500, 1000)
        assert (large_high - large_low) < (small_high - small_low)

    def test_returns_none_for_an_empty_segment(self):
        assert wilson_interval(0, 0) is None


class TestPrecisionAtK:
    def test_takes_the_highest_scoring_k(self):
        assert precision_at_k([0, 1, 1, 0], [1, 9, 8, 2], k=2) == 1.0

    def test_k_larger_than_the_population_falls_back_to_all_rows(self):
        assert precision_at_k([0, 1], [1, 2], k=99) == 0.5

    def test_non_positive_k_returns_none(self):
        assert precision_at_k([0, 1], [1, 2], k=0) is None
        assert precision_at_k([0, 1], [1, 2], k=-5) is None

    def test_empty_input_returns_none(self):
        assert precision_at_k([], [], k=10) is None


class TestPrecisionRecallAtThreshold:
    def test_counts_flagged_precision_and_recall(self):
        result = precision_recall_at_threshold([0, 1, 1, 0], [10, 90, 80, 20], threshold=50)
        assert result["flagged"] == 2
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0

    def test_threshold_is_inclusive(self):
        assert precision_recall_at_threshold([1], [70], threshold=70)["flagged"] == 1

    def test_missed_positives_reduce_recall(self):
        # Two positives exist, the threshold only catches one of them.
        result = precision_recall_at_threshold([1, 1, 0], [90, 10, 5], threshold=50)
        assert result["precision"] == 1.0
        assert result["recall"] == pytest.approx(0.5)

    def test_precision_is_none_when_nothing_is_flagged(self):
        result = precision_recall_at_threshold([0, 1], [10, 20], threshold=99)
        assert result["flagged"] == 0
        assert result["precision"] is None


class TestPopulationStabilityIndex:
    EDGES = (0, 40, 50, 60, 70, 80, 90, 101)

    def test_identical_distributions_score_zero(self):
        sample = [10, 45, 55, 65, 75, 85, 95]
        assert population_stability_index(sample, sample, self.EDGES) == pytest.approx(0.0)

    def test_is_symmetric(self):
        a, b = [10, 20, 30, 65], [70, 75, 80, 95]
        forward = population_stability_index(a, b, self.EDGES)
        backward = population_stability_index(b, a, self.EDGES)
        assert forward == pytest.approx(backward)

    def test_a_shifted_distribution_crosses_the_alert_band(self):
        rng = np.random.default_rng(0)
        baseline = rng.normal(60, 15, 3000)
        shifted = rng.normal(70, 15, 3000)
        assert population_stability_index(baseline, shifted, self.EDGES) > 0.10

    def test_empty_bins_do_not_blow_up(self):
        # Without flooring the bin shares this divides by zero and returns infinity.
        result = population_stability_index([5, 5, 5], [95, 95, 95], self.EDGES)
        assert np.isfinite(result)

    def test_returns_none_for_an_empty_side(self):
        assert population_stability_index([], [1, 2, 3], self.EDGES) is None
