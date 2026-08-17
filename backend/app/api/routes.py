"""HTTP layer. Each route validates its inputs and hands straight to the service."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_session
from app.metrics import service
from app.metrics.queries import DIMENSIONS

router = APIRouter(prefix="/api")

# Reused by three endpoints. Annotated keeps it a type, not a shared mutable default.
ExcludeFamily = Annotated[
    str | None,
    Query(
        description="Drop one job family before computing. Use Healthcare to see the "
        "platform without the rule scorer's broken segment.",
    ),
]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/overview", response_model=schemas.Overview)
def get_overview(session: Session = Depends(get_session)):
    return service.overview(session)


@router.get("/effectiveness", response_model=schemas.Effectiveness)
def get_effectiveness(
    exclude_family: ExcludeFamily = None,
    session: Session = Depends(get_session),
):
    return service.effectiveness(session, exclude_family=exclude_family)


@router.get("/agreement", response_model=schemas.Agreement)
def get_agreement(
    exclude_family: ExcludeFamily = None,
    session: Session = Depends(get_session),
):
    return service.agreement(session, exclude_family=exclude_family)


@router.get("/segments", response_model=schemas.Segments)
def get_segments(
    dimension: str = Query("job_family", description=f"One of: {', '.join(DIMENSIONS)}"),
    session: Session = Depends(get_session),
):
    try:
        return service.segments(session, dimension=dimension)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/calibration", response_model=schemas.Calibration)
def get_calibration(
    scorer: Literal["llm", "rule"] = "llm",
    exclude_family: ExcludeFamily = None,
    session: Session = Depends(get_session),
):
    return service.calibration(session, scorer=scorer, exclude_family=exclude_family)


@router.get("/recruiter-behaviour", response_model=schemas.RecruiterBehaviour)
def get_recruiter_behaviour(session: Session = Depends(get_session)):
    return service.recruiter_behaviour(session)


@router.get("/quality-gate", response_model=schemas.QualityGate)
def get_quality_gate(session: Session = Depends(get_session)):
    return service.quality_gate(session)
