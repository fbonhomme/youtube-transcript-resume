"""Run before uvicorn: ensure DB schema is up to date via alembic."""
import subprocess
import sys

from database import engine
from sqlalchemy import inspect, text


def main():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # DB was bootstrapped by create_all (no alembic): stamp to 0001 — the
    # pre-Alembic baseline (themes + summaries only). Later migrations are
    # all idempotent (inspect/get_columns guards), so `upgrade head` then
    # safely adds whatever the existing schema is missing.
    if "themes" in tables and "alembic_version" not in tables:
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            conn.execute(text("INSERT INTO alembic_version VALUES ('0001')"))
            conn.commit()
        print("[preflight] Stamped existing DB to revision 0001", flush=True)

    result = subprocess.run(["alembic", "upgrade", "head"])
    if result.returncode != 0:
        print("[preflight] alembic upgrade failed", file=sys.stderr, flush=True)
        sys.exit(1)

    print("[preflight] DB schema up to date", flush=True)


if __name__ == "__main__":
    main()
