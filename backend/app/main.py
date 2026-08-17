"""Application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

app = FastAPI(
    title="Match Quality Insight",
    description="Quality metrics for the rule-based and LLM scorers behind candidate matching.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)
