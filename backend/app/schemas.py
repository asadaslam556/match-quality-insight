"""Response shapes for the API.

The metric rows are deliberately typed loosely: their columns are decided by the SQL files,
and mirroring every column here would mean editing two places for one change. What is
pinned down is the envelope of each endpoint, which is the part the frontend depends on.
"""

from typing import Any

from pydantic import BaseModel

Row = dict[str, Any]


class ScorerMetrics(BaseModel):
    n: int
    auc: float | None
    at_threshold: Row
    precision_at_k: dict[str, float | None]


class AucPair(BaseModel):
    rule: float | None
    llm: float | None
    n: int


class QualityGate(BaseModel):
    status: str
    baseline_version: str | None = None
    current_version: str | None = None
    llm_psi: float | None = None
    rule_psi_control: float | None = None
    warn_at: float | None = None
    fail_at: float | None = None
    mean_llm_score: Row | None = None
    flag_rate_at_threshold: Row | None = None
    reason: str | None = None


class Overview(BaseModel):
    counts: Row
    pooled: AucPair
    excluding_healthcare: AucPair
    quality_gate: QualityGate


class Effectiveness(BaseModel):
    excluded_job_family: str | None
    distribution_by_decision: list[Row]
    rule: ScorerMetrics
    llm: ScorerMetrics


class Agreement(BaseModel):
    excluded_job_family: str | None
    quadrants: list[Row]
    agreement_rate: float | None
    winner_on_disagreement: str | None
    matrix: list[Row]


class Segments(BaseModel):
    dimension: str
    segments: list[Row]
    min_segment_size: int


class Calibration(BaseModel):
    scorer: str
    excluded_job_family: str | None
    bands: list[Row]


class RecruiterBehaviour(BaseModel):
    monthly: list[Row]
    funnel: Row
