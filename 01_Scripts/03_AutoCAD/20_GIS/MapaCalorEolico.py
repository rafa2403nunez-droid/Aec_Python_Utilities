# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

# Button: wind-siting suitability heat map for the active zone.
# Zone comes from 04_QGIS/zona_activa.json (outputs live in output/<slug>/).
# Reads aptitud.json (analysis cells from the PyQGIS engine) and draws one
# colored Solid per cell at its terrain elevation, blue (low) -> red (high score),
# dark gray for excluded cells. Each cell carries the APTITUD_EOLICA property set
# (Score, VientoMs, PendientePct). Re-running cleans the layer first.

import clr
import json
from pathlib import Path

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("AecBaseMgd")
clr.AddReference("AecPropDataMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, BlockTableRecord, Solid, LayerTableRecord
from Autodesk.AutoCAD.Colors import Color, ColorMethod
from Autodesk.AutoCAD.Geometry import Point3d
from Autodesk.Aec.PropertyData.DatabaseServices import (
    PropertySetDefinition, PropertyDefinition, PropertyDataServices,
)
from Autodesk.Aec.PropertyData import DataType

# Repo location of the standalone PyQGIS engine (01_Scripts/04_QGIS). Set it once per machine in
# %USERPROFILE%\.pynet\paths.json (not versioned):  {"qgis_dir": "C:\\Repos\\PyNetLibrary\\01_Scripts\\04_QGIS"}
_PATHS = Path.home() / ".pynet" / "paths.json"
QGIS_DIR = (Path(json.loads(_PATHS.read_text(encoding="utf-8"))["qgis_dir"]) if _PATHS.exists()
            else Path(r"C:\Repos\PyNetLibrary\01_Scripts\04_QGIS"))
CFG = json.loads((QGIS_DIR / "zona_activa.json").read_text(encoding="utf-8"))
APT_PATH = QGIS_DIR / "output" / CFG["slug"] / "aptitud.json"
LAYER_NAME = "GIS_MAPA_CALOR"
PSET_NAME = "APTITUD_EOLICA"
NOD_PSET_KEY = "AEC_PROPERTY_SET_DEFS"
Z_OFFSET = 1.0  # drape 1 m above terrain

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

if not APT_PATH.exists():
    raise Exception("Falta el fichero de aptitud: " + str(APT_PATH))

data = json.loads(APT_PATH.read_text(encoding="utf-8"))
cells = data["cells"]
half = data["cell_size"] / 2.0
print(f"Mapa de aptitud leido: {len(cells)} celdas de {data['cell_size']} m ({data['zona']})")

# Stretch the gradient over the real score range of non-excluded cells
valid_scores = [c["score"] for c in cells if not c.get("excl")]
smin, smax = min(valid_scores), max(valid_scores)
span = float(max(1, smax - smin))
n_excl = sum(1 for c in cells if c.get("excl"))


def heat_rgb(t):
    """0..1 -> blue, cyan, green, yellow, red."""
    if t < 0.25:
        return 0, int(255 * t * 4), 255
    if t < 0.5:
        return 0, 255, int(255 * (1 - (t - 0.25) * 4))
    if t < 0.75:
        return int(255 * (t - 0.5) * 4), 255, 0
    return 255, int(255 * (1 - (t - 0.75) * 4)), 0


lock = doc.LockDocument()
try:
    t = db.TransactionManager.StartTransaction()
    try:
        lt = t.GetObject(db.LayerTableId, OpenMode.ForRead)
        if not lt.Has(LAYER_NAME):
            lt.UpgradeOpen()
            ltr = LayerTableRecord()
            ltr.Name = LAYER_NAME
            lt.Add(ltr)
            t.AddNewlyCreatedDBObject(ltr, True)

        nod = t.GetObject(db.NamedObjectsDictionaryId, OpenMode.ForRead)
        pset_dict = t.GetObject(nod[NOD_PSET_KEY], OpenMode.ForWrite)
        if not pset_dict.Contains(PSET_NAME):
            pset_def = PropertySetDefinition()
            pset_def.SetToStandard(db)
            pset_def.SubSetDatabaseDefaults(db)
            pset_def.Description = "Aptitud eolica v1: 70% viento + 30% pendiente"
            pset_def.AppliesToAll = True
            for name in ("Score", "VientoMs", "PendientePct"):
                pd = PropertyDefinition()
                pd.SetToStandard(db)
                pd.SubSetDatabaseDefaults(db)
                pd.Name = name
                pd.DataType = DataType.Real
                pd.DefaultData = 0.0
                pset_def.Definitions.Add(pd)
            pset_dict.SetAt(PSET_NAME, pset_def)
            t.AddNewlyCreatedDBObject(pset_def, True)
            print(f"Property set creado: {PSET_NAME}")
        pset_def = t.GetObject(pset_dict.GetAt(PSET_NAME), OpenMode.ForRead)

        bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
        ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite)

        erased = 0
        for oid in ms:
            ent = t.GetObject(oid, OpenMode.ForRead)
            if hasattr(ent, "Layer") and ent.Layer == LAYER_NAME:
                ent.UpgradeOpen()
                ent.Erase()
                erased += 1
        if erased:
            print(f"Reimportacion: {erased} celdas anteriores eliminadas")

        drawn = 0
        for c in cells:
            x, y, z = c["x"], c["y"], c["z"] + Z_OFFSET
            # Solid vertex order is BL, BR, TL, TR (edges 1-2 and 3-4)
            sol = Solid(
                Point3d(x - half, y - half, z), Point3d(x + half, y - half, z),
                Point3d(x - half, y + half, z), Point3d(x + half, y + half, z),
            )
            if c.get("excl"):
                r, g, b = 70, 70, 70  # excluded: dark gray
            else:
                r, g, b = heat_rgb((c["score"] - smin) / span)
            sol.Color = Color.FromRgb(r, g, b)
            sol.Layer = LAYER_NAME
            ms.AppendEntity(sol)
            t.AddNewlyCreatedDBObject(sol, True)

            PropertyDataServices.AddPropertySet(sol, pset_def.Id)
            pset = t.GetObject(PropertyDataServices.GetPropertySet(sol, pset_def.Id), OpenMode.ForWrite)
            pset.SetAt(pset.PropertyNameToId("Score"), float(c["score"]))
            pset.SetAt(pset.PropertyNameToId("VientoMs"), float(c["viento"]))
            pset.SetAt(pset.PropertyNameToId("PendientePct"), float(c["pendiente"]))

            drawn += 1
            if drawn % 1000 == 0:
                print(f"  ...{drawn} celdas")

        t.Commit()
        print(f"Mapa de calor dibujado: {drawn} celdas")
    except:
        t.Abort()
        raise
finally:
    lock.Dispose()

doc.SendStringToExecute("_.ZOOM _E ", True, False, False)

best = max(cells, key=lambda c: c["score"])
extra = ""
if "dist_red" in best:
    extra = f" | red a {best['dist_red']} m, acceso a {best['dist_acceso']} m"
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox
MessageBox.Show(
    f"Celdas: {len(cells)} (100x100 m) en capa {LAYER_NAME}\n"
    f"Excluidas (gris): {n_excl} | aptas: {len(valid_scores)}\n"
    f"Score: {smin} - {smax} | celdas >=70: {sum(1 for s in valid_scores if s >= 70)}\n"
    f"Mejor celda: score {best['score']} ({best['viento']} m/s, "
    f"pendiente {best['pendiente']}%{extra})\n"
    f"Criterios: {data.get('criterios', 'provisional: 70% viento + 30% pendiente')}",
    f"PyNET - Mapa de calor eolico ({data['zona']})",
)
