"""
Single CLI entrypoint for the platform.

Usage:
    python main.py etl              # run one ETL cycle
    python main.py monitor          # run one monitoring cycle
    python main.py report           # generate an Excel report
    python main.py dashboard        # start the Flask dashboard
    python main.py schedule         # start ETL + monitoring + report scheduler
    python main.py all              # run etl -> monitor -> report once, then exit
"""
import sys

from etl.pipeline import run_pipeline
from monitoring.monitor import run_monitoring_cycle
from reports.excel_report import generate_excel_report
from etl.logger import get_logger

logger = get_logger("main")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "etl":
        print(run_pipeline())

    elif command == "monitor":
        print(run_monitoring_cycle())

    elif command == "report":
        print("Report written to:", generate_excel_report())

    elif command == "dashboard":
        from dashboard.app import app
        from config.config import config
        app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=True)

    elif command == "schedule":
        from scheduler.scheduler import start_scheduler
        import time
        start_scheduler()
        logger.info("Scheduler running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(2)
        except KeyboardInterrupt:
            logger.info("Stopped.")

    elif command == "all":
        print("ETL:", run_pipeline())
        print("Monitoring:", run_monitoring_cycle())
        print("Report:", generate_excel_report())

    else:
        print(f"Unknown command: {command}\n")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
