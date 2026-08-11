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
    result = []
    for aid in civil_doc.GetAlignmentIds():
        a = t.GetObject(aid, OpenMode.ForRead)
        profiles = []
        for pid in a.GetProfileIds():
            p = t.GetObject(pid, OpenMode.ForRead)
            profiles.append(
                {
                    "name": p.Name,
                    "type": type(p).__name__,
                    "length": round(p.Length, 2),
                }
            )
        result.append({"alignment": a.Name, "profiles": profiles})
    t.Commit()
finally:
    t.Dispose()

for a in result:
    print(f"{a['alignment']}: {len(a['profiles'])} profiles")
    for p in a["profiles"]:
        print(f"  {p['name']} ({p['type']}) — {p['length']} m")

ia_Result = result
