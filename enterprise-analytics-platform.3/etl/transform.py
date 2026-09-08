"""
Transformation layer.

Cleans raw extracted DataFrames into a shape that matches the ORM models,
applies validation rules, and separates good rows from rejected rows so
the pipeline can report data-quality metrics.

This replaces the original clean_data() / transform_data() / validate_data()
helpers from utils.py with the same business rules (dedup, fillna, salary
after bonus, cpu_status banding) -- reorganized into the pipeline's
extract -> transform -> load contract and with proper row-level validation
instead of a blanket fillna(0).
"""
import pandas as pd
from etl.logger import get_logger
from config.config import config

logger = get_logger("etl.transform")


def transform_employees(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean + enrich raw employee/CPU-usage rows.
    Returns (clean_df, rejected_df).
    """
    if df.empty:
        return df, df

    df = df.copy()
    initial_count = len(df)

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required_cols = {"employee_id", "name", "department", "salary", "cpu_usage"}
    missing = required_cols - set(df.columns)
    if missing:
        logger.error(f"Employee source missing required columns: {missing}")
        return pd.DataFrame(), df

    # Drop exact duplicate rows (mirrors original clean_data's drop_duplicates)
    before_dedup = len(df)
    df = df.drop_duplicates()
    if before_dedup != len(df):
        logger.warning(f"Dropped {before_dedup - len(df)} exact-duplicate rows")

    # Type coercion
    df["salary"] = pd.to_numeric(df["salary"], errors="coerce")
    df["cpu_usage"] = pd.to_numeric(df["cpu_usage"], errors="coerce")

    # Validation rules -> split good vs rejected instead of silently
    # fillna(0), which would hide bad records inside real metrics
    valid_mask = (
        df["employee_id"].notna()
        & df["name"].notna()
        & df["salary"].notna() & (df["salary"] > 0)
        & df["cpu_usage"].notna() & (df["cpu_usage"] >= 0) & (df["cpu_usage"] <= 100)
    )
    clean = df[valid_mask].copy()
    rejected = df[~valid_mask].copy()

    # Deduplicate on business key
    before_key_dedup = len(clean)
    clean = clean.drop_duplicates(subset=["employee_id"])
    if before_key_dedup != len(clean):
        logger.warning(f"Dropped {before_key_dedup - len(clean)} duplicate employee_id rows")

    # Enrichment (business rules from the original transform_data())
    def _format_department(name: str) -> str:
        name = str(name).strip()
        # Preserve short all-caps acronyms (IT, HR) instead of letting
        # str.title() mangle them into "It" / "Hr"
        return name if name.isupper() and len(name) <= 4 else name.title()

    clean["department"] = clean["department"].fillna("Unknown").apply(_format_department)
    clean["salary_after_bonus"] = (clean["salary"] * 1.1).round(2)
    clean["cpu_status"] = clean["cpu_usage"].apply(
        lambda x: "High" if x > config.CPU_HIGH_THRESHOLD
        else "Medium" if x > config.CPU_MEDIUM_THRESHOLD
        else "Low"
    )
    clean["source"] = "csv"

    logger.info(
        f"Transform complete: {initial_count} raw -> {len(clean)} clean, "
        f"{len(rejected)} rejected"
    )
    return clean, rejected


def transform_logs(df: pd.DataFrame) -> pd.DataFrame:
    """Clean raw log rows into the SystemLog schema."""
    if df.empty:
        return df

    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["level"] = df.get("level", pd.Series(dtype=str)).str.upper()
    df["response_time_ms"] = pd.to_numeric(df.get("response_time_ms"), errors="coerce")
    df["status_code"] = pd.to_numeric(df.get("status_code"), errors="coerce").astype("Int64")

    df = df.dropna(subset=["timestamp"])
    logger.info(f"Transformed {len(df)} log rows")
    return df
