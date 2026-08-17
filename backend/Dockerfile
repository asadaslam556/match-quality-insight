FROM python:3.12-slim

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
COPY sql ./sql
COPY scripts ./scripts

# Editable install so pyproject stays the single source of truth for dependencies and the
# container runs the same files that are checked in, not a copy in site-packages.
RUN pip install --no-cache-dir -e .

# Load the CSVs, then serve. The load script drops and recreates everything, so a restart
# is harmless and a fresh container always matches a fresh database.
CMD ["sh", "-c", "python -m scripts.load_data && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
