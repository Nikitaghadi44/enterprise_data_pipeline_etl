"""
Alert dispatch.

Rebuilt from the original alerts.py (which just print()'d high-CPU rows)
into a module that persists alerts to the database and optionally pushes
them to an external channel (e.g. a Slack incoming webhook), so alerts
survive past the console and can drive the live dashboard.
"""
import requests
from database.db import get_session
from database.models import Alert
from etl.logger import get_logger
from config.config import config

logger = get_logger("monitoring.alerts")


def raise_alert(rule_name: str, severity: str, metric_value: float,
                 threshold: float, entity: str, message: str) -> Alert:
    """Persist an alert row and fan it out to configured channels."""
    with get_session() as session:
        alert = Alert(
            rule_name=rule_name,
            severity=severity,
            metric_value=metric_value,
            threshold=threshold,
            entity=entity,
            message=message,
        )
        session.add(alert)
        session.flush()
        alert_id = alert.id

    logger.warning(f"ALERT[{severity}] {rule_name} :: {message}")
    _dispatch_webhook(severity, rule_name, message)
    return alert_id


def _dispatch_webhook(severity: str, rule_name: str, message: str):
    """Push the alert to a Slack-style incoming webhook, if configured."""
    if not config.ALERT_WEBHOOK_URL:
        return
    try:
        payload = {"text": f"[{severity}] {rule_name}: {message}"}
        requests.post(config.ALERT_WEBHOOK_URL, json=payload, timeout=5)
    except requests.RequestException as e:
        logger.error(f"Failed to dispatch alert webhook: {e}")


def get_active_alerts(limit: int = 50):
    """Return the most recent unresolved alerts, newest first."""
    with get_session() as session:
        rows = (
            session.query(Alert)
            .filter_by(resolved=False)
            .order_by(Alert.triggered_at.desc())
            .limit(limit)
            .all()
        )
        return [a.to_dict() for a in rows]


def resolve_alert(alert_id: int) -> bool:
    with get_session() as session:
        alert = session.query(Alert).get(alert_id)
        if not alert:
            return False
        alert.resolved = True
        return True
