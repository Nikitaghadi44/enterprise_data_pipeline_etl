"""
Central configuration for the Enterprise Data Analytics & Real-Time
Monitoring Platform.

All values are overridable via environment variables (see .env.example).
Defaults to a local SQLite file so the whole platform runs out-of-the-box
with zero external infra. Point DB_ENGINE / DB_* at MySQL for production.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    # ---- Database ---------------------------------------------------
    DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")  # "sqlite" or "mysql"

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "analytics_platform")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    SQLITE_PATH = BASE_DIR / "data" / "analytics_platform.db"

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        if self.DB_ENGINE == "mysql":
            return (
                f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return f"sqlite:///{self.SQLITE_PATH}"

    # ---- ETL ----------------------------------------------------------
    DATA_DIR = BASE_DIR / "data"
    LOG_DIR = BASE_DIR / "logs"
    EXPORT_DIR = BASE_DIR / "exports"

    CSV_SOURCE_PATH = DATA_DIR / "sample_employees.csv"
    LOG_SOURCE_PATH = DATA_DIR / "sample_logs.csv"
    API_SOURCE_URL = os.getenv("API_SOURCE_URL", "https://jsonplaceholder.typicode.com/todos")
    USE_API_SOURCE = os.getenv("USE_API_SOURCE", "false").lower() == "true"

    # ---- Monitoring / Alerts ------------------------------------------
    ERROR_RATE_THRESHOLD_PCT = float(os.getenv("ERROR_RATE_THRESHOLD_PCT", 5.0))
    RESPONSE_TIME_THRESHOLD_MS = float(os.getenv("RESPONSE_TIME_THRESHOLD_MS", 800))
    CPU_HIGH_THRESHOLD = float(os.getenv("CPU_HIGH_THRESHOLD", 85.0))   # % -> HIGH severity alert
    CPU_MEDIUM_THRESHOLD = float(os.getenv("CPU_MEDIUM_THRESHOLD", 50.0))  # % -> Medium status band
    ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")  # e.g. Slack incoming webhook
    ALERT_EMAIL_ENABLED = os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"

    # ---- Scheduler ------------------------------------------------------
    ETL_INTERVAL_MINUTES = int(os.getenv("ETL_INTERVAL_MINUTES", 5))
    REPORT_INTERVAL_HOURS = int(os.getenv("REPORT_INTERVAL_HOURS", 24))

    # ---- Flask / Dashboard -----------------------------------------------
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")


config = Config()

# Ensure runtime directories exist
for d in (config.DATA_DIR, config.LOG_DIR, config.EXPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)
