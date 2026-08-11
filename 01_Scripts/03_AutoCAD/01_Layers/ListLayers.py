# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, LayerTable, LinetypeTable

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

t = db.TransactionManager.StartTransaction()
try:
    lt = t.GetObject(db.LayerTableId, OpenMode.ForRead)
    ltt = t.GetObject(db.LinetypeTableId, OpenMode.ForRead)

    # Build linetype id → name map
    lt_names = {}
    for ltid in ltt:
        ltr = t.GetObject(ltid, OpenMode.ForRead)
        lt_names[ltid.ToString()] = ltr.Name

    layers = []
    for lid in lt:
        lr = t.GetObject(lid, OpenMode.ForRead)
        layers.append(
            {
                "name": lr.Name,
                "on": not lr.IsOff,
                "frozen": lr.IsFrozen,
                "locked": lr.IsLocked,
                "color": lr.Color.ColorIndex if lr.Color else None,
                "linetype": lt_names.get(lr.LinetypeObjectId.ToString(), "Continuous"),
            }
        )
    t.Commit()
finally:
    t.Dispose()

print(f"Found {len(layers)} layers")
ia_Result = layers
