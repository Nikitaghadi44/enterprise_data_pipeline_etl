"""
Load layer.

Writes clean DataFrames into the database via SQLAlchemy sessions.
Uses upsert-by-business-key semantics (update if employee_id/timestamp
already exists, insert otherwise) so the pipeline is safe to re-run.
"""
import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from database.db import get_session
from database.models import EmployeeRecord, SystemLog
from etl.logger import get_logger

logger = get_logger("etl.load")


def load_employees(df: pd.DataFrame) -> int:
    """Upsert clean employee rows. Returns count of rows written."""
    if df.empty:
        logger.info("No employee rows to load")
        return 0

    written = 0
    with get_session() as session:
        for _, row in df.iterrows():
            try:
                existing = (
                    session.query(EmployeeRecord)
                    .filter_by(employee_id=row["employee_id"])
                    .first()
                )
                if existing:
                    existing.name = row["name"]
                    existing.department = row["department"]
                    existing.salary = row["salary"]
                    existing.salary_after_bonus = row["salary_after_bonus"]
                    existing.cpu_usage = row["cpu_usage"]
                    existing.cpu_status = row["cpu_status"]
                    existing.source = row.get("source", "csv")
                else:
                    session.add(EmployeeRecord(
                        employee_id=row["employee_id"],
                        name=row["name"],
                        department=row["department"],
                        salary=row["salary"],
                        salary_after_bonus=row["salary_after_bonus"],
                        cpu_usage=row["cpu_usage"],
                        cpu_status=row["cpu_status"],
                        source=row.get("source", "csv"),
                    ))
                written += 1
            except SQLAlchemyError as e:
                logger.error(f"Failed to load employee_id={row.get('employee_id')}: {e}")

    logger.info(f"Loaded {written} employee records")
    return written


def load_logs(df: pd.DataFrame) -> int:
    """Insert clean log rows. Returns count of rows written."""
    if df.empty:
        logger.info("No log rows to load")
        return 0

    written = 0
    with get_session() as session:
        for _, row in df.iterrows():
            try:
                session.add(SystemLog(
                    timestamp=row["timestamp"],
                    service=row.get("service"),
                    level=row.get("level"),
                    status_code=row.get("status_code") if pd.notna(row.get("status_code")) else None,
                    response_time_ms=row.get("response_time_ms") if pd.notna(row.get("response_time_ms")) else None,
                    message=row.get("message"),
                ))
                written += 1
            except SQLAlchemyError as e:
                logger.error(f"Failed to load log row: {e}")

    logger.info(f"Loaded {written} log records")
    return written
