# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("AecBaseMgd")
clr.AddReference("AecPropDataMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, BlockTable, BlockTableRecord
from Autodesk.Aec.PropertyData.DatabaseServices import PropertyDataServices

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

PSET_NAME = "PYNET_TEST_PSET"

# Find all objects with the PropertySet attached
t = db.TransactionManager.StartTransaction()
try:
    nod = t.GetObject(db.NamedObjectsDictionaryId, OpenMode.ForRead)
    pset_dict = t.GetObject(nod["AEC_PROPERTY_SET_DEFS"], OpenMode.ForRead)
    pset_def = t.GetObject(pset_dict.GetAt(PSET_NAME), OpenMode.ForRead)
    pset_def_id = pset_def.Id

    bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
    ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead)

    found_handles = []
    found_types = []
    for oid in ms:
        obj = t.GetObject(oid, OpenMode.ForRead)
        for used_id in PropertyDataServices.GetPropertySetDefinitionsUsed(obj):
            if used_id == pset_def_id:
                found_handles.append(f"{obj.Handle.Value:X}")
                found_types.append(type(obj).__name__)
                break

    t.Commit()
finally:
    t.Dispose()

print(f"Found {len(found_handles)} object(s) with '{PSET_NAME}'")
for obj_type, handle in zip(found_types, found_handles):
    print(f"  {obj_type} — handle {handle}")

if found_handles:
    # Zoom to extents + select all found objects
    handles_lisp = " ".join(f'(handent "{h}")' for h in found_handles)
    cmd = (
        f"_.UCS _W "
        f"_.-VIEW _TOP "
        f"_.ZOOM _E "
        f"_.REGEN "
        f"_.SELECT '_SI {handles_lisp}  "
    )
    lock = doc.LockDocument()
    try:
        doc.SendStringToExecute(cmd, True, False, False)
    finally:
        lock.Dispose()

ia_Result = [{"type": t, "handle": h} for t, h in zip(found_types, found_handles)]
