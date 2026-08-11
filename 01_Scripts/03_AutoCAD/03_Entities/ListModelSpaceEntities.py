# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, BlockTable, BlockTableRecord

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

t = db.TransactionManager.StartTransaction()
try:
    bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
    ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead)
    counts = {}
    for oid in ms:
        obj = t.GetObject(oid, OpenMode.ForRead)
        type_name = type(obj).__name__
        counts[type_name] = counts.get(type_name, 0) + 1
    t.Commit()
finally:
    t.Dispose()

result = sorted([{"type": k, "count": v} for k, v in counts.items()], key=lambda x: -x["count"])
total = sum(r["count"] for r in result)
print(f"Found {total} entities across {len(result)} types")
for r in result:
    print(f"  {r['type']}: {r['count']}")

ia_Result = result
