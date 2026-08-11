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
    alignments = []
    for aid in civil_doc.GetAlignmentIds():
        a = t.GetObject(aid, OpenMode.ForRead)
        alignments.append({"name": a.Name, "length": round(a.Length, 2)})
    t.Commit()
finally:
    t.Dispose()

print(f"Found {len(alignments)} alignments")
for a in alignments:
    print(f"  {a['name']} — {a['length']} m")

ia_Result = alignments
