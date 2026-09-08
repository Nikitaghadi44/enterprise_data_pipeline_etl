-- Ad-hoc analysis queries for the employee_records / alerts / system_logs schema.
-- Run via `python database/run_sql.py` (reads DB credentials from config/.env,
-- never hardcoded -- see the fix note in README.md).

-- 1. Headcount and average CPU usage by department
SELECT department,
       COUNT(*)              AS headcount,
       ROUND(AVG(cpu_usage), 1) AS avg_cpu_usage,
       ROUND(AVG(salary), 0)    AS avg_salary
FROM employee_records
GROUP BY department
ORDER BY avg_cpu_usage DESC;

-- 2. Employees currently in the High CPU band
SELECT employee_id, name, department, cpu_usage
FROM employee_records
WHERE cpu_status = 'High'
ORDER BY cpu_usage DESC;

-- 3. Unresolved alerts by severity
SELECT severity, COUNT(*) AS alert_count
FROM alerts
WHERE resolved = 0
GROUP BY severity
ORDER BY alert_count DESC;

-- 4. Error rate in system logs over the last run
SELECT level, COUNT(*) AS log_count
FROM system_logs
GROUP BY level
ORDER BY log_count DESC;

-- 5. Pipeline run reliability
SELECT status, COUNT(*) AS run_count
FROM pipeline_runs
GROUP BY status;
