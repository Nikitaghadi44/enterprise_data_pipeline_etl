"""
Basic unit tests for the ETL transform layer -- run with:
    pytest tests/test_etl.py -v
"""
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl.transform import transform_employees, transform_logs


def _sample_employee_df():
    return pd.DataFrame([
        {"employee_id": "E1", "name": "Alice", "department": "engineering", "salary": 90000, "cpu_usage": 92},
        {"employee_id": "E2", "name": "Bob", "department": "sales", "salary": 60000, "cpu_usage": 40},
        {"employee_id": "E3", "name": "Carol", "department": "sales", "salary": -1, "cpu_usage": 30},   # invalid salary
        {"employee_id": None, "name": "NoId", "department": "sales", "salary": 50000, "cpu_usage": 20}, # invalid id
        {"employee_id": "E1", "name": "Alice", "department": "engineering", "salary": 90000, "cpu_usage": 92},  # dup
    ])


def test_transform_employees_splits_valid_and_invalid():
    clean, rejected = transform_employees(_sample_employee_df())
    assert len(clean) == 2  # E1 (deduped) + E2
    assert len(rejected) == 2  # bad salary + missing id


def test_transform_employees_cpu_status_bands():
    clean, _ = transform_employees(_sample_employee_df())
    e1 = clean[clean["employee_id"] == "E1"].iloc[0]
    e2 = clean[clean["employee_id"] == "E2"].iloc[0]
    assert e1["cpu_status"] == "High"     # 92% > 85 threshold
    assert e2["cpu_status"] == "Low"      # 40% < 50 threshold


def test_transform_employees_salary_after_bonus():
    clean, _ = transform_employees(_sample_employee_df())
    e2 = clean[clean["employee_id"] == "E2"].iloc[0]
    assert round(e2["salary_after_bonus"], 2) == 66000.0  # 60000 * 1.1


def test_transform_employees_empty_input():
    clean, rejected = transform_employees(pd.DataFrame())
    assert clean.empty and rejected.empty


def test_transform_logs_drops_bad_timestamps():
    df = pd.DataFrame([
        {"timestamp": "2026-08-08 09:00:00", "service": "api", "level": "info", "status_code": 200, "response_time_ms": 100},
        {"timestamp": "not-a-date", "service": "api", "level": "error", "status_code": 500, "response_time_ms": 900},
    ])
    result = transform_logs(df)
    assert len(result) == 1
    assert result.iloc[0]["level"] == "INFO"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
