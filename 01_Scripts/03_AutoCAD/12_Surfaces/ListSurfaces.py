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
    surfaces = []
    for sid in civil_doc.GetSurfaceIds():
        s = t.GetObject(sid, OpenMode.ForRead)
        surfaces.append({"name": s.Name, "type": type(s).__name__})
    t.Commit()
finally:
    t.Dispose()

print(f"Found {len(surfaces)} surfaces")
for s in surfaces:
    print(f"  {s['name']} ({s['type']})")

ia_Result = surfaces
