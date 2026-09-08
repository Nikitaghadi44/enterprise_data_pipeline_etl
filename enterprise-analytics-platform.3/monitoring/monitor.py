"""
Real-Time Monitoring Engine.

Runs a set of rule checks against the latest data in the database:
  1. High CPU usage per employee (replaces the original generate_alerts
     high_cpu > 85 check, now threshold-driven and persisted)
  2. Elevated error rate in system_logs (ERROR/CRITICAL share of recent logs)
  3. Slow response times in system_logs

Each rule that trips calls monitoring.alerts.raise_alert(). Designed to be
called on a schedule (see scheduler/scheduler.py) or on-demand from the
dashboard's "Run Monitoring Check" action.
"""
from datetime import datetime, timedelta
from sqlalchemy import func

from database.db import get_session
from database.models import EmployeeRecord, SystemLog
from monitoring.alerts import raise_alert
from etl.logger import get_logger
from config.config import config

logger = get_logger("monitoring.engine")


def check_high_cpu_usage() -> list:
    """Rule 1: flag any employee whose CPU usage exceeds the HIGH threshold."""
    triggered = []
    with get_session() as session:
        offenders = (
            session.query(EmployeeRecord)
            .filter(EmployeeRecord.cpu_usage > config.CPU_HIGH_THRESHOLD)
            .all()
        )
        for emp in offenders:
            alert_id = raise_alert(
                rule_name="high_cpu_usage",
                severity="HIGH" if emp.cpu_usage < 95 else "CRITICAL",
                metric_value=emp.cpu_usage,
                threshold=config.CPU_HIGH_THRESHOLD,
                entity=emp.employee_id,
                message=f"{emp.name} ({emp.department}) CPU at {emp.cpu_usage:.1f}% "
                        f"(threshold {config.CPU_HIGH_THRESHOLD:.0f}%)",
            )
            triggered.append(alert_id)
    if triggered:
        logger.warning(f"High-CPU rule triggered {len(triggered)} alert(s)")
    return triggered


def check_error_rate(window_minutes: int = 60) -> list:
    """Rule 2: flag if ERROR/CRITICAL logs exceed the configured % of recent volume."""
    triggered = []
    since = datetime.utcnow() - timedelta(minutes=window_minutes)
    with get_session() as session:
        total = session.query(func.count(SystemLog.id)).filter(SystemLog.timestamp >= since).scalar() or 0
        errors = (
            session.query(func.count(SystemLog.id))
            .filter(SystemLog.timestamp >= since, SystemLog.level.in_(["ERROR", "CRITICAL"]))
            .scalar() or 0
        )
        if total == 0:
            return triggered

        error_rate_pct = (errors / total) * 100
        if error_rate_pct > config.ERROR_RATE_THRESHOLD_PCT:
            alert_id = raise_alert(
                rule_name="elevated_error_rate",
                severity="HIGH" if error_rate_pct < 25 else "CRITICAL",
                metric_value=round(error_rate_pct, 2),
                threshold=config.ERROR_RATE_THRESHOLD_PCT,
                entity="system_logs",
                message=f"Error rate {error_rate_pct:.1f}% over last {window_minutes}m "
                        f"({errors}/{total} log lines)",
            )
            triggered.append(alert_id)
    if triggered:
        logger.warning(f"Error-rate rule triggered {len(triggered)} alert(s)")
    return triggered


def check_response_times(window_minutes: int = 60) -> list:
    """Rule 3: flag if average response time exceeds the configured threshold."""
    triggered = []
    since = datetime.utcnow() - timedelta(minutes=window_minutes)
    with get_session() as session:
        avg_ms = (
            session.query(func.avg(SystemLog.response_time_ms))
            .filter(SystemLog.timestamp >= since, SystemLog.response_time_ms.isnot(None))
            .scalar()
        )
        if avg_ms is None:
            return triggered

        if avg_ms > config.RESPONSE_TIME_THRESHOLD_MS:
            alert_id = raise_alert(
                rule_name="slow_response_time",
                severity="MEDIUM" if avg_ms < 2000 else "HIGH",
                metric_value=round(avg_ms, 1),
                threshold=config.RESPONSE_TIME_THRESHOLD_MS,
                entity="system_logs",
                message=f"Avg response time {avg_ms:.0f}ms over last {window_minutes}m "
                        f"(threshold {config.RESPONSE_TIME_THRESHOLD_MS:.0f}ms)",
            )
            triggered.append(alert_id)
    if triggered:
        logger.warning(f"Response-time rule triggered {len(triggered)} alert(s)")
    return triggered


def run_monitoring_cycle() -> dict:
    """Run all monitoring rules once. Called by the scheduler and the dashboard."""
    logger.info("Running monitoring cycle")
    result = {
        "high_cpu_alerts": check_high_cpu_usage(),
        "error_rate_alerts": check_error_rate(),
        "response_time_alerts": check_response_times(),
        "checked_at": datetime.utcnow().isoformat(),
    }
    total = sum(len(v) for v in result.values() if isinstance(v, list))
    logger.info(f"Monitoring cycle complete: {total} new alert(s)")
    return result


if __name__ == "__main__":
    print(run_monitoring_cycle())
