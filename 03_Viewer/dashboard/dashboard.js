// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

/** @type {HTMLIFrameElement} */
let viewerIframe;

/** @type {Array} */
let clashData = [];

/** @type {Array} */
let modelFiles = [];

async function initDashboard() {
  viewerIframe = document.getElementById("bim-viewer");
  document.getElementById("pnt-file-input").addEventListener("change", onPNTFileSelected);

  // Auto-load if the server already has a .pnt pre-extracted (e.g., pnt_server.py project.pnt)
  try {
    const resp = await fetch("/data/clashes.json");
    if (resp.ok) {
      const data = await resp.json();
      document.getElementById("reload-btn").style.display = "";
      loadProjectData(data);
      return;
    }
  } catch (_) {}

  showFilePicker();
}

function showFilePicker() {
  document.getElementById("file-picker-overlay").style.display = "flex";
  document.getElementById("reload-btn").style.display = "none";
}

function hideFilePicker() {
  document.getElementById("file-picker-overlay").style.display = "none";
  document.getElementById("reload-btn").style.display = "";
}

async function onPickPNT() {
  if (window.pywebview) {
    const path = await window.pywebview.api.open_pnt_dialog();
    if (!path) return;
    setPickerStatus("Loading package…");
    const data = await window.pywebview.api.load_pnt(path);
    if (!data) {
      setPickerStatus("Could not load the package.");
      return;
    }
    hideFilePicker();
    loadProjectData(data);
  } else {
    document.getElementById("pnt-file-input").click();
  }
}

function setPickerStatus(msg) {
  const el = document.getElementById("file-picker-status");
  if (el) el.textContent = msg;
}

async function onPNTFileSelected(event) {
  const file = event.target.files[0];
  if (!file) return;
  setPickerStatus("Uploading package…");
  const form = new FormData();
  form.append("file", file);
  let data;
  try {
    const resp = await fetch("/api/upload-pnt", { method: "POST", body: form });
    if (!resp.ok) throw new Error("Upload failed");
    data = await resp.json();
  } catch (e) {
    setPickerStatus("Upload failed. Please try again.");
    console.error("[Dashboard] PNT upload error:", e);
    return;
  }
  event.target.value = "";
  hideFilePicker();
  loadProjectData(data);
}

function loadProjectData(data) {
  clashData = data.clashes || [];
  modelFiles = data.models || [];

  renderCards(clashData);
  renderCoverage(data.classification || [], clashData);
  renderClashTable(clashData);

  document.getElementById("subtitle").textContent =
    `${data.project || "Project"} — ${clashData.length} clashes | ${countTests(clashData)} active tests | ${modelFiles.length} federated models`;

  const modelNames = modelFiles.map((m) => m.fileName).join(",");
  viewerIframe.src = `/viewer/?models=${encodeURIComponent(modelNames)}`;
}

function countTests(clashes) {
  return new Set(clashes.map((c) => c.Test)).size;
}

function loadModelsInViewer() {
  const viewer = viewerIframe.contentWindow;
  if (!viewer) return;

  for (const model of modelFiles) {
    const url = `/models/${model.fileName}`;
    // Use postMessage for iframe communication
    viewerIframe.contentWindow.postMessage(
      { type: "viewer-command", action: "loadModel", payload: { url, name: model.name } },
      "*"
    );
  }
}

function renderCards(clashes) {
  const container = document.getElementById("cards");

  const count = (status) => clashes.filter((c) => c.Status === status).length;
  const nNew      = count("New");
  const nActive   = count("Active");
  const nReviewed = count("Reviewed");
  const nApproved = count("Approved");
  const nResolved = count("Resolved");

  const cards = [
    { title: "New",        value: nNew,                    cls: "card-c5" },
    { title: "Active",     value: nActive,                 cls: "card-c4" },
    { title: "Reviewed",   value: nReviewed,               cls: "card-c2" },
    { title: "Approved",   value: nApproved,               cls: "card-c3" },
    { title: "Resolved",   value: nResolved,               cls: "card-c6" },
    { title: "To Resolve", value: nNew + nActive + nReviewed, cls: "card-c1" },
  ];

  container.innerHTML = cards
    .map(
      (c) => `
    <div class="card ${c.cls}">
      <div class="card-title">${c.title}</div>
      <div class="card-value">${c.value}</div>
    </div>
  `
    )
    .join("");
}

const STATUS_COLORS = {
  New:      "#ef4444",
  Active:   "#f97316",
  Reviewed: "#3b82f6",
  Approved: "#22c55e",
  Resolved: "#eab308",
};

const CODE_PALETTE = [
  "#6366f1","#3b82f6","#22c55e","#f97316",
  "#ef4444","#eab308","#8b5cf6","#06b6d4","#ec4899","#14b8a6",
];

let _barChart   = null;
let _donutChart = null;

function renderCoverage(classification, clashes) {
  if (!classification || !classification.length) return;
  document.getElementById("coverage-section").style.display = "";

  // — Coverage table —
  const tbody = document.getElementById("coverage-tbody");
  tbody.innerHTML = classification.map((m) => {
    const pct   = m.coverage_pct ?? 0;
    const color = pct >= 90 ? "#22c55e" : pct >= 60 ? "#f97316" : "#ef4444";
    const warn  = m.unclassified_type_count
      ? `<span style="color:#ef4444;font-size:0.7rem;margin-left:6px">${m.unclassified_type_count} sin clasificar</span>`
      : "";
    return `
      <tr>
        <td>${m.model}${warn}</td>
        <td style="text-align:right">${m.total_geometry_elements}</td>
        <td style="padding-right:12px">
          <div class="bar-track">
            <div style="background:${color};width:${pct}%;height:8px;border-radius:4px;transition:width 0.4s"></div>
          </div>
        </td>
        <td style="text-align:right;color:${color};font-weight:600;font-size:0.82rem">${pct}%</td>
      </tr>`;
  }).join("");

  // — Charts —
  renderDisciplineBar(clashes);
  renderCodeDonut(classification);
}

function renderDisciplineBar(clashes) {
  // One bar per test, stacked by status — only tests with results
  const map = {};
  clashes.forEach((c) => {
    const test = c.Test || "Unknown";
    if (!map[test]) map[test] = {};
    map[test][c.Status] = (map[test][c.Status] || 0) + 1;
  });

  const tests    = Object.keys(map).sort();
  const borderCol = document.body.classList.contains("light-mode") ? "#ffffff" : "#1e293b";

  const datasets = Object.entries(STATUS_COLORS)
    .filter(([s]) => tests.some((t) => map[t][s]))
    .map(([s, color]) => ({
      label:           s,
      data:            tests.map((t) => map[t][s] || 0),
      backgroundColor: color,
      borderColor:     borderCol,
      borderWidth:     1,
      borderRadius:    2,
    }));

  if (_barChart) _barChart.destroy();
  _barChart = new Chart(
    document.getElementById("chart-discipline-bar").getContext("2d"),
    {
      type: "bar",
      data: { labels: tests, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: "#94a3b8", boxWidth: 12, font: { size: 11 } } },
        },
        scales: {
          x: {
            stacked: true,
            ticks:   { color: "#94a3b8", font: { size: 10 }, maxRotation: 35 },
            grid:    { color: "#1e293b" },
          },
          y: {
            stacked: true,
            ticks:   { color: "#94a3b8", precision: 0 },
            grid:    { color: "#334155" },
          },
        },
      },
    }
  );
}

function _disciplineLabel(modelName) {
  const n = modelName.toUpperCase();
  if (n.includes("ARQ")) return "Architecture";
  if (n.includes("EST") || n.includes("STR")) return "Structure";
  if (n.includes("INS") || n.includes("MEP")) return "MEP";
  return modelName;
}

const DISCIPLINE_COLORS = ["#3b82f6", "#f97316", "#22c55e", "#8b5cf6", "#06b6d4"];

function renderCodeDonut(classification) {
  // One slice per model, sized by total geometry elements
  const labels = classification.map((m) => _disciplineLabel(m.model));
  const values = classification.map((m) => m.total_geometry_elements);
  const colors = classification.map((_, i) => DISCIPLINE_COLORS[i % DISCIPLINE_COLORS.length]);

  const borderCol = document.body.classList.contains("light-mode") ? "#ffffff" : "#1e293b";

  if (_donutChart) _donutChart.destroy();
  _donutChart = new Chart(
    document.getElementById("chart-code-donut").getContext("2d"),
    {
      type: "doughnut",
      data: {
        labels,
        datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: borderCol }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "58%",
        plugins: {
          legend: {
            position: "right",
            labels:   { color: "#94a3b8", boxWidth: 12, font: { size: 11 }, padding: 10 },
          },
        },
      },
    }
  );
}

function statusBadge(status) {
  if (!status) return "";
  const map = { New: "badge-new", Active: "badge-active", Reviewed: "badge-reviewed", Approved: "badge-approved" };
  const cls = map[status] || "badge-default";
  return `<span class="badge ${cls}">${status}</span>`;
}

function renderClashTable(clashes) {
  const thead = document.querySelector("#clash-table thead tr");
  thead.innerHTML = `
    <th>#</th>
    <th>Status</th>
    <th>Element A</th>
    <th>Element B</th>
    <th>Comment</th>
  `;

  const tbody = document.getElementById("clash-tbody");

  // Group by Test
  const groups = {};
  clashes.forEach((c, i) => {
    const t = c.Test || "Unknown";
    if (!groups[t]) groups[t] = [];
    groups[t].push({ ...c, _index: i });
  });

  let html = "";
  for (const [test, rows] of Object.entries(groups)) {
    const groupId = `group-${test.replace(/\W+/g, "-")}`;
    // Sort rows by the numeric part of the Clash name
    rows.sort((a, b) => {
      const na = parseInt((a.Clash || "").replace(/\D+/g, "")) || 0;
      const nb = parseInt((b.Clash || "").replace(/\D+/g, "")) || 0;
      return na - nb;
    });

    html += `
      <tr class="group-header" data-group="${groupId}">
        <td colspan="5">
          <span class="group-arrow">▾</span>
          <strong>${test}</strong>
          <span class="group-count">${rows.length} clashes</span>
        </td>
      </tr>
    `;
    for (const c of rows) {
      const num = parseInt((c.Clash || "").replace(/\D+/g, "")) || "";
      html += `
        <tr class="group-row" data-group-id="${groupId}" data-index="${c._index}">
          <td style="text-align:center">${num}</td>
          <td>${statusBadge(c.Status)}</td>
          <td title="${c["Element A"] || ""}">${c["Element A"] || ""}</td>
          <td title="${c["Element B"] || ""}">${c["Element B"] || ""}</td>
          <td title="${c.Comment || ""}" style="color:#94a3b8;font-size:0.82rem">${c.Comment || ""}</td>
        </tr>
      `;
    }
  }
  tbody.innerHTML = html;

  // Toggle group on header click
  tbody.addEventListener("click", (e) => {
    const header = e.target.closest(".group-header");
    if (header) {
      const groupId = header.dataset.group;
      const arrow = header.querySelector(".group-arrow");
      const isCollapsed = arrow.textContent === "▸";
      arrow.textContent = isCollapsed ? "▾" : "▸";
      tbody.querySelectorAll(`.group-row[data-group-id="${groupId}"]`).forEach(
        (r) => (r.style.display = isCollapsed ? "" : "none")
      );
      return;
    }

    // Clash row click → highlight in viewer
    const row = e.target.closest(".group-row");
    if (!row) return;
    const idx = parseInt(row.dataset.index);
    const clash = clashes[idx];
    if (!clash) return;

    console.log("[Dashboard] clash clicked →", clash.pnt_id_a, clash.pnt_id_b);
    tbody.querySelectorAll("tr.selected").forEach((r) => r.classList.remove("selected"));
    row.classList.add("selected");

    viewerIframe.contentWindow?.postMessage(
      {
        type: "viewer-command",
        action: "highlightClash",
        payload: {
          pnt_id_a: clash.pnt_id_a ?? null,
          pnt_id_b: clash.pnt_id_b ?? null,
        },
      },
      "*"
    );
  });
}

// Listen for events from the viewer
window.addEventListener("message", (event) => {
  if (!event.data || event.data.type !== "viewer-event") return;

  if (event.data.event === "modelsLoaded") {
    console.log("[Dashboard] All models loaded in viewer");
  }
});

function initThemeToggle() {
  const btn   = document.getElementById("theme-toggle");
  const label = document.getElementById("theme-label");
  let light   = localStorage.getItem("dashboard-theme") === "light";

  function apply() {
    document.body.classList.toggle("light-mode", light);
    label.textContent = light ? "Dark" : "Light";
    const tc = light ? "#64748b" : "#94a3b8";
    if (_barChart) {
      const bc = light ? "#ffffff" : "#1e293b";
      _barChart.data.datasets.forEach((ds) => { ds.borderColor = bc; });
      _barChart.options.scales.x.grid.color          = light ? "#e2e8f0" : "#1e293b";
      _barChart.options.scales.y.grid.color          = light ? "#e2e8f0" : "#334155";
      _barChart.options.scales.x.ticks.color         = tc;
      _barChart.options.scales.y.ticks.color         = tc;
      _barChart.options.plugins.legend.labels.color  = tc;
      _barChart.update();
    }
    if (_donutChart) {
      _donutChart.data.datasets[0].borderColor        = light ? "#ffffff" : "#1e293b";
      _donutChart.options.plugins.legend.labels.color = tc;
      _donutChart.update();
    }
  }

  btn.addEventListener("click", () => {
    light = !light;
    localStorage.setItem("dashboard-theme", light ? "light" : "dark");
    apply();
  });

  apply();
}

document.addEventListener("DOMContentLoaded", () => { initDashboard(); initThemeToggle(); });
