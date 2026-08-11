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
    blocks = []
    for bid in bt:
        btr = t.GetObject(bid, OpenMode.ForRead)
        if not btr.IsLayout and not btr.IsAnonymous:
            blocks.append(
                {
                    "name": btr.Name,
                    "entities": sum(1 for _ in btr),
                    "xref": btr.IsFromExternalReference,
                }
            )
    t.Commit()
finally:
    t.Dispose()

print(f"Found {len(blocks)} block definitions")
ia_Result = sorted(blocks, key=lambda b: b["name"])
