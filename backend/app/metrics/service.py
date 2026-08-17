"""The domain layer: turns query rows plus statistics into the metrics the API returns.

Routes stay thin and do no arithmetic. Everything below reads from queries.py and computes
with compute.py, which keeps the SQL and the statistics independently testable.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.metrics import queries
from app.metrics.compute import (
    MIN_SEGMENT_SIZE,
    population_stability_index,
    precision_at_k,
    precision_recall_at_threshold,
    roc_auc,
    wilson_interval,
)

HEALTHCARE = "Healthcare"

# Where the ranked-queue metrics are cut. A recruiter realistically works through the top
# of a shortlist, not the whole population, so precision is reported at those depths.
TOP_K_DEPTHS = (100, 250, 500, 1000)

# Bin edges for the drift comparison. Fixed rather than quantile-based, because a gate that
# re-derives its own bins from the new release cannot detect a shift in the new release.
LLM_PSI_EDGES = (0, 40, 50, 60, 70, 80, 90, 101)
RULE_PSI_EDGES = (0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.01)

PSI_WARN = 0.10
PSI_FAIL = 0.25


def _scorer_metrics(labels: list[int], scores: list[float], threshold: float) -> dict[str, Any]:
    return {
        "n": len(labels),
        "auc": roc_auc(labels, scores),
        "at_threshold": precision_recall_at_threshold(labels, scores, threshold),
        "precision_at_k": {str(k): precision_at_k(labels, scores, k) for k in TOP_K_DEPTHS},
    }


def overview(session: Session) -> dict[str, Any]:
    counts = queries.run_one(session, "overview")
    pooled = effectiveness(session, exclude_family=None)
    without_healthcare = effectiveness(session, exclude_family=HEALTHCARE)

    return {
        "counts": counts,
        "pooled": {"rule": pooled["rule"]["auc"], "llm": pooled["llm"]["auc"], "n": pooled["rule"]["n"]},
        "excluding_healthcare": {
            "rule": without_healthcare["rule"]["auc"],
            "llm": without_healthcare["llm"]["auc"],
            "n": without_healthcare["rule"]["n"],
        },
        "quality_gate": quality_gate(session),
    }


def effectiveness(session: Session, exclude_family: str | None = None) -> dict[str, Any]:
    rows = queries.run(session, "labeled_scores", dimension="overall", exclude_family=exclude_family)
    labels = [row["label"] for row in rows]

    return {
        "excluded_job_family": exclude_family,
        "distribution_by_decision": queries.run(
            session, "score_distribution", exclude_family=exclude_family
        ),
        "rule": _scorer_metrics(labels, [row["rule_score"] for row in rows], threshold=0.5),
        "llm": _scorer_metrics(
            labels, [row["llm_score"] for row in rows], threshold=settings.llm_flag_threshold
        ),
    }


def agreement(session: Session, exclude_family: str | None = None) -> dict[str, Any]:
    quadrants = queries.run(session, "disagreement_outcomes", exclude_family=exclude_family)

    decided = sum(row["decided"] for row in quadrants)
    agreed = sum(row["decided"] for row in quadrants if row["quadrant"] in ("both_high", "both_low"))
    by_quadrant = {row["quadrant"]: row for row in quadrants}

    def rate(quadrant: str) -> float | None:
        row = by_quadrant.get(quadrant)
        return row["positive_rate"] if row else None

    rule_only = rate("rule_high_llm_low")
    llm_only = rate("llm_high_rule_low")

    return {
        "excluded_job_family": exclude_family,
        "quadrants": quadrants,
        "agreement_rate": agreed / decided if decided else None,
        # Which scorer to trust when only one of them is positive about an application.
        "winner_on_disagreement": (
            None
            if rule_only is None or llm_only is None
            else ("rule" if rule_only > llm_only else "llm" if llm_only > rule_only else "tie")
        ),
        "matrix": queries.run(session, "agreement_matrix"),
    }


def segments(session: Session, dimension: str) -> dict[str, Any]:
    aggregates = queries.run(session, "segment_metrics", dimension=dimension)
    labelled = queries.run(session, "labeled_scores", dimension=dimension, exclude_family=None)

    grouped: dict[str, dict[str, list]] = defaultdict(lambda: {"labels": [], "rule": [], "llm": []})
    for row in labelled:
        bucket = grouped[str(row["segment"])]
        bucket["labels"].append(row["label"])
        bucket["rule"].append(row["rule_score"])
        bucket["llm"].append(row["llm_score"])

    results = []
    for row in aggregates:
        name = str(row["segment"])
        bucket = grouped.get(name, {"labels": [], "rule": [], "llm": []})
        decided, positives = row["decided"], row["positives"]
        interval = wilson_interval(positives, decided)

        results.append(
            {
                **row,
                "segment": name,
                "positive_rate": positives / decided if decided else None,
                "positive_rate_ci": list(interval) if interval else None,
                "rule_auc": roc_auc(bucket["labels"], bucket["rule"]),
                "llm_auc": roc_auc(bucket["labels"], bucket["llm"]),
                # Segments below this size are shown but flagged, so a reader does not act
                # on a difference that the confidence interval cannot support.
                "is_small_sample": decided < MIN_SEGMENT_SIZE,
            }
        )

    return {"dimension": dimension, "segments": results, "min_segment_size": MIN_SEGMENT_SIZE}


def calibration(session: Session, scorer: str, exclude_family: str | None = None) -> dict[str, Any]:
    if scorer not in ("llm", "rule"):
        raise ValueError("scorer must be 'llm' or 'rule'")

    rows = queries.run(session, "calibration", scorer=scorer, exclude_family=exclude_family)
    for row in rows:
        interval = wilson_interval(row["positives"], row["decided"])
        row["positive_rate_ci"] = list(interval) if interval else None
        row["band_label"] = f"{(row['band'] - 1) * 10}-{row['band'] * 10}"
        row["is_small_sample"] = row["decided"] < MIN_SEGMENT_SIZE

    return {"scorer": scorer, "excluded_job_family": exclude_family, "bands": rows}


def recruiter_behaviour(session: Session) -> dict[str, Any]:
    return {
        "monthly": queries.run(session, "recruiter_engagement_monthly"),
        "funnel": queries.run_one(session, "recruiter_funnel"),
    }


def quality_gate(session: Session) -> dict[str, Any]:
    """Post-release drift check, comparing the current scorer version against the previous one.

    The rule scorer runs alongside on the same applications and did not change, so it acts
    as a control: if both drift, the applicant population moved; if only the LLM drifts, the
    model did.
    """
    rows = queries.run(session, "version_scores")

    versions = sorted({row["llm_model_version"] for row in rows})
    if len(versions) < 2:
        return {"status": "skipped", "reason": "fewer than two model versions present"}

    baseline_version, current_version = versions[-2], versions[-1]
    baseline = [row for row in rows if row["llm_model_version"] == baseline_version]
    current = [row for row in rows if row["llm_model_version"] == current_version]

    llm_psi = population_stability_index(
        [row["llm_score"] for row in baseline], [row["llm_score"] for row in current], LLM_PSI_EDGES
    )
    rule_psi = population_stability_index(
        [row["rule_score"] for row in baseline], [row["rule_score"] for row in current], RULE_PSI_EDGES
    )

    threshold = settings.llm_flag_threshold
    baseline_flagged = sum(row["llm_score"] >= threshold for row in baseline) / len(baseline)
    current_flagged = sum(row["llm_score"] >= threshold for row in current) / len(current)

    status = "fail" if llm_psi >= PSI_FAIL else "warn" if llm_psi >= PSI_WARN else "pass"

    return {
        "status": status,
        "baseline_version": baseline_version,
        "current_version": current_version,
        "llm_psi": llm_psi,
        "rule_psi_control": rule_psi,
        "warn_at": PSI_WARN,
        "fail_at": PSI_FAIL,
        "mean_llm_score": {
            "baseline": sum(row["llm_score"] for row in baseline) / len(baseline),
            "current": sum(row["llm_score"] for row in current) / len(current),
        },
        "flag_rate_at_threshold": {
            "threshold": threshold,
            "baseline": baseline_flagged,
            "current": current_flagged,
        },
    }
