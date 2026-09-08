const POLL_MS = 5000;
let deptChart = null;

function fmtTime(iso) {
  if (!iso) return "--";
  const d = new Date(iso);
  return d.toLocaleTimeString();
}

function badge(cls, text) {
  return `<span class="badge badge-${cls}">${text}</span>`;
}

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

async function refreshSummary() {
  const s = await fetchJSON("/api/summary");
  document.getElementById("kpiHeadcount").textContent = s.headcount;
  document.getElementById("kpiAvgCpu").textContent = s.avg_cpu_usage + "%";
  document.getElementById("kpiHighCpu").textContent = s.high_cpu_count;
  document.getElementById("kpiAlerts").textContent = s.active_alerts;
  document.getElementById("kpiLastRun").textContent = s.last_pipeline_run
    ? `${s.last_pipeline_run.status} @ ${fmtTime(s.last_pipeline_run.started_at)}`
    : "No runs yet";
  document.getElementById("lastUpdated").textContent = "Updated " + fmtTime(s.generated_at);

  const labels = s.by_department.map(d => d.department);
  const data = s.by_department.map(d => d.avg_cpu);
  if (!deptChart) {
    const ctx = document.getElementById("deptChart").getContext("2d");
    deptChart = new Chart(ctx, {
      type: "bar",
      data: { labels, datasets: [{ label: "Avg CPU %", data, backgroundColor: "#4f8cff" }] },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true, max: 100, ticks: { color: "#8b93a7" } }, x: { ticks: { color: "#8b93a7" } } },
        plugins: { legend: { display: false } },
      },
    });
  } else {
    deptChart.data.labels = labels;
    deptChart.data.datasets[0].data = data;
    deptChart.update();
  }
}

async function refreshEmployees() {
  const rows = await fetchJSON("/api/employees");
  const tbody = document.querySelector("#employeeTable tbody");
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.employee_id}</td>
      <td>${r.name ?? ""}</td>
      <td>${r.department ?? ""}</td>
      <td>${r.salary != null ? r.salary.toLocaleString() : ""}</td>
      <td>${r.cpu_usage != null ? r.cpu_usage.toFixed(1) : ""}</td>
      <td>${badge(r.cpu_status, r.cpu_status ?? "")}</td>
    </tr>`).join("");
}

async function refreshAlerts() {
  const rows = (await fetchJSON("/api/alerts")).filter(a => !a.resolved);
  document.getElementById("kpiAlerts").textContent = rows.length;
  const tbody = document.querySelector("#alertsTable tbody");
  tbody.innerHTML = rows.map(a => `
    <tr>
      <td>${fmtTime(a.triggered_at)}</td>
      <td>${badge(a.severity, a.severity)}</td>
      <td>${a.rule_name}</td>
      <td>${a.message}</td>
      <td><button class="resolve-btn" onclick="resolveAlert(${a.id})">Resolve</button></td>
    </tr>`).join("");
}

async function resolveAlert(id) {
  await fetchJSON(`/api/alerts/${id}/resolve`, { method: "POST" });
  refreshAlerts();
}
window.resolveAlert = resolveAlert;

async function refreshLogs() {
  const rows = await fetchJSON("/api/logs");
  const tbody = document.querySelector("#logsTable tbody");
  tbody.innerHTML = rows.map(l => `
    <tr>
      <td>${fmtTime(l.timestamp)}</td>
      <td>${l.service ?? ""}</td>
      <td>${badge(l.level, l.level ?? "")}</td>
      <td>${l.status_code ?? ""}</td>
      <td>${l.response_time_ms != null ? l.response_time_ms.toFixed(0) : ""}</td>
    </tr>`).join("");
}

async function refreshRuns() {
  const rows = await fetchJSON("/api/pipeline-runs");
  const tbody = document.querySelector("#runsTable tbody");
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${fmtTime(r.started_at)}</td>
      <td>${badge(r.status === "SUCCESS" ? "Low" : r.status === "FAILED" ? "High" : "Medium", r.status)}</td>
      <td>${r.records_extracted}</td>
      <td>${r.records_loaded}</td>
      <td>${r.records_rejected}</td>
    </tr>`).join("");
}

async function refreshAll() {
  try {
    await Promise.all([refreshSummary(), refreshEmployees(), refreshAlerts(), refreshLogs(), refreshRuns()]);
  } catch (e) {
    console.error("Refresh failed:", e);
  }
}

document.getElementById("runEtlBtn").addEventListener("click", async (e) => {
  e.target.disabled = true;
  e.target.textContent = "Running...";
  try {
    await fetchJSON("/api/run-etl", { method: "POST" });
    await refreshAll();
  } catch (err) {
    alert("ETL run failed: " + err.message);
  } finally {
    e.target.disabled = false;
    e.target.textContent = "▶ Run ETL";
  }
});

document.getElementById("runMonitorBtn").addEventListener("click", async (e) => {
  e.target.disabled = true;
  e.target.textContent = "Checking...";
  try {
    await fetchJSON("/api/run-monitoring", { method: "POST" });
    await refreshAll();
  } catch (err) {
    alert("Monitoring run failed: " + err.message);
  } finally {
    e.target.disabled = false;
    e.target.textContent = "🔍 Run Monitoring";
  }
});

refreshAll();
setInterval(refreshAll, POLL_MS);
