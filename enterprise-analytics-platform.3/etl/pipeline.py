"""
Pipeline orchestrator.

Ties extract -> transform -> load together for each source, records an
audit trail row in pipeline_runs, and returns a summary dict that the
scheduler / CLI / dashboard can all consume.
"""
from datetime import datetime

from database.db import get_session, init_db
from database.models import PipelineRun
from etl.extract import extract_csv_employees, extract_logs, extract_api
from etl.transform import transform_employees, transform_logs
from etl.load import load_employees, load_logs
from etl.logger import get_logger

logger = get_logger("etl.pipeline")


def run_pipeline() -> dict:
    """Run one full ETL cycle across all configured sources."""
    init_db()
    logger.info("=" * 60)
    logger.info("ETL Pipeline started")

    run_id = None
    with get_session() as session:
        run = PipelineRun(started_at=datetime.utcnow(), status="RUNNING")
        session.add(run)
        session.flush()
        run_id = run.id

    summary = {
        "run_id": run_id,
        "started_at": datetime.utcnow().isoformat(),
        "employees_extracted": 0,
        "employees_loaded": 0,
        "employees_rejected": 0,
        "logs_extracted": 0,
        "logs_loaded": 0,
        "status": "RUNNING",
        "error": None,
    }

    try:
        # ---- Employees (CSV + optional API) ---------------------------
        raw_employees = extract_csv_employees()
        raw_api = extract_api()
        if not raw_api.empty:
            logger.info("API source returned data but requires custom field "
                        "mapping before merging with employee schema -- skipping merge")

        clean_emp, rejected_emp = transform_employees(raw_employees)
        loaded_emp = load_employees(clean_emp)

        summary["employees_extracted"] = len(raw_employees)
        summary["employees_loaded"] = loaded_emp
        summary["employees_rejected"] = len(rejected_emp)

        # ---- System logs ------------------------------------------------
        raw_logs = extract_logs()
        clean_logs = transform_logs(raw_logs)
        loaded_logs = load_logs(clean_logs)

        summary["logs_extracted"] = len(raw_logs)
        summary["logs_loaded"] = loaded_logs

        summary["status"] = "SUCCESS"
        logger.info(f"ETL Pipeline completed successfully: {summary}")

    except Exception as e:
        summary["status"] = "FAILED"
        summary["error"] = str(e)
        logger.error(f"ETL Pipeline failed: {e}")
        raise

    finally:
        with get_session() as session:
            run = session.query(PipelineRun).get(run_id)
            if run:
                run.finished_at = datetime.utcnow()
                run.status = summary["status"]
                run.records_extracted = summary["employees_extracted"] + summary["logs_extracted"]
                run.records_loaded = summary["employees_loaded"] + summary["logs_loaded"]
                run.records_rejected = summary["employees_rejected"]
                run.error_message = summary["error"]

    return summary


if __name__ == "__main__":
    result = run_pipeline()
    print("ETL Pipeline Completed:", result)
