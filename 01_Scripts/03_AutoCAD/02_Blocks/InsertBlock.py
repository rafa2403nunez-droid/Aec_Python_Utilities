# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import math

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import (
    OpenMode,
    BlockTable,
    BlockTableRecord,
    BlockReference,
)
from Autodesk.AutoCAD.Geometry import Point3d, Scale3d

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

# --- Config ---
BLOCK_NAME = "Catch Basin"  # must exist in the drawing
POSITION = Point3d(100.0, 200.0, 0.0)
ROTATION_DEG = 90.0
SCALE = 1.0
LAYER = "C-STRM-STRC"  # optional: set layer on the reference

lock = doc.LockDocument()
try:
    t = db.TransactionManager.StartTransaction()
    try:
        bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)

        if not bt.Has(BLOCK_NAME):
            print(f"Block '{BLOCK_NAME}' not found in drawing")
        else:
            ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite)

            ref = BlockReference(POSITION, bt[BLOCK_NAME])
            ref.Rotation = math.radians(ROTATION_DEG)
            ref.ScaleFactors = Scale3d(SCALE)
            if LAYER:
                ref.Layer = LAYER

            ms.AppendEntity(ref)
            t.AddNewlyCreatedDBObject(ref, True)

            print(f"Inserted '{BLOCK_NAME}' at {POSITION} rotated {ROTATION_DEG}° — handle: {ref.Handle}")

        t.Commit()
    except:
        t.Abort()
        raise
finally:
    lock.Dispose()
