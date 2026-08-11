<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Project Context — PyNET Platform (Navisworks · Revit · AutoCAD/Civil 3D)

This file is the **always-loaded core**: rules that apply to every interaction. Host-specific
boilerplate, WinForms, stubs, Excel, security lists and UI deployment live in `docs/` and are
loaded **on demand** — see the Router below. Read the matching guide *before* writing a script.

---

## 1. Execution environment

PyNET runs Python scripts inside three Autodesk hosts: **Navisworks**, **Revit**, and
**AutoCAD / Civil 3D**. All execute via **Python.NET** (CPython 3.10+ with `pythonnet` — not
IronPython). Full Python 3 syntax plus the `clr` bridge to .NET and the Autodesk APIs.

Scripts are sent to the plugin through the MCP bridge and executed locally inside the host process.

> **QGIS is a separate environment.** Standalone **PyQGIS** scripts (`04_QGIS`) are NOT PyNET-hosted —
> they run headless in QGIS's own Python launcher, outside the bridge and its validator
> ([docs/qgis.md](docs/qgis.md)). GIS *inside* AutoCAD (Map 3D / Civil, `01_Scripts/03_AutoCAD/20_GIS`) **is**
> bridge-hosted and lives under [docs/autocad-civil.md](docs/autocad-civil.md).

> **Always check `list_active_instances` first** to identify the running host and PID — boilerplate
> and APIs differ per host. Civil 3D appears as **"AutoCAD"** in the instance list.

> **Timeout rule:** always use a minimum timeout of **60 seconds** when calling `send_command`.

> **MCP bridge:** `pip show pynet-mcp-bridge` (NOT `pynet-bridge`) using Python 3.10 pip at
> `%LOCALAPPDATA%\Programs\Python\Python310\Scripts\pip.exe`. Installed: **1.5.4**.
> Note there are two copies on this machine (uv at `~/.local/bin` and pip); uv wins on PATH, so
> keep both upgraded or a client may silently run the older one.

---

## 2. Router — read the matching guide BEFORE writing a script

| If the task is… | Read first (`Read`) |
|---|---|
| A **Navisworks** script | [docs/navisworks.md](docs/navisworks.md) |
| A **Revit** script | [docs/revit.md](docs/revit.md) |
| A Revit **element query / measurement** | [.claude/commands/RevitApiPatterns.md](.claude/commands/RevitApiPatterns.md) |
| An **AutoCAD / Civil 3D** script (incl. GIS *inside* AutoCAD — Map 3D, `01_Scripts/03_AutoCAD/20_GIS`) | [docs/autocad-civil.md](docs/autocad-civil.md) |
| A **standalone QGIS / PyQGIS** script (`04_QGIS`, headless, NOT Autodesk-hosted) | [docs/qgis.md](docs/qgis.md) |
| Any **form / dialog / custom UI** (WinForms) | [docs/winforms.md](docs/winforms.md) |
| Reading an **Excel** file | [docs/excel-mcp.md](docs/excel-mcp.md) |
| **Generating stubs** / VS Code IntelliSense | [docs/stubs.md](docs/stubs.md) |
| **Deploying buttons / modules / Output Window** | [docs/ui-deployment.md](docs/ui-deployment.md) |
| Exporting a **`.pnt`** package for the VS Code viewer | [docs/pnt-export.md](docs/pnt-export.md) |
| Operating the VS Code viewer via **MCP** (`viewer_*` tools — select, isolate, highlight clashes, properties) | [docs/viewer-mcp.md](docs/viewer-mcp.md) |
| The **bridge is not connected** — `mcp__pynet-bridge__*` tools missing, or `MCP error -32000: Connection closed` | [docs/bridge-troubleshooting.md](docs/bridge-troubleshooting.md) |
| Full **security** whitelist/blocklist | [docs/security.md](docs/security.md) |

The Router row above (`RevitApiPatterns`) is a **reference** to read before writing Revit queries —
it lives in `.claude/commands/` but is consulted, not run.

Everything else in `.claude/commands/` is a **workflow Skill** the *user* invokes via slash command:
`/ClashDetection`, `/ClashCoordination`, `/ClashToleranceComparison`, `/QCModelAudit`, `/QuantityTakeoff`, `/WindSiting`, `/PowerlineFireRisk`, `/DevMode`. They are
self-contained and auto-load when invoked — do not duplicate their content here. Suggest the matching
one when the user describes its task (e.g. a clash run, a QC audit, a 5D takeoff, a GIS/wind-farm siting study,
a powerline wildfire-risk / vegetation-management study).

---

## 3. Context sources — use in this order

Be efficient: check existing context before writing from scratch.

1. **`AI_History/`** (check first) — full log of every script run through the bridge.
   `Requests/` (sent scripts), `Responses/` (results/errors), `Pipe_Session_*.log`. If a similar
   problem was already solved, reuse the validated pattern.
2. **Example scripts (MANDATORY before writing from scratch)** — `01_Scripts/01_Navisworks/`,
   `01_Scripts/02_Revit/`, `01_Scripts/03_AutoCAD/`. Use `Glob` to list the relevant folder, then
   `Read` the closest match. The library is validated and production-ready.
3. **Live API exploration** — write a short `send_command` script to inspect the actual model at
   runtime. The live model is the most accurate reference.
4. **API stubs** — `02_PyNet Stubs/` (50k+ lines; never read in full — search a specific name only).

---

## 4. Execution responses

Scripts return JSON. On **Success**, `Status: "Success"` with `PrintMessages` and `Data`.
On **Error**, `Status: "Error"` with `Message` carrying the `Python.Runtime.PythonException` and
stack trace — analyze `Message` to auto-correct and retry.

---

## 5. Script output — `ia_Result` vs `print`

The plugin collects a global variable named **`ia_Result`** after execution (JSON-serializable:
list of dicts or a single dict). If absent, no data output is generated.

- **During development** (scripts via `send_command`): use `ia_Result` as the primary channel for
  structured data back to the AI. Keep `print` minimal (brief status only) — do NOT flood the
  Navisworks Output Window with per-element prints.
- **When saving a script for the user** (button / source): add informative `print` statements
  (progress, summary, results). `ia_Result` is then optional.

Rules: serializable values only (numbers, strings, lists, dicts); never return complex objects —
convert to `dict` first; always include a `"type"` field per object; keep structure consistent
across scripts. Do not abbreviate or transform output values unless explicitly asked.

```python
ia_Result = [{"type": "Wall", "id": 1, "name": "Wall A", "height": 3.2}]
```

---

## 6. Script creation & execution

Scripts are an iterative process — **not saved to source until the user explicitly says so**.
Prepare and send directly via `send_command`.

| | `send_command` | `send_command_by_path` |
|---|---|---|
| Use for | All development, one-off actions, fixes, analysis | Production scripts run repeatedly |
| Script lives | Inline in the MCP call | Already saved in the repo |

**Default is `send_command`.** Save to disk + switch to `send_command_by_path` when a script grows
past ~150 lines or after its first successful run as a recurring workflow (much faster: ~215s → ~0s).
Write short, optimized scripts (< ~80 lines inline). If a script grows too long, fix the design —
do not save one-off scripts to disk just to work around length.

---

## 7. Security (summary)

The static validator only runs for scripts sent through the **MCP bridge** (`send_command`) into an
Autodesk host. Scripts run by their own launcher — **standalone QGIS** (`04_QGIS`, see
[docs/qgis.md](docs/qgis.md)) or a user-saved button — do NOT pass through it. Use `pathlib.Path`,
never `os.path`.

Quick reference (full lists in [docs/security.md](docs/security.md)):
- **Allowed imports:** `clr`, `sys`, `json`, `re`, `time`, `datetime`, `pathlib`, `typing`,
  `threading`, `collections`, `xml`, `math`, `functools`, `pandas`, `plotly`, `matplotlib`, `dash`,
  `webbrowser`, `psutil`, `openpyxl`, `uuid`, `zipfile`, `io`, `mimetypes`, `difflib`, `csv`,
  `ifcopenshell`, `numpy`, `shapely`, `qgis`, `processing`. Submodules: `http.server` (only).
- **Blocked imports:** `os`, `subprocess`, `shutil`, `socket`, `urllib`, `glob`, `inspect`, …
- **The sandbox is closed on purpose — no network, no local server.** `urllib` is blocked at the
  root, and `flask` / `webview` are not whitelisted. The code that legitimately needs them (GIS
  fetches in `04_QGIS`, the viewer and dashboard servers) runs through its own launcher, outside
  the validator — so the bridge never has to open. Do not "fix" this by widening the whitelist.
- **Blocked calls:** `eval`, `exec`, `compile`, `__import__`, `getattr`, `setattr`, … (blocked for MCP
  only; user-authored scripts may use them).

Do NOT attempt to bypass these. If a script needs something blocked, tell the user and suggest an
alternative within scope.

---

## 8. Execution confirmation policy

- **Read-only scripts** (query, export, list): execute directly, no confirmation.
- **Write scripts** (modify, create, delete, update the model): ask the user **once** before the
  first execution.
- If a confirmed script fails and you fix it, **re-execute immediately without asking again** — the
  user already approved the intent.

---

## 9. Running Python — use MCP, always

The MCP bridge (`send_command`) is the right tool for any Python task — file generation, data
processing, Excel, API queries. The plugin runs CPython 3.10 with pandas, openpyxl, matplotlib, etc.
Only fall back to Bash/PowerShell for genuine OS operations (pip install, git). If a whitelisted
library is missing and needed regularly, flag it so it can be added.

> **Be scrupulous with arithmetic — never compute by hand.** Quantities, tolerances, sums, areas,
> coordinates and any figure reported to the user must be calculated in Python (via the MCP bridge),
> not estimated mentally. Even a "trivial" sum gets verified in code. A single wrong number erodes
> trust in the whole analysis — double-check totals before reporting them.

---

## 10. Interaction mode

**Default: Production.** Unless `/DevMode developer` was invoked this session, behave in Production:
- Act as an AI integrated into the software — no mention of scripts, Python, JSON, MCP, PIDs, API
  names, or internals.
- Describe actions and results in natural language ("I scanned the models and found 7 element
  groups").
- Explain failures in user-friendly terms.

Use **Developer Mode** (full scripts, JSON, stack traces) only when activated with `/DevMode developer`.
See the `DevMode` skill for the full spec.

> **Language:** match the user's conversation language (Spanish ↔ Spanish, English ↔ English).
> All persistent repo AI artifacts (this file, `docs/`, skills) stay in **English**. See `CODEX.md`.
