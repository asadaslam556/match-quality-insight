"""Loads and runs the .sql files in this package's sql/ directory.

Two of those files carry a {dimension} placeholder because the only thing that varies
between segment breakdowns is the grouping column. The placeholder is filled from the
whitelist below and never from raw request input, so no user-supplied string reaches the
query text.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

SQL_DIR = Path(__file__).parent / "sql"

# Public segment name -> the column it maps to in scored_applications.
# "country" resolves to the job's country rather than the candidate's: the job posting is
# what defines the market being served, and 94% of applications are same-country anyway.
DIMENSIONS: dict[str, str] = {
    "overall": "'overall'",
    "job_family": "job_family",
    "country": "job_country",
    "seniority": "seniority",
    "model_version": "llm_model_version",
    "profile_band": "profile_band",
}


@lru_cache(maxsize=None)
def _read(name: str) -> str:
    path = SQL_DIR / f"{name}.sql"
    if not path.exists():
        raise FileNotFoundError(f"No such query: {name}")
    return path.read_text()


def resolve_dimension(dimension: str) -> str:
    if dimension not in DIMENSIONS:
        raise ValueError(f"Unknown dimension '{dimension}'. Expected one of: {', '.join(DIMENSIONS)}")
    return DIMENSIONS[dimension]


def run(session: Session, name: str, dimension: str | None = None, **params: Any) -> list[dict]:
    sql = _read(name)
    if dimension is not None:
        sql = sql.format(dimension=resolve_dimension(dimension))
    rows = session.execute(text(sql), params).mappings().all()
    return [dict(row) for row in rows]


def run_one(session: Session, name: str, **params: Any) -> dict:
    """For the queries that aggregate down to a single row."""
    rows = run(session, name, **params)
    return rows[0] if rows else {}
