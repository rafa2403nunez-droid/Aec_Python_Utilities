# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, DBDictionary, Layout

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

t = db.TransactionManager.StartTransaction()
try:
    layout_dict = t.GetObject(db.LayoutDictionaryId, OpenMode.ForRead)
    layouts = []
    for entry in layout_dict:
        layout = t.GetObject(entry.Value, OpenMode.ForRead)
        layouts.append(
            {
                "name": layout.LayoutName,
                "tab_order": layout.TabOrder,
                "is_model": layout.ModelType,
            }
        )
    t.Commit()
finally:
    t.Dispose()

layouts = sorted(layouts, key=lambda l: l["tab_order"])
print(f"Found {len(layouts)} layouts")
for l in layouts:
    tag = "Model" if l["is_model"] else "Paper"
    print(f"  [{l['tab_order']}] {l['name']} ({tag})")

ia_Result = layouts
