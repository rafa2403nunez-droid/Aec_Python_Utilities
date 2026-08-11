# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

# Button: build the active zone's terrain in Civil 3D from the PyQGIS engine output.
# Zone comes from 04_QGIS/zona_activa.json (outputs live in output/<slug>/).
# - Native TIN surface "MDT_<SLUG>" from the XYZ grid (IGN 5 m DEM).
# - Contour polylines (at their real elevation) on layer GIS_CURVAS_NIVEL.
# Re-running replaces the surface and the contour layer (repeatable import).

import clr
import json
from pathlib import Path

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("AecBaseMgd")
clr.AddReference("AeccDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, BlockTableRecord, Polyline, LayerTableRecord
from Autodesk.AutoCAD.Colors import Color, ColorMethod
from Autodesk.AutoCAD.Geometry import Point2d, Point3d, Point3dCollection
from Autodesk.Civil.ApplicationServices import CivilApplication
from Autodesk.Civil.DatabaseServices import TinSurface

# Repo location of the standalone PyQGIS engine (01_Scripts/04_QGIS). Set it once per machine in
# %USERPROFILE%\.pynet\paths.json (not versioned):  {"qgis_dir": "C:\\Repos\\PyNetLibrary\\01_Scripts\\04_QGIS"}
_PATHS = Path.home() / ".pynet" / "paths.json"
QGIS_DIR = (Path(json.loads(_PATHS.read_text(encoding="utf-8"))["qgis_dir"]) if _PATHS.exists()
            else Path(r"C:\Repos\PyNetLibrary\01_Scripts\04_QGIS"))
CFG = json.loads((QGIS_DIR / "zona_activa.json").read_text(encoding="utf-8"))
OUTPUT_DIR = QGIS_DIR / "output" / CFG["slug"]
XYZ_PATH = OUTPUT_DIR / "mdt_puntos.xyz"
CURVAS_PATH = OUTPUT_DIR / "curvas.geojson"
SURFACE_NAME = "MDT_" + CFG["slug"].upper()
LAYER_CURVAS = "GIS_CURVAS_NIVEL"
CHUNK = 20000

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database
civil_doc = CivilApplication.ActiveDocument

for p in (XYZ_PATH, CURVAS_PATH):
    if not p.exists():
        raise Exception("Falta el fichero de intercambio: " + str(p))

points = []
for line in XYZ_PATH.read_text(encoding="ascii").splitlines():
    x, y, z = line.split()
    points.append((float(x), float(y), float(z)))
print(f"Puntos MDT leidos: {len(points)}")

curvas = json.loads(CURVAS_PATH.read_text(encoding="utf-8"))["features"]
print(f"Curvas de nivel leidas: {len(curvas)}")

lock = doc.LockDocument()
try:
    t = db.TransactionManager.StartTransaction()
    try:
        # Replace existing surface on re-run
        for sid in civil_doc.GetSurfaceIds():
            surf = t.GetObject(sid, OpenMode.ForRead)
            if surf.Name == SURFACE_NAME:
                surf.UpgradeOpen()
                surf.Erase()
                print("Superficie anterior eliminada")

        surf_id = TinSurface.Create(db, SURFACE_NAME)
        surf = t.GetObject(surf_id, OpenMode.ForWrite)

        added = 0
        coll = Point3dCollection()
        for x, y, z in points:
            coll.Add(Point3d(x, y, z))
            if coll.Count >= CHUNK:
                surf.AddVertices(coll)
                added += coll.Count
                print(f"  ...{added} vertices")
                coll = Point3dCollection()
        if coll.Count:
            surf.AddVertices(coll)
            added += coll.Count
        print(f"Superficie TIN '{SURFACE_NAME}': {added} vertices")

        # Contour polylines layer
        lt = t.GetObject(db.LayerTableId, OpenMode.ForRead)
        if not lt.Has(LAYER_CURVAS):
            lt.UpgradeOpen()
            ltr = LayerTableRecord()
            ltr.Name = LAYER_CURVAS
            ltr.Color = Color.FromColorIndex(ColorMethod.ByAci, 8)
            lt.Add(ltr)
            t.AddNewlyCreatedDBObject(ltr, True)

        bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
        ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite)

        erased = 0
        for oid in ms:
            ent = t.GetObject(oid, OpenMode.ForRead)
            if hasattr(ent, "Layer") and ent.Layer == LAYER_CURVAS:
                ent.UpgradeOpen()
                ent.Erase()
                erased += 1
        if erased:
            print(f"Reimportacion: {erased} curvas anteriores eliminadas")

        n_pl = 0
        for feat in curvas:
            geom = feat.get("geometry") or {}
            elev = float((feat.get("properties") or {}).get("ELEV") or 0.0)
            lines = [geom["coordinates"]] if geom.get("type") == "LineString" else geom.get("coordinates", [])
            if geom.get("type") not in ("LineString", "MultiLineString"):
                continue
            for line in lines:
                if len(line) < 2:
                    continue
                pl = Polyline()
                for i, pt in enumerate(line):
                    pl.AddVertexAt(i, Point2d(pt[0], pt[1]), 0.0, 0.0, 0.0)
                pl.Elevation = elev
                pl.Layer = LAYER_CURVAS
                ms.AppendEntity(pl)
                t.AddNewlyCreatedDBObject(pl, True)
                n_pl += 1
        print(f"Curvas de nivel dibujadas: {n_pl}")

        t.Commit()
    except:
        t.Abort()
        raise
finally:
    lock.Dispose()

doc.SendStringToExecute("_.ZOOM _E ", True, False, False)

zs = [p[2] for p in points]
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox
MessageBox.Show(
    f"Superficie TIN: {SURFACE_NAME} ({len(points)} puntos)\n"
    f"Elevaciones: {min(zs):.0f} - {max(zs):.0f} m\n"
    f"Curvas de nivel: {n_pl} en capa {LAYER_CURVAS}",
    f"PyNET - Topografia {CFG['nombre']} (IGN MDT05)",
)
