"""
Runs the ad-hoc analysis queries in sql/queries.sql against the configured
database and prints results.

Rebuilt from the original run_sql.py, which had a real database password
hardcoded in the connection string. Credentials now come exclusively from
config/config.py (which reads from .env) -- nothing sensitive lives in
source control.
"""
from sqlalchemy import text
from database.db import engine
from etl.logger import get_logger

logger = get_logger("database.run_sql")

SQL_FILE = "sql/queries.sql"


def run_sql_file(path: str = SQL_FILE):
    logger.info("=" * 50)
    logger.info(f"Running SQL statements from {path}")
    logger.info("=" * 50)

    with open(path, "r") as f:
        raw = f.read()

    # Strip full-line comments, then split into individual statements
    statements = [
        line for line in raw.splitlines() if not line.strip().startswith("--")
    ]
    commands = "\n".join(statements).split(";")

    with engine.connect() as conn:
        for command in commands:
            command = command.strip()
            if not command:
                continue
            logger.info(f"Executing: {command[:60]}...")
            result = conn.execute(text(command))
            if result.returns_rows:
                rows = result.fetchall()
                for row in rows:
                    print(row)

    logger.info("All SQL queries executed successfully")


if __name__ == "__main__":
    run_sql_file()
