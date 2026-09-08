# Enterprise Data Analytics & Real-Time Monitoring Platform

A modular, production-style data platform:

```
CSV / Logs / API  -->  Python ETL (extract/transform/load, logging)
                  -->  SQLAlchemy ORM  -->  MySQL (or SQLite for local dev)
                  -->  Real-Time Monitoring Engine (rule-based alerts)
                  -->  Flask Web Dashboard (live, auto-refreshing)
                  -->  Excel Reports (Power BI-ready export)
                  -->  Docker + APScheduler (unattended automation)
```

Domain: employee + infrastructure monitoring (headcount, salary, per-employee
CPU utilization, system logs, alerts).

## Why it's structured this way

This project was rebuilt from an earlier, simpler ETL script set
(`etl_pipeline.py` / `utils.py` / `alerts.py` / `db_connection.py`) into a
layered architecture:

| Old file | Became |
|---|---|
| `utils.py: clean_data/transform_data/validate_data` | `etl/transform.py` — now splits rows into **clean vs. rejected** instead of `fillna(0)` silently hiding bad data |
| `etl_pipeline.py` | `etl/pipeline.py` — orchestrates extract→transform→load and writes an audit row to `pipeline_runs` |
| `alerts.py` (just `print()`ed) | `monitoring/alerts.py` + `monitoring/monitor.py` — alerts are persisted to the DB, severity-graded, and optionally pushed to a webhook |
| `db_connection.py` | `database/db.py` — session-managed engine, SQLite by default, MySQL via one env var |
| `run_sql.py` (hardcoded password!) | `database/run_sql.py` — credentials now come only from `.env`, never source |
| `logger_config.py` | `etl/logger.py` — shared rotating-file logger used by every module |

**⚠️ Security note:** the original `run_sql.py` had a real-looking MySQL
password committed directly in the connection string. That pattern is gone
here — every credential is read from `config/config.py`, which loads `.env`
(git-ignored). Never commit `.env`.

## Quick start (SQLite, zero setup)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # defaults already point at SQLite

python main.py etl        # extract -> transform -> load
python main.py monitor    # run alert rules against loaded data
python main.py report     # generate an Excel workbook in exports/
python main.py dashboard  # http://localhost:5000
```

Or run everything once:
```bash
python main.py all
```

Run the test suite:
```bash
pip install pytest
pytest tests/ -v
```

## Run with MySQL + Docker (production-style)

```bash
cp .env.example .env
# edit .env: set DB_PASSWORD to something real

docker compose up --build
```

This starts three containers:
- **mysql** — the database
- **dashboard** — Flask app on port 5000
- **scheduler** — runs ETL every `ETL_INTERVAL_MINUTES`, monitoring on the
  same cadence, and an Excel report every `REPORT_INTERVAL_HOURS`

## Project layout

```
config/config.py        Central settings (env-driven, SQLite or MySQL)
etl/
  extract.py             CSV / log / API extractors
  transform.py            Cleaning, validation, enrichment (clean vs rejected)
  load.py                 Upsert into MySQL/SQLite via SQLAlchemy sessions
  pipeline.py              Orchestrator + pipeline_runs audit trail
  logger.py                Shared rotating-file logger
database/
  models.py                ORM models: EmployeeRecord, SystemLog, Alert, PipelineRun
  db.py                     Engine + session factory
  run_sql.py                Runs sql/queries.sql for ad-hoc analysis
monitoring/
  monitor.py                Rule engine: high CPU, error rate, slow responses
  alerts.py                 Persists alerts + optional webhook dispatch
dashboard/
  app.py                    Flask app + REST API for the live dashboard
  templates/index.html      Dashboard UI (KPIs, charts, tables)
  static/                   CSS + polling JS (auto-refresh every 5s)
reports/
  excel_report.py           Multi-sheet formatted .xlsx export
scheduler/
  scheduler.py               APScheduler jobs (ETL / monitoring / reports)
sql/queries.sql               Ad-hoc analysis queries
tests/test_etl.py              Unit tests for the transform layer
main.py                        CLI entrypoint (etl/monitor/report/dashboard/schedule/all)
Dockerfile / docker-compose.yml
```

## Monitoring rules (tunable via `.env`)

| Rule | Trigger | Severity |
|---|---|---|
| High CPU usage | employee `cpu_usage` > `CPU_HIGH_THRESHOLD` (85%) | HIGH / CRITICAL above 95% |
| Elevated error rate | ERROR+CRITICAL logs > `ERROR_RATE_THRESHOLD_PCT` (5%) of last hour | HIGH / CRITICAL above 25% |
| Slow response time | avg `response_time_ms` > `RESPONSE_TIME_THRESHOLD_MS` (800ms) | MEDIUM / HIGH above 2000ms |

## Power BI

Point Power BI's MySQL connector at the same database (`DB_HOST`/`DB_NAME`
from `.env`), or import the generated Excel workbook from `exports/`
directly — both `Employees` and `Department Summary` sheets are shaped for
that.

## Extending it

- **New data source**: add one function to `etl/extract.py`, wire it into
  `etl/pipeline.py::run_pipeline()`.
- **New alert rule**: add a `check_*()` function to `monitoring/monitor.py`
  and call it from `run_monitoring_cycle()`.
- **New KPI on the dashboard**: add a query to `dashboard/app.py::api_summary()`
  and render it in `dashboard/templates/index.html`.
