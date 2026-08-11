# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import sys
import json
from pathlib import Path
from datetime import datetime
import webbrowser

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application
clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

bundlePath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins"
              / "RAEN.Navisworks.PyNET.bundle" / "Contents" / "2024")
sys.path.append(str(bundlePath))
clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils #type:ignore

from Autodesk.Navisworks.Api import Application
doc = Application.ActiveDocument


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class DataExtractor:
    @staticmethod
    def Run(document):
        clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)
        tests = []
        for test in get_clash_tests(clashDoc):
            counts = {"New": 0, "Active": 0, "Reviewed": 0, "Approved": 0, "Resolved": 0}
            for r in test.Children:
                s = str(r.Status)
                if s in counts:
                    counts[s] += 1
            total = sum(counts.values())
            tol = round(test.Tolerance * 1000 * 0.3048, 1)
            tests.append({
                "name": test.DisplayName,
                "total": total,
                "new": counts["New"],
                "active": counts["Active"],
                "reviewed": counts["Reviewed"],
                "approved": counts["Approved"],
                "resolved": counts["Resolved"],
                "tolerance_mm": tol,
            })
        return tests


class MatrixBuilder:
    @staticmethod
    def Build(tests):
        rows, cols = [], []
        for t in tests:
            parts = t["name"].split(" vs ")
            if len(parts) != 2:
                continue
            a, b = parts[0].strip(), parts[1].strip()
            if a not in rows:
                rows.append(a)
            if b not in cols:
                cols.append(b)
        # index: (row, col) -> test data
        index = {}
        for t in tests:
            parts = t["name"].split(" vs ")
            if len(parts) == 2:
                index[(parts[0].strip(), parts[1].strip())] = t
        return rows, cols, index


class HtmlGenerator:
    REVIEWED_COLOR = "#e67e22"
    APPROVED_COLOR = "#27ae60"

    @staticmethod
    def StatusClass(test):
        if test["total"] == 0:
            return "empty", "—"
        approved = test["approved"]
        reviewed = test["reviewed"] + test["new"] + test["active"]
        if approved > 0 and reviewed == 0:
            label = f"{approved} A" if approved > 1 else "A"
            return "a", label
        if reviewed > 0 and approved == 0:
            label = f"{reviewed} R" if reviewed > 1 else "R"
            return "r", label
        return "mixed", f"{reviewed}R / {approved}A"

    @staticmethod
    def MatrixHtml(rows, cols, index):
        header = "".join(f"<th>{c}</th>" for c in cols)
        body = ""
        for r in rows:
            cells = ""
            for c in cols:
                t = index.get((r, c))
                if t is None:
                    cells += '<td class="na">—</td>'
                else:
                    css, label = HtmlGenerator.StatusClass(t)
                    cells += f'<td class="{css}">{label}</td>'
            body += f"<tr><th>{r}</th>{cells}</tr>"
        return f"""
        <table class="matrix">
          <thead><tr><th></th>{header}</tr></thead>
          <tbody>{body}</tbody>
        </table>"""

    @staticmethod
    def BarsHtml(tests):
        active = [t for t in tests if t["total"] > 0]
        if not active:
            return "<p style='color:#aaa'>No hay interferencias.</p>"
        max_total = max(t["total"] for t in active)
        bars = ""
        for t in active:
            pct = round(t["total"] / max_total * 100)
            reviewed = t["reviewed"] + t["new"] + t["active"]
            approved = t["approved"]
            if approved > 0 and reviewed == 0:
                css = "approved"
            elif reviewed > 0 and approved == 0:
                css = "reviewed"
            else:
                css = "mixed"
            bars += f"""
            <div class="bar-row">
              <div class="bar-label">{t["name"]}</div>
              <div class="bar-track">
                <div class="bar-fill {css}" style="width:{pct}%">{t["total"]}</div>
              </div>
              <div class="bar-count">{t["total"]}</div>
            </div>"""
        return f'<div class="bar-chart">{bars}</div>'

    @staticmethod
    def TestTableHtml(tests):
        rows = ""
        for t in tests:
            reviewed = t["reviewed"] + t["new"] + t["active"]
            tol = f"{t['tolerance_mm']} mm" if t["tolerance_mm"] else "—"
            if t["total"] == 0:
                status_html = '<span style="color:#aaa;font-size:12px;">Sin interferencias</span>'
            else:
                parts = []
                if reviewed > 0:
                    parts.append(f'<span class="badge reviewed">{reviewed} Reviewed</span>')
                if t["approved"] > 0:
                    parts.append(f'<span class="badge approved">{t["approved"]} Approved</span>')
                if t["resolved"] > 0:
                    parts.append(f'<span class="badge resolved">{t["resolved"]} Resolved</span>')
                status_html = " ".join(parts)
            rows += f"""
            <tr>
              <td>{t["name"]}</td>
              <td style="text-align:center">{tol}</td>
              <td style="text-align:center;font-weight:600">{t["total"]}</td>
              <td>{status_html}</td>
            </tr>"""
        return rows

    @staticmethod
    def Render(tests, rows, cols, index, doc_name, date_str):
        total = sum(t["total"] for t in tests)
        total_reviewed = sum(t["reviewed"] + t["new"] + t["active"] for t in tests)
        total_approved = sum(t["approved"] for t in tests)
        total_resolved = sum(t["resolved"] for t in tests)
        tests_with_clashes = sum(1 for t in tests if t["total"] > 0)
        num_tests = len(tests)

        pct_r = round(total_reviewed / total * 100) if total else 0
        pct_a = round(total_approved / total * 100) if total else 0

        # Donut: reviewed arc
        r_dash = round(pct_r * 0.628, 1)   # circumference ≈ 62.8 (r=10, stroke approach)
        a_dash = round(pct_a * 0.628, 1)
        r_offset = 15.7                      # start at top (-25% of 62.8)
        a_offset = round(-(r_dash - 15.7), 1)

        matrix_html = HtmlGenerator.MatrixHtml(rows, cols, index)
        bars_html = HtmlGenerator.BarsHtml(tests)
        test_rows_html = HtmlGenerator.TestTableHtml(tests)

        legend_note = (
            '<span style="color:#bbb;">— = sin interferencias &nbsp;|&nbsp; '
            '<span style="background:#f0f3f7;padding:1px 4px;border-radius:3px;">gris</span> = intra-modelo</span>'
        )

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Clash Dashboard — {doc_name} · {date_str}</title>
<style>
  :root {{
    --reviewed:#e67e22; --approved:#27ae60; --resolved:#3498db;
    --bg:#f4f6f9; --card:#fff; --header:#1a2332; --text:#2c3e50;
    --muted:#7f8c8d; --border:#dde3ec;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Segoe UI',Arial,sans-serif;background:var(--bg);color:var(--text);font-size:14px}}
  header{{background:var(--header);color:#fff;padding:22px 40px;display:flex;align-items:center;justify-content:space-between}}
  header h1{{font-size:19px;font-weight:600}}
  header .meta{{font-size:12px;color:#9ab;text-align:right;line-height:1.9}}
  main{{max-width:1200px;margin:0 auto;padding:28px 24px;display:grid;gap:22px}}
  .kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
  .kpi{{background:var(--card);border-radius:10px;padding:18px 22px;border-left:4px solid var(--muted);box-shadow:0 1px 4px rgba(0,0,0,.07)}}
  .kpi.reviewed{{border-color:var(--reviewed)}} .kpi.approved{{border-color:var(--approved)}}
  .kpi.info{{border-color:var(--resolved)}}
  .kpi .value{{font-size:34px;font-weight:700;line-height:1;margin-bottom:5px}}
  .kpi.reviewed .value{{color:var(--reviewed)}} .kpi.approved .value{{color:var(--approved)}}
  .kpi.info .value{{color:var(--resolved)}}
  .kpi .label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}}
  .kpi .sub{{font-size:11px;color:var(--muted);margin-top:3px}}
  h2{{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:14px}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
  .card{{background:var(--card);border-radius:10px;padding:22px;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
  table.matrix{{border-collapse:collapse;width:100%}}
  table.matrix th,table.matrix td{{border:1px solid var(--border);padding:9px 13px;text-align:center;font-size:13px}}
  table.matrix thead th{{background:var(--header);color:#fff;font-weight:600}}
  table.matrix tbody th{{background:#f0f3f7;font-weight:600;text-align:left;padding-left:14px}}
  table.matrix td.na{{background:#f0f3f7;color:#bbb;font-size:11px}}
  table.matrix td.empty{{color:#bbb;font-size:12px}}
  table.matrix td.r{{background:#fef3e8;color:var(--reviewed);font-weight:700}}
  table.matrix td.a{{background:#eafaf1;color:var(--approved);font-weight:700}}
  table.matrix td.mixed{{background:#fff8e1;font-weight:700;font-size:12px}}
  .bar-chart{{display:flex;flex-direction:column;gap:9px}}
  .bar-row{{display:flex;align-items:center;gap:9px}}
  .bar-label{{width:115px;font-size:12px;text-align:right;color:var(--text);flex-shrink:0}}
  .bar-track{{flex:1;background:#ecf0f1;border-radius:4px;height:21px;overflow:hidden}}
  .bar-fill{{height:100%;border-radius:4px;display:flex;align-items:center;padding-left:7px;font-size:11px;font-weight:700;color:#fff;min-width:24px}}
  .bar-fill.reviewed{{background:var(--reviewed)}} .bar-fill.approved{{background:var(--approved)}}
  .bar-fill.mixed{{background:linear-gradient(90deg,var(--reviewed) 0%,var(--approved) 100%)}}
  .bar-count{{font-size:12px;font-weight:600;width:18px;flex-shrink:0}}
  .donut-wrap{{display:flex;align-items:center;gap:22px;justify-content:center;padding:10px 0}}
  .donut-legend{{display:flex;flex-direction:column;gap:9px}}
  .legend-item{{display:flex;align-items:center;gap:7px;font-size:13px}}
  .legend-dot{{width:11px;height:11px;border-radius:50%;flex-shrink:0}}
  table.detail{{border-collapse:collapse;width:100%}}
  table.detail th{{background:#f0f3f7;padding:9px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);border-bottom:2px solid var(--border)}}
  table.detail td{{padding:10px 12px;border-bottom:1px solid var(--border);font-size:13px;vertical-align:middle}}
  table.detail tr:last-child td{{border-bottom:none}}
  table.detail tr:hover td{{background:#f8fafc}}
  .badge{{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600;margin-right:3px}}
  .badge.reviewed{{background:#fef3e8;color:var(--reviewed);border:1px solid #f9c98a}}
  .badge.approved{{background:#eafaf1;color:var(--approved);border:1px solid #a9dfbf}}
  .badge.resolved{{background:#ebf5fb;color:var(--resolved);border:1px solid #aed6f1}}
  footer{{text-align:center;padding:18px;font-size:11px;color:#aaa}}
</style>
</head>
<body>
<header>
  <div>
    <h1>Clash Detection Report — {doc_name}</h1>
    <div style="font-size:12px;color:#9ab;margin-top:3px">{num_tests} tests · modelos federados</div>
  </div>
  <div class="meta">
    <div>Generado: {date_str}</div>
    <div>PyNET Platform</div>
  </div>
</header>
<main>
  <div class="kpi-row">
    <div class="kpi">
      <div class="value">{total}</div>
      <div class="label">Total interferencias</div>
      <div class="sub">{tests_with_clashes} de {num_tests} tests activos</div>
    </div>
    <div class="kpi reviewed">
      <div class="value">{total_reviewed}</div>
      <div class="label">Reviewed</div>
      <div class="sub">Requieren coordinación ({pct_r}%)</div>
    </div>
    <div class="kpi approved">
      <div class="value">{total_approved}</div>
      <div class="label">Approved</div>
      <div class="sub">Condiciones aceptadas ({pct_a}%)</div>
    </div>
    <div class="kpi info">
      <div class="value">{total_resolved}</div>
      <div class="label">Resolved</div>
      <div class="sub">Resueltos</div>
    </div>
  </div>

  <div class="two-col">
    <div class="card">
      <h2>Matriz de interferencias</h2>
      {matrix_html}
      <div style="margin-top:11px;font-size:11px;color:var(--muted);display:flex;gap:14px;flex-wrap:wrap">
        <span><b style="color:var(--reviewed)">R</b> = Reviewed/New/Active</span>
        <span><b style="color:var(--approved)">A</b> = Approved</span>
        {legend_note}
      </div>
    </div>
    <div class="card">
      <h2>Distribución de estado</h2>
      <div class="donut-wrap">
        <svg width="130" height="130" viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="10" fill="none" stroke="#ecf0f1" stroke-width="3.8"/>
          <circle cx="18" cy="18" r="10" fill="none" stroke="{HtmlGenerator.REVIEWED_COLOR}" stroke-width="3.8"
            stroke-dasharray="{r_dash} {round(62.8-r_dash,1)}" stroke-dashoffset="{r_offset}" stroke-linecap="round"/>
          <circle cx="18" cy="18" r="10" fill="none" stroke="{HtmlGenerator.APPROVED_COLOR}" stroke-width="3.8"
            stroke-dasharray="{a_dash} {round(62.8-a_dash,1)}" stroke-dashoffset="{a_offset}" stroke-linecap="round"/>
          <text x="18" y="17" text-anchor="middle" font-size="5.5" font-weight="700" fill="#2c3e50">{total}</text>
          <text x="18" y="22" text-anchor="middle" font-size="3" fill="#7f8c8d">TOTAL</text>
        </svg>
        <div class="donut-legend">
          <div class="legend-item"><div class="legend-dot" style="background:var(--reviewed)"></div><b>{total_reviewed}</b>&nbsp;Reviewed ({pct_r}%)</div>
          <div class="legend-item"><div class="legend-dot" style="background:var(--approved)"></div><b>{total_approved}</b>&nbsp;Approved ({pct_a}%)</div>
          <div class="legend-item"><div class="legend-dot" style="background:var(--resolved)"></div><b>{total_resolved}</b>&nbsp;Resolved</div>
        </div>
      </div>
      <h2 style="margin-top:18px">Clashes por test</h2>
      {bars_html}
    </div>
  </div>

  <div class="card">
    <h2>Resumen por test</h2>
    <table class="detail">
      <thead>
        <tr><th>Test</th><th>Tolerancia</th><th>Total</th><th>Estado</th></tr>
      </thead>
      <tbody>
        {test_rows_html}
      </tbody>
    </table>
  </div>
</main>
<footer>PyNET Platform · {doc_name} · {date_str}</footer>
</body>
</html>"""


class DashboardManager:
    @staticmethod
    def Run(document):
        print("Extrayendo datos de interferencias...")
        tests = DataExtractor.Run(document)

        active = sum(1 for t in tests if t["total"] > 0)
        total = sum(t["total"] for t in tests)
        print(f"  {len(tests)} tests · {active} con interferencias · {total} clashes totales")

        rows, cols, index = MatrixBuilder.Build(tests)

        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        date_tag = datetime.now().strftime("%Y%m%d_%H%M")
        doc_name = Path(document.FileName).stem if document.FileName else "Navisworks"

        save_dir = Path.home() / "AppData" / "Roaming" / "Pynet" / "Navisworks" / "Dashboards"
        save_dir.mkdir(parents=True, exist_ok=True)
        out_path = save_dir / f"ClashDashboard_{doc_name}_{date_tag}.html"

        html = HtmlGenerator.Render(tests, rows, cols, index, doc_name, date_str)
        out_path.write_text(html, encoding="utf-8")

        print(f"Dashboard guardado: {out_path}")
        webbrowser.open(out_path.as_uri())

        MessageBox.Show(
            f"Dashboard generado correctamente.\n\n{out_path}",
            "Clash Dashboard",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )


DashboardManager.Run(doc)
