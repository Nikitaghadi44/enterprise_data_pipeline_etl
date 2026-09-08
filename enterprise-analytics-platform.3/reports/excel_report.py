"""
Excel Reports.

Exports the current employee/CPU dataset, active alerts, and pipeline run
history into a single formatted .xlsx workbook -- the artifact that would
typically feed a Power BI import or get emailed to stakeholders.
"""
from datetime import datetime
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from database.db import get_session
from database.models import EmployeeRecord, Alert, PipelineRun
from etl.logger import get_logger
from config.config import config

logger = get_logger("reports.excel")

HEADER_FILL = PatternFill(start_color="1F2A44", end_color="1F2A44", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)


def _style_sheet(ws, df: pd.DataFrame):
    for col_idx, col_name in enumerate(df.columns, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
        max_len = max(len(str(col_name)), df[col_name].map(lambda x: len(str(x))).max() if len(df) else 0)
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 45)
    ws.freeze_panes = "A2"


def generate_excel_report(output_path=None) -> str:
    """Build the workbook and return the path it was written to."""
    output_path = output_path or (config.EXPORT_DIR / f"analytics_report_{datetime.now():%Y%m%d_%H%M%S}.xlsx")

    with get_session() as session:
        employees = pd.DataFrame([e.to_dict() for e in session.query(EmployeeRecord).all()])
        alerts = pd.DataFrame([a.to_dict() for a in session.query(Alert).order_by(Alert.triggered_at.desc()).all()])
        runs = pd.DataFrame([r.to_dict() for r in session.query(PipelineRun).order_by(PipelineRun.started_at.desc()).all()])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        if not employees.empty:
            employees.drop(columns=["id"], errors="ignore").to_excel(writer, sheet_name="Employees", index=False)
        else:
            pd.DataFrame([{"note": "No employee data loaded yet"}]).to_excel(writer, sheet_name="Employees", index=False)

        if not employees.empty:
            dept_summary = (
                employees.groupby("department")
                .agg(headcount=("employee_id", "count"), avg_cpu_usage=("cpu_usage", "mean"), avg_salary=("salary", "mean"))
                .round(1)
                .reset_index()
            )
            dept_summary.to_excel(writer, sheet_name="Department Summary", index=False)

        if not alerts.empty:
            alerts.drop(columns=["id"], errors="ignore").to_excel(writer, sheet_name="Alerts", index=False)
        else:
            pd.DataFrame([{"note": "No alerts raised yet"}]).to_excel(writer, sheet_name="Alerts", index=False)

        if not runs.empty:
            runs.drop(columns=["id"], errors="ignore").to_excel(writer, sheet_name="Pipeline Runs", index=False)

        # Apply header styling to every sheet
        for sheet_name, df in (
            ("Employees", employees), ("Alerts", alerts), ("Pipeline Runs", runs)
        ):
            if sheet_name in writer.sheets and not df.empty:
                _style_sheet(writer.sheets[sheet_name], df.drop(columns=["id"], errors="ignore"))

    logger.info(f"Excel report written to {output_path}")
    return str(output_path)


if __name__ == "__main__":
    print(generate_excel_report())
