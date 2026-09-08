"""
SQLAlchemy ORM models for the analytics platform.

Domain: employee + infrastructure monitoring (rebuilt from the user's
existing employee/CPU-usage ETL scripts into the advanced platform's
modular structure).

Tables:
    employee_records -> cleaned HR/ops data loaded from CSV/API
                         (salary, department, CPU usage per host/user, etc.)
    system_logs       -> operational log events (for monitoring)
    alerts            -> alerts raised by the monitoring engine
    pipeline_runs     -> ETL run history / audit trail
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Boolean
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class EmployeeRecord(Base):
    __tablename__ = "employee_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100))
    department = Column(String(100), index=True)
    salary = Column(Float)
    salary_after_bonus = Column(Float)
    cpu_usage = Column(Float, index=True)           # % CPU utilization tied to this employee's workstation/host
    cpu_status = Column(String(20), index=True)      # Low / Medium / High
    source = Column(String(20), default="csv")        # csv / api / log
    loaded_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "name": self.name,
            "department": self.department,
            "salary": self.salary,
            "salary_after_bonus": self.salary_after_bonus,
            "cpu_usage": self.cpu_usage,
            "cpu_status": self.cpu_status,
            "source": self.source,
        }


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    service = Column(String(50), index=True)
    level = Column(String(20), index=True)  # INFO / WARNING / ERROR / CRITICAL
    status_code = Column(Integer)
    response_time_ms = Column(Float)
    message = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "service": self.service,
            "level": self.level,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "message": self.message,
        }


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    rule_name = Column(String(100))
    severity = Column(String(20))  # LOW / MEDIUM / HIGH / CRITICAL
    metric_value = Column(Float)
    threshold = Column(Float)
    entity = Column(String(100))     # e.g. employee_id or service name the alert is about
    message = Column(Text)
    resolved = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "entity": self.entity,
            "message": self.message,
            "resolved": self.resolved,
        }


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    status = Column(String(20), default="RUNNING")  # RUNNING / SUCCESS / FAILED
    records_extracted = Column(Integer, default=0)
    records_loaded = Column(Integer, default=0)
    records_rejected = Column(Integer, default=0)
    error_message = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "records_extracted": self.records_extracted,
            "records_loaded": self.records_loaded,
            "records_rejected": self.records_rejected,
            "error_message": self.error_message,
        }
