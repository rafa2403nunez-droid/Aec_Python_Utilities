<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Reference: Security & execution restrictions

Full whitelists/blocklists. The summary lives in `CLAUDE.md`; this is the complete reference. It mirrors the
validator in `PyNetBridge/pynet_mcp/server.py` — keep both in sync.

> **Scope:** this static analyzer only runs for scripts sent through the **MCP bridge** into an Autodesk
> host (Navisworks / Revit / AutoCAD). **Standalone QGIS scripts** (`04_QGIS`) run in QGIS's own Python and
> do **not** pass through it — see [qgis.md](qgis.md). Scripts a user writes/saves and runs from a button
> also skip the validator.

> **Do NOT attempt to bypass these restrictions.** If a script needs a blocked import or call, tell the user and suggest an alternative within scope. Use `pathlib.Path`, never `os.path`.

---

## Allowed CLR assemblies (`clr.AddReference`)

- `Autodesk.Navisworks.Api`, `.ComApi`, `.Interop.ComApi`, `.Clash`
- `RevitAPI`, `RevitAPIUI` (Revit)
- `AcMgd`, `AcCoreMgd`, `AcDbMgd`, `AecBaseMgd`, `AecPropDataMgd`, `AeccDbMgd`, `ManagedMapApi` (AutoCAD / Civil 3D / Map 3D)
- `System`, `System.Windows.Forms`, `System.Drawing`, `System.Collections.Generic`
- `Raen.Core.Pynet.*`, `Raen.Navisworks.Pynet.*`, `Raen.Revit.Pynet.*`, `Raen.Civil3D.Pynet.*` (any version)

`from Autodesk.* import …` / `from System import …` pass because the import root (`Autodesk`, `System`) is
whitelisted. Any other assembly / root is rejected.

## Allowed Python imports

`clr`, `sys`, `json`, `re`, `time`, `datetime`, `pathlib`, `typing`, `threading`, `collections`, `xml`, `math`, `functools`, `pandas`, `plotly`, `matplotlib`, `dash`, `webbrowser`, `psutil`, `openpyxl`, `uuid`, `zipfile`, `io`, `mimetypes`, `difflib`, `csv`, `ifcopenshell`, `numpy`, `shapely`, `qgis`, `processing`

Project-local shared modules also allowed: `pynet_clash`, `CoordinationDashboard` (≥ 1.5.4).
These are not third-party packages — they sit next to the script being run. `CoordinationDashboard`
is imported by `CoordinationWorkflow.py`, which runs through `send_command_by_path` and therefore
**does** pass the validator.

- `openpyxl` requires bridge **≥ 1.4.7** (not whitelisted in 1.4.6).
- `numpy` / `shapely` require bridge **≥ 1.5.4** (generative design).

### Submodule-level allows (the bare root is NOT allowed)

- `http.server` — serving local content (not `http.client` / `http.cookiejar`).

That is the whole list. There is no submodule escape hatch for `urllib`.

## Blocked Python imports

`os`, `subprocess`, `shutil`, `socket`, `urllib`, `ctypes`, `pickle`, `importlib`, `signal`, `multiprocessing`, `tempfile`, `glob`, `inspect`, `code`, `codeop`

## The sandbox is closed on purpose

No outbound network, no local server — decided in bridge 1.4.10 (`b7fa74e`), which reverted an
earlier widening. Specifically **not** whitelisted, and not to be re-added "for consistency":

| Not allowed | Why it does not need to be |
|---|---|
| `urllib` (and every submodule) | The scripts that fetch GIS data (catastro / WFS / MDT) live in `04_QGIS` and run in QGIS's own Python — they never reach this validator. The bridge-hosted GIS scripts (`03_AutoCAD/20_GIS`) use no network at all. |
| `flask`, `webview` | The viewer server and the coordination dashboard run from their own launcher, outside the bridge. A bridge script only *starts* the dashboard (via `CoordinationDashboard`, which is allowed); it never imports the server libraries itself. |

If a script sent through the bridge appears to need one of these, the script is in the wrong
place: it belongs to a launcher-run workflow, not to `send_command`.

## Blocked calls

`eval`, `exec`, `compile`, `__import__`, `getattr`, `setattr`, `delattr`, `globals`, `locals`, `vars`, `breakpoint`

## Blocked attribute access

`__builtins__`, `__subclasses__`, `__globals__`, `__code__`
