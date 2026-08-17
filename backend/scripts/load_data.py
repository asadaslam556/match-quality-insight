"""Rebuild the database from the four source CSVs.

Drops and recreates everything, so it is safe to run repeatedly.
Run with: python -m scripts.load_data
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402

SCHEMA_FILE = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"

# Load order follows the foreign keys. Columns are listed explicitly so a change in
# CSV column order fails loudly instead of loading into the wrong fields.
TABLES = [
    ("candidates", "candidates.csv", None),
    ("jobs", "jobs.csv", None),
    # Pending applications carry empty strings for these two, which COPY would otherwise
    # reject against a TIMESTAMP column. FORCE_NULL turns them into real NULLs.
    ("applications", "applications.csv", ("recruiter_decision", "decision_at")),
    ("recruiter_events", "recruiter_events.csv", None),
]


def copy_csv(cursor: psycopg.Cursor, table: str, path: Path, force_null: tuple[str, ...] | None) -> int:
    options = ["FORMAT csv", "HEADER true"]
    if force_null:
        options.append(f"FORCE_NULL ({', '.join(force_null)})")
    statement = f"COPY {table} FROM STDIN WITH ({', '.join(options)})"

    with cursor.copy(statement) as copy, path.open("rb") as handle:
        while chunk := handle.read(1 << 16):
            copy.write(chunk)

    cursor.execute(f"SELECT count(*) FROM {table}")
    return cursor.fetchone()[0]


def main() -> None:
    data_dir = Path(settings.data_dir)
    missing = [name for _, name, _ in TABLES if not (data_dir / name).exists()]
    if missing:
        raise SystemExit(f"Missing CSVs in {data_dir}: {', '.join(missing)}")

    with psycopg.connect(settings.libpq_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(SCHEMA_FILE.read_text())
            for table, filename, force_null in TABLES:
                rows = copy_csv(cursor, table, data_dir / filename, force_null)
                print(f"{table:<18} {rows:>6} rows")
        connection.commit()

    print("Load complete.")


if __name__ == "__main__":
    main()
