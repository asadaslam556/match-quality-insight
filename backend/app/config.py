"""Runtime settings, read from the environment (or a local .env) with defaults for docker."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Resolved from the repo root rather than the working directory, so the same .env is
    # picked up whether the backend is started from the repo root or from backend/.
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://mqi:mqi@localhost:5432/mqi"
    data_dir: str = str(REPO_ROOT / "data")
    cors_origin: str = "http://localhost:5173"

    # Recruiters see a "strong candidate" flag above this LLM score. It is the threshold
    # every precision and recall figure in the API is reported against.
    llm_flag_threshold: int = 70

    @property
    def libpq_url(self) -> str:
        """The same URL without the SQLAlchemy driver suffix, for psycopg's COPY."""
        return self.database_url.replace("postgresql+psycopg://", "postgresql://")


settings = Settings()
