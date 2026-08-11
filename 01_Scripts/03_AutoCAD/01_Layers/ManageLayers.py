# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, LayerTable, LayerTableRecord
from Autodesk.AutoCAD.Colors import Color, ColorMethod

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

LAYER_NAME = "PYNET_EXAMPLE"

lock = doc.LockDocument()
try:
    t = db.TransactionManager.StartTransaction()
    try:
        lt = t.GetObject(db.LayerTableId, OpenMode.ForWrite)

        # --- CREATE ---
        if not lt.Has(LAYER_NAME):
            lr = LayerTableRecord()
            lr.Name = LAYER_NAME
            lr.Color = Color.FromColorIndex(ColorMethod.ByAci, 3)  # green
            lt.Add(lr)
            t.AddNewlyCreatedDBObject(lr, True)
            print(f"Created layer: {LAYER_NAME}")
        else:
            print(f"Layer already exists: {LAYER_NAME}")

        # --- MODIFY ---
        lr = t.GetObject(lt[LAYER_NAME], OpenMode.ForWrite)
        lr.IsOff = False       # turn on
        lr.IsFrozen = False    # unfreeze  (cannot freeze current layer)
        lr.IsLocked = False    # unlock
        lr.Color = Color.FromColorIndex(ColorMethod.ByAci, 5)  # blue
        print(f"Modified layer: on={not lr.IsOff}, frozen={lr.IsFrozen}, locked={lr.IsLocked}, color={lr.Color.ColorIndex}")

        t.Commit()
    except:
        t.Abort()
        raise
finally:
    lock.Dispose()

# --- DELETE (separate transaction) ---
lock = doc.LockDocument()
try:
    t = db.TransactionManager.StartTransaction()
    try:
        lt = t.GetObject(db.LayerTableId, OpenMode.ForRead)
        if lt.Has(LAYER_NAME):
            lr = t.GetObject(lt[LAYER_NAME], OpenMode.ForWrite)
            lr.Erase()
            print(f"Deleted layer: {LAYER_NAME}")
        t.Commit()
    except:
        t.Abort()
        raise
finally:
    lock.Dispose()

print("Done")
