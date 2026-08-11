# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("AecBaseMgd")
clr.AddReference("AeccDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode
from Autodesk.Civil.ApplicationServices import CivilApplication

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database
civil_doc = CivilApplication.ActiveDocument

t = db.TransactionManager.StartTransaction()
try:
    corridors = []
    for cid in civil_doc.CorridorCollection:
        c = t.GetObject(cid, OpenMode.ForRead)
        corridors.append(
            {
                "name": c.Name,
                "baselines": c.Baselines.Count,
                "regions": sum(b.BaselineRegions.Count for b in c.Baselines),
            }
        )
    t.Commit()
finally:
    t.Dispose()

print(f"Found {len(corridors)} corridors")
for c in corridors:
    print(f"  {c['name']} — {c['baselines']} baselines, {c['regions']} regions")

ia_Result = corridors
