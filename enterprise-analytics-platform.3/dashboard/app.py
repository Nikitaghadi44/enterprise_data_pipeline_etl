"""
Flask Web Dashboard -- live view over the analytics platform.

Serves:
  GET  /                       -> dashboard UI
  GET  /api/summary            -> KPI summary (headcount, avg cpu, alert counts...)
  GET  /api/employees          -> employee records (+cpu status)
  GET  /api/alerts             -> active alerts
  GET  /api/logs               -> recent system logs
  GET  /api/pipeline-runs      -> ETL run history
  POST /api/run-etl            -> trigger an ETL cycle on demand
  POST /api/run-monitoring     -> trigger a monitoring cycle on demand
  POST /api/alerts/<id>/resolve-> mark an alert resolved

The front-end polls these endpoints every few seconds for a "live" feel
without requiring a websocket server.
"""
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from sqlalchemy import func

from config.config import config
from database.db import get_session, init_db
from database.models import EmployeeRecord, Alert, SystemLog, PipelineRun
from etl.pipeline import run_pipeline
from monitoring.monitor import run_monitoring_cycle
from etl.logger import get_logger

logger = get_logger("dashboard.app")

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/summary")
def api_summary():
    with get_session() as session:
        headcount = session.query(func.count(EmployeeRecord.id)).scalar() or 0
        avg_cpu = session.query(func.avg(EmployeeRecord.cpu_usage)).scalar() or 0
        high_cpu_count = (
            session.query(func.count(EmployeeRecord.id))
            .filter(EmployeeRecord.cpu_status == "High")
            .scalar() or 0
        )
        active_alerts = session.query(func.count(Alert.id)).filter_by(resolved=False).scalar() or 0
        last_run = (
            session.query(PipelineRun)
            .order_by(PipelineRun.started_at.desc())
            .first()
        )
        # Serialize while the session is still open -- to_dict() touches
        # lazy-loaded attributes, which raise DetachedInstanceError once
        # the session (and this `with` block) has closed.
        last_run_dict = last_run.to_dict() if last_run else None

        by_dept_rows = (
            session.query(EmployeeRecord.department, func.count(EmployeeRecord.id), func.avg(EmployeeRecord.cpu_usage))
            .group_by(EmployeeRecord.department)
            .all()
        )
        by_department = [
            {"department": d or "Unknown", "count": c, "avg_cpu": round(a or 0, 1)}
            for d, c, a in by_dept_rows
        ]

    return jsonify({
        "headcount": headcount,
        "avg_cpu_usage": round(avg_cpu, 1),
        "high_cpu_count": high_cpu_count,
        "active_alerts": active_alerts,
        "last_pipeline_run": last_run_dict,
        "by_department": by_department,
        "generated_at": datetime.utcnow().isoformat(),
    })


@app.route("/api/employees")
def api_employees():
    with get_session() as session:
        rows = session.query(EmployeeRecord).order_by(EmployeeRecord.cpu_usage.desc()).all()
        return jsonify([r.to_dict() for r in rows])


@app.route("/api/alerts")
def api_alerts():
    with get_session() as session:
        rows = (
            session.query(Alert)
            .order_by(Alert.triggered_at.desc())
            .limit(100)
            .all()
        )
        return jsonify([r.to_dict() for r in rows])


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def api_resolve_alert(alert_id):
    with get_session() as session:
        alert = session.query(Alert).get(alert_id)
        if not alert:
            return jsonify({"error": "not found"}), 404
        alert.resolved = True
    return jsonify({"ok": True})


@app.route("/api/logs")
def api_logs():
    with get_session() as session:
        rows = (
            session.query(SystemLog)
            .order_by(SystemLog.timestamp.desc())
            .limit(100)
            .all()
        )
        return jsonify([r.to_dict() for r in rows])


@app.route("/api/pipeline-runs")
def api_pipeline_runs():
    with get_session() as session:
        rows = (
            session.query(PipelineRun)
            .order_by(PipelineRun.started_at.desc())
            .limit(20)
            .all()
        )
        return jsonify([r.to_dict() for r in rows])


@app.route("/api/run-etl", methods=["POST"])
def api_run_etl():
    try:
        result = run_pipeline()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Manual ETL trigger failed: {e}")
        return jsonify({"status": "FAILED", "error": str(e)}), 500


@app.route("/api/run-monitoring", methods=["POST"])
def api_run_monitoring():
    try:
        result = run_monitoring_cycle()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Manual monitoring trigger failed: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=True)
