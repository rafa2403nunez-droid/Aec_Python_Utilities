# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

# Button: import Catastro parcels (GeoJSON from the PyQGIS engine) into Civil 3D.
# Reads the exchange GeoJSON, draws each parcel as a closed polyline on layer
# GIS_PARCELAS_CATASTRO and attaches a CATASTRO property set (RefCatastral, AreaM2).
# Re-running cleans the layer first, so the import is repeatable (re-sync).

import clr
import json
from pathlib import Path

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("AecBaseMgd")
clr.AddReference("AecPropDataMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import (
    OpenMode, BlockTableRecord, Polyline, LayerTableRecord,
)
from Autodesk.AutoCAD.Colors import Color, ColorMethod
from Autodesk.AutoCAD.Geometry import Point2d
from Autodesk.Aec.PropertyData.DatabaseServices import (
    PropertySetDefinition, PropertyDefinition, PropertyDataServices,
)
from Autodesk.Aec.PropertyData import DataType

# Repo location of the standalone PyQGIS engine (01_Scripts/04_QGIS). Set it once per machine in
# %USERPROFILE%\.pynet\paths.json (not versioned):  {"qgis_dir": "C:\\Repos\\PyNetLibrary\\01_Scripts\\04_QGIS"}
_PATHS = Path.home() / ".pynet" / "paths.json"
QGIS_DIR = (Path(json.loads(_PATHS.read_text(encoding="utf-8"))["qgis_dir"]) if _PATHS.exists()
            else Path(r"C:\Repos\PyNetLibrary\01_Scripts\04_QGIS"))
GEOJSON_PATH = QGIS_DIR / "output" / "parcelas_test.geojson"
LAYER_NAME = "GIS_PARCELAS_CATASTRO"
PSET_NAME = "CATASTRO"
NOD_PSET_KEY = "AEC_PROPERTY_SET_DEFS"

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

if not GEOJSON_PATH.exists():
    raise Exception("No se encuentra el GeoJSON de intercambio: " + str(GEOJSON_PATH))

features = json.loads(GEOJSON_PATH.read_text(encoding="utf-8"))["features"]
print(f"GeoJSON leido: {len(features)} parcelas en {GEOJSON_PATH.name}")


def rings_of(geometry):
    """Yield every ring (exterior + holes) as a list of [x, y] points."""
    gtype, coords = geometry["type"], geometry["coordinates"]
    polygons = [coords] if gtype == "Polygon" else coords if gtype == "MultiPolygon" else []
    for polygon in polygons:
        for ring in polygon:
            yield ring


lock = doc.LockDocument()
try:
    t = db.TransactionManager.StartTransaction()
    try:
        # Layer (create if missing)
        lt = t.GetObject(db.LayerTableId, OpenMode.ForRead)
        if not lt.Has(LAYER_NAME):
            lt.UpgradeOpen()
            ltr = LayerTableRecord()
            ltr.Name = LAYER_NAME
            ltr.Color = Color.FromColorIndex(ColorMethod.ByAci, 3)
            lt.Add(ltr)
            t.AddNewlyCreatedDBObject(ltr, True)
            print(f"Capa creada: {LAYER_NAME}")

        # Property set definition (create if missing)
        nod = t.GetObject(db.NamedObjectsDictionaryId, OpenMode.ForRead)
        pset_dict = t.GetObject(nod[NOD_PSET_KEY], OpenMode.ForWrite)
        if not pset_dict.Contains(PSET_NAME):
            pset_def = PropertySetDefinition()
            pset_def.SetToStandard(db)
            pset_def.SubSetDatabaseDefaults(db)
            pset_def.Description = "Atributos catastrales (INSPIRE WFS)"
            pset_def.AppliesToAll = True
            for name, dtype, default in [
                ("RefCatastral", DataType.Text, ""),
                ("AreaM2", DataType.Real, 0.0),
            ]:
                pd = PropertyDefinition()
                pd.SetToStandard(db)
                pd.SubSetDatabaseDefaults(db)
                pd.Name = name
                pd.DataType = dtype
                pd.DefaultData = default
                pset_def.Definitions.Add(pd)
            pset_dict.SetAt(PSET_NAME, pset_def)
            t.AddNewlyCreatedDBObject(pset_def, True)
            print(f"Property set creado: {PSET_NAME}")
        pset_def = t.GetObject(pset_dict.GetAt(PSET_NAME), OpenMode.ForRead)

        bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
        ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite)

        # Re-sync: clear previous import on this layer
        erased = 0
        for oid in ms:
            ent = t.GetObject(oid, OpenMode.ForRead)
            if hasattr(ent, "Layer") and ent.Layer == LAYER_NAME:
                ent.UpgradeOpen()
                ent.Erase()
                erased += 1
        if erased:
            print(f"Reimportacion: {erased} entidades anteriores eliminadas")

        drawn = 0
        for feat in features:
            props = feat.get("properties", {})
            ref = props.get("nationalcadastralreference") or ""
            area = float(props.get("areavalue") or 0.0)
            for ring in rings_of(feat.get("geometry") or {}):
                pl = Polyline()
                for i, pt in enumerate(ring):
                    pl.AddVertexAt(i, Point2d(pt[0], pt[1]), 0.0, 0.0, 0.0)
                pl.Closed = True
                pl.Layer = LAYER_NAME
                ms.AppendEntity(pl)
                t.AddNewlyCreatedDBObject(pl, True)

                PropertyDataServices.AddPropertySet(pl, pset_def.Id)
                pset = t.GetObject(PropertyDataServices.GetPropertySet(pl, pset_def.Id), OpenMode.ForWrite)
                pset.SetAt(pset.PropertyNameToId("RefCatastral"), ref)
                pset.SetAt(pset.PropertyNameToId("AreaM2"), area)
                drawn += 1

        t.Commit()
        print(f"Importacion completada: {drawn} polilineas de parcela con atributos catastrales")
    except:
        t.Abort()
        raise
finally:
    lock.Dispose()

doc.SendStringToExecute("_.ZOOM _E ", True, False, False)

clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox
MessageBox.Show(
    f"Parcelas importadas: {drawn}\nCapa: {LAYER_NAME}\nProperty set: {PSET_NAME} (RefCatastral, AreaM2)",
    "PyNET - Importar parcelas Catastro",
)
