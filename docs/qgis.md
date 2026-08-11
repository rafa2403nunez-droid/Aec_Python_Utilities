<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Guide: QGIS / PyQGIS scripts

Read this before writing any **standalone GIS** script (`01_Scripts/04_QGIS/`).

Related: [autocad-civil.md](autocad-civil.md) (GIS *inside* AutoCAD) · [security.md](security.md)

---

## Execution model — NOT PyNET-hosted

QGIS scripts are **fundamentally different** from the rest of the library:

- They do **not** run through the PyNET MCP bridge (the bridge only targets `roamer.exe` / `revit.exe`
  / `acad.exe`). `send_command` / `send_command_by_path` **cannot** run them.
- They run **headless** in **QGIS's own Python**, launched from QGIS's interpreter:
  ```
  & "C:\Program Files\QGIS 3.44.11\bin\python-qgis-ltr.bat" 04_QGIS\00_ProbeEnvironment.py
  ```
  (the `.bat` sets `PATH` / `PYTHONPATH` / `QGIS_PREFIX_PATH`). Run them from Bash/PowerShell, not MCP.
- Because they bypass the validator, **the security sandbox does not apply** — full standard Python is
  available here (`urllib`, etc.). The whitelist in [security.md](security.md) is only for bridge scripts.

> **Don't confuse the two GIS tracks:**
> - `04_QGIS/` → standalone PyQGIS (this guide).
> - `03_AutoCAD/20_GIS/` → GIS *inside* AutoCAD (Map 3D / Civil API), runs through the bridge → see
>   [autocad-civil.md](autocad-civil.md) and the MCP whitelist.

---

## Headless boilerplate

```python
import sys
from qgis.core import QgsApplication

# Headless app: no GUI event loop
qgs = QgsApplication([], False)
qgs.initQgis()

# Processing framework (Toolbox algorithms, usable headless)
qgis_plugins = r"C:\Program Files\QGIS 3.44.11\apps\qgis-ltr\python\plugins"
if qgis_plugins not in sys.path:
    sys.path.append(qgis_plugins)
from processing.core.Processing import Processing
import processing
Processing.initialize()

# ... your work ...

qgs.exitQgis()
```

> Don't hardcode the QGIS version path across machines if avoidable — derive it from the launcher's
> environment (`QGIS_PREFIX_PATH`) or read it from a config. `00_ProbeEnvironment.py` reports the live
> versions, providers and processing-algorithm count — run it first on a new machine.

---

## Data sources (network)

These scripts fetch external geodata over HTTP with `urllib.request` + `urllib.parse`:
- **Catastro** (WFS) — parcels.
- **IGN / MDT** — elevation/topography.

Network egress is fine here (no sandbox), but keep requests to known official endpoints.

---

## Scripts in `04_QGIS/`

- `00_ProbeEnvironment.py` — environment probe (versions, providers, processing algorithms).
- `01_CatastroWfs_Test.py` — catastro WFS fetch test.
- `02_MdtTopografia.py` — MDT / topography.
- `03_VientoAptitud.py` — wind suitability surface.
- `04_ExclusionesScore.py` — exclusion scoring.
- `05_PosicionAerogeneradores.py` — turbine siting.
- `06_RiesgoIncendio_LineaAT.py` — digital-twin flow A (line): vegetation/fuel surface
  (Sentinel-2 NDVI+NDMI, or PNOA VARI fallback) × slope → fire-risk ranking along the AT
  transmission-line corridor + presentation image. Civil 3D import:
  `03_AutoCAD/20_GIS/ImportarRiesgoIncendio.py`. Needs `02_MdtTopografia.py`.
- `07_DesbroceAerogeneradores.py` — digital-twin flow B (turbines): same fuel surface →
  vegetation-clearance ranking per wind turbine pad + presentation image. Civil 3D import:
  `03_AutoCAD/20_GIS/ImportarDesbroceAerogeneradores.py`. Needs `02_MdtTopografia.py` and
  `05_PosicionAerogeneradores.py`. The two flows are independent (each fetches its own S2).

Related workflow skill: `.claude/commands/WindSiting.md` (wind-farm siting study).
