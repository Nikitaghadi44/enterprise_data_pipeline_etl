"""
Extraction layer.

Each extractor returns a pandas DataFrame with raw, un-cleaned data.
Add a new source by writing one function here and wiring it into
pipeline.py -- the rest of the pipeline doesn't need to change.
"""
import pandas as pd
import requests
from etl.logger import get_logger
from config.config import config

logger = get_logger("etl.extract")


def extract_csv_employees(path=None) -> pd.DataFrame:
    """Extract raw employee/CPU-usage data from a CSV file (HRIS + monitoring agent export)."""
    path = path or config.CSV_SOURCE_PATH
    logger.info(f"Extracting employee CSV data from {path}")
    try:
        df = pd.read_csv(path)
        logger.info(f"Extracted {len(df)} rows from CSV source")
        return df
    except FileNotFoundError:
        logger.error(f"CSV source not found: {path}")
        return pd.DataFrame()


def extract_logs(path=None) -> pd.DataFrame:
    """Extract raw system/application log rows (simulates log-shipper output)."""
    path = path or config.LOG_SOURCE_PATH
    logger.info(f"Extracting system logs from {path}")
    try:
        df = pd.read_csv(path)
        logger.info(f"Extracted {len(df)} log rows")
        return df
    except FileNotFoundError:
        logger.error(f"Log source not found: {path}")
        return pd.DataFrame()


def extract_api(url=None, limit=50) -> pd.DataFrame:
    """
    Extract data from a REST API source. Disabled by default
    (USE_API_SOURCE=false) so the pipeline runs fully offline; flip it
    on in .env to pull from a real API and map fields in transform.py.
    """
    if not config.USE_API_SOURCE:
        logger.info("API source disabled (USE_API_SOURCE=false) -- skipping")
        return pd.DataFrame()

    url = url or config.API_SOURCE_URL
    logger.info(f"Extracting data from API: {url}")
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        df = pd.DataFrame(data[:limit] if isinstance(data, list) else [data])
        logger.info(f"Extracted {len(df)} rows from API")
        return df
    except requests.RequestException as e:
        logger.error(f"API extraction failed: {e}")
        return pd.DataFrame()
