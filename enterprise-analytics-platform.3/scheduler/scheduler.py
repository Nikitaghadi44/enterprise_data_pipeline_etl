"""
Automation layer: runs the ETL pipeline, monitoring engine, and Excel
report generation on a recurring schedule using APScheduler -- this is
what the Docker container's "scheduler" service runs.
"""
import time
from apscheduler.schedulers.background import BackgroundScheduler

from etl.pipeline import run_pipeline
from monitoring.monitor import run_monitoring_cycle
from reports.excel_report import generate_excel_report
from etl.logger import get_logger
from config.config import config

logger = get_logger("scheduler")


def scheduled_etl_job():
    try:
        result = run_pipeline()
        logger.info(f"[scheduled] ETL run finished: {result['status']}")
    except Exception as e:
        logger.error(f"[scheduled] ETL run failed: {e}")


def scheduled_monitoring_job():
    try:
        result = run_monitoring_cycle()
        logger.info(f"[scheduled] Monitoring cycle finished: {result}")
    except Exception as e:
        logger.error(f"[scheduled] Monitoring cycle failed: {e}")


def scheduled_report_job():
    try:
        path = generate_excel_report()
        logger.info(f"[scheduled] Excel report generated: {path}")
    except Exception as e:
        logger.error(f"[scheduled] Excel report generation failed: {e}")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(scheduled_etl_job, "interval", minutes=config.ETL_INTERVAL_MINUTES, id="etl_job", next_run_time=None)
    scheduler.add_job(scheduled_monitoring_job, "interval", minutes=config.ETL_INTERVAL_MINUTES, id="monitor_job")
    scheduler.add_job(scheduled_report_job, "interval", hours=config.REPORT_INTERVAL_HOURS, id="report_job")
    scheduler.start()
    logger.info(
        f"Scheduler started: ETL every {config.ETL_INTERVAL_MINUTES}m, "
        f"monitoring every {config.ETL_INTERVAL_MINUTES}m, "
        f"reports every {config.REPORT_INTERVAL_HOURS}h"
    )
    return scheduler


if __name__ == "__main__":
    # Run once immediately, then start the recurring schedule
    scheduled_etl_job()
    scheduled_monitoring_job()
    scheduled_report_job()

    sched = start_scheduler()
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler shutting down")
        sched.shutdown()
